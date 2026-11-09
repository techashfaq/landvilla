# LANDVILLA — Phase 2.1 Defect Fix Report

Date: 2026-11-02. Branch: dev. Scope: S15, S16 and S17 only.

## Outcome

PASS — the three findings are fixed in source with isolated regression coverage. Baseline: 49/49 tests passed. Final: 71/71 passed (22 added), zero failures/skips. Lint and TypeScript pass. Live browser acceptance and production build: NOT TESTED. This milestone does not confer Phase 2 live acceptance or production readiness. Phase 3 was not started.

## Preservation and inventory

Existing target contents and Git status/diff were inspected before editing. The entire web directory remains untracked, so ordinary Git diff does not enumerate its source changes. Target diffs were reviewed against exclusive-copy backups. Existing tracked diff remains 39 files, 2044 insertions and 1547 deletions, matching the initial inventory. No commands edited backend, Expo, environment, dependencies, databases, storage, existing reports or unrelated application files.

Modified (relative to F:/projects/landvilla):

- web/src/lib/browser-client.ts
- web/src/components/account/account-panel.tsx
- web/src/components/account/conversation.tsx
- web/src/components/properties/search-form.tsx

Created:

- web/tests/account-concurrency.test.ts — eight adapter concurrency/identity/error tests.
- web/tests/account-state.test.ts — six component resource-state tests.
- web/tests/search-fidelity.test.ts — eight form round-trip/validation/reset tests.
- web/tests/phase21-harness.ts — test-only in-memory TSX transpilation and narrow hook/effect harness using installed TypeScript/React; no application runtime dependency.
- web/reports/PHASE2_1_DEFECT_FIX_REPORT.md — this report.

Backups created before source edits, using COPYFILE_EXCL (no overwrite):

- web/backups/phase2-1-20261102/src/lib/browser-client.ts.bak
- web/backups/phase2-1-20261102/src/components/account/account-panel.tsx.bak
- web/backups/phase2-1-20261102/src/components/account/conversation.tsx.bak
- web/backups/phase2-1-20261102/src/components/properties/search-form.tsx.bak

No existing tests were replaced. No packages installed; no lockfile/configuration changes. No commit, push, deployment or process lifecycle operation.

## S15 — Concurrent account reads

Original reproduction: hold the first GET /api/saved response, then request GET /api/enquiries/me. The old client rejects the second read with status 409. This was reproduced again by transpiling the untouched backup into memory: beforeS15ConcurrentReadRejected=true, exit 0, no application API connection.

Root cause: BrowserClient.account routed all methods through exclusive(), sharing the mutationPending lock with authentication and business writes.

Changed functions: BrowserClient.account and bootstrap in web/src/lib/browser-client.ts.

Fix: only GET bypasses exclusive(). It still validates accountPath, obtains the existing session/CSRF context, requires an authenticated user and passes through the same request() function. POST/PUT/PATCH/DELETE and existing authentication/upload mutations retain the existing lock, including rejection of overlapping mutations. Session generation is checked after bootstrap and before/after response-body decoding. A bootstrap that replaces user identity or CSRF context advances the generation, invalidating reads from the old session. Existing accept(), invalidate() and logout() invalidation remain in use. No token store, alternate transport or provider was added. Cookie, proxy Origin and CSRF rules were not modified.

New tests cover two simultaneous GETs, overlapping mutation rejection with an independent read, pending reads rejected after logout, Google session replacement, bootstrap replacement and explicit invalidation, sanitized errors with subsequent recovery, and replacement during body decoding.

Before: 49 baseline tests passed but did not cover this read lock defect; backup reproduction confirms rejection. After: all eight new S15 tests pass within 71/71.

Limitations: injected responses establish adapter behavior, not real cookie revocation or provider login. Requests already in flight are ignored through generation checks rather than necessarily aborted at the network layer. Mutation behavior intentionally remains reject-while-busy, not a new queue.

## S16 — Account and conversation state

Original reproduction: load owner listing page 1, click Next; old results remain rendered alongside Page 2. Backup component reproduction confirms beforeS16OldDataUnderNewPage=true. Old effects only set loading initially and retained data/error when request identity changed.

Changed components: AccountPanel and Conversation in the approved account component files.

Fix: each result is associated with path, refresh revision, user ID and CSRF session context. Render derives current data only when that key matches the current request. Consequently old data disappears on the first render of a refresh, page change, section change, conversation change or session change, before effects run. An unmatched result displays loading. Failure stores null data and a safe error for the current key. Retried requests start with a new key, clearing the previous error. Existing effect cleanup prevents old asynchronous reads from applying after navigation/unmount. Conversation responses must be objects rather than silently leaving an indefinite loading state on malformed data. Mutation error setters cannot replace a different request's result. Save notices are associated with the refreshed request.

Existing AccountGate session remounting and BrowserClient generation protection remain unchanged except the S15 bootstrap generation fix. The result key is internal component state; it is not serialized into HTML, logged or persisted as authentication storage.

New tests cover refresh loading/error/retry, page 1 to page 2 followed by failure, rapid conversation navigation with late success and late error, logout/account switch during pending reads, and unmount before response completion. The tests execute actual TSX with a narrow injected hook/effect harness; they assert rendered element-tree text and callback behavior. They are not browser or full React reconciliation tests.

