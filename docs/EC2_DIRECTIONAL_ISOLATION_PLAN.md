# EC2 directional isolation — investigation and validation gate

Updated 11 November 2026 using the owner's verified EC2/AWS inventory. **PLAN ONLY; ISOLATION NOT APPLIED OR PROVEN ON EC2.**

Repository baseline: dev, a1d58b33a23c869617975e70875e922bf75bd11f. No host connection, AWS API call, container deployment, firewall mutation, migration or provider write was performed. Existing Compose remains an incomplete deployment artifact, not a strict isolation implementation. Local Docker Desktop being unavailable does not relax this gate.

## Confirmed inventory, proposed design and unverified behavior

Evidence labels used below:
- **CONFIRMED (owner inventory):** supplied verified observations; not independently re-collected during this documentation task.
- **PROPOSED:** intended design, not installed or approved for execution.
- **UNVERIFIED:** missing evidence or acceptance test; never a passing security result.

| Item | CONFIRMED (owner inventory) |
|---|---|
| Host | Amazon Linux 2023, kernel 6.18 |
| Docker | Engine 25.0.18; generated iptables-compatible chains; LiveRestore=false |
| Firewall tools/path | iptables v1.8.8 (nf_tables); IPv4 FORWARD policy DROP; DOCKER-USER contains only RETURN |
| Host policies | IPv4 and IPv6 INPUT/OUTPUT policies ACCEPT; this does not establish the contents/effect of every explicit rule |
| Default Docker bridge | 172.17.0.0/16; ICC enabled; masquerading enabled; bridge IPv6 disabled |
| Current workloads | No running containers and no custom Docker networks; stopped containers/restart policies are not covered by this observation |
| AWS location/network | Mumbai; VPC 172.31.0.0/16; subnets 172.31.0.0/20, 172.31.16.0/20 and 172.31.32.0/20 |
| AWS inbound | TCP 80/443 from 0.0.0.0/0; TCP 22 only from the EC2 Instance Connect prefix list |
| AWS outbound | All IPv4 traffic to 0.0.0.0/0 |
| DNS | EC2 resolver 172.31.0.2; host resolution works |
| IPv6 | No VPC IPv6 CIDR or EC2 global IPv6; Docker default bridge IPv6 disabled |
| Persistence | No firewall persistence service/configuration found |
| Reverse-path filtering | rp_filter all=0, default=2, ens5=2, docker0=2 |

**Conclusions limited to this inventory:** use the existing iptables-compatible Docker integration as the design baseline. DOCKER-USER's current RETURN adds no LANDVILLA restrictions. ICC enabled is not directional isolation; FORWARD DROP does not invalidate Docker's explicit allow paths. AWS inbound restrictions do not enforce container-to-container or host-local directions. AWS outbound is currently unrestricted IPv4, not the restricted egress policy proposed below. Do not change rp_filter values; their effect on the chosen multi-interface routing must be tested.

**UNVERIFIED:** complete explicit IPv4/IPv6 rules and jump order; br_netfilter/bridge hook traversal; IP-forward sysctls; IPv6 link-local reachability; stopped-container restart behavior; effective Docker unit dependencies; firewalld/other rule ownership; full route/policy-routing/address-pool inventory; VPC peering/VPN/TGW/prefix-list/Atlas private routes; and every proposed connectivity, persistence and rollback outcome. No security test is inferred from the absence of running containers.

### Documented capability context (not additional host observations)

Amazon Linux 2023's current package catalogue includes nftables, iptables-nft and firewalld packages. Availability is not evidence that a particular AMI installed/enabled them. Record the actual OS release, kernel, package versions and active services. [AWS package catalogue](https://docs.aws.amazon.com/linux/al2023/release-notes/all-packages-AL2023.12.html)

The supplied Engine 25.0.18 and generated chains establish the iptables-compatible design path; do not migrate to Docker's later native nftables backend for this task. Keep Docker firewall/NAT management enabled. [Docker firewall overview](https://docs.docker.com/engine/network/packet-filtering-firewalls/)

