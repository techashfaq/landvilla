# LANDVILLA — Independent Production Deployment

Nothing here has been deployed. Every step that costs money or touches live data needs your approval first.

## 1. Services still tied to Emergent
| Service | Today | Independent option (cost-conscious, India) | Effort |
|---|---|---|---|
| Backend hosting | Emergent deployment | **Render** or **Railway** (Docker or Python service, ~US$7/mo), or a Mumbai VM (DigitalOcean BLR, AWS Lightsail Mumbai ~US$5–10/mo) + Nginx + Let's Encrypt | Low |
| Database | Emergent-managed MongoDB | **MongoDB Atlas** Flex or M10 in Mumbai, with backups | Low (dump and restore) |
| File storage | Emergent Object Storage | **Cloudflare R2** (10 GB free, no egress fees) or S3 Mumbai | Medium (code change + copy) |
| Google sign-in | Emergent hosted auth | Your own Google Cloud OAuth (free) | Medium (code change) |
| Secrets | Emergent Secrets panel | Your host's env-var settings or secret manager | Low |
| Android signing / build | Emergent build service (its key) | Your upload key + Play App Signing, built locally | Low |
| Domain / DNS / HTTPS | none | Domain (~₹800–1,000/yr) + Cloudflare DNS (free) | Low |

Recommended order: domain → database → backend host (still using Emergent storage and auth) → test → storage → auth → release.

## 2. Run the backend on your own host
Start command (exactly what the app needs):
```
cd backend && pip install -r requirements-local.txt && uvicorn server:app --host 0.0.0.0 --port $PORT --workers 2
```
- Health check path: `/health`
- Python: 3.11
- Environment: every variable in ENVIRONMENT_VARIABLES.md, with `SEED_DEMO_LISTINGS=false`, `SEED_TEST_SESSIONS=false`, `PUBLIC_BASE_URL=https://api.<domain>` and `ADMIN_EMAILS` set.
- HTTPS: Render and Railway provide it automatically. On a VM, run Nginx as a reverse proxy to `127.0.0.1:8001` with certbot.
- DNS: add a CNAME `api` pointing to the host's domain (Cloudflare proxy optional).
- Restrict CORS to your web domain (currently `*` in `server.py`). This is a small code change; ask before doing it.
- Rate limiting: add Cloudflare rate rules or Nginx `limit_req` for `/api/auth/*`, `/api/enquiries`, `/api/uploads`.
- Logs: use the host's log viewer. Optional monitoring: uptime checks on `/health` (UptimeRobot, free).
- Startup runs `seed.py` automatically and only adds missing reference data, so it's safe on a production DB.

## 3. Cutover checklist (with your approval)
1. Restore the production dump to Atlas and run `db_verify.py`, which should show all OK.
2. Deploy the backend to the new host, pointed at Atlas. Run `scripts/health_check.py --url https://api.<domain> --skip-db` and confirm everything passes.
3. Change the Razorpay webhook URL to `https://api.<domain>/api/payments/razorpay/webhook`, still in test mode.
4. Build the release AAB with `EXPO_PUBLIC_BACKEND_URL=https://api.<domain>` and test it with internal testing.
5. Freeze writes on Emergent, take a final dump and restore it (or sync the changes), then publish.
6. Keep Emergent running until you have tested the new setup and approve shutting it down.

## 4. Release configuration
- `frontend/app.json`: decide the final `android.package` (the current one is `com.emergent.ujjainestate.rq35d7`). Set `version` and `android.versionCode` above whatever was already uploaded.
- `frontend/.env` on the build machine: `EXPO_PUBLIC_BACKEND_URL=https://api.<domain>`.
- Signing: your own upload key only (ANDROID_BUILD_AND_PLAY.md §4). **Don't publish with Emergent's signing key or app ID** unless you knowingly accept that Emergent then holds the key needed for future updates.
- Store and legal: the privacy policy and terms (`/api/legal/privacy`, `/api/legal/terms`) are marked DRAFT and need legal review.
