# PR #1 independent read-only review

Date: 2026-11-02. Overall result: **BLOCKED**. Recommend blocking merge for R1 (HIGH).

PR: https://github.com/techashfaq/landvilla/pull/1
Repository reviewed: F:/projects/landvilla-integration-backend
Base: e53e776294851a4f9a7c35ab9079e8efda927575
Head: e9dd3e0b6ad294ae37d25a651f67548cece601b0

This review is independent in reasoning from the earlier narrow four-file fix acceptance; it examines interactions across the full backend PR. It is not a separate human or external security certification. Passing tests do not establish production safety.

## 1. Repository integrity and scope

Local HEAD and GitHub headRefOid match the supplied head; merge-base and GitHub baseRefOid match the supplied base. PR was OPEN with mergedAt=null when read. Initial worktree was clean. No original, mobile or web worktree was accessed during this review.

Exactly 17 changed paths, all below backend/:

- .env.example
- browser_sessions.py
- database_diagnostics.py
- extras.py
- identity.py
- marketplace.py
- requirements-local.txt
- requirements-test.txt
- scripts/apply_identity_indexes.py
- scripts/diagnose_atlas.py
- scripts/inspect_identity.py
- scripts/inspect_properties.py
- seed.py
- server.py
- tests/unit/test_regressions.py
- tests/unit/test_security_review.py
- visibility.py

The diff was reviewed against the recorded base, including new files and surrounding call sites. No real environment contents were read. No credentials or accidental backup files were identified in this diff; this is not an exhaustive repository-history secret scan.

## 2. Findings

### R1 — HIGH — General seed runner bypasses explicit identity migration safety gates (CONFIRMED)

Evidence: F:/projects/landvilla-integration-backend/backend/seed.py:62, :71, :74, :101, :232; backend/server.py:687. The hardened CLI is backend/scripts/apply_identity_indexes.py:7, :54.

The dedicated CLI correctly requires explicit development configuration, landvilla_dev and both confirmation arguments. However, seed.py adds m002_identity_indexes to the ordinary MIGRATIONS list. run_migrations invokes it without environment, database-name, duplicate-preflight or explicit-confirmation checks. seed_all calls run_migrations even for ordinary reference-data seeding. The standalone seed entry point selects the configured DB and calls seed_all without importing the server's production startup guard. Only demo seeding is prohibited in production. Consequently, running the documented ordinary seed command against a production or incorrectly selected database can apply the newly introduced identity indexes and marker without the supposedly mandatory approval path. Development startup with SEED_ON_STARTUP=true is another caller.

Offline reproduction: supplied a SimpleNamespace database named not_development with AsyncMock collections, marked migration 001 applied, left 002 absent, set process-local APP_ENV=production and DB_NAME=not_development, then invoked seed.run_migrations. Observed two users index calls, two OTP index calls, one rate-limit index call and a migration-marker insert; returned ['002_identity_indexes']. No real database was contacted. This is an operator-triggered safety bypass, not an unauthenticated remote endpoint exploit.

Recommended fix: remove identity provisioning from ordinary seed/startup migration dispatch or enforce one shared explicit authorization guard at every supported entry point. Keep reference-data seeding separate. Add mocked tests proving seed CLI, seed_all and startup cannot provision identity indexes implicitly, including production, absent environment and wrong database. This requires a separately approved source change. **Block merge until resolved.**

### R2 — MEDIUM — Email-only registration permanently reserves an unverified mobile identifier (CONFIRMED)

Evidence: backend/identity.py:227-230 and :280-290; backend/seed.py:64. Absolute root for these references is F:/projects/landvilla-integration-backend/.

Registration verifies email, then persists the supplied mobile with mobile_verified=False under a unique mobile index. Subsequent registration is considered ineligible if that mobile appears on any account, regardless of verification. Someone controlling an email account can reserve someone else's phone number without receiving its SMS. The actual phone owner then cannot register with it; authenticated contact verification also encounters the unique ownership conflict. This does not authenticate the attacker as the phone owner, but creates an account-registration denial of service and recovery burden.

Offline reproduction: register one synthetic email with a synthetic mobile using mocked delivery; verification returned 200. Request registration for a different synthetic email with the same mobile: generic 200, no delivery. No OTP values or real identifiers were printed.

