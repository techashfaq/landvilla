"""R2 mobile identity regressions; in-memory DB and mocked delivery only."""
import asyncio
import unittest
from datetime import timedelta
from unittest.mock import patch

import test_regressions as f

PHONE = "+919876543210"
OTHER = "+919876543211"


class MobileReservation(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = f.Regressions.asyncSetUp
    asyncTearDown = f.Regressions.asyncTearDown
    request_code = f.Regressions.request_code
    browser_bootstrap = f.Regressions.browser_bootstrap
    browser_login = f.Regressions.browser_login

    async def register(self, email):
        profile = dict(first_name="Review", last_name="Fixture", email=email, mobile=PHONE,
                       account_role="buyer", accept_terms=True, accept_privacy=True)
        response, code = await self.request_code("register", email, profile)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(code)
        return await self.verify(response, code)

    async def verify(self, response, code, headers=None):
        return await self.api.post("/api/auth/otp/verify", headers=headers,
            json={"challenge_id": response.json()["challenge_id"], "code": code})

    async def contact(self, phone=PHONE, headers=None):
        return await self.request_code("contact", phone, headers=headers or self.headers)

    async def owner(self):
        return await self.db.users.find_one({"user_id": "owner"})

    async def second_user(self):
        await self.db.users.insert_one({"user_id": "second", "email": "second@example.com", "role": "buyer"})
        await self.db.user_sessions.insert_one({"session_token": "second-token", "user_id": "second",
            "created_at": f.server.now(), "expires_at": f.server.now() + timedelta(days=1)})
        return {"Authorization": "Bearer second-token"}

    async def test_registration_omits_mobile_and_profile_is_explicit(self):
        response = await self.register("new@example.com")
        self.assertEqual(response.status_code, 200)
        user = await self.db.users.find_one({"email": "new@example.com"})
        self.assertNotIn("mobile", user)
        self.assertFalse(user["mobile_verified"])
        result = await self.api.get("/api/me/profile", headers={"Authorization": "Bearer " + response.json()["session_token"]})
        self.assertIsNone(result.json()["mobile"])
        self.assertFalse(result.json()["profile_complete"])
        self.assertNotIn("mobile_contact_version", result.json())

    async def test_two_emails_can_supply_same_mobile(self):
        for email in ("one@example.com", "two@example.com"):
            self.assertEqual((await self.register(email)).status_code, 200)
        self.assertEqual(await self.db.users.count_documents({"mobile": PHONE}), 0)

    async def test_absent_and_unverified_mobile_cannot_login(self):
        for present in (False, True):
            if present:
                await self.db.users.update_one({"user_id": "owner"}, {"$set": {"mobile": PHONE, "mobile_verified": False}})
            response, code = await self.request_code("login", PHONE)
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(code)
            await self.db.otp_challenges.delete_many({})  # isolated test reset only

    async def test_mobile_assignment_is_one_atomic_update(self):
        response, code = await self.contact()
        self.assertNotIn("mobile", await self.owner())
        original = f.Collection.__getattr__
        writes = []
        def instrument(collection, name):
            call = original(collection, name)
            if name == "update_one" and collection.coll.name == "users":
                async def wrapped(*args, **kwargs):
                    writes.append(args)
                    return await call(*args, **kwargs)
                return wrapped
            return call
        with patch.object(f.Collection, "__getattr__", instrument):
            result = await self.verify(response, code, self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][1]["$set"]["mobile"], PHONE)
        self.assertIs(writes[0][1]["$set"]["mobile_verified"], True)
        self.assertIn("mobile_contact_version", writes[0][1]["$set"])
        self.assertEqual((await self.owner())["mobile"], PHONE)

    async def test_invalid_expired_and_reused_challenges(self):
        response, code = await self.contact()
        wrong = "000000" if code != "000000" else "111111"
        self.assertEqual((await self.verify(response, wrong, self.headers)).status_code, 400)
        self.assertNotIn("mobile", await self.owner())
        await self.db.otp_challenges.update_one({"challenge_id": response.json()["challenge_id"]}, {"$set": {"expires_at": f.server.now() - timedelta(seconds=1)}})
        self.assertEqual((await self.verify(response, code, self.headers)).status_code, 400)
        self.assertNotIn("mobile", await self.owner())
        fresh, code = await self.contact(OTHER)
        self.assertEqual((await self.verify(fresh, code, self.headers)).status_code, 200)
        before = await self.owner()
        self.assertEqual((await self.verify(fresh, code, self.headers)).status_code, 400)
        self.assertEqual(await self.owner(), before)

    async def test_wrong_account_cannot_claim(self):
        response, code = await self.contact()
        headers = await self.second_user()
        self.assertEqual((await self.verify(response, code, headers)).status_code, 403)
        self.assertEqual(await self.db.users.count_documents({"mobile": PHONE}), 0)

    async def test_recent_auth_rechecked(self):
        response, code = await self.contact()
        await self.db.user_sessions.update_one({"session_token": "owner-token"}, {"$set": {"created_at": f.server.now() - timedelta(minutes=16)}})
        self.assertEqual((await self.verify(response, code, self.headers)).status_code, 403)
        self.assertEqual((await self.contact(OTHER))[0].status_code, 403)
        self.assertNotIn("mobile", await self.owner())

    async def test_browser_challenge_cannot_be_used_as_native(self):
        headers = await self.browser_login()
        with patch.object(f.identity, "provider_ready"), patch.object(f.identity, "deliver", new_callable=f.AsyncMock) as delivery:
            response = await self.api.post("https://localhost/api/auth/otp/request", headers=headers,
                json={"purpose": "contact", "identifier": PHONE})
        self.assertEqual(response.status_code, 200)
        code = delivery.await_args.args[2]
        self.api.cookies.clear()
        self.assertEqual((await self.verify(response, code, self.headers)).status_code, 400)
        self.assertNotIn("mobile", await self.owner())

    async def test_concurrent_claims_unique_index_and_retry(self):
        headers = await self.second_user()
        first, code1 = await self.contact()
        second, code2 = await self.contact(headers=headers)
        original = f.Collection.__getattr__
        arrived = 0
        gate = asyncio.Event()
        async def synchronized(collection, query, *args, **kwargs):
            nonlocal arrived
            result = await original(collection, "find_one")(query, *args, **kwargs)
            if collection.coll.name == "users" and query == {"mobile": PHONE}:
                arrived += 1
                if arrived == 2: gate.set()
                await asyncio.wait_for(gate.wait(), 3)
            return result
        # Both availability reads see no owner; the unique index must arbitrate writes.
        with patch.object(f.Collection, "find_one", synchronized, create=True):
            results = await asyncio.gather(self.verify(first, code1, self.headers), self.verify(second, code2, headers))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        self.assertEqual(await self.db.users.count_documents({"mobile": PHONE, "mobile_verified": True}), 1)
        loser = 0 if results[0].status_code == 409 else 1
        self.assertEqual(results[loser].json()["detail"], "Contact cannot be linked")
        loser_headers = [self.headers, headers][loser]
        fresh, code = await self.contact(OTHER, loser_headers)
        self.assertEqual((await self.verify(fresh, code, loser_headers)).status_code, 200)

    async def test_existing_verified_and_legacy_unverified_owners_untouched(self):
        headers = await self.second_user()
        for verified, phone in ((True, PHONE), (False, OTHER)):
            await self.db.users.update_one({"user_id": "second"}, {"$set": {"mobile": phone, "mobile_verified": verified}})
            before = await self.db.users.find_one({"user_id": "second"})
            response, code = await self.contact(phone)
            result = await self.verify(response, code, self.headers)
            self.assertEqual(result.status_code, 409)
            self.assertEqual(await self.db.users.find_one({"user_id": "second"}), before)
            self.assertNotIn("mobile", await self.owner())
        self.assertEqual((await self.register("new@example.com")).status_code, 200)
        self.assertEqual((await self.db.users.find_one({"user_id": "second"}))["mobile"], OTHER)

    async def test_stale_contact_challenge_and_missing_snapshot_rejected(self):
        first, code1 = await self.contact()
        second, code2 = await self.contact(OTHER)
        self.assertEqual((await self.verify(second, code2, self.headers)).status_code, 200)
        self.assertEqual((await self.verify(first, code1, self.headers)).status_code, 409)
        self.assertEqual((await self.owner())["mobile"], OTHER)
        await self.db.otp_challenges.update_many({}, {"$set": {"resend_at": f.server.now() - timedelta(seconds=1)}})
        fresh, code = await self.contact()
        await self.db.otp_challenges.update_one({"challenge_id": fresh.json()["challenge_id"]}, {"$unset": {"mobile_state": ""}})
        self.assertEqual((await self.verify(fresh, code, self.headers)).status_code, 409)
        self.assertEqual((await self.owner())["mobile"], OTHER)

    async def test_verified_mobile_email_and_google_login(self):
        response, code = await self.contact()
        self.assertEqual((await self.verify(response, code, self.headers)).status_code, 200)
        for identifier in (PHONE, "owner@example.com"):
            response, code = await self.request_code("login", identifier)
            result = await self.verify(response, code)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["user"]["user_id"], "owner")
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"google_sub": "fixture-google"}})
        with patch.object(f.identity, "verify_google", return_value={"sub": "fixture-google", "email": "owner@example.com"}):
            result = await self.api.post("/api/auth/google", json={"id_token": "synthetic-google-credential"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["user"]["user_id"], "owner")

    async def test_changed_away_and_back_invalidates_old_challenge(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"mobile": PHONE, "mobile_verified": True}})
        old, old_code = await self.contact("+919876543212")
        for phone in (OTHER, PHONE):
            response, code = await self.contact(phone)
            self.assertEqual((await self.verify(response, code, self.headers)).status_code, 200)
        self.assertEqual((await self.verify(old, old_code, self.headers)).status_code, 409)
        self.assertEqual((await self.owner())["mobile"], PHONE)