Before: baseline suite passed while backup page-transition reproduction demonstrated stale results. After: six new S16 tests pass within 71/71. Old page results are absent immediately after transition and after a failed request; old conversation/identity data does not replace current results in the exercised cases.

Limitations: real StrictMode scheduling, browser focus/keyboard behavior and DOM-level account navigation still require manual/component-renderer acceptance. No owned-account mutations or private customer data were used. This milestone does not change backend pagination or workflow policies.

## S17 — URL/filter fidelity

Original reproduction: bhk=2,5 is accepted by propertyQuery but the old single select has no matching option; locality IDs/slugs and multi-value selections have the same problem. Backup form reproduction confirms beforeS17NoMatchingOption=true.

Changed component: SearchForm in web/src/components/properties/search-form.tsx. The existing property-query parser was inspected completely and was not modified.

Fix: normalize/validate incoming values using propertyQuery. Locality and BHK controls accept the backend's comma-separated syntax directly, with datalist suggestions and instructions. Locality suggestions include actual metadata IDs and slugs; entered slug/ID lists are preserved verbatim after parser normalization. BHK suggestions cover 1–20 and 4+. This deliberately uses comma-separated text inputs rather than repeated HTML multi-select parameter keys, which the existing parser rejects. Accepted values remain intact even if absent from current metadata. Category/type/zone selects retain an explicit Current filter option for such values, without inventing taxonomy records. page and limit are retained as hidden fields; an absent sort remains absent after normalization. The form key changes with normalized URL values to reset uncontrolled inputs on navigation. Clear filters links to /properties without a query.

New tests render the actual form with React server rendering, inspect its successful controls, serialize those values and run the existing parser. Cases include a complete supported search with page/limit, multiple localities, multiple BHK values including 5/20/4+, locality slug, mixed slug/ID plus metadata-absent filters, empty query, invalid/duplicate parameters and reset behavior. Select tests assert a matching option actually exists rather than merely reading defaultValue.

Before: 49 baseline tests covered parsing but not form fidelity; backup reproduction proves a missing matching option. After: eight new S17 tests pass within 71/71, with equivalent normalized query output.

Limitations: datalist assistance for comma-separated entries varies by browser; users can type the full list. No unsupported city/area filters added. Invalid user-entered syntax remains rejected by the existing discovery parser. Preserving a syntactically accepted identifier does not assert that a corresponding live record exists. Page is retained on submission to avoid silently discarding an accepted parameter; Clear filters also resets pagination. Native DOM submission and responsive layout require browser acceptance.

## Verification evidence

Commands run from F:/projects/landvilla/web unless noted. TypeScript incremental output and ESLint caching were disabled to avoid unapproved artifact writes.

| Command / check | Result | Exit | Evidence |
|---|---|---|---|
| npm.cmd run test — baseline | PASS | 0 | 49 passed, 0 failed/skipped; Node duration 525.2068 ms |
| Backup-only reproduction via node --input-type=module (stdin) | PASS | 0 | All three before-defect indicators true; no source restoration or live requests |
| npm.cmd run test — final | PASS | 0 | 71 passed, 0 failed/skipped; Node duration 1626.041 ms |
| npm.cmd run lint -- --no-cache | PASS | 0 | eslint . --max-warnings 0 --no-cache completed without diagnostics |
| npm.cmd run typecheck -- --incremental false | PASS | 0 | tsc --noEmit --incremental false; tool wall duration 5.807 s |
| git diff --check — repository root | PASS | 0 | No whitespace errors; pre-existing LF/CRLF warnings |
| Backup-to-source no-index diffs | PASS (review) | 1 | Differences expected because sources changed; no whitespace diagnostics; explicit changed-file trailing-whitespace scan empty |
| npm.cmd run build | NOT TESTED | N/A | Would create/update .next and generated files outside the approved paths; no build artifacts were authorized |
| Live browser acceptance | NOT TESTED | N/A | No browser interaction or live business/provider actions performed |

One intermediate npm.cmd run test was inadvertently invoked from the repository root and failed ENOENT (exit 1: no root package.json). It did not run tests. It was rerun from web/ with the final results above. An initial edit script failed an anchor check before writing source; the corrected script used the inspected file line endings. An initial no-index whitespace wrapper treated the expected differences exit code 1 as failure; direct inspection found no whitespace diagnostics and a changed-file whitespace scan was empty. These are recorded rather than represented as product/test failures.

The existing suite includes mock session/CSRF/Origin checks and an isolated loopback HTTP proxy test. It does not contact the configured LANDVILLA backend or prove live OTP/Google acceptance. No historical results replace this milestone's fresh results.

## Remaining gates and stop point

S15/S16/S17 are addressed at source and isolated-test level. Remaining Phase 2 acceptance requirements from the prior report, including real browser, identity/provider, ownership/media, content and production SEO gates, remain outstanding and were not expanded into this milestone. Browser bearer tokens were not added to localStorage/sessionStorage. Backend authorization remains authoritative.

No Phase 3 work was performed. Stop after this report; separate authorization is required for further scope, generated build artifacts or live acceptance operations.
