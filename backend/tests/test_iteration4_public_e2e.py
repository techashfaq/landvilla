# Iteration 4: public-URL E2E for owner/broker listings, moderation, leads privacy, report/block,
# account deletion, legal pages, featured (no keys), commissions, SEO. Run with: pytest -n 0
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE = (os.environ.get("EXPO_BACKEND_URL") or os.environ.get("EXPO_PUBLIC_BACKEND_URL")).rstrip("/")
API = BASE + "/api"
TOK = {r: f"test_session_{r}_landvilla" for r in ("buyer", "admin", "owner", "broker")}
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")
STATE = {"props": [], "reports": [], "comms": []}


def h(role):
    return {"Authorization": f"Bearer {TOK[role]}"}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    if STATE["props"]:
        mdb.properties.delete_many({"id": {"$in": STATE["props"]}})
        mdb.enquiries.delete_many({"property_id": {"$in": STATE["props"]}})
        mdb.abuse_reports.delete_many({"target_id": {"$in": STATE["props"]}})
    mdb.commission_agreements.delete_many({"property_description": {"$regex": "^TEST_"}})


def free_locality():
    used = mdb.properties.distinct("locality_id", {"listing_status": "active", "is_demo": {"$ne": True}})
    loc = mdb.localities.find_one({"is_active": True, "id": {"$nin": used}, "merged_into": None})
    return loc


def upload(role, kind="property_photo"):
    r = requests.post(f"{API}/uploads", headers=h(role), data={"kind": kind},
                      files={"file": ("p.png", io.BytesIO(PNG), "image/png")}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def listing_payload(loc_id, photo, posted_as="owner", title=None):
    return {"posted_as": posted_as, "title_en": title or f"TEST_ 2BHK flat {uuid.uuid4().hex[:5]}",
            "description_en": "TEST_ Spacious well-lit 2BHK apartment close to market and school.",
            "purpose": "buy", "segment": "residential", "type": "apartment", "locality_id": loc_id,
            "price": 3500000, "bhk": 2, "bathrooms": 2, "area_sqft": 1100, "furnishing": "semi-furnished",
            "amenities": [], "photo_ids": [photo], "owner_declaration_accepted": True}


# --- Legal public pages
def test_legal_pages_and_public_deletion_form():
    for d in ("privacy", "terms", "delete-account"):
        r = requests.get(f"{API}/legal/{d}", timeout=20)
        assert r.status_code == 200 and "<html" in r.text.lower(), d
    email = f"test_del_{uuid.uuid4().hex[:6]}@example.com"
    r = requests.post(f"{API}/legal/delete-account", data={"email": email, "reason": "TEST_ please delete"}, timeout=20)
    assert r.status_code == 200, r.text[:300]
    reps = requests.get(f"{API}/admin/reports", headers=h("admin"), timeout=20).json()
    blob = str(reps)
    assert email in blob, "public deletion request not visible in admin reports"


# --- Owner listing + moderation + SEO
def test_owner_listing_moderation_and_seo():
    loc = free_locality()
    assert loc, "no free locality"
    city = mdb.cities.find_one({"id": loc["city_id"]})["slug"]
    seo = f"{API}/l/{city}/{loc['slug']}"
    r = requests.get(seo, timeout=20)
    assert r.status_code == 200 and 'name="robots" content="noindex' in r.text
    assert f'rel="canonical"' in r.text
    # validation
    bad = requests.post(f"{API}/listings", headers=h("owner"), json={"posted_as": "owner"}, timeout=20)
    assert bad.status_code in (400, 422)
    photo = upload("owner")
    r = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], photo), timeout=20)
    assert r.status_code in (200, 201), r.text
    p = r.json()
    pid = p.get("id") or p.get("property", {}).get("id")
    STATE["props"].append(pid)
    mine = requests.get(f"{API}/listings/mine", headers=h("owner"), timeout=20).json()
    items = mine if isinstance(mine, list) else mine.get("items", mine.get("listings", []))
    me = [x for x in items if x["id"] == pid][0]
    assert me["listing_status"] == "pending_review"
    # not public yet
    assert requests.get(f"{API}/properties/{pid}", timeout=20).status_code == 404
    # duplicate flags
    r2 = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], photo, title=me["title_en"]), timeout=20)
    assert r2.status_code in (200, 201), r2.text
    pid2 = r2.json().get("id")
    STATE["props"].append(pid2)
    q = requests.get(f"{API}/admin/listings", headers=h("admin"), params={"status": "pending_review"}, timeout=20).json()
    qi = q if isinstance(q, list) else q.get("items", [])
    dup = [x for x in qi if x["id"] == pid2][0]
    assert dup.get("duplicate_flags") or dup.get("duplicates"), f"no duplicate flags: {list(dup.keys())}"
    # request changes needs note
    rc = requests.post(f"{API}/admin/listings/{pid2}/request-changes", headers=h("admin"), json={"note": ""}, timeout=20)
    assert rc.status_code in (400, 422)
    rc = requests.post(f"{API}/admin/listings/{pid2}/request-changes", headers=h("admin"), json={"note": "TEST_ fix photos"}, timeout=20)
    assert rc.status_code == 200, rc.text
    rj = requests.post(f"{API}/admin/listings/{pid2}/reject", headers=h("admin"), json={"note": "TEST_ duplicate"}, timeout=20)
    assert rj.status_code == 200, rj.text
    ap = requests.post(f"{API}/admin/listings/{pid}/approve", headers=h("admin"), json={"note": ""}, timeout=20)
    assert ap.status_code == 200, ap.text
    assert requests.get(f"{API}/properties/{pid}", timeout=20).status_code == 200
    s = requests.get(f"{API}/properties", params={"locality": loc["id"]}, timeout=20).json()
    assert pid in str(s), "approved listing missing in public search"
    r = requests.get(seo, timeout=20)
    assert 'content="index,follow"' in r.text
    sm = requests.get(f"{API}/sitemap.xml", timeout=20).text
    assert loc["slug"] in sm
    STATE["owner_prop"] = pid


