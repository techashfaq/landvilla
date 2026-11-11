# LANDVILLA current state audit

Date: 2026-11-10 (Asia/Calcutta). Scope: current checkout, safe isolated checks and anonymous local HTTP reads. Historical reports are background only.

## Verified baseline

- Branch `dev`, tracking `origin/dev`; HEAD `de39e8e7f7915eef8ff693bd01edc42f1c54f8b6`.
- Recent commits include merged backend PR #1, web PR #2, mobile PR #3. No branch, worktree or remote change performed.
- Initial modified files were exactly `web/src/lib/proxy.ts` and `web/tests/proxy.test.ts`. Their validated public property read/query forwarding additions are preserved. Subsequent work may extend the proxy without replacing these additions.
- Git emits the pre-existing access-denied warning for `backend/.pytest_cache`; no cache/ACL repair attempted.
- Independent FastAPI backend, Next.js web, Expo mobile. No framework/dependency changes planned. Read README, existing reports, current route tree, proxy, public transport, account components and configuration. Backend/security and staging audits recorded separately.

## Executed baseline commands

From repository: `git status -sb`, `git rev-parse HEAD`, `git remote -v`, `git log -6 --oneline`, targeted `git diff` and file reads.

From web, sequentially: `npm.cmd run test` (72 passed; zero failed/cancelled/skipped), `npm.cmd run typecheck` (exit 0), `npm.cmd run lint` (exit 0), `npm.cmd run build` (exit 0; Next.js 16.4.3). Build recognized `.env.local`; values were not printed. Generated `.next` and TypeScript artifacts are expected.

Backend offline unit execution/result is recorded in PHASE3_5_SECURITY_REVIEW.md and the final report; no integration/seed/UI/database-reset suites authorized or run.

## Live findings

Existing services answered `http://127.0.0.1:8000/health` and `http://localhost:19006/` with HTTP 200. No service was started or restarted. Anonymous GET smoke: public properties 200; invalid/duplicate filters 400; admin stats and auth/me 401. Public pages and account shells returned 200; unknown route 404. Account/admin shell 200 does not establish authenticated acceptance.

Confirmed gaps:

1. `/city/ujjain` returns 404; locality pages exist, but no city directory.
2. ShareProperty dereferences unavailable clipboard API before its promise catch; this can break copying in unsupported contexts.
3. Homepage incorrectly claims enquiries/submissions are future features despite implemented account routes.
4. Admin provides only overview metrics; backend capabilities exceed current web UI.
5. Contact/FAQ/business policies remain dependent on owner-approved information. No contact details or policies may be invented.
6. Crawl policy is intentionally prelaunch noindex, robots disallow-all, empty sitemap. This protects demo inventory from intentional indexing but is not finished launch SEO.
7. Browser automation attempt failed: `Local browser use is disabled in Work settings`. Visual/responsive/keyboard/console and real authenticated browser acceptance remain BLOCKED; HTTP and synthetic harness checks are separate evidence.

## Prioritized implementation plan

- Preserve and extend validated proxy reads; audit backend/public data exposure and authorization first.
- Fix missing city navigation, share fallback, and inaccurate public copy with focused offline regressions.
- Add admin modules using real existing endpoints, strict method/path/query/body policies, existing browser session and CSRF, independent server access checks, and explicit unavailable states for absent APIs.
- Re-run web tests/typecheck/lint/build; run backend offline tests; repeat anonymous smoke against existing services. Do not exercise real account/provider/database writes without controlled fixtures and explicit authorization.
- Record browser steps, security findings, approved-content gaps and conditional AWS architecture in requested reports. No staging/production deployment, cloud changes, installs or Git mutations.

## Limitations

Passing source checks/build do not establish real OTP, session lifecycle, broker approval, upload, payment or admin workflows. AWS account region/IAM verification requires an accessible authorized account context. Secrets, personal data and live response bodies are excluded from evidence output.