| Observed Docker backend | Candidate integration, subject to host tests |
|---|---|
| iptables-compatible Docker chains: CONFIRMED | PROPOSED: LANDVILLA-owned chain reached from DOCKER-USER before Docker accepts forwarding. Exact jump ordering, same-bridge traversal and counters remain UNVERIFIED. |
| Native nftables Docker backend: not the supplied configuration | Not selected. A future migration would require a new design and approval, including separate tables/hooks and priority analysis. |
| Additional/mixed firewall managers or unexpected packet paths: UNVERIFIED | Stop implementation if found; reconcile rule ownership before applying anything. |

`iptables --version` reporting nf_tables identifies the CLI compatibility implementation, not Docker's selected native backend. Configuration, daemon arguments, version and observed rules must agree. An old DOCKER-USER chain can remain after a backend change, so existence alone is insufficient. [Docker iptables](https://docs.docker.com/engine/network/firewall-iptables/), [Docker native nftables](https://docs.docker.com/engine/network/firewall-nftables/)

## Gate 1: read-only host evidence

The supplied inventory satisfies the baseline OS, Engine, bridge, VPC and policy observations above. Do not repeat it unnecessarily. An authorized operator must collect only missing evidence or recheck facts that have changed before implementation. Commands below are a reference for read-only collection; this task has NOT executed them remotely. Use a controlled terminal, not a public transcript. Rule comments, addresses, hostnames and daemon arguments may be private; return only a redacted summary. Never collect environment files, container Config.Env, credential files, metadata credentials or unredacted Compose output.

```sh
cat /etc/os-release
uname -r
rpm -q docker containerd iptables iptables-nft nftables firewalld
docker version --format '{{.Server.Version}}'
docker info --format '{{json .SecurityOptions}}'
docker info --format '{{.Swarm.LocalNodeState}}'
iptables --version
ip6tables --version
nft --version
systemctl is-active docker firewalld nftables iptables
systemctl is-enabled docker firewalld nftables iptables
sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding
sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables
ip -json address show
ip -json route show table all
ip -6 -json route show table all
ip -json rule show
docker network ls
```

Missing packages/sysctls are findings, not permission to install packages or load kernel modules. Inspect only relevant, version-supported daemon configuration fields (`iptables`, `ip6tables`, `ip-forward`, `ipv6`, `live-restore`, `default-address-pools`) with a whitelist JSON reader. Do not add options from newer Docker releases to Engine 25. Inspect the effective dockerd command privately for flags overriding configuration. Do not dump arbitrary daemon configuration, systemd Environment/EnvironmentFile values or command-line secrets. Include stopped containers' names/state/restart policy using a narrow projection, never Config.Env.

With authorized sudo, privately inspect `iptables -S FORWARD`, `iptables -S DOCKER-USER`, `iptables -t nat -S`, their IPv6 equivalents, and `nft list ruleset`. Record ownership, hooks, priorities, bridge traversal and existing accept/drop paths. Review firewalld zones/policies if active. No flush, insert, restore, reload or service restart at this stage.

For each existing Docker network, inspect only Name, Driver, Internal, EnableIPv6, IPAM.Config and Options. Do not inspect container environments. Determine bridge names, endpoint addresses, published port bindings and all host-facing interfaces. Confirm whether traffic traverses bridge hooks, routed forward hooks, or both. A plan limited to routed FORWARD is insufficient until same-bridge packets are demonstrated to hit the intended enforcement point.

## Gate 2: subnet and identity allocation

The supplied VPC/subnets, lack of VPC IPv6 and default Docker bridge are CONFIRMED. Final allocation approval remains pending. Obtain missing read-only evidence for effective route tables, policy routes, peering, Transit Gateway/VPN routes, managed prefix lists, Atlas private-endpoint/peering ranges and Docker address pools. Host routes alone do not reveal the complete VPC topology. AWS routes treat IPv4 and IPv6 separately. [VPC route tables](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-route-tables.html)

