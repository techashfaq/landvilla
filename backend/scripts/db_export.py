"""LANDVILLA – MongoDB export helper (safe, read-only on the source).

Usage (from backend/):
    python scripts/db_export.py                 # full dump of DB_NAME -> backups/<db>-<timestamp>/
    python scripts/db_export.py --counts-only   # just print per-collection document counts

Reads MONGO_URL / DB_NAME from backend/.env (or the environment). Never prints the connection
string. Requires the MongoDB Database Tools (mongodump) on PATH for a full dump.
Output contains personal data – store it encrypted, never commit it, never upload it publicly.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def counts(db) -> dict:
    return {c: db[c].estimated_document_count() for c in sorted(db.list_collection_names())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--counts-only", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "backups"))
    a = ap.parse_args()

    url, name = os.environ["MONGO_URL"], os.environ["DB_NAME"]
    db = MongoClient(url, serverSelectionTimeoutMS=10000)[name]
    c = counts(db)
    print(json.dumps({"db": name, "collections": c}, indent=2))
    if a.counts_only:
        return

    if not shutil.which("mongodump"):
        sys.exit("mongodump not found. Install MongoDB Database Tools and retry.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(a.out) / f"{name}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    # URI passed via --uri argument is not echoed; output goes to an archive with gzip.
    r = subprocess.run(["mongodump", f"--uri={url}", f"--db={name}", f"--archive={out / 'dump.archive.gz'}", "--gzip"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("mongodump failed (details suppressed to avoid leaking the URI). Check connectivity/credentials.")
    (out / "counts.json").write_text(json.dumps(c, indent=2))
    print(f"Dump written to {out}")


if __name__ == "__main__":
    main()
