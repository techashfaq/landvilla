# LANDVILLA production proxy and Docker readiness

> Historical Phase 2 evidence below. The later master execution changed authenticated client identity, production target/TLS validation, pinned base digests and rehearsal configuration. Current instructions and results: [master report](PRODUCTION_READINESS_MASTER_REPORT.md), [verification matrix](PRODUCTION_VERIFICATION_MATRIX.md), [deployment runbook](PRODUCTION_DEPLOYMENT_RUNBOOK.md). Earlier statements that Caddy receives no credentials, all caller IP is discarded, or base images remain mutable describe the previous implementation. They are not current acceptance claims.

Prepared 12 November 2026 for `landvilla.in`, AWS Mumbai, Amazon Linux 2023.

**Phase 2 status (12 November 2026): CONDITIONALLY READY FOR ISOLATED REHEARSAL; production deployment remains BLOCKED.** See [PRODUCTION_SECURITY_REVIEW_PHASE2.md](PRODUCTION_SECURITY_REVIEW_PHASE2.md) for the current security findings, dependency evidence and precise review commands. Local test results are not host acceptance. No production containers were started. No AWS/security-group/firewall/DNS/Atlas/R2 settings, credentials, indexes, migrations, data, payments, commits, pushes or merges were changed. The pre-existing untracked `docs/EC2_DIRECTIONAL_ISOLATION_PLAN.md` was read and left untouched; its starting hash still matches.

Phase 2 retained the architecture and added WebSocket-safe Host rejection, stricter session cookie parsing, identity-free metadata/legal reads, isolated build environment/asset checks, readiness timeout headroom and no-store probes. Production pins now use tested FastAPI 0.133.0 / Starlette 1.3.1 / PyMongo 4.18.3 plus explicit transitive constraints. The release checker requires immutable application image references, rejects alternate build/mount/entrypoint inputs, and checks explicit non-root users. `--allow-build-tags` is a separately labelled pre-build check, never release acceptance. Existing `backend/.venv` was not upgraded; use the tested isolated environment below or a fresh install of the revised requirements.

## Audit and implementation decisions

| Audit finding | Prepared change / retained boundary |
|---|---|
| Web rejected every production HTTP backend | Public `WEB_ORIGIN` remains HTTPS-only. Explicit `BACKEND_TRANSPORT=private-http` accepts **only the exact string** `http://api:8000`. No IP-range allowance, alternate port, external HTTP hostname, URL alias or environment-controlled allowlist. Default production backend transport remains HTTPS. |
| Backend HTTPS enforcement sees internal HTTP | Every server API caller now generates `X-Forwarded-Proto` from validated `WEB_ORIGIN`. Uvicorn accepts it only from the configured exact Web peer. Backend HTTPS checks are retained. |
| Proxy address validation only rejected `*` | Require canonical literal RFC1918 IPv4 addresses; reject wildcard, hostname, CIDR, public, loopback and malformed values. Compose configures one exact Web IP. Pinned Uvicorn 0.25.0 uses exact peer strings and reads `FORWARDED_ALLOW_IPS`; no wildcard/CIDR trust. |
| TrustedHost ran after request guards | Strict complete Host-authority validation and TrustedHost now wrap CORS, browser guards and throttling. Duplicate/missing Host and malformed ports/path injection fail first. `www_redirect=False`. Internal Host is `api:8000`; loopback probe Host is `127.0.0.1:8000`. |
| Caller forwarding headers must not cross trust boundaries | Caddy deletes `X-Forwarded-*` before generating canonical scheme/host, then deletes `Forwarded`, `X-Real-IP` and `X-Forwarded-For` upstream. Web builds new outbound headers and never reads caller forwarding fields. API Host comes from the fixed fetch destination, not the browser. |
| Browser security context must survive | Existing Origin, Referer, Sec-Fetch and CSRF allowlist and validation retained. No synthetic Origin/Referer is invented. Session cookie selection, Secure/HttpOnly/Path=/SameSite=Lax, host-only scope, duplicate rejection and deletion attributes retained. Public listing reads continue stripping identity. |
| SSR bypassed browser forwarder | Updated public transport, private/admin reads, published content and legal pages as well as browser forwarding. All use generated scheme, bounded timeouts, no-store and redirect rejection. |
| Web production server bound localhost; no image | Node 24 multi-stage Dockerfile, Next standalone build, copied static/public assets, non-root UID 1000, `HOSTNAME=0.0.0.0`, `PORT=3000`. `npm start` launches standalone; development remains localhost:19006. |
| API already bound correctly | Python 3.12 image retains 0.0.0.0:8000, UID 10001, proxy headers on, access logs off and 30s drain. Dockerfile now copies runtime constraints as well as direct requirements; compatible security upgrades are covered by Phase 2 tests. Linux image acceptance remains unverified. |
| Compose published API loopback port | Removed API publication; Web has no publication; only Caddy publishes TCP 80/443. No MongoDB/R2 container or credentials in Web/Caddy. |
| No complete ingress/health configuration | Caddy automatic HTTPS and canonical www redirect, request size/time limits, internal readiness, loopback liveness. Read-only filesystems, bounded tmpfs, dropped capabilities, no-new-privileges, restart, CPU/memory/PID and rotated logging declarations. |

