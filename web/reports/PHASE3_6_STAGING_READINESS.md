# LANDVILLA Phase 3.6 — Staging readiness

Inspection date: 10 November 2026 (Asia/Calcutta). Repository: `F:\projects\landvilla`; baseline branch `dev`, HEAD `de39e8e7f7915eef8ff693bd01edc42f1c54f8b6`.

**Decision: deployment remains blocked.** This is a preparation document. No infrastructure, DNS, account setting, bucket, database, cloud credential or deployment was created or changed by this inspection. Public documentation was researched; authenticated AWS access was unavailable. Test/build/browser results belong in the companion final and acceptance reports, not inferred here.

## 1. Evidence and limits

Read source configuration, example files, ignore rules, deployment docs, and route/session implementations. Checked command availability and local configuration file existence without reading private configuration values.

| Check | Result |
| --- | --- |
| `web/.env.local` exists | PASS; values intentionally not displayed or copied |
| `web/.env` exists | No; `.env.local` is the existing local configuration path |
| `backend/.env` exists | PASS; credentials and connection details not inspected |
| `git check-ignore web/.env.local backend/.env frontend/.env` | All three ignored |
| Tracked files matching env/key filename patterns | Only the three `.env.example` files; this filename check is not a full secret/history scan |
| AWS CLI on PATH | Not found |
| Default user AWS config/credentials files | Neither found |
| AWS environment credential/profile/region variable names | None found in this execution process |
| Connected AWS tools | None available |
| AWS region and IAM/SCP permissions | BLOCKED; no authenticated account evidence |

The existing `docs/PRODUCTION_DEPLOYMENT.md`, `docs/INTEGRATIONS_SETUP.md`, and environment guide contain historical assumptions. In particular, storage and Google integrations have since been implemented, startup seeding is opt-in, explicit origins are enforced, and the website is now separate Next.js. Do not follow the older restore/seed/cutover instructions as current authorization.

## 2. Required configuration by feature

Values below are setting names and safe policy choices, not actual environment values. File existence does not verify that settings are correct or provider credentials work.

