# Image security gate — BLOCKED

12 November 2026. [Run43245360600](https://github.com/techashfaq/landvilla/actions/runs/43245360600), source `ad1acd44cf1a185ecaadcd852d80c3d37af2a9a0`, completed Linux runtime acceptance but failed the separate image scan. Scanner: Grype0.121.3, archive SHA256 `e9da18cc1429e786722e32161288103600efffd8e483c90761f90485bd1bec85`, matched authoritative GitHub release metadata before execution. No ignore file, severity downgrade or ignore-unfixed option was used.

Evidence: workflow artifact `disposable-runtime-evidence-ad1acd44cf1a185ecaadcd852d80c3d37af2a9a0`, `image-security.json` and `result.json`; downloaded under `.cache/master-readiness/ci-43245360600/`. Artifacts have14-day retention; preserve the sanitized release evidence in an approved operational archive before expiry. The table counts package/advisory matches, not unique CVEs or proven exploitable application paths.

| Image | Total matches | High | Critical | Unique high/critical advisory IDs within image |
|---|---:|---:|---:|---:|
| API | 217 | 61 | 0 | 19 |
| Web | 232 | 55 | 2 | 25 |
| Caddy | 11 | 3 | 1 | 4 |
| Mongo rehearsal fixture | 96 | 3 | 0 | 3 |
| Mail rehearsal fixture | 5 | 0 | 1 | 1 |
| Total package/advisory matches | 561 | 122 | 4 | Not additive across images |

API/Web/Caddy are production artifact concerns. Mongo/Mail are rehearsal-only images, not a production Mongo or SMTP deployment. The earlier36-Python/55-npm feed check did not cover OS packages, base-image tooling or embedded Go modules. Its zero-entry observation is not an all-image clean bill.

## Material vendor verification

1. **Web glibc:** image `libc6`/`libc-bin`2.36-9+deb12u14 matched CVE-2026-5450, scanner Critical. [Debian](https://security-tracker.debian.org/tracker/CVE-2026-5450) lists this Bookworm build as vulnerable and Trixie2.41-12+deb13u4 as fixed. Debian also labels the Bookworm issue minor/no-DSA; that severity disagreement is recorded, not used to silently waive it. Applicability to the application's input path has not been demonstrated or disproven. Review a compatible supported Node24 runtime base containing the fixed library, then rebuild and rerun; never replace glibc manually across distributions.
2. **API zlib:** installed1:1.3.dfsg+really1.3.1-1+b1 matched CVE-2026-76844 and CVE-2026-85091. [Debian's advisory](https://security-tracker.debian.org/tracker/CVE-2026-76844) lists1:1.3.dfsg+really1.3.1-1+deb13u1 as the Trixie security fix. A reviewed updated base or narrowly versioned vendor package update is required; no package/image change is asserted here.
3. **Caddy/Mail Alpine zlib:** installed1.3.2-r1 matched CVE-2026-4738, scanner Critical. [Alpine](https://security.alpinelinux.org/vuln/CVE-2026-4738) lists1.4-r0 fixed on supported branches. Its description references GDAL's contributed infback9 code and severity metadata differs; package build/content reachability needs investigation. The scan remains failing pending a reviewed correction or documented security determination; no unsupported false-positive claim.
4. **Caddy Go modules:** `github.com/go-jose/go-jose/v3`v3.0.5 matches [GHSA-mgcc-cww5-fp2q](https://github.com/advisories/GHSA-mgcc-cww5-fp2q), whose v3 line has no patched version; v4.1.6 is a different major line. Do not force a transitive major replacement into Caddy. `golang.org/x/net`v0.60.0 matches [GO-2026-6860](https://pkg.go.dev/vuln/GO-2026-6860), fixed0.62.0 for affected HTML parsers. `klauspost/compress`v1.20.1 matches GO-2026-6865, with scanner fix1.20.2. Confirm exact compiled call paths and supported upstream remediation. Official Caddy latest-release metadata still reported2.11.9 on this review date; no newer patched Caddy version is invented.
5. **Web embedded/tooling npm packages:** scan found brace-expansion5.0.9 and undici6.28.0. [Brace advisory](https://github.com/advisories/GHSA-qhr7-859c-m2p7) requires5.0.11 on that line; [Undici advisory](https://github.com/advisories/GHSA-xjj6-f33q-929c) requires6.29.1 for the affected6.x range. The application lockfile has development brace versions5.0.12/1.1.21 and no direct undici entry. This suggests base/embedded tooling, but package locations were not retained in the summary, so exact provenance/reachability remains unresolved. Do not pretend an application npm override fixes an embedded image copy. Inventory locations/SBOM, update the owning distribution or remove demonstrably unused runtime tooling, then scan and test the changed artifact.
6. **Mongo fixture:** js-yaml3.13.1 has three high advisory matches; scanner reports highest relevant3.x fix3.15.2. Review a patched official fixture image or a supported fixture-tool update. This does not imply an Atlas server/package finding.

Many additional OS matches are tagged `wont-fix` or `not-fixed` by scanner/vendor metadata. Those labels are not automatic acceptance. The complete sanitized artifact retains every matched ID, package version, fix metadata and source URL. No exploit test was sent to production and no reachability conclusion is inferred from a package match alone.

## Concrete next engineering work

The latest user authorization allows disposable GitHub CI but explicitly says not to modify production deployment settings. Current production Dockerfiles/base pins and Compose/Caddy settings were therefore retained while the new findings were investigated. No unverified major dependency pin, custom Caddy binary, broad OS upgrade or changed distribution was introduced.

Prepare/review an image-remediation change set: enumerate package locations; select vendor-supported patched Python/Node/Caddy artifacts with observed digests; resolve unavailable upstream fixes through supported upgrades or a documented security review; keep the existing trust, UID, capability, TLS and cookie boundaries; build all candidates only on disposable runners; rerun373 local checks plus complete Linux smoke and unsuppressed scans. Production image-setting changes require authorization under the current constraint. Any subsequent release requires zero unresolved critical/high findings, exact new artifact identities and the separate EC2/provider/recovery gates.

**Runtime rehearsal PASS. Image security gate FAIL. Production release BLOCKED.** No images were published as a release; no EC2 service or production provider was accessed or changed by this campaign.
