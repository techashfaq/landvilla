"""Tests for idempotent seeding, duplicate prevention and locality filtering.
Run: cd /app/backend && python -m pytest tests/test_seed.py -q
Uses an isolated database (DB_NAME + '_pytest') that is dropped after the run.
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import seed_data as D  # noqa: E402
from seed import seed_all  # noqa: E402

TEST_DB = os.environ["DB_NAME"] + "_pytest"


@pytest.fixture(scope="module")
def db():
    loop = asyncio.new_event_loop()
    client = AsyncIOMotorClient(os.environ["MONGO_URL"], io_loop=loop)
    database = client[TEST_DB]
    loop.run_until_complete(client.drop_database(TEST_DB))
    yield loop, database
    loop.run_until_complete(client.drop_database(TEST_DB))
    client.close()
    loop.close()


def run(loop, coro):
    return loop.run_until_complete(coro)


def test_seed_is_idempotent(db):
    loop, database = db
    r1 = run(loop, seed_all(database, include_demo=True))
    assert r1["inserted"]["localities"] == len(D.LOCALITIES)
    assert r1["inserted"]["demo_listings"] == len(D.DEMO_LISTINGS)
    r2 = run(loop, seed_all(database, include_demo=True))
    assert r2["inserted"]["localities"] == 0
    assert r2["skipped_duplicates"]["localities"] == len(D.LOCALITIES)
    assert r2["inserted"]["demo_listings"] == 0
    assert run(loop, database.localities.count_documents({})) == len(D.LOCALITIES)
    assert run(loop, database.properties.count_documents({})) == len(D.DEMO_LISTINGS)
    assert run(loop, database.property_categories.count_documents({})) == len(D.CATEGORIES)


def test_aliases_resolve_not_duplicate(db):
    loop, database = db
    rep = run(loop, seed_all(database, include_demo=False))
    res = {c["candidate"]: c for c in rep["candidate_resolution"]}
    assert res["Free Ganj"]["resolved_to"] == "freeganj"
    assert res["Free Ganj"]["status"] == "duplicate_of_earlier_candidate"
    assert res["Mahakal area"]["resolved_to"] == "mahakal-area"
    assert res["Mahakal Area"]["status"] == "duplicate_of_earlier_candidate"
    assert rep["unresolved_localities"] == []


def test_unique_constraint_blocks_duplicate_slug(db):
    loop, database = db
    city = run(loop, database.cities.find_one({"slug": "ujjain"}))
    from pymongo.errors import DuplicateKeyError
    with pytest.raises(DuplicateKeyError):
        run(loop, database.localities.insert_one({"id": "loc_dup", "city_id": city["id"], "slug": "freeganj"}))


def test_no_fabricated_geo_or_verification(db):
    loop, database = db
    bad = run(loop, database.localities.count_documents({"$or": [{"latitude": {"$ne": None}}, {"verification_status": {"$ne": "unverified"}}]}))
    assert bad == 0
    assert run(loop, database.properties.count_documents({"is_demo": {"$ne": True}})) == 0


def test_parent_relationship(db):
    loop, database = db
    parent = run(loop, database.localities.find_one({"slug": "rishi-nagar"}))
    child = run(loop, database.localities.find_one({"slug": "rishi-nagar-extension"}))
    assert child["parent_id"] == parent["id"]


def test_locality_filtering_uses_db_records(db):
    loop, database = db
    loc = run(loop, database.localities.find_one({"slug": "university-road"}))
    props = run(loop, database.properties.find({"locality_id": loc["id"]}).to_list(100))
    expected = [p for p in D.DEMO_LISTINGS if p["locality"] == "university-road"]
    assert len(props) == len(expected) and len(props) > 0
