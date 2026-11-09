# LANDVILLA web — Phase 1 foundation

> **2 November 2026 update:** Phase 2 public/account/listing source is now implemented. Current verification is 49 web tests plus passing lint, full TypeScript and production build. Dependencies and the web lockfile now exist. The installation blocker below is historical. See `reports/PHASE2_COMPLETION_REPORT.md` for current scope, commands, API/security changes, browser blockers and incomplete acceptance gates. Do not interpret the older foundation-only route description as the current allowlist.

Independent Next.js App Router website and read-only admin shell. Existing FastAPI owns all identities, sessions, authorization, database records and media. Expo `../frontend/` is unchanged. No database or storage SDK is included here.

## Current verification boundary

Source implementation and dependency-free adapter tests are present. **Installation/build verification is blocked**, not complete: automatic approval review failed due to its usage limit before npm metadata could run. No dependency download or installation occurred and no package-lock was fabricated. `package.json` contains exact candidate pins; registry availability, peer compatibility and resolved lockfile still need verification through the approved npm installation. Do not deploy this unbuilt foundation.

## Windows local development

Use Node 24 (verified local Node: 24.21.0) and PowerShell. This application is isolated; run all npm commands from `F:\projects\landvilla\web`.

After tool/network approval is restored (or run these locally yourself), verify the pins and install:

```powershell
Set-Location F:\projects\landvilla\web
npm.cmd view next@16.4.3 engines peerDependencies --json
npm.cmd install
npm.cmd run test
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run dev
```

Stop on install/peer/version errors; do not use `--force`, `--legacy-peer-deps` or change Expo dependencies. Review the resulting **web-local** package-lock. Once it exists, use `npm.cmd ci` for repeatable installs. There is no monorepo/workspace installation step. No global packages are required. Tests use Node's native TypeScript stripping and `node:test`, avoiding an additional test framework for this foundation.

Development URL: **http://localhost:19006**. Use `localhost`, not the LAN IP or an alternate origin. 19006 is an existing default trusted origin in the backend; this avoids changing backend source/environment. If that port is occupied, identify the owner; do not terminate an unrelated Expo/server process. Any alternate web port must already be accepted by the backend's operator-managed WEB_APP_ORIGINS. This phase did not change that setting.

The existing backend must be running and ready on http://127.0.0.1:8000. It is not started by the website and its startup database check must not be bypassed. Existing command (root, only if no instance already owns the port):

```powershell
Set-Location F:\projects\landvilla
.\backend\.venv\Scripts\python.exe -m uvicorn server:app --app-dir backend --host 127.0.0.1 --port 8000
```

A running backend requires its existing valid Atlas/provider/index configuration. Never change DB name/URI, seed or provision indexes to make this site load. The public homepage shell works without a backend; sign-in and admin explain unavailable dependencies instead of inventing data.

## Environment

No actual `.env` was copied from backend or Expo. Development defaults work for the two loopback origins above. If you need overrides, copy `.env.example` to a new `.env.local` **only if it does not already exist** and configure privately. Never paste credentials into chat/logs.

| Variable | Scope | Meaning |
|---|---|---|
| BACKEND_ORIGIN | Server only | Fixed FastAPI origin, development default http://127.0.0.1:8000; no path, query or embedded credentials. |
| WEB_ORIGIN | Server only | Exact browser origin, development default http://localhost:19006. Must match backend trusted origin configuration. |
| NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID | Public, bundled | Optional Google web OAuth audience matching backend GOOGLE_CLIENT_IDS. No client secret. Blank disables Google sign-in with an explanation. |

Production runtime requires explicit HTTPS origins; insecure remote origins, credentials, paths and self-proxy loops fail closed. `npm.cmd start` uses production mode, so it is **not** a substitute for local HTTP `npm.cmd run dev`. A production-mode auth smoke test needs approved HTTPS origins, a correctly configured existing production/staging backend and ingress. No production configuration was made.

For Google, the authorized JavaScript origin must match this website exactly; use the existing owned Google Cloud project/audience. Do not change production OAuth configuration merely to test localhost. This code follows the existing GIS nonce contract; no managed callback or new identity provider is introduced. No real Google/OTP action was executed during implementation.

## Architecture and scope