Recommended fix: distinguish pending/unverified contact claims from verified unique identities, or require mobile proof before reserving it; define a secure reclaim policy. Any schema/index change needs explicit approval. Add tests for unverified-number reservation and legitimate-owner recovery. Treat as a release gate for public registration.

### R3 — MEDIUM — Expired featured listings retain ranking priority (CONFIRMED)

Evidence: backend/server.py:265 and :350-352; backend/marketplace.py:783. The PR removes the search-time expiry update, but still sorts using persisted featured before pagination. enrich changes only the outgoing boolean after selection. No replacement expiry invocation was found in the changed flow.

Offline reproduction: inserted 21 synthetic active properties into MemoryDB; the oldest had featured=True and an expired featured_until. GET /api/properties?sort=newest&limit=1 returned that oldest listing first with featured=False. The expired paid feature therefore still affects ranking and page composition even though its badge disappears.

Recommended fix: calculate effective featured status before sorting/pagination, or establish an explicit reliable expiry mechanism without restoring writes to public GETs. Add expired-featured ordering/pagination regressions. Do not change commercial prices or durations.

### R4 — MEDIUM — Owner-listing default response silently drops older items for legacy consumers (CONFIRMED contract change; client impact NOT TESTED)

Evidence: backend/marketplace.py:449-464. Base returned up to 200 owner items without pagination; head defaults to 20 and caps explicit limit at 100. items is retained and pagination metadata is additive, but semantics are not fully backward compatible.

Offline reproduction: a request to /api/listings/mine without pagination parameters returned 20 of 21 synthetic owner listings and total=21. Consumers that only read items will no longer display all previously returned listings. Mobile/web worktrees were deliberately not inspected; whether current clients consume pagination is unverified.

Recommended fix: obtain client-contract acceptance and pagination tests for both clients, or preserve a compatible legacy default while versioning/introducing pagination intentionally. This is an integration acceptance gate, not proven data loss.

### R5 — LOW — Partial migration and cleanup failures need clearer operator semantics (CONFIRMED implementation; operational impact potential)

Evidence: backend/scripts/apply_identity_indexes.py:33-50 and backend/seed.py:62-68. Index creation is sequential and nontransactional. A later failure can leave earlier indexes installed without a marker; the CLI correctly returns a sanitized failure and requires review. Retrying compatible create_index operations is normally idempotent, but options conflicts/duplicates require operator intervention. Concurrent marker insertion is not uniquely guarded here. A close failure only prints a category and can leave an otherwise successful return code at zero.

Recommendation: document partial-apply state and read-only recovery inspection; test failure after individual index steps and concurrent execution. Never automatically drop/rewrite records or indexes. This review did not execute any migration.

### R6 — INFO — Production and transport assumptions remain acceptance gates

Evidence: backend/server.py:32-36, :663-672; backend/browser_sessions.py:37-70; backend/marketplace.py:257-274 and :847-867.

Application production detection defaults missing APP_ENV to development (the dedicated migration CLI is stricter). Deployment must explicitly configure production, HTTPS, trusted origins and trusted proxy forwarding. Browser classification uses headers/cookies and is not proof of platform identity; non-browser callers can select native transport but still need valid credentials. Native query-string file-token compatibility remains and can expose tokens to access logs outside these sanitized application handlers. Payment fulfilment requires real replica-set transactions; mock transaction tests do not establish rollback or concurrency behavior. These are not newly proven authentication bypasses.

## 3. Security controls inspected

