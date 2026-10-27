# LANDVILLA — Environment Variables & Secrets Inventory

This list comes from the actual code (`os.environ` in `backend/*.py`, `process.env` in `frontend/`).
**Rules:**
- `backend/.env` holds private settings and must never be committed.
- `frontend/.env` is public: every `EXPO_PUBLIC_*` value is bundled into the APK and anyone can read it.
- Never put a secret in `EXPO_PUBLIC_*`.
- Use separate values for **dev** (your PC), **staging** (optional) and **production** (deployed backend).

## Backend (`backend/.env`)
| Variable | Used in | Required | Public/secret | Where to get it | Dev / Prod value | How to test |
|---|---|---|---|---|---|---|
| `MONGO_URL` | server.py | **Yes** | **Secret** | Local MongoDB, or Atlas → Connect → Drivers | dev `mongodb://localhost:27017`; prod `mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority` | `python scripts/health_check.py` → "MongoDB connect" PASS |
| `DB_NAME` | server.py | **Yes** | Config | You choose | dev `landvilla_dev`; prod `landvilla` | same |
| `ADMIN_EMAILS` | server.py | Recommended | Config | Your company Google emails, comma-separated | your email | Sign in, then Profile shows Admin tools |
| `PUBLIC_BASE_URL` | extras.py (sitemap, legal, canonical links) | Prod: yes | Config | Your deployed backend HTTPS URL | dev empty (uses request host); prod `https://api.<domain>` | Open `/api/sitemap.xml`. The URLs should use this base |
| `SEED_DEMO_LISTINGS` | server.py, seed.py | No (default false) | Config | — | dev `true`; **prod `false`** | `true` → 20 fictional listings. `false` → hidden |
| `SEED_TEST_SESSIONS` | server.py | No (default false) | Config (enables fixed test tokens) | — | dev/test `true`; **prod `false`** | `false` → `test_session_*` tokens get 401 |
| `RAZORPAY_KEY_ID` | marketplace.py | For payments | Semi-public (sent to the checkout) | dashboard.razorpay.com → Account & Settings → API Keys (Test mode) | dev `rzp_test_…`; prod `rzp_live_…` only after approval | `/api/featured-plans` → `payments_configured:true, mode:"test"` |
| `RAZORPAY_KEY_SECRET` | marketplace.py | For payments | **Secret** | Shown once when you generate the key | separate test/live | same |
| `RAZORPAY_WEBHOOK_SECRET` | marketplace.py | For the webhook | **Secret**, **different from the key secret** | You invent it (a long random string) and type the same value into Razorpay → Webhooks | separate per environment | Unsigned POST to the webhook → 400 (set) vs 503 (missing) |
| `INTEGRATION_PROXY_URL` | marketplace.py (storage) | Uploads only | Config | Emergent | `https://integrations.emergentagent.com` | Upload a photo → 200 |
| `EMERGENT_LLM_KEY` | marketplace.py `_init_storage()` (read only when the first upload happens) | Uploads only | **Secret** | Emergent (Profile → Universal Key). Not a Google or Razorpay key | Leave it unset locally if you don't test uploads | Upload a photo. Without the key: 500 error (KeyError) on upload. Everything else still works |

`EMERGENT_LLM_KEY` and `INTEGRATION_PROXY_URL` are the only remaining Emergent dependencies in the backend config. See INTEGRATIONS_SETUP.md §2.

## Frontend (`frontend/.env`)
| Variable | Used in | Required | Public | Value per environment |
|---|---|---|---|---|
| `EXPO_PUBLIC_BACKEND_URL` | src/api.ts, src/auth.tsx | **Yes** | Public | emulator `http://10.0.2.2:8001` · phone on Wi-Fi `http://<PC-IP>:8001` · USB with `adb reverse` `http://localhost:8001` · release `https://api.<domain>` |

Do **not** add `/api` at the end, because `api.ts` adds it. The value is baked in when Metro bundles or Gradle builds, so restart `yarn start --clear` after changing it.
Emergent-only (do not set on your PC): `EXPO_PACKAGER_PROXY_URL`, `EXPO_PACKAGER_HOSTNAME`, `EXPO_TUNNEL_SUBDOMAIN`, `METRO_CACHE_ROOT`, `EXPO_USE_FAST_RESOLVER`, `REACT_APP_BACKEND_URL`.

## Not used by the code (no variable needed)
JWT/session signing secret (sessions are random tokens stored in Mongo), SMTP/email, SMS/OTP, push/Firebase, maps/geocoding, analytics, Sentry.
There is **no Google OAuth client ID** either, because sign-in goes through Emergent's hosted auth (INTEGRATIONS_SETUP.md §1).

## Where to configure
| Environment | Location |
|---|---|
| Your PC | `backend/.env`, `frontend/.env` (copied from `.env.example`, git-ignored) |
| Emergent deployment | Publish → Deployment panel → **Secrets**, then redeploy |
| Your own host (Render/Railway/VM) | The provider's environment-variable settings. Never commit them in the repo |
| Release APK/AAB | `frontend/.env` on the build machine at build time (public URL only) |

## Check
`powershell -ExecutionPolicy Bypass -File .\scripts\check-config.ps1` checks that each variable is present. It prints names and status but **never the secret values**.

## Secret history check (done)
Tracked files and the full git history were scanned. They contain only pytest placeholders (`rzp_test_pytest`, `pytest_webhook_secret`) and no real credentials, so nothing needs rotating.
If you ever commit a secret, **rotate it at the provider first**, because removing it from a later commit doesn't remove it from history.