- Server-rendered original public shell at `/` with responsive LANDVILLA terracotta/stone styling and original CSS architecture illustration. Illustration is explicitly not a property. No fake listings, counters, reviews, app downloads or unusable search form.
- `/login` integrates existing email/mobile OTP login, email OTP registration, Google nonce/token exchange, session restoration and logout. Registration role selection cannot grant staff authority. Terms/privacy text loads from the existing backend at `/legal/terms` and `/legal/privacy`, escaped as text, never injected HTML.
- `/admin` checks `/api/auth/me` server-side. Stats loader independently checks access; backend `/api/admin/stats` remains authoritative. Only the four actual counts are rendered, and only when available. No additional staff roles, moderation, pricing or payment actions implemented.
- `/api/[...path]` is a fixed-upstream forwarding route. Phase 1 allowlist covers meta, auth bootstrap/me/logout/OTP/Google/nonce, profile read, admin stats, terms/privacy JSON. No Phase 2 mutation routes, native managed callbacks, query credentials, private-file links, uploads, payments or database operations added. Future needed routes require explicit review; no open proxy.
- Browser requests carry same-origin cookies and in-memory CSRF. The proxy verifies exact unsafe Origin and rejects cross-site/bearer/query requests before forwarding. It preserves original Origin/Referer, CSRF and individual Set-Cookie headers. It strips caller-supplied forwarded IP/host/scheme, forwards only the appropriate LANDVILLA session cookie, bounds JSON request bodies to 32 KiB, refuses redirects and sanitizes server/network failures. No forged trusted Origin is created.
- Auth state is one per-browser-provider instance. No token in localStorage/sessionStorage/URLs; no session token returned or stored by Next. Cross-tab BroadcastChannel transmits only a change notification. Generation checks reject stale responses; no private query cache is introduced. Server fetches are request-local and `no-store`.
- Both root metadata and robots disable indexing while this is a foundation. No fake sitemap or premature property SEO pages. Phase 2 must deliberately revise crawl policy after real content and canonical review.

The built-in forwarder handles JSON only in this phase. Multipart/media transport is intentionally not exposed until the posting workflow is approved; existing mobile `/api/files/{id}` and R2 are untouched. We do not issue query-token links or use private media in an image optimizer. Later ingress may forward directly, but it must preserve the same session/CSRF/origin and privacy invariants.

## Deployment decisions not made

Initial proposal remains landvilla.in plus `/admin`; future admin.landvilla.in has a separate host-only login/session by default. No Domain cookie, cross-host SSO, DNS, hosting or cloud changes. The backend sees the web server as its direct caller: IP-based throttles will be shared unless a trusted ingress/client-IP policy is explicitly configured by the operator. This is a release blocker, not a reason to trust arbitrary X-Forwarded-For. No CSP tuned for Google/Next nonces or HSTS policy is claimed; current headers are baseline nosniff/frame denial/referrer/permissions policy. Production needs a reviewed CSP/ingress policy and real browser tests.

## Tests

```powershell
# Works with Node 24 even before dependencies are installed
npm.cmd run test

# Requires completed local installation
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Tests are isolated fixtures, never real OTPs, tokens, Atlas records or provider calls. The integration test opens a temporary loopback HTTP upstream, checks real forwarding/body/cookies and closes it. It does not simulate a production provider success in application code. See `PHASE1_COMPLETION_REPORT.md` for actual command results and unresolved gates.

## Manual acceptance after installation

1. Run checks above, then open desktop and mobile-width homepage. Verify no overflow, keyboard skip link/focus, readable contrast and noninteractive illustration.
2. With backend stopped, login/admin must show unavailable states without fabricated counts. Start only the intended existing backend, then retry.
3. With approved owned test contacts, exercise OTP signup/login, resend cooldown, wrong/expired/reused code, network failure and recovery. Registration requires consents and ordinary roles.
4. With configured owned OAuth, test success/cancel/rejection/replayed nonce; confirm no Google token is persisted. Real provider testing requires separate explicit authorization.
5. Inspect cookies: HttpOnly, appropriate Secure/Lax/host/path. Verify browser storage contains no bearer credentials. Test reload, expiry, logout, server revocation and account switching across two tabs.
6. Ordinary account and no-cookie requests must not receive admin counts. Approved administrator sees only actual backend stats. Change/revoke role server-side in an isolated test setup and revalidate access.
7. Malicious Origin, CSRF omission, `Authorization` header, query tokens, unsafe routes and redirects must fail. Verify no private HTML or error response is publicly cached.

Stop at Phase 1. Discovery/search/posting/moderation/CMS/finance/staff implementation requires separate Phase 2/later approval.
