"""Idempotent migrations + seed for LANDVILLA.

Run standalone:  python seed.py            (reference data only)
                 python seed.py --demo     (also fictional demo listings - dev only)
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

import seed_data as D

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")


def now():
    return datetime.now(timezone.utc)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------- migrations
async def m001_indexes(db):
    await db.cities.create_index("slug", unique=True)
    await db.zones.create_index([("city_id", ASCENDING), ("slug", ASCENDING)], unique=True)
    await db.localities.create_index([("city_id", ASCENDING), ("slug", ASCENDING)], unique=True)
    await db.localities.create_index("id", unique=True)
    await db.localities.create_index("search_keys")
    await db.property_categories.create_index("slug", unique=True)
    await db.property_types.create_index("slug", unique=True)
    await db.amenities.create_index("slug", unique=True)
    await db.listing_statuses.create_index("slug", unique=True)
    await db.verification_statuses.create_index("slug", unique=True)
    await db.properties.create_index("id", unique=True)
    await db.properties.create_index("demo_key", unique=True, partialFilterExpression={"demo_key": {"$type": "string"}})
    await db.properties.create_index([("locality_id", ASCENDING), ("purpose", ASCENDING), ("listing_status", ASCENDING)])
    await db.properties.create_index([("created_at", DESCENDING)])
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.user_sessions.create_index("user_id")
    await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.enquiries.create_index("id", unique=True)
    await db.enquiries.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.saved.create_index([("user_id", ASCENDING), ("property_id", ASCENDING)], unique=True)


MIGRATIONS = [("001_indexes", m001_indexes)]


async def run_migrations(db):
    applied = []
    for version, fn in MIGRATIONS:
        if await db.schema_migrations.find_one({"version": version}):
            continue
        await fn(db)
        await db.schema_migrations.insert_one({"version": version, "applied_at": now()})
        applied.append(version)
    return applied


# ---------------------------------------------------------------- seeding
async def _upsert_simple(db, coll, items, report_key, report, extra=None):
    ins = skip = 0
    for i, item in enumerate(items):
        if await db[coll].find_one({"slug": item["slug"]}):
            skip += 1
            continue
        doc = {**item, "id": new_id(coll[:4]), "is_active": True, "order": item.get("order", i + 1), "created_at": now()}
        if extra:
            doc.update(extra)
        await db[coll].insert_one(doc)
        ins += 1
    report["inserted"][report_key] = ins
    report["skipped_duplicates"][report_key] = skip


async def seed_all(db, include_demo: bool = False) -> dict:
    report = {"ran_at": now().isoformat(), "migrations_applied": [], "inserted": {}, "skipped_duplicates": {},
              "candidate_resolution": [], "unresolved_localities": [], "zone_unresolved": [], "notes": []}
    report["migrations_applied"] = await run_migrations(db)

    # City
    city = await db.cities.find_one({"slug": D.CITY["slug"]})
    if city:
        report["skipped_duplicates"]["cities"] = 1
        report["inserted"]["cities"] = 0
    else:
        city = {**D.CITY, "id": new_id("city"), "created_at": now()}
        await db.cities.insert_one(city)
        report["inserted"]["cities"] = 1
        report["skipped_duplicates"]["cities"] = 0
    city_id = city["id"]

    # Zones
    ins = skip = 0
    zone_ids = {}
    for z in D.ZONES:
        ex = await db.zones.find_one({"city_id": city_id, "slug": z["slug"]})
        if ex:
            skip += 1
            zone_ids[z["slug"]] = ex["id"]
            continue
        doc = {**z, "id": new_id("zone"), "city_id": city_id, "is_active": True, "created_at": now()}
        await db.zones.insert_one(doc)
        zone_ids[z["slug"]] = doc["id"]
        ins += 1
    report["inserted"]["zones"], report["skipped_duplicates"]["zones"] = ins, skip

    # Localities (canonical)
    ins = skip = 0
    loc_ids = {}
    for loc in D.LOCALITIES:
        ex = await db.localities.find_one({"city_id": city_id, "slug": loc["slug"]})
        if ex:
            skip += 1
            loc_ids[loc["slug"]] = ex["id"]
            continue
        keys = sorted({norm(loc["name_en"]), loc["name_hi"], *[norm(a) for a in loc["aliases"]]})
        doc = {
            "id": new_id("loc"), "city_id": city_id, "slug": loc["slug"],
            "name_en": loc["name_en"], "name_hi": loc["name_hi"], "aliases": loc["aliases"],
            "search_keys": keys,
            "zone_id": zone_ids.get(loc["zone"]) if loc["zone"] else None,
            "zone_assignment": "tentative" if loc["zone"] else "unassigned",
            "parent_id": None,
            "is_active": True, "source": "founder_provided_list",
            "verification_status": "unverified", "last_verified_at": None, "verified_by": None,
            "latitude": None, "longitude": None, "geocode_source": None,
            "merged_into": None, "created_at": now(), "updated_at": now(),
        }
        await db.localities.insert_one(doc)
        loc_ids[loc["slug"]] = doc["id"]
        ins += 1
        if not loc["zone"]:
            report["zone_unresolved"].append(loc["name_en"])
    # resolve parents
    for loc in D.LOCALITIES:
        if loc.get("parent") and loc["parent"] in loc_ids:
            await db.localities.update_one({"id": loc_ids[loc["slug"]], "parent_id": None},
                                           {"$set": {"parent_id": loc_ids[loc["parent"]]}})
    if not report["zone_unresolved"]:
        report["zone_unresolved"] = [doc_["name_en"] async for doc_ in db.localities.find({"city_id": city_id, "zone_id": None, "is_active": True}, {"_id": 0, "name_en": 1})]
    report["inserted"]["localities"], report["skipped_duplicates"]["localities"] = ins, skip

    # Candidate resolution report (dedupe raw names -> canonical)
    seen = {}
    for raw in D.LOCALITY_CANDIDATES:
        n = norm(raw)
        hit = await db.localities.find_one({"city_id": city_id, "search_keys": n}, {"_id": 0, "slug": 1})
        if not hit:
            report["unresolved_localities"].append(raw)
            continue
        status = "duplicate_of_earlier_candidate" if hit["slug"] in seen else "resolved"
        report["candidate_resolution"].append({"candidate": raw, "resolved_to": hit["slug"], "status": status})
        seen[hit["slug"]] = raw

    # Lookups
    await _upsert_simple(db, "property_categories", D.CATEGORIES, "property_categories", report)
    await _upsert_simple(db, "property_types", D.PROPERTY_TYPES, "property_types", report)
    await _upsert_simple(db, "amenities", D.AMENITIES, "amenities", report)
    await _upsert_simple(db, "listing_statuses", D.LISTING_STATUSES, "listing_statuses", report)
    await _upsert_simple(db, "verification_statuses", D.VERIFICATION_STATUSES, "verification_statuses", report)

    # Demo listings (development only)
    if include_demo:
        ins = skip = 0
        for p in D.DEMO_LISTINGS:
            if await db.properties.find_one({"demo_key": p["demo_key"]}):
                skip += 1
                continue
            loc_id = loc_ids.get(p["locality"])
            if not loc_id:
                report["notes"].append(f"demo {p['demo_key']} skipped: unknown locality {p['locality']}")
                continue
            doc = {
                "id": new_id("prop"), "demo_key": p["demo_key"], "is_demo": True,
                "title_en": p["title_en"], "title_hi": p["title_hi"],
                "description_en": "FICTIONAL DEMO LISTING for development and testing only. Not a real property, owner, price or availability.",
                "description_hi": "यह केवल विकास और परीक्षण के लिए काल्पनिक डेमो लिस्टिंग है। यह वास्तविक संपत्ति, मालिक, कीमत या उपलब्धता नहीं है।",
                "purpose": p["purpose"], "segment": p["segment"], "type": p["type"],
                "city_id": city_id, "locality_id": loc_id,
                "price": p["price"], "bhk": p["bhk"], "bathrooms": p["bathrooms"], "area_sqft": p["area_sqft"],
                "furnishing": p["furnishing"], "amenities": p["amenities"], "images": p["images"],
                "posted_by_role": "demo", "posted_by_name": "Demo Listing (Fictional)",
                "listing_status": "active", "verification_status": "unverified",
                "featured": p["demo_key"] in ("demo-003", "demo-010", "demo-014"),
                "created_at": now(), "updated_at": now(),
            }
            await db.properties.insert_one(doc)
            ins += 1
        report["inserted"]["demo_listings"], report["skipped_duplicates"]["demo_listings"] = ins, skip
    else:
        report["notes"].append("Demo listings NOT seeded (SEED_DEMO_LISTINGS is not true).")

    await db.seed_reports.insert_one({**report})
    report.pop("_id", None)
    return report


async def _main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    import json
    rep = await seed_all(db, include_demo="--demo" in sys.argv)
    print(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
    client.close()


if __name__ == "__main__":
    asyncio.run(_main())
