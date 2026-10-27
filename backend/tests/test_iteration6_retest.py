# Iteration 6: retest of iteration-4 minor fixes (block state in GET lead/enquiry, buyer message reopens closed lead,
# public delete-account per-email + per-IP limits). Run with: pytest -n 0
import uuid

import pytest
import requests

from tests.test_iteration4_public_e2e import API, mdb, h, free_locality, upload, listing_payload

STATE = {"props": [], "emails": [], "eid": None}
BUYER, OWNER = "user_testbuyer01", "user_testowner01"


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    mdb.blocks.delete_many({"blocker_id": {"$in": [BUYER, OWNER]}, "blocked_id": {"$in": [BUYER, OWNER]}})
    if STATE["props"]:
        mdb.properties.delete_many({"id": {"$in": STATE["props"]}})
        mdb.enquiries.delete_many({"property_id": {"$in": STATE["props"]}})
    if STATE["emails"]:
        mdb.deletion_requests.delete_many({"email": {"$in": STATE["emails"]}})


def _enquiry():
    if STATE["eid"]:
        return STATE["eid"]
    loc = free_locality() or mdb.localities.find_one({"is_active": True})
    r = requests.post(f"{API}/listings", headers=h("owner"), json=listing_payload(loc["id"], upload("owner")), timeout=20)
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    STATE["props"].append(pid)
    assert requests.post(f"{API}/admin/listings/{pid}/approve", headers=h("admin"), json={"note": ""}, timeout=20).status_code == 200
    e = requests.post(f"{API}/enquiries", headers=h("buyer"), json={"property_id": pid, "name": "Test Buyer", "phone": "9876500006",
                      "message": "TEST_ iter6", "intent": "info", "share_phone_consent": False}, timeout=20)
    assert e.status_code in (200, 201), e.text
    STATE["eid"] = e.json()["id"]
    return STATE["eid"]


def _state(eid):
    lead = requests.get(f"{API}/leads/{eid}", headers=h("owner"), timeout=20).json()
    enq = requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()
    return (lead["blocked_by_me"], lead["messaging_blocked"]), (enq["blocked_by_me"], enq["messaging_blocked"])


# --- Block state exposed on GET lead / enquiry
def test_block_state_initially_false():
    eid = _enquiry()
    assert _state(eid) == ((False, False), (False, False))


def test_owner_blocks_buyer_state():
    eid = _enquiry()
    assert requests.post(f"{API}/enquiries/{eid}/block", headers=h("owner"), json={}, timeout=20).status_code == 200
    assert _state(eid) == ((True, True), (False, True))
    assert requests.post(f"{API}/enquiries/{eid}/messages", headers=h("buyer"), json={"text": "TEST_ x"}, timeout=20).status_code == 403
    assert requests.delete(f"{API}/enquiries/{eid}/block", headers=h("owner"), timeout=20).status_code == 200
    assert _state(eid) == ((False, False), (False, False))


def test_buyer_blocks_owner_state():
    eid = _enquiry()
    assert requests.post(f"{API}/enquiries/{eid}/block", headers=h("buyer"), json={}, timeout=20).status_code == 200
    assert _state(eid) == ((False, True), (True, True))
    assert requests.post(f"{API}/enquiries/{eid}/messages", headers=h("owner"), json={"text": "TEST_ x"}, timeout=20).status_code == 403
    assert requests.delete(f"{API}/enquiries/{eid}/block", headers=h("buyer"), timeout=20).status_code == 200
    assert _state(eid) == ((False, False), (False, False))


# --- Buyer message on a closed lead reopens it
def test_buyer_message_reopens_closed_lead():
    eid = _enquiry()
    assert requests.patch(f"{API}/leads/{eid}", headers=h("owner"), json={"status": "closed"}, timeout=20).status_code == 200
    assert requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()["status"] == "closed"
    m = requests.post(f"{API}/enquiries/{eid}/messages", headers=h("buyer"), json={"text": "TEST_ still interested"}, timeout=20)
    assert m.status_code == 200, m.text
    assert requests.get(f"{API}/leads/{eid}", headers=h("owner"), timeout=20).json()["status"] == "new"
    new_ids = [x["id"] for x in requests.get(f"{API}/leads", headers=h("owner"), params={"status": "new"}, timeout=20).json()["items"]]
    assert eid in new_ids
    assert requests.get(f"{API}/enquiries/{eid}", headers=h("buyer"), timeout=20).json()["status"] in ("sent", "replied")


def test_lister_message_on_closed_lead_keeps_closed():
    eid = _enquiry()
    requests.patch(f"{API}/leads/{eid}", headers=h("owner"), json={"status": "closed"}, timeout=20)
    assert requests.post(f"{API}/enquiries/{eid}/messages", headers=h("owner"), json={"text": "TEST_ bye"}, timeout=20).status_code == 200
    assert requests.get(f"{API}/leads/{eid}", headers=h("owner"), timeout=20).json()["status"] == "closed"


# --- Public delete-account rate limits (unique X-Forwarded-For per test so suite runs don't share the IP quota)
def _post(email, ip):
    STATE["emails"].append(email.lower())
    return requests.post(f"{API}/legal/delete-account", data={"email": email}, headers={"X-Forwarded-For": ip}, timeout=20)


def _ip():
    return f"10.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}"


def test_delete_account_per_email_limit():
    email, ip = f"test_del6_{uuid.uuid4().hex[:6]}@example.com", _ip()
    t = [_post(email, ip).text for _ in range(3)]
    assert "Request received" in t[0] and "Request received" in t[1] and "Request already received" in t[2]
    # different IP doesn't bypass per-email limit
    assert "Request already received" in _post(email.upper(), _ip()).text
    assert mdb.deletion_requests.count_documents({"email": email}) == 2


def test_delete_account_per_ip_limit_5_per_hour_no_global_cap():
    ip = _ip()
    res = [_post(f"test_del6ip_{uuid.uuid4().hex[:6]}@example.com", ip).text for _ in range(6)]
    assert all("Request received" in r for r in res[:5]), res
    assert "Request already received" in res[5]
    assert mdb.deletion_requests.count_documents({"ip": ip}) == 5
    # another IP is still accepted (no global cap)
    assert "Request received" in _post(f"test_del6ip_{uuid.uuid4().hex[:6]}@example.com", _ip()).text
