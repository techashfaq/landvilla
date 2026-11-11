# LANDVILLA focused security review

Date: 2026-11-10 (Asia/Calcutta). **Incomplete security acceptance; not a penetration-test certification.** Scope: current web/backend source, synthetic web tests, anonymous loopback HTTP checks, and backend test-source review. No real credentials, private records, provider requests or database mutations were used for acceptance.

## Findings

| ID | Severity | Finding/evidence | Resolution / remaining gate |
|---|---|---|---|
| SEC-01 | High | `backend/marketplace.py` `moderate` and `set_broker` authorized admin role but did not exclude the subject administrator's own listing/application. Client hiding alone is bypassable. | Added server-side 403 checks before writes, plus four offline tests for self-review rejection, no audit/data mutation, independent administrator success and ordinary-role denial. Python AST syntax check PASS. **Backend suite execution BLOCKED; fix not accepted for staging yet.** |
| SEC-02 | Medium | Intentional public property proxy addition passed caller cookie/CSRF upstream and returned the complete upstream property record, unlike existing projected public SSR transport. Fixed-field backend stripping does not exclude future private fields. No live secret leak claimed. | Preserved query/read routing; now omits cookie/CSRF for public properties, discards upstream Set-Cookie, validates data and positively projects public wire fields. Existing `title_en`/pagination contract retained; malformed data fails with sanitized 502 and backend errors are generic. Synthetic privacy regression and live key-only check PASS. |
| SEC-03 | Medium | Admin list APIs cap results rather than providing full server pagination. Listing/broker transition validation reads state then updates by ID; concurrent moderator decisions may overwrite each other. | New UI discloses bounded search/pages and asks confirmation. True server pagination and conditional status/version updates remain required for reliable concurrent operations. No live race test performed. |
| SEC-04 | Medium | Production CSP/HSTS/trusted ingress/client-IP policy is not verified. Existing proxy strips caller forwarded IP; shared upstream IP may affect abuse limits. | Existing security checks retained; nosniff/frame-denial/referrer/permissions headers present. Review concrete HTTPS ingress and nonce/CSP strategy before staging sign-off; do not trust arbitrary forwarded headers. |
| SEC-05 | Medium | Upload protection checks extension, MIME, magic prefix and size, not full decoding/malware analysis. Real cross-account R2 acceptance not performed. | Existing limits and private owner/admin checks retained; new admin document links use authorized `/api/files/{id}` only. No public object URLs or query credentials introduced. Live synthetic upload/private-access test and file-handling policy remain gates. |
| SEC-06 | Low | Missing clipboard API throws before the original promise catch. | Guarded optional API + rejection fallback; regression PASS. Share links exclude query/fragment. |
| SEC-07 | Informational | Demo inventory is explicitly labelled; prelaunch noindex/disallow-all/empty sitemap remains in force. | Retain until real inventory and launch crawl policy approved. Robots is not access control. |
| SEC-08 | Informational | Backend `APP_ENV=staging` does not activate `production` checks. | Staging report requires `APP_ENV=production` with isolated staging resources, explicit HTTPS origins and seed/test flags disabled. No real env changed. |

No Critical finding was confirmed within this limited scope. This is not a claim that the complete application or dependencies are free of Critical/High vulnerabilities.

## Reviewed boundaries and evidence

- Browser sessions: backend cookie transport, hashed session lookup, expiry, exact origin/CSRF guard, nonce consumption and account status checks reviewed. Web adapter stores session state in memory and rejects native bearer responses; existing session tests pass. No browser tokens added to localStorage.
- Administrative access: layout checks role; each new resource reader independently checks `/api/auth/me` before fetching records; backend routes use `Depends(admin_user)`. No arbitrary user/staff grant routes exposed. Anonymous live reads of stats/listings/brokers/payments return 401. Non-admin and malformed-response synthetic tests pass.
- Admin writes: exact reviewed routes, bounded status queries, existing Origin/CSRF proxy guard, session generation checks, role check, explicit confirm/cancel, matching backend decision confirmation before success. Live writes were not performed. Backend self-review checks are pending unit execution.
- Private data: new admin pages use explicit field projections after authorization and no-store server fetches. Private document URLs preserve backend authorization/audit. Public properties positively project reviewed fields. No account contact data is copied into reports.
- IDOR: source checks in enquiry/lead/file and listing ownership flows reviewed; injected authorization-denial and existing account privacy regressions cover only synthetic behavior. Two real test-user acceptance remains blocked.
- Query safety: public query whitelist rejects duplicate/unknown/out-of-range values; backend text search escapes regex; admin path/query policies reject credentials, arbitrary routes and query injection. Invalid live public requests return 400.
- Error handling: web 5xx/network errors sanitized; new public malformed JSON/data produces generic 502. General authenticated upstream 4xx response sanitization remains dependent on backend behavior; BrowserClient messages are generic. No exception details exposed by the new admin projections.
- Rate limiting/payment: existing identity limits and signature/provider checks preserved. No live OTP delivery or payment transaction occurred; no payment success UI fabricated. Paid-order counts are not revenue or settlement confirmation.
- Environment/secret hygiene: `.env.local` remains ignored; no real environment file values printed or edited. Example/config matrix and business approval gates are in PHASE3_6_STAGING_READINESS.md. No exhaustive history/secret or fresh online dependency vulnerability scan was performed; those remain separate gates.

## Backend verification blocker and compatibility

Attempted from backend: `./.venv/Scripts/python.exe -m unittest discover -s tests/unit -v`. Sandbox execution failed before Python started with `Unable to create process using` the venv's configured Python312 executable. An outside-sandbox retry was requested and then cancelled; no permission was bypassed. The independently verified owner interpreter may still work; this failure does not establish that the user's venv is broken.

No backend test is marked passed in this run. Earlier 133 passed is historical. Global Python parsed the two changed Python files via `ast.parse` only; this imports no app and is not a substitute for the suite. Four new tests use the existing `mongomock`/in-process ASGI fixture. No pytest/integration/seed/UI test suite was executed.

API compatibility: independent administrators retain existing endpoints/response shapes. Self-moderation now returns 403 for browser and native callers alike. No Mongo schema, index, migration, storage layout, auth transport or mobile source change. Public web proxy intentionally removes unreviewed extra fields while retaining the documented public data fields and validated query routing.

## Acceptance gates

1. Execute the backend offline suite with approved interpreter access and resolve any failure before accepting SEC-01.
2. Browser/provider acceptance with owner-approved controlled accounts and synthetic disposable records, including private media and role revocation. No production mutation.
3. Independent HTTPS/staging ingress, rate limits, headers and dependency advisory review.
4. Review concurrent moderation and full administrative audit/pagination requirements before multi-operator use.