The shared bridge is a private transport/service-discovery configuration, **not directional isolation**. It does not enforce Caddy-to-API or API-to-Web denial, restricted provider egress, host-local denial or firewall persistence. There are no four-network isolation rules, host firewall commands, systemd guards or changes to the proposed isolation plan. All bridge participants and Docker/host administrators remain trusted. If directional isolation is a launch requirement, its separately approved design and acceptance remain blocking.

## Prepared architecture (not deployed)

```text
Browser -- HTTPS landvilla.in:443 --> Caddy
          HTTP :80 redirects             |
          www redirects to apex          | HTTP web:3000, fixed Host/scheme
                                        v
                              Next.js Website + /admin
                                        |
                                        | HTTP api:8000, generated HTTPS scheme
                                        | one exact verified Web source IP
                                        v
                               Uvicorn + FastAPI
                                        |
                                  TLS to Atlas / R2
```

Only Caddy has host port bindings. Caddy's admin endpoint is disabled; its liveness listener binds container loopback `127.0.0.1:8080`. HTTP/3/UDP 443 is not enabled. `www.landvilla.in` redirects to `https://landvilla.in`; it is not a second session origin. HSTS is set without preload or includeSubDomains.

The ordinary bridge requires an approved, collision-checked RFC1918 subnet plus a separate dynamic allocation pool within it. Web's static address must be outside that pool, outside gateway/network/broadcast addresses. This prevents dynamically allocated API/Caddy addresses from consuming the proxy identity during initial startup or recreation. These declarations do not prove the actual source address: observe it on an isolated host rehearsal before production. No candidate subnet/IP from the separate isolation document is silently approved here.

### Health and resource behavior

| Service | Docker liveness | Dependency readiness | Writable locations / limits |
|---|---|---|---|
| API | HTTP loopback:8000 `/health`, no database/provider check | `/ready`: Mongo ping/hello and R2 HeadBucket, generic 503 on failure | `/tmp` 64 MiB; 1 CPU, 768 MiB RAM, 128 PIDs |
| Web | HTTP loopback:3000 `/health`, validates fixed config | `/ready` calls API `/ready`, requires status 200, discards diagnostics/cookies; 7s deadline leaves headroom above API's 5s and below Caddy's 8s | `/tmp` 64 MiB; `/app/.next/cache` 128 MiB owned by 1000; 1 CPU, 768 MiB RAM, 128 PIDs |
| Caddy | HTTP loopback:8080 `/health` | Active Web `/ready` check every 15s, 8s timeout, status 200 | Persistent named `/data` and `/config`; `/tmp` 32 MiB; 0.5 CPU, 256 MiB RAM, 64 PIDs |

Caddy refuses public `/health` and `/ready` paths. Active readiness withdraws Web after a failed check; failure detection is not instantaneous and initial health state is not a substitute for the explicit pre-publication readiness gate below. Docker dependency startup uses liveness; readiness is checked separately before Caddy starts. Docker healthchecks mark status; they do not automatically restart an unhealthy process. `unless-stopped` restarts exited processes. Restart/reboot readiness and any separate firewall startup dependencies remain untested. Memory figures are starting limits, not capacity acceptance; tmpfs counts toward memory usage. All services have 40s stop grace and rotated JSON-file logs (10 MiB x 3). Caddy retains only NET_BIND_SERVICE beyond dropped capabilities; its official image runs as root with read-only rootfs. Validate this image/volume behavior on Linux.

