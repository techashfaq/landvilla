# Iteration 3 E2E (public URL): owner listing, moderation, broker gate, leads privacy, report/block,
# account deletion, legal, featured payments (not configured), commissions, SEO/sitemap.
import io
import os
import struct
import uuid
import zlib
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE = (os.environ.get("EXPO_PUBLIC_BACKEND_URL") or os.environ.get("EXPO_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"
TOK = {"buyer": "test_session_buyer_landvilla", "admin": "test_session_admin_landvilla",
       "owner": "test_session_owner_landvilla", "broker": "test_session_broker_landvilla"}
LOC_SLUG = "chandukhedi"
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
S = {}


def H(role):
    return {"Authorization": f"Bearer {TOK[role]}"}


def png(seed):
    raw = b"\x00" + bytes([seed % 256, 10, 20]) * 1
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def upload(role, kind, seed):
    r = requests.post(f"{API}/uploads", headers=H(role), files={"file": (f"p{seed}.png", io.BytesIO(png(seed)), "image/png")}, data={"kind": kind})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def loc_id():
    return db.localities.find_one({"slug": LOC_SLUG})["id"]


def listing_body(photo, posted_as="owner", title=None):
    return {"posted_as": posted_as, "title_en": title or f"TEST_ 2BHK flat {uuid.uuid4().hex[:5]}", "description_en": "TEST_ spacious flat near main road, good light.",
            "purpose": "buy", "segment": "residential", "type": "apartment", "locality_id": loc_id(), "price": 3123457, "bhk": 2,
            "area_sqft": 1111, "photo_ids": [photo], "owner_declaration_accepted": True}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    db.blocks.delete_many({"blocker_id": {"$in": ["user_testowner01", "user_testbuyer01"]}})
    yield
    pids = S.get("props", [])
    db.properties.delete_many({"id": {"$in": pids}})
    db.enquiries.delete_many({"property_id": {"$in": pids}})
    db.abuse_reports.delete_many({"$or": [{"target_id": {"$in": pids + S.get("enqs", [])}}, {"enquiry_id": {"$in": S.get("enqs", [])}}]})
    db.contact_access_logs.delete_many({"enquiry_id": {"$in": S.get("enqs", [])}})
    db.blocks.delete_many({"blocker_id": {"$in": ["user_testowner01", "user_testbuyer01"]}})
    db.broker_profiles.delete_many({"user_id": "user_testbroker01"})
    db.commission_agreements.delete_many({"property_description": {"$regex": "^TEST_"}})
    db.deletion_requests.delete_many({"email": {"$regex": "^test_"}})


# --- owner flow + validation
def test_owner_listing_validation_and_create():
    photo = upload("owner", "property_photo", 1)
    b = listing_body(photo); b["owner_declaration_accepted"] = False
    assert requests.post(f"{API}/listings", headers=H("owner"), json=b).status_code == 400
    b = listing_body(photo); b["photo_ids"] = []
    assert requests.post(f"{API}/listings", headers=H("owner"), json=b).status_code == 422
    b = listing_body(photo); b["bhk"] = None
    assert requests.post(f"{API}/listings", headers=H("owner"), json=b).status_code == 400
    other = upload("buyer", "property_photo", 2)
    assert requests.post(f"{API}/listings", headers=H("owner"), json=listing_body(other)).status_code == 400
    r = requests.post(f"{API}/listings", headers=H("owner"), json=listing_body(photo))
    assert r.status_code == 200, r.text
    p = r.json(); S["prop"] = p["id"]; S.setdefault("props", []).append(p["id"])
    assert p["listing_status"] == "pending_review" and "photo_hashes" not in p
    mine = requests.get(f"{API}/listings/mine", headers=H("owner")).json()
    items = mine["items"] if isinstance(mine, dict) else mine
    assert any(x["id"] == p["id"] and x["listing_status"] == "pending_review" for x in items)
    # not public while pending
    assert requests.get(f"{API}/properties/{p['id']}").status_code == 404
    # duplicate (same photo) flagged
    r2 = requests.post(f"{API}/listings", headers=H("owner"), json=listing_body(photo))
    S["dup"] = r2.json()["id"]; S["props"].append(S["dup"])
    assert any(f["property_id"] == p["id"] for f in r2.json()["duplicate_flags"])


# --- admin moderation queue
def test_admin_queue_and_moderation():
    assert requests.get(f"{API}/admin/listings?status=pending_review", headers=H("owner")).status_code == 403
    q = requests.get(f"{API}/admin/listings?status=pending_review", headers=H("admin")).json()
    dup = next(x for x in q["items"] if x["id"] == S["dup"])
    assert dup["duplicate_flags"]
    assert requests.post(f"{API}/admin/listings/{S['dup']}/reject", headers=H("admin"), json={"note": "no"}).status_code == 400
    assert requests.post(f"{API}/admin/listings/{S['dup']}/request-changes", headers=H("admin"), json={"note": "abc"}).status_code == 400
    r = requests.post(f"{API}/admin/listings/{S['dup']}/request-changes", headers=H("admin"), json={"note": "Please add more photos"})
    assert r.status_code == 200
    mine = requests.get(f"{API}/listings/mine", headers=H("owner")).json()
    items = mine["items"] if isinstance(mine, dict) else mine
    d = next(x for x in items if x["id"] == S["dup"])
    assert d["listing_status"] == "changes_requested" and "Please add more photos" in str(d)
    assert requests.post(f"{API}/admin/listings/{S['dup']}/reject", headers=H("admin"), json={"note": "Duplicate listing"}).status_code == 200
    assert requests.post(f"{API}/admin/listings/{S['prop']}/approve", headers=H("admin"), json={"note": ""}).status_code == 200
    assert requests.get(f"{API}/properties/{S['prop']}").status_code == 200
    s = requests.get(f"{API}/properties", params={"locality": LOC_SLUG}).json()
    assert S["prop"] in str(s)


# --- broker gate + private docs
def test_broker_gate_and_private_docs():
    db.broker_profiles.delete_many({"user_id": "user_testbroker01"})
    photo = upload("broker", "property_photo", 3)
    assert requests.post(f"{API}/listings", headers=H("broker"), json=listing_body(photo, "broker")).status_code == 403
    base = {"full_name": "TEST Broker", "phone": "9876543210", "declaration_accepted": True}
    assert requests.post(f"{API}/broker/apply", headers=H("broker"), json={**base, "document_ids": []}).status_code == 422
    doc = upload("broker", "broker_doc", 4)
    assert requests.get(f"{API}/files/{doc}", headers=H("buyer")).status_code == 403
    assert requests.get(f"{API}/files/{doc}").status_code == 403
    assert requests.get(f"{API}/files/{doc}", headers=H("broker")).status_code == 200
    assert requests.get(f"{API}/files/{doc}", headers=H("admin")).status_code == 200
    r = requests.post(f"{API}/broker/apply", headers=H("broker"), json={**base, "document_ids": [doc]})
    assert r.status_code == 200 and r.json()["status"] == "pending"
    assert requests.post(f"{API}/broker/apply", headers=H("broker"), json={**base, "document_ids": [doc]}).status_code == 409
    assert requests.post(f"{API}/listings", headers=H("broker"), json=listing_body(photo, "broker")).status_code == 403
    assert requests.post(f"{API}/admin/brokers/user_testbroker01/approve", headers=H("admin"), json={"note": ""}).status_code == 200
    assert requests.get(f"{API}/me/lister", headers=H("broker")).json()["can_post_as_broker"] is True
    r = requests.post(f"{API}/listings", headers=H("broker"), json=listing_body(photo, "broker"))
    assert r.status_code == 200; S["props"].append(r.json()["id"])
    assert requests.post(f"{API}/admin/brokers/user_testbroker01/suspend", headers=H("admin"), json={"note": "TEST suspend"}).status_code == 200
    assert requests.get(f"{API}/me/lister", headers=H("broker")).json()["can_post_as_broker"] is False
    assert requests.post(f"{API}/admin/listings/{r.json()['id']}/approve", headers=H("admin"), json={"note": ""}).status_code in (400, 403)


# --- leads + privacy + messages
def test_leads_privacy_and_messages():
    e1 = requests.post(f"{API}/enquiries", headers=H("buyer"), json={"property_id": S["prop"], "name": "TEST Buyer", "phone": "9123456780",
                                                                   "intent": "info", "share_phone_consent": False, "message": "TEST hi"})
    assert e1.status_code == 200, e1.text
    e2 = requests.post(f"{API}/enquiries", headers=H("broker"), json={"property_id": S["prop"], "name": "TEST Consent", "phone": "9988776655",
                                                                    "intent": "info", "share_phone_consent": True})
    assert e2.status_code == 200, e2.text
    S["e1"], S["e2"] = e1.json()["id"], e2.json()["id"]; S["enqs"] = [S["e1"], S["e2"]]
    leads = requests.get(f"{API}/leads", headers=H("owner"))
    assert "9123456780" not in leads.text and "9988776655" not in leads.text
    l1 = requests.get(f"{API}/leads/{S['e1']}", headers=H("owner"))
    assert "9123456780" not in l1.text and l1.json()["phone"] is None and l1.json()["phone_masked"] == "91XXXXXX80"
    n0 = db.contact_access_logs.count_documents({"enquiry_id": S["e2"]})
    l2 = requests.get(f"{API}/leads/{S['e2']}", headers=H("owner")).json()
    assert l2["phone"] == "9988776655"
    assert db.contact_access_logs.count_documents({"enquiry_id": S["e2"]}) == n0 + 1
    assert requests.get(f"{API}/leads/{S['e1']}", headers=H("buyer")).status_code == 404
    u = requests.patch(f"{API}/leads/{S['e1']}", headers=H("owner"), json={"status": "contacted", "note": "TEST note",
                                                                           "follow_up_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()})
    assert u.status_code == 200 and u.json()["notes"][-1]["text"] == "TEST note"
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("owner"), json={"text": "Hello from owner"}).status_code == 200
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("buyer"), json={"text": "Hello from buyer"}).status_code == 200
    t = requests.get(f"{API}/enquiries/{S['e1']}", headers=H("buyer")).json()
    assert [m["from"] for m in t["messages"]][-2:] == ["lister", "buyer"] and "notes" not in t
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("admin"), json={"text": "x"}).status_code == 404


# --- report & block
def test_report_and_block():
    r = requests.post(f"{API}/properties/{S['prop']}/report", headers=H("buyer"), json={"reason": "fake_listing", "note": "TEST"})
    assert r.status_code == 200
    assert requests.post(f"{API}/properties/{S['prop']}/report", headers=H("buyer"), json={"reason": "spam"}).status_code == 409
    assert requests.post(f"{API}/enquiries/{S['e1']}/report-user", headers=H("owner"), json={"reason": "abuse", "note": "TEST"}).status_code == 200
    assert requests.post(f"{API}/enquiries/{S['e1']}/block", headers=H("owner")).status_code == 200
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("buyer"), json={"text": "blocked?"}).status_code == 403
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("owner"), json={"text": "blocked?"}).status_code == 403
    db.enquiries.update_one({"id": S["e1"]}, {"$set": {"created_at": datetime.now(timezone.utc) - timedelta(days=2)}})
    ne = requests.post(f"{API}/enquiries", headers=H("buyer"), json={"property_id": S["prop"], "name": "TEST Buyer", "phone": "9123456780", "intent": "info", "share_phone_consent": False})
    assert ne.status_code == 403
    assert requests.delete(f"{API}/enquiries/{S['e1']}/block", headers=H("owner")).status_code == 200
    assert requests.post(f"{API}/enquiries/{S['e1']}/messages", headers=H("buyer"), json={"text": "unblocked"}).status_code == 200
    reps = requests.get(f"{API}/admin/reports", headers=H("admin")).json()["items"]
    rep = next(x for x in reps if x.get("target_id") == S["prop"])
    assert requests.post(f"{API}/admin/reports/{rep['id']}/resolve", headers=H("admin"), json={"action": "dismiss", "note": ""}).status_code == 422
    assert requests.post(f"{API}/admin/reports/{rep['id']}/resolve", headers=H("admin"), json={"action": "dismiss", "note": "TEST ok"}).status_code == 200


