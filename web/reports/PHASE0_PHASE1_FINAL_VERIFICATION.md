# LANDVILLA — Phase 0/1 final verification and Phase 2 approval plan

Date: **2 November 2026**. Branch: `dev`. Scope: verification only; no application implementation authorized by this report.

**Final phase status: BLOCKED** — automated foundation checks pass, but live authenticated browser acceptance is incomplete. **Production verdict: NOT READY.** Phase 2 has not started and requires explicit approval.

## Objective and initial state

Verify the existing architecture and web foundation without rebuilding authentication or modifying backend/mobile code. Read the requested Phase 0 architecture report, Phase 1 completion report, web README, root README, current manifests/configuration, web routes/components/adapters/tests, backend browser-session and identity code, unit tests and relevant property/workflow handlers. All requested documents exist.

Git has substantial pre-existing tracked modifications, untracked source, reports and backups. These were preserved. The entire web directory is untracked, so Git cannot provide its historical source diff; current files were inspected directly. Root tracked diff summary was inspected, along with relevant backend dependency changes. No checkout/reset/cleanup occurred.

The old Phase 1 report/README are stale about missing dependencies. An existing web-local lockfile (version 3) and installed dependencies now exist. This pass neither installed nor upgraded packages. Current direct manifest, lock and installed versions agree:

| Dependency | Version |
|---|---|
| next / eslint-config-next | 16.4.3 |
| react / react-dom | 19.3.0 |
| server-only | 0.0.1 |
| typescript | 6.0.3 |
| eslint | 9.39.1 |
| @types/node | 24.10.0 |
| @types/react | 19.3.0 |
| @types/react-dom | 19.2.2 |

This is an installed-version check, not a fresh registry vulnerability assessment or clean-install reproducibility test. This report supersedes the earlier installation/build blocker; earlier provider-success claims remain historical.

## Completed work and files

- Created only `web/reports/PHASE0_PHASE1_FINAL_VERIFICATION.md`.
- Modified application source files: none. Modified existing documentation/manifests/lockfiles: none.
- Build/typecheck tools produced normal ignored `.next`/TypeScript artifacts. No existing application file was deliberately edited, so no source backup was needed.
- Backend, Expo, MongoDB business data, R2 objects, configuration, indexes and migrations: unchanged by this pass.
- Browser navigation to login used the existing bootstrap endpoint, which may create an ordinary short-lived pre-auth session in the existing session store. No users/listings/enquiries were created, and no OTP delivery or external sign-in was initiated.
- No commit, push, deployment, DNS or cloud operation.

## Architecture and contract findings

PASS — Existing Next App Router remains separate from Expo. FastAPI remains the sole session and business authority. No Mongo/R2 SDK or separate auth provider was added to web.

PASS — BrowserClient retains session display and CSRF in memory; no localStorage/sessionStorage bearer implementation was found in `web/src`. Session responses containing a native session token are rejected. This is source/test evidence, not inspection of every existing user's browser storage.

PASS — Fixed upstream proxy exposes a narrow method/path allowlist. It rejects bearer headers and query parameters, requires exact Origin and CSRF presence for POST, strips caller forwarding headers, limits JSON bodies, rejects redirects, validates cookie attributes and sanitizes network/5xx errors. Backend still validates CSRF values, cookie sessions and permissions. Distinct cookie headers and logout deletion attributes have isolated tests.

PASS — Admin layout checks the backend user; stats loader independently checks access and backend stats authorization. No client-selected role grants authority. No fabricated statistics appear when access/data is unavailable.

PASS — Existing Google nonce, token verification and account-linking contracts are preserved. Native/mobile paths were not changed. Native/browser separation and callback replay are covered in isolated backend tests.

Current routes: `/`, `/login`, `/legal/[doc]`, `/admin`, `/api/[...path]`, `/robots.txt`, not-found/loading/error handling. Root metadata and robots intentionally disable indexing at this foundation stage.

APIs inspected/used by foundation: GET `/api/meta`, `/api/auth/me`, `/api/auth/browser/bootstrap`, `/api/me/profile`, `/api/admin/stats`, `/api/legal/{privacy|terms}.json`; POST `/api/auth/otp/request`, `/api/auth/otp/verify`, `/api/auth/google`, `/api/auth/browser/google-nonce`, `/api/auth/logout`. Live probes used only the subset listed below; inspecting a contract is not executing it.

## Exact checks and results

Commands run from `F:\projects\landvilla\web`:

