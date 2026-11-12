# LANDVILLA production security review — Phase 2

> Historical Phase 2 evidence below. The later master execution changed authenticated client identity, production target/TLS validation, pinned base digests and rehearsal configuration. Current instructions and results: [master report](PRODUCTION_READINESS_MASTER_REPORT.md), [verification matrix](PRODUCTION_VERIFICATION_MATRIX.md), [deployment runbook](PRODUCTION_DEPLOYMENT_RUNBOOK.md). Earlier statements that Caddy receives no credentials, all caller IP is discarded, or base images remain mutable describe the previous implementation. They are not current acceptance claims.

Evidence date: 12 November 2026. Scope: safe local code remediation and preparation for a separately authorized EC2 rehearsal. This report is not deployment authorization.

## 1. Executive summary

**CONDITIONALLY READY FOR ISOLATED REHEARSAL. Production release remains BLOCKED.**

Preserved the existing uncommitted implementation of Browser → Caddy → Next.js Web/Admin → FastAPI → MongoDB Atlas + Cloudflare R2. Fixed compatible dependency vulnerabilities, WebSocket Host rejection, session-cookie validation, public-read credential isolation, build-environment isolation and health semantics. Strengthened offline Compose validation without choosing network allocations or image digests.

Final local results: **200 backend + 112 Web + 23 Compose + 5 Caddy tests passed (340 total)**. Web lint, TypeScript, standalone production build, Python compilation, dependency compatibility and diff whitespace checks passed. No production services or credentials were used. Linux Docker build/runtime, actual Web-to-API source identity, public TLS and provider/browser acceptance remain unverified.

## 2. Starting Git commit and branch

- Repository: `F:\projects\landvilla`.
- Branch: `dev`.
- Starting and final HEAD: `a1d58b33a23c869617975e70875e922bf75bd11f`.
- No staging, commit, branch creation, checkout, reset, stash, merge, rebase, push or remote changes.

## 3. Existing changes preserved

The initial working tree contained 17 modified tracked files and 17 relevant untracked file/directory entries. Initial status, diff stat, untracked inventory and file hashes were saved in ignored `.cache/phase2-security-review/starting-*` artifacts before edits. Existing modifications were reviewed and extended in place. No starting file was removed. The pre-existing untracked `docs/EC2_DIRECTIONAL_ISOLATION_PLAN.md` has the same SHA-256 as at the start; it was neither rewritten nor implemented.

Actual `.env` values were not opened, printed, copied into artifacts or requested. Existing `backend/.venv` was left unchanged. Dependency experiments and installed candidate packages are under `.cache/phase2-security-review/dependencies/candidate-venv`, inside the repository. Public package/advisory metadata and official validation binaries were retrieved; no AWS, EC2, Atlas, Cloudflare or application production endpoint was contacted.

## 4. Files modified by this task

These are Phase 2 additions/edits relative to the initial dirty-tree snapshot, not all changes relative to HEAD. The complete final Git inventory is appended below.

| Area | Phase 2 files |
|---|---|
| Backend packaging | `backend/.dockerignore`, `backend/Dockerfile`, `backend/requirements-local.txt`, `backend/requirements-production.txt`, `backend/requirements-production-constraints.txt` (new), `backend/requirements.txt` (historical-file warning only) |
| Backend boundaries | `backend/production_runtime.py`, `backend/server.py` |
| Backend tests | `backend/tests/unit/test_production_runtime.py`, `backend/tests/unit/test_runtime_http.py`, new `test_framework_security.py`, `test_host_asgi.py`, `test_host_boundary.py` in the same directory |
| Deployment checks | `deploy/compose.production.yml`, `scripts/check-production-compose.py`, `tests/test_production_deployment.py`, `tests/test_caddy_configuration.py` |
| Web packaging | `web/.dockerignore`, `web/scripts/prepare-standalone.mjs`, `web/scripts/verify-production-build.mjs`, new `production-build-safety.mjs` and `production-build-safety.d.mts` in the same directory |
| Web transport | `web/src/lib/admin-server.ts`, `web/src/lib/health.ts`, `web/src/lib/proxy.ts`, `web/src/lib/server-api.ts`, new `web/src/lib/session-cookie.ts` |
| Web tests | `web/tests/phase2-security.test.ts` (new) |
| Documentation | `docs/RELEASE_OPERATIONS.md`, `docs/PRODUCTION_PROXY_DOCKER_READINESS.md`, this new report |

Existing `deploy/Caddyfile`, Web Dockerfile and isolation plan were reviewed; their contents were not changed in Phase 2. No lockfile/package change was needed for Web.

## 5. Security findings and severity

Severity below is the review's deployment-risk assessment, not a replacement for each advisory's CVSS rating.

| Finding | Severity | Result / limitation |
|---|---|---|
| Vulnerable Starlette framework pins; FastAPI constrained safe upgrades | High | Coordinated FastAPI/Starlette upgrade, tested transitive constraints and regression suite. No assertion that an existing deployment or old virtualenv was patched. |
| Additional PyMongo BSON parser advisory | Medium in this application | Upgraded to patched 4.18.3. Advisory's malformed caller-supplied mmap/array BSON scenario is distinct from normal MongoDB wire decoding. |
| Invalid WebSocket Host used HTTP ASGI rejection events | Medium | Strict middleware now emits WebSocket close 1008; raw ASGI and actual FastAPI tests cover both protocols. |
| Ambiguous/invalid session-cookie attributes and duplicate selection | Medium | Shared strict request/response parser; reject duplicate session cookies/attributes, invalid octets, Domain, unknown attributes and malformed expiry/age. Required Secure/HttpOnly/Path=/SameSite=Lax retained. |
| Build verification inherited environment and could copy nested env assets | Medium | Allowlisted subprocess environment, repository-local temp/home, recursive env-file exclusions and artifact completeness checks. Docker context independently restricted. |
| Release checker accepted mutable application tags and alternate execution inputs | Medium | Digests required by default; tags only in explicit pre-build mode. Reject alternate mounts, entrypoints, build secrets/contexts and service aliases; check exact non-root users. |
| Public metadata/legal reads could unnecessarily carry session identity | Low | They now share the identity-free public-read path; upstream cookies are discarded. |
| Probe success caching and insufficient nested timeout headroom | Low | API successes no-store; Web readiness requires 200 with 7s budget around API 5s, below Caddy 8s. |
| Ordinary shared bridge and aggregate API IP throttles | Open architectural gate | No claim of directional isolation or original client-IP attribution. Requires explicit acceptance and separate controls if needed. |

