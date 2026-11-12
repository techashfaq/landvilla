"""Native Caddy adapter/header checks with loopback-only synthetic upstreams.

Set CADDY_BINARY to a verified Caddy binary. No Docker, ACME, production listener,
provider, credential, or real application is started by this test.
"""
import copy
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


def handlers(value):
    if isinstance(value, dict):
        if "handler" in value:
            yield value
        for item in value.values():
            yield from handlers(item)
    elif isinstance(value, list):
        for item in value:
            yield from handlers(item)


class Echo(BaseHTTPRequestHandler):
    ready = True

    def do_GET(self):
        body = json.dumps(dict(self.headers)).encode()
        self.send_response(200 if self.path != "/ready" or Echo.ready else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", "__Host-lv_session=synthetic; Secure; HttpOnly; Path=/; SameSite=Lax")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@unittest.skipUnless(os.getenv("CADDY_BINARY"), "Set CADDY_BINARY for native loopback Caddy checks")
class CaddyConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = ROOT / ".cache"
        cache.mkdir(exist_ok=True)
        cls.directory = tempfile.TemporaryDirectory(prefix="caddy-review-", dir=cache)
        cls.addClassCleanup(cls.directory.cleanup)
        work = Path(cls.directory.name)
        environment = {name: value for name, value in os.environ.items()
                       if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}}
        environment.update(LANDVILLA_INGRESS_TOKEN="d"*64, ACME_EMAIL="operator@example.invalid", XDG_DATA_HOME=str(work / "data"),
                           XDG_CONFIG_HOME=str(work / "config"), TEMP=str(work), TMP=str(work), HOME=str(work))
        binary = str(Path(os.environ["CADDY_BINARY"]).resolve())
        adapted = subprocess.run([binary, "adapt", "--config", str(ROOT / "deploy/Caddyfile"),
                                  "--adapter", "caddyfile"], env=environment,
                                 capture_output=True, text=True, timeout=20, check=True)
        cls.production = json.loads(adapted.stdout)
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Echo)
        threading.Thread(target=cls.upstream.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.upstream.server_close)
        cls.addClassCleanup(cls.upstream.shutdown)
        cls.server = next(server for server in cls.production["apps"]["http"]["servers"].values()
                          if ":443" in server["listen"])
        # Copy the actual production route/header handlers. Only listener/TLS and
        # upstream and probe timings are replaced for an isolated HTTP unit harness.
        route_server = copy.deepcopy(cls.server)
        for handler in handlers(route_server):
            if handler.get("handler") == "reverse_proxy":
                handler["upstreams"] = [{"dial": f"127.0.0.1:{cls.upstream.server_port}"}]
                handler["health_checks"]["active"]["interval"] = 100_000_000
                handler["health_checks"]["active"]["timeout"] = 500_000_000
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        route_server.update(listen=[f"127.0.0.1:{cls.port}"], automatic_https={"disable": True})
        route_server.pop("strict_sni_host", None)
        config = {"admin": {"disabled": True}, "apps": {"http": {"servers": {"test": route_server}}}}
        config_path = work / "synthetic.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        log = (work / "synthetic.log").open("wb")
        cls.addClassCleanup(log.close)
        cls.process = subprocess.Popen([binary, "run", "--config", str(config_path)], env=environment,
                                       stdout=log, stderr=log,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        cls.addClassCleanup(cls.stop_process)
        for _ in range(100):
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    break
            except OSError:
                if cls.process.poll() is not None:
                    raise RuntimeError("Synthetic Caddy exited before accepting requests")
                time.sleep(0.05)
        else:
            raise RuntimeError("Synthetic Caddy did not start")

    @classmethod
    def stop_process(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)

    def request(self, path, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request("GET", path, headers={"Host": "landvilla.in", **(headers or {})})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_production_tls_hosts_and_loopback_probe(self):
        self.assertTrue(self.server["strict_sni_host"])
        self.assertNotIn("disable", self.server.get("automatic_https", {}))
        self.assertEqual(self.server["protocols"], ["h1", "h2"])
        self.assertEqual({host for route in self.server["routes"] for match in route["match"]
                          for host in match.get("host", [])}, {"landvilla.in", "www.landvilla.in"})
        listeners = [listener for server in self.production["apps"]["http"]["servers"].values()
                     for listener in server["listen"]]
        self.assertEqual(set(listeners), {":443", "127.0.0.1:8080"})
        self.assertTrue(self.production["admin"]["disabled"])
        self.assertFalse(self.production["admin"]["config"]["persist"])
        proxy = next(handler for handler in handlers(self.server) if handler["handler"] == "reverse_proxy")
        active = proxy["health_checks"]["active"]
        self.assertEqual((active["uri"], active["expect_status"], active["interval"], active["timeout"], active["fails"], active["passes"]),
                         ("/ready", 200, 15_000_000_000, 8_000_000_000, 1, 1))
        self.assertNotIn("follow_redirects", active)
        body = next(handler for handler in handlers(self.server) if handler["handler"] == "request_body")
        self.assertEqual(body["max_size"], 12_000_000)

    def test_health_withdrawal_and_recovery_are_independent_of_public_probe_routes(self):
        def wait_status(expected):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if self.request("/api/auth/me")[0] == expected:
                    return
                time.sleep(0.05)
            self.fail("Caddy active health state did not converge")

        try:
            Echo.ready = False
            wait_status(503)
            self.assertEqual(self.request("/ready")[0], 404)
        finally:
            Echo.ready = True
            wait_status(200)

    def test_forwarding_replacement_and_browser_security_preservation(self):
        context = {"Origin": "https://landvilla.in", "Referer": "https://landvilla.in/account",
                   "Cookie": "__Host-lv_session=synthetic", "X-CSRF-Token": "synthetic",
                   "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
        status, response_headers, body = self.request("/api/auth/me", {**context, "X-LV-Client-IP":"attacker", "X-LV-Ingress-Token":"attacker", "X-LV-IP-Signature":"attacker",
            "Forwarded": "proto=http;host=attacker.invalid", "X-Forwarded-Proto": "http",
            "X-Forwarded-Host": "attacker.invalid", "X-Forwarded-For": "8.8.8.8",
            "X-Forwarded-Port": "80", "X-Forwarded-Unrecognized": "attacker",
            "X-Real-IP": "8.8.8.8"})
        self.assertEqual(status, 200)
        upstream = {name.lower(): value for name, value in json.loads(body).items()}
        self.assertEqual(upstream["host"], "landvilla.in")
        self.assertEqual(upstream["x-forwarded-proto"], "https")
        self.assertEqual(upstream["x-forwarded-host"], "landvilla.in")
        self.assertEqual(upstream["x-lv-client-ip"], "127.0.0.1")
        self.assertEqual(upstream["x-lv-ingress-token"], "d"*64)
        self.assertNotIn("x-lv-ip-signature", upstream)
        for name in ("forwarded", "x-forwarded-for", "x-forwarded-port", "x-forwarded-unrecognized", "x-real-ip"):
            self.assertNotIn(name, upstream)
        for name, value in context.items():
            self.assertEqual(upstream[name.lower()], value)
        self.assertIn("__Host-lv_session=synthetic; Secure; HttpOnly; Path=/; SameSite=Lax",
                      response_headers["Set-Cookie"])

    def test_probe_routes_are_not_public(self):
        for path in ("/health", "/health/", "/ready", "/ready/detail", "/%68ealth", "/%72eady", "/ready%2fdetail"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_www_canonical_redirect_and_unrecognized_host(self):
        status, headers, _ = self.request("/properties?q=synthetic", {"Host": "www.landvilla.in"})
        self.assertEqual(status, 308)
        self.assertEqual(headers["Location"], "https://landvilla.in/properties?q=synthetic")
        _, _, body = self.request("/api/auth/me", {"Host": "attacker.invalid"})
        self.assertNotIn(b"__Host-lv_session", body)


if __name__ == "__main__":
    unittest.main()