| Area | Evidence and assessment |
|---|---|
| Cookie/native isolation | browser_sessions.py:51-58, :75-90; server.py:118-146. Browser cookies use transport=browser and hashed session tokens; bearer lookup rejects browser rows and digest replay. Existing legacy native plaintext rows remain readable for compatibility. |
| Cookie policy | browser_sessions.py:57-61, :131-139. HttpOnly, SameSite=Lax, Path=/, Secure and __Host prefix for HTTPS/production; plaintext development restricted to loopback. Reverse-proxy/cookie forwarding needs deployment testing. |
| Origin/CSRF | browser_sessions.py:64-70, :98-128. Exact configured origins and cross-site refusal; mutation CSRF tied to current cookie session; bearer/cookie mixing rejected. Webhook exemption retains signature validation. Safe reads may omit CSRF, so cross-tab stale-read protection depends on clients supplying the session token header. |
| Rotation/logout | browser_sessions.py:165-185. Atomic old-session consumption before replacement, cookie expiry on logout, active-user/expiry lookup. DB failure between consumption and replacement can require fresh login; ordinary in-flight request revocation races were not concurrency-tested here. |
| OTP | identity.py:85-98, :177-300. secrets-based six digits, HMAC verifier, 5-minute expiry, 60-second cooldown, atomic fixed-window counters, five-attempt lookup and single-use claim. Delivery must succeed before verification; provider failures generic. R2 above remains. Generic responses reduce but do not prove resistance to timing/delivery-error enumeration. |
| Google | identity.py:332-439; browser_sessions.py:189-206. Maintained verifier handles signature/audience/issuer/expiry; verified email and stable subject required. Existing email accounts are not automatically linked; linking needs recent authenticated session and matching verified email. Browser nonce is single-use and bound to session. Managed browser callback fails closed; native managed exchange remains. |
| Ownership | server.py saved/enquiry routes; marketplace.py:304-323, :354-380, :434-489, :650-746; extras.py:243-250. Server selects owner IDs, verifies file ownership and broker approval, returns new/edited listings to moderation, scopes saved/lead/enquiry records and checks conversation participants. |
| Private media | marketplace.py:211-274. Kind/type/size and magic-prefix checks; private files owner/admin only; cross-owner admin access audited; private no-store. Magic bytes are not complete image decoding, PDF sanitization or malware scanning. Public property photos are public before moderation by design; operator must keep private bucket policy correct. |
| Payments | marketplace.py:787-980. Server selects price, validates capture/amount/currency/order, raw-body webhook HMAC, transactional entitlement update, completed-event deduplication, live-key gate. Refunds require manual reconciliation. No real gateway, duplicate-concurrency or transaction rollback verification. |
| Demo/startup | visibility.py:4-8; server.py:687-707. Demo flags remain explicit and read-only; mandatory ping and opt-in seeding. Production flags reject demo/test/startup seeding when correctly declared. R1 bypass applies to standalone/general seeding. |
| Logging/errors | identity.py:372-384; marketplace.py:114,154,178,181,252; database_diagnostics.py:3-22. Reviewed provider log calls use fixed categories, not exceptions/claims/keys. Validation omits input values; timing logs contain stage/duration. Third-party debug/access logs are not covered. |

No CRITICAL finding was established. Counts: HIGH 1, MEDIUM 3, LOW 1, INFO 1.

## 4. Migration assessment

Dedicated module import performs no dotenv load/client construction/write. CLI requires both flags before environment load; missing/unknown APP_ENV fails closed, production refuses, exact landvilla_dev and nonempty URI required. Actual database name is checked before ping, duplicate mobile/Google groups before index creation, marker written after successful callback. These narrow controls are covered by the 14 security regressions. They do not cover the alternate seed dispatcher: R1 supersedes the earlier conclusion that all provisioning paths are guarded.

Potential races between duplicate preflight and unique-index creation fail at MongoDB constraints rather than deleting data; actual index build behavior was not tested. No production migration process is approved by this report.

## 5. Dependencies and reproducibility

requirements-local.txt:15-16 adds google-auth==2.62.0 and boto3==1.43.117. requirements-test.txt:1-2 includes requirements-local.txt and mongomock==4.3.0. Read-only inspection of the existing disposable Python 3.12.14 QA environment confirmed boto3 1.43.117, botocore 1.43.123, s3transfer 0.19.3, jmespath 1.1.0, google-auth 2.62.0 and mongomock 4.3.0. pip check freshly passed. Clean installation was verified during the preceding dependency milestone, not repeated in this review. No installation or network dependency audit was performed. Transitive versions are not hash-locked by these manifests; future clean resolutions are not guaranteed bit-for-bit identical.

## 6. Tests and exact results

Working directory: F:/projects/landvilla-integration-backend.
Interpreter: F:/projects/landvilla-dependency-qa-20261102-boto3/Scripts/python.exe.

