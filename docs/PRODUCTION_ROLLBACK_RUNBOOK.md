# Rollback and failed startup

**Known-good rollback target: not yet established. Rollback execution: NOT TESTED.** The old vulnerable dependency pins or API-only Compose file are not automatically safe rollback targets.

Before deployment retain a clean prior checkout, configuration checksums, immutable API/Web/Caddy digests, compatible external settings, backup/recovery point and DB/index/media compatibility decision. Keep Caddy data/config volumes. A same-image restart is not a rollback test.

On failed acceptance, stop public ingress first using the exact current project/file/settings, then stop application services with their40-second grace:

```sh
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml stop caddy
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME="$HOME" docker compose --env-file /etc/landvilla/compose.env -f deploy/compose.production.yml stop web api
```

Use the retained reviewed prior checkout and `/etc/landvilla/compose.previous.env`, retaining the same project identity and TLS volumes. Validate with its checker, compare immutable artifact IDs and environment compatibility, start API/Web privately, verify readiness/trust, then restore Caddy only after approval and acceptance. Never run a blind checkout/reset over user work.

No DB restore, migration reversal, index drop, object deletion, `down -v`, volume removal, broad prune, HTTPS disablement or proxy trust expansion is part of application rollback. Additive indexes/data and R2 metadata must remain compatible with the old application; otherwise leave ingress stopped and design a separate recovery. Production restore needs independent approval and evidence. No known-good release means stop and investigate, not roll back to an unverified historical baseline.

Rehearsal cleanup applies only to the labelled disposable project in ISOLATED_REHEARSAL_RUNBOOK.md. Network/firewall policy changes have their own approved rollback and must not be mixed into application rollback.
