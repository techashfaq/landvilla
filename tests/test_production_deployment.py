"""Offline deployment boundary checks; Compose config never starts containers."""
import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("production_compose", ROOT / "scripts" / "check-production-compose.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class DeploymentConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix="compose-review-", dir=cache)
        cls.addClassCleanup(cls.directory.cleanup)
        work = Path(cls.directory.name)
        cls.api_env_file = work / "api.env"
        cls.api_env_file.write_text("\n".join([
            "MONGO_URL=mongodb://synthetic.invalid:27017/?tls=true", "DB_NAME=landvilla_prod",
            "CORS_ORIGINS=https://landvilla.in", "WEB_APP_ORIGINS=https://landvilla.in",
            "STORAGE_PROVIDER=cloudflare_r2", "S3_ENDPOINT=https://synthetic.r2.invalid",
            "S3_BUCKET=landvilla-property-media-prod", "S3_ACCESS_KEY_ID=synthetic", "S3_SECRET_ACCESS_KEY=never-print-secret",
            "IDENTITY_ENABLED=true", "OTP_HMAC_SECRET=synthetic-test-secret-at-least-32-characters",
            "GOOGLE_CLIENT_IDS=synthetic.apps.googleusercontent.com",
            # Compose environment must override unsafe env_file values.
            "FORWARDED_ALLOW_IPS=*", "TRUSTED_HOSTS=*", "SEED_ON_STARTUP=true",
            "ALLOW_LIVE_PAYMENTS=true", "RAZORPAY_KEY_SECRET=never-use-this-synthetic-key",
        ]) + "\n", encoding="utf-8")
        cls.env_file = work / "compose.env"
        cls.env_file.write_text("\n".join([
            f"LANDVILLA_ENV_FILE={cls.api_env_file.as_posix()}",
            "LANDVILLA_DOCKER_SUBNET=172.30.250.0/24", "LANDVILLA_WEB_PROXY_IP=172.30.250.10",
            "LANDVILLA_DOCKER_DYNAMIC_RANGE=172.30.250.128/25",
            "LANDVILLA_API_IMAGE=landvilla-api@sha256:" + "b" * 64,
            "LANDVILLA_WEB_IMAGE=landvilla-web@sha256:" + "c" * 64,
            "LANDVILLA_CADDY_IMAGE=caddy:2.11.9-alpine@sha256:" + "a" * 64,
            "LANDVILLA_INGRESS_TOKEN=" + "a1" * 32, "LANDVILLA_WEB_API_IP_KEY=" + "b2" * 32, "LANDVILLA_ACME_EMAIL=operator@example.invalid", "NEXT_PUBLIC_GOOGLE_WEB_CLIENT_ID=",
        ]) + "\n", encoding="utf-8")
        # Do not inherit operator interpolation values or local .env files.
        cls.environment = {name: value for name, value in os.environ.items()
                           if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "USERPROFILE", "HOME"}}
        cls.environment.update(COMPOSE_DISABLE_ENV_FILE="1", PYTHONDONTWRITEBYTECODE="1")
        cls.compose_binary = os.getenv("LANDVILLA_TEST_COMPOSE_BINARY")
        cls.model = checker.resolve_compose(cls.env_file, environment=cls.environment, compose_binary=cls.compose_binary)

    def rejected(self, mutate):
        model = copy.deepcopy(self.model)
        mutate(model)
        with self.assertRaises(checker.ConfigurationError):
            checker.validate_model(model)

    def test_resolved_production_configuration(self):
        checker.validate_model(self.model)

    def test_application_tags_require_explicit_prebuild_mode(self):
        model = copy.deepcopy(self.model)
        for service in ("api", "web"):
            model["services"][service]["image"] = "landvilla-" + service + ":synthetic-build"
        with self.assertRaises(checker.ConfigurationError):
            checker.validate_model(model)
        checker.validate_model(model, allow_build_tags=True)
        model["services"]["web"]["image"] = "landvilla-web:latest"
        with self.assertRaises(checker.ConfigurationError):
            checker.validate_model(model, allow_build_tags=True)

    def test_build_arguments_and_mounts_cannot_supply_secrets(self):
        self.rejected(lambda model: model["services"]["web"]["build"]["args"].update(OTP_HMAC_SECRET="synthetic"))
        self.rejected(lambda model: model["services"]["web"]["build"].update(context="https://unreviewed.invalid/repo"))
        self.rejected(lambda model: model["services"]["api"]["build"].update(secrets=["unexpected"]))
        for service in ("api", "web", "caddy"):
            with self.subTest(service=service):
                self.rejected(lambda model: model["services"][service].setdefault("volumes", []).append(
                    {"type": "bind", "source": "synthetic.env", "target": "/app/.env"}))
                self.rejected(lambda model: model["services"][service].update(secrets=["unexpected"]))

    def test_entrypoints_users_aliases_and_health_targets_cannot_bypass_review(self):
        for service in ("api", "web"):
            for key, value in (("command", ["unreviewed"]), ("user", "0"), ("entrypoint", ["unreviewed"])):
                with self.subTest(service=service, key=key):
                    self.rejected(lambda model: model["services"][service].update({key: value}))
        self.rejected(lambda model: model["services"]["web"]["networks"]["application"].update(aliases=["api"]))
        self.rejected(lambda model: model["services"]["web"]["healthcheck"].update(test=["CMD", "true"]))
        self.rejected(lambda model: model["services"]["api"].update(depends_on={"caddy": {"condition": "service_healthy"}}))

    def test_security_environment_overrides_env_file(self):
        api = self.model["services"]["api"]["environment"]
        self.assertEqual(api["SEED_ON_STARTUP"], "false")
        self.assertEqual(api["ALLOW_LIVE_PAYMENTS"], "false")
        self.assertEqual(api["RAZORPAY_KEY_SECRET"], "")
        self.assertEqual(api["TRUSTED_HOSTS"], "api,127.0.0.1")
        self.assertEqual(api["FORWARDED_ALLOW_IPS"], "172.30.250.10")

    def test_no_api_or_web_publication(self):
        for service in ("api", "web"):
            with self.subTest(service=service):
                self.rejected(lambda model: model["services"][service].update(
                    ports=[{"target": 8000, "published": "8000", "protocol": "tcp"}]))

    def test_only_caddy_publishes_http_and_https(self):
        self.rejected(lambda model: model["services"]["caddy"]["ports"].append(
            {"target": 2019, "published": "2019", "protocol": "tcp"}))

    def test_caddy_image_must_be_digest_pinned(self):
        self.rejected(lambda model: model["services"]["caddy"].update(image="caddy:2.10.2-alpine"))
        self.rejected(lambda model: model["services"]["caddy"].update(image="unreviewed/caddy@sha256:" + "a" * 64))

    def test_proxy_trust_must_equal_exact_web_address(self):
        for value in ("*", "172.30.250.0/24", "172.30.250.11", "web", "127.0.0.1", "172.30.250.10,172.30.250.11"):
            with self.subTest(value=value):
                self.rejected(lambda model: model["services"]["api"]["environment"].update(FORWARDED_ALLOW_IPS=value))

    def test_proxy_ip_requires_private_usable_network_membership(self):
        for value in ("172.30.250.0", "172.30.250.1", "172.30.250.128", "172.30.250.129", "172.30.250.255", "172.30.251.10", "8.8.8.8"):
            with self.subTest(value=value):
                self.rejected(lambda model: model["services"]["web"]["networks"]["application"].update(ipv4_address=value))
        self.rejected(lambda model: model["networks"]["application"]["ipam"]["config"][0].update(subnet="8.8.8.0/24"))

    def test_dynamic_range_is_canonical_private_child_with_capacity(self):
        for value in ("", "172.30.250.129/25", "172.30.251.0/25", "8.8.8.0/25",
                      "172.30.250.0/24", "172.30.250.128/30", "172.30.250.128/255.255.255.128"):
            with self.subTest(value=value):
                self.rejected(lambda model: model["networks"]["application"]["ipam"]["config"][0].update(ip_range=value))
        self.rejected(lambda model: model["networks"]["application"]["ipam"]["config"][0].pop("ip_range"))
        minimum = copy.deepcopy(self.model)
        minimum["networks"]["application"]["ipam"]["config"][0]["ip_range"] = "172.30.250.128/29"
        checker.validate_model(minimum)

    def test_production_dotenv_loading_is_disabled(self):
        self.rejected(lambda model: model["services"]["api"]["environment"].update(PYTHON_DOTENV_DISABLED="0"))

    def test_public_origin_internal_transport_and_hosts(self):
        for name, value in (("WEB_ORIGIN", "http://landvilla.in"), ("BACKEND_ORIGIN", "http://attacker.example:8000"),
                            ("BACKEND_TRANSPORT", "https"), ("HOSTNAME", "localhost")):
            with self.subTest(name=name):
                self.rejected(lambda model: model["services"]["web"]["environment"].update({name: value}))
        self.rejected(lambda model: model["services"]["api"]["environment"].update(TRUSTED_HOSTS="*"))
        for name in ("CORS_ORIGINS", "WEB_APP_ORIGINS"):
            with self.subTest(name=name):
                self.rejected(lambda model: model["services"]["api"]["environment"].update({name: "http://landvilla.in"}))

    def test_production_seed_and_payment_flags_cannot_enable(self):
        for name in checker.DISABLED_FEATURES:
            with self.subTest(name=name):
                self.rejected(lambda model: model["services"]["api"]["environment"].update({name: "true"}))
        self.rejected(lambda model: model["services"]["api"]["environment"].update(RAZORPAY_KEY_SECRET="synthetic"))

    def test_health_checks_use_only_loopback_liveness(self):
        expected = {"api": "http://127.0.0.1:8000/health", "web": "http://127.0.0.1:3000/health",
                    "caddy": "http://127.0.0.1:8080/health"}
        for name, url in expected.items():
            with self.subTest(name=name):
                probe = " ".join(self.model["services"][name]["healthcheck"]["test"])
                self.assertIn(url, probe)
                self.assertNotIn("/ready", probe)

    def test_caddy_only_routes_web_and_keeps_readiness_private(self):
        caddy = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
        self.assertIn("reverse_proxy web:3000", caddy)
        self.assertNotIn("api:8000", caddy)
        self.assertIn("health_uri /ready", caddy)
        self.assertIn("respond @probes 404", caddy)
        self.assertIn("bind 127.0.0.1", caddy)
        self.assertIn("redir https://landvilla.in{uri} 308", caddy)
        self.assertIn("header_up -Forwarded", caddy)
        self.assertIn("request_header -X-Forwarded-*", caddy)
        self.assertIn("header_up -X-Forwarded-For", caddy)
        self.assertIn("header_up X-Forwarded-Proto https", caddy)
        self.assertNotIn("trusted_proxies", caddy)
        self.assertNotIn("auto_https off", caddy)

    def test_backend_image_binds_container_interface_and_trusts_explicit_proxy(self):
        dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('"--host", "0.0.0.0"', dockerfile)
        self.assertIn('"--proxy-headers"', dockerfile)
        self.assertNotIn('"--forwarded-allow-ips", "*"', dockerfile)
        self.assertIn("USER app", dockerfile)
        ignore = (ROOT / "backend" / ".dockerignore").read_text(encoding="utf-8")
        self.assertEqual(ignore.splitlines()[0], "*")
        self.assertNotIn("!.env", ignore)

    def test_secrets_belong_only_to_api(self):
        for name in ("web", "caddy"):
            with self.subTest(name=name):
                self.rejected(lambda model: model["services"][name].setdefault("environment", {}).update(MONGO_URL="synthetic"))
        self.rejected(lambda model: model["services"]["web"]["environment"].update(UNEXPECTED_PROVIDER_SECRET="synthetic"))

    def test_service_name_cannot_be_overridden_to_external_host(self):
        self.rejected(lambda model: model["services"]["web"].update(extra_hosts={"api": "8.8.8.8"}))

    def test_hardening_and_health_probes_required(self):
        for name in ("web", "api", "caddy"):
            for key, value in (("read_only", False), ("cap_drop", []), ("healthcheck", {"disable": True}),
                               ("mem_limit", 0), ("privileged", True), ("network_mode", "host")):
                with self.subTest(service=name, setting=key):
                    self.rejected(lambda model: model["services"][name].update({key: value}))

    def test_cli_never_prints_resolved_environment(self):
        arguments = [sys.executable, str(ROOT / "scripts" / "check-production-compose.py"), "--env-file", str(self.env_file)]
        if self.compose_binary:
            arguments.extend(["--compose-binary", self.compose_binary])
        result = subprocess.run(arguments, cwd=ROOT, env=self.environment,
                                capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS production Compose declarations", result.stdout)
        self.assertNotIn("never-print-secret", result.stdout + result.stderr)
        self.assertNotIn("mongodb://", result.stdout + result.stderr)

    def test_docker_failures_do_not_print_stderr_or_config(self):
        failure = subprocess.CompletedProcess([], 1, stdout='{"secret":"never-print-secret"}',
                                              stderr="never-print-secret")
        with patch.object(checker.subprocess, "run", return_value=failure):
            with self.assertRaisesRegex(checker.ConfigurationError, "Compose interpolation or syntax") as caught:
                checker.resolve_compose(self.env_file)
        self.assertNotIn("never-print-secret", str(caught.exception))

    def test_missing_proxy_allocation_fails_compose_interpolation(self):
        text = self.env_file.read_text(encoding="utf-8")
        incomplete = Path(self.directory.name) / "incomplete.env"
        for name in ("LANDVILLA_WEB_PROXY_IP", "LANDVILLA_DOCKER_DYNAMIC_RANGE"):
            with self.subTest(name=name):
                incomplete.write_text("\n".join(line for line in text.splitlines()
                                                if not line.startswith(name + "=")), encoding="utf-8")
                with self.assertRaises(checker.ConfigurationError):
                    checker.resolve_compose(incomplete, environment=self.environment, compose_binary=self.compose_binary)


if __name__ == "__main__":
    unittest.main()