## Required configuration

Keep two external access-controlled files, for example `/etc/landvilla/compose.env` (operator settings) and `/etc/landvilla/backend.env` (API secrets). Neither belongs in Git or a build context. `deploy/.env.example` lists names with deliberately blank required values. The preparation did not create external files or read existing credentials.

| Operator setting | Required value / evidence |
|---|---|
| `LANDVILLA_ENV_FILE` | Absolute API secret-file path, accessible only to the deployment operator/root |
| `LANDVILLA_DOCKER_SUBNET` | Canonical RFC1918 CIDR, collision-checked against host/Docker/VPC/VPN/peering/Atlas routes |
| `LANDVILLA_DOCKER_DYNAMIC_RANGE` | Canonical child CIDR in that subnet with at least four usable dynamic addresses; exclude static Web IP |
| `LANDVILLA_WEB_PROXY_IP` | Exact verified private Web IPv4 source; assigned to Web AND API `FORWARDED_ALLOW_IPS` |
| `LANDVILLA_API_IMAGE`, `LANDVILLA_WEB_IMAGE` | Reviewed `repository@sha256:<verified-digest>` references for release/rollback. Tags accepted only by the explicit pre-build checker mode, not release acceptance. No digest has been invented or selected here. |
| `LANDVILLA_CADDY_IMAGE` | Reviewed official `caddy:2.11.9-alpine@sha256:<verified-manifest-digest>` or separately revalidated version; no fabricated digest, no latest tag |
| `LANDVILLA_ACME_EMAIL` | Monitored certificate operations email |
| `NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID` | Optional public OAuth web audience at BUILD time; blank disables Google UI. Must match a backend audience when enabled. Rebuild to change it. |

API secret file: `MONGO_URL` (Atlas TLS/SRV URI), `DB_NAME`, `STORAGE_PROVIDER=cloudflare_r2`, `S3_ENDPOINT` (HTTPS origin), `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, optional `S3_REGION=auto`, `IDENTITY_ENABLED=true`, and a securely generated `OTP_HMAC_SECRET` of at least 32 characters. `GOOGLE_CLIENT_IDS` is needed for enabled Google login. Configure approved email/SMS senders using the existing SMTP/Twilio variables only for intended channels. Index/identity prerequisites must already be satisfied; no startup provisioning is authorized.

Compose fixes API `APP_ENV=production`, `PYTHON_DOTENV_DISABLED=1`, `TRUSTED_HOSTS=api,127.0.0.1`, `CORS_ORIGINS=https://landvilla.in`, `WEB_APP_ORIGINS=https://landvilla.in` and the exact proxy address. It forces all three seed flags, `ALLOW_LIVE_PAYMENTS`, `GOOGLE_PLAY_BILLING_ENABLED` and `REFUNDS_ENABLED` false, and clears Razorpay keys/webhook secret. This disables test Razorpay processing as well as live processing. Never add provider secrets to public Next variables, build args, Caddy or Web env.

Web gets only `NODE_ENV=production`, `WEB_ORIGIN=https://landvilla.in`, `BACKEND_ORIGIN=http://api:8000`, `BACKEND_TRANSPORT=private-http`, bind/port and telemetry settings. No API env_file is attached. Backend URL may not be overridden through `extra_hosts`, external links, user input or alternate Compose files. The checker reviews the repository Compose model only; do not append unreviewed overrides to deployment commands.

## Verified local results

