"""Owner lifecycle tests use in-memory storage, never external providers."""
import unittest
import test_regressions as fixture


class OwnerListings(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = fixture.Regressions.asyncTearDown

    async def asyncSetUp(self):
        await fixture.Regressions.asyncSetUp(self)
        loc = self.db.raw.localities.find_one({"is_active": True})
        for pid in ("photo-one", "photo-two"):
            await self.db.files.insert_one({"id": pid, "owner_id": "owner", "kind": "property_photo", "is_deleted": False, "sha256": pid})
        self.body = {"posted_as": "owner", "title_en": "Owner test house", "description_en": "A clear description of this property", "purpose": "buy", "segment": "residential", "type": "independent-house", "locality_id": loc["id"], "price": 1000000, "area_sqft": 800, "bhk": 2, "photo_ids": ["photo-two", "photo-one"], "owner_declaration_accepted": True}
        response = await self.api.post("/api/listings", json=self.body, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.pid = response.json()["id"]
        self.url = f"/api/listings/{self.pid}"

    async def action(self, action, headers=None):
        return await self.api.post(self.url + "/status", json={"action": action}, headers=self.headers if headers is None else headers)

    async def test_owner_and_auth_boundaries(self):
        self.assertEqual((await self.action("delete", {})).status_code, 401)
        await self.db.properties.update_one({"id": self.pid}, {"$set": {"owner_user_id": "another-owner"}})
        for action in ("deactivate", "reactivate", "delete"):
            self.assertEqual((await self.action(action)).status_code, 404)
        self.assertEqual((await self.api.put(self.url, json=self.body, headers=self.headers)).status_code, 404)

    async def test_reactivation_requires_review_and_retains_order(self):
        self.assertEqual((await self.action("deactivate")).json()["listing_status"], "inactive")
        self.assertEqual((await self.action("reactivate")).json()["listing_status"], "pending_review")
        self.assertEqual((await self.api.get("/api/properties/" + self.pid)).status_code, 404)
        doc = self.db.raw.properties.find_one({"id": self.pid})
        self.assertEqual(doc["images"], ["/api/files/photo-two", "/api/files/photo-one"])

    async def test_reactivation_revalidates_photo_ownership(self):
        await self.action("deactivate")
        await self.db.files.update_one({"id": "photo-one"}, {"$set": {"owner_id": "someone-else"}})
        self.assertEqual((await self.action("reactivate")).status_code, 400)

    async def test_soft_delete_cannot_be_republished_or_edited(self):
        self.assertEqual((await self.action("delete")).status_code, 200)
        self.assertEqual(self.db.raw.properties.find_one({"id": self.pid})["listing_status"], "deleted")
        self.assertEqual((await self.api.get("/api/listings/mine", headers=self.headers)).json()["total"], 0)
        self.assertEqual((await self.api.get(self.url + "/edit", headers=self.headers)).status_code, 404)
        self.assertEqual((await self.api.put(self.url, json=self.body, headers=self.headers)).status_code, 404)
        self.assertEqual((await self.action("reactivate")).status_code, 404)
        self.assertEqual(self.db.raw.files.count_documents({"owner_id": "owner"}), 2)

    async def test_invalid_transitions(self):
        self.assertEqual((await self.action("reactivate")).status_code, 409)
        self.assertEqual((await self.action("approve")).status_code, 422)
        for status in ("expired", "sold_rented", "rejected"):
            await self.db.properties.update_one({"id": self.pid}, {"$set": {"listing_status": status}})
            self.assertEqual((await self.action("reactivate")).status_code, 409)
            self.assertEqual((await self.action("deactivate")).status_code, 409)

    async def test_resubmit_photo_removal(self):
        result = await self.api.put(self.url, json={**self.body, "photo_ids": ["photo-one"]}, headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["images"], ["/api/files/photo-one"])
        self.assertEqual(result.json()["listing_status"], "pending_review")

    async def test_public_response_hides_owner_history(self):
        await self.action("deactivate")
        await self.db.properties.update_one({"id": self.pid}, {"$set": {"listing_status": "active"}})
        result = await self.api.get("/api/properties/" + self.pid)
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("owner_history", result.json())
