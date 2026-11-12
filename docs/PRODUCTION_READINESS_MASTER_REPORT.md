# LANDVILLA production readiness master report

Execution date: 12 November 2026. **Production release BLOCKED.** No production deployment or EC2 mutation has occurred. Current executed evidence is maintained in PRODUCTION_VERIFICATION_MATRIX.md; historical Phase2 counts are not current results.

## Verified starting state and preservation

Started in `F:\projects\landvilla`, branch `dev`, HEAD `a1d58b33a23c869617975e70875e922bf75bd11f`, remote `https://github.com/techashfaq/landvilla.git`. There were22 modified tracked files,26 untracked files and0 staged files; diff522 insertions/81 deletions. The preceding read-only audit hashed all48 paths and the index; none changed during that audit. This execution intentionally extends that preserved work. No reset/stash/rebase/branch replacement was used. The existing directional isolation plan remains unchanged.

GitHub read-only API inspection confirmed remote dev at the same starting SHA, public repository, dev default branch, no branch protection and no Actions workflows. A scoped pinned-action CI workflow is now prepared. No branch protection or GitHub settings were changed. Final release commit and actual CI result must be recorded after verification; no earlier SHA is a deployment approval.

## Changes implemented

- Preserved coordinated FastAPI0.133.0/Starlette1.3.1/PyMongo4.18.3 dependency closure. Production Docker installs production requirements plus constraints, not historical freeze/test packages. Node24/Python3.12 bases are pinned to registry-observed manifest digests recorded in deploy/reviewed-base-images.json.
- Enforced production DB/bucket identity and verified Mongo TLS options, including duplicate/semicolon option rejection. An explicit rehearsal tier accepts only fixed local disposable endpoints and HTTPS loopback origin; it cannot select production targets.
- Replaced shared-peer rate buckets with authenticated client-IP attestation: Caddy overwrites X-LV-* and uses its direct TCP peer, authenticates to Web with a dedicated runtime token; Web signs method/path/time/IP with a separate key; API verifies freshness, HMAC, exact Web peer and absence of X-Forwarded-For. It does not alter Host/scheme/authorization. No arbitrary browser forwarding chain is trusted. Production rejects public rehearsal credentials.
- Preserved HTTPS enforcement, strict Host/WebSocket rejection, Origin/Referer/CSRF, secure cookie/session rotation, public identity isolation, admin authorization, bounded upload/media responses and no startup seeds. Added cross-visitor rate-limit regression coverage.
- Browser requests reject redirects; removed refund UI/proxy action while keeping payment records read-only inspectable. Backend payment/refund/Play flags remain false. Expo source unchanged.
- Optional Google preflight now follows enabled audience configuration. Sanitized Compose validation removes ambient interpolation variables. Actual Compose secret values are never printed.
- Implemented separate nonproduction Compose/Caddy, disposable replica/index preparation, bounded storage fixture and authenticated STARTTLS mail catcher. Separate project/network/volumes; loopback-only TLS; no production environment or ACME certificate. Static collision checks do not select an EC2 subnet.
- Promoted four previously ignored compatibility probes into the backend suite, correcting their test-scope environment isolation. Added authenticated identity, target/TLS, rehearsal topology and actual-SDK/mock storage tests.
- Added credential-isolated local verifier, public-registry advisory checker, safe host inspection, exact artifact recorder and GitHub-hosted disposable Linux build/runtime campaign. CI publishes only sanitized evidence, no application images or release.
- Prepared deployment/rollback/operations/rehearsal/external-blocker runbooks. Updated old report banners and README to distinguish historical evidence.

## Security decisions and remaining findings

Production configuration now needs two narrow hop credentials, contrary to the earlier no-Caddy-credential architecture. Caddy still receives no Mongo/R2/OTP credentials; Web receives no provider/database credentials. Keep credentials in private external runtime files, distinct, random, coordinated for rotation. A compromised trusted proxy remains in the trust boundary. Actual observed peer and path behavior must be tested; crypto validation does not prove network isolation. Host/URL/session decisions never consume the client-IP attestation.

No wildcard proxy trust, broad CIDR trust, public API port, TLS-verification bypass, seed enablement, payment enablement or production data operation was introduced. The rehearsal storage fixture deliberately does not validate AWS signatures; it is a test dependency, not production media infrastructure. Rehearsal local Mongo/storage HTTP exceptions are fixed, tier-scoped and incompatible with production target identities.

**High release gates remain:** EC2 source-IP/network behavior, actual Linux artifact acceptance, directional isolation decision/testing, provider identity/permissions, backups/restore, real DNS/TLS/browser acceptance, native bearer ingress and known-good rollback. All are explicit, not waived by unit tests. Mutable base-tag risk was addressed by pinning observed manifests; actual image provenance/scans/runtime remain distinct.

