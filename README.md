# LANDVILLA — Real Estate Marketplace (Ujjain first)

Buyers/tenants search and enquire. Owners and approved brokers post listings. Admins moderate.
Featured listings are paid through Razorpay.

## Guides
| Start here | [docs/COMPLETE_SETUP_GUIDE.md](docs/COMPLETE_SETUP_GUIDE.md): zero to app running on Android |
|---|---|
| Config & secrets | [docs/ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md) |
| Database | [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md) · [docs/DATABASE_MIGRATION.md](docs/DATABASE_MIGRATION.md) |
| Android run/debug | [docs/ANDROID_RUN_AND_DEBUG.md](docs/ANDROID_RUN_AND_DEBUG.md) |
| Auth, storage, Razorpay | [docs/INTEGRATIONS_SETUP.md](docs/INTEGRATIONS_SETUP.md) |
| Build APK/AAB & Play | [docs/ANDROID_BUILD_AND_PLAY.md](docs/ANDROID_BUILD_AND_PLAY.md) |
| Self-hosting | [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) |
| Pass/fail checks | [docs/VERIFICATION_CHECKLIST.md](docs/VERIFICATION_CHECKLIST.md) |
| Ownership & security | [docs/HANDOVER_REPORT.md](docs/HANDOVER_REPORT.md) · [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md) |

## Quick start (Windows PowerShell)
```powershell
git clone -b dev https://github.com/techashfaq/landvilla.git C:\src\landvilla; cd C:\src\landvilla
Set-ExecutionPolicy -Scope Process Bypass; .\scripts\windows-setup.ps1      # venv, deps, .env files
notepad backend\.env; notepad frontend\.env                                  # see ENVIRONMENT_VARIABLES.md
.\scripts\check-config.ps1
# window 1:  cd backend; .\.venv\Scripts\activate; uvicorn server:app --host 0.0.0.0 --port 8001 --reload
# window 2:  .\scripts\health-check.ps1
# window 3:  cd frontend; yarn start --clear   (press a)
```

## 1. Architecture

| Layer | Technology (verified in code) |
|---|---|
| Mobile + web app | Expo SDK 58 (`expo@58.0.17`), React Native 0.88, React 19.3, expo-router (file-based routes), TypeScript, TanStack Query |
| Android project | **Expo managed / Continuous Native Generation.** No `android/` folder is committed. Run `npx expo prebuild` to generate it |
| Backend | Python 3.11, FastAPI 0.110, Uvicorn. Entry point: `backend/server.py` (`app`), plus routers in `marketplace.py` and `extras.py` |
| Database | **MongoDB 7** through Motor (async), with no ORM. Schema/indexes are created by code in `backend/seed.py` (`schema_migrations` collection) |
| Auth | Emergent-managed Google sign-in (`auth.emergentagent.com`). The backend stores sessions in `user_sessions` (7-day bearer token) |
| File storage | Emergent Object Storage (`INTEGRATION_PROXY_URL/objstore`). Metadata is in the `files` collection |
| Payments | Razorpay Orders + Checkout (WebView). The server verifies signatures and handles the `/api/payments/razorpay/webhook` webhook |
| Push / maps / SMS / email / analytics | **Not used** |

```
backend/   server.py (core, auth, properties, enquiries)  marketplace.py (uploads, listings, moderation,
           leads, payments)  extras.py (legal pages, deletion, reports/blocks, commissions, SEO, sitemap)
           seed.py + seed_data.py (idempotent reference data & indexes)  scripts/ (db export/verify)  tests/
frontend/  app/ (screens/routes)  src/ (api.ts, auth.tsx, i18n.tsx, theme.ts, components/)  assets/  app.json
docs/      handover documentation          scripts/windows-setup.ps1   safe Windows bootstrap
```

## 2. Prerequisites
Git, Node.js 20 LTS or newer (Node 24 was used in development), Yarn 1.22.22 (`corepack enable`), Python 3.11,
MongoDB 7 Community (or Atlas), and MongoDB Database Tools. For Android you also need Android Studio
with JDK 17 or the bundled JBR, plus SDK Platform 36/37, Build-Tools 37 and NDK 27.1.12297006.

## 3. Install & run locally
```bash
# backend
cd backend
python -m venv .venv && .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements-local.txt
copy .env.example .env                                  # then edit values
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# frontend
cd frontend
yarn install --frozen-lockfile
copy .env.example .env                                  # set EXPO_PUBLIC_BACKEND_URL
yarn start                                              # Expo dev server (press a for Android)
```
On startup the backend creates its indexes and loads the reference data (city, zones, localities, categories, plans) without duplicating anything.

## 4. Environment variables
See `backend/.env.example` and `frontend/.env.example`. **Never commit real `.env` files.**
In production, `SEED_DEMO_LISTINGS=false` and `SEED_TEST_SESSIONS=false` must be set.

## 5. Database
MongoDB does not need a separate migration tool. `seed.py` runs on startup and records applied versions in
the `schema_migrations` collection. To run it manually, use `python seed.py`, or `python seed.py --demo` to add fictional listings for development only.
For backup and restore, see `docs/DATABASE_MIGRATION.md` (`scripts/db_export.py`, `scripts/db_verify.py`).

## 6. Android
```bash
cd frontend
npx expo prebuild --platform android      # generates frontend/android (do not commit)
npx expo run:android                      # debug build on emulator/device
cd android && gradlew.bat bundleRelease   # signed AAB after configuring your upload key
```
Full steps are in `docs/ANDROID_BUILD_AND_PLAY.md`.

## 7. Testing
```bash
cd backend
# tests call a running backend; set SEED_TEST_SESSIONS=true ONLY on a dev database
pytest -n 0
```

## 8. Deployment
The current production deployment runs on Emergent. To self-host, run Uvicorn behind HTTPS (for example
Render/Railway/VM + Nginx) with a managed MongoDB, set the backend env vars, and point
`EXPO_PUBLIC_BACKEND_URL` of the release build to that HTTPS URL. See `docs/HANDOVER_REPORT.md` §F.

## 9. Troubleshooting
| Symptom | Fix |
|---|---|
| App shows network error on emulator | Use `http://10.0.2.2:8001`, not `localhost` |
| Phone cannot reach backend | Use your PC's LAN IP, allow port 8001 in Windows Firewall, and make sure the phone and PC are on the same Wi-Fi |
| `pip install -r requirements.txt` fails | Use `requirements-local.txt`. The full file references a private Emergent index |
| Gradle "SDK location not found" | Set `ANDROID_HOME` or create `android/local.properties` with `sdk.dir=...` |
| Google sign-in fails off-Emergent | Auth is Emergent-managed. See HANDOVER_REPORT §F (auth migration) |
| Photo upload 5xx locally | Storage needs an Emergent key. See HANDOVER_REPORT §F (storage migration) |
