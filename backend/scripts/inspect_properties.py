"""Read-only diagnosis. Never prints connection strings, tokens, or user data."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = None
    try:
        client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=8000,
                             connectTimeoutMS=8000, socketTimeoutMS=8000)
        db = client[os.environ["DB_NAME"]]
        client.admin.command("ping")
        city = db.cities.find_one({"slug": "ujjain"}, {"_id": 0, "id": 1, "is_active": 1})
        report = {
            "database": db.name, "connection": "ok", "city": city,
            "demo_visibility": os.getenv("SEED_DEMO_LISTINGS", "false"),
            "demo_total": db.properties.count_documents({"is_demo": True}),
            "demo_statuses": list(db.properties.aggregate([
                {"$match": {"is_demo": True}},
                {"$group": {"_id": {"status": "$listing_status", "purpose": "$purpose", "city": "$city_id"}, "count": {"$sum": 1}}}
            ])),
            "active_total": db.properties.count_documents({"listing_status": "active"}),
            "last_seed": db.seed_reports.find_one({}, {"_id": 0, "inserted": 1, "skipped_duplicates": 1,
                                                       "unresolved_localities": 1}, sort=[("ran_at", -1)]),
        }
        print(json.dumps(report, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"connection": "failed", "error_type": type(exc).__name__,
                          "hint": "Check Atlas network access, DNS, database user and local configuration privately."}))
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
