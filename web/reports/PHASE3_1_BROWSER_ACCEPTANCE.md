# LANDVILLA browser acceptance and HTTP evidence

Date: 2026-11-10 (Asia/Calcutta). Browser acceptance is **BLOCKED**, not passed. The browser tool returned `Local browser use is disabled in Work settings`. Existing backend and web services were reachable; neither was started, stopped or restarted. Anonymous HTTP requests were made to loopback only, with response bodies/records omitted from logs.

PASS below means the stated HTTP or offline scope only. It does not prove browser rendering, accessibility or authenticated workflows. No OTP, Google login, private document retrieval, upload, real mutation or payment was performed.

| ID | Route/feature and steps | Expected | Actual | Status/evidence |
|---|---|---|---|---|
| HTTP-01 | GET backend `/health` | 200 | 200 | PASS liveness only |
| HTTP-02 | GET `/`, `/properties`, `/buy`, `/rent` | 200 without unavailable/error marker | All 200; no unavailable marker | PASS HTTP |
| HTTP-03 | GET `/about`, `/approach`, `/contact`, `/faq` | Honest content shells | All 200 | PASS HTTP; approved contact/FAQ content BLOCKED |
| HTTP-04 | GET `/legal/privacy`, `/legal/terms` | Policy routes respond | Both 200, no outage marker | PASS HTTP; legal approval BLOCKED |
| HTTP-05 | GET `/robots.txt`, `/sitemap.xml` | Prelaunch crawl controls | Both 200; source disallows crawling and emits no URLs | PASS prelaunch only |
| HTTP-06 | GET `/login`, `/account`, `/account/profile`, `/account/saved`, `/account/enquiries`, `/account/listings`, `/account/leads`, `/account/broker/apply` | Entry/account shells | All 200 | PASS HTTP shells; hydration/authenticated content BLOCKED |
| HTTP-07 | GET `/api/properties?limit=1` | 200 valid public pagination | 200, integer total | PASS |
| HTTP-08 | GET property query buy/rent, category/type, zone/locality using actual metadata, min/max price, BHK, q, both price sorts, page 2/limit 5 | Supported query 200 | All 200 | PASS HTTP contracts; result relevance requires browser/data review |
| HTTP-09 | GET invalid key, duplicate purpose, limit 51, page 0, reversed prices | Reject before forwarding | All 400 | PASS |
| HTTP-10 | Read a returned property ID, follow its detail URL | Page displays public property, demo label when applicable, noindex | 200, demo warning and noindex present | PASS HTTP; gallery interactions BLOCKED |
| HTTP-11 | Follow returned locality slug | Locality route works | 200 | PASS HTTP |
| HTTP-12 | GET `/city/ujjain` | City directory | Initially 404; now 200 with API-supplied locality directory | PASS after fix; offline empty/outage/unknown-city tests |
| HTTP-13 | GET `/unknown-landvilla-audit-route` | 404 | 404 | PASS |
| HTTP-14 | GET nonexistent property/locality and unsupported city | HTTP 404 and not-found content | Initially HTTP 200; moved global loading boundary to discovery routes; all now 404 | PASS after fix; smoke script regression |
| HTTP-15 | GET `/admin`, `/admin/properties`, `/admin/brokers`, `/admin/payments`, `/admin/staff` anonymously | No protected content | Sign-in gate; no decision controls | PASS anonymous HTTP gate, shell status 200 |
| HTTP-16 | GET `/api/admin/stats`, `/api/admin/listings?status=pending_review`, `/api/admin/brokers?status=pending`, `/api/admin/payments`, `/api/auth/me` anonymously | 401 | All 401 | PASS |
| HTTP-17 | POST synthetic empty payload to moderation/upload routes without Origin/CSRF | Rejected by web before backend | 403 | PASS; no backend/provider write |
| HTTP-18 | GET public proxy and inspect key names only | No account/private record keys | No owner ID, email, mobile, documents, moderation, address or posted-by name; 200 | PASS after projection fix; synthetic unknown-field regression also passes |
| BROWSER-01 | At 390px, 768px and 1440px open home/discovery/detail; inspect overflow, navigation, labels, focus and console | Usable responsive experience, no errors | Browser tool disabled | BLOCKED |
| BROWSER-02 | Submit every filter, paginate, open details, use gallery/copy link | Correct state and navigation | Parser/transport/harness tests pass; actual browser unavailable | BLOCKED browser |
| BROWSER-03 | Owned test account: OTP/Google sign-in, refresh, two tabs, expiry, logout | Server cookie and session lifecycle | No owned account/provider test executed | BLOCKED |
| BROWSER-04 | Two controlled accounts: saved/enquiry/conversation/profile access | Ownership/privacy enforced | Offline regressions only | BLOCKED live |
| BROWSER-05 | Controlled owner: create/edit listing, status, leads | Actual persisted workflow | No authorized disposable record set | BLOCKED |
| BROWSER-06 | Controlled broker: application, private document, review status | Correct approval and privacy | No real upload/application | BLOCKED |
| BROWSER-07 | Authorized admin: review photos/docs, confirm action, refresh; ordinary role rejected | Server permission/status enforcement and audit | Offline authorization tests; anonymous smoke only | BLOCKED authenticated |
| BROWSER-08 | Upload synthetic JPEG/PNG/PDF; wrong type/size; cross-account private GET | Correct rejection and private access | Offline upload tests only; no R2 calls | BLOCKED live |

