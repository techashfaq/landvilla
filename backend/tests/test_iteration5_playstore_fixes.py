# Iteration 5: retest of Play Store readiness fixes (buyer-safe enquiry status, deletion-request closing,
# delete-account rate limit, field-named validation errors, block → 403, featured web-only gate). Run with: pytest -n 0
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

from tests.test_iteration4_public_e2e import API, mdb, h, free_locality, upload, listing_payload

STATE = {"props": [], "emails": []}


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    if STATE["props"]:
        mdb.properties.delete_many({"id": {"$in": STATE["props"]}})
        mdb.enquiries.delete_many({"property_id": {"$in": STATE["props"]}})
        mdb.abuse_reports.delete_many({"target_id": {"$in": STATE["props"]}})
    if STATE["emails"]:
        mdb.deletion_requests.delete_many({"email": {"$in": STATE["emails"]}})


def _owner_live_listing():
    if STATE.get("pid"):
        return STATE["pid"]
    loc = free_locality() or mdb.localities.find_one({"is_active": True})
    r = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], upload("owner")), timeout=20)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    STATE["props"].append(pid)
    ap = requests.post(f"{API}/admin/listings/{pid}/approve", headers=h("admin"), json={"note": ""}, timeout=20)
    assert ap.status_code == 200, ap.text
    STATE["pid"] = pid
    return pid


def _enquire(pid, phone="9876543210"):
    r = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": phone,
                      "message": "TEST_ interested", "intent": "info", "share_phone_consent": False}, timeout=20)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# --- Buyer enquiry view: buyer-safe status
def test_buyer_enquiry_status_is_buyer_safe():
    pid = _owner_live_listing()
    eid = _enquire(pid)
    STATE["eid"] = eid
    b = requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()
    assert b["status"] == "sent" and "follow_up_at" not in b and "notes" not in b
    fu = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    up = requests.patch(f"{API}/leads/{eid}", headers=h("owner"), json={"status": "follow_up", "follow_up_at": fu, "note": "TEST_ private crm"}, timeout=20)
    assert up.status_code == 200, up.text
    b = requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()
    assert b["status"] == "sent", b["status"]
    assert "follow_up_at" not in b and "TEST_ private crm" not in str(b)
    m = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("owner"), json={"text": "TEST_ reply"}, timeout=20)
    assert m.status_code == 200
    assert requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()["status"] == "replied"
    requests.patch(f"{API}/leads/{eid}", headers=h("owner"), json={"status": "closed"}, timeout=20)
    assert requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()["status"] == "closed"
    # lister still sees CRM status
    assert requests.get(f"{API}/leads/{eid}", headers=h("owner"), timeout=20).json()["status"] == "closed"


# --- Admin closes web deletion requests
def test_admin_close_deletion_requests():
    ids = {}
    for st in ("completed", "rejected"):
        email = f"test_del5_{uuid.uuid4().hex[:6]}@example.com"
        STATE["emails"].append(email)
        assert requests.post(f"{API}/legal/delete-account", data={"email": email, "reason": "TEST_"}, timeout=20).status_code == 200
        dr = requests.get(f"{API}/admin/reports", headers=h("admin"), timeout=20).json()["deletion_requests"]
        ids[st] = [d for d in dr if d["email"] == email][0]["id"]
    rid = ids["completed"]
    assert requests.post(f"{API}/admin/deletion-requests/{rid}", headers=h("buyer"), json={"status": "completed", "note": "TEST_ ok"}, timeout=20).status_code == 403
    bad = requests.post(f"{API}/admin/deletion-requests/{rid}", headers=h("admin"), json={"status": "done", "note": "TEST_ ok"}, timeout=20)
    assert bad.status_code == 422
    short = requests.post(f"{API}/admin/deletion-requests/{rid}", headers=h("admin"), json={"status": "completed", "note": "x"}, timeout=20)
    assert short.status_code == 422 and short.json()["detail"][0]["loc"][-1] == "note"
    for st, rid in ids.items():
        r = requests.post(f"{API}/admin/deletion-requests/{rid}", headers=h("admin"), json={"status": st, "note": "TEST_ handled"}, timeout=20)
        assert r.status_code == 200 and r.json()["status"] == st, r.text
        doc = mdb.deletion_requests.find_one({"id": rid})
        assert doc["status"] == st and doc["resolution_note"] == "TEST_ handled" and doc.get("resolved_by")
        again = requests.post(f"{API}/admin/deletion-requests/{rid}", headers=h("admin"), json={"status": st, "note": "TEST_ again"}, timeout=20)
        assert again.status_code == 404
    left = [d["id"] for d in requests.get(f"{API}/admin/reports", headers=h("admin"), timeout=20).json()["deletion_requests"]]
    assert not set(ids.values()) & set(left)
    assert requests.post(f"{API}/admin/deletion-requests/delreq_nope", headers=h("admin"), json={"status": "completed", "note": "TEST_"}, timeout=20).status_code == 404


