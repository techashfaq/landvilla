# Verification matrix — master execution

Historical master campaign:12 November2026. Latest image-remediation evidence is in the13November section below. PASS means executed within the stated scope; FAIL means executed unsuccessfully; BLOCKED means unavailable access/configuration/approval; NOT TESTED means not executed. Local evidence directory: `.cache/master-readiness/`. Each verifier command writes its exact arguments, cwd, exit code, elapsed time and log there. No live backend test suite targeting real services was run.

| Check / command | Environment | Expected | Actual/status | Evidence |
|---|---|---|---|---|
| Git branch/HEAD/status/diff check | Windows repository | Preserve dev and inherited changes | PASS starting22modified/26untracked/0staged; expectedHEAD | Master report starting inventory |
| `python -m pip check` | Existing isolated Python3.12.10 verification environment | Compatible closure | PASS no broken requirements | pip-check.log / command.json |
| `python -m unittest discover -s tests/unit -v` | Windows Python3.12.10, dotenv disabled, in-memory fixtures | All backend tests | PASS211 tests,0failures/errors | backend-tests.log / command.json |
| `node --test tests/*.test.ts` | Node24, environment allowlist | All Web tests | PASS117 tests,0failed/0skipped | web-tests.log / command.json |
| ESLint `--max-warnings 0` | Same Web install | Zero errors/warnings | PASS final local run | web-lint.log / command.json |
| TypeScript `--noEmit --incremental false` | Same Web install | No errors | PASS final local run | web-types.log / command.json |
| `node scripts/verify-production-build.mjs` | Environment-free isolated source copy | Complete standalone artifacts | PASS complete standalone artifact | web-build.log / command.json |
| `unittest discover -s tests -p test_*.py -v` | Python + Compose5.7.1/Caddy2.11.9, synthetic loopback | All deployment/fixture tests | PASS45:23production Compose,5Caddy,10rehearsal/host inventory,1real TLS,1fixture TLS reuse,2SDK/storage,1artifact identity,2input inventory | deployment-tests.log / command.json |
| Caddy production native forwarding/health tests | Synthetic HTTP; TLS/SNI disabled in harness | Sanitize/replace custom claims, preserve browser context, health withdrawal/recovery | PASS included above | test_caddy_configuration.py |
| Rehearsal Caddy adapt | Caddy2.11.9 native | Internal issuer, no ACME/production domain | PASS included above | test_rehearsal_deployment.py |
| Python compilation | Existing isolated interpreter | All source compiles | PASS | python-compilation.log / command.json |
| `python scripts/audit-production-dependencies.py` | Public registry metadata, no credentials/proxy | No active entries/yanked pins | PASS dated observation:36Python/55Web names,0entries/0yanked | dependency-advisories.json |
| Base-image manifest digest verification | Docker Hub public manifests, no image pull/start | SHA256 body equals digest header | PASS5 registry manifest observations | image-manifests.json; deploy/reviewed-base-images.json |
| Local Linux Docker availability | Explicit Docker Desktop Linux named pipe | Reach daemon | BLOCKED pipe absent | Tool result; master report |
| EC2 inspection | Operator manual Instance Connect | Host metadata, no mutations | PASS scoped operator report; inputs/routes incomplete | PRODUCTION_ENVIRONMENT_INVENTORY.md |
| Linux API/Web image builds | GitHub Ubuntu24.04, commit6c9e98b | Exact source Linux images | PASS both built; no publication | Run43231926515 result.json |
| Complete Linux rehearsal | GitHub isolated runner, ad1acd4 | TLS/auth/media/recovery/cleanup | PASS runtime step; historical failures below retained | Run43245360600 |
| API observed sourceIP / negative peer | GitHub Linux rehearsal | Exact Web TCP peer; untrusted HTTPS claim denied | PASS ephemeral runner only; EC2 NOT TESTED | Run43231926515 result.json |
| UID/caps/read-only/resources/private ports | GitHub Linux rehearsal | Runtime declaration effectiveness | PASS inspected; load/EC2 NOT TESTED | Run43231926515 result.json |
| Dependency/restart recovery | GitHub Linux rehearsal | Recovery and TLS application acceptance | PASS storage failure/recovery and repeated synthetic auth/media smoke after API/Web restart | Run43245360600 runtime step |
| Whole-image vulnerability scan | Checksum-pinned Grype0.121.3, existing CI images | Dated package/OS scan with no unresolved high/critical matches | FAIL:122High/4Critical package-advisory matches across five images; no suppression | Run43245360600 image-security.json; PRODUCTION_IMAGE_SECURITY_REVIEW.md |
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

