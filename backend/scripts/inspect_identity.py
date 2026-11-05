"""Read-only identity preflight: counts and index names, never contact values or secrets."""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from database_diagnostics import error_category


async def main():
    client = None
    try:
        import server
        from identity import missing_identity_indexes
        client = server.client
        await server.db.command("ping")
        duplicates = {}
        for field in ("mobile", "google_sub"):
            rows = await server.db.users.aggregate([
                {"$match": {field: {"$type": "string"}}},
                {"$group": {"_id": "$" + field, "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}},
                {"$count": "groups"},
            ], maxTimeMS=5000).to_list(1)
            duplicates[field] = rows[0]["groups"] if rows else 0
        print(json.dumps({"connection": "ok", "database": server.db.name,
            "identity_enabled": os.getenv("IDENTITY_ENABLED", "false").lower() == "true",
            "migration_recorded": bool(await server.db.schema_migrations.find_one({"version": "002_identity_indexes"})),
            "missing_indexes": await missing_identity_indexes(server.db), "duplicate_groups": duplicates}))
        return 0
    except Exception as exc:
        print(json.dumps({"connection": "unavailable", "error_type": type(exc).__name__,
            "error_category": error_category(exc),
            "hint": "Check configuration and Atlas access privately. No changes were made."}))
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
