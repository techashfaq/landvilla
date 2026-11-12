# Production inputs and EC2 preflight — 12 November 2026

Source: operator-reported manual inspection through AWS Console Instance Connect. The assistant did not execute commands on EC2. No production secret values were inspected or supplied. This is host metadata and assignment-presence evidence, not application acceptance.

## Host and checkout

- Amazon Linux 2023, x86_64, Mumbai; 2 vCPU, 1.9 GiB RAM, approximately 1.4 GiB available, 2 GiB swap.
- Root disk 20 GiB, approximately 16 GiB available. Docker active, Engine 25.0.18, Compose 5.7.1, overlay2, cgroup v2.
- No containers or Compose projects; one inactive 196 MB image. Docker socket requires `sudo` for `ec2-user`; do not change group/socket permissions as a workaround.
- `/opt/landvilla`: clean `dev`, HEAD `a1d58b33a23c869617975e70875e922bf75bd11f`. It lacks the new inspection script and does **not** match newer local/remote candidate commits. No EC2 pull, checkout or merge was performed. A candidate requires successful exact-commit Linux evidence before release.
- `/etc/landvilla/production.env`: root-owned, mode 0600, exactly two assignments: `DB_NAME`, `MONGO_URL`. Values, target identity, TLS options and provider permissions remain unverified.

## Required external API file inputs

Compose loads one API `env_file`, selected by `LANDVILLA_ENV_FILE`, then overrides fixed entries listed below. No other credential manager or alternate secret mount is configured. An unreported external mechanism must be reviewed explicitly; it cannot be assumed.

| Name | Source | Current evidence |
|---|---|---|
| `DB_NAME`, `MONGO_URL` | External API file | Assignments present only; correctness unverified |
| `STORAGE_PROVIDER` | External API file | MISSING |
| `IDENTITY_ENABLED` | External API file | MISSING |
| `OTP_HMAC_SECRET` | External API file | MISSING |
| `S3_ENDPOINT` | External API file | MISSING |
| `S3_BUCKET` | External API file | MISSING |
| `S3_ACCESS_KEY_ID` | External API file | MISSING |
| `S3_SECRET_ACCESS_KEY` | External API file | MISSING |

These seven names are required by `backend/production_runtime.py`; Compose does not supply them. The reported two-variable file cannot start the intended production API. Operator provisioning needs separate approval and secure access. Do not fill or transmit values during this inspection. No real secret is needed in chat/source.

## Required Compose interpolation inputs

The documented external `/etc/landvilla/compose.env` has **not been inspected**. Its existence, permissions and assignments remain NOT VERIFIED. Required names:

`LANDVILLA_ENV_FILE`, `LANDVILLA_DOCKER_SUBNET`, `LANDVILLA_DOCKER_DYNAMIC_RANGE`, `LANDVILLA_WEB_PROXY_IP`, `LANDVILLA_API_IMAGE`, `LANDVILLA_WEB_IMAGE`, `LANDVILLA_CADDY_IMAGE`, `LANDVILLA_ACME_EMAIL`, `LANDVILLA_INGRESS_TOKEN`, `LANDVILLA_WEB_API_IP_KEY`.

The last two are distinct runtime hop credentials. The first is Caddy/Web-only; the second becomes `WEB_API_IP_KEY` in Web/API. `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID` is optional public build configuration. Never print resolved Compose JSON; the checker captures it privately and emits fixed check labels.

## Inputs supplied by Compose

