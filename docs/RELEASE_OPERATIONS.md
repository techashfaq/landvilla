# Release operations — prepared, not deployed

The artifacts do not certify production readiness. No cloud resources, database indexes, builds or real payments were executed for this preparation.

## Backend build and traffic boundary

From repository root, after authorization: `docker build -t landvilla-api:<release-tag> backend`. Pin the validated base image digest and preserve the immutable application image digest in the release record. The Docker context excludes environment files and local credentials. Runtime is Python 3.12, UID 10001, no access log, no startup seed. `deploy/compose.production.yml` is a target-neutral example using an external environment file; do not commit that file or render interpolated compose output into logs.

Terminate TLS at a controlled ingress. Bind the API privately, permit ingress only from that proxy, strip client Forwarded/X-Forwarded-* headers and set trusted proxy headers. Set FORWARDED_ALLOW_IPS to actual proxy IPs; never `*`. TRUSTED_HOSTS must include the API hostname and 127.0.0.1 for the container probe. Configure ingress request-size limits aligned with upload validation, request timeouts, and independent abuse limits. Application write limits share atomic Mongo counters; existing OTP recipient limits remain. Do not log headers, bodies, query strings or raw provider exceptions at ingress.

`/health` is process liveness. `/ready` checks Mongo ping, session-capable replica-set/sharded topology and read-only R2 HeadBucket with short timeouts; errors return generic 503. Restrict probes to ingress/orchestrator. This does not prove transaction privileges or read/write object rights: perform abort-only transaction and synthetic-object tests in an isolated staging database/bucket before release. No production test writes. Readiness failure should remove traffic; only liveness failure should restart. SIGTERM gets 30 seconds to drain; orchestrator allows at least 40. Existing startup ping fails fast and shutdown closes Mongo.

## Environment names (values belong in the secret manager)

Mandatory: APP_ENV, MONGO_URL, DB_NAME, CORS_ORIGINS, WEB_APP_ORIGINS, TRUSTED_HOSTS, FORWARDED_ALLOW_IPS, STORAGE_PROVIDER, S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, IDENTITY_ENABLED, OTP_HMAC_SECRET, GOOGLE_CLIENT_IDS. Set all seed flags false: SEED_ON_STARTUP, SEED_DEMO_LISTINGS, SEED_TEST_SESSIONS. Optional S3_REGION. Website also needs its existing backend transport and public origin configuration; preserve its secret separation.

Email OTP: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM. SMS OTP: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM. Enable only channels with configured senders. Billing: names and permissions in MONETIZATION_SETUP.md; keep live payments/refunds disabled until policies and provider tests are approved. Native build: EXPO_PUBLIC_BACKEND_URL, existing Google client configuration. EXPO_PUBLIC values are public; never place secrets there.

## Additive index provisioning

Offline plan: `python backend/scripts/provision_release_indexes.py`. This does not import the application, load dotenv or connect. After backup, isolated staging rehearsal and explicit database authorization, inject environment securely, then run `python backend/scripts/provision_release_indexes.py --apply --confirm-database <approved-database-name>`. Repeated runs ensure existing indexes; no records/indexes are dropped and no reference/demo data is seeded. TTL indexes expire session/OTP/rate-limit records by design: review that effect before applying. Conflicts or duplicates stop safely and may leave earlier additive indexes present. Never resolve conflicts by deleting user records.

Legacy unique non-partial razorpay_order_id indexes block multiple Google Play orders without Razorpay IDs. The command refuses this state before applying indexes. Replacement requires separately approved migration after checking data; it is deliberately not automated. Existing reference locations/categories must be reviewed and provisioned separately, not startup-seeded.

## Backups, storage and deletion

Enable encrypted Atlas backups/PITR and approved retention. Record snapshot ID before release. Restore to a separate isolated cluster/database, validate counts, ownership, indexes and referential consistency with read-only scripts; never restore over live data. Drill access and recovery time before launch. Restrict backup-reader roles and audit exports; never put database URLs on a command line or into logs.

Keep the R2 bucket private: disable r2.dev and public custom domains for this shared bucket. Use least-privilege bucket-scoped credentials. Deliver files through the existing authorized API. Broker documents remain private regardless of metadata flags. HeadBucket readiness does not prove bucket privacy; review dashboard policies separately. Maintain an encrypted, access-controlled backup strategy for media; database snapshots alone do not back up R2 objects.

Account deletion currently tombstones media and hides listings, removes sessions/profile/saved data and anonymizes enquiries/payment ownership. It does NOT physically purge R2 bytes. Approve retention periods for identity documents, images, audit records, backups and statutory payment records before scheduling physical deletion. No automated purge or retention duration has been invented. Public deletion requests need a staffed ownership-verification and fulfilment process; confirm the existing 30-day promise before publication.

## Region, rollout and rollback

No local AWS config region was found; permitted region and account/SCP permissions remain unverified. Do not select Mumbai or Sydney on that basis. An authorized operator must confirm account identity privately, enabled regions and service permissions before selecting regional compute, logging, secrets and network resources. Artifacts above create nothing. Prefer private backend compute behind TLS ingress, secrets manager injection, Atlas restricted egress and R2 outbound HTTPS. Costs require the chosen region and sizing; none are asserted here.

Preflight: `python scripts/check-production-release.py`, then `python scripts/check-monetization-release.py` in a secure configured shell. They print only check names and never contact services. Before rollout: targeted/full release tests, image scan, staging smoke tests, device acceptance, private-media checks, restore drill, operator approval. Deploy immutable images with readiness gates only after authorization. Roll back to the previous image and compatible environment; retain additive indexes. Do not roll back by restoring the live database or removing payment records. Disable new purchases if a payment incident occurs, retain verified receipts and reconcile through provider events. Set alerts for 5xx, readiness failures, OTP abuse, webhook processing delay and payment-review counts without recording personal data.