Final completed local suites: **373 passing tests =211 backend +117 Web +45 deployment/fixture**. No tests skipped in these recorded runs. Lint, TypeScript, standalone build, pip check, Python compilation and diff whitespace checks passed. The Python environment was reused from the earlier isolated verification; it is not described as a fresh install.

- `pip-check`: exit0, 1.406s; `.cache/master-readiness/pip-check-command.json`.
- `backend-tests`: exit0, 39.469s; `.cache/master-readiness/backend-tests-command.json`.
- `web-tests`: exit0, 2.532s; `.cache/master-readiness/web-tests-command.json`.
- `web-lint`: exit0, 11.312s; `.cache/master-readiness/web-lint-command.json`.
- `web-types`: exit0, 4.688s; `.cache/master-readiness/web-types-command.json`.
- `web-build`: exit0, 60.157s; `.cache/master-readiness/web-build-command.json`.
- `deployment-tests`: exit0, 15.11s; `.cache/master-readiness/deployment-tests-command.json`.
- `python-compilation`: exit0, 2.797s; `.cache/master-readiness/python-compilation-command.json`.

DNS read-only observation: apex A records3.33.130.190 and15.197.148.33; www CNAME resolves to the same apex addresses. These differ from owner-supplied EC2 EIP3.111.250.146. Production DNS/TLS release gate is BLOCKED pending separately approved correction and verification. No DNS changes made.

## GitHub runtime execution history

