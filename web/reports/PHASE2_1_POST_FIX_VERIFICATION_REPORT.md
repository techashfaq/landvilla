# LANDVILLA — Phase 2.1 Post-Fix Verification Report

Date: 2026-11-02 (Asia/Calcutta). Milestone: controlled verification and manual acceptance preparation only.

## 1. Verdict

**Automated verification: PASS. Production build: NOT TESTED. Live browser acceptance: NOT TESTED. Manual acceptance preparation: complete, execution conditional on the prerequisites below. Production readiness: NOT READY. Phase 3: not started.**

Fresh execution produced 71 passing tests, zero failures/skips, and successful lint and TypeScript checks. This demonstrates current test/type-check health, not a successful Next.js production compilation, hydration, real authentication or browser acceptance. No historical pass result was substituted for current execution.

Build artifacts have not been explicitly authorized: the request permits a build only if such authorization exists. Therefore npm.cmd run build was not executed. It would update .next and potentially generated Next.js files. No build output or build error is available from this milestone; absence of build errors is not a build PASS.

## 2. Git state and preservation

Repository: F:/projects/landvilla. Branch: dev. Commit: e53e776294851a4f9a7c35ab9079e8efda927575.

Initial git status --short showed 39 pre-existing tracked modifications across root/docs/backend/Expo and extensive untracked work, including web/, audit-report/, backend modules/tests/scripts, mobile auth files and backups. git diff --stat was 39 files changed, 2044 insertions and 1547 deletions. Final tracked status matched the initial list. No cleanup, reset, checkout, commit, push or deployment was performed.

Git warned that backend/.pytest_cache could not be enumerated and emitted pre-existing LF/CRLF warnings. These were not repaired. Ordinary Git diff does not cover untracked web source. A separate SHA-256 comparison of 329 readable tracked and nonignored untracked files before/after checks showed zero changed, removed or added files before this report was written. Ignored dependencies, .env files and build artifacts are not covered by that inventory. No command deliberately modified those files.

The sole created file is web/reports/PHASE2_1_POST_FIX_VERIFICATION_REPORT.md, created exclusively after confirming it did not exist. Application source, prior reports, backups, dependencies, lockfiles and environment configuration were not edited. Backend, Expo, database, Atlas and R2 operations were not performed.

No existing application server or unrelated process was started, stopped, restarted or killed. The explicitly requested existing test suite launches its own short-lived loopback HTTP fixture on an ephemeral port and closes it; this is a synthetic proxy test, not a LANDVILLA development server or real provider operation.

## 3. Exact checks and current results

Working directory for npm commands: F:/projects/landvilla/web. Node v24.21.0; npm 11.19.0. Package scripts were inspected before execution. No dependency installation or environment change was needed.

| Command | Result | Exit code | Current evidence |
|---|---|---|---|
| git branch --show-current (repository root) | PASS | 0 | dev |
| git rev-parse HEAD (repository root) | PASS | 0 | Commit above |
| git status --short / git diff --stat (repository root) | PASS | 0 | Pre-existing dirty/untracked work identified, preserved |
| npm.cmd run test | PASS | 0 | 71 tests, 71 pass, 0 fail, 0 cancelled, 0 skipped, 0 todo; Node duration 1617.5783 ms; tool wall time 2.991 s |
| npm.cmd run lint -- --no-cache | PASS | 0 | eslint . --max-warnings 0 --no-cache; no lint diagnostics; asynchronous completion confirmed |
| npm.cmd run typecheck -- --incremental false | PASS | 0 | tsc --noEmit --incremental false; no diagnostics; tool wall time 6.149 s |
| git diff --check (repository root) | PASS | 0 | No whitespace errors; pre-existing line-ending warnings |
| npm.cmd run build | NOT TESTED | N/A | Generated build artifacts not explicitly authorized |
| Live HTTP/browser acceptance | NOT TESTED | N/A | No application HTTP probes or browser interaction executed in this milestone |

Lint's complete elapsed duration was not captured; no estimate is presented as a measurement. TypeScript used the existing generated route types; disabling incremental output avoids tsbuildinfo writes. It cannot replace a fresh production build. git diff --check alone does not verify untracked web files; content preservation was additionally checked by hashes.

## 4. Regression coverage review

Inspected the complete S15/S16/S17 regression files, their harness, corresponding source changes, package scripts, the Phase 2.1 defect-fix report, and property/locality route implementations.

