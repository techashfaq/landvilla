# LANDVILLA — Handover Report

Prepared from a direct inspection of the Emergent workspace. Results marked "verified" were checked in this session.
No secrets are reproduced here.

## A. Source code & GitHub
- Local branch: `main`. History: 3 commits up to `75a11ce` plus uncommitted work (Play Store readiness, security fixes and these handover docs).
  Emergent auto-commits the workspace.
- **This workspace has no git remote configured** (`git remote -v` is empty), so the agent cannot `git push`.
  GitHub sync with Emergent is done through the **"Save to GitHub"** button in the Emergent chat UI. Choose repo `techashfaq/landvilla`, branch `main`
  (or a new branch such as `handover` if the repo already has content you want to keep). The push status and SHA can only be confirmed after you do this:
  `git ls-remote https://github.com/techashfaq/landvilla.git`.
- Repository contents: see the README §1 tree. The repo includes everything needed to build: backend (`server.py`, `marketplace.py`, `extras.py`,
  `seed.py`, `seed_data.py`, tests), frontend (`app/`, `src/`, `assets/`, `app.json`, `package.json`, `yarn.lock`), docs and scripts.
  It intentionally excludes `.env` files, `node_modules`, `android/` (generated) and test artifacts.
- Secret scan (verified): there are **no `.env`, keystore, google-services or credential files in tracked files or in history**. Pattern scan of
  the full history (Razorpay, OpenAI-style, Google API, PEM, Mongo URIs with passwords) found only pytest placeholders
  (`rzp_test_pytest`, `pytest_webhook_secret`). No rotation is needed for git history.
- `memory/test_credentials.md` is git-ignored. It holds only dev test-session tokens, which are disabled in production.

## B. Clone & open (Windows)
```powershell
git clone https://github.com/techashfaq/landvilla.git C:\src\landvilla
cd C:\src\landvilla; code .
Set-ExecutionPolicy -Scope Process Bypass; .\scripts\windows-setup.ps1
```
Details: `docs/WINDOWS_SETUP.md`.

## C. Android Studio
This is an Expo managed (CNG) project. Run `cd frontend; npx expo prebuild --platform android`, then in Android Studio **Open `frontend\android`**.
Details, versions, signing and AAB: `docs/ANDROID_BUILD_AND_PLAY.md`. A prebuild was verified. **No APK/AAB was built or tested** in this workspace (it has no Android SDK).

## D. Environment variables
| Variable | Where | Prod value guidance |
|---|---|---|
| MONGO_URL | backend | Your Atlas URI (secret) |
| DB_NAME | backend | e.g. `landvilla` |
| ADMIN_EMAILS | backend | Company admin Google emails (**currently empty in Emergent**, so nobody becomes admin automatically) |
| PUBLIC_BASE_URL | backend | `https://api.<domain>` |
| SEED_DEMO_LISTINGS | backend | **false** |
| SEED_TEST_SESSIONS | backend | **false** |
| RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET | backend | test keys in dev, live only on prod after approval (secret) |
| RAZORPAY_WEBHOOK_SECRET | backend | from Razorpay Dashboard webhook (secret) |
| INTEGRATION_PROXY_URL, EMERGENT_LLM_KEY | backend | only while using Emergent storage (secret) |
| EXPO_PUBLIC_BACKEND_URL | frontend (bundled, public) | `https://api.<domain>` |
Templates: `backend/.env.example`, `frontend/.env.example`. In Emergent, set these through the Secrets/Environment panel.

## E. Database & file storage
- MongoDB 7 (not PostgreSQL). The preview DB is verified to contain only test/demo data. The **production DB is not reachable from this workspace**.
  Export it through Emergent support, then run `scripts/db_export.py` → `mongorestore` → `scripts/db_verify.py` (`docs/DATABASE_MIGRATION.md`).
- Files: listing photos and broker documents are in **Emergent Object Storage**, addressed by the `files.storage_path` field. There is no bulk export
  API in the code. Migration plan: (1) create your own bucket (e.g. AWS S3 ap-south-1 or Cloudflare R2, private), (2) write a one-off
  script that runs **inside the Emergent production environment** (it needs the Emergent storage key), iterates `files`, downloads each object
  and uploads it to the new bucket under the same path, (3) swap `_put/_get` in `marketplace.py` to an S3 client, (4) verify counts and checksums, then cut over.
  Approval and coding are needed. Broker documents are personal data, so keep the bucket private.