| Check | Result |
|---|---|
| Python 3.12.10 offline backend unittest suite | **200 passed** in the isolated upgraded environment, actual Uvicorn middleware + fake database/provider boundaries; no live tests |
| Node 24.21.0 web suite | **112 passed**, including strict cookie duplicates, public identity isolation and build artifact/environment checks |
| Deployment model tests, official Compose v5.7.1 | **23 passed**, daemon-free `config`, synthetic env only; official Windows executable SHA-256 verified. Engine 25 execution remains untested. |
| Native Caddy v2.11.9 tests | **5 passed**, adapted routes with ephemeral loopback echo upstream; forwarding/Origin/cookies, encoded probe paths, www redirect, active health withdrawal/recovery verified. The harness changes listener/upstream/timing, disables automatic HTTPS and removes strict SNI for synthetic HTTP; real TLS/SNI is not exercised. |
| Caddy configuration | `caddy adapt --validate` passed; official Windows archive SHA-512 verified against release checksum. No production Caddy listener or certificate issuance. Validation can briefly initialize its active health probe; no application/production backend was started. |
| Web lint / TypeScript | `eslint . --max-warnings 0` and `tsc --noEmit` passed |
| Web production build | Next standalone build passed in an ignored repository-local copy excluding every `.env*`; static/public assets prepared. No existing environment file was moved or read. |
| Backend dependency compatibility / syntax | Upgraded environment `pip check`, clean final requirements resolution and Python compilation passed. PyPI version metadata reported zero advisories for 36 tested runtime distributions; npm bulk advisory metadata reported none for 55 production package entries. These are dated feed observations, not proof of absence of vulnerabilities. No backend linter/typechecker is configured. |
| Diff whitespace | `git diff --check` passed; Git emitted only normal LF/CRLF conversion notices |
| Docker Linux builds / runtime | **NOT RUN**: local Docker Desktop Linux engine unavailable. Compose parsing does not prove builds, filesystem permissions, memory limits, health, binding or TLS on EC2. |

The native Caddy test is intentionally a synthetic local HTTP harness; it does **not** validate public TLS, certificate renewal, Linux image behavior or real proxy source IP. Full backend tests use in-memory seeded fixtures only; no production seeds/data changes occurred. Old live `backend/tests/test_*.py` suites were not run because they target real/preview services and may mutate records. Logs/builds/downloaded validation binary are ignored under repository `.cache`.

## Unresolved blockers and acceptance gates

1. **Dependency release acceptance:** code requirements now use compatible FastAPI 0.133.0, Starlette 1.3.1 and PyMongo 4.18.3, verified in a separate Python 3.12 environment. The three originally reported Starlette advisories and later reported Starlette/PyMongo advisories are outside the selected versions' affected ranges; see the Phase 2 advisory table and behavioral tests. Existing `backend/.venv` and the historical Emergent freeze still contain older pins and are NOT release inputs. Rebuild clean Linux images from revised requirements, scan exact artifacts, and repeat advisory checks before rehearsal/release. No running deployment has been patched or certified.
2. **Host/network identity:** final subnet/dynamic pool, complete collision evidence, actual Web source IP at API, service DNS, IPv6 behavior, no direct public Web/API reachability, Docker recreation/reboot behavior and exact supported Compose version on Engine 25 remain unverified. No proxy address is approved by this repository change.
3. **Linux image acceptance:** build both Dockerfiles on the target architecture, pin/scan images, verify read-only operation, writable cache/TLS volumes, secrets exclusion, uploads, timeouts, resource sizing and graceful shutdown. Existing production dependency pins must resolve on clean Python 3.12 Linux; local installed compatibility alone is insufficient.
4. **DNS/TLS:** prerequisites below and real certificate issuance/renewal remain unverified. No DNS or firewall changes were performed.
5. **Dependency and browser acceptance:** isolated staging transaction privileges and synthetic-object rights, private R2 policy, backup restore, legal approval, correct OAuth/OTP channels, full browser signup/login/admin/logout, session renewal/revocation, CSRF failures, private media and outage/recovery must pass. No production test writes.
6. **Abuse controls:** no client IP is relayed. API IP throttles aggregate users behind Web. Recipient/account checks remain; load/abuse acceptance and separately reviewed edge limiting are required. Do not solve this by trusting caller `X-Forwarded-For`.
7. **Ingress scope:** browser proxy rejects native Bearer credentials and does not expose payment webhooks. Android/direct API clients and callbacks require a separate approved design. Billing stays disabled; this preparation does not make the entire native ecosystem deployable.
8. **Directional isolation:** the four-network/firewall proposal remains unapplied and unproven. Its required host-policy, persistence, cold-start and rollback approval gates are not closed by this ordinary bridge configuration. Do not publish if launch requires that policy.

## DNS and TLS prerequisites (operator work, not performed)