| Command | Result |
|---|---|
| `npm.cmd run test` | PASS — 29 tests, 29 passed, 0 failures, 0 skipped |
| `npm.cmd run lint` | PASS — ESLint exit 0, no reported warnings/errors |
| `npm.cmd run typecheck` | PASS — full project TypeScript exit 0 |
| `npm.cmd run build` | PASS — Next 16.4.3 production build exit 0; compilation, TypeScript and generation of 5 static pages completed |

Production build lists public homepage/login/robots as static and admin/API/legal as dynamic. Building does not prove production HTTPS authentication or deployment readiness.

Backend isolated suite, from repository root:

```powershell
& 'C:\Users\ashfa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "import sys,unittest,logging; sys.path[:0]=['.cache/qa-deps','backend/.venv/Lib/site-packages']; logging.disable(logging.CRITICAL); result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('backend/tests/unit')); sys.exit(not result.wasSuccessful())"
```

PASS — **78 tests**, 12.895 seconds, exit 0. Tests disable dotenv, inject in-memory database and mock delivery/provider dependencies; they do not mutate configured Atlas business data. Existing Google verifier prints detailed synthetic exception messages despite logging suppression; see risks below. No real credentials were submitted to these tests.

`git diff --check` from root: PASS, exit 0, with pre-existing LF/CRLF warnings. This checks tracked diffs; it does not validate all untracked files. Expo checks: NOT TESTED this pass; no Expo changes were made. Historical Expo results were not reclassified as current passes.

## Runtime and browser evidence

Existing processes were reused, not restarted or duplicated:

| Surface | Observation | Result |
|---|---|---|
| Web | node PID 14616 listening on localhost port 19006 | PASS |
| Backend | python PID 2492 listening on port 8000 | PASS |
| Backend liveness | GET `http://127.0.0.1:8000/health` → 200 | PASS |
| Backend readiness | GET `http://127.0.0.1:8000/ready` → 200; source performs Mongo ping | PASS |
| Homepage/login shell | HTTP 200, Cache-Control no-store in development | PASS |
| API forwarding | GET `http://localhost:19006/api/meta` → 200, no-store | PASS |
| Anonymous admin API | GET `/api/admin/stats` → 401, no-store | PASS |
| Anonymous admin page | HTTP 200 denial shell; browser shows “Sign in to continue”, no counts | PASS |
| Wrong-origin POST | `/api/auth/logout` with synthetic untrusted Origin → 403 | PASS |
| Missing-CSRF POST | `/api/auth/logout` with local Origin but no CSRF → 403 | PASS |
| Browser login bootstrap | Real browser progresses from loading to email/mobile form without submitting contact details | PASS |
| Homepage responsiveness | Browser screenshots inspected at 390×844 and 1440×900; measured document widths 375/1425, no horizontal overflow | PASS for this limited smoke check |
| Google readiness | Browser explicitly displays Google sign-in not configured | BLOCKED |

HTTP probes used Node fetch with bounded timeouts and printed only status/cache results, never response payloads, credentials or cookies. Rejected POST probes were stopped before logout mutation. No authenticated session was logged out. Browser viewport override was reset after inspection. These are local development checks, not Android Chrome/iPhone Safari or exhaustive accessibility validation.

Existing server terminal logs were not attached to this session: NOT TESTED for comprehensive recurring-log monitoring. Health/page results show present responsiveness, not proof that earlier startups were error-free. Database ping success does not prove R2 connectivity, all identity indexes or production configuration.

## Authentication acceptance matrix

| Scenario | Isolated automated evidence | Live browser evidence this pass |
|---|---|---|
| OTP request, verification and session creation | PASS — mocked delivery and memory DB | NOT TESTED — no owned contact supplied for this pass |
| Invalid, expired, exhausted and reused OTP | PASS — backend cases | NOT TESTED |
| Resend/rate limits and concurrent single-use | PASS — backend cases | NOT TESTED |
| Anonymous bootstrap | PASS | PASS — form reached |
| Authenticated refresh/persistence | Adapter/bootstrap contract PASS | NOT TESTED — historical success not rerun |
| Logout, revocation, expiry | PASS — cookie deletion, expired/revoked sessions | NOT TESTED authenticated flow |
| Bootstrap after logout | Bootstrap and logout independently PASS | NOT TESTED as a complete browser sequence |
| Account switching/stale responses | PASS — adapter generation and backend session checks | NOT TESTED across real tabs/accounts |
| Origin/CSRF rejection | PASS | PASS for local HTTP negative probes; browser exploit test NOT TESTED |
| Cookie attributes | PASS — isolated production/development tests | NOT TESTED by live cookie inspection |
| Google nonce and replay/token failures | PASS — injected verifier/cryptographic unit cases | BLOCKED — web Google UI unconfigured |
| Anonymous admin denial | PASS | PASS |
| Normal-user/admin role authorization | PASS — adapter denial and registration/profile protections | NOT TESTED with real normal/admin accounts |
| Native compatibility | PASS — existing isolated backend cases | NOT TESTED on device; mobile untouched |

