"""Offline tests: no Atlas, no providers, no actual environment file loading.

Run from backend: python -m unittest discover -s tests/unit -v
"""
import asyncio
import copy
import hashlib
import hmac
import json
import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.update(MONGO_URL="mongodb://127.0.0.1:27017", DB_NAME="landvilla_unit",
                  PYTHON_DOTENV_DISABLED="1", SEED_ON_STARTUP="false", SEED_DEMO_LISTINGS="true",
                  SEED_TEST_SESSIONS="false", APP_ENV="development", IDENTITY_ENABLED="true",
                  OTP_HMAC_SECRET="unit-tests-only-not-a-real-secret-0123456789")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import httpx
import mongomock
from pydantic import ValidationError
import server
import marketplace
import identity
import browser_sessions
import extras
import seed


class Cursor:
    def __init__(self, cursor): self.cursor = cursor
    def sort(self, *args): self.cursor = self.cursor.sort(*args); return self
    def skip(self, n): self.cursor = self.cursor.skip(n); return self
    def limit(self, n): self.cursor = self.cursor.limit(n); return self
    async def to_list(self, n): return list(self.cursor)[:n]
    def __aiter__(self): return self
    async def __anext__(self):
        try: return next(self.cursor)
        except StopIteration: raise StopAsyncIteration


class Collection:
    def __init__(self, coll): self.coll = coll
    def find(self, *args, **kwargs): return Cursor(self.coll.find(*args, **kwargs))
    def aggregate(self, *args, **kwargs): return Cursor(iter(self.coll.aggregate(*args, **kwargs)))
    def __getattr__(self, name):
        async def call(*args, **kwargs):
            kwargs.pop("session", None)
            return getattr(self.coll, name)(*args, **kwargs)
        return call


class MemoryDB:
    def __init__(self): self.raw = mongomock.MongoClient(tz_aware=True).db
    def __getitem__(self, name): return Collection(self.raw[name])
    def __getattr__(self, name): return self[name]


