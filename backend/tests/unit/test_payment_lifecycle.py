"""Payment guards and Play verification: all providers and databases are mocked."""
import unittest
from unittest.mock import AsyncMock, patch
import test_regressions as f
import play_billing as play
from payment_contracts import captured_payment
from fastapi import HTTPException


class PaymentLifecycle(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = f.Regressions.asyncSetUp
    asyncTearDown = f.Regressions.asyncTearDown

    async def test_only_explicitly_published_packages_are_available(self):
        for status in ("draft", "inactive", "active"):
            await self.db.featured_plans.insert_one({"id": status, "status": status, "is_active": True, "order": 1})
        await self.db.featured_plans.insert_one({"id": "legacy", "is_active": True})
        response = await self.api.get("/api/featured-plans")
        self.assertEqual([p["id"] for p in response.json()["items"]], ["active"])

    async def test_payment_contract_requires_provider_amount_currency_order_and_capture(self):
        order = {"razorpay_order_id": "order_x", "amount": 50000}
        good = {"id": "pay_x", "order_id": "order_x", "amount": 50000, "currency": "INR", "status": "captured"}
        self.assertTrue(captured_payment(good, order))
        self.assertFalse(captured_payment({**good, "status": "authorized"}, order))
        for change in ({"amount": "50000"}, {"amount": 1}, {"currency": "USD"}, {"order_id": "other"}):
            with self.assertRaises(HTTPException): captured_payment({**good, **change}, order)

    async def test_play_pending_and_wrong_account_cannot_activate(self):
        await self.db.payment_orders.insert_one({"id": "play-intent", "user_id": "owner", "provider": "google_play", "play_product_id": "featured.test", "status": "pending"})
        data = {"obfuscatedExternalAccountId": play.account_id("owner"), "obfuscatedExternalProfileId": "play-intent", "productLineItem": [{"productId": "featured.test"}], "purchaseStateContext": {"purchaseState": "PENDING"}}
        with patch.object(play, "purchase_details", AsyncMock(return_value=data)), patch.object(f.marketplace, "fulfil", AsyncMock()) as fulfil:
            r = await self.api.post("/api/payments/play/verify", headers=self.headers, json={"purchase_token": "synthetic-token"})
            self.assertEqual(r.status_code, 200); self.assertEqual(r.json()["status"], "pending"); fulfil.assert_not_awaited()
            data["obfuscatedExternalAccountId"] = play.account_id("someone-else")
            self.assertEqual((await self.api.post("/api/payments/play/verify", headers=self.headers, json={"purchase_token": "synthetic-token"})).status_code, 403)

    async def test_play_receipt_replay_cannot_move_between_orders(self):
        await self.db.payment_orders.insert_one({"id": "play-intent", "user_id": "owner", "provider": "google_play", "play_product_id": "featured.test", "status": "pending", "play_receipt_hash": "different-receipt"})
        data = {"obfuscatedExternalAccountId": play.account_id("owner"), "obfuscatedExternalProfileId": "play-intent", "productLineItem": [{"productId": "featured.test"}], "testPurchaseContext": {"fopType": "TEST"}, "purchaseStateContext": {"purchaseState": "PURCHASED"}}
        with patch.object(play, "purchase_details", AsyncMock(return_value=data)), patch.object(f.marketplace, "fulfil", AsyncMock()) as fulfil:
            self.assertEqual((await self.api.post("/api/payments/play/verify", headers=self.headers, json={"purchase_token": "synthetic-token"})).status_code, 409)
            fulfil.assert_not_awaited()

    async def test_refunds_require_admin_and_policy_gate(self):
        r = await self.api.post("/api/admin/payments/x/refund", headers=self.headers, json={"note": "Synthetic reason"})
        self.assertEqual(r.status_code, 403)
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})
        with patch.dict("os.environ", {"REFUNDS_ENABLED": "false"}):
            self.assertEqual((await self.api.post("/api/admin/payments/x/refund", headers=self.headers, json={"note": "Synthetic reason"})).status_code, 503)

    async def test_play_notifications_require_authenticated_sender(self):
        with patch.dict("os.environ", {"GOOGLE_PLAY_PUBSUB_AUDIENCE": "https://example.invalid/callback", "GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT": "sender@example.invalid"}):
            self.assertEqual((await self.api.post("/api/payments/play/notifications", json={})).status_code, 401)

    async def test_full_refund_is_idempotent_and_preserves_another_paid_period(self):
        from datetime import timedelta
        cutoff = f.server.now()
        await self.db.properties.insert_one({"id": "refund-property", "featured": True, "featured_until": cutoff + timedelta(days=10)})
        original = {"id": "refund-order", "property_id": "refund-property", "status": "paid", "featured_from": cutoff, "featured_until": cutoff + timedelta(days=10)}
        await self.db.payment_orders.insert_one(original.copy())
        await self.db.payment_orders.insert_one({"id": "other-paid", "property_id": "refund-property", "status": "paid", "featured_from": cutoff, "featured_until": cutoff + timedelta(days=3)})
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def with_transaction(self, callback): return await callback(None)
        class Client:
            async def start_session(self): return Session()
        self.db.client = Client()
        await f.marketplace.apply_full_refund(original, "refund_test")
        await f.marketplace.apply_full_refund(original, "refund_test")
        prop = await self.db.properties.find_one({"id": "refund-property"})
        self.assertTrue(prop["featured"])
        self.assertEqual(prop["featured_until"], (await self.db.payment_orders.find_one({"id": "other-paid"}))["featured_until"])
        self.assertEqual((await self.db.payment_orders.find_one({"id": "refund-order"}))["status"], "refunded")

    async def test_capture_for_ineligible_listing_is_recorded_without_activation(self):
        await self.db.properties.insert_one({"id": "hidden", "owner_user_id": "owner", "listing_status": "suspended", "is_demo": False, "featured": False})
        order = {"id": "review-order", "user_id": "owner", "property_id": "hidden", "status": "created", "duration_days": 7}
        await self.db.payment_orders.insert_one(order.copy())
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def with_transaction(self, callback): return await callback(None)
        class Client:
            async def start_session(self): return Session()
        self.db.client = Client()
        result = await f.marketplace.fulfil(order, "pay_verified", "webhook")
        self.assertEqual(result["status"], "payment_review")
        self.assertEqual(result["razorpay_payment_id"], "pay_verified")
        self.assertFalse((await self.db.properties.find_one({"id": "hidden"}))["featured"])

    async def test_razorpay_refresh_cannot_process_a_play_purchase(self):
        await self.db.payment_orders.insert_one({"id": "play_pending", "user_id": "owner", "status": "pending", "provider": "google_play"})
        with patch.object(f.marketplace.httpx, "AsyncClient") as provider:
            r = await self.api.post("/api/payments/play_pending/refresh", headers=self.headers, json={})
            self.assertEqual(r.status_code, 400)
            provider.assert_not_called()
