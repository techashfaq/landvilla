# Isolated Linux rehearsal

Prepared configuration, not evidence of execution. Never run the production startup recipe as a rehearsal.

Current EC2 restriction: no container start/stop/recreate is authorized. Operator-reported1.9GiB memory is not approved for this seven-service fixture. The owner explicitly authorized only disposable GitHub-hosted runtime execution; commands below are gated future operator steps. Docker on EC2 requires `sudo`; do not change socket permissions or group membership. Preparation now inserts one guarded synthetic city reference record so public meta/discovery checks cannot pass merely by rendering an error fallback. It creates no customer listings or production records.

`deploy/compose.rehearsal.yml` uses project `landvilla-rehearsal`, separate project-scoped Mongo/TLS volumes, an owned internal IPv4 bridge and only `127.0.0.1:8443` ingress. API/Web have no published ports. Caddy uses its disposable internal CA for `localhost`; no production ACME/domain/certificate is used. No production env file is mounted. All fixture credentials are explicitly public test values and rejected by production validation where applicable.

Caddy also joins a separate ordinary ingress bridge. This is required for effective Docker loopback port publication; the first internal-only bridge configuration failed with connection refused in Linux. Web/API/dependencies join only the internal bridge. Both subnets must be collision-checked and non-overlapping; `REHEARSAL_INGRESS_SUBNET` has no EC2 default. Caddy has ordinary bridge egress, which is not an egress allowlist. No directional isolation is claimed. The checker refuses existing project containers, named networks or volumes before any reuse.

The executed GitHub runner uses Engine28.0.4/Compose2.38.2; this does not certify EC2 Engine25.0.18/Compose5.7.1 runtime compatibility. Docker documents [localhost port reachability limitations before Engine28](https://docs.docker.com/engine/network/port-publishing/). Before any EC2 rehearsal, obtain separately approved host/network controls and prove external denial; the loopback declaration alone is insufficient on that host. No daemon, firewall, network policy or EC2 change was made.

Mongo uses only `landvilla_rehearsal`; preparation initializes the disposable replica set and identity indexes/marker, not customer/demo seeds or production migration commands. Storage is a bounded in-memory S3-shaped mock for only `landvilla-property-media-rehearsal`. It is NOT evidence of real R2 authentication, privacy or permissions. Mailpit catches synthetic OTP email locally, requires authenticated STARTTLS and uses a generated disposable CA trusted by the API. It has no relay or published UI. Actual fixture image/user/volume behavior remains a Linux test gate.

## Before startup

1. Record host identity, clean source commit, capacity and all existing resources with `scripts/inspect-rehearsal-host.sh`. Do not alter existing production resources.
2. Approve complete route/network collision inventory. No static EC2 subnet is provided. Copy `deploy/rehearsal.env.example` to a private nonproduction settings file outside Git, fill the approved subnet/pool/Web IP and exact reviewed application image IDs or repository digests. The static Web IP must be outside the dynamic pool.
3. Build the same reviewed backend/Web Dockerfiles on Linux with full-commit tags; no separate application fork. Review image provenance/scans. The registry-derived base digest inventory is `deploy/reviewed-base-images.json`; digest observation is not runtime acceptance.
4. Validate declarations and local collisions before creating anything:

```sh
python3 scripts/check-rehearsal.py --env-file /etc/landvilla/rehearsal.env --host-check
```

This host check cannot establish remote VPC/VPN/peering routes. On an existing rehearsal it intentionally refuses silent reuse; inspect existing resources explicitly before any rerun.

## Start, accept and stop

The following commands are future operator actions, never proof they were run. `REHEARSAL_SETTINGS` denotes the reviewed nonproduction file; it must not be `/etc/landvilla/production.env` or production Compose settings.

```sh
REHEARSAL_SETTINGS=/etc/landvilla/rehearsal.env
docker compose --env-file "$REHEARSAL_SETTINGS" -f deploy/compose.rehearsal.yml up -d --wait --wait-timeout 180
docker compose --env-file "$REHEARSAL_SETTINGS" -f deploy/compose.rehearsal.yml exec -T web node -e 'fetch("http://127.0.0.1:3000/ready").then(r=>process.exit(r.status===200?0:1))'
docker compose --env-file "$REHEARSAL_SETTINGS" -f deploy/compose.rehearsal.yml ps
```

Retrieve only the rehearsal CA public certificate from `/data/caddy/pki/authorities/local/root.crt` in its Caddy container into ignored local evidence. Use `curl --cacert` or a temporary browser profile with explicitly approved CA trust. Never disable TLS verification or bypass a browser warning. The CA private key must not leave the disposable container. `scripts/smoke-rehearsal.py --env-file "$REHEARSAL_SETTINGS" --ca <public-CA-path>` validates targets first and exercises synthetic OTP, CSRF, role denial, private upload/media and logout. It prints no OTP, cookies or response payloads.

Measure the actual Web TCP peer inside the API namespace with bounded connection metadata, not packet bodies. Compare with FORWARDED_ALLOW_IPS; repeat after recreation/reboot. Test unsigned/expired/duplicate/wrong-key identity claims and a genuine request. Do not broaden trust on failure. Validate UID, effective capabilities, read-only paths, memory/PID limits, no published API/Web ports, storage outage/recovery and signal drain. Distinct client identity is locally regression-tested; actual topology remains a separate gate.

Public `/health` and `/ready` must return 404. Internal readiness is not a public diagnostic endpoint. Dependency-free `/health` starts only after API startup's DB/index requirements succeed; database outages at cold start can cause exit. Rehearsal uses restart=no so failures remain visible.

```sh
docker compose --env-file "$REHEARSAL_SETTINGS" -f deploy/compose.rehearsal.yml stop --timeout 40
docker compose --env-file "$REHEARSAL_SETTINGS" -f deploy/compose.rehearsal.yml down
```

`down` retains rehearsal volumes. After confirming labels/project/settings and that all data is disposable, the same exact rehearsal command with `down --volumes` removes ONLY this exercise's data. Never use a production file, global prune, wildcard deletion or production volume names. Retain sanitized acceptance evidence before cleanup.

Rollback here means restore an already tested rehearsal image/settings manifest, then rerun acceptance; restart of the same image is not rollback evidence. No known-good prior production artifact is asserted. The shared bridge does not prohibit Caddy→API or API→Web: directional isolation remains unapplied and separately approved.

## Disposable CI alternative

The GitHub `Isolated release verification` workflow uses an ephemeral hosted Linux runner, no repository secrets, no image publication and no production services. `scripts/rehearse-linux-ci.py` refuses ordinary hosts/EC2, checks local routes before selecting an ephemeral-only subnet, builds exact-commit images, validates the fixture, tests runtime behavior and removes its own labelled resources. Uploaded `result.json` records actual completed checks and artifact IDs; a failed workflow is FAIL, not acceptance. CI results never establish EC2 source IP, host isolation, Atlas/R2 or public DNS/TLS.