Limited secret review covered tracked filenames, known credential patterns in tracked text and history filenames for env/private-key/credential paths. Matches in MongoDB setup documents were example password placeholders; no actual secret was identified or printed. This is not a comprehensive historical secret-scanner certificate. No production env file entered Git or a build, and no application secrets were introduced into Web/Caddy or build arguments.

## 6. Dependency advisory status

`backend/requirements-production.txt` is the release input, now including `requirements-production-constraints.txt`. Local requirements include production requirements; test requirements include local requirements plus mongomock. The large old `backend/requirements.txt` Emergent freeze remains historical and explicitly unsupported for release: its vulnerable pins were not silently rewritten. Web runtime pins are in `web/package.json` and `web/package-lock.json`; unrelated native/frontend dependency sets were not upgraded or certified.

| Package | Initially installed | Tested candidate / final requirements |
|---|---|---|
| FastAPI | 0.110.1 | 0.133.0 |
| Starlette | 0.37.2 | 1.3.1 |
| PyMongo | 4.18.2 | 4.18.3 |
| Pydantic | 2.14.1 | 2.14.1 |
| Uvicorn | 0.25.0 | 0.25.0 |
| HTTPX | 0.28.1 | 0.28.1 |
| python-multipart | 0.0.32 | 0.0.32 |
| Motor | 3.7.1 | 3.7.1 |