**Operational gates:** capacity/retention, restart/outage/reboot, log redaction, monitoring/on-call ownership, support/legal content approval. Source includes public discovery/search/details/localities, account/saved/enquiry/leads, broker/listings and admin modules; actual browser/provider acceptance remains NOT TESTED. Contact/FAQ intentionally disclose missing approved business content. No fabricated contacts or customer listings were created.

## Current access facts

Subsequent operator inspection through Instance Connect verified AL2023/x86_64,2vCPU/1.9GiB RAM,2GiB swap,16GiB free disk,Engine25.0.18/Compose5.7.1, no containers/projects, and root:0600 API file containing only DB_NAME/MONGO_URL assignments. EC2 remains clean at the starting commit. These are operator-reported findings, not assistant-executed host commands. Seven required API input names are missing, Compose settings are unverified, and capacity headroom is insufficient at configured ceilings. See PRODUCTION_ENVIRONMENT_INVENTORY.md for the complete source mapping and constraints. No EC2 files, Git state or containers were changed; further production actions require explicit approval.

Local Docker Linux named pipe absent: executed connection failed. Existing AWS browser window was visible in inventory, but computer-use URL verification stopped access before any host command. Direct SSH with batch mode, strict host-key checking and bounded timeout failed to connect. User supplied EC2 identifiers are connection context, not fresh host inventory. `scripts/inspect-rehearsal-host.sh` is ready for manual Instance Connect execution; no environment values are printed.

