# Image security remediation — BLOCKED

Updated 13 November 2026 (India). Public advisory and registry observations below were retrieved on 12 November 2026 UTC. Supported image changes are prepared, but **candidate Linux builds, complete runtime rehearsal and fresh image scans are still pending**. This document does not accept the candidate or authorize production deployment.

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

The baseline summary retains every matched ID, installed version, package type, catalog location, fix metadata and advisory URL. **It does not retain the original full SBOM, full Grype JSON, or complete layer attribution. Those missing historical artifacts have not been recovered.** Registry layer inspection corroborates selected upstream package provenance, but cannot substitute for a full SBOM of the exact deleted runner image. The remediation workflow must archive full candidate SBOMs, full unsuppressed Grype reports, image IDs, rootfs layers, source revision, package locations, match details and report hashes. Historical artifacts had 14-day retention; preserve evidence before expiry. Updated candidate workflow requests 90-day retention.

API/Web/Caddy are production artifact concerns. Mongo/Mail are disposable fixtures and do not describe Atlas or a production mail service. The 36-Python/55-npm application feed observation did not cover these OS, tooling and embedded-binary findings.

## Implemented candidate changes, awaiting Linux verification

| Artifact | Reviewed change | Provenance / exact input |
|---|---|---|
| API | Retain Python 3.12 and Debian Trixie; install signed vendor `zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1` | Parent `python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`. Fixed package exists in Trixie security repository; no core-library transplant. |
| Web | Move all three stages together to official Node 24 Trixie Slim; install the same Trixie zlib fix in runtime; remove unused npm/npx and Yarn runtime tooling | Parent `node:24-trixie-slim@sha256:af02d57b57719b9657a45199a79264a9437940cd55b3c7b3fc99615654f124a0`. Official image metadata lists Node 24.22.3. Build stages retain npm; standalone runtime still invokes `node server.js`. |
| Caddy | Candidate wrapper installs signed Alpine 3.24 `zlib=1.4-r0`; upstream Caddy binary is unchanged | Parent `caddy:2.11.9-alpine@sha256:0bbb055bda6793c999bde78b1b5ce3e89f829fb031af2cf50056ea1246559fee`; Dockerfile `deploy/images/caddy/Dockerfile`. Current parent is Alpine 3.24.4 and its own branch repository contains this fix. No Go module replacements. |
| Mongo fixture | Same-major js-yaml 3.15.2 replaces the separately vendored entrypoint helper only | Parent `mongo:8.0@sha256:d97fea17ccb8d004cd137be8dab54d70d0df11be69c9f422aefe4484c8414ab7`; Dockerfile `deploy/images/mongo/Dockerfile`. npm tarball SHA256 `7f005cf0b8ee639b4557e0e321dc067c1f2aa0a442d096e03f2ab53353738794`, verified against registry SHA512 integrity. Server and mongosh remain unchanged. |
| Mail fixture | Upgrade official Mailpit from v1.33.0 to v1.33.1 | `axllent/mailpit:v1.33.1@sha256:aef2aacc11f075ec0fb6874275ee4a421e688e11a96ebb296134d1735c7761ce`. Registry filesystem inspection finds zlib 1.4-r0 in layer `sha256:9c6a15861a91c5c783ea0bf2f785f597ed230ba18361b2dbed693d6cda6ae453`; runtime and fresh scan remain required. |

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

Mongo's `/opt/js-yaml/package.json` reports 3.13.1. [Official Docker image source](https://github.com/docker-library/mongo/tree/master/8.0) vendors `/opt/js-yaml/js-yaml.js` and package metadata for entrypoint YAML configuration parsing; it is not a mongosh bundled package. Rehearsal supplies explicit mongod flags rather than a YAML config, but still updates the vulnerable package.

- [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m): scanner fix 3.15.0.
- [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj): scanner fix 3.15.1.
- [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh): scanner fix 3.15.2.

Candidate selects the supported same-major 3.15.2 distribution bundle after verifying [npm metadata](https://registry.npmjs.org/js-yaml/3.15.2) and tarball integrity. Mailpit's sole Critical baseline finding is the same Alpine zlib CVE-2026-4738 above; v1.33.1 contains the fixed package. Both fixture gates still require fresh scans and successful Mongo/SMTP/TLS runtime acceptance. No change concerns production Atlas or production email credentials.

## Candidate verification and acceptance gate

Pending candidate evidence must state the exact tested commit, run URL, all image IDs/digests, per-image complete scan counts, installed fixed versions/locations/layers, test totals and hashes of full SBOM/Grype reports. Do not substitute this static review for those results.

The workflow uses disposable GitHub-hosted Linux runners and synthetic local dependencies only. No production credentials, environment files or external production resources are supplied; images are not published. Nonroot, read-only filesystems, capability restrictions, resources, TLS verification, Host/SNI validation, signed proxy identity, cookies, CSRF and target identity controls remain required. Candidate fixture metadata is bound to the tested source revision and exact Linux amd64 image IDs.

The gate fails on every unresolved High/Critical match, including vendor-unfixed matches and rehearsal fixtures. No ignore configuration, severity override, exclusion or `ignore-unfixed` flag is introduced. Raw findings are retained. A successful runtime rehearsal does not change that gate.

**Baseline runtime rehearsal PASS; baseline image security FAIL. Candidate verification PENDING. Production release BLOCKED.** Supported vendor fixes are implemented for review; unresolved Debian and Caddy upstream findings remain explicit blockers. No production readiness or deployment is claimed.