def test_sitemap_lists_only_indexable():
    sm = requests.get(f"{API}/sitemap.xml", timeout=20).text
    used = set(mdb.properties.distinct("locality_id", {"listing_status": "active", "is_demo": {"$ne": True}}))
    for slug in re.findall(r"/api/l/[^/]+/([^<]+)</loc>", sm):
        loc = mdb.localities.find_one({"slug": slug})
        assert loc and loc["id"] in used, f"non-indexable locality in sitemap: {slug}"


# --- Broker gate
def test_broker_gate():
    lister = requests.get(f"{API}/me/lister", headers=h("broker"), timeout=20).json()
    loc = mdb.localities.find_one({"is_active": True})
    photo = upload("broker")
    bp = (lister.get("broker") or lister.get("broker_profile") or {})
    if bp.get("status") != "approved":
        r = requests.post(f"{API}/listings", headers=h("broker"), json=listing_payload(loc["id"], photo, "broker"), timeout=20)
        assert r.status_code == 403
        nodoc = requests.post(f"{API}/broker/apply", headers=h("broker"), json={"full_name": "Test Broker", "phone": "9876543210",
                              "document_ids": [], "declaration_accepted": True}, timeout=20)
        assert nodoc.status_code in (400, 422)
        doc = upload("broker", "broker_doc")
        ap = requests.post(f"{API}/broker/apply", headers=h("broker"), json={"full_name": "Test Broker", "phone": "9876543210",
                           "document_ids": [doc], "declaration_accepted": True}, timeout=20)
        assert ap.status_code in (200, 201), ap.text
        ok = requests.post(f"{API}/admin/brokers/user_testbroker01/approve", headers=h("admin"), json={"note": "ok"}, timeout=20)
        assert ok.status_code == 200, ok.text
    r = requests.post(f"{API}/listings", headers=h("broker"), json=listing_payload(loc["id"], photo, "broker"), timeout=20)
    assert r.status_code in (200, 201), r.text
    STATE["props"].append(r.json()["id"])


# --- Leads privacy, messages, block, report
def test_enquiry_consent_leads_block_report():
    pid = STATE.get("owner_prop")
    if not pid:
        pytest.skip("owner listing not created")
    e1 = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": "9876543210",
                       "message": "TEST_ interested", "intent": "info", "share_phone_consent": False}, timeout=20)
    assert e1.status_code in (200, 201), e1.text
    eid = e1.json().get("id")
    lead = requests.get(f"{API}/leads/{eid}", headers=h("owner"), timeout=20).json()
    assert lead.get("phone") in (None, ""), f"phone leaked: {lead.get('phone')}"
    assert "9876543210" not in str(lead)
    e2 = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": "9876543211",
                       "message": "TEST_ call me", "intent": "callback", "share_phone_consent": True}, timeout=20)
    if e2.status_code == 200:
        eid2 = e2.json()["id"]
        assert "9876543211" in str(requests.get(f"{API}/leads/{eid2}", headers=h("owner"), timeout=20).json())
    up = requests.patch(f"{API}/leads/{eid}", headers=h("owner"), json={"status": "contacted", "note": "TEST_ private"}, timeout=20)
    assert up.status_code == 200, up.text
    m = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("owner"), json={"text": "TEST_ hello buyer"}, timeout=20)
    assert m.status_code == 200, m.text
    th = requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()
    assert "TEST_ hello buyer" in str(th) and "TEST_ private" not in str(th), "buyer view wrong"
    # report listing
    rp = requests.post(f"{API}/properties/{pid}/report", headers=h("buyer"), json={"reason": "wrong_info", "note": "TEST_"}, timeout=20)
    assert rp.status_code in (200, 201), rp.text
    reps = requests.get(f"{API}/admin/reports", headers=h("admin"), timeout=20).json()
    items = reps if isinstance(reps, list) else reps.get("items", reps.get("reports", []))
    mine = [r for r in items if r.get("target_id") == pid and r.get("status") == "open"]
    assert mine, "report not in admin queue"
    rs = requests.post(f"{API}/admin/reports/{mine[0]['id']}/resolve", headers=h("admin"), json={"action": "dismiss", "note": "TEST_ ok"}, timeout=20)
    assert rs.status_code == 200, rs.text
    # block
    b = requests.post(f"{API}/enquiries/{eid}/block", headers=h("owner"), json={}, timeout=20)
    assert b.status_code == 200, b.text
    bm = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("buyer"), json={"text": "TEST_ blocked?"}, timeout=20)
    assert bm.status_code == 403
    requests.delete(f"{API}/enquiries/{eid}/block", headers=h("owner"), timeout=20)


