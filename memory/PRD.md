# LANDVILLA – PRD

## Original problem statement
Ujjain-first (Madhya Pradesh) real estate marketplace like Housing.com, expanding across India. Trust-first: verified listings, real owners/brokers, good leads, mobile-first Hindi + English. Full vision: buyers/tenants, owners, brokers, builders, admins; moderation, duplicate detection, enquiry tracking, subscriptions, featured listings, payments, SEO locality pages, analytics, configurable branding/pricing/cities from admin. Seed Ujjain city, 5 zones, 32 localities (EN+HI, aliases, parent links, slug, active, source, last-verified), categories, types, amenities, listing/verification statuses, clearly fictional demo listings. Never invent coordinates, boundaries, postal codes, prices, owners or verified status. Idempotent seeds, unique constraints, migrations, seed report, tests.

## User choices
- MVP scope: Buyer/Tenant app (search, filters, details, enquiry)
- Brand: LANDVILLA · Auth: Emergent-managed Google login · Languages: English + Hindi

## Architecture
- Expo Router app (tabs: Home, Saved, Enquiries, Profile; stack: property/[id], login modal, admin/localities)
- FastAPI + MongoDB (`server.py`, `seed.py` migrations + idempotent seeding, `seed_data.py` reference data)
- Mongo collections: cities, zones, localities, property_categories, property_types, amenities, listing_statuses, verification_statuses, properties, users, user_sessions, enquiries, saved, audit_logs, schema_migrations, seed_reports
- Unique indexes on slugs, (city_id, slug), ids, saved(user, property), demo_key

## Implemented (Oct 2026)
- Seed: 1 city, 5 zones, 32 localities (all `unverified`, source `founder_provided_list`, lat/lng null, zone tentative; 7 with zone unassigned), 36 candidate names resolved (aliases dedupe e.g. "Free Ganj"→Freeganj), 0 unresolved names, 6 categories, 10 types, 12 amenities, 6 listing + 4 verification statuses, 20 fictional DEMO listings (dev only via SEED_DEMO_LISTINGS)
- Search API with DB-validated locality/zone/category/type filters, alias text search, budget, BHK, sort, pagination
- Property detail, saved list, enquiries (validated Indian mobile, 24h duplicate block), My Enquiries
- Google login (Emergent), role-based admin via ADMIN_EMAILS
- Admin locality workflow: create, edit, verify (requires source), deactivate/activate, merge (moves listings + aliases), audit log, loop/conflict checks
- EN/HI toggle persisted, Devanagari fonts (Mukta/Hind)
- Tests: backend/tests (seed idempotency, duplicates, locality filtering, API) – 27 passing

## Iteration 2 (Oct 2026) – built, backend tests pass, NOT yet verified by testing agent
- Owner/Broker listing submission with photos (object storage), owner-authority declaration, moderation disclaimer
- Broker verification (private docs, RERA recorded separately), admin approve/reject/suspend; server-enforced gate
- Admin approval queue (approve / reject / request changes) + duplicate flags (price/area, title, same lister, identical photo hash)
- Lead inbox: masked buyer phone unless per-enquiry consent, audited reveal, status/follow-up/notes, in-app messages
- Featured plans (₹299/30d, ₹499/45d – admin editable), Razorpay order/checkout/signature verify/webhook/idempotent activation/expiry
- Pending: Razorpay TEST keys from user (secure card requested), testing-agent run, commission records workflow

## Play Store readiness review (Oct 2026) – blockers found
- No in-app account deletion; no privacy policy/terms; SEED_TEST_SESSIONS + SEED_DEMO_LISTINGS true in live slot
- No user block/report UI for messages; Featured payments via Razorpay need Play Billing classification
- expo-image-picker camera/mic perms + media-library permission request to tighten

## Iteration 3 (Oct 2026) – Play readiness fixes, commissions, SEO (testing agent: all flows pass)
- Account deletion (DELETE confirm + sign-in within 30 min, sessions revoked, data deleted/anonymised, payments retained pseudonymised); public page /api/legal/delete-account + admin close requests
- Privacy Policy & Terms (DRAFT, admin-editable via PUT /api/admin/legal/{doc}); public /api/legal/privacy, /api/legal/terms; linked on login, profile, listing form
- Test tokens (`test_session_*`) rejected whenever SEED_TEST_SESSIONS!=true; test users purged at startup; demo listings hidden when SEED_DEMO_LISTINGS!=true
- Report (listings, conversations; rate limited 10/day) + Block (blocks messages & enquiries) + admin Reports queue with resolution notes and audit log
- Featured plans ₹299/15d, ₹499/30d; purchase offered on web only (app hides it; server rejects non-web clients) pending Play/App Store billing decision
- Commission agreements admin module: state machine, evidence & deal value required, invoices, payment recording blocked until legal review + collection enabled, full audit trail
- Locality SEO pages /api/l/ujjain/{slug} (canonical, unique meta, JSON-LD, live non-demo listings, noindex when thin) + /api/sitemap.xml
- Android: camera/mic disabled for photo picker, blockedPermissions list, system photo picker on Android

## Manual / pending
- Set live SEED_TEST_SESSIONS=false and SEED_DEMO_LISTINGS=false; add Razorpay TEST keys; set PUBLIC_BASE_URL; fill support email/grievance officer/legal entity in Privacy & Terms; lawyer review
- SEO pages live under /api/ on the backend host; a real website domain is needed for proper search indexing

## Backlog
- P0: Owner/broker listing submission + admin approval queue; enquiry management for owners/brokers; broker tools
- P1: Payments (Razorpay) for featured listings/subscriptions; duplicate listing detection; image uploads (object storage); admin CMS for brand/pricing/cities
- P2: SEO locality pages (web), analytics dashboards, WhatsApp/SMS alerts, maps with verified geocoding
- Launch: privacy policy, ToS, backups, monitoring, disable SEED_TEST_SESSIONS & SEED_DEMO_LISTINGS in production

## Handover (June 2026)
- Added README, docs/HANDOVER_REPORT.md, WINDOWS_SETUP.md, ANDROID_BUILD_AND_PLAY.md, DATABASE_MIGRATION.md, scripts/windows-setup.ps1,
  backend/scripts/db_export.py + db_verify.py, .env.example files, requirements-local.txt, hardened .gitignore. No app behaviour changed.
- Pending user actions: Save to GitHub, confirm SEED_* live=false, set Razorpay test keys + webhook, ADMIN_EMAILS, upload key, versionCode bump.