| Execution | Result |
|---|---|
| git merge-base supplied-base HEAD; git rev-parse HEAD; git diff --name-only base HEAD | Expected base/head and exact 17 paths. Exit 0. |
| gh pr view 1 --repo techashfaq/landvilla --json baseRefOid,headRefOid,state,mergedAt | Matching commits, OPEN, unmerged. Exit 0. |
| python.exe -B - via stdin: ast.parse for each backend/**/*.py, unittest.TextTestRunner(...).run(unittest.defaultTestLoader.discover('backend/tests/unit')) | 30 syntax files; 92 tests, 10.297 seconds, OK, exit 0. Includes all 14 security regressions; not 106 distinct tests. |
| Same stdin test process: mocked seed.run_migrations under production/nondevelopment DB; synthetic email registrations through ASGITransport | Both R1 and R2 reproduced; assertions passed. Exit 0. |
| Separate python.exe -B - stdin: MemoryDB + ASGITransport fixtures with 21 synthetic owner properties | R3 expired ranking and R4 default pagination reproduced; assertions passed. Exit 0. |
| python.exe -B -m pip check | No broken requirements found. Exit 0. |
| python.exe -B -c importlib.metadata version inspection | Versions listed above, exit 0. |
| git diff --check e53e776 HEAD | No output, exit 0. |

All custom reproduction code was passed over stdin; no test/source file was added. Existing fixtures disable dotenv, replace database objects with mongomock wrappers and mock provider delivery. -B prevented bytecode writes. No Atlas, R2, SMTP, Twilio, Google OAuth or payment-provider access occurred. No application server ran. An earlier read command was blocked by automatic approval review's usage limit and was later resumed successfully; no workaround bypassed approval.

## 7. API compatibility

Native session response still supplies session_token/user; issued tokens now belong to LANDVILLA and are stored hashed. Old native bearer rows are accepted, browser rows are not. Browser auth intentionally changes from bearer/managed callback to cookie/bootstrap/CSRF and independent Google/OTP. Existing managed-browser callers require coordinated client rollout and will receive refusal. Browser bootstrap also depends on identity feature/index readiness. New profile and OTP routes use strict protected-field rejection.

Existing property and /api/files/{id} shapes are retained, with additive fields. Listing input now rejects extra fields; clients must send the declared schema. R4 is a confirmed owner-list pagination contract change. Saved/enquiry routes preserve ownership checks. Payment fulfilment now requires transactions; standalone MongoDB no longer supports that flow. No mobile/web files were inspected or runtime client compatibility claimed under this task's boundaries.

## 8. Missing tests and production acceptance gaps

Before merge: fix R1 with alternate-entry-point regression tests and independently re-review.
Before public registration: resolve R2 and test legitimate phone-owner recovery.
Before marketplace acceptance: resolve R3; validate R4 with actual client pagination.
Additional gaps: transaction rollback/write conflict/parallel webhook tests on a dedicated disposable replica set; provider delivery and external auth; physical-device native login; browser proxy/cookie/origin behavior; authorization tests across all supported admin/user transitions; concurrent logout/contact update/session replacement; partial migration retry; upload decoding and malicious document policy; public-property allowlist projection (current enrich is a denylist); rate-limit behavior behind trusted proxies; production secret/origin/env validation and infrastructure access-log redaction.

Existing Google crypto tests use locally generated signing keys and patched certificate fetching; they exercise the maintained verifier without Google access. Browser tests use ASGITransport, not a real browser. Payment session mocks discard database session arguments and cannot establish ACID semantics. Tests passing are valuable regression evidence but do not close these gates.

## 9. Final recommendation and preservation statement

**BLOCKED — do not merge PR #1 until R1 is corrected and tested.** Resolve or explicitly track the other findings with owners and acceptance criteria. Production readiness: NOT READY. No fixes were made as part of this review.

Only this explicitly requested report was created. No source files were modified, formatted, restored, staged or deleted. No commit, push, merge, GitHub comment, approval or PR metadata change was performed. Original checkout and mobile/web worktrees were not touched. PR remains unmerged; no provider/database/storage/production operations were performed.