# --- account deletion with throwaway user
def test_account_delete_throwaway():
    uid_, tok = f"user_TESTdel{uuid.uuid4().hex[:6]}", f"TESTdel_{uuid.uuid4().hex}"
    db.users.insert_one({"user_id": uid_, "email": f"{uid_}@example.com", "name": "TEST Del", "role": "buyer", "created_at": datetime.now(timezone.utc)})
    db.user_sessions.insert_one({"user_id": uid_, "session_token": tok, "expires_at": datetime.now(timezone.utc) + timedelta(days=1), "created_at": datetime.now(timezone.utc)})
    h = {"Authorization": f"Bearer {tok}"}
    assert requests.get(f"{API}/auth/me", headers=h).status_code == 200
    e = requests.post(f"{API}/enquiries", headers=h, json={"property_id": S["prop"], "name": "TEST Del", "phone": "9000000001", "intent": "info", "share_phone_consent": True})
    assert e.status_code == 200
    S["enqs"].append(e.json()["id"])
    db.payment_orders.insert_one({"id": f"TESTpo_{uid_}", "user_id": uid_, "amount": 299})
    assert requests.post(f"{API}/account/delete", headers=h, json={"confirm": "nope"}).status_code == 400
    assert requests.post(f"{API}/account/delete", headers=h, json={"confirm": "DELETE"}).status_code == 200
    assert db.users.count_documents({"user_id": uid_}) == 0 and db.user_sessions.count_documents({"user_id": uid_}) == 0
    en = db.enquiries.find_one({"id": e.json()["id"]})
    assert en["user_id"] is None and en["phone"] == "" and en["name"] == "Deleted user"
    po = db.payment_orders.find_one({"id": f"TESTpo_{uid_}"})
    assert po and po["user_id"].startswith("deleted_")
    db.payment_orders.delete_one({"id": f"TESTpo_{uid_}"})
    assert requests.get(f"{API}/auth/me", headers=h).status_code == 401