FastAPI 0.110.1 requires Starlette `>=0.37.2,<0.38.0`; forcing a patched modern Starlette onto it is incompatible. [FastAPI 0.133.0 explicitly adds Starlette 1+ support](https://github.com/fastapi/fastapi/releases/tag/0.133.0), with metadata requiring Starlette `>=0.40.0` and Pydantic `>=2.7.0`. Exact pins were selected together, not installed with dependency checks bypassed. Installed metadata, clean resolution, `pip check` and all 200 backend regressions validate this Windows/Python 3.12 combination. Parsing limits, routing URL authority and actual application startup/shutdown lifecycle have additional behavior tests; existing authentication, CSRF, uploads and browser HTTP tests also pass.

| Official advisory | Patched version | Assessment for selected pins |
|---|---|---|
| [GHSA-f96h-pmfr-66vw](https://github.com/Kludex/starlette/security/advisories/GHSA-f96h-pmfr-66vw), multipart non-file field DoS | Starlette 0.40.0 | 1.3.1 outside affected range; added oversized non-file form regression. Host middleware alone would not fix this. |
| [GHSA-2c2j-9gv5-cj73](https://github.com/Kludex/starlette/security/advisories/GHSA-2c2j-9gv5-cj73), multipart file spool rollover blocks event loop | Starlette 0.47.2 | 1.3.1 outside affected range; no claim of independent load/DoS reproduction. |
| [GHSA-86qp-5c8j-p5mr](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr), Host URL poisoning | Starlette 1.0.1 | 1.3.1 plus strict authority regression coverage. |
| [GHSA-wqp7-x3pw-xc5r](https://github.com/Kludex/starlette/security/advisories/GHSA-wqp7-x3pw-xc5r), Windows StaticFiles UNC credential exposure | Starlette 1.1.0 | 1.3.1 outside affected range; Windows-specific issue is not a claimed Linux exploit. |
| [GHSA-x746-7m8f-x49c](https://github.com/Kludex/starlette/security/advisories/GHSA-x746-7m8f-x49c), HTTPEndpoint method dispatch | Starlette 1.1.0 | 1.3.1 outside affected range; app does not use this endpoint class. |
| [GHSA-jp82-jpqv-5vv3](https://github.com/Kludex/starlette/security/advisories/GHSA-jp82-jpqv-5vv3), malformed scope path changes URL authority | Starlette 1.3.0 | 1.3.1; added direct malformed-path URL regression. |
| [GHSA-82w8-qh3p-5jfq](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq), urlencoded limits ignored | Starlette 1.3.1 | 1.3.1; field-count and field-size behavior tests pass. |
| [GHSA-98qm-wvgf-w4cf](https://github.com/advisories/GHSA-98qm-wvgf-w4cf), BSON Regex out-of-bounds read | PyMongo 4.18.3 | Upgraded from 4.18.2; no unsafe parser exploit was run. |

The selected 36-package Python runtime closure is recorded in `.cache/phase2-security-review/dependencies/candidate-runtime-tree.json`. Public PyPI per-version vulnerability metadata reported **zero advisory entries** for those versions; evidence is `candidate-runtime-advisories.json`. A public npm bulk advisory query for 55 production lockfile package entries also returned zero (`web-runtime-advisories.json`). These are dated feed observations, not comprehensive vulnerability proof, and exclude OS images and unrelated native/frontend trees. The old local virtualenv and historical freeze remain vulnerable release inputs and must not be reused. Clean Linux resolution, image scanning, supply-chain review and a fresh advisory check are still required.

## 7. Host and proxy security findings

Strict Host validation rejects missing/duplicate Host, non-ASCII, control/invalid characters, malformed labels and IPv4, credentials/path/query/fragment injection, empty ports, nonnumeric ports and ports outside 1–65535. Canonical `api` and `api:8000`, and loopback probe `127.0.0.1:8000`, pass; unknown public hosts fail. IPv6 Host literals and trailing-dot/uppercase variants are deliberately not accepted. WebSocket invalid/untrusted authorities close with 1008; lifespan events pass through.

The actual built middleware stack is tested: StrictTrustedHost is the **outermost application/user middleware**, outside CORS, browser guards and request middleware. Starlette's framework ServerErrorMiddleware and Uvicorn's external ProxyHeaders wrapper still enclose it. Do not call it literally outside every ASGI wrapper. It rejects before URL-sensitive application decisions, DB access and CORS processing.

Production proxy configuration accepts only explicit canonical RFC1918 IPv4 literals: no wildcard, CIDR, public, loopback or hostname entries. Compose sets one exact address shared with Web's static allocation; the checker verifies equality and allocation validity. **That declaration does not prove the actual peer source address at API.** Measure it during the later rehearsal, including recreation/reboot, before accepting trust.

Only generated `X-Forwarded-Proto` is needed for the API's HTTPS scheme. Uvicorn 0.25.0 can also process X-Forwarded-For from its trusted peer; this capability was not described as disabled. Caddy deletes client-IP claims and every Web-to-API transport builds fresh allowlisted headers without forwarding them. Thus the API retains the Web peer as client address. Forwarded host/real IP/Forwarded values cannot supply application authority or cookie scope. The authorized Web service remains part of the trusted computing base. Compromising it is not mitigated by these header checks.

HTTPS enforcement remains enabled for application traffic. Internal probe exceptions do not bypass strict Host validation. Existing CORS, unsafe Origin/Referer, Fetch Metadata, CSRF and host-only browser sessions remain covered by regressions; no synthetic browser Origin is invented.

## 8. Caddy review

The existing exact Caddyfile was retained. Official [request_header semantics](https://caddyserver.com/docs/caddyfile/directives/request_header) support suffix wildcard deletion. Native **Caddy v2.11.9** adapter and loopback behavior tests verified `request_header -X-Forwarded-*`, including an arbitrary custom suffix, before reverse-proxy replacements. Deletion in request_header is intentional: putting a wildcard delete alongside generated header_up values would risk removing replacements. [Reverse proxy documentation](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) and the versioned adapter behavior underpin this conclusion.

| Control | Evidence / remaining limit |
|---|---|
| Automatic HTTPS / ACME | Both apex and www are named TLS sites; [automatic HTTPS](https://caddyserver.com/docs/automatic-https) supplies issuance and HTTP redirects. Real ACME/TLS/renewal not run. |
| Canonicalization / SNI | www 308 points to HTTPS apex, preserving URI; native HTTP route test passes. `strict_sni_host on` adapts correctly; real SNI mismatch handshake not exercised. |
| HSTS / request bound | Apex has one-year HSTS without preload/includeSubDomains; body cap adapts to 12,000,000 bytes. Actual Linux upload/load behavior remains a gate. |
| Header trust | Caller X-Forwarded-* deleted, then Host/X-Forwarded-Host=`landvilla.in` and scheme=`https` generated. Forwarded/X-Real-IP/X-Forwarded-For absent upstream. Origin, Referer, Cookie, CSRF and secure response cookie survive native echo test. |
| Readiness | Direct Web `/ready`, Host apex, every 15s, timeout 8s, status 200, fail/pass thresholds 1. Accelerated native harness demonstrates withdrawal/recovery. Initial health is not proof of readiness. |
| Public diagnostics | Public /health and /ready plus descendants blocked with 404, including tested encoded paths. Active upstream probes bypass that public handler and have no startup circular dependency. |
| Liveness / admin | Only `127.0.0.1:8080` liveness; admin off, config persistence off. Adapted JSON checked. |
| Filesystem / privilege | Persistent /data and /config, read-only root, /tmp tmpfs, only NET_BIND_SERVICE capability retained, no-new-privileges. Official image runs root; Linux permissions/capability acceptance not run. |
| Shutdown / logging | 30s Caddy grace, 40s Compose stop grace; access/error request logs excluded. Native test server shut down; target container shutdown and log redaction remain acceptance checks. |

Exact `adapt --validate` passed using the official Windows binary; downloaded archive SHA-512 matched the official release checksums. No image/digest was invented. Validation may initialize an active health probe against the configured local service name; it did not start application services or perform certificate issuance. The five native tests use only ephemeral loopback HTTP listeners and synthetic echo data. Their adapted test model changes listener/upstream and health timing, not public production TLS. A dependency outage intentionally withdraws the whole Web upstream; assess that availability tradeoff and monitor recovery. Docker health status does not create a restart loop by itself.

## 9. Docker Compose review

Official **Compose v5.7.1 Windows** executable downloaded within `.cache/phase2-security-review/compose`; SHA-256 matched its release checksum. Daemon-free `config` and 23 tests verify interpolation/required variables, env_file precedence, YAML model and security controls. Installed Compose v5.6.0 was not used for the final target-version test. Docker Engine 25 runtime/API negotiation with v5.7.1 was **not tested**; successful config parsing is not daemon compatibility evidence. See [Compose service reference](https://docs.docker.com/reference/compose-file/services/).

Only Caddy publishes TCP 80/443. API/Web have no published ports; API EXPOSE metadata alone is not host publication. Secret env_file attaches only to API; explicit Compose environment overrides unsafe inherited seed/billing/proxy values. No application secrets reach Web or Caddy. Public Google client ID is the only permitted build argument. Fixed `http://api:8000` transport, exact UIDs 10001/1000, dropped capabilities, no-new-privileges, readonly roots, bounded tmpfs/resources/PIDs, restart and rotated logs are checked.

Required subnet, child dynamic pool and static Web IP have no deployment defaults. Checker rejects noncanonical/out-of-range allocations and Web inside the dynamic pool; host/VPC/VPN/peering collisions cannot be proven offline. Synthetic addresses and fake digest strings occur only in tests and are **not deployment recommendations**. No network allocation was selected.

Release mode requires immutable API/Web/Caddy digest references. `--allow-build-tags` explicitly validates pre-build declarations only and cannot certify a release. Actual image existence/provenance/scan and Dockerfile base-image digests remain blockers: Dockerfiles still name Python 3.12 and Node 24 tags, and no unverified digest was fabricated. Rejecting alternative mounts/entrypoints/build inputs and service aliases prevents a superficially valid model from bypassing reviewed runtime paths. Caddy's two writable volumes are preserved. Dependency startup uses API then Web liveness; Caddy readiness does not hold their startup hostage.

**An ordinary Docker bridge is not directional isolation.** Caddy-to-API or API-to-Web denial, restricted egress, host-local denial and firewall persistence are neither configured nor claimed. The separate isolation plan remains unapproved/unimplemented.

## 10. Web container review

Node 24 multi-stage Dockerfile uses clean `npm ci`, Next standalone output, copied public and `.next/static`, USER node/UID 1000, `HOSTNAME=0.0.0.0`, PORT 3000 and node server.js. Production start script binds the same defaults. Native Next 16.4.3 build passed with Node 24.21.0; required server/manifest/static artifacts exist. Docker build/runtime was unavailable and is not inferred from this result.

Docker context allowlist excludes local node_modules, generated output, env files and key/credential patterns. Only reviewed source/config/assets/build helper scripts enter it. Build verifier recursively excludes env entries, strips ambient secret/Node hook/proxy/npm configuration variables, uses synthetic public config and returns nonzero on build/preparation failure. Public OAuth ID may be embedded in browser assets by design; it is not a secret. No backend/database credential is a build input.

Compose grants only bounded /tmp and UID-owned `.next/cache` writes; actual Linux caching, permissions, dependency native modules, memory use, signal handling and artifact/image secret inspection still require rehearsal. Existing developer `.env.local` remains untouched.

## 11. API transport and session review

All server transports use validated fixed backend origin, generated public scheme, redirect rejection and bounded timeouts. Production public origin must be HTTPS. The sole private HTTP exception is the exact string `http://api:8000` plus explicit `private-http`; alternate host/port/URL suffix/external HTTP fails. No browser-selected upstream URL or caller forwarding headers enter the API request.

Public property, metadata and legal reads omit session and CSRF identity and discard upstream Set-Cookie. Admin/session reads select one validated host-only session cookie and still require backend authorization; responses are no-store. Duplicate request cookies fail closed in SSR and proxy paths. Response cookies require exact name, valid value, unique known attributes, HttpOnly, Path=/, SameSite=Lax and production Secure. Domain is prohibited; expiry/deletion values remain supported.

Original Origin/Referer/Fetch Metadata/CSRF checks and request-body/media restrictions remain effective. Existing upload size, content-type, disposition/nosniff and authorization regressions pass. Redirects and internal upstream errors do not become browser-visible provider details. Native Bearer clients and payment callbacks are outside this browser proxy's supported ingress; they are not newly exposed.

## 12. Readiness review

API `/health` is dependency-free and no-store. API `/ready` wraps Mongo ping/hello and R2 HeadBucket in a 5s coroutine deadline with a short-lived bounded-timeout R2 client; generic no-store 503 on failure, client closed on exit. Tests assert read-only command names and success/timeout sanitization. Threaded provider I/O uses bounded connect/read attempts; a real host DNS/TLS/outage exercise remains necessary.

Web `/health` validates config without backend I/O. Web `/ready` uses 7s, rejects redirects, requires exactly 200, cancels the upstream body and emits only generic status. No upstream diagnostic, cookie, connection string or hostname is returned. Caddy's loopback liveness is independent; dependency readiness interval is 15s/8s. No health operation writes to a database or bucket. **Ping/hello does not prove transaction privileges or successful writes; HeadBucket does not prove object write/read rights or bucket privacy.** Docker marks unhealthy processes; unless-stopped restarts exited processes, not each failed healthcheck.

## 13. Tests executed with exact results

| Check | Final result / evidence |
|---|---|
| Entire offline backend `tests/unit` suite | 200 passed, 40.466s; `.cache/phase2-security-review/backend-tests.log` |
| Web Node test suite | 112 passed, 0 failed/skipped; `.cache/phase2-security-review/web-tests.log` |
| Compose + native Caddy unittest suites | 23 + 5 passed, 0 skipped, 2.395s final run; `.cache/phase2-security-review/deployment-tests.log` |
| Web lint | `eslint . --max-warnings 0`: exit 0 |
| Web TypeScript | `tsc --noEmit`: exit 0 |
| Web production build | `npm.cmd run build:verify`: exit 0; 11 static pages, dynamic health/ready; `.cache/phase2-security-review/web-build.log` |
| Python compilation | Changed production Python and all unit/review test files: exit 0 |
| Dependency compatibility | Candidate `pip check`: “No broken requirements found.” |
| Clean requirements resolution | `pip install --dry-run --ignore-installed ... -r backend/requirements-test.txt`: exit 0; `dependencies/final-resolution.json` and `.log` |
| Caddy exact config | v2.11.9 `adapt --validate`: exit 0 |
| Git whitespace | `git diff --check`: exit 0, only normal LF/CRLF notices |

Independent review commands (PowerShell; separate steps, stop on failure; no containers/services):

```powershell
Set-Location F:\projects\landvilla
git status --short
git diff --stat
git diff --check
git diff -- backend deploy docs web scripts tests
git ls-files --others --exclude-standard
# Git diff omits untracked contents; inspect the file inventory below as well.

$reviewPython='F:\projects\landvilla\.cache\phase2-security-review\dependencies\candidate-venv\Scripts\python.exe'
$env:PYTHON_DOTENV_DISABLED='1'
Set-Location F:\projects\landvilla\backend
& $reviewPython -m unittest discover -s tests/unit -v
& $reviewPython -m pip check

Set-Location F:\projects\landvilla
$env:LANDVILLA_TEST_COMPOSE_BINARY='F:\projects\landvilla\.cache\phase2-security-review\compose\docker-compose.exe'
$env:CADDY_BINARY='F:\projects\landvilla\.cache\caddy-validation\caddy.exe'
& $reviewPython -m unittest tests.test_production_deployment tests.test_caddy_configuration -v
& $reviewPython -m compileall -q backend/production_runtime.py backend/server.py backend/tests/unit scripts/check-production-compose.py tests/test_production_deployment.py tests/test_caddy_configuration.py

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

The cached executables/environment are local evidence, not committed release artifacts. On another checkout, create a fresh repository-local Python 3.12 virtualenv from `backend/requirements-test.txt`, install Web's lockfile with Node 24, and obtain independently verified official Caddy 2.11.9/Compose 5.7.1 binaries. Do not use the old backend virtualenv. Native Caddy tests are opt-in via CADDY_BINARY; the recorded run supplied it and skipped nothing.

Clean dependency resolution was also executed with the equivalent explicit command below, under a sanitized environment using repository-local cache/temp and no pip credentials/config. It contacts only public PyPI and installs nothing:

```powershell
& $reviewPython -m pip install --dry-run --ignore-installed --index-url https://pypi.org/simple --report .cache/phase2-security-review/dependencies/final-resolution.json -r backend/requirements-test.txt
```

## 14. Checks not performed and why

- Linux Docker builds, image startup, container health, UID/read-only/tmpfs/capability/limit/graceful-stop behavior: local Docker Desktop Linux engine unavailable. No Docker build/pull/up/start was performed.
- Engine 25 with Compose v5.7.1 runtime negotiation, EC2/host route/collision/source-IP observation, public port reachability: require approved isolated host access; none was used.
- Real TLS/SNI mismatch, ACME issuance/renewal, DNS correctness, provider permissions/privacy, backup restore and full real-browser signup/admin/media flows: require external configuration and separate acceptance. No production credentials or cloud access.
- Old live `backend/tests/test_*.py` integration scripts: intentionally not run; they target real/preview services and may mutate records. This is a scope restriction, not suppression of failures in the offline regression suite.
- Backend lint/static typing: no configured project checker; Python compilation and regression tests were run. Full OS/container, native/frontend and development-dependency vulnerability audits were not claimed.
- No database migrations, index application, provisioning, seeds, provider writes, payment/refund/billing tests or production startup commands.

## 15. Remaining production blockers

1. Clean target-architecture Linux images, exact reviewed base/release digests, supply-chain/security scans, native-package resolution and runtime acceptance. Existing local env/legacy freeze is not an acceptable fallback.
2. Approved network allocation and collision evidence; actual API-observed Web source address, positive/negative trust controls, no public Web/API ports and recreation/reboot behavior. No guessed IP is accepted.
3. Supported Engine 25 / Compose v5.7.1 runtime; bounded resources, cache/TLS persistence, signal drain, restart and readiness outage recovery under realistic load.
4. DNS for apex/www, valid monitored ACME contact, CAA/routing/port prerequisites, real TLS/SNI/renewal, stable endpoint and IPv6 consistency. No DNS/security-group edits are authorized by this report.
5. Isolated provider and full browser acceptance: transaction/object rights, private storage, restore drill, OAuth/OTP, session lifecycle, CSRF, admin/media authorization and legal/content approval. Any writes require separate nonproduction authorization.
6. Aggregate IP-rate-limit behavior and edge abuse policy; native client/webhook ingress if required. Payments, refunds and Play billing remain disabled.
7. Directional isolation, if required for launch: separately approve and test the existing proposal. Ordinary bridge checks do not close that gate.

## 16. EC2 rehearsal prerequisites

Obtain separate authorization for an isolated rehearsal with nonproduction dependencies and an approved network plan. Use reviewed images/settings with no secrets in build inputs or terminal output; run the sanitized Compose checker and exact-image Caddy validation before startup. The operator startup sequence, DNS/TLS prerequisites and environment names are in [PRODUCTION_PROXY_DOCKER_READINESS.md](PRODUCTION_PROXY_DOCKER_READINESS.md). Those commands are proposed future operator actions, not actions taken here.

Before enabling ingress, measure the **actual TCP source IPv4 observed inside the API network namespace** for a Web-generated request. Use bounded connection metadata only (no payload/headers/cookies); record address and method, including a genuine Web request as positive control and an untrusted peer as negative control. Compare to static allocation and FORWARDED_ALLOW_IPS; stop on mismatch instead of broadening trust. Docker inspect alone reports configured allocation and is insufficient. Repeat after service recreation and host restart. Do not capture real user traffic or modify routing/firewalls for this check without separate approval.

Then verify liveness/readiness, unpublished application ports, Host/forwarding rejection, permissions/read-only operation, resource/logging bounds, outage recovery and TLS persistence on the isolated host. Full browser/provider tests must use approved synthetic accounts/data and cannot be inferred from local mocks.

## 17. Rollback limitations

No rollback was performed. Retain a separately validated prior checkout, immutable image digests and compatible private settings before deployment. Preserve Caddy data/config volumes and stop ingress on failed gates. Never roll back by publishing API ports, disabling HTTPS, broadening proxy trust, restoring live databases, dropping indexes or deleting volumes. The original API-only Compose and vulnerable framework pins are not automatically approved rollback targets. If no verified compatible prior release exists, leave services stopped pending review. Network allocation changes need their own tested rollback; this task has not approved one.

## 18. Final release verdict

**CONDITIONALLY READY FOR ISOLATED REHEARSAL**, subject to the explicit prerequisites above. **Production deployment is BLOCKED.** Code-level safeguards and mocked/native local checks are verified; Linux, actual network identity, TLS, providers and operational acceptance are not. No commit, push, deployment, cloud mutation or production startup was performed.

## Independent dependency verification — 12 November 2026

This is a separate verification run requested after Phase 2, not a repetition of the implementation. **Overall verdict: Dependency remediation partially verified.** The selected dependency remediation is verified in a clean Windows/Python 3.12 environment, including current advisory checks and actual application regressions. Production Linux artifact/runtime verification remains blocked by the unavailable local Docker engine. No dependency, application, test or Docker configuration was changed during this verification.

### Inputs and production installation path

All four requirements files, the production constraints, backend Dockerfile/.dockerignore, this report and RELEASE_OPERATIONS.md were independently inspected:

| Input | Verified role |
|---|---|
| `backend/requirements.txt` | Historical Emergent freeze, explicitly unsupported. Still contains FastAPI 0.110.1 / Starlette 0.37.2 / PyMongo 4.18.2; these remain vulnerable and must not be installed as release inputs. Not installed in this verification. |
| `backend/requirements-production.txt` | Twelve exact direct runtime pins, including FastAPI 0.133.0 / Starlette 1.3.1 / PyMongo 4.18.3; `-c requirements-production-constraints.txt` applies the exact transitive pins. |
| `backend/requirements-production-constraints.txt` | Twenty-four exact transitive runtime pins. Clean installation matched all 36 direct/transitive versions with no missing or additional runtime package. Pip tooling excluded from that count. |
| `backend/requirements-local.txt` | Includes production requirements and pytest 9.1.1 / pytest-xdist 3.8.0. Does not include the historical freeze. |
| `backend/requirements-test.txt` | Includes local requirements and mongomock 4.3.0. Installing it did not change any production-resolved version. |
| `backend/Dockerfile` | `COPY requirements-production*.txt ./` copies both runtime inputs; `RUN pip install --no-cache-dir -r requirements-production.txt` follows the constraints include. The historical freeze is not the install input. |
| `backend/.dockerignore` | Explicitly permits both production files; excludes the historical/local/test requirements and local virtualenv from the context. |

The Dockerfile install path is **statically verified**, and the same requirements were installed from scratch with pip. An actual Linux Docker build was not run: the explicit local `npipe:////./pipe/dockerDesktopLinuxEngine` check failed because the pipe does not exist. No conclusion about installed contents of a built production image is inferred from source inspection. The Python 3.12 base-image tag remains mutable; verified base/release digests, Linux native wheels, image scanning and runtime acceptance are still release gates.

### Clean environment and exact resolution

A new environment was created from the base CPython **3.12.10** executable, not from either existing virtualenv:

`F:\projects\landvilla\.cache\dependency-independent-verification\run-20261112-01\venv`

Its `pyvenv.cfg` confirms `include-system-site-packages = false`. Production requirements were installed first using public PyPI with cache disabled; `pip check` passed before test dependencies were added. Test requirements were then installed and `pip check` passed again. `pip inspect --local` captured both environments and their complete dependency metadata. All 36 production versions remained unchanged after the test install. Neither `backend/.venv` nor the previous Phase 2 candidate environment was upgraded or reused.

Exact clean production resolution (all packages, including every transitive runtime dependency):

```text
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
boto3==1.43.117
botocore==1.43.122
certifi==2026.10.23
cffi==2.1.1
charset-normalizer==3.5.2
click==8.5.0
cryptography==50.0.2
dnspython==2.9.0
fastapi==0.133.0
google-auth==2.62.0
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.20
jmespath==1.1.0
motor==3.7.1
pyasn1==0.6.5
pyasn1-modules==0.4.2
pycparser==3.12
pydantic==2.14.1
pydantic-core==2.50.1
pymongo==4.18.3
python-dateutil==2.9.0.post0
python-dotenv==1.2.4
python-multipart==0.0.32
requests==2.34.2
s3transfer==0.19.3
six==1.17.0
starlette==1.3.1
typing-extensions==4.16.0
typing-inspection==0.4.4
urllib3==2.8.0
uvicorn==0.25.0
```

The test install additionally resolved colorama 0.4.6, execnet 2.1.2, iniconfig 2.3.1, mongomock 4.3.0, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, pytest 9.1.1, pytest-xdist 3.8.0, pytz 2026.6 and sentinels 1.1.1. These are test tooling, not production packages; their transitive versions are recorded observations rather than a new lockfile. Bootstrap pip was 25.0.1 and was not upgraded.

Installed metadata confirms compatible constraints: FastAPI requires Starlette `>=0.40.0` and Pydantic `>=2.7.0`; Starlette requires AnyIO `>=3.6.2,<5`; Pydantic requires exactly pydantic-core 2.50.1; Motor requires PyMongo `>=4.9,<5`; PyMongo requires dnspython `>=2.7,<3`. HTTPX 0.28.1, AnyIO 4.15.1 and the installed typing packages satisfy the active requirements. No `--no-deps`, forced override or incompatible Starlette pin was used. [FastAPI 0.133.0 release support for Starlette 1+](https://github.com/fastapi/fastapi/releases/tag/0.133.0) agrees with [exact FastAPI metadata](https://pypi.org/pypi/fastapi/0.133.0/json) and [exact Starlette metadata](https://pypi.org/pypi/starlette/1.3.1/json).

### Current advisory evidence

Fresh unauthenticated public queries checked the complete GitHub reviewed advisory results for Starlette, FastAPI and python-multipart, their maintainer advisory indexes, and exact-version PyPI metadata for all 36 installed runtime distributions. No query used production credentials or an environment proxy. The Starlette query contained 10 active records plus 3 withdrawn duplicates; FastAPI had 1 active record plus 1 withdrawn duplicate, with no next result page. All active affected ranges below exclude the selected versions.

| Package / reviewed advisory | Affected range | First patched | Selected status |
|---|---|---|---|
| Starlette [GHSA-f96h-pmfr-66vw](https://github.com/advisories/GHSA-f96h-pmfr-66vw) | `<0.40.0` | 0.40.0 | 1.3.1 unaffected |
| Starlette [GHSA-2c2j-9gv5-cj73](https://github.com/advisories/GHSA-2c2j-9gv5-cj73) | `<0.47.2` | 0.47.2 | 1.3.1 unaffected |
| Starlette [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) | `<=1.0.0` | 1.0.1 | 1.3.1 unaffected |
| Starlette [GHSA-wqp7-x3pw-xc5r](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r) | `<1.1.0` | 1.1.0 | 1.3.1 unaffected |
| Starlette [GHSA-x746-7m8f-x49c](https://github.com/advisories/GHSA-x746-7m8f-x49c) | `<1.1.0` | 1.1.0 | 1.3.1 unaffected |
| Starlette [GHSA-jp82-jpqv-5vv3](https://github.com/advisories/GHSA-jp82-jpqv-5vv3) | `<1.3.0` | 1.3.0 | 1.3.1 unaffected |
| Starlette [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq) | `>=0.4.1,<1.3.1` | 1.3.1 | 1.3.1 unaffected |
| Starlette [GHSA-7f5h-v6xp-fcq8](https://github.com/advisories/GHSA-7f5h-v6xp-fcq8) | `>=0.39.0,<=0.49.0` | 0.49.1 | 1.3.1 unaffected |
| Starlette [GHSA-v5gw-mw7f-84px](https://github.com/advisories/GHSA-v5gw-mw7f-84px) | `>=0.13.5,<0.27.0` | 0.27.0 | 1.3.1 unaffected |
| Starlette [GHSA-74m5-2c7w-9w3x](https://github.com/advisories/GHSA-74m5-2c7w-9w3x) | `<0.25.0` | 0.25.0 | 1.3.1 unaffected |
| FastAPI [GHSA-8h2j-cgx8-6xv7](https://github.com/advisories/GHSA-8h2j-cgx8-6xv7) | `<0.65.2` | 0.65.2 | 0.133.0 unaffected |
| PyMongo [GHSA-98qm-wvgf-w4cf](https://github.com/advisories/GHSA-98qm-wvgf-w4cf) | `>=3.9.0,<=4.18.2` | 4.18.3 | 4.18.3 unaffected |

There is an advisory metadata discrepancy worth retaining: the maintainer pages for f96h and 2c2j list narrower affected ranges (`<0.39.2` and `<0.47.1`) than the GitHub reviewed global records. This verification uses the conservative global ranges matching the first patched versions, 0.40.0 and 0.47.2. Starlette 1.3.1 exceeds both interpretations; the discrepancy does not justify a lower pin.

All nine active [python-multipart advisory records](https://api.github.com/advisories?ecosystem=pip&affects=python-multipart&per_page=100) exclude 0.0.32. The largest first-patched version among them is 0.0.31 ([GHSA-v9pg-7xvm-68hf](https://github.com/advisories/GHSA-v9pg-7xvm-68hf)). Withdrawn framework Content-Type ReDoS duplicates refer to canonical multipart [GHSA-2jv5-9r88-3w3p](https://github.com/advisories/GHSA-2jv5-9r88-3w3p), patched in 0.0.7. Current PyPI exact-version metadata returned **zero active advisory entries and zero yanked releases across all 36 production distributions**. This is dated published-advisory coverage, not proof that no undisclosed vulnerability or OS-image issue exists.

Later Starlette releases contain additional behavior/hardening changes beyond published GHSAs. This review does not claim 1.3.1 contains every upstream fix. No applicable published advisory was found that requires another speculative dependency change. The old Emergent freeze and existing older local environment remain unsuitable release inputs.

### Application behavior and independent test results

The previous 340-test claim is **independently reproduced**, rather than carried forward as an assumption:

| Check actually rerun | This verification result |
|---|---|
| Entire offline backend `unittest discover -s tests/unit -v` in the new environment | **200 passed**, 32.009s; no skipped tests |
| Existing Web test suite, Node 24.21.0 / existing Web installation | **112 passed**, 0 failed/skipped, 1892.4155ms |
| Existing Compose 5.7.1 + native Caddy 2.11.9 suites in the new Python environment | **28 passed** (23 + 5), 1.717s; no skipped tests |
| Four additional independent application compatibility probes | **4 passed**, 2.171s; separate from the original 340 |
| `pip check` immediately after production install | Exit 0, “No broken requirements found.” |
| `pip check` after test requirements install | Exit 0, “No broken requirements found.” |
| Runtime resolution comparison | All 36 versions match requirements/constraints, unchanged by test install |
| Final repository/preservation checks | Only this report changed outside ignored verification artifacts; branch/HEAD and original virtualenv package metadata/records/executables unchanged; no starting file removed |

Thus this run executed **344 passing tests: the original 340 plus 4 supplemental probes**. No test file was edited, weakened or skipped to obtain this result. The extra probes live only in ignored `.cache/dependency-independent-verification/extra_compatibility.py`, not in the committed test suite. Web dependencies were reused because the independent clean installation requirement concerns the backend; no claim of a clean Web install is made.

The original backend suite exercises real application routing, middleware order, HTTP request/response handling, strict Host, Uvicorn proxy-header ASGI wrapper, auth/session/CSRF/CORS/cookies, upload failures and readiness with mocked services. The supplemental probes close specific coverage gaps without changing application behavior:

1. Successful browser OTP authentication with mocked delivery, then actual `/api/uploads` multipart parsing of a synthetic JPEG-signature payload larger than 1 MiB. Instrumentation confirms real SpooledTemporaryFile disk rollover before application read. Mocked storage verifies bytes/type/metadata; the actual file route returns the expected body/headers. This is not a DoS/load benchmark or a live R2 write.
2. Actual production-boundary CORS preflight, session rotation, secure cookie attributes, authenticated profile, invalid-CSRF rejection before storage, untrusted Origin rejection, logout deletion and subsequent authorization failure.
3. Actual router lifespan with the identity fixture enabled, mocked ping/client close, and explicit no-startup-seed assertion. This matters because Starlette 1.0 removed legacy APIs while FastAPI retains its own compatible lifecycle wrappers. [Starlette release notes](https://starlette.dev/release-notes/)
4. Actual application OpenAPI generation including multipart schema, plus Pydantic request-validation failure through the sanitized 422 handler without leaking input values.

WebSocket **ASGI behavior** is covered by existing synthetic FastAPI routes and raw Host rejection tests. The production app defines no WebSocket endpoint, and base Uvicorn requirements install neither websockets nor wsproto. A live WebSocket handshake/message path is therefore not accepted or claimed. If WebSocket service becomes a release requirement, an explicitly selected protocol dependency and wire-level tests are a separate blocker. Existing HTTPX ASGI tests also do not prove a Linux Uvicorn socket deployment or real MongoDB transactions.

Web lint, TypeScript, production build, Python compilation and the previous standalone exact Caddy `adapt --validate` command were **not rerun in this dependency-only verification**; their earlier results remain historical Phase 2 evidence. The native Caddy test suite was rerun and adapted its exact input before exercising loopback HTTP. Both cached validator versions were checked again; Compose executable and Caddy archive checksums matched the previously retrieved official checksum files, and the Caddy executable matched that archive. No Docker container was started.

### Commands and evidence

Evidence directory: `.cache/dependency-independent-verification/run-20261112-01/`. It contains production/test pip installation reports, `pip inspect` metadata, `pip check` logs, each test log and `*-command.json` with exact executable/arguments/cwd/exit status. Current advisory JSON is in sibling `advisories/`, and fresh per-package PyPI metadata is under `run-20261112-01/runtime-metadata/` with summary `runtime-advisory-check.json`. These ignored local files were not committed.

The local orchestrator `.cache/dependency-independent-verification/verify.py` ran child processes with an environment allowlist (OS PATH/SystemRoot/WINDIR/COMSPEC/PATHEXT/processor count only), disabled dotenv/pip config, and repository-local temporary/home/cache directories. No ambient database/provider credentials, proxies or pip tokens were inherited. The following are the exact operation arguments expressed with PowerShell path variables; production installation preceded test installation and checks:

```powershell
Set-Location F:\projects\landvilla
$verificationRoot='F:\projects\landvilla\.cache\dependency-independent-verification\run-20261112-01'
$basePython='C:\Users\ashfa\AppData\Local\Programs\Python\Python312\python.exe'
$verificationPython="$verificationRoot\venv\Scripts\python.exe"

# Already executed in the sanitized child environment; do not overwrite this
# evidence venv when repeating. Choose another unused repository-local path.
& $basePython -m venv "$verificationRoot\venv"
& $verificationPython -m pip install --no-cache-dir --no-input --index-url https://pypi.org/simple --report "$verificationRoot\production-install-report.json" -r backend/requirements-production.txt
& $verificationPython -m pip check
& $verificationPython -m pip inspect --local
& $verificationPython -m pip install --no-cache-dir --no-input --index-url https://pypi.org/simple --report "$verificationRoot\test-install-report.json" -r backend/requirements-test.txt
& $verificationPython -m pip check
& $verificationPython -m pip inspect --local

Set-Location F:\projects\landvilla\backend
& $verificationPython -m unittest discover -s tests/unit -v
Set-Location F:\projects\landvilla\web
& 'C:\Program Files\nodejs\node.exe' 'C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js' test

Set-Location F:\projects\landvilla
$env:LANDVILLA_TEST_COMPOSE_BINARY='F:\projects\landvilla\.cache\phase2-security-review\compose\docker-compose.exe'
$env:CADDY_BINARY='F:\projects\landvilla\.cache\caddy-validation\caddy.exe'
& $verificationPython -m unittest tests.test_production_deployment tests.test_caddy_configuration -v
# Supplemental probe also uses repository-local TEMP/TMP for upload spooling.
& $verificationPython .cache/dependency-independent-verification/extra_compatibility.py
& $verificationPython .cache/dependency-independent-verification/audit_resolved.py

# Read-only check of the explicit local Docker pipe: failed, daemon unavailable.
docker --host npipe:////./pipe/dockerDesktopLinuxEngine version --format '{{.Server.Version}}'
git status --short
git diff --stat
git diff --check
```

Use the supplied cached orchestrator for the same environment isolation, or reproduce that allowlist before running direct commands; do not inherit production credentials. Its `bootstrap` stage deliberately refuses an already existing evidence directory. Running `backend`, `web`, `deployment`, `extra` or `preservation` stages uses the recorded local environment and logs. Advisory requests went only to public GitHub/PyPI; provider tests used in-memory data and mocks.

### Independent verdict and preservation

- **Dependency remediation verified:** intended exact pins/constraints, clean Python 3.12 installation, compatibility metadata, current published affected-range exclusion, all original 340 tests and four supplemental application probes.
- **Dependency remediation partially verified (overall):** production Docker installation is verified as a build instruction, not as an executed Linux artifact. Linux wheels/image contents/native runtime/provider behavior remain unverified acceptance gates.
- **Dependency remediation blocked:** no new vulnerable/incompatible selected runtime package was identified. Production artifact acceptance remains blocked until a separately authorized clean Linux build/scan/runtime check. The historical freeze is still vulnerable and prohibited as a release input; live WebSockets would require separate support and verification if introduced.

Only this report was updated by the independent verification; all new executable/evidence files are ignored and repository-local. File-hash comparison found no changes to dependency files, application code, existing tests, Docker/Compose configuration or the isolation plan, and no removed starting files. Existing backend virtualenv metadata/records/executables retain their starting hashes. Final Git status remains **22 modified tracked files and 26 untracked files**, all inherited paths; nothing is staged. Branch `dev` and HEAD `a1d58b33a23c869617975e70875e922bf75bd11f` are unchanged. `git diff --stat` remains **22 files changed, 522 insertions(+), 81 deletions(-)** because this report is untracked; `git diff --check` passes. The complete path inventory below still applies.

**No existing work was discarded. No commit, push, merge, branch change, AWS/EC2/Atlas/R2/DNS access, production startup or production database write was performed.**

## Final repository evidence

The snapshot below includes inherited changes and Phase 2 work. Git diff statistics omit untracked files, so the expanded untracked list is included separately. Git emitted ordinary LF/CRLF conversion notices; these were not whitespace errors.

### `git status --short`

```text
 M backend/.dockerignore
 M backend/Dockerfile
 M backend/production_runtime.py
 M backend/requirements-local.txt
 M backend/requirements-production.txt
 M backend/requirements.txt
 M backend/server.py
 M backend/tests/unit/test_production_runtime.py
 M backend/tests/unit/test_runtime_http.py
 M deploy/compose.production.yml
 M docs/RELEASE_OPERATIONS.md
 M web/.env.example
 M web/README.md
 M web/next.config.ts
 M web/package.json
 M web/src/app/(public)/legal/[doc]/page.tsx
 M web/src/lib/admin-server.ts
 M web/src/lib/config.ts
 M web/src/lib/proxy.ts
 M web/src/lib/public-transport.ts
 M web/src/lib/published-content.ts
 M web/src/lib/server-api.ts
?? backend/requirements-production-constraints.txt
?? backend/tests/unit/test_framework_security.py
?? backend/tests/unit/test_host_asgi.py
?? backend/tests/unit/test_host_boundary.py
?? deploy/.env.example
?? deploy/Caddyfile
?? docs/EC2_DIRECTIONAL_ISOLATION_PLAN.md
?? docs/PRODUCTION_PROXY_DOCKER_READINESS.md
?? docs/PRODUCTION_SECURITY_REVIEW_PHASE2.md
?? scripts/check-production-compose.py
?? tests/test_caddy_configuration.py
?? tests/test_production_deployment.py
?? web/.dockerignore
?? web/Dockerfile
?? web/scripts/prepare-standalone.mjs
?? web/scripts/production-build-safety.d.mts
?? web/scripts/production-build-safety.mjs
?? web/scripts/start-production.mjs
?? web/scripts/verify-production-build.mjs
?? web/src/app/health/
?? web/src/app/ready/
?? web/src/lib/backend-headers.ts
?? web/src/lib/health.ts
?? web/src/lib/session-cookie.ts
?? web/tests/phase2-security.test.ts
?? web/tests/production-proxy.test.ts
```

### `git diff --stat`

```text
 backend/.dockerignore                         |   1 +
 backend/Dockerfile                            |   2 +-
 backend/production_runtime.py                 |  91 +++++++++++-
 backend/requirements-local.txt                |  13 +-
 backend/requirements-production.txt           |   8 +-
 backend/requirements.txt                      |   3 +
 backend/server.py                             |  10 +-
 backend/tests/unit/test_production_runtime.py |  41 +++++-
 backend/tests/unit/test_runtime_http.py       | 190 +++++++++++++++++++++++++-
 deploy/compose.production.yml                 | 138 +++++++++++++++++--
 docs/RELEASE_OPERATIONS.md                    |  18 ++-
 web/.env.example                              |   6 +-
 web/README.md                                 |   8 +-
 web/next.config.ts                            |   1 +
 web/package.json                              |   4 +-
 web/src/app/(public)/legal/[doc]/page.tsx     |   5 +-
 web/src/lib/admin-server.ts                   |   9 +-
 web/src/lib/config.ts                         |  11 +-
 web/src/lib/proxy.ts                          |  29 ++--
 web/src/lib/public-transport.ts               |   3 +-
 web/src/lib/published-content.ts              |   3 +-
 web/src/lib/server-api.ts                     |   9 +-
 22 files changed, 522 insertions(+), 81 deletions(-)
```

### `git diff --check`

```text
Exit code: 0
No whitespace errors. Standard LF/CRLF conversion notices only.
```

### Full changed and untracked file list

Modified tracked paths (22; all unstaged):

```text
backend/.dockerignore
backend/Dockerfile
backend/production_runtime.py
backend/requirements-local.txt
backend/requirements-production.txt
backend/requirements.txt
backend/server.py
backend/tests/unit/test_production_runtime.py
backend/tests/unit/test_runtime_http.py
deploy/compose.production.yml
docs/RELEASE_OPERATIONS.md
web/.env.example
web/README.md
web/next.config.ts
web/package.json
web/src/app/(public)/legal/[doc]/page.tsx
web/src/lib/admin-server.ts
web/src/lib/config.ts
web/src/lib/proxy.ts
web/src/lib/public-transport.ts
web/src/lib/published-content.ts
web/src/lib/server-api.ts
```

Expanded untracked paths (26; includes the unchanged pre-existing isolation plan):

```text
backend/requirements-production-constraints.txt
backend/tests/unit/test_framework_security.py
backend/tests/unit/test_host_asgi.py
backend/tests/unit/test_host_boundary.py
deploy/.env.example
deploy/Caddyfile
docs/EC2_DIRECTIONAL_ISOLATION_PLAN.md
docs/PRODUCTION_PROXY_DOCKER_READINESS.md
docs/PRODUCTION_SECURITY_REVIEW_PHASE2.md
scripts/check-production-compose.py
tests/test_caddy_configuration.py
tests/test_production_deployment.py
web/.dockerignore
web/Dockerfile
web/scripts/prepare-standalone.mjs
web/scripts/production-build-safety.d.mts
web/scripts/production-build-safety.mjs
web/scripts/start-production.mjs
web/scripts/verify-production-build.mjs
web/src/app/health/route.ts
web/src/app/ready/route.ts
web/src/lib/backend-headers.ts
web/src/lib/health.ts
web/src/lib/session-cookie.ts
web/tests/phase2-security.test.ts
web/tests/production-proxy.test.ts
```

**Confirmation: no commit, push, deployment, cloud mutation or production startup was performed.**
