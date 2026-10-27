"""Marketplace tests: authz, broker approval gate, privacy consent, payment signature,
webhook idempotency and featured expiry. Runs in-process against the dev database and
cleans up the records it creates. Run: cd /app/backend && python -m pytest tests/test_marketplace.py -q
"""
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "pytest_webhook_secret")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "pytest_key_secret")
os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_pytest")
WEBHOOK_SECRET = os.environ["RAZORPAY_WEBHOOK_SECRET"]
KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

import server  # noqa: E402

BUYER = {"Authorization": "Bearer test_session_buyer_landvilla"}
ADMIN = {"Authorization": "Bearer test_session_admin_landvilla"}
OWNER = {"Authorization": "Bearer test_session_owner_landvilla"}
BROKER = {"Authorization": "Bearer test_session_broker_landvilla"}


@pytest.fixture(scope="module")
def c():
    with TestClient(server.app) as client:
        yield client


def run(coro):
    return server.client.get_io_loop().run_until_complete(coro) if hasattr(server.client, "get_io_loop") else None


@pytest.fixture(scope="module")
def prop(c):
    """An active, owner-posted test property inserted directly."""
    import asyncio
    pid = f"prop_pytest_{uuid.uuid4().hex[:8]}"
    async def setup():
        loc = await server.db.localities.find_one({"slug": "nanakheda"})
        city = await server.db.cities.find_one({"slug": "ujjain"})
        await server.db.properties.insert_one({"id": pid, "is_demo": False, "city_id": city["id"], "locality_id": loc["id"], "owner_user_id": "user_testowner01",
            "title_en": "PYTEST listing", "title_hi": "PYTEST", "description_en": "x" * 30, "description_hi": "x", "purpose": "buy", "segment": "residential",
            "type": "apartment", "price": 1234567, "bhk": 2, "bathrooms": 1, "area_sqft": 777, "furnishing": None, "amenities": [], "images": ["/api/files/none"],
            "listing_status": "active", "verification_status": "unverified", "featured": False, "featured_until": None, "posted_by_role": "owner",
            "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)})
    c.portal.call(setup) if hasattr(c, "portal") else asyncio.get_event_loop().run_until_complete(setup())
    yield pid
    async def teardown():
        await server.db.properties.delete_one({"id": pid})
        await server.db.enquiries.delete_many({"property_id": pid})
        await server.db.payment_orders.delete_many({"property_id": pid})
        await server.db.broker_profiles.delete_one({"user_id": "user_testbroker01"})
    c.portal.call(teardown)


def test_admin_endpoints_forbidden_for_non_admin(c):
    for path in ("/api/admin/listings", "/api/admin/brokers", "/api/admin/featured-plans", "/api/admin/payments", "/api/admin/contact-access-logs"):
        assert c.get(path, headers=BUYER).status_code == 403
        assert c.get(path).status_code == 401


def test_broker_cannot_post_until_approved(c):
    c.portal.call(server.db.broker_profiles.delete_one, {"user_id": "user_testbroker01"})
    body = {"posted_as": "broker", "title_en": "Broker flat test", "description_en": "y" * 30, "purpose": "buy", "segment": "residential",
            "type": "apartment", "locality_id": "x", "price": 100000, "bhk": 2, "area_sqft": 500, "photo_ids": ["file_x"], "owner_declaration_accepted": True}
    assert c.post("/api/listings", json=body, headers=BROKER).status_code == 403
    # pending profile still blocked
    c.portal.call(server.db.broker_profiles.insert_one, {"user_id": "user_testbroker01", "status": "pending", "document_ids": []})
    assert c.post("/api/listings", json=body, headers=BROKER).status_code == 403
    assert c.get("/api/me/lister", headers=BROKER).json()["can_post_as_broker"] is False
    # admin approves -> allowed past the broker gate (fails later on validation, not 403)
    r = c.post("/api/admin/brokers/user_testbroker01/approve", json={"note": ""}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert c.post("/api/listings", json=body, headers=BROKER).status_code == 400
    # suspend requires a reason; suspended blocked again
    assert c.post("/api/admin/brokers/user_testbroker01/suspend", json={"note": ""}, headers=ADMIN).status_code == 400
    assert c.post("/api/admin/brokers/user_testbroker01/suspend", json={"note": "pytest suspend"}, headers=ADMIN).status_code == 200
    assert c.post("/api/listings", json=body, headers=BROKER).status_code == 403


def test_phone_privacy_and_consent(c, prop):
    c.portal.call(server.db.enquiries.delete_many, {"property_id": prop})
    r = c.post("/api/enquiries", json={"property_id": prop, "name": "Pytest Buyer", "phone": "9876500011", "share_phone_consent": False}, headers=BUYER)
    assert r.status_code == 200
    eid = r.json()["id"]
    leads = c.get("/api/leads", headers=OWNER).json()["items"]
    lead = next(x for x in leads if x["id"] == eid)
    assert lead["phone"] is None and "9876500011" not in json.dumps(lead)
    detail = c.get(f"/api/leads/{eid}", headers=OWNER).json()
    assert detail["phone"] is None and detail["phone_masked"] == "98XXXXXX11"
    # other users cannot read the lead
    assert c.get(f"/api/leads/{eid}", headers=BROKER).status_code == 404
    # public listing data never carries owner id/phone
    pub = c.get(f"/api/properties/{prop}").json()
    assert "owner_user_id" not in pub
    # with consent the number is shown and access is logged
    c.portal.call(server.db.enquiries.update_one, {"id": eid}, {"$set": {"share_phone_consent": True}})
    before = c.portal.call(server.db.contact_access_logs.count_documents, {"enquiry_id": eid})
    d2 = c.get(f"/api/leads/{eid}", headers=OWNER).json()
    assert d2["phone"] == "9876500011"
    assert c.portal.call(server.db.contact_access_logs.count_documents, {"enquiry_id": eid}) == before + 1
    # in-app message from lister marks lead contacted
    assert c.post(f"/api/enquiries/{eid}/messages", json={"text": "Hello"}, headers=OWNER).status_code == 200
    assert c.get(f"/api/leads/{eid}", headers=OWNER).json()["status"] == "contacted"


def _order(c, prop, oid="order_pytest_1"):
    doc = {"id": f"pay_{uuid.uuid4().hex[:8]}", "user_id": "user_testowner01", "property_id": prop, "plan_id": "p", "plan_slug": "featured-30",
           "duration_days": 30, "amount": 29900, "currency": "INR", "razorpay_order_id": f"{oid}_{uuid.uuid4().hex[:6]}",
           "status": "created", "mode": "test", "created_at": datetime.now(timezone.utc)}
    c.portal.call(server.db.payment_orders.insert_one, dict(doc))
    return doc


def test_checkout_signature_rejected(c, prop):
    o = _order(c, prop)
    r = c.post("/api/payments/featured/verify", json={"razorpay_order_id": o["razorpay_order_id"], "razorpay_payment_id": "pay_x", "razorpay_signature": "bad"}, headers=OWNER)
    assert r.status_code == 400
    p = c.get(f"/api/properties/{prop}").json()
    assert p["featured"] is False
    # someone else's order is not found
    assert c.post("/api/payments/featured/verify", json={"razorpay_order_id": o["razorpay_order_id"], "razorpay_payment_id": "pay_x", "razorpay_signature": "bad"}, headers=BUYER).status_code == 404


def _hook(c, payload, event_id, secret=WEBHOOK_SECRET):
    raw = json.dumps(payload).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post("/api/payments/razorpay/webhook", content=raw, headers={"x-razorpay-signature": sig, "x-razorpay-event-id": event_id, "Content-Type": "application/json"})


def test_webhook_signature_idempotency_and_expiry(c, prop):
    o = _order(c, prop)
    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_pytest", "order_id": o["razorpay_order_id"], "amount": 29900, "currency": "INR"}}}}
    assert _hook(c, payload, "evt_bad", secret="wrong").status_code == 400
    ev = f"evt_{uuid.uuid4().hex[:8]}"
    assert _hook(c, payload, ev).status_code == 200
    p1 = c.portal.call(server.db.properties.find_one, {"id": prop})
    assert p1["featured"] is True
    until1 = p1["featured_until"]
    # duplicate event and a second event for the same order do not extend again
    assert _hook(c, payload, ev).json().get("duplicate") is True
    assert _hook(c, payload, f"evt_{uuid.uuid4().hex[:8]}").status_code == 200
    p2 = c.portal.call(server.db.properties.find_one, {"id": prop})
    assert p2["featured_until"] == until1
    # wrong amount never activates
    o2 = _order(c, prop)
    bad = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_p2", "order_id": o2["razorpay_order_id"], "amount": 100, "currency": "INR"}}}}
    _hook(c, bad, f"evt_{uuid.uuid4().hex[:8]}")
    assert c.portal.call(server.db.payment_orders.find_one, {"id": o2["id"]})["status"] == "created"
    # expiry: past featured_until is cleared on next search
    c.portal.call(server.db.properties.update_one, {"id": prop}, {"$set": {"featured_until": datetime.now(timezone.utc) - timedelta(minutes=1)}})
    c.get("/api/properties?limit=1")
    assert c.portal.call(server.db.properties.find_one, {"id": prop})["featured"] is False