- [Run43227010070](https://github.com/techashfaq/landvilla/actions/runs/43227010070), commit `cb57daaebc81e9e94f18149c31b5afb178916485`: fresh Linux backend/Web job passed; rehearsal failed before building because built-in Docker networks return null IPAM.Config. Corrected with a regression test.
- [Run43231926515](https://github.com/techashfaq/landvilla/actions/runs/43231926515), commit `6c9e98b5634dc6d67affd8f33ad374ea7cd7fa42`: fresh Linux backend/Web job passed; both images built, startup/readiness/source-IP/spoof rejection/runtime declarations passed. Complete rehearsal FAILED at docker cp public CA extraction. Cleanup removed only disposable runner resources. Downloaded evidence: `.cache/master-readiness/ci-43231926515/result.json`.
- Image content IDs for that failed campaign: API `sha256:7214410a92021b08177f604145b599dd713ff9eb076df60bde6c006c99c46722`; Web `sha256:f5612fae857106b516dd57c8630d3a0174f01532b551670a8d1070218bc2c615`. These are local Docker image IDs, not published registry digests or production releases.
- Public CA extraction correction uses the exact public file inside the container mount namespace. The documented [Caddy data path](https://caddyserver.com/docs/conventions) is retained. No private CA key is exported, TLS verification remains enabled and host trust stores are unchanged.

A whitespace-only inherited report EOF issue was detected during staged review and corrected in6c9e98b; no substantive inherited work was discarded. Current git diff --check passes.

- [Run43233624597](https://github.com/techashfaq/landvilla/actions/runs/43233624597), commit `528e1c561e46df9bcdb2b66e29e379d172ae5288`: public CA extraction succeeded; first host HTTPS request failed. No TLS bypass was introduced.
- [Run43234773167](https://github.com/techashfaq/landvilla/actions/runs/43234773167), commit `956597b616b54f9baf3d9ff4b56452d97455dcae`: precise failure was curl exit7, connection refused to localhost8443. The native Caddy TLS regression independently passes chain verification, strict SNI and hidden probes. Docker did not publish the internal-only bridge port effectively. A separate Caddy-only ingress bridge is now prepared; application dependencies remain internal and production Compose is unchanged. No runtime success is inferred before rerun.
- Runner evidence records Engine28.0.4/Compose2.38.2, Linux amd64, API195,947,445 bytes and Web270,032,630 bytes for956597b. These measurements do not certify target EC2 capacity/version compatibility. Whole-image OS scanning remains NOT TESTED.

- [Run43236173733](https://github.com/techashfaq/landvilla/actions/runs/43236173733), commit `c0035841b7cfb15978f900d1b5567c52280a783f`: loopback TLS, public paths, synthetic registration/CSRF/admin denial/private media reached logout, which returned502. Root cause reproduced locally: Starlette quoted-empty cookie deletion was rejected by the Web validator. Fixed with strict deletion-specific acceptance and two regression tests; no cookie/CSRF control removed.
- [Run43245360600](https://github.com/techashfaq/landvilla/actions/runs/43245360600), commit `ad1acd44cf1a185ecaadcd852d80c3d37af2a9a0`: backend/Web job PASS; complete Linux runtime campaign PASS with10 recorded check groups, including postrestart login/media and cleanup. Separate image security scan FAIL with122High/4Critical package-advisory matches. Overall workflow FAIL is intentional and not waived. Scanner archive digest matched authoritative GitHub release asset metadata; no unpinned install action or production credentials were used.
- Verified runtime image IDs: API `sha256:5ccac299e68192cc1de369736ca97982b0fea66ac74b7b039d5bb725ab5c4ab4`; Web `sha256:9c1ca56631d3a708c311dca35752101f6cd29fdb8c30b8737342c9a65af5425a`. Linux amd64 sizes195,947,445 and270,032,676 bytes. These are disposable local image IDs, not published release digests. No deployment SHA exists. Subsequent documentation-only commits trigger the same gates and require their own run identity; the final handover names that run explicitly.

## Image remediation verification — 13 November 2026

Starting source: d5bf8093cf45e27d7faa5b932e43096c9f484dcf, clean dev. The earlier122High/4Critical results above are historical baseline evidence, not candidate results.

| Check | Environment | Result / evidence |
|---|---|---|
| Backend unit suite and pip check | Existing isolated Python3.12.10, no production configuration | PASS211 tests; pip check PASS |
| Web suite, lint and TypeScript | Existing Node24, sanitized environment | PASS117 tests; lint and types PASS |
| Standalone production build | Environment-free local source copy | PASS96.422 seconds; complete standalone assets |
| Dependency advisory metadata | Public PyPI/npm registries | PASS dated observation36Python/55Web runtime names,0active entries,0yanked; excludes OS/embedded tooling |
| Deployment/evidence tests | Native Compose5.7.1/Caddy2.11.9 and mock evidence | PASS52 tests (46 deployment/fixture +6 new scanner integrity); 380 total with backend/Web |
| Python compilation | Existing isolated Python3.12.10 | PASS3.36 seconds (final changed scripts) |
| Candidate Linux builds and complete runtime | GitHub Linux amd64, `c52e8f21f882abb2e21b013394b2bc9869956bfc` | PASS four builds + pinned Mail image;11 runtime check groups; [run43288981277](https://github.com/techashfaq/landvilla/actions/runs/43288981277) |
| Full Syft SBOM / Grype scan | Same exact five runtime images | FAIL505matches:120High/0Critical; API59/Web58/Caddy3; Mongo/Mail0High/0Critical |
| Evidence integrity | Downloaded immutable CI artifact | PASS15 file SHA256 checks; complete package/layer provenance retained |
| Production Compose/Caddy settings | Git diff against starting commit | Unchanged |

CI adds full SBOM and full Grype reports for all five runtime images, exact image IDs and layers, package locations/ranges/vendor fixes, source binding and evidence checksums. Artifact retention is90days. High/Critical gate remains unsuppressed, even for vendor-unfixed matches.

CI attempt history for this campaign: run43286352072 failed before image builds because a new test did not create its scratch directory; corrected without changing assertions. Run43286555636 built API/Web/Caddy but failed Mongo's curl-based download; replaced with checksum-verified Docker ADD. Run43287374286 completed runtime and full scan (160High/3Critical), exposing pre-existing Mongo tools and an incorrect YAML destination; finalrun43288981277 corrects the actual entrypoint path and removes unused tools. No failed attempt was hidden or treated as acceptance.

Final source `c52e8f21f882abb2e21b013394b2bc9869956bfc`, artifactID13974974795. CI test totals:211 backend,117Web,6scanner integrity; lint/type/build/pip check PASS. Local380 total includes52deployment/evidence tests. Exact images and all15 checksums are in PRODUCTION_IMAGE_SECURITY_REVIEW.md. Reports added after this source commit do not alter tested application/build code; no production release artifact is published.

## Residual campaign preparation — historical local evidence

Starting sourcea4736dfa875d5b5bbfbeb9049da786950caee299; baseline120High/0Critical. Local backend211/Web117 tests and lint/types passed. Deployment54 tests PASS, including two new manifest integrity cases; total382 local tests. Standalone production build PASS88.359s, compilation PASS5.375s, pip check PASS. New Linux campaign must run the backend suite on musl, upstream Caddy configuration/HTTP/TLS tests, all LANDVILLA deployment tests against the custom binary, native C-extension/CA/DNS/Sharp probes, complete TLS/auth/media/recovery rehearsal and unsuppressed scans. No old pass is transferred to these new images.

## Final residual candidate — 13 November 2026

**REHEARSAL PASSED — PRODUCTION RELEASE BLOCKED. Image security acceptance: FAIL.** Exact tested source `197f5098720cd7c3adcbaec8590d94cc9164e65b`, [CI43375237826](https://github.com/techashfaq/landvilla/actions/runs/43375237826). Four Linux images built; the pinned Mail fixture was pulled and tested. All13 runtime check groups passed. The unsuppressed scan reports **172 total matches:15 High /0 Critical**: API4, Web11, Caddy0, Mongo0, Mail0 High. No finding was suppressed or waived.

Compared with the120-High starting scan,108 original package/advisory matches are no longer reported and12 carry forward (including3 renamed SQLite matches). Three new matches remain: SQLite CLI advisory119586 and2 libgomp1 matches. Net reduction is105 High matches (87.5%). The intermediate candidate had24 High; the supported Alpine krb5-libs1.22.3-r0 update removed all9 Kerberos matches. Counts are package/advisory matches, not proven exploits or unique CVEs.

Verified application/deployment tests: **383 distinct tests** (211 backend +117 Web +55 deployment/evidence); CI also reran the211 backend tests inside Alpine with network disabled. Caddy upstream configuration/HTTP/TLS tests passed in18 packages in each of two contexts (36 package executions; individual Go test-case count was not recorded). The second context is the retained xcaddy build module with matching build tags, unchanged go.mod before/after preparation and readonly tests. Lint, TypeScript, production build, pip check and Python compilation passed. No existing test was skipped or weakened.

| Check/command | Environment | Expected | Actual | Status | Evidence |
|---|---|---|---|---|---|
| unittest backend discovery | GitHub Python3.12/glibc |211 pass|211 pass|PASS|offline.log|
| Backend image build regression | Alpine3.24/Python3.12.16; test network disabled |211 pass/native extensions|211 pass; PyMongo/BSON C extensions present|PASS|linux.log|
| npm test/lint/typecheck/build | Node24 GitHub and local |117 pass/no warnings/type errors/build complete|117 pass,0skipped; all checks passed|PASS|offline.log/local logs|
| unittest deployment discovery | GitHub, exact custom Caddy binary |55 pass|55 pass4.030s|PASS|linux.log|
| Caddy go test both module contexts | Official pinned builder Go1.27.4 |HTTP/TLS/config tests and graph consistency|18 package results per context,36 executions; checksums unchanged|PASS|linux.log/Caddy build-info|
| verify-image-inputs.py | GitHub/public registries |7 exact manifests|7 hashes/amd64 targets verified|PASS|base-manifests.json|
| rehearse-linux-ci.py | Disposable Linux amd64 |All13 groups|13 passed; TLS/auth/media/outage/restart/cleanup|PASS|result.json|
| scan-rehearsal-images.py | Exact same5 runtime images |0High/Critical|15High/0Critical,172 total|FAIL|image-security.json +15 raw reports|
| Evidence integrity | Local downloaded artifact |15 checksums/source/image consistency|15 matched|PASS|PRODUCTION_IMAGE_SECURITY_REVIEW.md|
| Python compilation/pip check | Existing local isolated environment and CI |No errors|Passed|PASS|local logs/offline.log|
| Production settings preservation | Git diff vs a4736dfa |No settings/isolation-plan change|No differences|PASS|Git history|
| EC2/runtime/provider/public HTTPS/previous-release rollback |Production|Approved measured acceptance|Not executed; prohibited/unavailable|BLOCKED|PRODUCTION_EXTERNAL_BLOCKERS.md|

Earlier382/380/344 counts above are historical. Current distinct local/CI suite coverage is383, with repeated musl/backend and upstream Go package executions reported separately. The9 scanner/manifest tests in the offline job are included in the55 deployment total, not counted twice. No scanner exclusions, ignore-unfixed, risk waiver or production credentials were used.