| Consumer | Names supplied or overridden |
|---|---|
| API | `APP_ENV`, `DEPLOYMENT_TIER`, `CLIENT_IP_MODE`, `WEB_API_IP_KEY`, `PYTHON_DOTENV_DISABLED`, `FORWARDED_ALLOW_IPS`, `TRUSTED_HOSTS`, `CORS_ORIGINS`, `WEB_APP_ORIGINS` |
| API disabled features | `SEED_ON_STARTUP`, `SEED_DEMO_LISTINGS`, `SEED_TEST_SESSIONS`, `ALLOW_LIVE_PAYMENTS`, `GOOGLE_PLAY_BILLING_ENABLED`, `REFUNDS_ENABLED`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` |
| Web | `NODE_ENV`, `NEXT_TELEMETRY_DISABLED`, `HOSTNAME`, `PORT`, `WEB_ORIGIN`, `BACKEND_ORIGIN`, `BACKEND_TRANSPORT`, `CLIENT_IP_MODE`, `LANDVILLA_INGRESS_TOKEN`, `WEB_API_IP_KEY` |
| Caddy | `ACME_EMAIL`, `LANDVILLA_INGRESS_TOKEN` |

Compose `environment` overrides API `env_file` for overlapping names. Validation/startup must use the same sanitized interpolation environment. Image Python buffering/bytecode defaults are not credentials. No Mongo/R2 credential belongs in Web, Caddy or build arguments.

## Conditional and optional API inputs

- Email OTP requires `SMTP_HOST`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`; absent. `SMTP_PORT` defaults to 587. This implementation requires STARTTLS, not implicit SMTPS port 465. Email sign-in is not operationally ready.
- SMS OTP requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`; absent. Unconfigured channels fail closed. No real OTP was sent.
- Google sign-in requires approved `GOOGLE_CLIENT_IDS` and matching public Web audience when enabled; not established.
- `S3_REGION` is optional. `ADMIN_EMAILS` is optional and affects authorization; any production admin assignment requires an approved identity/access review. Absence is not a reason to invent users/defaults.
- DB/bucket identities must match intended production targets. Assignment presence does not establish this. Existing identity index constraints and marker require read-only verification before separately approved provisioning. No automatic seed/migration is enabled.

## Capacity assessment

Production limits: API 768 MiB + Web 768 MiB + Caddy 256 MiB = **1,792 MiB (1.75 GiB)**. A nominal 1.9 GiB host has only about 154 MiB remaining if services approach their limits, before Linux/Docker overhead. Current available memory (~1.4 GiB) is below that aggregate. Limits are ceilings, not measured usage; this establishes inadequate worst-case headroom, not an observed OOM event. Swap does not prove latency/availability acceptance.

CPU quotas total 2.5 CPU on 2 vCPU; sharing is allowed but peak throughput is unverified. Seven rehearsal ceilings total 5.25 GiB and are not approved for this EC2 host. Do not build Next.js images there as an untested workaround. Current Linux checks use disposable GitHub runners; EC2 container starts remain prohibited.

Capacity remains BLOCKED until approved sizing or measured representative load/failure tests establish safe headroom. A host with at least 4 GiB is a starting sizing candidate, not proven acceptance; resizing needs separate AWS approval. Do not lower limits simply to fit. Disk acceptance requires measured images plus retained rollback images/logs/cache/free reserve; 16 GiB available alone is insufficient evidence.

## Next read-only inspection

No EC2 repository update is authorized. Review local scripts before any separately approved transfer or manual reproduction. `scripts/inspect-production-inputs.py` uses only Python's standard library, evaluates no shell/env expressions, and emits fixed names plus PRESENT/MISSING/EMPTY/DUPLICATE. Once the reviewed script is available through approved transfer:

```sh
sudo -n python3 scripts/inspect-production-inputs.py --api-env /etc/landvilla/production.env --compose-env /etc/landvilla/compose.env
```

Metadata-only commands the operator can run now:

```sh
sudo -n stat -c '%U %G %a %n' /etc/landvilla/production.env /etc/landvilla/compose.env
sudo -n docker version --format '{{.Server.Version}}'
sudo -n docker compose version --short
sudo -n docker network inspect --format '{{.Name}} {{json .IPAM.Config}} {{.Internal}} {{.EnableIPv6}}' $(sudo -n docker network ls -q)
ip -4 route
ip -6 route
ss -lnt
git -C /opt/landvilla --no-optional-locks status --short
git -C /opt/landvilla --no-optional-locks rev-parse HEAD
```

No containers start and no environment values print. Missing files/metadata do not authorize creation. VPC/VPN/peering routes, proxy peer measurement and directional isolation remain separate unverified gates.