- Both `landvilla.in` and `www.landvilla.in` resolve publicly to the approved EC2 endpoint, with stable address ownership. Remove stale AAAA records only through a separately authorized DNS change if the host has no working IPv6; no DNS edits are included here.
- Public TCP 80/443 already reach only intended Caddy publication; ports are not occupied by other services. Do not widen security groups or firewall rules from this runbook. Validate existing routing/permissions.
- Use direct DNS-to-Caddy for this design. An upstream CDN/load balancer needs its own reviewed TLS/header/health model; no upstream proxy addresses are trusted by Caddy.
- CAA policy, if present, must permit the selected ACME issuer. Host clock, DNS resolution and outbound ACME HTTPS must work; no Cloudflare DNS token is needed for the HTTP/TLS challenge design.
- Caddy `/data` and `/config` volumes persist across recreation and are privately backed up; certificate/private-key material never enters Git or application images. Test issuance/renewal with staging ACME in a separately reviewed isolated configuration before production issuance. Do not erase volumes on routine rollback.

## Exact future build and startup sequence — NOT EXECUTED

**Stop before this sequence until all blockers above are closed and production deployment is explicitly authorized.** First rehearse with isolated nonproduction dependencies and the approved network allocation; observe the actual Web TCP source at the API and confirm an untrusted peer cannot satisfy HTTPS enforcement. Never substitute `*`, a bridge CIDR or the Caddy IP for the Web peer. The commands below assume the reviewed checkout at `/opt/landvilla`, prepared private files at the paths above, and a compatible installed Docker Compose. They do not install software, modify infrastructure or provision data.

```sh
cd /opt/landvilla
# Fixed -f prevents implicit compose.override discovery. Never print resolved config.
python3 scripts/check-production-compose.py --env-file /etc/landvilla/compose.build.env --allow-build-tags

# Build/review offline artifacts first; this starts no application containers.
docker compose --env-file /etc/landvilla/compose.build.env -f deploy/compose.production.yml build --pull api web
docker compose --env-file /etc/landvilla/compose.build.env -f deploy/compose.production.yml pull caddy
# Record verified image digests and complete security scanning/isolated rehearsal here.
# Prepare compose.env with immutable image references; no fallback to build tags.
python3 scripts/check-production-compose.py --env-file /etc/landvilla/compose.env
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml config --quiet

# Validate the SAME selected Caddy image/config without publishing ports or starting dependencies.
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

# Private services first. --wait is liveness only; no Caddy yet.
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 api web
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml exec -T web node -e 'fetch("http://127.0.0.1:3000/ready",{signal:AbortSignal.timeout(8000)}).then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))'

# Narrow inspection: no Config.Env or broad docker inspect output.
docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$(docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml ps -q web)"
docker inspect --format '{{json .NetworkSettings.Ports}}' "$(docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml ps -q api)"
docker inspect --format '{{json .NetworkSettings.Ports}}' "$(docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml ps -q web)"
# Confirm address equals the previously observed/approved source and ports are unpublished.
# Stop on readiness, identity, secret, host, or binding mismatch.

# Only now publish ingress; requires the separate production approval above.
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 caddy
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml ps
curl --fail --silent --show-error --head http://landvilla.in/
curl --fail --silent --show-error --head https://landvilla.in/
curl --fail --silent --show-error --head https://www.landvilla.in/
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://landvilla.in/health
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' https://landvilla.in/ready
```

Every command is a stop-on-failure step; do not paste as an unattended sequence. Expected: HTTP redirects to HTTPS, www redirects to apex, public probes return 404. Validate the certificate chain, expiry and renewal, malicious Host/forwarding rejection, invalid Origin/missing CSRF, secure cookie flags/deletion, private media authorization and direct Web/API port denial from an independent host. Verify request failures never log credentials. Close acceptance before opening normal user traffic. Caddy admin is disabled: reviewed config changes use container recreation, not an unauthenticated reload endpoint.

### Rollback — operator procedure, NOT EXECUTED

Retain the previous reviewed checkout/Caddyfile, immutable images and compatible secret/settings files before launch. No database restore, migration reversal, index drop, credential printout, volume removal or `down -v` is a rollback step.

