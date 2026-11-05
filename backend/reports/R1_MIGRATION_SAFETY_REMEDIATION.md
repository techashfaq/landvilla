# R1 identity migration safety remediation

Date: 2026-11-02. Result: PASS for R1 remediation and isolated regression verification; awaiting review. Not production acceptance.
Worktree: F:/projects/landvilla-integration-backend
Branch: integration/backend
Unchanged HEAD: e9dd3e0b6ad294ae37d25a651f67548cece601b0
PR base: e53e776294851a4f9a7c35ab9079e8efda927575

## Root cause and execution-path map

Before this change, seed.MIGRATIONS contained both 001_indexes and 002_identity_indexes. That made these ordinary paths invoke identity index creation without the dedicated CLI guards:

1. seed.run_migrations(database) -> registry callbacks -> identity indexes and marker.
2. seed.seed_all(database) -> run_migrations -> same registry.
3. python seed.py -> __main__ -> asyncio.run(_main()) -> configured client/database -> seed_all -> registry.
4. server.startup(), when SEED_ON_STARTUP=true -> seed_all -> registry. Production import already rejects startup seeding, but other environments still reached implicit identity provisioning.
5. Existing legacy backend/tests/test_seed.py calls seed_all; those database-backed integration tests were inspected by call-site search only and were NOT executed.

The intended explicit path is scripts/apply_identity_indexes.py -> main() confirmations/config validation -> apply_indexes() actual database check, ping and duplicate preflight -> m002_identity_indexes -> success marker. This path remains unchanged. inspect_identity.py and identity.require_identity only inspect the marker/index prerequisites; they do not provision indexes.

## Minimal fix

backend/seed.py:71-73 now registers only 001_indexes for ordinary migrations. A comment identifies the dedicated identity provisioning CLI. All other seed behavior, reference migration ordering and both index-definition functions remain unchanged. Normal seeding does not remove pre-existing indexes or migration markers.

The existing authentication test fixture now explicitly invokes m002_identity_indexes against MemoryDB and inserts its marker after reference seeding. This is test-only setup, not a runtime fallback or bypass. It makes the fixture's authentication prerequisites explicit instead of relying on the bug.

No schema change, refactor, new dependency or server edit was required.

## Changed/created files

- Modified: backend/seed.py — remove only migration 002 from ordinary dispatch; explanatory comment.
- Modified: backend/tests/unit/test_regressions.py — explicit identity provisioning and marker in isolated test fixture.
- Created: backend/tests/unit/test_migration_dispatch.py — six R1 regression tests.
- Created: backend/reports/R1_MIGRATION_SAFETY_REMEDIATION.md — this report.

The pre-existing untracked backend/reports/PR1_READ_ONLY_REVIEW.md is preserved and unchanged. No R2–R6 fixes are included.

## Regression coverage

Six new tests:

1. test_run_migrations_never_dispatches_identity — first run applies only 001, second applies nothing; no identity index or marker.
2. test_seed_all_reference_data_without_identity — cities/localities seeded, rerun idempotent, no identity index or marker.
3. test_standalone_seed_entrypoint_without_identity — executes actual seed.py __main__ with runpy, mocked Motor client and dotenv, real in-memory seed logic; client closes and no identity provisioning.
4. test_startup_seeding_without_identity — invokes actual startup coroutine with mocked ping and in-memory database, actual seed_all and marketplace reference seeding; no identity provisioning.
5. test_existing_identity_indexes_and_marker_preserved — explicitly constructs identity indexes in memory, then confirms ordinary seeding preserves all index options and marker sentinel.
6. test_dedicated_cli_missing_environment_and_uri_fail_closed — absent APP_ENV, empty URI and wrong DB all return refusal code 2 without constructing a client.

Each of the first four entry-point tests covers the Cartesian product of development/production/missing APP_ENV/staging and landvilla_dev/wrong_database: eight cases per path. Environment modifications exist only inside patched test-process scopes. The startup test deliberately invokes the dispatcher directly even for combinations production import would reject, proving dispatcher separation independently of the earlier guard. It does not claim production server startup is permitted.