No mocked test proves real email/SMS delivery or Google authentication. No real OTP, token, cookie or CSRF value was printed.

## Defects, gaps and risk assessment

1. **BLOCKED — live acceptance:** owned test accounts/contact access are required for OTP/provider, refresh/logout/account-switching and authorized admin browser checks. Do not invent accounts or grant admin. Browser cookie/HTTPS acceptance still needs a controlled environment.
2. **FAIL — documentation freshness:** existing README/Phase 1 report still state dependencies are absent. Current checks supersede that claim. They were preserved; updating them can accompany approved follow-up work with backups.
3. **FAIL — backend log hygiene:** `backend/identity.py::verify_google` prints exception type/message. The isolated suite reproduces verbose verifier output. Propose separately approved backend change to category-only logging plus regression test; no authentication logic change is necessary. No fix was made under verification-only scope.
4. **BLOCKED — production ingress policy:** proxy intentionally strips forwarded IP headers, so backend IP throttles can aggregate users behind the web server. Requires an approved trusted ingress/client-IP design, not trusting arbitrary X-Forwarded-For. Production CSP/HTTPS/origin/cookie topology remains unverified.
5. **BLOCKED — clean backend dependency setup:** `marketplace.py` imports boto3; minimal `requirements-local.txt` still does not declare it. Existing environment works, but clean minimal setup is not proven. Separate backend manifest approval needed.
6. **NOT TESTED — deployment/security breadth:** no new vulnerability scan, clean npm-ci install, production runtime, complete accessibility, private-media/R2, backup/restore or real-device tests. No production-readiness claim.
7. **BLOCKED — Phase 2 API coverage:** proxy currently rejects all query strings, only supports JSON and excludes property/account mutations. Discovery needs validated query allowlists; uploads/private media need reviewed bounded multipart/streaming transport. A blanket unrestricted proxy would be unsafe.
8. **BLOCKED — product completeness:** current backend search is Ujjain-specific and lacks requested city/area/verified-only filters. Owner lifecycle, general CMS, advanced staff roles and several admin/finance capabilities are missing. Do not simulate them in Next.

No source change was justified merely to make these checks pass. Present risk is concentrated in unverified live journeys, production topology and unimplemented product scope, rather than a failing web build.

## Phase 2 implementation proposal — approval required

### Scope and ordering

1. Public data layer: typed allowlisted property/meta DTOs; anonymous SSR fetches; strict query validation; no private/security fields in client props or SEO. Preserve explicit fictional-demo labeling and noindex for demo/thin pages. Start with no-store until moderation/expiry invalidation is proven.
2. Discovery: home with actual recent listings, `/properties`, buy/rent entry points, URL-backed supported filters, sorting/pagination, responsive controls and honest empty/error states. Existing filters: purpose, segment, type, locality, zone, min_price/max_price, bhk, q, sort, page/limit. Ujjain is the current supported city; do not offer ignored multi-city/area/verified filters.
3. Property detail: stable ID-bearing readable slug, canonical title handling, public images, factual amenities, privacy-safe owner/broker labels, share, related results from supported filters. Exclude current property, never invent recommendations or verification.
4. Customer/owner/broker: existing profile, saved, enquiry/history, listings and broker contracts only. Add scoped API methods using the current cookie/CSRF adapter; no new auth state manager. Support safe uploads/private retrieval only after transport and access tests. Honor pending review and broker approval; no browser grant/publication override.
5. Informational/SEO: About/approach and supplied approved support content, existing legal documents, meaningful locality pages, metadata/canonical/sitemap/private noindex. Do not fabricate contact details, FAQ policy or CMS persistence. Keep prelaunch crawl restrictions until content and canonical origin are approved.
6. Tests: query/filter validation, DTO privacy, anonymous/private cache separation, gallery/error states, session-aware account flows, ownership/moderation, file transport, search pagination and browser journeys with authorized test data.

### Existing APIs to reuse