Compare candidate private Docker CIDRs pairwise with every allocated/local/reachable network using CIDR overlap calculations, not string comparison. Treat default routes as reachability information rather than claiming every candidate overlaps 0.0.0.0/0. Inspect more-specific routes and policy routing. Reserve the approved allocations in deployment documentation; recheck immediately before deployment and after network changes.

PROPOSED deterministic IPv4 assignments, not created or reserved on the host:

| Segment / proposed bridge name | CIDR / gateway | Container addresses | Purpose |
|---|---|---|---|
| edge_web / lv-edge-web | 172.28.240.0/28; gateway .1 | Caddy .2; web .3 | Internal bridge; Caddy -> web TCP 3000 only |
| web_api / lv-web-api | 172.28.240.16/28; gateway .17 | web .18; api .19 | Internal bridge; web -> api TCP 8000 only |
| caddy_egress / lv-caddy-out | 172.28.240.32/28; gateway .33 | Caddy .34 | Published TCP 80/443 and controlled ACME/DNS egress |
| api_egress / lv-api-out | 172.28.240.48/28; gateway .49 | api .50 | Controlled Atlas/R2 and approved provider/DNS egress |

All abbreviated addresses above have prefix 172.28.240. Proposed web port 3000 is container-internal; local development port 19006 stays unchanged. Arithmetic comparison performed locally confirms these four candidate CIDRs are mutually disjoint and do not overlap the supplied 172.17.0.0/16, 172.31.0.0/16 or three VPC subnets. **UNVERIFIED:** overlap with any unsupplied routes, address pools or connected networks; actual bridge names/gateway behavior, route selection, NAT and source address selection. Do not call this full subnet validation.

PROPOSED: web has no independent general internet-egress network; it reaches API on web_api. Caddy and API use distinct external-capable bridges. All four require firewall coverage; network separation is not the enforcement mechanism. The exact web API source IP must be observed as 172.28.240.18 before setting FORWARDED_ALLOW_IPS to that single address. Proposed TRUSTED_HOSTS is api,127.0.0.1; acceptance of Host api:8000 must be tested. Do not add other hosts without a demonstrated need. No IP is approved for runtime use by this document.

Every interface/address of a multi-homed service must be covered, including egress interfaces. Internal-only bridges cannot alone provide Atlas/R2 internet access; the final egress design must retain NAT/routing without creating an unfiltered alternate path. Pin bridge names and service endpoint addresses after collision checks. No container gets host networking, Docker socket, NET_ADMIN, NET_RAW or privileged mode. Host administrators/Docker administrators remain trusted; this is not protection against root controlling the host.

## Gate 3: policy design (requirements, not executable firewall rules)

Apply a narrowly scoped LANDVILLA policy without changing unrelated host forwarding. Use validated service identity/interface matches, not source IP alone. Preserve Docker-owned NAT and connection tracking. Do not globally flush tables or set a host-wide default policy as a shortcut.

| Initiator | Destination | Required result for NEW connection |
|---|---|---|
| Internet | Caddy published TCP 80/443 | Allow; HTTP redirects to HTTPS |
| Caddy | web TCP 3000 (proposed) | Allow |
| web | api TCP 8000 | Allow |
| api | web, on every interface/port | Deny |
| api | Caddy, on every interface/port | Deny |
| Caddy | api | Deny |
| Internet/VPC peers/unrelated containers | web/api directly | Deny |
| web/api | host/public address hairpin back into protected services | Deny bypass paths |
| Any service | Other LANDVILLA service/port not explicitly allowed | Deny |

UDP 443/HTTP3 is not included by default; confirm if needed. Administrative host access is a separate existing policy, not a public application port. Do not lock out SSH/SSM or recovery access while restricting application traffic.

### Host-local bypass coverage — PROPOSED, all paths UNVERIFIED

