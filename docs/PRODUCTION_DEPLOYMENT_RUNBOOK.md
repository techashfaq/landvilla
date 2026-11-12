# Controlled production deployment

**STOP: execution requires all release gates in PRODUCTION_EXTERNAL_BLOCKERS.md and recorded operator approval.** Nothing in this document claims deployment. Public exposure, DNS, firewall, AWS security groups, Atlas allow lists and billing each retain separate approval requirements.

## Artifact and environment gate

Use only a clean identified commit on `dev` with passing final tests and Linux rehearsal evidence. Compare local/CI source SHA with `/opt/landvilla` HEAD and `git status --porcelain`; stop if different/dirty. Never `reset --hard`, overwrite a dirty host checkout or deploy the historical Emergent freeze. Retain previous checkout/configuration before a reviewed fast-forward update.

On an approved Linux build host, build API/Web using full SHA tags and pinned base digests. `scripts/record-release.py --api <repository>:<full-sha> --web <repository>:<full-sha> --output .cache/releases/<full-sha>.json` records actual image IDs, repository digests when present, architecture and configuration/dependency hashes. A local image ID is NOT a registry manifest digest. Choose the authorized registry/artifact transport, publish only after that approval, pull by recorded digest and compare resulting image identity. Do not invent a registry digest or use latest. Keep the exact images and manifest for rollback; CI's disposable image build alone does not distribute a release.

Production API settings remain `/etc/landvilla/production.env`; do not display them. Require approved ownership/mode0600, DB_NAME=landvilla_prod, S3_BUCKET=landvilla-property-media-prod, verified Mongo TLS, private R2, strong OTP secret and approved sender configuration. Required variables are listed in RELEASE_OPERATIONS.md. SMTP/Twilio/Google are required only for enabled channels.

Access-controlled `/etc/landvilla/compose.env` references that API file and contains immutable image references, collision-approved subnet/pool/exact Web peer, ACME contact, and two distinct dedicated proxy credentials. LANDVILLA_INGRESS_TOKEN is Caddy/Web-only; LANDVILLA_WEB_API_IP_KEY becomes WEB_API_IP_KEY in Web/API. These are runtime secrets, never build arguments. Public Google audience is the only Web build argument. Never print resolved Compose/config/container environments.

Use a sanitized environment for **both validation and startup**, avoiding ambient shell interpolation overriding the reviewed file. The examples below assume standard executables in `/usr/local/bin:/usr/bin:/bin`; verify installed paths first. Docker context must be the intended local production daemon, never an inherited remote DOCKER_HOST.

```sh
cd /opt/landvilla
git status --porcelain
git rev-parse HEAD
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" python3 scripts/check-production-compose.py --env-file /etc/landvilla/compose.env
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml config --quiet
```

The checker prints names/results only. Validate the exact selected Caddy image in the separately authorized rehearsal. Do not treat adaptation as TLS/browser acceptance. Validate secret presence/configuration privately; never source unreviewed files as executable shell code.

## Backup and capacity gate

Record Atlas backup/PITR state and latest successful recovery point. Complete an isolated restore integrity/timing drill. Confirm media backups independently. No automatic index/seed/migration occurs at startup; any additive production index operation still requires separate DB approval after backup/compatibility review. Verify free disk/inodes, image+rollback storage, memory headroom and bounded tmpfs usage. No known-good rollback target means first-launch failure leaves services stopped.

## Approved startup only

```sh
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 api web
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml exec -T web node -e 'fetch("http://127.0.0.1:3000/ready",{signal:AbortSignal.timeout(8000)}).then(r=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))'
```

Stop on failure. Confirm actual API-observed Web source, authenticated client identity, secret scoping, health, immutable artifact identity and unpublished API/Web ports before Caddy. `docker inspect` configured allocation alone is insufficient. Do not broad-log headers, cookies, query strings, provider errors or environment values. Database failure at cold start can exit/restart the API even though its running `/health` is dependency-free.

After explicit public-exposure approval and verified DNS/TLS/network prerequisites:

```sh
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml up -d --no-build --wait --wait-timeout 120 caddy
```

Run real external TLS/redirect/security-header/static/public-route checks, then authorized account/admin/CSRF/private-media acceptance. Internal API `/health` and `/ready` remain private; public equivalents must return404. Record exact release SHA/digests and monitoring baseline. DNS/TLS failure cannot be substituted by internal HTTP success. Keep previous artifacts throughout the acceptance window. Follow PRODUCTION_ROLLBACK_RUNBOOK.md immediately on a failed release gate.