## Manual browser procedure

1. Enable the supported local browser tool or open `http://localhost:19006` manually. Keep backend health reachable. Use DevTools at 390, 768 and 1440 CSS pixels; check horizontal overflow, keyboard-only focus order, skip link, form labels, and console/network failures.
2. Traverse header/footer links; open city directory, an available locality and a returned property. Verify demo banners; never treat examples as inventory. Use buy/rent, each filter, sort and pagination; reload the resulting URL and check retained values. Enter an invalid query and verify a helpful rejection. Confirm image fallback and clipboard failure message.
3. Use only owner-approved test accounts and disposable records in a reviewed test environment. Confirm consent before provider/record writes. Request one OTP, test wrong/expired code without repeated sends, then sign in; inspect HttpOnly/Lax/Secure cookies (Secure on HTTPS) and absence of bearer tokens in browser storage. Reload, switch account/tab, expire/revoke, logout.
4. With two accounts, exercise saved items, enquiry consent, private notes/conversations and file access. Only the participant/owner or authorized admin should receive private information. Test synthetic uploads against authorized staging storage only.
5. Use an existing approved administrator. Open each supported module, search/paginate within its disclosed returned batch, review full listing/photos and broker documents, confirm one authorized decision and verify backend/audit outcome. Cancel must not write. Attempt with an ordinary account and verify denial. Do not elevate roles or create an admin to complete this test.

## Remaining functional boundaries

Admin property/broker decisions reuse existing endpoints. Packages, payments, locations, reports and contact-access logs have projected read views. General users, staff/RBAC, global enquiries, generic CMS and full audit-log APIs remain unavailable. Search/pages apply to the backend's bounded returned batches, not server-wide pagination. Price changes, report resolution, location editing and general legal publication remain deferred pending business controls or further implementation. No complete module or launch acceptance is claimed for an unavailable state.

## Final recheck

Final web suite: 92 passed, zero failed/cancelled/skipped; typecheck, lint and production build exit 0. Explicit `node scripts/smoke-public.mjs`: 26/26 PASS. A GET-only crawl of 66 unique internal links from nine public entry pages found 66 HTTP 200, zero redirects/failures and zero not-found fallback markers. The initial crawl found 14 locality links with no inventory returning not-found content; known localities now show an empty state and remain distinct from unknown localities (404). Root loading boundary was relocated to properties and reused by buy/rent so async notFound can set HTTP status before headers stream. Visual layout, hydration, console and authenticated browser acceptance remain BLOCKED.
