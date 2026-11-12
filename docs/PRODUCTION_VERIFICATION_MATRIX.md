# Verification matrix — master execution

Date:12 November2026. PASS means executed within the stated scope; FAIL means executed unsuccessfully; BLOCKED means unavailable access/configuration/approval; NOT TESTED means not executed. Local evidence directory: `.cache/master-readiness/`. Each verifier command writes its exact arguments, cwd, exit code, elapsed time and log there. No live backend test suite targeting real services was run.

| Check / command | Environment | Expected | Actual/status | Evidence |
|---|---|---|---|---|
| Git branch/HEAD/status/diff check | Windows repository | Preserve dev and inherited changes | PASS starting22modified/26untracked/0staged; expectedHEAD | Master report starting inventory |
| `python -m pip check` | Existing isolated Python3.12.10 verification environment | Compatible closure | PASS no broken requirements | pip-check.log / command.json |
| `python -m unittest discover -s tests/unit -v` | Windows Python3.12.10, dotenv disabled, in-memory fixtures | All backend tests | PASS211 tests,0failures/errors | backend-tests.log / command.json |
| `node --test tests/*.test.ts` | Node24, environment allowlist | All Web tests | PASS115 tests,0failed/0skipped | web-tests.log / command.json |
| ESLint `--max-warnings 0` | Same Web install | Zero errors/warnings | PASS final local run | web-lint.log / command.json |
| TypeScript `--noEmit --incremental false` | Same Web install | No errors | PASS final local run | web-types.log / command.json |
| `node scripts/verify-production-build.mjs` | Environment-free isolated source copy | Complete standalone artifacts | PASS complete standalone artifact | web-build.log / command.json |
| `unittest discover -s tests -p test_*.py -v` | Python + Compose5.7.1/Caddy2.11.9, synthetic loopback | All deployment/fixture tests | PASS37:23production Compose,5Caddy,7rehearsal,2SDK/storage fixture | deployment-tests.log / command.json |
| Caddy production native forwarding/health tests | Synthetic HTTP; TLS/SNI disabled in harness | Sanitize/replace custom claims, preserve browser context, health withdrawal/recovery | PASS included above | test_caddy_configuration.py |
| Rehearsal Caddy adapt | Caddy2.11.9 native | Internal issuer, no ACME/production domain | PASS included above | test_rehearsal_deployment.py |
| Python compilation | Existing isolated interpreter | All source compiles | PASS | python-compilation.log / command.json |
| `python scripts/audit-production-dependencies.py` | Public registry metadata, no credentials/proxy | No active entries/yanked pins | PASS dated observation:36Python/55Web names,0entries/0yanked | dependency-advisories.json |
| Base-image manifest digest verification | Docker Hub public manifests, no image pull/start | SHA256 body equals digest header | PASS5 registry manifest observations | image-manifests.json; deploy/reviewed-base-images.json |
| Local Linux Docker availability | Explicit Docker Desktop Linux named pipe | Reach daemon | BLOCKED pipe absent | Tool result; master report |
| EC2 inspection | Existing console/strict batchSSH | Read-only host identity/capacity/resources | BLOCKED browser URL verification; SSH timeout | Master report; inspect-rehearsal-host.sh ready |
| Linux image build/runtime | Prepared isolated GitHub workflow | Exact commit images start and pass smoke | NOT TESTED until workflow execution | .github/workflows/readiness.yml |
| API observed sourceIP / negative peer | Linux rehearsal | Exact Web TCP peer; untrusted HTTPS claim denied | NOT TESTED runtime | rehearse-linux-ci.py prepared; EC2 repeat required |
| UID/caps/read-only/resources/shutdown/recovery | Linux rehearsal | Actual runtime limits/permissions | NOT TESTED runtime | CI/runbook prepared |
| Directional isolation, host bypass, IPv6, reboot | Actual host | Allowed/denied path matrix | BLOCKED topology/access/separate policy approval | Existing isolation plan unchanged |
| Atlas identity/roles/transactions/backup restore | Production plus authorized isolated recovery target | Scoped readWrite landvilla_prod, verified recovery | BLOCKED external evidence | External blockers/runbook |
| R2 private policy/permissions/object recovery | Production policy + authorized nonproduction objects | Correct private bucket, scoped rights/recovery | BLOCKED external evidence | HeadBucket/mock does not prove these |
| DNS/TLS/public/browser/mobile acceptance | Actual public deployment | Real endpoint and authorized flows | NOT TESTED; no deployment | No internal success substituted |
| Previous-release rollback | Known-good compatible artifact | Verified recovery | BLOCKED no established target | Rollback runbook |

Initial master verification failures were corrected, not skipped: promoted compatibility probes leaked environment across tests; corrected fixture scoping. Refund UI removal left an unused variable; removed it. New test record typing was corrected. Mutable-base Dockerfile assertion was strengthened to require a digest after base pinning. Final executed totals/commit/CI outcome are recorded in the completion section below; do not treat pending rows as PASS.

## Exact local verification invocation

```powershell
$p='F:/projects/landvilla/.cache/dependency-independent-verification/run-20261112-01/venv/Scripts/python.exe'
$compose='F:/projects/landvilla/.cache/phase2-security-review/compose/docker-compose.exe'
$caddy='F:/projects/landvilla/.cache/caddy-validation/caddy.exe'
# Run separately for backend, web, deploy, syntax and build.
& $p scripts/verify-readiness.py --python $p --compose $compose --caddy $caddy --stage backend
& $p scripts/audit-production-dependencies.py
git diff --check
```

On another machine install the reviewed requirements-test.txt into a fresh isolated Python3.12 environment and Web lockfile with Node24; obtain verified validators. Do not reuse historical requirements.txt or infer a clean install from this reused isolated environment. No tests were disabled to improve counts. Extra compatibility probes now live in the normal backend suite.

## Final local completion evidence

Final completed local suites: **363 passing tests =211 backend +115 Web +37 deployment/fixture**. No tests skipped in these recorded runs. Lint, TypeScript, standalone build, pip check, Python compilation and diff whitespace checks passed. The Python environment was reused from the earlier isolated verification; it is not described as a fresh install.

- `pip-check`: exit0, 5.422s; `.cache/master-readiness/pip-check-command.json`.
- `backend-tests`: exit0, 59.453s; `.cache/master-readiness/backend-tests-command.json`.
- `web-tests`: exit0, 2.078s; `.cache/master-readiness/web-tests-command.json`.
- `web-lint`: exit0, 8.781s; `.cache/master-readiness/web-lint-command.json`.
- `web-types`: exit0, 4.0s; `.cache/master-readiness/web-types-command.json`.
- `web-build`: exit0, 62.062s; `.cache/master-readiness/web-build-command.json`.
- `deployment-tests`: exit0, 11.312s; `.cache/master-readiness/deployment-tests-command.json`.
- `python-compilation`: exit0, 6.828s; `.cache/master-readiness/python-compilation-command.json`.

DNS read-only observation: apex A records3.33.130.190 and15.197.148.33; www CNAME resolves to the same apex addresses. These differ from owner-supplied EC2 EIP3.111.250.146. Production DNS/TLS release gate is BLOCKED pending separately approved correction and verification. No DNS changes made.
