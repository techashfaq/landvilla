"""Broker journey tests: mongomock and mocked file storage only."""
import unittest
from unittest.mock import patch, AsyncMock
import test_regressions as f


class BrokerJourney(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = f.Regressions.asyncTearDown

    async def asyncSetUp(self):
        await f.Regressions.asyncSetUp(self)
        await self.db.broker_profiles.create_index("user_id", unique=True)
        await self.db.files.insert_one({"id": "private-doc", "owner_id": "owner", "kind": "broker_doc", "is_public": False, "is_deleted": False, "storage_path": "synthetic", "content_type": "application/pdf", "original_name": "synthetic.pdf"})
        self.body = {"full_name": "Test Broker", "phone": "9876543210", "firm_name": "Test firm", "locality_id": self.db.raw.localities.find_one({"is_active": True})["id"], "document_ids": ["private-doc"], "declaration_accepted": True}

    async def apply(self, body=None):
        return await self.api.post("/api/broker/apply", headers=self.headers, json=body or self.body)

    async def test_submit_duplicate_and_private_profile(self):
        self.assertEqual((await self.apply()).status_code, 200)
        self.assertEqual((await self.apply()).status_code, 409)
        response = await self.api.get("/api/broker/me", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["application"]["locality_id"], self.body["locality_id"])
        self.assertEqual(response.json()["application"]["documents"], [{"id": "private-doc", "name": "synthetic.pdf"}])
        self.assertEqual((await self.api.get("/api/broker/me")).status_code, 401)
        self.assertEqual(await self.db.audit_logs.count_documents({"action": "broker.submitted"}), 1)

    async def test_invalid_locality_and_foreign_documents(self):
        self.assertEqual((await self.apply({**self.body, "locality_id": "missing"})).status_code, 400)
        await self.db.files.update_one({"id": "private-doc"}, {"$set": {"owner_id": "someone-else"}})
        self.assertEqual((await self.apply()).status_code, 400)
        self.assertEqual((await self.apply({**self.body, "status": "approved"})).status_code, 422)

    async def test_rejected_resubmission_and_suspension(self):
        await self.apply()
        await f.marketplace.set_broker("owner", {"user_id": "reviewer", "role": "admin"}, "rejected", "Provide updated proof", ("pending",))
        self.assertEqual((await self.apply()).json()["status"], "pending")
        await f.marketplace.set_broker("owner", {"user_id": "reviewer", "role": "admin"}, "approved", "Checked", ("pending",))
        self.assertTrue((await self.api.get("/api/me/lister", headers=self.headers)).json()["can_post_as_broker"])
        await f.marketplace.set_broker("owner", {"user_id": "reviewer", "role": "admin"}, "suspended", "Review required", ("approved",))
        self.assertEqual((await self.apply()).status_code, 403)
        self.assertFalse((await self.api.get("/api/me/lister", headers=self.headers)).json()["can_post_as_broker"])

    async def test_private_document_access_audited_even_with_bad_public_flag(self):
        await self.db.files.update_one({"id": "private-doc"}, {"$set": {"is_public": True, "owner_id": "other"}})
        with patch.object(f.marketplace, "_get", return_value=(b"synthetic", "application/pdf")) as storage:
            self.assertEqual((await self.api.get("/api/files/private-doc")).status_code, 403)
            self.assertEqual((await self.api.get("/api/files/private-doc", headers=self.headers)).status_code, 403)
            storage.assert_not_called()
            await self.db.users.update_one({"user_id": "owner"}, {"$set": {"role": "admin"}})
            response = await self.api.get("/api/files/private-doc", headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertEqual(await self.db.audit_logs.count_documents({"action": "file.view_private"}), 1)

    async def test_dashboard_counts_only_owned_broker_activity(self):
        for pid, owner, role in [("mine", "owner", "broker"), ("personal", "owner", "owner"), ("foreign", "other", "broker")]:
            await self.db.properties.insert_one({"id": pid, "owner_user_id": owner, "posted_by_role": role, "listing_status": "active"})
            await self.db.enquiries.insert_one({"id": pid, "property_id": pid, "lister_user_id": owner, "status": "new"})
        response = await self.api.get("/api/broker/me", headers=self.headers)
        self.assertEqual(response.json()["listings"], {"active": 1})
        self.assertEqual(response.json()["leads"], {"new": 1})

    async def test_broker_listing_cannot_bypass_approval_by_changing_role(self):
        await self.db.properties.insert_one({"id": "broker-listing", "owner_user_id": "owner", "posted_by_role": "broker", "listing_status": "changes_requested"})
        body = {"posted_as": "owner", "title_en": "Test listing", "description_en": "A synthetic description of this property", "purpose": "buy", "segment": "residential", "type": "independent-house", "locality_id": self.body["locality_id"], "price": 1000000, "area_sqft": 800, "bhk": 2, "photo_ids": ["photo"], "owner_declaration_accepted": True}
        response = await self.api.put("/api/listings/broker-listing", headers=self.headers, json=body)
        self.assertEqual(response.status_code, 400)
        response = await self.api.put("/api/listings/broker-listing", headers=self.headers, json={**body, "posted_as": "broker"})
        self.assertEqual(response.status_code, 403)