| Finding | Current coverage | Count | Limitations / acceptance still required |
|---|---|---:|---|
| S15 | web/tests/account-concurrency.test.ts: two simultaneous GETs; mutations remain exclusive while reads proceed; pending read rejected after logout, Google replacement, bootstrap replacement and explicit invalidation; sanitized rejection/recovery; invalidation during body decoding | 8 PASS | Injected transport with synthetic identities. Does not verify actual browser cookies, backend revocation, provider auth or cross-tab scheduling. Google test name refers to mocked endpoint output, not a real Google login. |
| S16 | web/tests/account-state.test.ts: refresh/error/retry; page transition/failure without old results; rapid conversations with out-of-order success/error; pending response during account switch/logout; unmount | 6 PASS | phase21-harness.ts substitutes React hooks/effect scheduling and selected imports. It does not mount a real DOM or execute full React reconciliation, StrictMode replay, hydration, AccountGate and SessionProvider together. Successful page-two rendering, section transitions, pending mutation completions after navigation and real consented conversations warrant manual checks. |
| S17 | web/tests/search-fidelity.test.ts: six round trips (complete query, multiple locality IDs, multiple BHK, slug, mixed/metadata-absent values, empty query), invalid/duplicate rejection and reset | 8 PASS | Actual component is transpiled in memory and React server-rendered, but form submission is reconstructed from element props. No native DOM submit, datalist interaction, browser autofill/history or responsive behavior is tested. Synthetic metadata does not prove live records exist. |
| Existing suite | Authentication/session adapters, CSRF/origin/proxy restrictions, public DTO/query validation, upload/ownership forwarding and one loopback HTTP fixture | 49 PASS | Mocks do not execute actual Atlas ownership/moderation/provider behavior. No live customer accounts, OTPs, Google sign-in, payments or business records used. |

Current source observations: BrowserClient.account allows GETs outside exclusive() while retaining its request generation checks; bootstrap advances generation on identity/CSRF replacement. AccountPanel and Conversation display only results matching path/revision/session context. SearchForm uses the existing propertyQuery parser, comma-separated locality/BHK inputs, retained options for accepted metadata-absent values, hidden page/limit and a clean reset link. These observations corroborate isolated tests, not full production correctness.

Further robustness cases not exhaustively covered include bootstrap failure while other reads are pending, same-user session replacement through every possible lifecycle path, delayed mutations after navigation, and all browser form value normalization behavior. No extra fixes or tests were added under verification-only scope.

## 5. Manual browser acceptance prerequisites

The checklist below is preparation, not a record of executed steps. All rows start NOT TESTED.

1. Obtain separate permission for generated web build artifacts and a fresh production build. Have the operator arrange existing development/staging servers without duplicating or interfering with processes. This milestone did not assess their current availability.
2. Use only a separately approved nonproduction environment, tester-owned accounts and controlled fixtures. Authenticated tests require prearranged legitimate test sessions; do not inject tokens or bypass backend auth. No real customer accounts, OTP/Google flow or writes are authorized by this report.
3. Prepare two distinct tester identities, two owned synthetic conversations and enough approved synthetic owner listings for two pages. Do not create them during this verification milestone. Mutation checks require explicit approval for the exact disposable fixture changes; otherwise mark BLOCKED.
4. Browser DevTools may throttle/delay/block individual requests for the later test. Record route, method, status, timing and expected UI only. Do not export raw HAR files, auth headers, cookie/CSRF values, profile data or message contents. Prefer labelled synthetic screenshots.
5. Use a desktop viewport and a mobile-width viewport (for example 1440 and 390 CSS pixels), keyboard-only form navigation, and at least the intended deployment browser. Capture browser/version and dev versus production mode. No browser PASS can be inferred from this document.

## 6. Manual acceptance checklist