# --- legal
def test_legal():
    for d in ("privacy", "terms"):
        j = requests.get(f"{API}/legal/{d}.json"); assert j.status_code == 200 and j.json()
        h = requests.get(f"{API}/legal/{d}"); assert h.status_code == 200 and "<html" in h.text.lower()
    g = requests.get(f"{API}/legal/delete-account"); assert g.status_code == 200 and "<form" in g.text.lower()
    n = db.deletion_requests.count_documents({})
    p = requests.post(f"{API}/legal/delete-account", data={"email": "test_del@example.com", "name": "TEST", "reason": "TEST"})
    assert p.status_code == 200 and db.deletion_requests.count_documents({}) == n + 1


# --- featured payments (keys not configured)
def test_featured_not_configured():
    plans = requests.get(f"{API}/featured-plans").json()
    plans = plans.get("items", plans) if isinstance(plans, dict) else plans
    assert sorted((p["price_inr"], p["duration_days"]) for p in plans) == [(299, 15), (499, 30)]
    r = requests.post(f"{API}/payments/featured/order", headers={**H("owner"), "X-LV-Client": "web"}, json={"property_id": S["prop"], "plan_id": plans[0].get("id"), "plan_slug": plans[0].get("slug")})
    assert r.status_code == 503, r.text
    assert requests.post(f"{API}/payments/razorpay/webhook", data=b"{}").status_code == 503


