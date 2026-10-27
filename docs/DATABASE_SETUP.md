# LANDVILLA — Database Setup (MongoDB)

## 1. Which database and why
LANDVILLA uses **MongoDB** through **Motor** (async driver, no ORM). This was checked in `backend/server.py` (`AsyncIOMotorClient(MONGO_URL)[DB_NAME]`).
It is not PostgreSQL. Do not swap databases without a migration plan. Preview server version: MongoDB 7.0.

Collections created by the code: `cities, zones, localities, property_categories, property_types, amenities, listing_statuses,
verification_statuses, featured_plans, app_settings, schema_migrations, seed_reports` (reference data) and
`users, user_sessions, properties, saved, enquiries, contact_access_logs, files, broker_profiles, payment_orders,
payment_webhook_events, abuse_reports, blocks, deletion_requests, commission_agreements, audit_logs` (app data).

## 2. Options
| Option | Use for | Cost |
|---|---|---|
| **Local MongoDB Community 7** on Windows | Development (recommended to start) | Free |
| **MongoDB Atlas M0** (free, 512 MB) in region Mumbai `ap-south-1` | Shared dev or staging. Not for production | Free |
| **Atlas Flex or M10** with backups | Production | Paid. Needs your approval |

## 3A. Local MongoDB (Windows)
```powershell
winget install MongoDB.Server          # installs and starts the "MongoDB" Windows service
winget install MongoDB.Shell           # mongosh
winget install MongoDB.DatabaseTools   # mongodump / mongorestore
Get-Service MongoDB                    # expected: Status Running
mongosh --eval "db.runCommand({ping:1})"   # expected: { ok: 1 }
```
In `backend\.env`:
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=landvilla_dev
```
By default local MongoDB only listens on 127.0.0.1 without a password. That's fine for development; don't expose port 27017 to your network.

## 3B. MongoDB Atlas (hosted)
1. Go to cloud.mongodb.com and create an Organisation (your company) → Project "LANDVILLA" → Create cluster (M0 for dev, region Mumbai).
2. **Database Access** → Add user `landvilla_app`, password authentication, role *Read and write to any database*, or a custom role limited to `landvilla`.
3. **Network Access** → add your current IP (dev) or your backend host's outbound IPs (prod). Avoid `0.0.0.0/0` in production.
4. **Connect → Drivers → Python** and copy the connection string:
   `mongodb+srv://landvilla_app:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority&appName=landvilla`
   TLS is always on with `mongodb+srv`. If the password has `@ : / ?`, URL-encode it.
5. Put it in `backend\.env` as `MONGO_URL=...` and set `DB_NAME=landvilla`. Never commit it.

## 4. Initialise collections and indexes
There is no separate migration tool. `seed.py` handles this. It runs **automatically every time the backend starts**, is safe to re-run (no duplicates), and records its version in `schema_migrations` (`001_indexes`).
Manual run (from `backend\`, with the venv active):
```powershell
python seed.py           # reference data + indexes
python seed.py --demo    # + 20 fictional demo listings (DEV ONLY)
```
Expected: a JSON report with `inserted` and `skipped_duplicates` counts.

## 5. Create a development admin
Option A (recommended): put your Google email in `ADMIN_EMAILS`, restart the backend and sign in. You get the `admin` role.
Option B (dev DB only, after you've signed in once):
```powershell
mongosh "mongodb://localhost:27017/landvilla_dev" --eval 'db.users.updateOne({email:"you@example.com"},{$set:{role:"admin"}})'
```
Option C (automated tests only): `SEED_TEST_SESSIONS=true` creates test users (buyer, admin, owner, broker) with fixed tokens
(`test_session_admin_landvilla` and others). **These tokens are public knowledge, so never enable this on a reachable or production server.**

## 6. Verify read/write
```powershell
cd backend; .\.venv\Scripts\activate
python scripts\health_check.py
```
Expected lines: `[PASS] MongoDB connect + read/write: ping ok, read/write ok, localities=32 ...` and `RESULT: ALL REQUIRED CHECKS PASSED`.
Manual check: `mongosh "mongodb://localhost:27017/landvilla_dev" --eval "db.getCollectionNames()"`.

## 7. Import existing data
Get a dump of the Emergent production DB from Emergent support (see `DATABASE_MIGRATION.md`). Restore it **only** into a secured database (local, disk-encrypted, or Atlas with a user and IP allow-list):
```powershell
mongorestore --uri="mongodb://localhost:27017" --gzip --archive=backups\<db>-<ts>\dump.archive.gz --nsFrom="<srcdb>.*" --nsTo="landvilla_dev.*"
python scripts\db_verify.py backups\<db>-<ts>\counts.json
```
Do not load real customer data onto a laptop unless that's necessary and authorised.

## 8. Backup & restore
```powershell
cd backend
python scripts\db_export.py                 # -> backups\<db>-<UTC>\dump.archive.gz + counts.json (git-ignored)
python scripts\db_export.py --counts-only   # quick inventory
mongorestore --uri="<target>" --gzip --archive=<file> --nsFrom="<db>.*" --nsTo="<newdb>.*"
python scripts\db_verify.py <counts.json>    # row-count comparison + index list + demo/test classification
```
Atlas paid tiers also offer automatic snapshots. Turn them on in production.

## 9. Demo vs real data
Demo listings have `is_demo:true`. Test users have IDs `user_test*`. With `SEED_*=false` the backend hides demo listings and deletes test users and sessions at startup (checked in `server.py`).
