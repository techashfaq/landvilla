"""Offline Compose review. Never prints resolved config, secrets, or Docker stderr.

This validates declarations, not actual Docker source addresses, routing, TLS or
provider access. It does not contact the Docker daemon or start any containers.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from production_runtime import validate_environment

PRIVATE_NETWORKS = tuple(ipaddress.IPv4Network(value) for value in
                         ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
DISABLED_FEATURES = ("SEED_ON_STARTUP", "SEED_DEMO_LISTINGS", "SEED_TEST_SESSIONS",
                     "ALLOW_LIVE_PAYMENTS", "GOOGLE_PLAY_BILLING_ENABLED", "REFUNDS_ENABLED")
PRIVATE_ENV = {"MONGO_URL", "DB_NAME", "S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID",
               "S3_SECRET_ACCESS_KEY", "OTP_HMAC_SECRET", "SMTP_PASSWORD",
               "TWILIO_AUTH_TOKEN", "RAZORPAY_KEY_SECRET"}


class ConfigurationError(RuntimeError):
    """Messages contain fixed check names only, never supplied configuration."""


def require(condition, check):
    if not condition:
        raise ConfigurationError(check)


def resolve_compose(env_file, *, environment=None, compose_binary=None):
    # Optional verified standalone binary permits exact-version, daemon-free review.
    executable = [str(Path(compose_binary).resolve())] if compose_binary else ["docker", "compose"]
    command = [*executable, "--env-file", str(Path(env_file).resolve()),
               "--file", str(ROOT / "deploy" / "compose.production.yml"),
               "config", "--format", "json"]
    if environment is None:
        environment = {k: v for k, v in os.environ.items() if k.upper() in
                       {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "HOME", "USERPROFILE"}}
        environment["COMPOSE_DISABLE_ENV_FILE"] = "1"
    try:
        result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                                text=True, encoding="utf-8", timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ConfigurationError("Compose configuration command unavailable") from None
    require(result.returncode == 0, "Compose interpolation or syntax")
    try:
        return json.loads(result.stdout)
    except (TypeError, ValueError):
        raise ConfigurationError("Compose JSON output") from None


def validate_model(model, *, allow_build_tags=False):
    """Validate a resolved Compose model without exposing its contents."""
    services = model.get("services", {})
    require(set(services) == {"caddy", "web", "api"}, "exact production services")
    networks = model.get("networks", {})
    require(set(networks) == {"application"}, "application network declaration")
    network = networks["application"]
    require(network.get("driver") == "bridge" and not network.get("external"),
            "owned bridge network")
    require(not network.get("enable_ipv6"), "IPv4 deployment network")
    allocations = network.get("ipam", {}).get("config", [])
    require(len(allocations) == 1, "one explicit IPv4 subnet")
    try:
        subnet_text = allocations[0]["subnet"]
        subnet = ipaddress.IPv4Network(subnet_text, strict=True)
        dynamic_text = allocations[0]["ip_range"]
        dynamic_range = ipaddress.IPv4Network(dynamic_text, strict=True)
        web_ip_text = services["web"]["networks"]["application"]["ipv4_address"]
        web_ip = ipaddress.IPv4Address(web_ip_text)
        gateway = ipaddress.IPv4Address(allocations[0].get("gateway", subnet.network_address + 1))
    except (KeyError, TypeError, ValueError, ipaddress.AddressValueError):
        raise ConfigurationError("canonical subnet, dynamic range, and web IPv4 address") from None
    require(str(subnet) == subnet_text and any(subnet.subnet_of(private) for private in PRIVATE_NETWORKS),
            "RFC1918 application subnet")
    require(gateway in subnet and gateway not in (subnet.network_address, subnet.broadcast_address),
            "usable bridge gateway")
    require(str(dynamic_range) == dynamic_text and dynamic_range.subnet_of(subnet) and
            dynamic_range != subnet and dynamic_range.num_addresses - 2 - int(gateway in dynamic_range) >= 4,
            "usable private child subnet for dynamic allocation")
    require(str(web_ip) == web_ip_text and web_ip in subnet and
            web_ip not in dynamic_range and web_ip not in (subnet.network_address, subnet.broadcast_address, gateway),
            "web proxy address within usable subnet")

    for name, service in services.items():
        require(service.get("read_only") is True, "read-only service filesystem")
        require(service.get("restart") == "unless-stopped", "service restart policy")
        require("ALL" in service.get("cap_drop", []), "dropped service capabilities")
        require("no-new-privileges:true" in service.get("security_opt", []),
                "no-new-privileges service boundary")
        require(not service.get("privileged") and not service.get("network_mode") and
                not service.get("pid") and not service.get("devices"),
                "no privileged or host service namespace")
        require(not service.get("extra_hosts") and not service.get("external_links"),
                "unmodified private service discovery")
        require(not service.get("secrets") and not service.get("configs") and
                not service.get("volumes_from") and not service.get("use_api_socket"),
                "no alternate secret or host mounts")
        require(set(service.get("networks", {})) == {"application"}, "service bridge membership")
        require(not (service["networks"]["application"] or {}).get("aliases"), "unmodified service aliases")
        require(float(service.get("cpus", 0)) > 0 and int(service.get("mem_limit", 0)) > 0 and
                int(service.get("pids_limit", 0)) > 0, "service resource limits")
        logging = service.get("logging", {})
        require(logging.get("driver") == "json-file" and
                logging.get("options", {}).get("max-size") == "10m" and
                logging.get("options", {}).get("max-file") == "3", "bounded service logs")
        image = service.get("image", "")
        immutable = bool(re.fullmatch(r"[^\s@]+@sha256:[a-f0-9]{64}", image))
        build_tag = bool(re.fullmatch(r"[^\s@]+:[A-Za-z0-9_.-]+", image)) and not image.endswith(":latest")
        require(immutable or (allow_build_tags and name != "caddy" and build_tag), "immutable release images")
        health = service.get("healthcheck", {})
        require(bool(health.get("test")) and not health.get("disable"), "service health probe")
        require(all(volume.get("target") != "/var/run/docker.sock" for volume in service.get("volumes", [])),
                "no Docker socket mount")
        if name != "caddy":
            require(not service.get("ports"), "unpublished web and API ports")
            require(not service.get("cap_add"), "unprivileged application capabilities")
            require(not service.get("volumes"), "no application bind mounts")
            require(not service.get("entrypoint") and not service.get("command"), "unchanged application entrypoints")
            require(service.get("user") == ("10001:10001" if name == "api" else "1000:1000"),
                    "non-root image runtime user")
        else:
            require(set(service.get("cap_add", [])) <= {"NET_BIND_SERVICE"}, "minimal ingress capability")
        if name != "api":
            require(not (set(service.get("environment", {})) & PRIVATE_ENV), "API-only private environment")

    caddy, web, api = (services[name] for name in ("caddy", "web", "api"))
    for name, service in (("api", api), ("web", web)):
        build = service.get("build", {})
        require(Path(build.get("context", "")).resolve() == ROOT / ("backend" if name == "api" else "web"),
                "fixed application build context")
        require(build.get("dockerfile", "Dockerfile") == "Dockerfile" and
                not any(build.get(key) for key in ("secrets", "ssh", "additional_contexts", "dockerfile_inline", "network")),
                "no alternate build secret or network inputs")
        require(set(build.get("args", {})) <= ({"NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID"} if name == "web" else set()),
                "public-only build arguments")
    require(not caddy.get("build") and not caddy.get("entrypoint") and
            caddy.get("command") == ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"],
            "reviewed ingress entrypoint")
    require(bool(re.fullmatch(r"(?:docker\.io/library/)?caddy(?::[a-zA-Z0-9_.-]+)?@sha256:[a-f0-9]{64}",
                              caddy.get("image", ""))), "digest-pinned official Caddy image")
    ports = caddy.get("ports", [])
    require(len(ports) == 2 and {(str(port.get("published")), port.get("target"), port.get("protocol"))
                                for port in ports} == {("80", 80, "tcp"), ("443", 443, "tcp")},
            "Caddy-only TCP 80 and 443 publication")
    api_env = api.get("environment", {})
    require(api_env.get("APP_ENV") == "production", "production API environment")
    require(api_env.get("PYTHON_DOTENV_DISABLED") == "1", "disabled production dotenv loading")
    require(api_env.get("FORWARDED_ALLOW_IPS") == web_ip_text, "exact web proxy trust address")
    require(api_env.get("TRUSTED_HOSTS") == "api,127.0.0.1", "internal API and probe hosts")
    require(all(api_env.get(name) == "false" for name in DISABLED_FEATURES), "disabled seeds and payments")
    require(all(api_env.get(name) == "" for name in
                ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET")),
            "disabled Razorpay credentials")
    require(api_env.get("CORS_ORIGINS") == "https://landvilla.in" and
            api_env.get("WEB_APP_ORIGINS") == "https://landvilla.in", "canonical HTTPS browser origin")
    try:
        validate_environment(api_env)
    except (RuntimeError, ValueError, KeyError, TypeError):
        raise ConfigurationError("backend production environment") from None
    expected_web = {"NODE_ENV": "production", "WEB_ORIGIN": "https://landvilla.in",
                    "BACKEND_ORIGIN": "http://api:8000", "BACKEND_TRANSPORT": "private-http",
                    "HOSTNAME": "0.0.0.0", "PORT": "3000", "CLIENT_IP_MODE": "signed-v1"}
    token = web.get("environment", {}).get("LANDVILLA_INGRESS_TOKEN", "")
    key = web.get("environment", {}).get("WEB_API_IP_KEY", "")
    require(bool(re.fullmatch(r"[a-f0-9]{64}", token)) and bool(re.fullmatch(r"[a-f0-9]{64}", key)) and token != key,
            "distinct dedicated ingress identity credentials")
    require(token != "d"*64 and key != "e"*64, "no public rehearsal identity credentials")
    require(caddy.get("environment", {}).get("LANDVILLA_INGRESS_TOKEN") == token and
            api_env.get("WEB_API_IP_KEY") == key and api_env.get("DEPLOYMENT_TIER") == "production",
            "scoped authenticated identity hops and production target")
    require("LANDVILLA_INGRESS_TOKEN" not in api_env, "no ingress credential in API")
    require(all(web.get("environment", {}).get(name) == value for name, value in expected_web.items()),
            "explicit web private transport and public HTTPS origin")
    require(set(web.get("environment", {})) <= set(expected_web) | {
                "NEXT_TELEMETRY_DISABLED", "NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID", "LANDVILLA_INGRESS_TOKEN", "WEB_API_IP_KEY"} and
            set(caddy.get("environment", {})) == {"ACME_EMAIL", "LANDVILLA_INGRESS_TOKEN"}, "explicit scoped web and ingress environment")
    require(any(str(item).startswith("/app/.next/cache:") for item in web.get("tmpfs", [])),
            "writable bounded Next cache")
    require(web.get("depends_on", {}).get("api", {}).get("condition") == "service_healthy" and
            caddy.get("depends_on", {}).get("web", {}).get("condition") == "service_healthy" and
            not api.get("depends_on"), "acyclic liveness startup dependencies")
    for name, service, port in (("api", api, 8000), ("web", web, 3000), ("caddy", caddy, 8080)):
        require(f"http://127.0.0.1:{port}/health" in " ".join(service["healthcheck"]["test"]) and
                "/ready" not in " ".join(service["healthcheck"]["test"]), "loopback-only liveness target")
    caddy_mounts = {item["target"]: item for item in caddy.get("volumes", [])}
    require(set(caddy_mounts) == {"/etc/caddy/Caddyfile", "/data", "/config"} and
            caddy_mounts.get("/etc/caddy/Caddyfile", {}).get("type") == "bind" and
            Path(caddy_mounts.get("/etc/caddy/Caddyfile", {}).get("source", "")).resolve() == ROOT / "deploy/Caddyfile" and
            caddy_mounts.get("/etc/caddy/Caddyfile", {}).get("read_only") is True and
            all(caddy_mounts.get(path, {}).get("type") == "volume" for path in ("/data", "/config")),
            "read-only Caddy configuration and persistent TLS storage")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True, help="Access-controlled Compose interpolation file")
    parser.add_argument("--compose-binary", help="Verified standalone Compose binary (default: docker compose)")
    parser.add_argument("--allow-build-tags", action="store_true", help="Pre-build review only; never release acceptance")
    args = parser.parse_args()
    try:
        validate_model(resolve_compose(args.env_file, compose_binary=args.compose_binary), allow_build_tags=args.allow_build_tags)
    except ConfigurationError as exc:
        print(f"BLOCKED {exc}")
        return 1
    except (KeyError, TypeError, ValueError, AttributeError):
        print("BLOCKED unexpected Compose model shape")
        return 1
    print("PASS " + ("pre-build declarations ONLY; NOT a release gate" if args.allow_build_tags else
                    "production Compose declarations; resolved values withheld"))
    print("UNVERIFIED runtime proxy source IP, subnet overlap, containers, TLS, and provider acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
