"""Administrative decisions: in-memory fixtures only, no providers or real DB."""
import unittest
import test_regressions as f


class ModerationBoundaries(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = f.Regressions.asyncSetUp
    asyncTearDown = f.Regressions.asyncTearDown

    async def test_admin_cannot_moderate_own_listing(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})
        original = {"id": "review-fixture", "owner_user_id": "owner", "posted_by_role": "owner", "listing_status": "pending_review", "is_demo": False}
        await self.db.properties.insert_one(original.copy())
        before = await self.db.properties.find_one({"id": "review-fixture"})
        for action in ("approve", "reject", "request-changes"):
            response = await self.api.post(f"/api/admin/listings/review-fixture/{action}", headers=self.headers, json={"note": "Synthetic review reason"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(await self.db.properties.find_one({"id": "review-fixture"}), before)
        self.assertEqual(await self.db.audit_logs.count_documents({}), 0)

    async def test_admin_cannot_review_own_broker_application(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})
        await self.db.broker_profiles.insert_one({"user_id": "owner", "status": "pending"})
        before = await self.db.broker_profiles.find_one({"user_id": "owner"})
        for action in ("approve", "reject", "suspend"):
            response = await self.api.post(f"/api/admin/brokers/owner/{action}", headers=self.headers, json={"note": "Synthetic review reason"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(await self.db.broker_profiles.find_one({"user_id": "owner"}), before)
        self.assertEqual(await self.db.audit_logs.count_documents({}), 0)

    async def test_independent_admin_can_approve_and_audit(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})
        await self.db.users.insert_one({"user_id": "other", "email": "other@example.test", "role": "buyer", "account_status": "active"})
        await self.db.properties.insert_one({"id": "review-fixture", "owner_user_id": "other", "posted_by_role": "owner", "listing_status": "pending_review", "is_demo": False})
        response = await self.api.post("/api/admin/listings/review-fixture/approve", headers=self.headers, json={"note": "Synthetic review"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["listing_status"], "active")
        self.assertEqual(await self.db.audit_logs.count_documents({"actor": "owner", "target": "review-fixture"}), 1)
        await self.db.broker_profiles.insert_one({"user_id": "other", "status": "pending"})
        response = await self.api.post("/api/admin/brokers/other/approve", headers=self.headers, json={"note": "Synthetic review"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")

    async def test_non_admin_cannot_issue_any_moderation_decision(self):
        for path in ("listings/review-fixture/approve", "brokers/other/approve"):
            response = await self.api.post("/api/admin/" + path, headers=self.headers, json={"note": "Synthetic review"})
            self.assertEqual(response.status_code, 403)
        self.assertEqual(await self.db.audit_logs.count_documents({}), 0)