The existing 14 security tests continue covering CLI import safety, both confirmation arguments, production/unknown environments, duplicate preflight, actual DB mismatch, mocked success and sanitized failures. No provider/database operation occurred outside mocks or MemoryDB. No real migration was executed.

## Before/after evidence and exact commands

All commands ran in F:/projects/landvilla-integration-backend using:
F:/projects/landvilla-dependency-qa-20261102-boto3/Scripts/python.exe

### Before production fix

    & 'F:\projects\landvilla-dependency-qa-20261102-boto3\Scripts\python.exe' -B -m unittest discover -s backend/tests/unit -p test_migration_dispatch.py

Exit 1: 6 test methods ran in 1.073 seconds; 32 failing subtests across the four unsafe entry-point tests. The dedicated refusal and preservation tests passed. These are 32 subtest failures, not 32 additional test methods. This reproduces the original defect using the new tests before changing seed.py.

### After fix — targeted

    & 'F:\projects\landvilla-dependency-qa-20261102-boto3\Scripts\python.exe' -B -c "import unittest,logging,sys; logging.disable(logging.CRITICAL); r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('backend/tests/unit',pattern='test_migration_dispatch.py')); sys.exit(not r.wasSuccessful())"

Exit 0: 6/6 tests passed in 1.215 seconds, including all environment/database subtests.

### After fix — syntax and full unit suite

    & 'F:\projects\landvilla-dependency-qa-20261102-boto3\Scripts\python.exe' -B -c "import ast,pathlib,unittest,logging,sys; files=list(pathlib.Path('backend').rglob('*.py')); [ast.parse(p.read_text(encoding='utf-8-sig')) for p in files]; print('Syntax files:',len(files),flush=True); logging.disable(logging.CRITICAL); r=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover('backend/tests/unit')); sys.exit(not r.wasSuccessful())"

Exit 0: 31 Python syntax files passed; 98/98 tests passed in 11.615 seconds. This is the prior 92 tests plus six R1 tests. The existing logging tests intentionally re-enable capture and emitted only sanitized categories.

### Diff and source verification

    git diff --check
    git diff -- backend/seed.py backend/tests/unit/test_regressions.py
    rg -n 'run_migrations|seed_all|m002_identity_indexes|002_identity_indexes' backend --glob '*.py'
    git status --short --untracked-files=all

Exit 0. Whitespace check passes; Git emits an LF/CRLF conversion advisory for the existing regression file, not a whitespace error. The new untracked test file was separately checked for trailing whitespace and exactly one final newline.

Additional Python AST comparisons confirmed m001_indexes and m002_identity_indexes are unchanged. Normalized byte comparisons with HEAD confirmed server.py, scripts/apply_identity_indexes.py and both dependency manifests unchanged. The only runtime call site passing m002_identity_indexes for provisioning is the dedicated CLI; remaining direct invocations are explicit isolated test setup/preservation checks. No source/runtime index-definition changes.

## Preserved safeguards and remaining risks

Dedicated CLI still requires --apply, --confirm-database landvilla_dev, explicit APP_ENV=development, exact selected database, nonempty URI and duplicate preflight. It remains import-safe and sanitizes failures. Missing prerequisites keep identity authentication disabled/failing closed; ordinary seeding no longer manufactures them.

Reference migration 001 retains its pre-existing indexes, including users email/user_id and session indexes; this remediation removes implicit provisioning of migration 002, not existing reference-data behavior. Existing identity markers/indexes are left intact. Operators who previously relied on reference seeding to enable identity must use the explicit approved provisioning process.

Real MongoDB index creation, permissions, partial failure and provider behavior remain unverified. R5 partial-migration operational concerns and R2–R6 remain outside this authorization. Directly importing and manually invoking a low-level migration function from custom operator code is not a supported CLI path; this change prevents implicit dispatch, not arbitrary Python execution.

## Stop state

No commit, push, PR amendment, merge or GitHub metadata operation. No source outside this backend worktree was touched. No original checkout, mobile/web worktree, shared/root file, dependency, environment file, Atlas, R2, SMTP, Google, Razorpay or production service was modified or accessed. No application server was started. All changes remain local and unstaged for review.