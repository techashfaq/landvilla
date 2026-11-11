"""Admin operations use the existing in-memory fixture; no provider calls."""
import unittest
from unittest.mock import patch
import test_regressions as f


class AdminOperations(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = f.Regressions.asyncTearDown

    async def asyncSetUp(self):
        await f.Regressions.asyncSetUp(self)
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})

    async def test_users_project_only_safe_fields_and_paginate(self):
        for i in range(23):
            await self.db.users.insert_one({"user_id": f"customer-{i:02}", "email": f"customer-{i:02}@example.test", "name": "Sample customer", "role": "buyer", "password_hash": "hidden", "otp": "hidden"})
        r = await self.api.get("/api/admin/users?q=Sample&page=2&limit=20", headers=self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total"], 23)
        self.assertEqual(len(r.json()["items"]), 3)
        self.assertNotIn("hidden", r.text)

    async def test_suspend_revokes_sessions_and_hides_listings(self):
        await self.db.users.insert_one({"user_id": "customer", "role": "buyer", "account_status": "active"})
        await self.db.user_sessions.insert_one({"session_token": "synthetic", "user_id": "customer"})
        await self.db.properties.insert_one({"id": "listing", "owner_user_id": "customer", "listing_status": "active"})
        r = await self.api.post("/api/admin/users/customer/suspend", headers=self.headers, json={"note": "Reviewed abuse report"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(await self.db.user_sessions.count_documents({"user_id": "customer"}), 0)
        self.assertEqual((await self.db.properties.find_one({"id": "listing"}))["listing_status"], "suspended")
        r = await self.api.post("/api/admin/users/customer/reactivate", headers=self.headers, json={"note": "Review completed"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((await self.db.properties.find_one({"id": "listing"}))["listing_status"], "suspended")

    async def test_staff_permissions_fail_closed_and_no_self_changes(self):
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"admin_permissions": ["listings"]}})
        for path in ("users", "audit", "payments", "brokers"):
            self.assertEqual((await self.api.get("/api/admin/" + path, headers=self.headers)).status_code, 403)
        self.assertEqual((await self.api.get("/api/admin/listings", headers=self.headers)).status_code, 200)
        await self.db.users.update_one({"user_id": "owner"}, {"$unset": {"admin_permissions": ""}})
        self.assertEqual((await self.api.post("/api/admin/users/owner/suspend", headers=self.headers, json={"note": "Self suspension"})).status_code, 403)
        with patch.dict("os.environ", {"STAFF_MANAGER_IDS": ""}):
            self.assertEqual((await self.api.post("/api/admin/staff/other/permissions", headers=self.headers, json={"note": "Grant permissions", "permissions": ["listings"]})).status_code, 403)

    async def test_cms_drafts_never_public_and_published_text_is_projected(self):
        body = {"kind": "faq", "title": "Sample question", "body": "Approved synthetic answer", "note": "Content review completed", "status": "draft"}
        r = await self.api.post("/api/admin/cms", headers=self.headers, json=body)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((await self.api.get("/api/content?kind=faq")).json()["items"], [])
        await self.api.put("/api/admin/cms/" + r.json()["id"], headers=self.headers, json={**body, "status": "published"})
        public = (await self.api.get("/api/content?kind=faq")).json()["items"]
        self.assertEqual(len(public), 1)
        self.assertNotIn("note", public[0])

    async def test_anonymous_and_customer_admin_access_denied(self):
        self.assertEqual((await self.api.get("/api/admin/users")).status_code, 401)
        await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "buyer"}})
        for path in ("users", "cms", "audit", "enquiries", "staff", "cities", "zones"):
            self.assertEqual((await self.api.get("/api/admin/" + path, headers=self.headers)).status_code, 403)
