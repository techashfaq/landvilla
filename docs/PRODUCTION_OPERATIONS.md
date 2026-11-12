# Production operations — acceptance pending

Use PRODUCTION_DEPLOYMENT_RUNBOOK.md and PRODUCTION_ROLLBACK_RUNBOOK.md for exact controlled startup/shutdown. Operate only the identified project and immutable release. Production is not certified by this document.

## Health, outages and observability

API `/health` is running-process liveness; startup requires Mongo connectivity and identity indexes first. API `/ready` is a bounded Mongo ping/hello plus R2 HeadBucket, not transaction/object-write permission proof. Web readiness hides API diagnostics; Caddy withdraws the whole Web upstream after readiness failure (15s interval/8s timeout). Docker unhealthy state itself does not restart a process; unless-stopped restarts exited processes. Alert on sustained readiness failures, error-rate, certificate expiry, disk/inodes/memory pressure, auth abuse and restart count. Define alert ownership/on-call before launch.

Inspect narrowly: service state, health status, timestamps and bounded sanitized logs. Never dump Config.Env, full resolved Compose, cookies, request bodies/headers, query strings or provider exceptions. Caddy request logs are disabled; application structured logs retain event/request ID/status/duration only. Validate actual redaction before enabling traffic. Container logs rotate at10MiB×3; avoid unbounded exports.

For Mongo/R2 outage, preserve data and current artifacts, verify provider status/config privately, then recover dependency readiness before ingress. Never seed, reset, drop indexes or switch to an unrelated bucket to pass health. Use controlled cold-start/failure drills and stop criteria; repeated process restarts are not recovery evidence.

## Secret rotation

Rotate provider/API credentials in their approved secret manager, verify least privilege with nonproduction tests, prepare access-controlled external files atomically, then recreate only affected services in a controlled window. Do not generate or display real credentials in chat. Proxy token/key rotation requires coordinated Caddy/Web/API configuration; mixed generations fail closed. Stop ingress during rotation, validate private readiness and authenticated path, then restore it. There is no implicit dual-key grace period. Rotate OTP HMAC with a reviewed outstanding-challenge/session policy. Confirm revoked old credentials stop working without exposing them.

## Backups and recovery

Monitor Atlas backup/PITR completion and retention; record recovery points before releases. Restore only into approved isolated targets and validate ownership, indexes, counts and consistency. Record measured recovery time. R2 object backup/recovery is separate from Mongo backups. Keep backups encrypted and access-controlled, with deletion/retention approved by the owner. Never claim restore-tested without a completed drill.

## Disk and artifact lifecycle

Before builds/releases inspect `df -h`, `df -i`, memory and `docker system df`. Reserve enough capacity for both current and known-good rollback images, build working space, logs and TLS/data volumes; thresholds require actual host sizing. On pressure stop new releases, preserve rollback artifacts and investigate. Remove only individually reviewed unused image IDs after confirming no current/rollback reference. Never use broad `system prune`, volume prune or delete Caddy `/data`/`/config`. Rehearsal volumes have separate labels and cleanup approval.

## Certificates and restart

Caddy owns automatic renewal; persist and privately back up `/data` and `/config`, monitor expiry/renewal errors and verify egress/clock/DNS. Rehearse with internal/staging issuance before production. Reboot/recreation tests must establish resource persistence, API source IP, readiness and any future firewall fail-closed ordering. No directional policy is currently implemented; an internal/ordinary bridge does not block every unintended path.

## Dependencies and incident handling

Use requirements-production.txt and its constraints, requirements-test.txt for regression tooling, and Web's lockfile. Coordinate framework upgrades, run pip check, all regression suites, advisory checks and Linux image acceptance. Recheck exact image manifests/scans; never replace a digest silently. Historical requirements.txt is archival only.

For suspected compromise: stop ingress using the reviewed runbook, preserve sanitized evidence and immutable artifacts, involve the owner, assess credential rotation and recovery scope. Do not erase logs/data or widen trust. Native Android ingress, legal/support readiness and production provider/browser acceptance remain explicit release gates.
