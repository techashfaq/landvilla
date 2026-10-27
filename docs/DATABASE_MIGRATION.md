# LANDVILLA — Database Export & Migration (MongoDB)

**Engine:** MongoDB (the preview server runs 7.0.45), accessed with Motor/PyMongo. This project does **not** use PostgreSQL,
so `pg_dump` does not apply. Use `mongodump`/`mongorestore` instead.
**Schema mechanism:** there is no ORM. `backend/seed.py` creates all indexes (unique and partial) and reference data at startup,
and records versions in `schema_migrations` (currently `001_indexes`). Restoring a dump also restores the indexes.

## 1. Two separate databases
| DB | Where | Contents | Access from this workspace |
|---|---|---|---|
| Preview | Emergent workspace container (local MongoDB) | Demo listings (20, all `is_demo:true`), 4 test sessions, reference data. ~305 MB on disk including MongoDB system files | Yes (verified counts below) |
| Production | Emergent deployment (managed MongoDB, created when you click *Publish*) | Real users, enquiries, payments, if any | **No.** Its connection string is injected only in the deployed app |

Preview collection counts (verified 2026, read-only): localities 32, properties 20 (all demo), enquiries 17,
files 81, users 4, user_sessions 4, featured_plans 4, payment_webhook_events 33, payment_orders 0, audit_logs 478.
**The preview DB contains test data only. Do not migrate it into production.**

## 2. Export production (requires your action)
Emergent does not expose the production connection string inside this workspace. Supported paths:
1. Ask Emergent support (support@emergent.sh) for a **production database export** (mongodump archive) or
   a time-limited read-only connection string for the `ujjainestate` deployment, delivered securely.
2. When you have the URI, run the export only on a trusted, disk-encrypted (BitLocker) machine:
```powershell
cd backend
# put the PRODUCTION URI temporarily in a separate env file, never committed:
$env:MONGO_URL = Read-Host "Mongo URI" ; $env:DB_NAME = "<prod db name>"
python scripts\db_export.py            # -> backups\<db>-<UTC timestamp>\dump.archive.gz + counts.json
Remove-Item Env:MONGO_URL
```
The script prints no credentials and only reads the source. `backups/` is git-ignored.

## 3. Restore into a database you control
Recommended target: MongoDB Atlas (your company org) with an M10+ cluster in the Mumbai (ap-south-1) region. This is paid, so get approval first.
Set up a dedicated DB user with least privilege, TLS on, an IP allow-list, and backups enabled.
```powershell
mongorestore --uri="<target-uri>" --gzip --archive=backups\<db>-<ts>\dump.archive.gz `
  --nsFrom="<prod db>.*" --nsTo="landvilla.*" --drop:false
```
Do not use `--drop` against a database that already holds data you need.

## 4. Verify
```powershell
$env:MONGO_URL="<target-uri>"; $env:DB_NAME="landvilla"
python scripts\db_verify.py backups\<db>-<ts>\counts.json   # row counts, indexes, demo/test classification
```
Expected: every collection `OK`, real properties > 0, `test users` = 0 and `test sessions` = 0 in production.
Spot-check manually: `db.users.findOne()`, `db.payment_orders.find({status:"paid"}).count()` equals the paid orders on the Razorpay Dashboard.

## 5. Demo vs real data
- Demo listings have `is_demo: true` / `demo_key: "demo-NNN"`. Test users have IDs `user_test*` and tokens `test_session_*`.
- With `SEED_TEST_SESSIONS=false`, test users and sessions are deleted automatically on startup. With `SEED_DEMO_LISTINGS=false`, demo listings are hidden (`demo_hidden`).
- To remove demo listings permanently from production after you approve: `db.properties.deleteMany({is_demo:true})`. This is irreversible. Take a backup first.

## 6. Files (photos/documents)
DB records in `files` point to Emergent Object Storage paths. The bytes are **not** in the Mongo dump.
See HANDOVER_REPORT §E for the storage migration.
