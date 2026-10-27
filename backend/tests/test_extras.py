"""Tests: account deletion, block, commission rules, SEO thin-page rules.
Run: cd /app/backend && python -m pytest tests/test_extras.py -q -n 0
"""
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server  # noqa: E402

ADMIN = {"Authorization": "Bearer test_session_admin_landvilla"}
OWNER = {"Authorization": "Bearer test_session_owner_landvilla"}
BUYER = {"Authorization": "Bearer test_session_buyer_landvilla"}


@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        yield client


def test_commission_rules(c):
    body = {"property_description": "PYTEST deal", "payer_type": "owner", "payer_name": "Pytest Owner", "rate_percent": 1, "calculation_method": "1% of sale",
            "due_terms": "15 days", "taxes_note": "GST extra", "cancellation_terms": "none", "dispute_process": "mediation", "service_description": "Brokerage service"}
    assert c.post("/api/admin/commissions", json=body, headers=BUYER).status_code == 403
    cm = c.post("/api/admin/commissions", json=body, headers=ADMIN).json()
    cid = cm["id"]
    assert cm["commission_amount"] is None
    # cannot skip to payable without accepted agreement
    assert c.post(f"/api/admin/commissions/{cid}/status", json={"status": "approved_payable", "note": "skip"}, headers=ADMIN).status_code == 400
    # acceptance requires evidence
    assert c.post(f"/api/admin/commissions/{cid}/status", json={"status": "agreement_accepted", "note": "okay"}, headers=ADMIN).status_code == 400
    assert c.post(f"/api/admin/commissions/{cid}/status", json={"status": "agreement_accepted", "note": "okay", "acceptance_evidence": "Signed PDF ref 123"}, headers=ADMIN).status_code == 200
    assert c.post(f"/api/admin/commissions/{cid}/status", json={"status": "deal_reported", "note": "okay"}, headers=ADMIN).status_code == 400
    r = c.post(f"/api/admin/commissions/{cid}/status", json={"status": "deal_reported", "note": "okay", "deal_value": 5000000}, headers=ADMIN).json()
    assert r["commission_amount"] == 50000.0
    assert c.post(f"/api/admin/commissions/{cid}/status", json={"status": "approved_payable", "note": "reviewed"}, headers=ADMIN).status_code == 200
    assert c.post(f"/api/admin/commissions/{cid}/invoices", json={"invoice_number": "INV-1", "amount": 50000, "tax_amount": 9000}, headers=ADMIN).status_code == 200
    # collection disabled until legal review
    assert c.post(f"/api/admin/commissions/{cid}/payments", json={"amount": 59000, "method": "NEFT", "reference": "UTR1"}, headers=ADMIN).status_code == 403
    assert c.put("/api/admin/commission/settings", json={"default_rate_percent": 1, "legal_review_complete": False, "collection_enabled": True}, headers=ADMIN).status_code == 400
    full = c.get("/api/admin/commissions", headers=ADMIN).json()
    rec = next(x for x in full["items"] if x["id"] == cid)
    assert len(rec["audit"]) >= 5 and rec["status"] == "invoiced"
    c.portal.call(server.db.commission_agreements.delete_one, {"id": cid})


def test_seo_pages_exclude_demo_and_noindex_thin(c):
    html = c.get("/api/l/ujjain/nanakheda").text
    assert "(Demo)" not in html and 'content="noindex,follow"' in html
    assert c.get("/api/l/ujjain/not-a-real-place").status_code == 404
    assert "/api/l/ujjain/nanakheda" not in c.get("/api/sitemap.xml").text


def test_block_and_account_deletion(c):
    uid_ = f"user_pydel_{uuid.uuid4().hex[:6]}"
    tok = f"pytest_del_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    c.portal.call(server.db.users.insert_one, {"user_id": uid_, "email": f"{uid_}@x.dev", "name": "Del Me", "role": "buyer", "created_at": now})
    c.portal.call(server.db.user_sessions.insert_one, {"session_token": tok, "user_id": uid_, "expires_at": now + timedelta(days=1), "created_at": now})
    H = {"Authorization": f"Bearer {tok}"}
    eid = f"enq_py_{uuid.uuid4().hex[:6]}"
    c.portal.call(server.db.enquiries.insert_one, {"id": eid, "user_id": uid_, "lister_user_id": "user_testowner01", "property_id": "x", "name": "Del Me",
                                                    "phone": "9876500099", "message": "hi", "messages": [], "status": "new", "created_at": now})
    assert c.post(f"/api/enquiries/{eid}/block", headers=OWNER).status_code == 200
    assert c.post(f"/api/enquiries/{eid}/messages", json={"text": "hello"}, headers=H).status_code == 403
    assert c.post("/api/account/delete", json={"confirm": "nope"}, headers=H).status_code == 400
    assert c.post("/api/account/delete", json={"confirm": "DELETE"}, headers=H).status_code == 200
    assert c.get("/api/auth/me", headers=H).status_code == 401
    e = c.portal.call(server.db.enquiries.find_one, {"id": eid})
    assert e["phone"] == "" and e["name"] == "Deleted user" and e["user_id"] is None
    assert c.portal.call(server.db.users.find_one, {"user_id": uid_}) is None
    c.portal.call(server.db.enquiries.delete_one, {"id": eid})


def test_deletion_requires_recent_signin(c):
    uid_ = f"user_pyold_{uuid.uuid4().hex[:6]}"
    tok = f"pytest_old_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc)
    c.portal.call(server.db.users.insert_one, {"user_id": uid_, "email": f"{uid_}@x.dev", "name": "Old", "role": "buyer", "created_at": now})
    c.portal.call(server.db.user_sessions.insert_one, {"session_token": tok, "user_id": uid_, "expires_at": now + timedelta(days=1), "created_at": now - timedelta(hours=2)})
    r = c.post("/api/account/delete", json={"confirm": "DELETE"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403 and "reauth_required" in r.json()["detail"]
    assert c.portal.call(server.db.users.find_one, {"user_id": uid_}) is not None
    c.portal.call(server.db.users.delete_one, {"user_id": uid_})
    c.portal.call(server.db.user_sessions.delete_one, {"session_token": tok})


def test_test_tokens_rejected_when_disabled(c, monkeypatch):
    assert c.get("/api/auth/me", headers=ADMIN).status_code == 200
    monkeypatch.setattr(server, "SEED_TEST_SESSIONS", False)
    for h in (ADMIN, OWNER, BUYER):
        assert c.get("/api/auth/me", headers=h).status_code == 401
    assert c.get("/api/admin/listings", headers=ADMIN).status_code == 401


def test_report_rate_limit_and_validation(c):
    pid = c.get("/api/properties?limit=1").json()["items"][0]["id"]
    assert c.post(f"/api/properties/{pid}/report", json={"reason": "bogus"}, headers=BUYER).status_code == 422
    c.portal.call(server.db.abuse_reports.delete_many, {"reporter_id": "user_testbuyer01"})
    assert c.post(f"/api/properties/{pid}/report", json={"reason": "spam"}, headers=BUYER).status_code == 200
    assert c.post(f"/api/properties/{pid}/report", json={"reason": "spam"}, headers=BUYER).status_code == 409
    c.portal.call(server.db.abuse_reports.delete_many, {"reporter_id": "user_testbuyer01"})