# --- commissions
def test_commissions():
    assert requests.get(f"{API}/admin/commissions", headers=H("owner")).status_code == 403
    body = {"property_description": "TEST_ plot deal", "payer_type": "owner", "payer_name": "TEST Payer", "rate_percent": 1,
            "calculation_method": "1% of deal", "due_terms": "on registry", "taxes_note": "GST extra", "cancellation_terms": "n/a",
            "dispute_process": "mediation", "service_description": "Listing & lead service"}
    c = requests.post(f"{API}/admin/commissions", headers=H("admin"), json=body); assert c.status_code == 200
    cid = c.json()["id"]
    st = lambda **k: requests.post(f"{API}/admin/commissions/{cid}/status", headers=H("admin"), json={"note": "TEST step", **k})
    assert st(status="approved_payable").status_code == 400
    assert st(status="agreement_accepted").status_code == 400
    assert st(status="agreement_accepted", acceptance_evidence="signed copy #1").status_code == 200
    assert st(status="deal_reported").status_code == 400
    assert st(status="deal_reported", deal_value=1000000).status_code == 200
    assert st(status="approved_payable").status_code == 200
    inv = requests.post(f"{API}/admin/commissions/{cid}/invoices", headers=H("admin"), json={"invoice_number": "TEST-1", "amount": 10000, "tax_amount": 1800})
    assert inv.status_code == 200
    pay = requests.post(f"{API}/admin/commissions/{cid}/payments", headers=H("admin"), json={"amount": 10000, "method": "UPI", "reference": "TESTref"})
    assert pay.status_code == 403
    s = requests.put(f"{API}/admin/commission/settings", headers=H("admin"), json={"default_rate_percent": 1, "legal_review_complete": False, "collection_enabled": True})
    assert s.status_code == 400


# --- SEO + sitemap (run before cleanup removes listing)
def test_seo_pages():
    r = requests.get(f"{API}/l/ujjain/{LOC_SLUG}")
    assert r.status_code == 200 and "<title>" in r.text and 'rel="canonical"' in r.text.replace("'", '"')
    assert "index,follow" in r.text and "noindex" not in r.text.split("</head>")[0]
    assert S["prop"] not in r.text  # card text shows title
    assert f"/api/l/ujjain/{LOC_SLUG}" in requests.get(f"{API}/sitemap.xml").text
    assert requests.get(f"{API}/l/ujjain/zz-unknown-x").status_code == 404
    demo = db.properties.find_one({"is_demo": True, "listing_status": "active"})
    dl = db.localities.find_one({"id": demo["locality_id"]})
    if not db.properties.find_one({"locality_id": dl["id"], "is_demo": {"$ne": True}, "listing_status": "active"}):
        d = requests.get(f"{API}/l/ujjain/{dl['slug']}").text
        assert "noindex" in d and demo["title_en"] not in d
        assert f"/api/l/ujjain/{dl['slug']}<" not in requests.get(f"{API}/sitemap.xml").text
    merged = db.localities.find_one({"merged_into": {"$ne": None, "$exists": True}})
    if merged:
        assert requests.get(f"{API}/l/ujjain/{merged['slug']}", allow_redirects=False).status_code == 301
