"""Explicit, development-only identity index application. Importing performs no I/O."""
import argparse
import asyncio
import os
from pathlib import Path


def configuration_allowed(env):
    # Missing/unknown environment is not implicitly development.
    return (env.get("APP_ENV", "").strip().lower() == "development"
            and env.get("DB_NAME") == "landvilla_dev"
            and bool(env.get("MONGO_URL", "").strip()))


async def apply_indexes(env, client_factory, migration, clock):
    if not configuration_allowed(env):
        print("identity_migration_configuration_refused")
        return 2
    client = None
    try:
        client = client_factory(env["MONGO_URL"], serverSelectionTimeoutMS=10000)
        db = client[env["DB_NAME"]]
        if db.name != "landvilla_dev":
            print("identity_migration_database_refused")
            return 2
        await db.command("ping")
        for field in ("mobile", "google_sub"):
            duplicates = await db.users.aggregate([
                {"$match": {field: {"$type": "string"}}},
                {"$group": {"_id": "$" + field, "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
                {"$count": "groups"},
            ], maxTimeMS=5000).to_list(1)
            if duplicates:
                print("identity_migration_duplicates_refused")
                return 2
        await migration(db)
        if not await db.schema_migrations.find_one({"version": "002_identity_indexes"}):
            await db.schema_migrations.insert_one({"version": "002_identity_indexes", "applied_at": clock()})
        print("identity_migration_completed")
        return 0
    except Exception:
        # No raw driver/provider text or traceback; partial index creation may require review.
        print("identity_migration_failed_review_required")
        return 1
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                print("identity_migration_close_failed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-database")
    args = parser.parse_args(argv)
    if not args.apply or args.confirm_database != "landvilla_dev":
        print("identity_migration_confirmation_required")
        return 2
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
        if not configuration_allowed(os.environ):
            print("identity_migration_configuration_refused")
            return 2
        from motor.motor_asyncio import AsyncIOMotorClient
        # Package import is resolved only during explicitly confirmed execution.
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from seed import m002_identity_indexes, now
        return asyncio.run(apply_indexes(os.environ, AsyncIOMotorClient, m002_identity_indexes, now))
    except Exception:
        print("identity_migration_failed_review_required")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
