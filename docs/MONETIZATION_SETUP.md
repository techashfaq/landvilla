# Monetization setup (no deployment performed)

Android uses Google Play Billing; web uses the existing Razorpay integration. Packages are never sold until an administrator explicitly sets status=active and is_active=true. Existing seeded prices remain unpublished until reviewed. Set each Android package's play_product_id to an approved one-time consumable Play product. Android displays Google's price; Play transactions do not invent an INR settlement amount from the catalogue.

## Provider configuration
- Razorpay: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET. Subscribe the HTTPS `/api/payments/razorpay/webhook` endpoint to captured/failed/refund events. `ALLOW_LIVE_PAYMENTS=false` remains the default.
- Play: provision Android Publisher access using workload identity or a private `GOOGLE_APPLICATION_CREDENTIALS` file. Set GOOGLE_PLAY_PACKAGE_NAME=com.landvilla.app. Enable GOOGLE_PLAY_BILLING_ENABLED only after test setup.
- Authenticated Pub/Sub push: `/api/payments/play/notifications`, exact GOOGLE_PLAY_PUBSUB_AUDIENCE and GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT. Configure Play real-time developer notifications; do not use an unauthenticated push subscription.
- REFUNDS_ENABLED stays false until the refund policy is approved. The admin operation supports full Razorpay refunds with a stable provider idempotency key. Partial refunds remain flagged for review. Google refunds are performed in Play Console and reconciled through authenticated notifications; no manual paid switch exists.
- MongoDB must support transactions (Atlas/replica set). Existing payment/index provisioning must be applied through the reviewed deployment process, not through application startup seeding.

## Recovery and acceptance
- An uncertain Razorpay order creation is recorded as creation_unknown; reconcile its receipt with Razorpay before retrying a new purchase. Never automatically recreate an uncertain provider order.
- Test duplicate captured events, pending purchases, app termination, account switch, restore, late capture after cancellation, full refund with overlapping entitlements, notification retries and expiry on isolated staging.
- Build the `play-testing` AAB, upload it manually to an authorized internal test track, configure license testers, and install through Play. Expo Go cannot exercise native Billing. Production signing and account eligibility remain Play Console prerequisites.
- Run `python scripts/check-monetization-release.py` with staging process variables supplied privately. It prints names/status only, performs no network operations and does not read `.env`.
- No AWS target or deployment is selected here. Verify account region permissions before provisioning; existing Sydney/Mumbai restrictions remain unresolved.

Release is blocked until real-device license-test purchases, provider notifications/refunds, database transaction behavior, policies, and Play account eligibility are verified. No real payment was run during implementation.