class Regressions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from mongo_type_fixture import install_type_operator
        install_type_operator(self)
        self.db = MemoryDB()
        self.patches = [patch.object(module, "db", self.db) for module in (server, marketplace, identity, extras, browser_sessions)]
        for p in self.patches: p.start()
        self.api = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
        await seed.seed_all(self.db, include_demo=True)
        # Explicit isolated fixture setup; ordinary seeding must not enable identity.
        await seed.m002_identity_indexes(self.db)
        await self.db.schema_migrations.insert_one({"version": "002_identity_indexes", "applied_at": server.now()})
        self.user = {"user_id": "owner", "email": "owner@example.com", "email_verified": True, "role": "buyer", "account_status": "active"}
        await self.db.users.insert_one(self.user)
        await self.db.user_sessions.insert_one({"session_token": "owner-token", "user_id": "owner", "created_at": server.now(), "expires_at": server.now() + timedelta(days=1)})
        self.headers = {"Authorization": "Bearer owner-token"}

    async def asyncTearDown(self):
        await self.api.aclose()
        for p in reversed(self.patches): p.stop()

    async def test_startup_database_failure_is_sanitized_and_never_seeds(self):
        from pymongo.errors import ServerSelectionTimeoutError
        ping = AsyncMock(side_effect=ServerSelectionTimeoutError("TLS handshake failed private-host private-secret"))
        with patch.object(self.db, "command", ping, create=True), patch.object(server, "seed_all", new_callable=AsyncMock) as seed_call:
            with self.assertRaisesRegex(RuntimeError, "tls_handshake_failed") as caught:
                await server.startup()
            self.assertNotIn("private-", str(caught.exception))
            ping.assert_awaited_once_with("ping")
            seed_call.assert_not_awaited()

    async def test_startup_success_requires_ping_without_implicit_seeding(self):
        ping = AsyncMock(return_value={"ok": 1})
        with patch.object(self.db, "command", ping, create=True), patch.dict(os.environ, {"IDENTITY_ENABLED": "false", "SEED_ON_STARTUP": "false"}), patch.object(server, "seed_all", new_callable=AsyncMock) as seed_call:
            await server.startup()
            ping.assert_awaited_once_with("ping")
            seed_call.assert_not_awaited()

    async def test_seed_duplicates_hidden_records_and_api(self):
        await self.db.properties.update_many({"is_demo": True}, {"$set": {"listing_status": "demo_hidden"}})
        report = await seed.seed_all(self.db, include_demo=True)
        self.assertEqual(report["skipped_duplicates"]["demo_listings"], 20)
        self.assertEqual(report["inserted"]["demo_listings"], 0)
        self.assertEqual(report["demo_inventory"]["legacy_hidden"], 20)
        for query, total in [("limit=5", 20), ("purpose=buy&limit=5", 12), ("purpose=rent&limit=5", 8), ("page=2&limit=5", 20)]:
            result = await self.api.get("/api/properties?" + query)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["total"], total)
            self.assertEqual(len(result.json()["items"]), 5)
            self.assertTrue(all(p["is_demo"] for p in result.json()["items"]))
        pid = result.json()["items"][0]["id"]
        detail = await self.api.get("/api/properties/" + pid)
        self.assertIn("FICTIONAL", detail.json()["description_en"])
        self.assertTrue(detail.json()["images"][0].startswith("https://"))
        self.assertEqual(await self.db.properties.count_documents({"listing_status": "demo_hidden"}), 20)

    async def test_demo_disabled_search_detail_and_saved(self):
        pid = self.db.raw.properties.find_one()["id"]
        with patch.object(server, "SEED_DEMO", False):
            self.assertEqual((await self.api.get("/api/properties")).json()["total"], 0)
            self.assertEqual((await self.api.get("/api/properties/" + pid)).status_code, 404)
            self.assertEqual((await self.api.post("/api/saved/" + pid, headers=self.headers)).status_code, 404)

    async def test_search_text_does_not_override_visibility(self):
        await self.db.properties.update_many({}, {"$set": {"listing_status": "rejected"}})
        self.assertEqual((await self.api.get("/api/properties?q=house")).json()["total"], 0)

    async def test_invalid_pagination(self):
        self.assertEqual((await self.api.get("/api/properties?limit=0")).status_code, 422)

    async def test_suspended_private_file_query_token_rejected(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"suspended": True}})
        await self.db.files.insert_one({"id": "doc", "owner_id": "owner", "is_public": False, "is_deleted": False})
        self.assertEqual((await self.api.get("/api/files/doc?token=owner-token")).status_code, 403)

    async def test_disabled_test_token_private_file_rejected(self):
        await self.db.user_sessions.insert_one({"session_token": "test_session_unit", "user_id": "owner", "expires_at": server.now() + timedelta(days=1)})
        self.assertIsNone(await server.user_for_token("test_session_unit"))

    async def test_expired_session(self):
        await self.db.user_sessions.update_one({}, {"$set": {"expires_at": server.now() - timedelta(seconds=1)}})
        self.assertEqual((await self.api.get("/api/auth/me", headers=self.headers)).status_code, 401)

    async def test_hashed_session_and_logout(self):
        result = await identity.issue_session(self.user)
        token = result["session_token"]
        self.assertIsNone(await self.db.user_sessions.find_one({"session_token": token}))
        headers = {"Authorization": "Bearer " + token}
        self.assertEqual((await self.api.get("/api/auth/me", headers=headers)).status_code, 200)
        self.assertEqual((await self.api.post("/api/auth/logout", headers=headers)).status_code, 200)
        self.assertEqual((await self.api.get("/api/auth/me", headers=headers)).status_code, 401)

    async def test_profile_mass_assignment(self):
        result = await self.api.patch("/api/me/profile", headers=self.headers, json={"first_name": "A", "last_name": "B", "role": "admin"})
        self.assertEqual(result.status_code, 422)
        self.assertEqual((await self.db.users.find_one({"user_id": "owner"}))["role"], "buyer")

    async def test_profile_persists(self):
        result = await self.api.patch("/api/me/profile", headers=self.headers, json={"first_name": "First", "last_name": "Last", "preferred_location": "Ujjain"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual((await self.api.get("/api/me/profile", headers=self.headers)).json()["preferred_location"], "Ujjain")

    async def request_code(self, purpose="login", identifier="owner@example.com", registration=None, headers=None):
        body = {"purpose": purpose, "identifier": identifier}
        if registration: body["registration"] = registration
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", new_callable=AsyncMock) as delivery:
            result = await self.api.post("/api/auth/otp/request", json=body, headers=headers)
            code = delivery.await_args.args[2] if delivery.await_count else None
            return result, code

    async def test_otp_success_single_use(self):
        response, code = await self.request_code()
        body = {"challenge_id": response.json()["challenge_id"], "code": code}
        row = await self.db.otp_challenges.find_one({})
        self.assertNotEqual(row["verifier"], code)
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body)).status_code, 200)
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body)).status_code, 400)

    async def test_missing_actual_index_despite_marker(self):
        self.db.raw.users.drop_index("mobile_1")
        self.assertEqual((await self.request_code())[0].status_code, 503)

    async def test_provider_failure_never_enables_challenge(self):
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", side_effect=server.HTTPException(503, "Delivery unavailable")):
            response = await self.api.post("/api/auth/otp/request", json={"identifier": "owner@example.com"})
        self.assertEqual(response.status_code, 503)
        row = await self.db.otp_challenges.find_one({})
        self.assertTrue(row["used"])
        self.assertFalse(row["delivered"])

    async def test_smtp_requires_tls_and_rejects_transport_failure(self):
        env = {"SMTP_HOST": "smtp.example.test", "SMTP_FROM": "sender@example.test", "SMTP_PORT": "587", "SMTP_USERNAME": "unit", "SMTP_PASSWORD": "unit"}
        with patch.dict(os.environ, env), patch("identity.smtplib.SMTP") as smtp:
            identity.provider_ready("email")
            identity.smtp_send("owned@example.test", "unit-only")
            connection = smtp.return_value.__enter__.return_value
            connection.starttls.assert_called_once()
            connection.login.assert_called_once()
            connection.send_message.assert_called_once()
            connection.starttls.side_effect = OSError("transport failure")
            with self.assertRaises(server.HTTPException) as error:
                await identity.deliver("email", "owned@example.test", "unit-only")
            self.assertEqual(error.exception.status_code, 503)
        with patch.dict(os.environ, {**env, "SMTP_PORT": "invalid"}):
            with self.assertRaises(server.HTTPException): identity.provider_ready("email")

    async def test_identifier_throttle_and_normalization(self):
        response, _ = await self.request_code(identifier=" OWNER@EXAMPLE.COM ")
        self.assertEqual(response.status_code, 200)
        for _ in range(4):
            await self.db.otp_challenges.update_many({}, {"$set": {"resend_at": server.now() - timedelta(seconds=1)}})
            self.assertEqual((await self.request_code())[0].status_code, 200)
        self.assertEqual((await self.request_code())[0].status_code, 429)

    async def test_profile_security_metadata_not_exposed(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"google_sub": "private-subject", "password_digest": "private-digest"}})
        response = await self.api.get("/api/me/profile", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        for field in ("google_sub", "password_digest", "_session_created_at"):
            self.assertNotIn(field, response.json())
        for field in ("suspended", "email_verified", "account_status", "user_id", "email", "mobile"):
            response = await self.api.patch("/api/me/profile", headers=self.headers,
                json={"first_name": "First", "last_name": "Last", field: "unauthorized"})
            self.assertEqual(response.status_code, 422)

    async def test_delivery_in_flight_cannot_verify(self):
        entered, finish = asyncio.Event(), asyncio.Event()
        captured = []
        async def delivery(channel, identifier, code):
            captured.append(code); entered.set(); await finish.wait()
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", side_effect=delivery):
            pending = asyncio.create_task(self.api.post("/api/auth/otp/request", json={"identifier": "owner@example.com"}))
            await entered.wait()
            row = await self.db.otp_challenges.find_one({})
            response = await self.api.post("/api/auth/otp/verify", json={"challenge_id": row["challenge_id"], "code": captured[0]})
            finish.set(); await pending
        self.assertEqual(response.status_code, 400)

    async def test_concurrent_otp_verification_single_session(self):
        response, code = await self.request_code()
        body = {"challenge_id": response.json()["challenge_id"], "code": code}
        results = await asyncio.gather(*(self.api.post("/api/auth/otp/verify", json=body) for _ in range(8)))
        self.assertEqual(sorted(r.status_code for r in results), [200] + [400] * 7)
        self.assertEqual(await self.db.user_sessions.count_documents({}), 2)

    async def test_concurrent_resend_delivers_once(self):
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", new_callable=AsyncMock) as delivery:
            results = await asyncio.gather(*(self.api.post("/api/auth/otp/request", json={"identifier": "owner@example.com"}) for _ in range(4)))
        self.assertEqual(sorted(r.status_code for r in results), [200, 429, 429, 429])
        self.assertEqual(delivery.await_count, 1)

    async def test_contact_recent_auth_rechecked_on_verify(self):
        response, code = await self.request_code("contact", "+919876543210", headers=self.headers)
        await self.db.user_sessions.update_one({}, {"$set": {"created_at": server.now() - timedelta(minutes=16)}})
        result = await self.api.post("/api/auth/otp/verify", headers=self.headers,
            json={"challenge_id": response.json()["challenge_id"], "code": code})
        self.assertEqual(result.status_code, 403)
        self.assertNotIn("mobile", await self.db.users.find_one({"user_id": "owner"}))

    async def test_identity_database_outage_sanitized(self):
        from pymongo.errors import ServerSelectionTimeoutError
        with patch.object(identity, "missing_identity_indexes", side_effect=ServerSelectionTimeoutError("private diagnostic")):
            result = await self.api.post("/api/auth/google", json={"id_token": "invalid-credential-value"})
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("private diagnostic", result.text)

    async def test_google_existing_email_never_automatically_links(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"email": "owner@gmail.com"}})
        claims = {"sub": "google-unit", "email": "owner@gmail.com", "email_verified": True}
        with patch.object(identity, "verify_google", return_value=claims):
            result = await self.api.post("/api/auth/google", json={"id_token": "mock-credential-for-unit-test"})
        self.assertEqual(result.status_code, 409)
        self.assertNotIn("google_sub", await self.db.users.find_one({"user_id": "owner"}))

    async def test_google_explicit_link_and_subject_login(self):
        claims = {"sub": "google-unit", "email": self.user["email"], "email_verified": True}
        with patch.object(identity, "verify_google", return_value=claims):
            result = await self.api.post("/api/auth/google/link", headers=self.headers, json={"id_token": "mock-credential-for-unit-test"})
            self.assertEqual(result.status_code, 200)
            result = await self.api.post("/api/auth/google", json={"id_token": "mock-credential-for-unit-test"})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["user"]["user_id"], "owner")

    async def test_google_link_conflict_and_recent_auth(self):
        await self.db.users.insert_one({"user_id": "other", "email": "other@example.com", "google_sub": "taken"})
        with patch.object(identity, "verify_google", return_value={"sub": "taken", "email": self.user["email"]}):
            result = await self.api.post("/api/auth/google/link", headers=self.headers, json={"id_token": "mock-credential-for-unit-test"})
            self.assertEqual(result.status_code, 409)
            await self.db.user_sessions.update_one({}, {"$set": {"created_at": server.now() - timedelta(minutes=16)}})
            result = await self.api.post("/api/auth/google/link", headers=self.headers, json={"id_token": "mock-credential-for-unit-test"})
            self.assertEqual(result.status_code, 403)

    async def test_managed_google_cannot_take_over_independent_account(self):
        class Provider:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def get(self, *args, **kwargs):
                return httpx.Response(200, json={"email": "owner@example.com", "session_token": "mock-provider-token"})
        with patch.object(server.httpx, "AsyncClient", return_value=Provider()):
            response = await self.api.post("/api/auth/session", json={"session_id": "mock-provider-session"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(await self.db.user_sessions.count_documents({}), 1)

    async def test_validation_does_not_echo_authentication_inputs(self):
        response = await self.api.post("/api/auth/otp/verify", json={"challenge_id": "short-private-id", "code": "private-invalid-code"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-invalid-code", response.text)
        self.assertNotIn("short-private-id", response.text)
        response = await self.api.post("/api/auth/google", json={"id_token": "private-token"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("private-token", response.text)

    async def test_otp_attempt_limit(self):
        response, code = await self.request_code()
        body = {"challenge_id": response.json()["challenge_id"], "code": "999999" if code != "999999" else "888888"}
        for _ in range(5): self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body)).status_code, 400)
        body["code"] = code
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body)).status_code, 400)

    async def test_otp_expired(self):
        response, code = await self.request_code()
        await self.db.otp_challenges.update_one({}, {"$set": {"expires_at": server.now() - timedelta(seconds=1)}})
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json={"challenge_id": response.json()["challenge_id"], "code": code})).status_code, 400)

    async def test_resend_cooldown_and_invalidation(self):
        first, code = await self.request_code()
        self.assertEqual((await self.request_code())[0].status_code, 429)
        await self.db.otp_challenges.update_one({}, {"$set": {"resend_at": server.now() - timedelta(seconds=1)}})
        second, _ = await self.request_code()
        self.assertEqual(second.status_code, 200)
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json={"challenge_id": first.json()["challenge_id"], "code": code})).status_code, 400)

    async def test_unknown_login_no_delivery(self):
        response, code = await self.request_code(identifier="unknown@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(code)

    async def test_registration_and_admin_rejection(self):
        profile = {"first_name": "Buyer", "last_name": "Test", "email": "new@example.com", "mobile": "+919876543210", "account_role": "owner", "accept_terms": True, "accept_privacy": True}
        with self.assertRaises(ValidationError): identity.Registration(**{**profile, "account_role": "admin"})
        response, code = await self.request_code("register", "new@example.com", profile)
        self.assertEqual(await self.db.users.count_documents({"email": "new@example.com"}), 0)
        response = await self.api.post("/api/auth/otp/verify", json={"challenge_id": response.json()["challenge_id"], "code": code})
        self.assertEqual(response.status_code, 200)
        user = await self.db.users.find_one({"email": "new@example.com"})
        self.assertEqual(user["role"], "buyer"); self.assertTrue(user["email_verified"]); self.assertFalse(user["mobile_verified"])

    async def test_invalid_registration_fields(self):
        for field, value in [("email", "invalid"), ("mobile", "123"), ("accept_terms", False), ("first_name", " ")]:
            profile = {"first_name": "First", "last_name": "Last", "email": "new@example.com", "mobile": "+919876543210", "account_role": "buyer", "accept_terms": True, "accept_privacy": True}
            with self.assertRaises(ValidationError): identity.Registration(**{**profile, field: value})

    async def test_contact_requires_same_user(self):
        response, code = await self.request_code("contact", "+919876543210", headers=self.headers)
        body = {"challenge_id": response.json()["challenge_id"], "code": code}
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body)).status_code, 401)
        self.assertEqual((await self.api.post("/api/auth/otp/verify", json=body, headers=self.headers)).status_code, 200)
        self.assertTrue((await self.db.users.find_one({"user_id": "owner"}))["mobile_verified"])

    async def test_upload_unauthorized_and_invalid_content(self):
        self.assertEqual((await self.api.post("/api/uploads", data={"kind": "property_photo"}, files={"file": ("bad.png", b"fake", "image/png")})).status_code, 401)
        self.assertEqual((await self.api.post("/api/uploads", headers=self.headers, data={"kind": "property_photo"}, files={"file": ("bad.png", b"fake", "image/png")})).status_code, 400)

    async def test_listing_ownership_and_pagination(self):
        self.assertEqual((await self.api.get("/api/listings/not-owned/edit", headers=self.headers)).status_code, 404)
        result = await self.api.get("/api/listings/mine?limit=1", headers=self.headers)
        self.assertEqual(result.status_code, 200); self.assertEqual(result.json()["total"], 0)
        self.assertEqual((await self.api.post("/api/admin/listings/example/approve", headers=self.headers, json={"note": ""})).status_code, 403)

    async def test_webhook_invalid_signature_and_authorized_not_fulfilled(self):
        await self.db.payment_orders.insert_one({"id": "order", "razorpay_order_id": "rzp-order", "amount": 100, "status": "created"})
        raw = json.dumps({"event": "payment.authorized", "payload": {"payment": {"entity": {"id": "pay", "order_id": "rzp-order", "status": "authorized", "amount": 100, "currency": "INR"}}}}).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": "unit-webhook"}), patch.object(marketplace, "fulfil", new_callable=AsyncMock) as fulfil:
            self.assertEqual((await self.api.post("/api/payments/razorpay/webhook", content=raw)).status_code, 400)
            signature = hmac.new(b"unit-webhook", raw, hashlib.sha256).hexdigest()
            response = await self.api.post("/api/payments/razorpay/webhook", content=raw, headers={"x-razorpay-signature": signature})
            self.assertEqual(response.status_code, 200); fulfil.assert_not_awaited()

    async def test_webhook_retry_and_deduplication(self):
        await self.db.payment_orders.insert_one({"id": "order", "razorpay_order_id": "rzp-order", "amount": 100, "status": "created"})
        raw = json.dumps({"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay", "order_id": "rzp-order", "status": "captured", "amount": 100, "currency": "INR"}}}}).encode()
        signature = hmac.new(b"unit-webhook", raw, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": "unit-webhook"}), patch.object(marketplace, "fulfil", new_callable=AsyncMock) as fulfil:
            fulfil.side_effect = RuntimeError("simulated processing failure")
            with self.assertRaises(RuntimeError): await self.api.post("/api/payments/razorpay/webhook", content=raw, headers={"x-razorpay-signature": signature})
            self.assertEqual(await self.db.payment_webhook_events.count_documents({"processed": True}), 0)
            fulfil.side_effect = None; fulfil.return_value = {}
            for _ in range(2): self.assertEqual((await self.api.post("/api/payments/razorpay/webhook", content=raw, headers={"x-razorpay-signature": signature})).status_code, 200)
            self.assertEqual(fulfil.await_count, 2)

    async def test_google_missing_configuration(self):
        with patch.dict(os.environ, {"GOOGLE_CLIENT_IDS": ""}):
            self.assertEqual((await self.api.post("/api/auth/google", json={"id_token": "invalid-credential-value"})).status_code, 503)

    async def test_live_payments_disabled(self):
        with patch.dict(os.environ, {"RAZORPAY_KEY_ID": "rzp_live_unit", "RAZORPAY_KEY_SECRET": "unit", "ALLOW_LIVE_PAYMENTS": "false"}):
            with self.assertRaises(server.HTTPException) as error: marketplace.rzp_keys()
            self.assertEqual(error.exception.status_code, 503)

    async def test_session_hash_cannot_be_replayed(self):
        result = await identity.issue_session(self.user)
        stored = "sha256:" + hashlib.sha256(result["session_token"].encode()).hexdigest()
        self.assertIsNone(await server.user_for_token(stored))

    async def test_otp_provider_missing(self):
        with patch.dict(os.environ, {"SMTP_HOST": "", "SMTP_PASSWORD": ""}):
            self.assertEqual((await self.api.post("/api/auth/otp/request", json={"identifier": "owner@example.com"})).status_code, 503)

    async def test_otp_requires_indexes(self):
        self.db.raw.schema_migrations.delete_one({"version": "002_identity_indexes"})
        self.assertEqual((await self.api.post("/api/auth/otp/request", json={"identifier": "owner@example.com"})).status_code, 503)

    async def test_duplicate_registration_does_not_deliver(self):
        profile = {"first_name": "First", "last_name": "Last", "email": "owner@example.com", "mobile": "+919876543210", "account_role": "buyer", "accept_terms": True, "accept_privacy": True}
        response, code = await self.request_code("register", "owner@example.com", profile)
        self.assertEqual(response.status_code, 200); self.assertIsNone(code)

    async def test_google_cryptographic_validation(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from google.auth import jwt, crypt
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "unit-test")])
        cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(1).not_valid_before(server.now() - timedelta(minutes=1)).not_valid_after(server.now() + timedelta(days=1)).sign(key, hashes.SHA256())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        signer = crypt.RSASigner.from_string(pem, key_id="unit")
        timestamp = int(server.now().timestamp())
        claims = {"iss": "https://accounts.google.com", "aud": "unit-client", "sub": "google-unit", "email": "unit@gmail.com", "email_verified": True, "iat": timestamp, "exp": timestamp + 300}
        certificates = {"unit": cert.public_bytes(serialization.Encoding.PEM).decode()}
        with patch.dict(os.environ, {"GOOGLE_CLIENT_IDS": "unit-client"}), patch("google.oauth2.id_token._fetch_certs", return_value=certificates):
            self.assertEqual(identity.verify_google(jwt.encode(signer, claims).decode())["sub"], "google-unit")
            for changed in [{"aud": "wrong"}, {"iss": "https://attacker.invalid"}, {"exp": timestamp - 300}, {"email_verified": False}, {"email_verified": "true"}, {"email": "invalid"}, {"sub": ""}]:
                with self.assertRaises(server.HTTPException) as error:
                    identity.verify_google(jwt.encode(signer, {**claims, **changed}).decode())
                self.assertEqual(error.exception.status_code, 401)
            token = jwt.encode(signer, claims).decode()
            with self.assertRaises(server.HTTPException): identity.verify_google(token[:-20] + "A" * 20)

    async def test_google_transport_failure_sanitized_and_session_preserved(self):
        from google.auth.exceptions import TransportError
        with patch.dict(os.environ, {"GOOGLE_CLIENT_IDS": "unit-client"}), patch("google.oauth2.id_token.verify_oauth2_token", side_effect=TransportError("sensitive-provider-diagnostic")):
            response = await self.api.post("/api/auth/google/link", headers=self.headers, json={"id_token": "mock-credential-for-unit-test"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sensitive-provider-diagnostic", response.text)
        self.assertEqual((await self.api.get("/api/auth/me", headers=self.headers)).status_code, 200)

    async def test_invalid_link_credential_does_not_invalidate_session(self):
        with patch.object(identity, "verify_google", side_effect=server.HTTPException(401, "private-detail")):
            response = await self.api.post("/api/auth/google/link", headers=self.headers, json={"id_token": "mock-credential-for-unit-test"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("private-detail", response.text)
        self.assertEqual((await self.api.get("/api/auth/me", headers=self.headers)).status_code, 200)

    async def test_cookie_credentials_are_not_accepted_by_bearer_api(self):
        headers = {"Cookie": "auth_token=owner-token; session=owner-token", "Origin": "https://attacker.invalid"}
        response = await self.api.patch("/api/me/profile", headers=headers, json={"first_name": "Attacker", "last_name": "Change"})
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual((await self.db.users.find_one({"user_id": "owner"})).get("first_name"), "Attacker")
        await self.api.post("/api/auth/logout", headers=headers)
        self.assertEqual((await self.api.get("/api/auth/me", headers=self.headers)).status_code, 200)

    async def test_auth_and_profile_responses_cannot_be_cached(self):
        for response in [await self.api.get("/api/auth/me", headers=self.headers),
                         await self.api.get("/api/me/profile", headers=self.headers),
                         await self.api.get("/api/auth/me")]:
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertNotIn("set-cookie", response.headers)

    async def test_twilio_configuration_validation_and_delivery_failure(self):
        env = {"TWILIO_ACCOUNT_SID": "AC" + "a" * 32, "TWILIO_AUTH_TOKEN": "unit-only", "TWILIO_FROM": "+919876543210"}
        with patch.dict(os.environ, env):
            identity.provider_ready("mobile")
            with patch.object(identity.httpx, "AsyncClient", side_effect=RuntimeError("private-provider-payload")):
                with self.assertRaises(server.HTTPException) as error:
                    await identity.deliver("mobile", "+919876543211", "unit-only")
                self.assertEqual(error.exception.status_code, 503)
                self.assertNotIn("private-provider-payload", error.exception.detail)
        for field, value in [("TWILIO_ACCOUNT_SID", "../invalid"), ("TWILIO_FROM", "bad\r\nsender")]:
            with patch.dict(os.environ, {**env, field: value}):
                with self.assertRaises(server.HTTPException): identity.provider_ready("mobile")

    async def test_readonly_diagnostic_sanitizes_dns_error(self):
        from scripts.inspect_identity import error_category
        from pymongo.errors import ConfigurationError
        self.assertEqual(error_category(ConfigurationError("DNS resolution lifetime expired: private-host")), "dns_srv_resolution_timeout")

    async def test_registration_rejects_privileged_fields(self):
        profile = {"first_name": "New", "last_name": "Buyer", "email": "new@example.com", "mobile": "+919876543210", "account_role": "buyer", "accept_terms": True, "accept_privacy": True}
        for field in ("role", "email_verified", "suspended", "account_status", "user_id", "google_sub"):
            response = await self.api.post("/api/auth/otp/request", json={"identifier": profile["email"], "purpose": "register", "registration": {**profile, field: "forbidden"}})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(await self.db.otp_challenges.count_documents({}), 0)

    async def test_login_challenge_cannot_follow_reassigned_identifier(self):
        response, code = await self.request_code()
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"email": "changed@example.com"}})
        await self.db.users.insert_one({"user_id": "new-owner", "email": "owner@example.com", "email_verified": True, "role": "buyer"})
        result = await self.api.post("/api/auth/otp/verify", json={"challenge_id": response.json()["challenge_id"], "code": code})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(await self.db.user_sessions.count_documents({"user_id": "new-owner"}), 0)

    async def test_ip_and_account_limits(self):
        for subject, limit in [("ip:unit-test", 20), ("account:unit-test", 5), ("verify-ip:unit-test", 50)]:
            for _ in range(limit):
                await identity.throttle(subject, limit, 3600)
            with self.assertRaises(server.HTTPException) as error:
                await identity.throttle(subject, limit, 3600)
            self.assertEqual(error.exception.status_code, 429)
            self.assertIn("Retry-After", error.exception.headers)

    async def test_listing_validation_and_submission(self):
        loc = self.db.raw.localities.find_one({"is_active": True})
        await self.db.files.insert_one({"id": "photo", "owner_id": "owner", "kind": "property_photo", "is_deleted": False, "sha256": "hash"})
        body = {"posted_as": "owner", "title_en": "A new house", "description_en": "A clear description of this property", "purpose": "buy", "segment": "residential", "type": "independent-house", "locality_id": loc["id"], "price": 1000000, "area_sqft": 800, "bhk": 2, "photo_ids": ["photo"], "owner_declaration_accepted": True}
        # Resolve a valid residential type from reference data instead of guessing its slug.
        body["type"] = self.db.raw.property_types.find_one({"segment": "residential"})["slug"]
        self.assertEqual((await self.api.post("/api/listings", json=body)).status_code, 401)
        self.assertEqual((await self.api.post("/api/listings", json={**body, "owner_user_id": "other"}, headers=self.headers)).status_code, 422)
        response = await self.api.post("/api/listings", json=body, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        listing = self.db.raw.properties.find_one({"id": response.json()["id"]})
        self.assertEqual(listing["owner_user_id"], "owner"); self.assertEqual(listing["listing_status"], "pending_review")
        self.assertEqual((await self.api.get("/api/properties/" + listing["id"])).status_code, 404)

    async def test_fulfil_transaction_contract_and_duplicate(self):
        prop = self.db.raw.properties.find_one()
        order = {"id": "order", "property_id": prop["id"], "status": "created", "duration_days": 7}
        await self.db.payment_orders.insert_one(order)
        sentinel = object()
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def with_transaction(self, callback): return await callback(sentinel)
        class Client:
            async def start_session(self): return Session()
        self.db.client = Client()
        paid = await marketplace.fulfil(order, "payment", "test")
        again = await marketplace.fulfil(order, "payment", "test")
        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["featured_until"], again["featured_until"])

    async def test_payment_authorized_verification_stays_pending(self):
        order_id, payment_id = "rzp-order", "pay"
        await self.db.payment_orders.insert_one({"id": "order", "user_id": "owner", "razorpay_order_id": order_id, "amount": 100, "status": "created"})
        signature = hmac.new(b"unit-secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        class Provider:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def get(self, *args, **kwargs): return httpx.Response(200, json={"order_id": order_id, "amount": 100, "currency": "INR", "status": "authorized"})
        with patch.object(marketplace, "rzp_keys", return_value=("rzp_test_unit", "unit-secret")), patch.object(marketplace.httpx, "AsyncClient", return_value=Provider()), patch.object(marketplace, "fulfil", new_callable=AsyncMock) as fulfil:
            response = await self.api.post("/api/payments/featured/verify", headers=self.headers, json={"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature})
            self.assertEqual(response.status_code, 200); self.assertEqual(response.json()["status"], "pending"); fulfil.assert_not_awaited()

    async def test_payment_bad_signature_and_cancel(self):
        await self.db.payment_orders.insert_one({"id": "order", "user_id": "owner", "razorpay_order_id": "rzp-order", "amount": 100, "status": "created"})
        with patch.object(marketplace, "rzp_keys", return_value=("rzp_test_unit", "unit-secret")):
            result = await self.api.post("/api/payments/featured/verify", headers=self.headers, json={"razorpay_order_id": "rzp-order", "razorpay_payment_id": "pay", "razorpay_signature": "bad"})
            self.assertEqual(result.status_code, 400)
        await self.db.payment_orders.update_one({"id": "order"}, {"$set": {"status": "created"}})
        result = await self.api.post("/api/payments/featured/failed", headers=self.headers, json={"razorpay_order_id": "rzp-order", "reason": "cancelled"})
        self.assertEqual(result.status_code, 200); self.assertEqual(result.json()["status"], "cancelled")

    async def test_payment_order_uses_server_price_and_blocks_native(self):
        prop = self.db.raw.properties.find_one()
        await self.db.properties.update_one({"id": prop["id"]}, {"$set": {"owner_user_id": "owner"}})
        await self.db.featured_plans.insert_one({"id": "plan", "slug": "unit", "name_en": "Unit", "price_inr": 299, "duration_days": 7, "is_active": True})
        body = {"property_id": prop["id"], "plan_id": "plan"}
        result = await self.api.post("/api/payments/featured/order", headers=self.headers, json=body)
        self.assertEqual(result.status_code, 403)
        observed = {}
        class Provider:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def post(self, *args, **kwargs): observed.update(kwargs["json"]); return httpx.Response(200, json={"id": "rzp-order"})
        headers = await self.browser_login()
        with patch.object(marketplace, "rzp_keys", return_value=("rzp_test_unit", "unit-secret")), patch.object(marketplace.httpx, "AsyncClient", return_value=Provider()):
            result = await self.api.post("https://localhost/api/payments/featured/order", headers=headers, json=body)
        self.assertEqual(result.status_code, 200); self.assertEqual(observed["amount"], 29900)

    async def browser_bootstrap(self):
        response = await self.api.get("https://localhost/api/auth/browser/bootstrap", headers={"Origin": "http://localhost:8081", "X-LV-Client": "web"})
        self.assertEqual(response.status_code, 200)
        return response, {"Origin": "http://localhost:8081", "X-LV-Client": "web", "X-CSRF-Token": response.json()["csrf_token"]}

    async def browser_login(self, identifier="owner@example.com"):
        _, headers = await self.browser_bootstrap()
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", new_callable=AsyncMock) as delivery:
            requested = await self.api.post("https://localhost/api/auth/otp/request", headers=headers, json={"identifier": identifier})
        self.assertEqual(requested.status_code, 200)
        response = await self.api.post("https://localhost/api/auth/otp/verify", headers=headers,
            json={"challenge_id": requested.json()["challenge_id"], "code": delivery.await_args.args[2]})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("session_token", response.json())
        return {**headers, "X-CSRF-Token": response.json()["csrf_token"]}

    async def test_browser_cookie_attributes_and_local_development(self):
        response, _ = await self.browser_bootstrap()
        cookie = response.headers["set-cookie"]
        for attribute in ("__Host-lv_session=", "HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age="):
            self.assertIn(attribute, cookie)
        self.assertNotIn("Domain=", cookie)
        self.assertNotIn("session_token", response.json())
        local = await self.api.get("http://localhost/api/auth/browser/bootstrap", headers={"Origin": "http://localhost:8081"})
        self.assertIn("lv_dev_session=", local.headers["set-cookie"])
        self.assertIn("HttpOnly", local.headers["set-cookie"])

    async def test_browser_csrf_origin_and_mixed_credentials_rejected(self):
        headers = await self.browser_login()
        url = "https://localhost/api/me/profile"
        body = {"first_name": "First", "last_name": "Last"}
        for changed in [{"X-CSRF-Token": ""}, {"X-CSRF-Token": "wrong"}, {"Origin": "https://attacker.invalid"}, {"Origin": "null"}, {"Origin": ""}, {"Authorization": "Bearer owner-token"}]:
            response = await self.api.patch(url, headers={**headers, **changed}, json=body)
            self.assertEqual(response.status_code, 403)
        self.assertEqual((await self.api.patch(url, headers=headers, json=body)).status_code, 200)

    async def test_browser_expiry_revocation_and_logout(self):
        headers = await self.browser_login()
        url = "https://localhost/api/auth/me"
        self.assertEqual((await self.api.get(url, headers=headers)).status_code, 200)
        response = await self.api.post("https://localhost/api/auth/logout", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertEqual((await self.api.get(url, headers=headers)).status_code, 401)
        self.assertEqual((await self.api.post("https://localhost/api/auth/logout", headers=headers)).status_code, 200)
        # Bootstrap expiry is checked by the API even before Mongo TTL cleanup.
        _, fresh = await self.browser_bootstrap()
        await self.db.user_sessions.update_many({"transport": "browser"}, {"$set": {"expires_at": server.now() - timedelta(seconds=1)}})
        self.assertEqual((await self.api.post("https://localhost/api/auth/browser/google-nonce", headers=fresh)).status_code, 403)

    async def test_browser_cookie_cannot_be_used_as_native_bearer(self):
        await self.browser_login()
        token = self.api.cookies.get(browser_sessions.SECURE_COOKIE)
        self.assertIsNone(await server.user_for_token(token))
        self.api.cookies.clear()
        response = await self.api.post("/api/auth/logout", headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await self.db.user_sessions.count_documents({"transport": "browser", "user_id": "owner", "consumed": {"$ne": True}}), 1)
        self.assertEqual((await self.api.get("/api/auth/me", headers=self.headers)).status_code, 200)

    async def test_browser_managed_callback_rejected_before_provider(self):
        _, headers = await self.browser_bootstrap()
        with patch.object(server.httpx, "AsyncClient") as provider:
            for _ in range(2):
                response = await self.api.post("https://localhost/api/auth/session", headers=headers, json={"session_id": "untrusted-callback"})
                self.assertEqual(response.status_code, 503)
            provider.assert_not_called()

    async def test_browser_google_nonce_binding_and_replay(self):
        headers = await self.browser_login()
        nonce_response = await self.api.post("https://localhost/api/auth/browser/google-nonce", headers=headers)
        nonce = nonce_response.json()["nonce"]
        payload = {"id_token": "mock-credential-for-unit-test"}
        with patch.object(identity, "verify_google", return_value={"sub": "browser-google", "email": "owner@example.com", "nonce": "wrong"}):
            self.assertEqual((await self.api.post("https://localhost/api/auth/google/link", headers=headers, json=payload)).status_code, 400)
        with patch.object(identity, "verify_google", return_value={"sub": "browser-google", "email": "owner@example.com", "nonce": nonce}):
            self.assertEqual((await self.api.post("https://localhost/api/auth/google/link", headers=headers, json=payload)).status_code, 200)
            self.assertEqual((await self.api.post("https://localhost/api/auth/google/link", headers=headers, json=payload)).status_code, 400)

    async def test_browser_rotation_invalidates_old_cookie_and_tab_csrf(self):
        response, old_headers = await self.browser_bootstrap()
        old_cookie = self.api.cookies.get(browser_sessions.SECURE_COOKIE)
        headers = await self.browser_login()
        self.assertNotEqual(headers["X-CSRF-Token"], old_headers["X-CSRF-Token"])
        stale = await self.api.get("https://localhost/api/me/profile", headers=old_headers)
        self.assertEqual(stale.status_code, 401)
        old = await self.db.user_sessions.find_one({"session_token": browser_sessions.digest(old_cookie)})
        self.assertTrue(old["consumed"])

    async def test_browser_otp_cannot_be_verified_as_native(self):
        _, headers = await self.browser_bootstrap()
        with patch.object(identity, "provider_ready"), patch.object(identity, "deliver", new_callable=AsyncMock) as delivery:
            result = await self.api.post("https://localhost/api/auth/otp/request", headers=headers, json={"identifier": "owner@example.com"})
        code = delivery.await_args.args[2]
        self.api.cookies.clear()
        result = await self.api.post("/api/auth/otp/verify", json={"challenge_id": result.json()["challenge_id"], "code": code})
        self.assertEqual(result.status_code, 400)

    async def test_production_browser_origins_fail_closed(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "WEB_APP_ORIGINS": ""}):
            self.assertEqual((await self.api.get("https://localhost/api/auth/browser/bootstrap", headers={"Origin": "http://localhost:8081"})).status_code, 503)
        with patch.dict(os.environ, {"APP_ENV": "production", "WEB_APP_ORIGINS": "http://localhost:8081"}):
            with self.assertRaises(server.HTTPException): browser_sessions.origins()

    async def test_browser_account_switch_and_revocation(self):
        first = await self.browser_login()
        await self.db.users.insert_one({"user_id": "second", "email": "second@example.com", "email_verified": True, "role": "buyer"})
        second = await self.browser_login("second@example.com")
        url = "https://localhost/api/me/profile"
        self.assertEqual((await self.api.get(url, headers=first)).status_code, 401)
        response = await self.api.get(url, headers=second)
        self.assertEqual(response.json()["user_id"], "second")
        await self.db.user_sessions.update_many({"user_id": "second"}, {"$set": {"consumed": True}})
        self.assertEqual((await self.api.get(url, headers=second)).status_code, 401)

    async def test_browser_multipart_and_private_file_authorization(self):
        headers = await self.browser_login()
        file = {"file": ("invalid.png", b"invalid", "image/png")}
        response = await self.api.post("https://localhost/api/uploads", headers={**headers, "X-CSRF-Token": "wrong"}, files=file, data={"kind": "property_photo"})
        self.assertEqual(response.status_code, 403)
        response = await self.api.post("https://localhost/api/uploads", headers=headers, files=file, data={"kind": "property_photo"})
        self.assertEqual(response.status_code, 400)
        await self.db.files.insert_one({"id": "private", "owner_id": "other", "is_public": False, "is_deleted": False})
        response = await self.api.get("https://localhost/api/files/private?token=owner-token", headers=headers)
        self.assertEqual(response.status_code, 403)

    async def test_browser_cors_preflight_and_cross_site_rejection(self):
        response = await self.api.options("https://localhost/api/me/profile", headers={"Origin": "http://localhost:8081", "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "x-csrf-token,content-type"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:8081")
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")
        response = await self.api.get("https://localhost/api/auth/browser/bootstrap", headers={"Origin": "http://localhost:8081", "Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 403)

    async def test_browser_bootstrap_disabled_without_identity(self):
        with patch.dict(os.environ, {"IDENTITY_ENABLED": "false"}):
            response = await self.api.get("https://localhost/api/auth/browser/bootstrap", headers={"Origin": "http://localhost:8081"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(await self.db.user_sessions.count_documents({"transport": "browser"}), 0)

    async def test_native_managed_exchange_remains_supported(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"auth_provider": "emergent"}})
        class Provider:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def get(self, *args, **kwargs):
                return httpx.Response(200, json={"email": "owner@example.com", "session_token": "unit-provider-token"})
        with patch.object(server.httpx, "AsyncClient", return_value=Provider()):
            response = await self.api.post("/api/auth/session", headers={"X-LV-Client": "android"}, json={"session_id": "unit-provider-session"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("session_token", response.json())
        self.assertNotIn("set-cookie", response.headers)
        self.assertEqual((await server.user_for_token(response.json()["session_token"]))["user_id"], "owner")

    async def test_browser_google_login_rotation_and_callback_replay(self):
        _, headers = await self.browser_bootstrap()
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"google_sub": "web-google"}})
        nonce = (await self.api.post("https://localhost/api/auth/browser/google-nonce", headers=headers)).json()["nonce"]
        with patch.object(identity, "verify_google", return_value={"sub": "web-google", "email": "owner@example.com", "nonce": nonce}):
            response = await self.api.post("https://localhost/api/auth/google", headers=headers, json={"id_token": "mock-credential-for-unit-test"})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("session_token", response.json())
            fresh = {**headers, "X-CSRF-Token": response.json()["csrf_token"]}
            self.assertEqual((await self.api.post("https://localhost/api/auth/google", headers=fresh, json={"id_token": "mock-credential-for-unit-test"})).status_code, 400)

    async def test_browser_authenticated_expiry_and_secure_production_cookie(self):
        headers = await self.browser_login()
        await self.db.user_sessions.update_many({"transport": "browser", "user_id": "owner"}, {"$set": {"expires_at": server.now() - timedelta(seconds=1)}})
        self.assertEqual((await self.api.get("https://localhost/api/auth/me", headers=headers)).status_code, 401)
        with patch.dict(os.environ, {"APP_ENV": "production", "WEB_APP_ORIGINS": "https://app.example.test"}):
            response = await self.api.get("https://localhost/api/auth/browser/bootstrap", headers={"Origin": "https://app.example.test"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("__Host-lv_session=", response.headers["set-cookie"])
            self.assertIn("Secure", response.headers["set-cookie"])

    async def test_unrelated_user_cannot_unblock_thread(self):
        await self.db.enquiries.insert_one({"id": "thread", "user_id": "other", "lister_user_id": "another"})
        self.assertEqual((await self.api.delete("/api/enquiries/thread/block", headers=self.headers)).status_code, 404)

    async def test_refund_is_recorded_for_review_without_mutating_entitlement(self):
        await self.db.payment_orders.insert_one({"id": "order", "razorpay_payment_id": "pay", "amount": 100, "status": "paid"})
        raw = json.dumps({"event": "refund.processed", "payload": {"refund": {"entity": {"id": "refund", "payment_id": "pay", "amount": 50}}}}).encode()
        signature = hmac.new(b"unit-webhook", raw, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": "unit-webhook"}):
            response = await self.api.post("/api/payments/razorpay/webhook", content=raw, headers={"x-razorpay-signature": signature})
        self.assertEqual(response.status_code, 200)
        order = await self.db.payment_orders.find_one({"id": "order"})
        self.assertEqual(order["refund_status"], "processed_requires_review"); self.assertEqual(order["status"], "paid")


if __name__ == "__main__": unittest.main()