| Component / capability | Required settings or prerequisites | Failure/operating boundary |
| --- | --- | --- |
| Next.js production runtime | `NODE_ENV=production`, `BACKEND_ORIGIN`, `WEB_ORIGIN` | `readConfig()` requires explicit HTTPS origins; rejects credentials, paths, query/fragment, and a self-proxy loop |
| Staging backend using production safeguards | `APP_ENV=production`, `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`, `WEB_APP_ORIGINS` | Use a separate staging database/account. Setting `APP_ENV=staging` does **not** activate the code's production-only guards |
| Non-destructive startup | `SEED_ON_STARTUP=false`, `SEED_DEMO_LISTINGS=false`, `SEED_TEST_SESSIONS=false` | Production rejects enabled startup seeding, demo listings and fixed test sessions |
| Passwordless identity | `IDENTITY_ENABLED=true`, strong independent `OTP_HMAC_SECRET` (minimum 32 characters), verified existing identity indexes and migration marker | Startup checks identity prerequisites. Provisioning indexes requires a separately reviewed and explicitly authorized operation; do not run a migration as a health check |
| Email OTP | `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Current implementation uses STARTTLS; default port 587, rejects implicit-TLS port 465. Verify approved sender/domain and delivery using owned test contacts |
| Mobile OTP | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` | Optional until SMS login/contact verification is an approved launch feature. Sender policy and India delivery eligibility require provider review |
| Independent Google login | Backend `GOOGLE_CLIENT_IDS`; web `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID` | Optional; IDs are public audience identifiers. Authorized JavaScript origin must match the approved web origin. Never add a client secret to `NEXT_PUBLIC_*` |
| Cloudflare R2 uploads/retrieval | `STORAGE_PROVIDER=cloudflare_r2`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`; optional `S3_REGION` defaults to `auto` | Use a private staging bucket and bucket-scoped key. Backend validates configuration lazily; a healthy process does not prove uploads work |
| Legacy stored objects | `INTEGRATION_PROXY_URL`, `EMERGENT_LLM_KEY` only if retained legacy objects need this provider | Do not delete legacy configuration until object-provider inventory is independently reviewed |
| Payments | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | Optional while purchasing is unavailable. Staging must use approved test mode with `ALLOW_LIVE_PAYMENTS=false`; signatures and captured-payment checks remain required |
| Staff access | Privately approved `ADMIN_EMAILS` and existing authorized accounts | This is a privileged allowlist. No broad domains, synthetic admin identity, or privilege bypass to make acceptance pass |
| Public canonical links/legal URLs | Approved `PUBLIC_BASE_URL` on backend and `WEB_ORIGIN` on web | Validate each emitted URL before indexing. No production domain is approved by this report |

`backend/.env.example` currently omits the implemented R2 `S3_*` variables and defaults to legacy storage. The table above records the missing setup documentation without changing existing environments. Example files contain placeholders/local examples only in the inspected files. Do not treat example Razorpay placeholder strings as operational credentials.

## 3. AWS region restriction — unresolved gate

Neither `ap-south-1` (Mumbai) nor `ap-southeast-2` (Sydney) is confirmed usable by this account. A default-region list or successful `DescribeRegions` call does not establish permission to create the chosen hosting resources: IAM policy, permission boundaries, organization SCPs, service availability, quotas, billing/account restrictions and session policy can still deny access. AWS documents region status separately from IAM region controls. [AWS region management](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-regions.html).

An authorized owner can run the following **read-only** commands in an existing authenticated AWS CLI session; these were not run here. Review output privately; do not paste account IDs, ARNs, credentials or account resource names into reports.

```powershell
aws account list-regions --query "Regions[?RegionName=='ap-south-1' || RegionName=='ap-southeast-2'].[RegionName,RegionOptStatus]" --output table
aws ec2 describe-regions --all-regions --region ap-southeast-2 --query "Regions[?RegionName=='ap-south-1' || RegionName=='ap-southeast-2'].[RegionName,OptInStatus]" --output table
aws lightsail get-regions --region ap-southeast-2 --query "regions[?name=='ap-south-1' || name=='ap-southeast-2'].name" --output table
aws lightsail get-bundles --region ap-south-1 --query 'bundles[?isActive].[bundleId,ramSizeInGb,price]' --output table
aws lightsail get-bundles --region ap-southeast-2 --query 'bundles[?isActive].[bundleId,ramSizeInGb,price]' --output table
```

If an endpoint is denied, preserve only its error code and affected service/region. The owner must review effective creation permissions, including SCPs, without trying an actual create action. Do not enable regions or alter policies under this task.

Only after this gate passes: prefer a verified permitted region close to users and the existing approved Atlas region. Mumbai is a conditional latency candidate, not a deployment decision. If Sydney is the sole permitted option, obtain owner approval for latency/data-location implications and measure using staging before selecting it. Do not migrate Atlas merely to match an assumed AWS location.

## 4. Conditional low-cost staging architecture

This proposal preserves Next.js, FastAPI, Atlas and R2. It is a small staging topology with a single-host failure domain, not a high-availability production design.

1. **Compute:** one permitted-region Lightsail Linux instance, initially 4 GB RAM, public IPv4. Separate unprivileged service users for Next.js and Uvicorn. Build tested artifacts away from the small host and transfer immutable release artifacts through an approved deployment identity. Verify memory/CPU under staging load before choosing final sizing.
2. **HTTPS ingress:** Nginx or equivalent reverse proxy for owner-approved staging web and API subdomains under the same parent domain. TLS termination with certificate renewal alarms. Expose 443; limit SSH to approved operator access. Bind Next and FastAPI to loopback; no public 19006/8000 ports. `BACKEND_ORIGIN` remains the HTTPS API origin required by production config. Preserve Origin/Referer and host-only cookies; never fabricate a trusted browser Origin.
3. **Atlas:** a separate staging database/user with least privileges and a narrow access list for approved host egress. TLS verification stays enabled. No `0.0.0.0/0` shortcut, restore from production, data copy or reseeding. Confirm required MongoDB transactions/indexes work on the selected existing tier using explicitly approved isolated acceptance data.
4. **R2:** separate private staging bucket, explicit scoped access, authenticated backend retrieval for broker documents. Keep bucket public access disabled. CDN rules must bypass private API/session/account/admin/media responses; no query-token download links.
5. **Secrets:** maintain approved secrets in AWS Secrets Manager or the organization's existing manager. Use a short-lived operator/deployment identity to deliver an access-restricted runtime environment outside the checkout; exclude it from artifacts, logs and backups. Do not store permanent AWS administrator keys on a Lightsail VM. If workload roles and automatic secret retrieval are required, use EC2/ECS with an appropriate role and produce a revised regional cost estimate before provisioning.
6. **Ingress and abuse controls:** complete a trusted-proxy/client-IP design before real OTP tests. The Next proxy intentionally strips caller-supplied forwarded IP headers; backend IP throttles may otherwise share the proxy address across users. Set body/time limits consistent with validated upload limits. Plan a tested CSP and HSTS rollout after both approved HTTPS hosts are working; the existing basic headers are not a full CSP.
7. **Staging access:** require an approved ingress access restriction; retain prelaunch noindex. Existing web robots disallow all paths and the sitemap is empty. Robots is not access control. Do not enable indexing until demo/private visibility and canonical checks pass.

## 5. Monitoring, backup and rollback preparation

| Area | Plan / acceptance gate |
| --- | --- |
| Liveness | Backend `/health` proves process responsiveness only. Check it with a timeout and alert threshold; do not interpret HTTP 200 as Atlas or provider readiness |
| Readiness | Backend `/ready` performs a database ping; exercise only against the approved staging database after deployment authorization. Web readiness must also demonstrate safe public API access |
| Logs | Structured request ID, route template, status, duration and sanitized category. Suppress credentials, cookies, OTP bodies, auth headers, raw provider errors, private image/document paths and personal details. Set finite retention and operator access |
| Alerts | 5xx rate, p95 latency, unavailable upstream, memory/disk, TLS expiry, failed background work where implemented; notify approved owners only |
| AWS cost monitoring | Set owner-approved budget thresholds before provisioning; zero-cost assumption is not acceptable even for free-tier eligible accounts |
| Application rollback | Keep previous artifact and configuration version, health-check the candidate before switching ingress, revert traffic to previous artifact on failure. No Git reset/force push needed |
| Database backup | Owner-approved Atlas backup policy and restore exercise into a new isolated target. App rollback does not reverse schema/data changes. No backup/restore was performed here |
| Media backup | Document R2 retention and an approved independent copy/restore policy; bucket durability is not protection against application deletion |
| Disaster recovery | Owner must define RPO/RTO, recovery operator, restore access and retention before launch; no invented commitments |

Atlas Flex lacks private endpoints and continuous backup/PITR, so a Flex staging estimate must not be presented as a production recovery solution. Select Dedicated if these are requirements. [Atlas Flex limits](https://www.mongodb.com/docs/atlas/reference/flex-limitations/).

## 6. Illustrative monthly cost in INR

Prices checked against official pages on 10 November 2026. **Planning assumption: USD 1 = INR 100**, deliberately round and not asserted as a current exchange quote. Figures exclude taxes, FX/provider markup, domain purchase, messaging/email usage, optional monitoring, extra transfer, and support. Requote in the confirmed permitted region/account before approval. No credits/free trials assumed.

| Item / assumption | USD per month | INR at planning rate | Basis |
| --- | ---: | ---: | --- |
| Lightsail 4 GB Linux with public IPv4 | 24.00 | 2,400 | [Official instance bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html) |
| Instance snapshots, assumed 40 GB billed storage | 2.00 | 200 | $0.05/GB-month; actual snapshot storage varies. [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/) |
| Route 53, one zone and 100,000 standard queries | 0.54 | 54 | $0.50 + $0.04; avoid duplicate zone if DNS already exists. [Route 53 pricing](https://aws.amazon.com/route53/pricing/) |
| Secrets Manager, five stored secrets | 2.00 plus calls | 200 plus calls | $0.40/secret-month, $0.05/10,000 API calls. [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/) |
| Separate Atlas Flex for staging, if approved | 8–30 | 800–3,000 | Usage-based test/development estimate; existing account/tier not changed. [Atlas pricing](https://www.mongodb.com/pricing) |
| R2 Standard, assumed 20 GB-month within operation free allowances | 0.15 | 15 | 10 GB free, remaining 10 × $0.015; operations/usage above allowances extra. [R2 pricing](https://developers.cloudflare.com/r2/pricing/) |
| **Illustrative subtotal** | **36.69–58.69** | **3,669–5,869** | Before taxes and excluded usage; not a spend cap |

Lightsail published Mumbai and Sydney bundles have half the headline transfer allowance; confirm the bundle returned in the selected region. Attached static IPv4 is included under applicable Lightsail rules, while detached allocation can cost extra. [Lightsail pricing](https://aws.amazon.com/lightsail/pricing/), [Lightsail FAQ](https://aws.amazon.com/lightsail/faq/). A load balancer, NAT gateway, CloudFront/WAF, dedicated Atlas tier or multiple instances requires a different estimate; none is silently included above. R2 egress is free at the R2 layer, but media proxied through AWS still consumes AWS transfer allowance.

## 7. Owner decisions and blocked acceptance

Do not fill these with invented contact details or implied approval:

- Official support email, support phone, business/registered address and working hours where displayed.
- Legal approval/versioning for privacy policy and terms; refund/cancellation policy and complaint escalation.
- Commission rules, agreement evidence, taxes/invoicing and collection authorization.
- Featured package prices and entitlements; seeded/default values are implementation fixtures, not approved business prices.
- Payment provider ownership, test credentials, settlement flow, webhook ownership and refund responsibilities; no live payments enabled.
- Broker verification evidence, review authority, document retention, rejection/appeal process and prohibition of self-approval.
- Property moderation policy and who may publish/unpublish; real inventory and rights to every property photograph.
- Production domain ownership and staging subdomains; approved Google origins and email/SMS sender ownership.
- AWS region and resource permissions, approved budget, staging database isolation, log retention, backup retention and RPO/RTO.
- Existing customer/owner/broker/admin test accounts and owned test contacts for bounded end-to-end acceptance. Do not elevate privileges or repeatedly send real OTPs.

## 8. Next authorized steps

Finish the local implementation and safe verification reports. Obtain read-only account evidence to resolve AWS region and IAM restrictions. Then review a concrete staging plan with exact region, tier, budget, domains, secret ownership and isolated acceptance data. Provisioning, deployment, index migration, restore, data mutation and charge-incurring actions require the user's explicit authorization; none is implied by this document.