Dependency registry scan on this date observed36 pinned Python packages and55 Web runtime package names with0 active advisory entries and0 yanked Python pins. This is a dated feed observation, not proof of no vulnerabilities. Authoritative original advisory ranges remain below selected Starlette1.3.1: [multipart fields](https://github.com/advisories/GHSA-f96h-pmfr-66vw), [spool rollover](https://github.com/advisories/GHSA-2c2j-9gv5-cj73), [Host poisoning](https://github.com/advisories/GHSA-86qp-5c8j-p5mr).

## Inventory and review scope

All48 inherited changed/untracked files were inventoried in the prior final review and rechecked at execution start. Areas retained: backend runtime/dependencies/Host tests; production Compose/Caddy/template; four deployment/security documents; Compose/Caddy validators; Web Docker/build scripts/config/transports/cookies/probes/security tests. New master-task files are client identity source/tests, retained compatibility probes, rehearsal configuration/fixtures/tests, verification/artifact/inspection/CI tools and seven handover documents. Final Git status/diff is the authoritative full path list; generated evidence stays ignored under .cache. No production environment, key, dump, log or build output is a release source input.

## Release assessment

This report is not a production acceptance certificate. Code/configuration completion and executed local checks are separated from CI Linux evidence and external gates. No known-good production rollback artifact is established. Follow PRODUCTION_EXTERNAL_BLOCKERS.md and the verification matrix; do not publish production ingress until every required gate has actual evidence and approval.

Run43245360600 at ad1acd44cf1a185ecaadcd852d80c3d37af2a9a0 passed its complete disposable Linux runtime step. Image scanning is a separate gate. This is not EC2 rehearsal: the owner explicitly prohibits EC2 container operations and production changes. Production remains BLOCKED by incomplete runtime inputs, host capacity and source mismatch, provider/backup/DNS/TLS/network acceptance and a missing known-good rollback target. No production release image or deployed SHA is asserted.

The separate image scan completed and FAILED with122High/4Critical package-advisory matches. PRODUCTION_IMAGE_SECURITY_REVIEW.md records counts, material vendor checks, unresolved applicability and remediation prerequisites. No finding was suppressed and the workflow remains red. **Outcome: REHEARSAL PASSED — PRODUCTION RELEASE BLOCKED**, limited to disposable GitHub runtime acceptance. A passing application dependency feed scan did not cover OS/base/embedded image dependencies.

## Reviewed release path inventory

- `.github/workflows/readiness.yml`
- `backend/.dockerignore`
- `backend/Dockerfile`
- `backend/browser_sessions.py`
- `backend/client_identity.py`
- `backend/identity.py`
- `backend/production_runtime.py`
- `backend/requirements-local.txt`
- `backend/requirements-production-constraints.txt`
- `backend/requirements-production.txt`
- `backend/requirements.txt`
- `backend/server.py`
- `backend/tests/unit/test_client_identity.py`
- `backend/tests/unit/test_dependency_compatibility.py`
- `backend/tests/unit/test_framework_security.py`
- `backend/tests/unit/test_host_asgi.py`
- `backend/tests/unit/test_host_boundary.py`
- `backend/tests/unit/test_production_runtime.py`
- `backend/tests/unit/test_regressions.py`
- `backend/tests/unit/test_runtime_http.py`
- `deploy/.env.example`
- `deploy/Caddyfile`
- `deploy/Caddyfile.rehearsal`
- `deploy/compose.production.yml`
- `deploy/compose.rehearsal.yml`
- `deploy/rehearsal.env.example`
- `deploy/rehearsal/prepare.py`
- `deploy/rehearsal/storage_mock.py`
- `deploy/reviewed-base-images.json`
- `docs/EC2_DIRECTIONAL_ISOLATION_PLAN.md`
- `docs/ISOLATED_REHEARSAL_RUNBOOK.md`
- `docs/PRODUCTION_DEPLOYMENT_RUNBOOK.md`
- `docs/PRODUCTION_EXTERNAL_BLOCKERS.md`
- `docs/PRODUCTION_OPERATIONS.md`
- `docs/PRODUCTION_PROXY_DOCKER_READINESS.md`
- `docs/PRODUCTION_READINESS_MASTER_REPORT.md`
- `docs/PRODUCTION_ROLLBACK_RUNBOOK.md`
- `docs/PRODUCTION_SECURITY_REVIEW_PHASE2.md`
- `docs/PRODUCTION_VERIFICATION_MATRIX.md`
- `docs/RELEASE_OPERATIONS.md`
- `scripts/audit-production-dependencies.py`
- `scripts/check-production-compose.py`
- `scripts/check-production-release.py`
- `scripts/check-rehearsal.py`
- `scripts/inspect-rehearsal-host.sh`
- `scripts/record-release.py`
- `scripts/rehearse-linux-ci.py`
- `scripts/smoke-rehearsal.py`
- `scripts/verify-readiness.py`
- `tests/test_caddy_configuration.py`
- `tests/test_production_deployment.py`
- `tests/test_rehearsal_deployment.py`
- `tests/test_storage_fixture.py`
- `web/.dockerignore`
- `web/.env.example`
- `web/Dockerfile`
- `web/README.md`
- `web/next.config.ts`
- `web/package.json`
- `web/scripts/prepare-standalone.mjs`
- `web/scripts/production-build-safety.d.mts`
- `web/scripts/production-build-safety.mjs`
- `web/scripts/start-production.mjs`
- `web/scripts/verify-production-build.mjs`
- `web/src/app/(public)/legal/[doc]/page.tsx`
- `web/src/app/api/[...path]/route.ts`
- `web/src/app/health/route.ts`
- `web/src/app/ready/route.ts`
- `web/src/components/admin/operation-editor.tsx`
- `web/src/lib/admin-routes.ts`
- `web/src/lib/admin-server.ts`
- `web/src/lib/backend-headers.ts`
- `web/src/lib/browser-client.ts`
- `web/src/lib/config.ts`
- `web/src/lib/health.ts`
- `web/src/lib/ingress-identity.ts`
- `web/src/lib/proxy.ts`
- `web/src/lib/public-transport.ts`
- `web/src/lib/published-content.ts`
- `web/src/lib/server-api.ts`
- `web/src/lib/session-cookie.ts`
- `web/tests/admin-operations.test.ts`
- `web/tests/ingress-identity.test.ts`
- `web/tests/phase2-security.test.ts`
- `web/tests/production-proxy.test.ts`

Initial implementation commit: `2942f59d0adecad483f1fe42a9719dee72c9b251`; subsequent fixes and evidence are recorded in the verification matrix. Always compare the actual tested/pushed HEAD, not this historical implementation marker.

Additional reviewed paths from runtime verification:

- `docs/PRODUCTION_ENVIRONMENT_INVENTORY.md`
- `scripts/inspect-production-inputs.py`
- `scripts/scan-rehearsal-images.py`
- `tests/test_environment_inventory.py`
- `tests/test_release_artifacts.py`
- `tests/test_rehearsal_tls.py`
- `tests/test_rehearsal_prepare.py`
- `docs/PRODUCTION_IMAGE_SECURITY_REVIEW.md`

Runtime testing identified and corrected a real logout boundary defect: Starlette emits a quoted-empty deletion cookie, which the Web validator previously rejected with502. The validator now accepts that exact empty form only with Max-Age=0 and retains all security/duplicate-attribute checks. New tests preserve actual serialization. The rehearsal now has a Caddy-only ingress bridge, checked separately for collisions; its internal application bridge remains ordinary shared networking, not directional isolation. SMTP fixture CA reuse is idempotent across repeated setup; postrestart smoke repeats authentication and private media checks. Release artifact recording requires successful same-commit evidence and matching Linux image IDs/revision labels, not merely SHA-looking tags.