| ID | Scenario and steps for a separately approved session | Expected evidence / pass criteria | Current status |
|---|---|---|---|
| M01 | Concurrent account reads: throttle requests; open saved properties, then navigate to enquiries while the first GET is pending. Ensure requests originate through the application's shared BrowserClient, not raw console fetch. Repeat reverse completion order. If UI sequencing cannot generate overlap, use a separately approved browser integration harness. | Two reads can overlap without the old client-side 409 lock rejection. Only the currently requested resource renders; a late previous-page response does not replace it. Network status alone cannot prove the client locking behavior. | NOT TESTED |
| M02 | Mutation serialization: on a disposable approved test record, delay an approved save/update request and attempt a second application mutation before the first completes. Also attempt a safe account read. Do not replay raw HTTP writes or use business records. | One mutation proceeds; second is prevented or receives the existing busy error; read remains independent. After completion/failure a later mutation is usable. No duplicate write and no stuck UI. This is reject-while-busy behavior, not a queue. | NOT TESTED |
| M03 | Logout/account switch: begin a slow account GET in approved session A, perform approved logout, then release the GET. Separately switch to legitimate test session B while an A request is pending; release A response after B is visible. Repeat with expiry/revocation if separately supported by the test setup. | A data never reappears after logout or overwrites B. Protected UI shows signed-out/current-account state. Record only safe status/UI evidence; never cookies or session material. | NOT TESTED |
| M04 | Account refresh: load an approved test account section, click Refresh under throttling; fail one request through browser network controls, then restore and retry. Repeat for profile and saved sections. | Previous contents disappear during refresh; loading is visible; failure gives safe error without stale results; retry clears error and shows fresh data. Form values correspond to the refreshed profile. | NOT TESTED |
| M05 | Pagination: using approved multi-page owner fixtures, load page 1 then Next; delay page 2. Test both success and blocked/failing request. Navigate back and change account section. | Page 1 records never appear under page 2 label. Failure cannot look like successful page 2. Retry recovers; successful page 2 has correct count/items. Section changes show only the requested section. | NOT TESTED |
| M06 | Conversations: open owned synthetic conversation A, immediately B under delayed/reordered GETs. Release B then A; repeat with A failing. Navigate away before completion. Later, separately test a delayed approved message mutation across navigation. | B remains B; A text/phone/status/error never contaminates it. Loading/error states are clear. No post-navigation stale overwrite. Do not use real messages; note that authenticated lead reads may generate backend access-audit records. | NOT TESTED |
| M07 | Multi-locality: obtain actual public IDs from reviewed metadata, open /properties?locality=ID1,ID2, submit unchanged, refresh and use browser back/forward. Type the full comma-separated value when datalist suggestions are insufficient. | Both values remain visible and reach the supported parser as one comma-separated parameter; no repeated locality keys or dropped value. Query order/encoding can normalize without changing meaning. | NOT TESTED |
| M08 | Multi-BHK: open /properties?bhk=2,5,20,4%2B; submit unchanged, refresh and navigate history. Test a combined locality/BHK query with price/sort/page/limit. | All BHK values, including literal 4+, survive. URL uses %2B for plus where needed. Existing filters, page and limit remain intact. Zero results for uncommon values is not a fidelity defect. | NOT TESTED |
| M09 | Locality slug: use a real supported slug from current public metadata, then a mixed slug/ID list. Submit unchanged. | Slug remains represented rather than silently converting to blank; mixed values survive and backend results/empty state are honest. No invented locality record is required. | NOT TESTED |
| M10 | Metadata-absent values: choose a safe syntactically valid test-only category/type/zone token absent from the current options; open the URL, submit unchanged. Do not write taxonomy records. | Current filter option preserves the value; no silent fallback to All. Empty results or backend rejection are reported honestly, not fabricated matches. | NOT TESTED |
| M11 | Invalid/reset: try unsupported city, duplicate locality keys, bhk=21 and page=0. Then load a valid multi-filter URL and click Clear filters. | Invalid values show validation without silently forwarding unsupported filters. Clear goes to /properties without query; controls clear and pagination resets. Page/limit otherwise remain deliberately preserved on normal submit. | NOT TESTED |
| M12 | Unknown routes/status: with a known working backend, open a verified-nonexistent syntactically valid property ID at /property/unknown~ID and a nonexistent /city/ujjain/SLUG. Also test unsupported city and a known empty locality. Inspect Network document GET status on hard reload, then client navigation; repeat after a permitted production build. | Appropriate not-found UI and noindex. Record actual document status separately: a 200 streamed not-found page is not strict HTTP 404 acceptance. Distinguish a backend outage/503 from a missing record. No private IDs or DB changes needed. | NOT TESTED |

For each executed row later, record tester/date/browser/viewport, mode, sanitized URL/query, request order/status, UI result and PASS/FAIL/BLOCKED. Restore temporary browser throttling/blocking afterward. Do not infer server security from hidden buttons or matching UI alone.

## 7. Unknown-route and build considerations

Read-only source inspection: web/src/app/(public)/property/[slug]/page.tsx load() invokes notFound() for invalid IDs/backend 404; other upstream errors propagate. The page may redirect old slugs to the canonical property URL. web/src/app/(public)/city/[city]/[locality]/page.tsx calls notFound() for unsupported city, missing locality or zero results. These are source facts, not proof of transport status.

The prior audit/completion report records a streaming HTTP 200 concern for unknown pages. It was not reproduced in this milestone and is not cleared by TypeScript or tests. Verify actual document status after a fresh permitted production build as well as during development. Do not enable indexing merely because fallback UI looks correct.

## 8. Remaining acceptance gates and final status

- Explicit build-artifact permission and a successful fresh Next.js production build are still required. No build or generated-route regeneration was attempted.
- Local/staging availability and safe operator-owned fixture/session prerequisites are not verified here; no existing server was managed.
- Execute the manual checklist under separate authorization, including real DOM/hydration/StrictMode checks and account isolation. Tests using mocks do not prove OTP delivery, Google authentication, cookie revocation or backend persistence.
- Existing Phase 2 content, private-media, authorization, SEO and production operational gates remain outstanding; this verification did not expand scope to repair them.
- No source edits, no new dependencies, no backend/mobile/database/storage/environment changes, no commit/push/deploy, and no Phase 3 work.

The code passes current isolated tests, lint and type checking and has a prepared manual acceptance procedure. It is **not yet production-build verified or live-browser accepted**. Stop after this report.
