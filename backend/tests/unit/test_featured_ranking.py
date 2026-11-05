"""R3: isolated public ranking, UTC, renewal and read-only regressions."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import test_regressions as f
from featured import effective_featured

T = datetime(2030, 1, 1, tzinfo=timezone.utc)
MISSING = object()


class FeaturedRanking(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = f.Regressions.asyncSetUp
    asyncTearDown = f.Regressions.asyncTearDown

    async def fixtures(self):
        self.template = self.db.raw.properties.find_one()
        self.db.raw.properties.delete_many({})
        self.clock = patch.object(f.server, "now", return_value=T)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.extra_clock = patch.object(f.extras, "now", return_value=T)
        self.extra_clock.start()
        self.addCleanup(self.extra_clock.stop)

    async def add(self, ident, featured=False, expiry=MISSING, age=0, price=100, **fields):
        p = copy.deepcopy(self.template)
        for key in ("_id", "demo_key", "featured_until"):
            p.pop(key, None)
        p.update(id=ident, title_en=ident, is_demo=False, featured=featured,
                 listing_status="active", created_at=T-timedelta(days=age), price=price)
        if expiry is not MISSING:
            p["featured_until"] = expiry
        p.update(fields)
        await self.db.properties.insert_one(p)

    async def search(self, query=""):
        r = await self.api.get("/api/properties" + ("?"+query if query else ""))
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def test_active_priority_and_flags(self):
        await self.fixtures()
        await self.add("ordinary")
        await self.add("active", True, T+timedelta(days=1), age=10)
        result = await self.search()
        self.assertEqual([p["id"] for p in result["items"]], ["active", "ordinary"])
        self.assertEqual([p["featured"] for p in result["items"]], [True, False])
        self.assertNotIn("_id", result["items"][0])
        self.assertNotIn("effective_featured", result["items"][0])

    async def test_expired_loses_priority(self):
        await self.fixtures()
        await self.add("expired", True, T-timedelta(seconds=1), age=5)
        await self.add("ordinary")
        result = await self.search()
        self.assertEqual([p["id"] for p in result["items"]], ["ordinary", "expired"])
        self.assertFalse(result["items"][1]["featured"])

    async def test_ordinary_order_and_tie_breaker(self):
        await self.fixtures()
        await self.add("z")
        await self.add("a")
        await self.add("old", age=1)
        self.assertEqual([p["id"] for p in (await self.search())["items"]], ["a", "z", "old"])

    async def test_price_sorts_unchanged(self):
        await self.fixtures()
        await self.add("cheap", price=10)
        await self.add("featured", True, T+timedelta(days=1), price=20)
        await self.add("expensive", True, T, price=30)
        for sort, expected in [("price_asc", ["cheap", "featured", "expensive"]),
                               ("price_desc", ["expensive", "featured", "cheap"])]:
            result = await self.search("sort="+sort)
            self.assertEqual([p["id"] for p in result["items"]], expected)
            self.assertFalse(next(p for p in result["items"] if p["id"] == "expensive")["featured"])

    async def test_exact_boundary_and_just_before(self):
        await self.fixtures()
        await self.add("boundary", True, T)
        await self.add("active", True, T+timedelta(milliseconds=1), age=2)
        result = await self.search()
        self.assertEqual([(p["id"], p["featured"]) for p in result["items"]], [("active", True), ("boundary", False)])

    async def test_pagination_and_total(self):
        await self.fixtures()
        await self.add("expired", True, T, age=3)
        await self.add("ordinary")
        await self.add("active", True, T+timedelta(days=1), age=10)
        for page, ident in enumerate(["active", "ordinary", "expired"], 1):
            result = await self.search(f"limit=1&page={page}")
            self.assertEqual([p["id"] for p in result["items"]], [ident])
            self.assertEqual(result["total"], 3)
        self.assertEqual((await self.search("limit=1&page=4"))["items"], [])

    async def test_missing_null_expiry_compatibility(self):
        await self.fixtures()
        await self.add("missing", True, age=2)
        await self.add("null", True, None, age=1)
        await self.add("ordinary")
        result = await self.search()
        self.assertEqual([p["id"] for p in result["items"]], ["null", "missing", "ordinary"])
        self.assertTrue(all(p["featured"] for p in result["items"][:2]))

    async def test_malformed_expiry_fails_closed(self):
        await self.fixtures()
        for ident, value in [("string", "2099-01-01"), ("number", 999), ("object", {}), ("array", [])]:
            await self.add(ident, True, value)
        self.assertTrue(all(not p["featured"] for p in (await self.search())["items"]))
        docs = await f.extras.seo_listings(self.template["locality_id"])
        self.assertTrue(all(not p["featured"] for p in docs))

    async def test_naive_and_offset_datetimes(self):
        await self.fixtures()
        future = T+timedelta(seconds=1)
        for ident, expiry in [("naive", future.replace(tzinfo=None)),
                              ("offset", future.astimezone(timezone(timedelta(hours=5, minutes=30))))]:
            self.assertTrue(effective_featured({"featured": True, "featured_until": expiry}, T))
            await self.add(ident, True, expiry)
        self.assertTrue(all(p["featured"] for p in (await self.search())["items"]))
        self.assertFalse(effective_featured({"featured": True, "featured_until": T.replace(tzinfo=None)}, T))

    async def test_locality_top_50_and_badges(self):
        await self.fixtures()
        await self.add("ACTIVE-FIXTURE", True, T+timedelta(days=1), age=100)
        for i in range(50):
            await self.add(f"expired-{i}", True, T, age=i)
        docs = await f.extras.seo_listings(self.template["locality_id"])
        self.assertEqual(len(docs), 50)
        self.assertEqual(docs[0]["id"], "ACTIVE-FIXTURE")
        self.assertEqual(sum(p["featured"] for p in docs), 1)
        loc = self.db.raw.localities.find_one({"id": self.template["locality_id"]})
        city = self.db.raw.cities.find_one({"id": self.template["city_id"]})
        r = await self.api.get(f"/api/l/{city['slug']}/{loc['slug']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.text.count("⭐ Featured"), 1)

    async def test_filters_and_visibility_preserved(self):
        await self.fixtures()
        await self.add("buy", purpose="buy", price=100)
        await self.add("rent", True, purpose="rent", price=200)
        await self.add("pending", True, listing_status="pending_review", purpose="buy")
        result = await self.search("purpose=buy&min_price=50&max_price=150")
        self.assertEqual([p["id"] for p in result["items"]], ["buy"])
        self.assertEqual(result["total"], 1)

    async def test_reads_never_mutate_records(self):
        await self.fixtures()
        await self.add("expired", True, T)
        before = list(self.db.raw.properties.find())
        await self.search()
        await self.search("sort=price_asc")
        await self.api.get("/api/properties/expired")
        await f.extras.seo_listings(self.template["locality_id"])
        self.assertEqual(list(self.db.raw.properties.find()), before)

    async def test_one_cutoff_for_search(self):
        await self.fixtures()
        await self.add("active", True, T+timedelta(milliseconds=1))
        self.clock.stop()
        with patch.object(f.server, "now", side_effect=[T]) as clock:
            result = await self.search()
            self.assertTrue(result["items"][0]["featured"])
            clock.assert_called_once()

    async def test_renewal_priority_and_duplicate_fulfillment(self):
        await self.fixtures()
        await self.add("expired", True, T, age=5)
        await self.add("ordinary")
        order = {"id": "renewal", "property_id": "expired", "status": "created", "duration_days": 7}
        await self.db.payment_orders.insert_one(order)
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def with_transaction(self, callback): return await callback(self)
        class Client:
            async def start_session(self): return Session()
        self.db.client = Client()
        with patch.object(f.marketplace, "now", return_value=T):
            first = await f.marketplace.fulfil(order, "mock-payment", "test")
            second = await f.marketplace.fulfil(order, "mock-payment", "test")
        self.assertEqual(first["featured_until"], (T+timedelta(days=7)))
        self.assertEqual(second["featured_until"], first["featured_until"])
        self.assertEqual((await self.search())["items"][0]["id"], "expired")