DOCKER-USER forwarding policy alone must not be treated as host INPUT/OUTPUT protection. Host-initiated connections to container addresses and container connections terminating on bridge gateways or host interfaces need separate scoped analysis/enforcement. The confirmed ACCEPT INPUT/OUTPUT policies make this an explicit requirement; full rule contents remain unverified.

- Host -> web/api: deny ordinary application access from host processes by default. Permit only separately approved, narrowly scoped diagnostics if needed. Run liveness probes inside each container's loopback namespace, not through a broad host exception. Root/Docker operators remain a trusted recovery boundary.
- Containers -> host: deny host services, bridge-gateway listeners, Docker control endpoints and metadata/credential endpoints unless an approved dependency requires a narrowly defined exception. Preserve necessary upstream DNS through the observed resolver path. No Docker socket mounts.
- API -> Caddy/web: test every container endpoint and host private/public address, published 80/443 hairpin path, domain resolution and IPv6/link-local alias. A route through the host must not evade the same prohibition. Identify INPUT/OUTPUT/FORWARD/NAT traversal for each actual path before writing rules.
- Internet/VPC -> container IPs: test direct routes as well as published addresses. The AWS rules and lack of published web/api ports are defense layers, not proof of the host isolation policy. The host's public/private interface addresses and relevant route tables still need private inventory.
- Validate interface/source binding and anti-spoofing assumptions with dropped container capabilities. Do not rely on loose rp_filter as an access-control mechanism or change it to strict mode without routing tests.

Permit reply traffic for allowed established connections; API responses to web are not API-initiated sessions. Scope connection-state handling so it does not perpetuate pre-existing prohibited sessions indefinitely. First activation must occur in a controlled maintenance/test window without such sessions; any targeted conntrack cleanup needs separate approval. Do not globally flush conntrack. Preserve required ICMP/error handling and TCP/UDP DNS, including Docker embedded DNS and its upstream path. Allow container-local loopback health checks without adding public readiness access.

Map NAT stage explicitly: published destination addresses may already be translated at the user filtering hook; match original destinations through conntrack only where actually necessary and tested. Block API-to-web/Caddy via container IP, host gateway, private/public host IP, service DNS, public domain and IPv6. Native nftables bridge-family enforcement or br_netfilter-dependent traversal must be chosen from observed kernel behavior, never assumed. Account for IPv6 neighbor discovery if enabled; otherwise verify no active container IPv6 bypass. Do not change host IPv6 blindly.

Outbound API dependency inventory must include Atlas SRV/TXT DNS and the actual resolved members/ports, R2 HTTPS, and enabled authentication/SMTP/provider services. Do not freeze Atlas or CDN addresses from one DNS answer. Decide approved dynamic egress policy using DNS/private connectivity and provider requirements; broad TCP 443 egress alone is not strict destination allowlisting. Explicitly deny lateral and host-hairpin destinations before any general outbound allowance. Review IMDS/link-local access without breaking the selected credentials mechanism; never probe credential endpoints for this investigation. No database authentication, writes, provider requests or uploads are needed for initial TCP/TLS reachability testing.

### DNS and outbound acceptance — PROPOSED

Host DNS via 172.31.0.2 is CONFIRMED; DNS from the proposed container networks is UNVERIFIED. Test Docker service-name resolution and the embedded resolver's actual upstream packet path. Permit only the observed required TCP/UDP 53 path to the approved resolver; do not add a blanket VPC allowance. Verify large DNS replies/TCP fallback and Atlas SRV/TXT lookups. Do not assume every DNS packet traverses DOCKER-USER or has a container source address after translation.

Caddy needs approved DNS and ACME issuer egress; API needs approved DNS, actual Atlas transport ports and R2 HTTPS. Inventory Google/SMTP/other enabled providers separately. Keep payments/refunds/billing disabled as currently required; do not enable them to test connectivity. A reviewed endpoint-update mechanism or approved egress gateway policy is required for dynamic provider addresses. Failure to refresh approved endpoints must fail closed with an operational alert, not open all destinations. Egress mechanism, allowlist, update behavior and DNS-bypass/exfiltration controls are UNVERIFIED and require approval. The existing AWS allow-all IPv4 outbound rule is unchanged and does not satisfy this proposed policy.