```sh
cd /opt/landvilla
# Stop public ingress while investigating or preparing a rollback.
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml stop caddy
docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml stop web api

# In the retained previous checkout, using its reviewed, compatible settings:
cd /opt/landvilla-previous
python3 scripts/check-production-compose.py --env-file /etc/landvilla/compose.previous.env
docker compose --env-file /etc/landvilla/compose.previous.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 api web
docker compose --env-file /etc/landvilla/compose.previous.env -f deploy/compose.production.yml exec -T web node -e 'fetch("http://127.0.0.1:3000/ready",{signal:AbortSignal.timeout(8000)}).then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))'
# Recheck the same network identity/publication constraints before reopening:
docker compose --env-file /etc/landvilla/compose.previous.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 caddy
```

This previous-release example assumes an already validated release of this architecture using the same `landvilla` project/network/volumes. The old API-only Compose is not a safe rollback target. If no previous verified release exists, leave all three stopped; do not fall back to public API binding, disabled HTTPS, broad proxy trust or the unproven firewall plan. Network allocation changes require a separately reviewed rollback plan, not automatic network destruction. Retain persistent Caddy volumes.

## Independent local review commands (safe, no deployment)

```powershell
Set-Location F:\projects\landvilla
git status --short
git diff --check
git diff -- backend deploy docs web scripts tests
Get-Content deploy/Caddyfile
Get-Content web/Dockerfile
Get-Content scripts/check-production-compose.py
# git diff omits untracked files: inspect the complete changed-file list below too.

Set-Location F:\projects\landvilla\backend
$env:PYTHON_DOTENV_DISABLED='1'
..\.cache\phase2-security-review\dependencies\candidate-venv\Scripts\python.exe -m unittest discover -s tests/unit -v
..\.cache\phase2-security-review\dependencies\candidate-venv\Scripts\python.exe -m pip check

Set-Location F:\projects\landvilla
$env:LANDVILLA_TEST_COMPOSE_BINARY='F:\projects\landvilla\.cache\phase2-security-review\compose\docker-compose.exe'
.cache\phase2-security-review\dependencies\candidate-venv\Scripts\python.exe -m unittest tests.test_production_deployment -v
# Locally downloaded official/checksummed validator; substitute your verified path if absent.
$env:CADDY_BINARY='F:\projects\landvilla\.cache\caddy-validation\caddy.exe'
.cache\phase2-security-review\dependencies\candidate-venv\Scripts\python.exe -m unittest tests.test_caddy_configuration -v
$env:ACME_EMAIL='operator@example.invalid'
$env:XDG_DATA_HOME='F:\projects\landvilla\.cache\caddy-validation\data'
$env:XDG_CONFIG_HOME='F:\projects\landvilla\.cache\caddy-validation\config'
& $env:CADDY_BINARY adapt --config deploy/Caddyfile --adapter caddyfile --validate > $null

Set-Location F:\projects\landvilla\web
npm.cmd test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build:verify
```

`build:verify` copies installed dependencies into a fresh ignored repository-local directory because Turbopack rejects an out-of-project node_modules junction. It excludes local env files and supplies synthetic fixed origins; it does not start a server or access Atlas/R2. Ordinary `npm run build` can load developer `.env.local`; use the verification command for independent secret-free checks. Docker builds use `.dockerignore` plus clean `npm ci`. Tests do not supply real deployment secrets. To review actual future settings privately: `python scripts/check-production-compose.py --env-file <external-compose-settings-file>`; it reports check names only and never prints resolved credentials. Do not run bare `docker compose config`, `config --environment`, broad `docker inspect` or shell tracing in a shareable transcript.

## Files changed

The [Phase 2 review](PRODUCTION_SECURITY_REVIEW_PHASE2.md#4-files-modified-by-this-task) distinguishes the 31 files added/edited in Phase 2 from inherited work and includes final Git status, tracked diff statistics and the expanded untracked inventory. The prior untracked isolation plan is preserved unchanged and is not part of these edits. Untracked files must be reviewed explicitly because `git diff` alone omits their contents.

Implementation references: installed Next `dist/docs` standalone/output guidance; [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https), [Docker Compose service controls](https://docs.docker.com/reference/compose-file/services/), and installed Uvicorn 0.25.0 middleware source. Caddy header ordering was checked against [v2.11.9 source](https://github.com/caddyserver/caddy/blob/v2.11.9/modules/caddyhttp/headers/headers.go) and the executable loopback test; no security decision relies only on a string assertion.
