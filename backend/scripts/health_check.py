"""LANDVILLA – backend + database health check (read-only except one temporary test document).

Usage (from backend/, venv active):
    python scripts/health_check.py                       # uses http://localhost:8001
    python scripts/health_check.py --url https://api.example.com
    python scripts/health_check.py --token <session token>   # also checks auth + role (optional)

Exit code 0 = all required checks passed. Never prints secrets or connection strings.
"""
import argparse
import os
import sys
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
REQUIRED_COLLECTIONS = ["cities", "zones", "localities", "property_categories", "property_types", "amenities",
                        "featured_plans", "schema_migrations"]
results = []


def check(name, fn, required=True):
    try:
        detail = fn()
        results.append((True, name, detail or ""))
    except Exception as e:  # noqa: BLE001
        results.append((False if required else None, name, str(e)[:200]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("HEALTH_URL", "http://localhost:8001"))
    ap.add_argument("--token", default=os.environ.get("HEALTH_TOKEN"))
    ap.add_argument("--skip-db", action="store_true", help="skip direct DB checks (e.g. checking a remote server)")
    a = ap.parse_args()
    base = a.url.rstrip("/")

    # ---- environment
    def env_check():
        missing = [k for k in ("MONGO_URL", "DB_NAME") if not os.environ.get(k)]
        if missing:
            raise RuntimeError(f"missing in backend/.env: {missing}")
        flags = {k: os.environ.get(k, "false") for k in ("SEED_DEMO_LISTINGS", "SEED_TEST_SESSIONS")}
        rzp = "set" if os.environ.get("RAZORPAY_KEY_ID") and os.environ.get("RAZORPAY_KEY_SECRET") else "not set"
        return f"flags={flags} razorpay_keys={rzp} webhook_secret={'set' if os.environ.get('RAZORPAY_WEBHOOK_SECRET') else 'not set'}"
    check("backend/.env variables", env_check)

    # ---- database
    if not a.skip_db:
        def db_check():
            db = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)[os.environ["DB_NAME"]]
            db.command("ping")
            names = set(db.list_collection_names())
            miss = [c for c in REQUIRED_COLLECTIONS if c not in names]
            if miss:
                raise RuntimeError(f"collections missing {miss} – start the backend once (it seeds on startup) or run: python seed.py")
            tmp = f"healthcheck_{uuid.uuid4().hex[:8]}"
            db.healthcheck.insert_one({"_id": tmp})
            assert db.healthcheck.find_one({"_id": tmp})
            db.healthcheck.delete_one({"_id": tmp})
            return f"ping ok, read/write ok, localities={db.localities.count_documents({})}, properties={db.properties.count_documents({})}"
        check("MongoDB connect + read/write", db_check)

    # ---- API
    def get(path, **kw):
        r = requests.get(base + path, timeout=15, **kw)
        r.raise_for_status()
        return r

    check("GET /health", lambda: get("/health").text[:60])
    check("GET /api/meta (reference data)", lambda: f"localities={len(get('/api/meta').json().get('localities', []))}")

    def listings():
        j = get("/api/properties?limit=5").json()
        if j["items"]:
            pid = j["items"][0]["id"]
            d = get(f"/api/properties/{pid}").json()
            return f"total={j['total']}, detail ok: {str(d.get('title_en') or d.get('title') or pid)[:40]}"
        return f"total={j['total']} (no active listings – set SEED_DEMO_LISTINGS=true on a dev DB to see demo data)"
    check("Listings + property detail", listings)

    def plans():
        j = get("/api/featured-plans").json()
        return f"plans={len(j['items'])}, payments_configured={j['payments_configured']}, mode={j['mode']}"
    check("Featured plans / Razorpay config", plans)

    def unauth():
        r = requests.get(base + "/api/auth/me", timeout=15)
        if r.status_code != 401:
            raise RuntimeError(f"expected 401 without token, got {r.status_code}")
        r = requests.get(base + "/api/admin/stats", timeout=15)
        if r.status_code not in (401, 403):
            raise RuntimeError(f"admin endpoint not protected: {r.status_code}")
        return "401/403 enforced"
    check("Auth enforced on protected APIs", unauth)

    if a.token:
        def me():
            u = get("/api/auth/me", headers={"Authorization": f"Bearer {a.token}"}).json()
            return f"signed in as role={u.get('role')}"
        check("Session token valid (/api/auth/me)", me)

    def webhook():
        r = requests.post(base + "/api/payments/razorpay/webhook", data=b"{}", timeout=15)
        return {503: "route exists, RAZORPAY_WEBHOOK_SECRET not set", 400: "route exists, secret set (unsigned call rejected)"}.get(
            r.status_code, f"unexpected status {r.status_code}")
    check("Razorpay webhook route", webhook, required=False)

    ok = True
    for passed, name, detail in results:
        tag = {True: "PASS", False: "FAIL", None: "WARN"}[passed]
        ok &= passed is not False
        print(f"[{tag}] {name}: {detail}")
    print("\nRESULT:", "ALL REQUIRED CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