## F. Resource ownership
| Resource | Current owner/control (verified?) | Exportable | Migration path | Risk/cost |
|---|---|---|---|---|
| Source code | Emergent workspace. GitHub `techashfaq/landvilla` **after you click Save to GitHub** | Yes | Save to GitHub | None |
| Backend hosting, API URL, HTTPS | Emergent deployment (`*.emergent.host`-style URL). Not yours | Code yes, hosting no | Self-host FastAPI (Render/Railway/VM+Nginx) and add your domain/DNS and TLS | Monthly hosting cost |
| Custom domain / DNS | **None configured** in the code | n/a | Buy the domain in your company account and point `api.` to your host | Domain cost |
| MongoDB (prod) | Emergent-managed. Not yours | Via Emergent support | §E | Paid Atlas if migrated |
| MongoDB (preview) | Emergent workspace. Test data only | Yes (mongodump verified available) | Not needed | — |
| Object storage (photos/docs) | Emergent-managed | No self-serve bulk export | §E plan | Bucket cost and a dev task |
| Google sign-in | **Emergent-managed auth** (`auth.emergentagent.com`, session exchange at `demobackend.emergentagent.com`). There is no Google Cloud project of yours | No | Create a Google Cloud OAuth client (Android SHA-1 of the **Play app-signing** key, plus web), then replace `/auth/session` and the login flow in `frontend/src/auth.tsx` with Google ID-token verification on the backend. Keep `users` keyed by email so existing accounts carry over | Code change. Users must re-login. This is the **largest lock-in** |
| Sessions / users | In the Mongo `users` and `user_sessions` collections | With the DB | With the DB | — |
| Password reset / email / SMS / OTP | **Not used** (Google only) | — | — | — |
| Razorpay | **Not configured in this Emergent app** (`payments_configured:false`, no RAZORPAY_* secrets set). Whoever owns the Razorpay account owns it | Keys come from your dashboard | Create or confirm the company Razorpay account, set the test keys first, and add the webhook `https://<api>/api/payments/razorpay/webhook` for `payment.captured`, `payment.failed` and `order.paid` with a secret | Live mode needs KYC and your approval |
| Push / Firebase / maps / analytics / error tracking | **Not used** | — | Add Sentry/Crashlytics later if wanted | — |
| Background jobs / cron | None in the app code. Only Emergent's internal `.emergent/cron` runner | — | — | — |
| CI/CD, GitHub Actions | **None in the repo** | — | Optional: add an Actions workflow for pytest and lint | — |
| Android signing | Emergent signed 1.0.1 with **its** key (not exportable from here) | Unknown | Generate **your own upload key** and use Play App Signing. If 1.0.1 was uploaded to some Play account with Emergent's key, ask Emergent support about key export or an upload-key reset | Key ownership is critical |
| Play Console listing | Yours (company) | — | Manual | — |
| LLM key | Emergent universal key. Present but **not used by the code** | — | Remove it after the storage migration | — |

## G. Missing / limitations
- No missing source was found. The Android native project is generated, not missing.
- Production DB, object storage files and the Emergent signing key cannot be exported from this workspace.
- Google auth and storage depend on Emergent services until they are migrated (§F).
- `requirements.txt` is an Emergent environment freeze. Use `backend/requirements-local.txt` outside Emergent.
- Backend tests are integration tests against a running server with test sessions. Pytest was not re-run in this session.

## H. Security findings
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `SEED_TEST_SESSIONS` and `SEED_DEMO_LISTINGS` are `true` in the preview. Both have a **live** slot set, but the agent cannot read live values | **Blocker** | Your action: confirm live = `false` in Emergent Secrets before publish. Code removes test users/sessions and hides demo listings when false (verified in `server.py` startup) |
| 2 | Release template signs with the debug key | Blocker for self-built AAB | Fix with docs step 4 |
| 3 | versionCode/versionName mismatch with build 1.0.1 | Blocker for upload | Bump in app.json |
| 4 | `ADMIN_EMAILS` is empty, so there are no admins in production | High | Set the company admin emails |
| 5 | Privacy Policy/Terms are marked DRAFT | High (Play/DPDP) | Legal review |
| 6 | CORS `allow_origins=["*"]` | Medium | Bearer-token auth (no cookies) reduces the risk. Restrict to your web domain when self-hosting |
| 7 | Rate limiting only on reports (429). There is no global limit | Medium | Add rate limits at the proxy (Nginx/Cloudflare) or with slowapi |
| 8 | Razorpay: signatures are verified (HMAC, constant-time). The amount comes from the server-side plan and is re-checked against Razorpay. Webhooks are deduplicated by a unique event_id. Fulfilment is idempotent (`status != paid`). Key secret stays server-only. Only `key_id` goes to the client. Purchases are blocked in the native apps | OK (code reviewed) | — |
| 9 | Auth enforced via `current_user` / `admin_user` dependencies on protected routes. Test tokens are rejected when `SEED_TEST_SESSIONS` is false | OK (code reviewed) | — |
| 10 | Account deletion (in-app and public web form), report/block and admin moderation are implemented. Legal pages are linked in the app | OK (tested in iteration 6) | — |

## I. Checklist
| Task | Status |
|---|---|
| Inspect architecture & document | COMPLETED AND VERIFIED |
| Secret scan of tracked files + history | COMPLETED AND VERIFIED |
| .gitignore hardening, .env.example files | COMPLETED AND VERIFIED |
| README + docs + Windows script + DB export/verify scripts | COMPLETED BUT NOT VERIFIED on Windows. DB scripts were run on the preview DB |
| Expo prebuild (Android project generation) | COMPLETED AND VERIFIED (throwaway copy) |
| Debug APK / signed AAB build | REQUIRES MY ACTION (no Android SDK in workspace) |
| Push to GitHub `techashfaq/landvilla` | REQUIRES MY ACTION ("Save to GitHub" button) |
| Confirm SEED_* = false in production secrets | REQUIRES MY ACTION |
| Configure Razorpay test keys & webhook | REQUIRES MY ACTION |
| Production DB export | BLOCKED / NOT AVAILABLE from workspace. Contact Emergent support |
| Object storage export | BLOCKED / NOT AVAILABLE self-serve. Needs a migration script (approval) |
| Google auth to company-owned OAuth | REQUIRES MY ACTION + approval for the code change |
| Upload key, Play App Signing, store listing, Data Safety | REQUIRES MY ACTION |
| Legal review of privacy/terms | REQUIRES MY ACTION |

## J. Next single step
Click **"Save to GitHub"** in Emergent, push to `techashfaq/landvilla` (branch `main`, or `handover` if the repo already has commits), then run
`git ls-remote https://github.com/techashfaq/landvilla.git` to confirm the commit SHA.
