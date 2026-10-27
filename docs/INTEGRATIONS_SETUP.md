# LANDVILLA — Integrations Setup

The status of each item below comes from reading the code. "Configured" means credentials exist in this Emergent workspace (checked through the secrets list, without reading any values).

| Integration | Implemented | Configured now | Depends on Emergent |
|---|---|---|---|
| Google sign-in | Yes (Emergent hosted auth) | Managed by Emergent | **Yes** |
| Photo/document storage | Yes (Emergent Object Storage) | Yes (Emergent key) | **Yes** |
| Razorpay (featured listings) | Yes (orders, verify, webhook) | **No (no keys set)** | No |
| Push, email, SMS/OTP, maps, analytics | **Not implemented** | — | — |

## 1. Google sign-in
**Current flow (checked in `frontend/src/auth.tsx` and `backend/server.py`):**
1. The app opens `https://auth.emergentagent.com/?redirect=<app deep link>` (web: the site origin).
2. Emergent handles Google and redirects back with `#session_id=…`.
3. The app sends `POST /api/auth/session {session_id}`. The backend calls `https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data` with header `X-Session-ID`,
   gets the email, name, picture and `session_token`, then upserts `users` and stores `user_sessions` (7-day expiry).
4. The app saves the token in SecureStore and sends it as `Authorization: Bearer <token>`.

You have **no Google Cloud OAuth client** today. There is no client ID, SHA-1 or redirect URI to configure, because Emergent owns them.
The app never reads the Android package name or SHA fingerprints for sign-in.
Whether this works from your own backend or an Expo Go session is **not verified**.

**How to test:** sign in, then the backend log should show `POST /api/auth/session 200` followed by `GET /api/auth/me 200`.
If you see `401 Invalid session` from `/api/auth/session`, the Emergent auth service rejected the request.

**Migration to company-owned Google sign-in (needs your approval; this is a code change):**
1. In Google Cloud Console (your company project), configure the **OAuth consent screen** (External, app name LANDVILLA, privacy URL).
2. Create OAuth clients:
   - **Web** (used for ID-token audience and the web build), with authorised redirect URI = your web origin.
   - **Android**, with package `<final package name>` and SHA-1 values of (a) your debug keystore (`keytool -list -v -keystore %USERPROFILE%\.android\debug.keystore -alias androiddebugkey -storepass android`), (b) your upload key, and (c) the **Play App Signing** key from Play Console → App integrity.
3. App: use `@react-native-google-signin/google-signin` or `expo-auth-session`. Native Google sign-in needs a **development build, not Expo Go**.
4. Backend: replace `/api/auth/session` with an endpoint that verifies the Google ID token (`aud` = web client ID, `iss` = accounts.google.com, `email_verified`), then upserts `users` **by email**, so existing accounts and listings stay linked.
5. Env vars to add: `GOOGLE_WEB_CLIENT_ID` (backend and `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID`; client IDs are public) and `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID`. No client secret is needed for ID-token verification.

## 2. Image and document storage
**Current (checked in `backend/marketplace.py`):**
- `POST /api/uploads` (multipart: `file`, `kind`, plus bearer auth).
- Limits for `property_photo`: JPEG, PNG or WebP, **8 MB**, public. For `broker_doc`: JPEG, PNG, WebP or PDF, **10 MB**, **private**.
- Bytes go to Emergent Object Storage at `<INTEGRATION_PROXY_URL>/objstore/api/v1/storage/objects/landvilla/{photos|private}/<user>/<id>.<ext>`.
  The storage key comes from `EMERGENT_LLM_KEY`.
- Retrieval goes through `GET /api/files/{id}`. Public files get a 24-hour cache. Private files need the owner or an admin (bearer token or `?token=`) and are sent with `no-store`.
  The app builds URLs with `fileUrl()` in `src/api.ts`.
- **How to test:** Post → add a photo → the backend logs `POST /api/uploads 200`, and the photo loads from `/api/files/<id>`.

**Migration (needs approval):** create a private bucket on **Cloudflare R2** (no egress fees) or **AWS S3 ap-south-1**. Replace `_put`/`_get` in `marketplace.py` with boto3 calls (S3 API; R2 is S3-compatible).
Copy the existing objects with a one-off script run where the Emergent key is valid, then verify counts and SHA-256 (the `files.sha256` field already exists).
New env vars: `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` (all backend, all secret except the bucket name). The API URLs (`/api/files/{id}`) stay the same.

## 3. Razorpay (Test mode first)
**Implemented (checked):**
- `POST /api/payments/featured/order`: the amount comes from the server-side `featured_plans` price, never from the client. **It returns 403 unless the client is web**, so Play Store and App Store users can't buy featured listings in-app.
- `POST /api/payments/featured/verify`: checks the HMAC-SHA256 of `order_id|payment_id` with the **key secret**, then re-fetches the payment from Razorpay and matches order, amount and currency.
- `POST /api/payments/razorpay/webhook`: checks the HMAC of the raw body with the **webhook secret**, which is a different secret. It removes duplicate events by `x-razorpay-event-id`, and `fulfil()` grants featured time only once.

**Setup:**
1. dashboard.razorpay.com → switch to **Test Mode** → Account & Settings → **API Keys** → Generate. Put the values in `RAZORPAY_KEY_ID` (`rzp_test_…`) and `RAZORPAY_KEY_SECRET` in `backend/.env`, or in the deployment secrets.
2. Settings → **Webhooks** → Add:
   - URL: `https://<your deployed backend>/api/payments/razorpay/webhook`. It must be a public HTTPS backend. Don't use localhost or the Emergent preview URL.
   - Secret: a new random string. Put the same value in `RAZORPAY_WEBHOOK_SECRET`.
   - Events: `payment.captured`, `payment.failed`, `order.paid`.
3. Restart or redeploy the backend. `GET /api/featured-plans` should return `"payments_configured": true, "mode": "test"`.
4. Test: open the **web** build, sign in as the owner of an approved listing → Feature → pay with a Razorpay test card or test UPI (`success@razorpay`). The order becomes `paid` and the listing gets the Featured badge.
5. Webhook test: in Razorpay → Webhooks → *Send test*. Expect 200. A 400 means the secret doesn't match. A 503 means the secret isn't set.

Local webhook testing needs a public tunnel (for example `cloudflared tunnel --url http://localhost:8001`). Use it with test mode only.
**Live mode** needs Razorpay KYC and your explicit approval. Use `rzp_live_` keys only on the production server.

## 4. Not implemented
There is no push, email, SMS/OTP, maps or analytics code. Don't create accounts or variables for them until a feature that needs them is built.
