# Image security remediation — BLOCKED

Current result,13November2026: **15 High /0 Critical; runtime PASS; security acceptance FAIL** at source `197f5098720cd7c3adcbaec8590d94cc9164e65b`, CI43375237826. See the final residual candidate section at the end for current evidence. Earlier sections preserve the historical122/4 and120/0 campaigns and are not current acceptance. No deployment is authorized.

## Baseline evidence and its limits

[Run 43247372938](https://github.com/techashfaq/landvilla/actions/runs/43247372938), exact source `d5bf8093cf45e27d7faa5b932e43096c9f484dcf`, passed the disposable Linux runtime step and failed the separate image-security gate. Its downloaded evidence is `.cache/master-readiness/ci-43247372938/result.json` and `image-security.json`; artifact name `disposable-runtime-evidence-d5bf8093cf45e27d7faa5b932e43096c9f484dcf`, artifact ID `13956778909`. Earlier run 43245360600 at `ad1acd44cf1a185ecaadcd852d80c3d37af2a9a0` reported the same counts; it is historical corroboration, not the new candidate.

The baseline scanner was Grype 0.121.3, verified release archive SHA256 `e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85`. No ignore file, severity downgrade, `ignore-unfixed`, or package exclusion was used. Counts are package/advisory matches, not unique CVEs or demonstrated exploits.

| Baseline image | Total matches | High | Critical | Unique High/Critical IDs within image |
|---|---:|---:|---:|---:|
| Production API candidate | 217 | 61 | 0 | 19 |
| Production Web candidate | 232 | 55 | 2 | 25 |
| Production Caddy concern | 11 | 3 | 1 | 4 |
| Rehearsal-only Mongo fixture | 96 | 3 | 0 | 3 |
| Rehearsal-only Mail fixture | 5 | 0 | 1 | 1 |
| Total | 561 | 122 | 4 | Not additive across images |

The baseline summary retains every matched ID, installed version, package type, catalog location, fix metadata and advisory URL. **It does not retain the original full SBOM, full Grype JSON, or complete layer attribution. Those missing historical artifacts have not been recovered.** Registry layer inspection corroborates selected upstream package provenance, but cannot substitute for a full SBOM of the exact deleted runner image. The remediation workflow now archives full candidate SBOMs, full unsuppressed Grype reports, image IDs, rootfs layers, source revision, package locations, match details and report hashes. Historical artifacts had 14-day retention; preserve evidence before expiry. Updated candidate workflow requests 90-day retention.

API/Web/Caddy are production artifact concerns. Mongo/Mail are disposable fixtures and do not describe Atlas or a production mail service. The 36-Python/55-npm application feed observation did not cover these OS, tooling and embedded-binary findings.

## Implemented candidate changes and verification scope

| Artifact | Reviewed change | Provenance / exact input |
|---|---|---|
| API | Retain Python 3.12 and Debian Trixie; install signed vendor `zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1` | Parent `python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`. Fixed package exists in Trixie security repository; no core-library transplant. |
| Web | Move all three stages together to official Node 24 Trixie Slim; install the same Trixie zlib fix in runtime; remove unused npm/npx and Yarn runtime tooling | Parent `node:24-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0`. Official image metadata lists Node 24.22.3. Build stages retain npm; standalone runtime still invokes `node server.js`. |
| Caddy | Candidate wrapper installs signed Alpine 3.24 `zlib=1.4-r0`; upstream Caddy binary is unchanged | Parent `caddy:2.11.9-alpine@sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee`; Dockerfile `deploy/images/caddy/Dockerfile`. Current parent is Alpine 3.24.4 and its own branch repository contains this fix. No Go module replacements. |
| Mongo fixture | Corrected same-major js-yaml 3.15.2 entrypoint bundle; remove unused database tools/metapackages and gosu from this nonroot fixture | Parent `mongo:8.0@sha256:d97fea17ccb8d004cd137be8dab54d70d0df11be69c9f422aefe4484c8414ab7`; Dockerfile `deploy/images/mongo/Dockerfile`. npm tarball SHA256 `7f005cf0b8ee639b4557e0e321dc067c1f2aa0a442d096e03f2ab53353738794`, verified against registry SHA512 integrity. Server and mongosh remain installed and are explicitly retained; corrected entrypoint path and tool removal await the corrective run below. |
| Mail fixture | Upgrade official Mailpit from v1.33.0 to v1.33.1 | `axllent/mailpit:v1.33.1@sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce`. Registry filesystem inspection finds zlib 1.4-r0 in layer `sha256:9c6a15861a91c5c783ea0bf2f785f597ed230ba18361b2dbed693d6cda6ae453`; the intermediate run below verified SMTP/TLS runtime and found zero High/Critical Mail matches. The corrective candidate requires its exact-source repeat. |

Registry manifest bytes matched Docker-Content-Digest for updated inputs. This proves input identity, not successful image build or runtime compatibility. Node's amd64 manifest is `sha256:60587baa7c895cf438d44f691e4ac8248b36c13b26be77332f874bebb3a64201`; Mailpit's is `sha256:c95e8356f55b65520e8b7fd4d74d3e2d06e4a83513f639e316b1e592fbd52646`. [Official Node metadata](https://raw.githubusercontent.com/docker-library/official-images/master/library/node), [Mailpit release](https://github.com/axllent/mailpit/releases/tag/v1.33.1).

**Production `deploy/compose.production.yml` and `deploy/Caddyfile` remain unchanged.** The derived Caddy image is selected only by the disposable CI candidate path; production settings do not automatically select it. A later approved production artifact-selection change remains necessary. No EC2, environment, cloud, DNS, database or storage changes are part of this remediation.

## Complete High/Critical advisory review

The following groups enumerate every unique High/Critical ID present in the baseline. Debian findings are matched from `/var/lib/dpkg/status` and corresponding `/var/lib/dpkg/info/<package>.*` / `/usr/share/doc/<package>/copyright` entries. These are package catalog locations, not necessarily vulnerable function locations. The baseline JSON retains each binary package/version instance. Debian source-package matching can associate one advisory with multiple binary packages; neither that duplication nor `no-dsa`, `wont-fix`, or `postponed` establishes a false positive.

### Production API and Web: Debian packages

| Package group / baseline installed versions | All relevant IDs | Vendor fix / remaining exposure and decision |
|---|---|---|
| zlib1g: API `1:1.3.dfsg+really1.3.1-1+b1`; Web `1:1.2.13.dfsg-1` | [CVE-2026-76844](https://security-tracker.debian.org/tracker/CVE-2026-76844), [CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091) | Trixie security `1:1.3.dfsg+really1.3.1-1+deb13u1` fixes both. Candidate installs it using signed apt repositories. Underlying flaw concerns failed gz writes and stale buffer state. |
| Web libc6/libc-bin `2.36-9+deb12u14` | [CVE-2026-5450](https://security-tracker.debian.org/tracker/CVE-2026-5450), [CVE-2026-5928](https://security-tracker.debian.org/tracker/CVE-2026-5928) | Trixie `2.41-12+deb13u4` is fixed. Supported Node distribution update addresses these; actual installed candidate version/scan must confirm. Affects formatted input and wide-character pushback paths. |
| Web libtasn1-6 `4.19.0-2+deb12u1` | [CVE-2025-13151](https://security-tracker.debian.org/tracker/CVE-2025-13151) | Trixie `4.20.0-2+deb13u1` fixed; confirm candidate package closure. |
| Web gzip `1.12-1` | [CVE-2026-41992](https://security-tracker.debian.org/tracker/CVE-2026-41992) | Trixie `1.13-1+deb13u1` fixed. Crafted mixed-format CLI decompression; package remains subject to scan. |
| Web util-linux source group `2.38.1-5+deb12u3` | [CVE-2026-53615](https://security-tracker.debian.org/tracker/CVE-2026-53615), [CVE-2026-53613](https://security-tracker.debian.org/tracker/CVE-2026-53613) | Trixie `2.41.5-0+deb13u1` fixed for these two only. Partition parsing/local mount race prerequisites; other util-linux findings below remain. |
| perl-base: API `5.40.1-6+deb13u1`; Web `5.36.0-7+deb12u4` | [CVE-2026-82560](https://security-tracker.debian.org/tracker/CVE-2026-82560), [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | No supported Trixie package fix observed. Affected components are Pod::Text before 6.1.1 and Archive::Tar before 3.10; the latter stable fix is postponed pending upstream regression resolution. Actual component presence/reachability is not established by the perl-base match. Retain blocker pending supported vendor update or independently evidenced applicability determination. |
| ncurses: API `6.5+20250216-2`; Web `6.4-4` | [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | Trixie remains vulnerable/no-dsa. Upstream fixes after `6.5-20251213`; Debian unstable `6.6+20251231-1` is fixed. Flaw is in infocmp CLI string analysis; library-package matches need actual code provenance. Do not import unstable packages. |
| gcc base/libgcc/libstdc++: API `14.2.0-19`; Web `12.2.0-14+deb12u1` | [CVE-2026-95619](https://security-tracker.debian.org/tracker/CVE-2026-95619), [CVE-2026-102010](https://security-tracker.debian.org/tracker/CVE-2026-102010) | Trixie GCC14 remains vulnerable/no-dsa; unstable GCC14 `14.4.0-3` fixed. Aligned allocation overflow and priority-queue erase UAF require actual affected native code paths. No supported stable fix proven. |
| libc6/libc-bin: API `2.41-12+deb13u4`; Web `2.36-9+deb12u14` | [CVE-2026-19499](https://security-tracker.debian.org/tracker/CVE-2026-19499), [CVE-2026-84243](https://security-tracker.debian.org/tracker/CVE-2026-84243), [CVE-2026-5435](https://security-tracker.debian.org/tracker/CVE-2026-5435) | Trixie remains vulnerable/no-dsa. Concerns strfmon width, attacker-controlled LANGUAGE/catalog loading, and deprecated DNS debug printers. First/third fixed only in unstable `2.43-5` / `2.43-3`; LANGUAGE issue remains unfixed there. No stable core-library replacement is approved. |
| API libsqlite3-0 `3.46.1-7+deb13u2` | [CVE-2026-119379](https://security-tracker.debian.org/tracker/CVE-2026-119379), [CVE-2026-119374](https://security-tracker.debian.org/tracker/CVE-2026-119374), [CVE-2026-119373](https://security-tracker.debian.org/tracker/CVE-2026-119373) | Trixie vulnerable/no-dsa; upstream 3.54.0 / unstable Debian `3.54.1-1` fixed. Crafted changesets/FTS5 operations; application uses MongoDB, but absence of direct SQLite calls does not establish absence of affected binary code. No stable patch established. |
| util-linux source group: API `2.41.5-0+deb13u1`; Web `2.38.1-5+deb12u3` | [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408), [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642), [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410), [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | Trixie vulnerable/no-dsa; fixes in unstable `2.42.4-1` or `2.42.3-1`. Root nsenter inheritance, mount hooks/source races/traversal. Nonroot, dropped capabilities and read-only filesystem limit prerequisites but do not fix packages. Trixie can newly match three IDs absent from Bookworm; evaluate complete fresh counts, not only disappearing baseline matches. |
| libacl1: API `2.3.2-2+b1`; Web `2.3.1-3` | [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369), [CVE-2026-54370](https://security-tracker.debian.org/tracker/CVE-2026-54370) | Trixie vulnerable; unstable `2.4.0-1` fixed. Vendor says new ABI/traversal rewrite is not individually backportable. Privileged ACL traversal/race prerequisites reduce apparent runtime exposure but are not a waiver. |

Remaining Debian groups require supported stable fixes or further package-payload/native reachability evidence and a formal security decision. No compatibility claim is made for mixing unstable libraries into Trixie. These candidate changes deliberately do not perform that mix.

### Production Web: embedded npm tooling

All six High findings are proven by baseline locations beneath `/usr/local/lib/node_modules/npm/node_modules/`, not by the application lockfile. Runtime `node server.js` does not invoke npm. Removing unused runtime tooling is a package removal, not a scanner exclusion; npm remains available in build stages. This does not imply removal or upgrade of Node's internal bundled undici, which is a separate component.

| Exact package location / installed version | All IDs | Supported fix version / candidate action |
|---|---|---|
| `/usr/local/lib/node_modules/npm/node_modules/brace-expansion/package.json`, 5.0.9 | [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7), [GHSA-6j4f-fj2g-mc7p](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) | Affected 4.x/5.x line fixes 5.0.11 and 5.0.10 respectively. Candidate removes the unused owning npm installation entirely; no application override. |
| `/usr/local/lib/node_modules/npm/node_modules/undici/package.json`, 6.28.0 | [GHSA-rfgv-xxqx-mfg5](https://github.com/advisories/GHSA-rfgv-xxqx-mfg5), [GHSA-xjj6-f33q-929c](https://github.com/advisories/GHSA-xjj6-f33q-929c), [GHSA-qrxm-fqhp-jwvm](https://github.com/advisories/GHSA-qrxm-fqhp-jwvm), [GHSA-2m5v-pch6-74hx](https://github.com/advisories/GHSA-2m5v-pch6-74hx) | First fixes in 6.28.1, remaining three in 6.29.1. Candidate removes this npm-owned copy; fresh complete SBOM must confirm absence and inventory other copies. |

### Production Caddy: embedded Go modules and Alpine

Caddy stable release metadata still reported [v2.11.9](https://github.com/caddyserver/caddy/releases/tag/v2.11.9). Its [upstream go.mod](https://raw.githubusercontent.com/caddyserver/caddy/v2.11.9/go.mod) retains all three affected modules. They are embedded in `/usr/bin/caddy`, upstream binary layer `sha256:5000c332a1cc372a1a248c2923696c0bc7817d213f2db0f4161fc18a3fc17cd7`, corroborated by registry inspection. The candidate preserves that binary and therefore does not claim these fixed.

| Installed module / package | Advisory and affected range | Fix / exposure / required decision |
|---|---|---|
| `github.com/go-jose/go-jose/v3` v3.0.5 | [GHSA-mgcc-cww5-fp2q](https://github.com/advisories/GHSA-mgcc-cww5-fp2q), v3 <=3.0.5 | No patched v3 release. v4.1.6 fixes the separate v4 line. Proven dependency path: Caddy → smallstep/certificates / go.step.sm/crypto → go-jose/v3. Crafted RSA JWK parsing can consume excessive CPU. No configured ACME-server/JWK endpoint and admin disabled reduce apparent exposure; transitive reachability remains unproven. Require supported Caddy upstream remediation; do not force a major module replacement. |
| `golang.org/x/net` v0.60.0 | [GO-2026-6860](https://pkg.go.dev/vuln/GO-2026-6860), before v0.62.0 | v0.62.0 fixes HTML Parse/ParseFragment resource consumption. No direct Caddy source import of that parser was found; transitive call paths remain unproven. Await supported upstream dependency update. |
| `github.com/klauspost/compress` v1.20.1 | [GO-2026-6865 / GHSA-fpmh-frq8-7rj8](https://github.com/klauspost/compress/security/advisories/GHSA-fpmh-frq8-7rj8), through v1.20.1 | v1.20.2 fixes crafted zstd decompression crashes. Caddy's own zstd module uses encoding and current config has no encoding handler; this does not prove transitive decoding unreachable. Retain blocker until supported upstream correction/evidence. |
| Alpine `zlib` 1.3.2-r1, `/lib/apk/db/installed` | [CVE-2026-4738](https://security.alpinelinux.org/vuln/CVE-2026-4738) | Alpine 3.24 vendor fix 1.4-r0 is installed by candidate wrapper. Vendor description references GDAL contrib/infback9 and has severity differences; no false-positive conclusion is made. Same-branch supported update avoids relying on that ambiguity. |

The current absence of an enabled route is exposure context, not proof of compiled unreachability and not a Grype exemption. All three Go findings remain blockers under the requested zero-unresolved-High/Critical gate.

### Rehearsal-only fixtures

Mongo's `/opt/js-yaml/package.json` reports 3.13.1. [Official Docker image source](https://github.com/docker-library/mongo/tree/master/8.0) vendors `/opt/js-yaml/dist/js-yaml.js`, linked from `/js-yaml.js`, and package metadata for entrypoint YAML configuration parsing; it is not a mongosh bundled package. Rehearsal supplies explicit mongod flags rather than a YAML config, but still updates the vulnerable package.

- [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m): scanner fix 3.15.0.
- [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj): scanner fix 3.15.1.
- [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh): scanner fix 3.15.2.

Candidate selects the supported same-major 3.15.2 distribution bundle after verifying [npm metadata](https://registry.npmjs.org/js-yaml/3.15.2) and tarball integrity. Mailpit's sole Critical baseline finding is the same Alpine zlib CVE-2026-4738 above; v1.33.1 contains the fixed package. The intermediate run verified SMTP/TLS operation, but its YAML patch targeted the wrong bundle path and is not accepted as entrypoint remediation. The corrected Mongo fixture requires fresh full verification, as detailed below. No change concerns production Atlas or production email credentials.

## Intermediate full-SBOM run and corrective Mongo work

[Run 43287374286](https://github.com/techashfaq/landvilla/actions/runs/43287374286), exact commit `1582b818949bc477d6b85ab95d541b78470fb688`, built API, Web, Caddy and Mongo candidates and used the pinned Mailpit image. **All 11 runtime check groups passed**, including verified TLS, synthetic OTP/CSRF/logout/private media, observed proxy peer, hardening, failure/recovery and cleanup. The separate unsuppressed scan failed:

| Intermediate image | Total matches | High | Critical |
|---|---:|---:|---:|
| API | 214 | 59 | 0 |
| Web | 193 | 58 | 0 |
| Caddy | 11 | 3 | 0 |
| Mongo fixture | 176 | 40 | 3 |
| Mail fixture | 5 | 0 | 0 |
| Total | 599 | 160 | 3 |

Artifact `13975751908`, `disposable-runtime-evidence-1582b818949bc477d6b85ab95d541b78470fb688`, contains Syft 1.57.1 SBOMs, Grype 0.121.3 reports and derived provenance for every image. All **15 report SHA256 checksums** were independently checked after download to `.cache/master-readiness/ci-43287374286/`. `image-security.json` binds file hashes, package versions/locations/ranges/fixes, distributions and image IDs; `result.json` binds runtime acceptance to the same commit. Node reported 24.22.3 with internal undici 7.30.2, distinct from the removed npm-owned undici copy; Python reported 3.12.16. No candidate image was published.

The Mongo scan exposed **35 gosu standard-library matches (32 High / 3 Critical)** plus **eight database-tool matches (8 High)**. These components belong to unchanged parent-image layers, not the YAML patch layer. The baseline summary did not report them. Because its full SBOM is unavailable, the precise contribution of cataloger coverage versus feed changes cannot be reconstructed. The additional findings are retained, not treated as an excuse or ignored.

| Owning component | Exact provenance | Advisory/fix evidence |
|---|---|---|
| gosu, compiled with Go 1.24.6 | `/usr/local/bin/gosu`; parent layer `sha256:2fa32752e6dfab6c4618e1fe6bc3485367a5176690865b58f3ec03d5f39a2c58` | 35 standard-library IDs below. No claimed reachability determination. Latest required stable fixed lines among these records are Go 1.26.9 / 1.27.2. |
| `mongodb-database-tools` 100.20.1, embedded x/net 0.61.0 | `/usr/bin/bsondump`, `mongodump`, `mongoexport`, `mongofiles`, `mongoimport`, `mongorestore`, `mongostat`, `mongotop`; parent layer `sha256:4f4ac09261bebb744a876c535b6b37c71c177f994f9adef6e18d1a5c9b6dc686` | Each matches [GO-2026-6860](https://vuln.go.dev/ID/GO-2026-6860.json), affected before 0.62.0, fixed 0.62.0. These are eight binaries, not nine. |

All 36 unique Go advisory JSON records matched in this Mongo image were checked against `vuln.go.dev`; none was withdrawn. Installed Go 1.24.6 falls within their recorded affected ranges. The table lists stable fixed branch endpoints; full introduced/fixed events, including prerelease branches where present, remain in the linked authoritative JSON and retained Grype match details. A package match does not establish that the vulnerable symbol executes in gosu.

| Stable fixed Go branches | Complete gosu advisory IDs |
|---|---|
| 1.24.8 / 1.25.2 | [GO-2025-4006](https://vuln.go.dev/ID/GO-2025-4006.json), [GO-2025-4009](https://vuln.go.dev/ID/GO-2025-4009.json), [GO-2025-4013](https://vuln.go.dev/ID/GO-2025-4013.json) |
| 1.24.9 / 1.25.3 | [GO-2025-4007](https://vuln.go.dev/ID/GO-2025-4007.json) |
| 1.24.11 / 1.25.5 | [GO-2025-4155](https://vuln.go.dev/ID/GO-2025-4155.json) |
| 1.24.12 / 1.25.6 | [GO-2026-4341](https://vuln.go.dev/ID/GO-2026-4341.json) |
| 1.24.13 / 1.25.7 | [GO-2026-4337](https://vuln.go.dev/ID/GO-2026-4337.json) |
| 1.25.8 / 1.26.1 | [GO-2026-4601](https://vuln.go.dev/ID/GO-2026-4601.json) |
| 1.25.9 / 1.26.2 | [GO-2026-4870](https://vuln.go.dev/ID/GO-2026-4870.json), [GO-2026-4946](https://vuln.go.dev/ID/GO-2026-4946.json), [GO-2026-4947](https://vuln.go.dev/ID/GO-2026-4947.json) |
| 1.25.10 / 1.26.3 | [GO-2026-4918](https://vuln.go.dev/ID/GO-2026-4918.json), [GO-2026-4971](https://vuln.go.dev/ID/GO-2026-4971.json), [GO-2026-4977](https://vuln.go.dev/ID/GO-2026-4977.json), [GO-2026-4981](https://vuln.go.dev/ID/GO-2026-4981.json), [GO-2026-4986](https://vuln.go.dev/ID/GO-2026-4986.json) |
| 1.25.11 / 1.26.4 | [GO-2026-5037](https://vuln.go.dev/ID/GO-2026-5037.json), [GO-2026-5038](https://vuln.go.dev/ID/GO-2026-5038.json) |
| 1.25.12 / 1.26.5 | [GO-2026-4970](https://vuln.go.dev/ID/GO-2026-4970.json) |
| 1.25.13 / 1.26.6 | [GO-2026-5026](https://vuln.go.dev/ID/GO-2026-5026.json), [GO-2026-5972](https://vuln.go.dev/ID/GO-2026-5972.json), [GO-2026-6088](https://vuln.go.dev/ID/GO-2026-6088.json), [GO-2026-6089](https://vuln.go.dev/ID/GO-2026-6089.json), [GO-2026-6090](https://vuln.go.dev/ID/GO-2026-6090.json) |
| 1.26.9 / 1.27.2 | [GO-2026-6603](https://vuln.go.dev/ID/GO-2026-6603.json), [GO-2026-6604](https://vuln.go.dev/ID/GO-2026-6604.json), [GO-2026-6605](https://vuln.go.dev/ID/GO-2026-6605.json), [GO-2026-6607](https://vuln.go.dev/ID/GO-2026-6607.json), [GO-2026-6608](https://vuln.go.dev/ID/GO-2026-6608.json), [GO-2026-6609](https://vuln.go.dev/ID/GO-2026-6609.json), [GO-2026-6610](https://vuln.go.dev/ID/GO-2026-6610.json), [GO-2026-6611](https://vuln.go.dev/ID/GO-2026-6611.json), [GO-2026-6612](https://vuln.go.dev/ID/GO-2026-6612.json), [GO-2026-6613](https://vuln.go.dev/ID/GO-2026-6613.json), [GO-2026-6617](https://vuln.go.dev/ID/GO-2026-6617.json) |

Critical gosu matches are GO-2026-4337, GO-2026-6604 and GO-2026-6612. Their raw severities are preserved; no applicability exclusion is introduced.

### YAML path correction and fixture minimization

The first candidate copied js-yaml 3.15.2 to `/opt/js-yaml/js-yaml.js` and updated package metadata, but the upstream entrypoint uses `/js-yaml.js` linked to `/opt/js-yaml/dist/js-yaml.js`. Its runtime probe exercised the newly created wrong path. **The disappearance of js-yaml matches and the 3.15.2 metadata in run 43287374286 therefore do not prove the actual entrypoint helper was patched. That remediation is not accepted from that run.** This was corrected rather than treating metadata as package-content proof.

Corrective commit `c52e8f21f882abb2e21b013394b2bc9869956bfc`, [run 43288981277](https://github.com/techashfaq/landvilla/actions/runs/43288981277), replaces the actual `dist/js-yaml.js` bundle, asserts the expected symlink during build, and exercises `/js-yaml.js` through mongosh at runtime. Its full result is recorded below: runtime PASS, image scan FAIL with zero Mongo High/Critical matches.

The same correction removes unused utilities with `apt-get purge mongodb-database-tools mongodb-org-tools mongodb-org`. The latter two are metapackages; `mongodb-org-server` and `mongodb-mongosh` are explicitly marked manual and required to remain executable. No `autoremove` is used. The standalone gosu binary is removed because this fixture's Dockerfile and Compose both require UID 999; upstream invokes gosu only for root startup. An accidental root invocation fails instead of gaining an alternate startup path. Runtime assertions require all eight database tools and gosu to be absent. [Upstream entrypoint](https://raw.githubusercontent.com/docker-library/mongo/master/8.0/docker-entrypoint.sh), [image source](https://raw.githubusercontent.com/docker-library/mongo/master/8.0/Dockerfile).

This fixture runs a disposable Mongo server and health shell; it is **not a production backup/export/restore-tool image**. No production database tools, backups or restore procedures are modified. These are actual package/binary removals from the runtime filesystem, not scanner exclusions. The final full SBOM, unsuppressed scan and runtime acceptance below confirm zero Mongo High/Critical matches for this corrected fixture.

## Candidate verification and acceptance gate

The intermediate run above records complete executed evidence. The corrective run below repeats it against its exact commit and image IDs, including installed fixed versions/locations/layers, test totals and report hashes. Do not transfer runtime or scanner acceptance between source revisions.

The workflow uses disposable GitHub-hosted Linux runners and synthetic local dependencies only. No production credentials, environment files or external production resources are supplied; images are not published. Nonroot, read-only filesystems, capability restrictions, resources, TLS verification, Host/SNI validation, signed proxy identity, cookies, CSRF and target identity controls remain required. Candidate fixture metadata is bound to the tested source revision and exact Linux amd64 image IDs.

The gate fails on every unresolved High/Critical match, including vendor-unfixed matches and rehearsal fixtures. No ignore configuration, severity override, exclusion or `ignore-unfixed` flag is introduced. Raw findings are retained. A successful runtime rehearsal does not change that gate.

**Final runtime rehearsal PASS; final image security FAIL (120 High / 0 Critical). Production release BLOCKED.** Supported vendor fixes are implemented for review; unresolved Debian and Caddy upstream findings remain explicit blockers. No production readiness or deployment is claimed.

## Final corrective candidate evidence — 13 November 2026

[Run 43288981277](https://github.com/techashfaq/landvilla/actions/runs/43288981277), exact source `c52e8f21f882abb2e21b013394b2bc9869956bfc`: **Linux build/runtime PASS; unsuppressed image-security FAIL; production release BLOCKED.** Overall workflow is red because High findings remain. All four local candidate images built (API, Web, Caddy, Mongo); Mailpit used its verified immutable upstream manifest. All five ran only on a disposable GitHub runner. No image was published.

| Image | Total matches | High | Critical | Cataloged packages |
|---|---:|---:|---:|---:|
| API | 214 | 59 | 0 | 131 |
| WEB | 193 | 58 | 0 | 150 |
| CADDY | 11 | 3 | 0 | 181 |
| MONGO | 82 | 0 | 0 | 126 |
| MAIL | 5 | 0 | 0 | 70 |
| Total | 505 | 120 | 0 | 658 |

Mongo and Mail pass the requested High/Critical threshold; lower-severity findings remain retained. Production candidate images still have API59 + Web58 + Caddy3 High matches. No blanket false-positive assertion or risk acceptance is made. The earlier122High/4Critical baseline and intermediate160High/3Critical counts used different catalog evidence; they are not a simple vulnerability-removal percentage. The new catalog exposed pre-existing Mongo binary packages, and the Trixie transition changes the set of Debian matches.

Exact Linux amd64 local image IDs (not published repository digests):

- API: `sha256:02e5ccff0d9feb59fa7d7500b035ff26ddcd8a25e23fda2416b6d562252ae07b`
- WEB: `sha256:6940c4de6de10776f1f648891d251aaa36fa271ea5c1806b68e8948b74c427b1`
- CADDY: `sha256:6b04c8e26bcfb016f1a22acd8dedae8097b03799dd4a1982fefc61c37b1c525b`
- MONGO: `sha256:ceb75063a31415e8153bad21edd50a9737656905e54cc309e8fa0a7c72c423e8`
- MAIL: `sha256:cfdafb05e489fd0a93f82045a641610317dbaa7ea1da3d7a847cdb82f1001937`

Mail vendor reference remains `axllent/mailpit:v1.33.1@sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce`. Parent manifests, rootfs layers and every package location/range/fix are retained in the full evidence. SBOM layer IDs are uncompressed rootfs diff IDs; earlier registry layer digests are compressed manifest blob identities and are not interchangeable.

The fixed versions are confirmed in the actual SBOMs: API/Web zlib1g `1:1.3.dfsg+really1.3.1-1+deb13u1`; Web libc6/libc-bin `2.41-12+deb13u4`; Caddy/Mail zlib `1.4-r0`; Mongo js-yaml `3.15.2`. Runtime checks use `/js-yaml.js` through its asserted `/opt/js-yaml/dist/js-yaml.js` target and verify all eight removed database tools plus gosu are absent. The checksum-pinned distribution bundle is copied into that actual target. Web runtime checks verify npm/npx/Yarn absence. Node reports24.22.3, bundled undici7.30.2; Python reports3.12.16. Removing npm did not replace Node's separately bundled undici.

Representative payload provenance from the final full SBOM:

| Payload | Installed package / layer ID |
|---|---|
| API `/usr/lib/x86_64-linux-gnu/libz.so.1.3.1` | patched zlib1g; `sha256:d2aec482183f9de7398488396bb9e6a8eb16ed29c7ade3995e5eae991879913e` |
| Web `/usr/lib/x86_64-linux-gnu/libz.so.1.3.1` | patched zlib1g; `sha256:68fec40f2efd25574ad0f8039645f0c80a993f38c3f4c01f552d578a95792c8f` |
| API/Web `/usr/lib/x86_64-linux-gnu/libc.so.6` | Trixie libc6; `sha256:dd57f90311a2567b55ff22eeacff1602fd04ad7566e315957731359eab173b90` |
| Caddy `/usr/lib/libz.so.1.4` | zlib1.4-r0; `sha256:3960f21a3d4832ef4ed35900a2fa4ba76b558af0cb920b6dc5d7a235a32f1db9` |
| Caddy `/usr/bin/caddy` | upstream binary with three unresolved Go matches; `sha256:9967a2865cff91c5c642d08363efa666854a7f6d7d3b27b589cc1a1484dcfa49` |
| Mail `/usr/lib/libz.so.1.4` | zlib1.4-r0; `sha256:f77e7cd019fa5f3cd81bd5b37ddbca8f2048f054793e54c8996b649f9f0c5c16` |

The full SBOM distinguishes package-database evidence from payload ownership; a rewritten `/var/lib/dpkg/status` layer alone is not the binary's origin. Full file locations and package-owned file lists are retained for independent assessment.

Local verification: **380 passing tests** (211 backend +117 Web +52 deployment/evidence), ESLint, TypeScript, Python compilation, pip check and standalone production build PASS. CI independently reran211 backend +117 Web +6 scanner integrity tests, lint, TypeScript and production build; zero Web skips. Runtime evidence has11 passing check groups: startup/liveness; dependency readiness; observed Web TCP peer; forged forwarding rejection; hardening; tool/version checks; real TLS; synthetic OTP/CSRF/private media/logout; storage outage recovery; same-artifact restart recovery; cleanup. Engine28.0.4/Compose2.38.2 on GitHub is not EC2 Engine25.0.18/Compose5.7.1 acceptance, and restart recovery is not previous-release rollback.

Artifact `disposable-runtime-evidence-c52e8f21f882abb2e21b013394b2bc9869956bfc`, ID13974974795, has90-day retention. Downloaded under `.cache/master-readiness/ci-43288981277/`. All15 SHA256 hashes below were independently recomputed and matched. Cataloger Syft1.57.1 and scanner Grype0.121.3 used a single vulnerability database snapshot and explicit empty configuration; no excluded or ignored matches. Preserve this evidence in an approved archive before expiry.

| Evidence file | Verified SHA256 |
|---|---|
| `security/api.syft.json` | `0d85e9cc220a10145f41a2fac566979ed9abf41953ecb3605db7e677feb977ac` |
| `security/api.grype.json` | `bcc9f3734a1b9253cf1b0bb2322084ce2491807d41a22ab41af75b54095273ea` |
| `security/api.provenance.json` | `7fe1f3267d23af1dfcb401e8ca6f27403dfa7b746e5c20af2057369b79e3128e` |
| `security/web.syft.json` | `eed54b76767bac02277b0d67fc3f48172a284fde25f28dc30941c815fbbec86e` |
| `security/web.grype.json` | `090e71e528dab70f03711491c1e3cf478ea3adf7cdfdb2de76e2d08f6daafad1` |
| `security/web.provenance.json` | `6414a69d8cdf0d74b6f37a931d83334970f30c392c8aecc250a8fda9a7c59e82` |
| `security/caddy.syft.json` | `6ca8fc3ae8073d1af315cd362a807b4ee181f3a5f9ce27ae30c72088e234959e` |
| `security/caddy.grype.json` | `2790b625e5d28e4b41b4c14cc94a2473b866963e561ffe3c7e10f0a1ae5b167f` |
| `security/caddy.provenance.json` | `99194dcdd4d599d90a0127134fb0592106cbe71076cbef910db525d6d45416b7` |
| `security/mongo.syft.json` | `fee1fc06d3143f2ffebad5925fc82d5f3ce09a6b3ecaa06edf6d95ab4aafdd55` |
| `security/mongo.grype.json` | `d0ea7c452a99a686cecb50bfa15572c709d46f0f1a116023e490399e389763d3` |
| `security/mongo.provenance.json` | `18383839e2a258d1b37cc7f51d2271aea13b057c82a8397b20523fd74f87cf4f` |
| `security/mail.syft.json` | `bc26139f4550038e0e4533e645acf58278692c4f6b98ea4aca6ba2c97e84f908` |
| `security/mail.grype.json` | `3b7be00fe558a44d1e4de50073e0f65a1152a284db1c6569f53f352be264680b` |
| `security/mail.provenance.json` | `65d454a8669c5d2018f806b598beafeebdf29003ed1753795d6bec79f0121095` |

The remaining supported-upstream gate is exact: stable Debian lacks compatible fixes for the listed remaining package groups; Caddy2.11.9 retains go-jose/v3 3.0.5 without a patched v3 line, plus x/net0.60.0 and compress1.20.1. The latter modules have upstream fixes, but no tested supported Caddy release combination was established here. A forced major replacement or unstable distribution library import is not approved. These findings remain unresolved and block candidate security acceptance. The unchanged production Caddy setting still selects the original official image, not this wrapper; any future promotion needs separate reviewed configuration and release approval.

Implementation references: Docker documents checksum verification for remote [ADD inputs](https://docs.docker.com/reference/dockerfile/#add---checksum); Next.js documents running the [standalone server directly with Node](https://nextjs.org/docs/app/api-reference/config/next-config-js/output). No local Next.js bundled documentation was present in the installed package, so the official reference was consulted.

### Exact remaining High package inventory in the final candidate

All rows below remain blocking; affected ranges, vendor fixes, primary/supporting locations and full payload layer mappings are retained in the matching Grype/Syft files. Debian rows are source-package advisory matches; listing them does not assert exploit reachability. All are High; no Critical remains.

| Images | Package | Installed | Advisory IDs |
|---|---|---|---|
| API, WEB | `bsdutils` | `1:2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `gcc-14-base` | `14.2.0-19` | CVE-2026-102010, CVE-2026-95619 |
| CADDY | `github.com/go-jose/go-jose/v3` | `v3.0.5` | GHSA-mgcc-cww5-fp2q |
| CADDY | `github.com/klauspost/compress` | `v1.20.1` | GO-2026-6865 |
| CADDY | `golang.org/x/net` | `v0.60.0` | GO-2026-6860 |
| API, WEB | `libacl1` | `2.3.2-2+b1` | CVE-2026-54369, CVE-2026-54370 |
| API, WEB | `libblkid1` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `libc-bin` | `2.41-12+deb13u4` | CVE-2026-19499, CVE-2026-5435, CVE-2026-84243 |
| API, WEB | `libc6` | `2.41-12+deb13u4` | CVE-2026-19499, CVE-2026-5435, CVE-2026-84243 |
| API, WEB | `libgcc-s1` | `14.2.0-19` | CVE-2026-102010, CVE-2026-95619 |
| API, WEB | `liblastlog2-2` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `libmount1` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API | `libncursesw6` | `6.5+20250216-2` | CVE-2025-69720 |
| API, WEB | `libsmartcols1` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `libsqlite3-0` | `3.46.1-7+deb13u2` | CVE-2026-119373, CVE-2026-119374, CVE-2026-119379 |
| API, WEB | `libstdc++6` | `14.2.0-19` | CVE-2026-102010, CVE-2026-95619 |
| API, WEB | `libtinfo6` | `6.5+20250216-2` | CVE-2025-69720 |
| API, WEB | `libuuid1` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `login` | `1:4.16.0-2+really2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `mount` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| API, WEB | `ncurses-base` | `6.5+20250216-2` | CVE-2025-69720 |
| API, WEB | `ncurses-bin` | `6.5+20250216-2` | CVE-2025-69720 |
| API, WEB | `perl-base` | `5.40.1-6+deb13u1` | CVE-2026-82560, CVE-2026-9538 |
| API, WEB | `util-linux` | `2.41.5-0+deb13u1` | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |

## Residual runtime minimization campaign — 13 November 2026

Starting state: clean dev at a4736dfa875d5b5bbfbeb9049da786950caee299, which supersedes the supplied c52e8f2 reference only by four reports. Latest completed baseline run43290785411 matches120High/0Critical. No earlier work was discarded.

The complete120-match review is in [RESIDUAL_IMAGE_FINDINGS.json](RESIDUAL_IMAGE_FINDINGS.json): every image/package/advisory links to installed version, catalog/payload layers, installation reason and dependency evidence, affected component, prerequisites, reachability limit, vendor fix, remediation and regression risk. All20 distinct advisories were reviewed. None was waived as a false positive. The compress advisory includes FSE/Huffman encoding and decoding functions; the earlier decoder-only rationale was insufficient.

Candidate work: official Python3.12 Alpine3.24 retains the vendor's complete native closure; PyMongo's C extensions are built in a separate stage and asserted present. The entire211-test backend suite runs on musl with network disabled during tests; compilers/test dependencies remain outside runtime. Web retains Debian/glibc build stages and uses maintained Node24 Debian13 distroless runtime, with CA roots and native library closure intact. Numeric UID1000 and exec-form startup preserve unchanged Compose settings. No essential Debian package is force-purged and no shared library is manually deleted.

Node Alpine was evaluated but not selected: the official Node project classifies musl amd64 as Experimental. Distroless is maintained for Node24 LTS; its shell/package-manager absence changes debugging procedures, not application API behavior. [Node support](https://github.com/nodejs/docker-node#musl-builds-for-alpine), [Distroless runtime policy](https://github.com/GoogleContainerTools/distroless/blob/main/nodejs/README.md).

Caddy latest stable remains2.11.9. UpstreamPR8368 merged coherent updates to certificates/crypto (removing go-jose/v3), x/net0.62.0 and compress1.20.3. The full master commit includes125commits beyond stable, so the candidate retains exact stable core0d98caea58f794f88e709b1bef2880996a471bca and uses upstream xcaddy with the compatible dependency versions. This is a downstream custom candidate, not a newly released official Caddy version. No forced go-jose major replacement or new plugin is introduced. Upstream configuration/HTTP/TLS tests plus LANDVILLA's full Caddy/TLS suite must pass against the actual binary. [Upstream review](https://github.com/caddyserver/caddy/pull/8368), [custom builder](https://github.com/caddyserver/xcaddy#custom-builds).

New CI records verified manifest bytes and exact amd64 digests for all seven build/runtime inputs, the custom Caddy build-info, full Syft/Grype provenance and runtime/native-closure checks. Production Compose/Caddy settings remain unchanged. That preparation was subsequently tested; see the final residual candidate section below. No production acceptance is claimed.

## Final residual candidate — 13 November 2026

**REHEARSAL PASSED — PRODUCTION RELEASE BLOCKED. Image security acceptance: FAIL.** Exact tested source `197f5098720cd7c3adcbaec8590d94cc9164e65b`, [CI43375237826](https://github.com/techashfaq/landvilla/actions/runs/43375237826). Four Linux images built; the pinned Mail fixture was pulled and tested. All13 runtime check groups passed. The unsuppressed scan reports **172 total matches:15 High /0 Critical**: API4, Web11, Caddy0, Mongo0, Mail0 High. No finding was suppressed or waived.

Compared with the120-High starting scan,108 original package/advisory matches are no longer reported and12 carry forward (including3 renamed SQLite matches). Three new matches remain: SQLite CLI advisory119586 and2 libgomp1 matches. Net reduction is105 High matches (87.5%). The intermediate candidate had24 High; the supported Alpine krb5-libs1.22.3-r0 update removed all9 Kerberos matches. Counts are package/advisory matches, not proven exploits or unique CVEs.

Verified application/deployment tests: **383 distinct tests** (211 backend +117 Web +55 deployment/evidence); CI also reran the211 backend tests inside Alpine with network disabled. Caddy upstream configuration/HTTP/TLS tests passed in18 packages in each of two contexts (36 package executions; individual Go test-case count was not recorded). The second context is the retained xcaddy build module with matching build tags, unchanged go.mod before/after preparation and readonly tests. Lint, TypeScript, production build, pip check and Python compilation passed. No existing test was skipped or weakened.

### Final image and base identities

Image IDs below identify disposable local Linux amd64 artifacts, not published registry digests. No production image was published. Package payload locations and uncompressed layer IDs are in the complete SBOM/provenance and [RESIDUAL_IMAGE_FINDINGS.json](RESIDUAL_IMAGE_FINDINGS.json); package-database layers are not substituted for payload ownership.

| Image | All matches | High | Critical | Exact image ID |
|---|---:|---:|---:|---|
| API | 28 | 4 | 0 | `sha256:802f72ea1f82ea00a4e23830cc1fa552b8c24fb49618bc6b6f9959a4327078df` |
| WEB | 53 | 11 | 0 | `sha256:13d1b20a8859b48f870fb2b42064ab40c22b1f95fd14742c58c4557a93393116` |
| CADDY | 4 | 0 | 0 | `sha256:42a44e1886aabc6192f3e0d5197ded1d7f0ee776fde8819c21670354a9b0a3ce` |
| MONGO | 82 | 0 | 0 | `sha256:81657a5eeb435a55b0935e7a1ed8ad7fd0a20bbd3af50c4255a33bd62044d9d0` |
| MAIL | 5 | 0 | 0 | `sha256:cfdafb05e489fd0a93f82045a641610317dbaa7ea1da3d7a847cdb82f1001937` |

All seven manifest bodies were hashed and matched the pinned registry digest and Docker-Content-Digest header; unique Linux amd64 selection was verified. This proves content identity over HTTPS, not a cosign signature verification.

| Input | Manifest/index digest | Selected Linux amd64 manifest |
|---|---|---|
| `library/python:3.12-alpine3.24` | `sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89` | `sha256:a61cbd76a882645de7f91423329fe43a67eed60d7da24f9e5331414bb3618b20` |
| `library/node:24-trixie-slim` | `sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0` | `sha256:60587baa7c895cf438d44f691e4ac8248b36c13b26be77332f874bebb3a64201` |
| `library/caddy:2.11.9-alpine` | `sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee` | `sha256:fc9cbc100585871d18d4e451cca7021785c90a7006087427ae5ceb3e4efe6424` |
| `library/mongo:8.0` | `sha256:d97fea17ccb8d004cd137be8dab54d70d0df11be69c9f422aefe4484c8414ab7` | `sha256:9b73c38e39783bd21335f603a9f08be60fe385f5c28933ea32bb4a9fa1fd6d23` |
| `axllent/mailpit:v1.33.1` | `sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce` | `sha256:c95e8356f55b65520e8b7fd4d74d3e2d06e4a83513f639e316b1e592fbd52646` |
| `gcr.io/distroless/nodejs24-debian13:nonroot` | `sha256:6abfcb367ebc291572c774c1592a986be2ab26a2486f73093401327495a5962a` | `sha256:d4b8c34560df58c821ebda89a2897d7d183220c0debaf474a2b67a6c7cc22064` |
| `library/caddy:2.11.9-builder-alpine` | `sha256:646fee578e680989ca5c7fd1ce6f1de574d19fd71ef2221810cc0510a9f40c86` | `sha256:29f98311e17e583811355fa62cc080f71d6f3aa19cf09a9e1494d30579f8bebf` |

Runtime: Python3.12.16, Node24.22.3, Node-bundled SQLite3.54.1/Undici7.30.2, Mongo helper js-yaml3.15.2. API128,213,011 bytes; Web194,409,548 bytes. API uses musl and retains the complete vendor native closure; Web uses glibc distroless with CA/DNS/native libraries intact. Build/test tools remain in intermediate stages. Public assets/static output, native PyMongo/BSON extensions, Python compression/SQLite/ctypes/curses, CA trust, DNS and Sharp PNG processing all passed runtime probes.

Caddy actual binary/SBOM confirms go-jose/v4 4.1.9 (v3 absent), compress1.20.3, x/net0.62.0, crypto0.92.0 and certificates0.30.3-0.20261105213751-6d5a251fbe01. It retains stable Caddy2.11.9 core. This is an upstream-reviewed dependency migration in a downstream custom build, not a new official stable release. Operational ownership and future promotion remain separate decisions. The default builder's effective file capability was disabled/removed; execution passed as UID10001 with dropped capabilities and no-new-privileges. Container restrictions were not relaxed.

### Exact unresolved High inventory and residual decision

| Image/package | Installed | Remaining High advisories |
|---|---|---|
| API sqlite-libs |3.53.4-r0|CVE-2026-119373, CVE-2026-119374, CVE-2026-119379, CVE-2026-119586|
| Web gcc-14-base |14.2.0-19|CVE-2026-95619, CVE-2026-102010|
| Web libgcc-s1 |14.2.0-19|CVE-2026-95619, CVE-2026-102010|
| Web libgomp1 |14.2.0-19|CVE-2026-95619, CVE-2026-102010|
| Web libstdc++6 |14.2.0-19|CVE-2026-95619, CVE-2026-102010|
| Web libc6 |2.41-12+deb13u4|CVE-2026-19499, CVE-2026-5435, CVE-2026-84243|

The15 matches represent9 advisory IDs. All remain blocking. No attack reachability was demonstrated. Runtime presence is confirmed; source-package matches do not prove each binary contains the vulnerable function.

- SQLite119373: FTS5 negative-rowid prefix MATCH overflow;119374: crafted FTS5 secure-delete index corruption;119379: crafted session changeset overflow. Alpine's3.24 recipe enables FTS5/session; upstream3.54.0 fixes these, but stable3.24 still packages3.53.4-r0. Classification: **vendor-unfixed and unresolved; application reachability not demonstrated**. MongoDB use does not prove absence of every native/transitive SQLite path. [Stable recipe](https://raw.githubusercontent.com/alpinelinux/aports/3.24-stable/main/sqlite/APKBUILD), [CNA119373](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/119xxx/CVE-2026-119373.json), [CNA119374](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/119xxx/CVE-2026-119374.json), [CNA119379](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/119xxx/CVE-2026-119379.json).
- SQLite119586 requires crafted recovery output piped into the SQLite CLI, then dot-command execution. No CLI package is cataloged; library/Python extension presence alone does not establish this path. Classification: **reachability not demonstrated**, pending independent component-absence proof; no false-positive waiver. [CNA119586](https://cveawg.mitre.org/api/cve/CVE-2026-119586).
- GCC95619 affects aligned operator-new size arithmetic;102010 affects native priority-queue erase_if. These require affected native call paths and attacker-influenced inputs. GCC14 fixes exist in14.4.0-3 unstable, but no supported Trixie backport was established. Native Node/Sharp library closure must not be removed. [95619](https://security-tracker.debian.org/tracker/CVE-2026-95619), [102010](https://security-tracker.debian.org/tracker/CVE-2026-102010).
- glibc19499 requires affected strfmon formatting;5435 concerns deprecated DNS pretty-printer handling of crafted data;84243 requires attacker-controlled LANGUAGE/locale plus a readable crafted catalog and gettext call. No browser-to-native exploit chain was established. Stable Debian remains unpatched for these records. Classification: **vendor-unfixed and unresolved**, not accepted harmlessness. [19499](https://security-tracker.debian.org/tracker/CVE-2026-19499), [5435](https://security-tracker.debian.org/tracker/CVE-2026-5435), [84243](https://security-tracker.debian.org/tracker/CVE-2026-84243).

**Required decision:** keep production security blocked. Await supported Alpine/Debian backports or qualify a maintained complete runtime/backport with ABI, native-closure, full rehearsal and unsuppressed scan evidence. Do not import unstable/edge core libraries, remove required libraries, force a Node Experimental musl build, or approve a release based only on unproven reachability. An independent component proof may clarify a source-package match but does not authorize scanner exclusions or waive other findings. Replacing Caddy was unnecessary because the custom upstream-reviewed dependency migration cleared its High gate and passed equivalent tests.

### Evidence and executed commands

Artifact14014147791,90-day retention: [download](https://github.com/techashfaq/landvilla/actions/runs/43375237826/artifacts/14014147791). Archive SHA256 `2205de149cc5a9fabb88360d2b64b3ecac87a721d937ca842307052ffc9cfa92`. Downloaded to `.cache/master-readiness/ci-43375237826/`; all15 report hashes below recomputed and matched. Source/image binding and base manifests were checked. Preserve reports in an approved archive before expiry. Raw lower-severity findings remain retained.

| Evidence | SHA256 |
|---|---|
| `security/api.syft.json` | `a837bc6f38e98440335c58af02f8b9fb84bf6b3adb000bddc35b58c27159b14f` |
| `security/api.grype.json` | `c1a67883ab50c185da1afe8f046faea52dedb094f906692fd330be1592fb2d6a` |
| `security/api.provenance.json` | `e6ba060c0e931964be6af998a1212d230a56d1dc72252bb81a6d6a8ddbbdf0c4` |
| `security/web.syft.json` | `b8fc9ba4c24df875cfe0e92ac2c1399071d43aec5b491d312057d99e87a44ca1` |
| `security/web.grype.json` | `7880ba13320c94aa14c2a47a97d09e32b8f4747f5b7a59834dfa2d9b44485a47` |
| `security/web.provenance.json` | `c9a1cc7823b1dd59abadfee397eda3d1a381853541fdb53ac48ab58417e369c7` |
| `security/caddy.syft.json` | `80e47360c5b09677a76e7bcc3449463ac8f544f73ed1e45d900ce8831fdefc64` |
| `security/caddy.grype.json` | `7885abcf62f35f3c0cb2a6e83be4d3d6d9db709ba3358b0f9c6c53d3a757ef1c` |
| `security/caddy.provenance.json` | `990c76b3dcc770dc31bb3de4eb7c8d2478350043bcd8813cbf833f688d4b5217` |
| `security/mongo.syft.json` | `c43f1afa3afe7ca461c8f4c76dfb424be6a9de75bdec2abee9cf3854b69728dc` |
| `security/mongo.grype.json` | `ca74cc9e173dbbe0092853cb216b3d6118c030d4afadd897cf092858cb9c31c3` |
| `security/mongo.provenance.json` | `d25b90f99936ad3178fe83534baafa076f4cccd7981f2760348b58cceca2fa2f` |
| `security/mail.syft.json` | `bc26139f4550038e0e4533e645acf58278692c4f6b98ea4aca6ba2c97e84f908` |
| `security/mail.grype.json` | `f8194d6d163c71e3d147e1b222a422bb756003a20279f0bf1f41cd8a7805d168` |
| `security/mail.provenance.json` | `dcc3648f37f7df4b7c9654139ec7a81d1e4fa435ea8b1caa746735532b5dc072` |

Executed in disposable GitHub Linux: `python scripts/rehearse-linux-ci.py`; `python scripts/scan-rehearsal-images.py --result .cache/linux-rehearsal/result.json`; backend unittest discovery, pip check, Web npm test/lint/typecheck/build,55 deployment tests against the exact copied Caddy binary. The scanner uses checksum-verified Grype0.121.3 and Syft1.57.1, explicit empty configuration and no ignored matches. All five scans used the same vulnerability database built2026-11-12T06:20:58Z; this is a dated feed observation, not proof against later disclosures. Linux log SHA256 `cba882d205af502273bf7174c069f33e5b322f514e6b27b8bf0d1ccb198e9195`; offline log SHA256 `93213907c997cfce9ea3162564e5d395d0aaa3a35ffa44882fd0de117b37dcbf`.

Local command: `.cache/dependency-independent-verification/run-20261112-01/venv/Scripts/python.exe scripts/verify-readiness.py --python F:/projects/landvilla/.cache/dependency-independent-verification/run-20261112-01/venv/Scripts/python.exe --compose F:/projects/landvilla/.cache/phase2-security-review/compose/docker-compose.exe --caddy F:/projects/landvilla/.cache/caddy-validation/caddy.exe --stage STAGE`, separately for backend,web,deploy,build,syntax. Local383 tests PASS; final deployment55PASS16.609s; buildPASS88.359s; final compilationPASS2.375s; pip check/lint/typesPASS. Local artifacts are under `.cache/master-readiness/`; they are not production credentials or committed build output.

Attempt history:43371089011 stopped before builds because sanitized child environment omitted non-secret runner identity; corrected with regression coverage.43371806526 built all images and passed211 musl tests but Caddy startup failed.43372193950 additionally passed the exact Caddy graph tests but reproduced startup failure. The inherited effective file capability was removed without changing container privileges. Pending superseded runs43372759278/43372859957 were cancelled by workflow concurrency, not recorded as tests.43373185420 passed all13 runtime groups and reported24High/0Critical.43375237826 verified the same-branch Kerberos patch and final15High/0Critical.

No EC2/provider connection, production environment/settings change, image publication, deployment, firewall/DNS mutation or production data operation occurred. Ordinary bridges are not directional isolation. GitHub Engine28.0.4/Compose2.38.2 acceptance is not target EC2 acceptance; same-artifact restart is not previous-release rollback. Existing external gates remain open.