### IPv4 and IPv6 — confirmed baseline, unverified enforcement

PROPOSED: keep LANDVILLA container networks IPv4-only; do not enable VPC, Docker or published IPv6. The confirmed lack of global IPv6 is not proof that link-local/loopback paths are absent. Inspect container/bridge IPv6 addresses and host IPv6 rules/listeners after an approved test deployment; test unintended link-local paths if present. Preserve host IPv6 loopback and necessary existing management behavior. IPv6 INPUT/OUTPUT ACCEPT is a confirmed policy observation, not a reason to ignore IPv6. IPv6 FORWARD policy and any explicit IPv6 rules are UNVERIFIED. Any later IPv6 enablement requires equivalent directional filtering, subnet checks and full re-acceptance before publication.

Kernel documentation distinguishes routed and bridged filtering: ordinary iptables and nftables ip/inet hooks cannot simply be assumed to cover bridge-forwarded packets. This is why same-bridge counter evidence is mandatory. [Linux bridge filtering](https://docs.kernel.org/networking/bridge.html), [nftables bridge family](https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering)

## Gate 4: persistence, restart safety and recovery design

Store only LANDVILLA-owned policy/configuration in root-owned versioned files. Validate syntax offline, stage a replacement without a permissive flush interval, and retain a last-known-good scoped policy. Do not save/replay Docker's entire transient ruleset as the persistence mechanism.

A boot-time prerequisite must establish a fail-closed guard before workloads can become reachable. The installer must reconcile Docker-dependent chains after Docker initialization without removing that guard. A simple service ordered After=docker.service or an ExecStartPost hook alone does NOT prove protection: Docker may restore containers first. **CONFIRMED:** LiveRestore=false and no persistence configuration found. Keep LiveRestore=false; this does not prove restart safety. Inventory stopped-container restart policies before any implementation. Do not enable unrestricted restart policies until startup ordering is proven. A future live-restore change needs separate review. [Docker live restore](https://docs.docker.com/engine/daemon/live-restore/)

PROPOSED lifecycle, not systemd configuration: (1) load a scoped pre-Docker fail-closed guard that does not depend on Docker-created chains; (2) start Docker while preserving that guard; (3) reconcile the LANDVILLA chain and verified DOCKER-USER jump; (4) validate endpoints, policy and counters; (5) allow the separately gated workload startup/publication. Exact pre-Docker hooks and persistence tool are UNVERIFIED and must be proven compatible with the installed iptables-nft path before implementation. Do not restore Docker-owned NAT chains from an old snapshot. Do not assume a generic nftables service is appropriate simply because iptables reports nf_tables.

On policy-load failure, missing chain, unexpected network/address, or failed reconciliation, application startup/publication must remain blocked. Reboot and Docker restart must re-enter this sequence without a permissive interval. Future updates must replace only owned rules atomically where supported and tested; no global flush. Rules must remain root-owned, versioned and idempotent. Health status alone must never authorize bypassing the guard.

Use systemd dependencies for orchestration only after observing the installed unit behavior; ordering and requirement dependencies are different. Policy validation failure must leave publication/workloads gated, not silently skip protection. Test reconciliation after Docker restart, host reboot, network recreation and any active firewall-manager reload. Never assume an existing chain will survive all of them. [systemd ordering](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)

Before any future approved application: establish independent recovery access and a timed, scoped rollback to known-good policy. Retain a second session. Rollback must not restore unrestricted public application exposure: withdraw/gate publication first if protection cannot be restored. Never restore a whole historical host ruleset over new Docker state. No systemd units, rollback jobs or firewall files are installed by this plan.

## Gate 5: actual-host acceptance protocol

Requires separate authorization for isolated test workloads and firewall application. Use nonproduction images/configuration without real accounts, documents or provider secrets. Do not use production database writes to test connectivity. The following matrix is a test specification, NOT an executed result.

1. Establish positive controls: a known listening test endpoint on each target; verify its health locally and from an allowed source. A refused socket/no listener is NOT proof of firewall blocking.
2. Test each allowed direction with a fresh TCP connection and HTTP response where applicable. Test each denied direction with the same known listening destination from the prohibited source. Use bounded timeouts and capture only outcome, port and rule counters, not payloads or private values.
3. Correlate denied probes with policy counters or a tightly scoped metadata-only trace. DNS failure or an upstream security-group denial cannot demonstrate the host firewall rule works.
4. Run probes from Caddy, web, API, an unrelated container, a VPC peer, and an external host. Use observed network-namespace/container identities; do not guess names or addresses. Test all alternate interfaces, same-bridge traffic, hairpin paths and IPv6 if enabled.
5. Verify established web-to-API responses, keep-alive and reconnects while API-initiated NEW connections remain blocked. Verify container DNS for services and external SRV/TXT records. Verify Atlas/R2 TCP/TLS reachability without credentials or writes; full application readiness remains a separate controlled acceptance step.
6. Verify backend scheme handling: only the exact web IP can influence Uvicorn proxy scheme; forged incoming forwarding headers are discarded by web. Internal Host `api:<port>` must be accepted while unrelated hosts are rejected. Caddy forwards only to web. Browser Origin/CSRF/cookie checks must still pass safely in isolated tests.
7. Repeat the matrix during and after controlled Docker restart, container restart, network recreation, firewall reload and reboot. Probe continuously through transitions; a single successful forbidden NEW connection fails acceptance. Exercise failed policy-load recovery and timed rollback. These operations are NOT authorized by this investigation.
8. Record host/Engine/kernel versions, actual backend, rule digest, approved network inventory, test results/counters, reboot/restart evidence and reviewer sign-off. Only then claim strict isolation and proceed to an independently approved deployment.

### Required path-specific tests — all UNVERIFIED / NOT RUN

| Test class | Acceptance evidence |
|---|---|
| Same bridge edge_web | Caddy -> web:3000 succeeds; web -> a known listening Caddy test endpoint is blocked with owned-rule counter evidence. Test IP and service DNS. |
| Same bridge web_api | web -> api:8000 succeeds; API -> known listening web:3000 is blocked. Confirm br_netfilter/hook traversal; FORWARD DROP alone is insufficient evidence. |
| Cross-network | Caddy -> both API addresses, API -> both Caddy addresses, API -> both web addresses, and unrelated test container -> web/api all fail at the intended policy boundary. Check gateway/alternate-route paths too. |
| Host-originated/terminated | Host -> web/api and containers -> forbidden host listeners are blocked by the appropriate scoped hook; approved management and container-loopback health checks still work. |
| NAT/hairpin/public | External TCP 80/443 reaches only Caddy; direct web/API access is blocked. API cannot reach Caddy/web through host private/public IP or public domain. Distinguish security-group rejection from host-firewall rejection. |
| Replies and DNS | Allowed request/reply, keep-alive, reconnect, DNS UDP/TCP fallback, SRV/TXT and approved non-mutating provider TCP/TLS probes pass. No stored credentials or request bodies in evidence. |
| IPv6 | No unintended IPv6 listener/publication/route; any available link-local path cannot bypass the policy. Test absence as well as explicit blocks. |
| rp_filter / routing | Correct source interface on each allowed flow; no unexpected reverse-path drops or asymmetric-route workaround that bypasses filtering. Existing values remain unchanged unless separately approved. |

### Failure, restart and rollback acceptance — all UNVERIFIED / NOT RUN

- Cold reboot with intended restart policies: continuously probe forbidden paths from the first moment target listeners become available. No forbidden connection may succeed before policy installation.
- Docker stop/start and restart with LiveRestore=false: positive paths recover only under the policy; forbidden paths stay blocked. Also test container recreation with the pinned addresses, policy reload and network recreation.
- Deliberately invalid candidate policy, absent owned chain/jump, stale IP assignment, occupied CIDR and failed persistence service: fail closed and report the error. No automatic switch to an unfiltered network or permissive rules.
- Scoped rule replacement: no gap during transition; established allowed sessions behave as documented; disallowed pre-existing sessions are handled under separately approved maintenance procedures.
- Timed rollback drill: confirm independent recovery and an active second session through the existing approved administration path before any change. Restore only the owned known-good policy; keep applications unpublished/stopped if no previously validated policy exists. In this initial inventory there is no verified LANDVILLA isolation policy to roll back to, so the safe fallback is no reachable workloads, not the current RETURN-only state with workloads exposed.
- Validate recovery after operator disconnect, installer interruption and reboot during installation. Record durable policy version and startup dependency evidence. SSM/serial-console availability and exact recovery procedure remain UNVERIFIED; do not assume they are available or widen TCP 22 access.

## Implementation sequence after evidence is available

The backend-specific design baseline is now Engine 25.0.18 with iptables-nft-compatible Docker chains. First close the missing packet-path, rule-order, routing and recovery evidence, then prepare a scoped firewall design and isolated test harness. Only after separate approval prepare/apply three-service Compose/Caddy/web Docker artifacts and persistence units using the approved assignments. Set Uvicorn's FORWARDED_ALLOW_IPS to the observed exact web endpoint; preserve HTTPS enforcement and health exceptions. Update all server-side web transport paths, not just the browser proxy. Internal HTTP must be restricted to the explicit deployment backend origin while public WEB_ORIGIN stays HTTPS. None of these code/runtime changes is authorized by this documentation task.

Separately resolve existing application ingress compatibility: the web proxy currently rejects native Bearer authentication and does not expose payment webhooks. Routing all traffic exclusively through that proxy does not automatically support Android API access or authenticated provider callbacks. Do not broaden route/auth policy or bypass web until a dedicated, tested design is approved. These are deployment blockers, not reasons to weaken firewall isolation.

## Explicit prerequisites and approval gates

1. **Inventory gate — partially satisfied:** accept the confirmed inventory above; obtain only missing rule ordering/bridge traversal, routes/address pools, stopped-container policies and recovery access evidence. No host writes.
2. **Design approval — pending:** approve candidate CIDRs after full overlap review, web port 3000, all endpoint identities, host INPUT/OUTPUT restrictions, DNS/provider egress and IPv6 policy. Confirm that existing administration remains available.
3. **Implementation approval — pending:** review exact version-compatible rule files, ownership, atomic replacement, pre-Docker guard, systemd dependencies and recovery procedure. No executable firewall rules are included here; no Docker backend migration is proposed.
4. **Controlled host-test approval — pending:** authorize isolated nonproduction listeners/test containers, scoped firewall application, negative probes and later disruptive reboot/restart/rollback drills. Read-only inventory is not authorization for these actions. No production database, R2 or billing changes.
5. **Acceptance gate — pending:** every required allowed/blocked path and transition passes with positive controls and policy evidence. Unexpected success or an untraceable path blocks deployment; retain isolation as UNPROVEN until then.
6. **Deployment approval — pending and separate:** address proxy/Android/webhook compatibility, health checks, secrets and release prerequisites, then obtain explicit production deployment approval. No AWS/DNS changes, migrations, commits or pushes are authorized by this plan update.

**Stop point:** host/backend and supplied VPC facts are confirmed by the owner, and candidate subnet arithmetic was checked locally. Packet-path enforcement, complete overlap safety, persistence, rollback and runtime connectivity remain UNVERIFIED. Only this document has changed; isolation is not proven. The next step is to close the missing read-only evidence and approve a concrete design before any host modification or test deployment.
