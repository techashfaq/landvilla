"""Explicit additive indexes only. Default prints a plan without importing the app."""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

EXTRA = [
    ("files", "id", {"unique": True}),
    ("broker_profiles", "user_id", {"unique": True}),
    ("featured_plans", "slug", {"unique": True}),
    ("payment_orders", "id", {"unique": True}),
    ("payment_orders", "razorpay_order_id", {"unique": True, "partialFilterExpression": {"razorpay_order_id": {"$type": "string"}}}),
    ("payment_webhook_events", "event_id", {"unique": True}),
    ("properties", "owner_user_id", {}),
    ("properties", "photo_hashes", {}),
    ("enquiries", [("lister_user_id", 1), ("created_at", -1)], {}),
]

async def apply(env):
    from motor.motor_asyncio import AsyncIOMotorClient
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # seed.py defines index-only functions; never call seed_all or run_migrations.
    from seed import m001_indexes, m002_identity_indexes
    client = AsyncIOMotorClient(env["MONGO_URL"], serverSelectionTimeoutMS=8000)
    try:
        db = client[env["DB_NAME"]]
        # Refuse legacy non-partial uniqueness BEFORE changing any indexes.
        indexes = await db.payment_orders.index_information()
        for index in indexes.values():
            if index.get("key") == [("razorpay_order_id", 1)] and index.get("partialFilterExpression") != {"razorpay_order_id": {"$type": "string"}}:
                print("BLOCKED: legacy payment index needs separately approved replacement")
                return 2
        await m001_indexes(db)
        await m002_identity_indexes(db)
        for collection, key, options in EXTRA:
            await db[collection].create_index(key, **options)
        for version in ("001_indexes", "002_identity_indexes", "003_release_indexes"):
            await db.schema_migrations.update_one({"version": version}, {"$setOnInsert": {"applied_at": datetime.now(timezone.utc)}}, upsert=True)
        print("PASS: release indexes provisioned")
        return 0
    except Exception:
        print("BLOCKED: index provisioning failed; inspect conflicts privately; no records or indexes were deleted")
        return 1
    finally:
        client.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-database")
    args = parser.parse_args()
    if not args.apply:
        print("PLAN: base + identity + release indexes; no seed, drop, reset or connection")
        return 0
    if not os.getenv("MONGO_URL") or not os.getenv("DB_NAME") or args.confirm_database != os.getenv("DB_NAME"):
        print("BLOCKED: explicit environment and matching database confirmation required")
        return 2
    return asyncio.run(apply(dict(os.environ)))

if __name__ == "__main__":
    raise SystemExit(main())