- Discovery/detail: GET `/api/meta`, `/api/properties`, `/api/properties/{prop_id}`.
- Profile: GET/PATCH `/api/me/profile`; existing OTP contact-verification mode requires recent auth and must be audited at implementation.
- Saved: GET `/api/saved`, POST/DELETE `/api/saved/{prop_id}`.
- Enquiries: POST `/api/enquiries`, GET `/api/enquiries/me`, GET `/api/enquiries/{enq_id}`, POST messages; owner GET `/api/leads`, GET/PATCH `/api/leads/{lead_id}`. Preserve consent/masking/participant authorization.
- Listings: POST `/api/listings`, GET `/api/listings/mine`, GET `/api/listings/{prop_id}/edit`, PUT `/api/listings/{prop_id}`.
- Broker: POST `/api/broker/apply`; reuse existing current-account broker projection after field-level review, not a fabricated broker-profile endpoint.
- Media: POST `/api/uploads`, GET `/api/files/{file_id}`; preserve provider selection and private authorization. Never issue private query-token URLs or send private documents through public image optimization.
- Safety/legal: existing property report and account deletion request contracts; review retention semantics before labeling deletion complete.
- Plans: existing featured-plan reads only. Payment initiation/commission/policy changes excluded pending separate approval.

Endpoint presence is not proof that every requested screen can be completed. Full schemas, ownership and privacy projections must be inspected before each workflow is implemented.

### Expected files (all paths relative to `F:\projects\landvilla`)

Existing files expected to change, after contents/diff inspection and backup:

- `web/src/lib/proxy.ts`, `browser-client.ts`, `contracts.ts`, `server-api.ts` — scoped queries/transports/account reads; preserve auth contracts.
- `web/src/components/site-header.tsx`, `site-footer.tsx` — real navigation.
- `web/src/app/(public)/page.tsx`, `web/src/app/layout.tsx`, `globals.css`, `robots.ts` — discovery shell/content/crawl policy.
- `web/tests/proxy.test.ts`, `contracts.test.ts`, `browser-client.test.ts` — expanded regression coverage.
- `web/README.md`, `web/PHASE1_COMPLETION_REPORT.md` — correct stale status and commands, with backups.

Proposed new files:

- `web/src/lib/property-contracts.ts`, `property-query.ts`, `public-api.ts`, `account-api.ts`, `seo.ts`.
- `web/src/components/properties/{property-card,search-form,filter-panel,pagination,image-gallery,enquiry-form}.tsx`.
- `web/src/components/account/{profile-form,saved-properties,listing-form,image-upload,broker-application,enquiry-thread}.tsx`.
- `web/src/app/(public)/properties/page.tsx`, `buy/page.tsx`, `rent/page.tsx`, `property/[slug]/page.tsx`.
- `web/src/app/(public)/about/page.tsx`, `approach/page.tsx`, `contact/page.tsx`, `faq/page.tsx`, `city/[city]/[locality]/page.tsx`.
- `web/src/app/(account)/account/{layout,page}.tsx`, `saved/page.tsx`, `enquiries/page.tsx`, `enquiries/[id]/page.tsx`, `listings/page.tsx`, `listings/new/page.tsx`, `listings/[id]/edit/page.tsx`, `broker/page.tsx`, `settings/page.tsx` (the latter routes nested under `account/`).
- `web/src/app/sitemap.ts` and appropriate route loading/error files.
- `web/tests/{property-query,property-contracts,account-api,media-proxy}.test.ts`, proposed browser acceptance suite after selecting an available supported runner.
- `web/reports/PHASE2_COMPLETION_REPORT.md`.

This is a proposed file map, not created code. No package additions are assumed; if a browser/component runner or accessible control dependency is needed, propose compatible pinned dependencies before installing. Existing Next/React/CSS/native controls can cover much of the scope.

### Backend/database/mobile impact and separate gates

Approved Phase 2 web work can reuse existing contracts without backend or database schema changes. Expo remains untouched. Uploads/submissions/enquiries will create normal business records only when explicitly exercised with approved data; tests must stay isolated by default. No seed or production operation.

Separate backend proposal required for multi-city/area filtering, missing owner status transitions, unsupported account preferences, CMS/support-content persistence, granular staff roles, central staff leads and extended finance/metrics. Each proposal must specify additive endpoint/schema, validation, authoritative permissions, compatibility and data/index impact before implementation. None is approved here.

Phase 2 also depends on approved public content/contact details, safe public property projections, usable data and owned provider/test accounts. If those remain absent, implement independent discovery/UI work and document blocked workflows rather than fake them. Phase 3/4 remain outside Phase 2 approval.

## Local commands and next decision

Existing servers remain running and were not terminated. Do not start duplicates. When starting them manually later, web command is:

```powershell
Set-Location F:\projects\landvilla\web
npm.cmd run dev
# http://localhost:19006
```

Verification commands are `npm.cmd run test`, `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build` from that directory. Do not use production `npm.cmd start` as a substitute for HTTP development authentication; production configuration requires explicit HTTPS origins.

Decision requested: approve the above Phase 2 web-only implementation against supported existing APIs, with backend extensions separately gated. Live Phase 1 authenticated acceptance remains an explicit outstanding gate and must not be described as passed.