# --- Public delete-account rate limit
def test_delete_account_rate_limit_per_email():
    email = f"test_rl_{uuid.uuid4().hex[:6]}@example.com"
    STATE["emails"].append(email)
    texts = []
    for _ in range(3):
        r = requests.post(f"{API}/legal/delete-account", data={"email": email.upper()}, timeout=20)
        assert r.status_code == 200
        texts.append(r.text)
    assert "Request received" in texts[0] and "Request received" in texts[1]
    assert "Request already received" in texts[2]
    assert mdb.deletion_requests.count_documents({"email": email}) == 2
    bad = requests.post(f"{API}/legal/delete-account", data={"email": "not-an-email"}, timeout=20)
    assert bad.status_code == 400


# --- Validation errors carry field loc (frontend maps to "Note: ...")
def test_validation_error_has_field_loc():
    r = requests.post(f"{API}/admin/reports/rep_nope/resolve", headers=h("admin"), json={"action": "dismiss", "note": "x"}, timeout=20)
    assert r.status_code == 422
    d = r.json()["detail"][0]
    assert d["loc"][-1] == "note" and "at least 3" in d["msg"]


# --- Block → buyer messaging 403
def test_block_prevents_buyer_messages():
    pid = _owner_live_listing()
    eid = STATE.get("eid") or _enquire(pid, "9876500001")
    mdb.enquiries.update_one({"id": eid}, {"$set": {"status": "contacted"}})  # reopen (earlier test closed it)
    assert requests.post(f"{API}/enquiries/{eid}/block", headers=h("owner"), json={}, timeout=20).status_code == 200
    bm = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("buyer"), json={"text": "TEST_ blocked?"}, timeout=20)
    assert bm.status_code == 403 and isinstance(bm.json()["detail"], str)
    requests.delete(f"{API}/enquiries/{eid}/block", headers=h("owner"), timeout=20)
    ok = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("buyer"), json={"text": "TEST_ unblocked"}, timeout=20)
    assert ok.status_code == 200, ok.text


# --- Featured order: web-only gate
def test_featured_order_web_only():
    pid = _owner_live_listing()
    plan = requests.get(f"{API}/featured-plans", timeout=20).json()
    plan = plan if isinstance(plan, list) else plan.get("plans", plan.get("items", []))
    body = {"property_id": pid, "plan_id": plan[0]["id"]}
    r = requests.post(f"{API}/payments/featured/order", headers=h("owner"), json=body, timeout=20)
    assert r.status_code == 403 and r.json()["detail"] == "Featured purchases are available on the web only"
    r = requests.post(f"{API}/payments/featured/order", headers={**h("owner"), "X-LV-Client": "android"}, json=body, timeout=20)
    assert r.status_code == 403
    r = requests.post(f"{API}/payments/featured/order", headers={**h("owner"), "X-LV-Client": "web"}, json=body, timeout=20)
    assert r.status_code == 503, r.text