# --- Account deletion with fresh user
def test_account_deletion_fresh_user():
    uid_ = f"user_TEST_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    mdb.users.insert_one({"user_id": uid_, "email": f"{uid_}@example.com", "name": "TEST Del", "role": "buyer", "created_at": now})
    old, fresh = f"tok_old_{uid_}", f"tok_new_{uid_}"
    mdb.user_sessions.insert_many([
        {"user_id": uid_, "session_token": old, "created_at": now - timedelta(hours=2), "expires_at": now + timedelta(days=1)},
        {"user_id": uid_, "session_token": fresh, "created_at": now, "expires_at": now + timedelta(days=1)}])
    r = requests.post(f"{API}/account/delete", headers={"Authorization": f"Bearer {old}"}, json={"confirm": "DELETE"}, timeout=20)
    assert r.status_code == 403 and "reauth_required" in r.text
    r = requests.post(f"{API}/account/delete", headers={"Authorization": f"Bearer {fresh}"}, json={"confirm": "nope"}, timeout=20)
    assert r.status_code == 400
    r = requests.post(f"{API}/account/delete", headers={"Authorization": f"Bearer {fresh}"}, json={"confirm": "DELETE"}, timeout=20)
    assert r.status_code == 200, r.text
    for t in (old, fresh):
        assert requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {t}"}, timeout=20).status_code == 401
    u = mdb.users.find_one({"user_id": uid_})
    assert u is None or "example.com" not in str(u.get("email", "")), "user not anonymised"


# --- Featured, no Razorpay keys
def test_featured_plans_and_order_503():
    plans = requests.get(f"{API}/featured-plans", timeout=20).json()
    s = str(plans)
    assert "299" in s and "499" in s and "15" in s and "30" in s
    items = plans if isinstance(plans, list) else plans.get("plans", plans.get("items", []))
    pid = STATE.get("owner_prop")
    if not pid:
        pytest.skip("no owner listing")
    r = requests.post(f"{API}/payments/featured/order", headers={**h("owner"), "X-LV-Client": "web"}, json={"property_id": pid, "plan_id": items[0]["id"]}, timeout=20)
    assert r.status_code == 503, r.text


# --- Commissions
def test_commission_flow():
    body = {"property_description": "TEST_ plot deal", "payer_type": "owner", "payer_name": "Test Payer", "rate_percent": 1.0,
            "calculation_method": "percent of deal", "due_terms": "on registry", "taxes_note": "GST extra",
            "cancellation_terms": "none", "dispute_process": "mediation", "service_description": "brokerage service"}
    c = requests.post(f"{API}/admin/commissions", headers=h("admin"), json=body, timeout=20)
    assert c.status_code in (200, 201), c.text
    cid = c.json()["id"]
    st = lambda **k: requests.post(f"{API}/admin/commissions/{cid}/status", headers=h("admin"), json={"note": "TEST_ step", **k}, timeout=20)
    assert st(status="agreement_accepted").status_code == 400
    assert st(status="agreement_accepted", acceptance_evidence="TEST_ signed whatsapp").status_code == 200
    assert st(status="deal_reported").status_code == 400
    assert st(status="deal_reported", deal_value=5000000).status_code == 200
    assert st(status="paid").status_code == 400
    assert st(status="approved_payable").status_code == 200
    inv = requests.post(f"{API}/admin/commissions/{cid}/invoices", headers=h("admin"), json={"invoice_number": "TEST-1", "amount": 50000, "tax_amount": 9000}, timeout=20)
    assert inv.status_code in (200, 201), inv.text
    assert requests.get(f"{API}/admin/commissions", headers=h("admin"), timeout=20).status_code == 200
    pay = requests.post(f"{API}/admin/commissions/{cid}/payments", headers=h("admin"), json={"amount": 50000, "method": "upi", "reference": "TEST_ref"}, timeout=20)
    assert pay.status_code in (403, 422)
    lst = requests.get(f"{API}/admin/commissions", headers=h("admin"), timeout=20).json()
    one = [x for x in (lst if isinstance(lst, list) else lst.get("items", [])) if x["id"] == cid][0]
    assert len(one.get("audit", [])) >= 3
