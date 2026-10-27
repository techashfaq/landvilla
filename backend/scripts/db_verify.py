"""LANDVILLA – verify a restored database against counts.json from db_export.py.

Usage (from backend/, with backend/.env pointing at the TARGET database):
    python scripts/db_verify.py backups/<db>-<timestamp>/counts.json

Also reports demo vs real data so you can confirm test data was not carried into production.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main():
    expected = json.loads(Path(sys.argv[1]).read_text())
    db = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=10000)[os.environ["DB_NAME"]]
    ok = True
    for coll, n in expected.items():
        got = db[coll].count_documents({})
        flag = "OK " if got == n else "DIFF"
        ok &= got == n
        print(f"{flag} {coll:32s} expected={n:<8} actual={got}")
    print("\nIndexes:")
    for coll in sorted(db.list_collection_names()):
        print(f"  {coll}: {[i['name'] for i in db[coll].list_indexes()]}")
    print("\nData classification:")
    print("  demo properties   :", db.properties.count_documents({"is_demo": True}))
    print("  real properties   :", db.properties.count_documents({"is_demo": {"$ne": True}}))
    print("  test users        :", db.users.count_documents({"user_id": {"$regex": "^user_test"}}))
    print("  test sessions     :", db.user_sessions.count_documents({"session_token": {"$regex": "^test_session_"}}))
    print("  schema_migrations :", [m["version"] for m in db.schema_migrations.find({}, {"_id": 0, "version": 1})])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
