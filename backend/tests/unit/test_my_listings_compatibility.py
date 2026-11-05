"""R4 legacy default and explicit pagination; in-memory fixtures only."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
import test_regressions as f


class MyListingsCompatibility(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = f.Regressions.asyncTearDown

    async def asyncSetUp(self):
        await f.Regressions.asyncSetUp(self)
        template = self.db.raw.properties.find_one()
        self.statuses = [s["slug"] for s in self.db.raw.listing_statuses.find()]
        self.assertTrue(self.statuses)
        self.created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.expiry = self.created + timedelta(days=1)
        self.ids = [f"owned-{i:03}" for i in range(205)]
        # Insert in reverse order to prove sorting is not insertion order.
        for i in reversed(range(205)):
            doc = copy.deepcopy(template)
            for key in ("_id", "demo_key"):
                doc.pop(key, None)
            doc.update(id=self.ids[i], owner_user_id="owner", is_demo=False,
                       listing_status=self.statuses[i % len(self.statuses)],
                       created_at=self.created-timedelta(days=i // 5),
                       moderation={"note": "Synthetic review note"},
                       photo_ids=["synthetic-photo"], featured=True,
                       featured_until=self.expiry, photo_hashes=["private-hash"],
                       duplicate_flags=["internal-flag"])
            await self.db.properties.insert_one(doc)
        other = copy.deepcopy(doc)
        other.pop("_id", None)
        other.update(id="other-newest", owner_user_id="other", created_at=self.created+timedelta(days=10))
        await self.db.properties.insert_one(other)
        for i in range(2):
            await self.db.enquiries.insert_one({"id": f"lead-{i}", "lister_user_id": "owner", "property_id": self.ids[0]})
        await self.db.enquiries.insert_one({"id": "other-lead", "lister_user_id": "other", "property_id": self.ids[0]})

    async def mine(self, query="", headers=None):
        return await self.api.get("/api/listings/mine"+("?"+query if query else ""),
                                  headers=self.headers if headers is None else headers)

    def assert_page(self, response, ids, page, limit, total=205):
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual([p["id"] for p in data["items"]], ids)
        self.assertEqual((data["page"], data["limit"], data["total"]), (page, limit, total))
        self.assertNotIn("other-newest", [p["id"] for p in data["items"]])
        return data

    async def test_legacy_default_200_and_metadata(self):
        self.assert_page(await self.mine(), self.ids[:200], 1, 200)

    async def test_explicit_20_and_second_page(self):
        self.assert_page(await self.mine("page=1&limit=20"), self.ids[:20], 1, 20)
        self.assert_page(await self.mine("page=2&limit=20"), self.ids[20:40], 2, 20)

    async def test_default_second_page_and_out_of_range(self):
        self.assert_page(await self.mine("page=2"), self.ids[200:], 2, 200)
        self.assert_page(await self.mine("page=3"), [], 3, 200)

    async def test_ties_and_all_statuses(self):
        data = self.assert_page(await self.mine(), self.ids[:200], 1, 200)
        self.assertEqual([p["id"] for p in data["items"][:5]], self.ids[:5])
        self.assertEqual({p["listing_status"] for p in data["items"]}, set(self.statuses))

    async def test_empty_account(self):
        await self.db.users.insert_one({"user_id": "empty", "email": "empty@example.com", "role": "buyer", "account_status": "active"})
        await self.db.user_sessions.insert_one({"session_token": "empty-test-token", "user_id": "empty", "created_at": f.server.now(), "expires_at": f.server.now()+timedelta(days=1)})
        self.assert_page(await self.mine(headers={"Authorization": "Bearer empty-test-token"}), [], 1, 200, 0)

    async def test_limits_and_invalid_queries(self):
        self.assert_page(await self.mine("limit=200"), self.ids[:200], 1, 200)
        self.assert_page(await self.mine("limit=1"), self.ids[:1], 1, 1)
        for query in ("limit=201", "limit=0", "limit=-1", "limit=abc", "limit=1.5",
                      "page=0", "page=-1", "page=abc", "page=1.5"):
            with self.subTest(query=query):
                self.assertEqual((await self.mine(query)).status_code, 422)

    async def test_unauthenticated_rejected(self):
        self.assertEqual((await self.mine(headers={})).status_code, 401)

    async def test_enrichment_and_lead_ownership(self):
        response = await self.mine("limit=2")
        data = self.assert_page(response, self.ids[:2], 1, 2)
        item = data["items"][0]
        self.assertEqual(item["moderation"], {"note": "Synthetic review note"})
        self.assertEqual(item["photo_ids"], ["synthetic-photo"])
        self.assertIsNotNone(item["locality"])
        self.assertIn("zone", item)
        self.assertIn("images", item)
        self.assertEqual(datetime.fromisoformat(item["featured_until"].replace("Z", "+00:00")), self.expiry)
        self.assertFalse(item["featured"])
        self.assertEqual(item["lead_count"], 2)
        self.assertEqual(data["items"][1]["lead_count"], 0)
        for key in ("owner_user_id", "photo_hashes", "duplicate_flags", "_id", "demo_key"):
            self.assertNotIn(key, item)
