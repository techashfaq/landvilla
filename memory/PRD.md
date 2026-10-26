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

## Backlog
- P0: Owner/broker listing submission + admin approval queue; enquiry management for owners/brokers; broker tools
- P1: Payments (Razorpay) for featured listings/subscriptions; duplicate listing detection; image uploads (object storage); admin CMS for brand/pricing/cities
- P2: SEO locality pages (web), analytics dashboards, WhatsApp/SMS alerts, maps with verified geocoding
- Launch: privacy policy, ToS, backups, monitoring, disable SEED_TEST_SESSIONS & SEED_DEMO_LISTINGS in production
