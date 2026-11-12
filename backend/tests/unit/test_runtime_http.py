"""HTTP boundary regressions using the existing offline fake database fixture."""
import unittest
import copy
import os
from unittest.mock import patch, AsyncMock, Mock
import test_regressions as f
from fastapi import HTTPException
from production_runtime import add_production_host_middleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


class RuntimeHTTP(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = f.Regressions.asyncSetUp
    asyncTearDown = f.Regressions.asyncTearDown

    async def test_insecure_production_request_rejected(self):
        with patch.object(f.server, "PRODUCTION", True):
            response = await self.api.get("/api/featured-plans")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.headers["x-request-id"]), 32)

    async def test_liveness_does_not_require_database(self):
        with patch.object(f.server, "PRODUCTION", True), patch.object(f.server.db, "command", AsyncMock(side_effect=RuntimeError("private"))):
            self.assertEqual((await self.api.get("/health")).status_code, 200)

    async def test_readiness_error_does_not_expose_provider_details(self):
        with patch.object(f.server, "PRODUCTION", True), patch.object(f.server, "readiness_storage_client", side_effect=RuntimeError("private-secret")):
            response = await self.api.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-secret", response.text)

    async def test_health_success_is_not_cached_and_never_checks_dependencies(self):
        with patch.object(f.server, "PRODUCTION", True), patch.object(f.server, "dependency_readiness", AsyncMock()) as dependencies:
            response = await self.api.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        dependencies.assert_not_awaited()

    async def test_readiness_success_and_deadline_close_probe_without_diagnostics(self):
        storage = Mock()
        with patch.object(f.server, "PRODUCTION", True), patch.dict(os.environ, {"S3_BUCKET": "synthetic"}), \
                patch.object(f.server, "readiness_storage_client", return_value=storage), \
                patch.object(f.server, "dependency_readiness", AsyncMock()) as dependencies:
            response = await self.api.get("/ready")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ready"})
            self.assertEqual(response.headers["cache-control"], "no-store")
            dependencies.assert_awaited_once_with(f.server.db, storage, "synthetic")
        storage.close.assert_called_once_with()
        storage.reset_mock()

        async def timeout(awaitable, *, timeout):
            self.assertEqual(timeout, 5)
            awaitable.close()
            raise TimeoutError("private-provider-host-secret")

        with patch.object(f.server, "PRODUCTION", True), patch.dict(os.environ, {"S3_BUCKET": "synthetic"}), \
                patch.object(f.server, "readiness_storage_client", return_value=storage), \
                patch.object(f.server, "dependency_readiness", AsyncMock()), \
                patch.object(f.server.asyncio, "wait_for", timeout):
            response = await self.api.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("private", response.text)
        storage.close.assert_called_once_with()

    async def test_sensitive_write_throttled_before_route(self):
        with patch.object(f.server, "PRODUCTION", True), patch.object(f.server.identity, "throttle", AsyncMock(side_effect=HTTPException(429, "Too many attempts", headers={"Retry-After": "60"}))):
            response = await self.api.post("https://test/api/uploads")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "60")


class ProductionProxyHTTP(unittest.IsolatedAsyncioTestCase):
    """Real Uvicorn and application middleware; all database work uses MemoryDB."""
    WEB_PEER = "172.28.240.18"
    WEB_ORIGIN = "https://landvilla.in"
    HTTPS_HEADERS = {"X-Forwarded-Proto": "https"}

    async def asyncSetUp(self):
        await f.Regressions.asyncSetUp(self)
        await self.api.aclose()
        settings = {"APP_ENV": "production", "WEB_APP_ORIGINS": self.WEB_ORIGIN,
                    "CLIENT_IP_MODE": "signed-v1", "WEB_API_IP_KEY": "e"*64,
                    "TRUSTED_HOSTS": "api,127.0.0.1", "FORWARDED_ALLOW_IPS": self.WEB_PEER}
        for item in (patch.dict(os.environ, settings), patch.object(f.server, "PRODUCTION", True)):
            self.patches.append(item)
            item.start()
        # Keep the real routes and security middleware without starting any lifespan
        # or changing the development application shared by the other offline tests.
        self.application = copy.copy(f.server.app)
        self.application.user_middleware = list(f.server.app.user_middleware)
        self.application.middleware_stack = None
        add_production_host_middleware(self.application, os.environ)
        self.proxied = ProxyHeadersMiddleware(self.application, trusted_hosts=os.environ["FORWARDED_ALLOW_IPS"])
        self.api = self.client(self.WEB_PEER)

    asyncTearDown = f.Regressions.asyncTearDown

    def client(self, peer):
        async def identity_header(request):
            import hmac, hashlib, time
            stamp=str(int(time.time()))
            address=request.headers.get("x-lv-client-ip", "203.0.113.10")
            message="\n".join(("v1",stamp,request.method,request.url.path,address))
            request.headers.update({"X-LV-Client-IP":address,"X-LV-IP-Time":stamp,
                                    "X-LV-IP-Signature":hmac.new(bytes.fromhex("e"*64),message.encode(),hashlib.sha256).hexdigest()})
        return f.httpx.AsyncClient(transport=f.httpx.ASGITransport(app=self.proxied, client=(peer, 45678)),
                                  base_url="http://api:8000", event_hooks={"request":[identity_header]})

    async def test_real_security_middleware_order(self):
        self.assertIs(self.proxied.app, self.application)
        stack = self.application.build_middleware_stack()
        self.assertEqual(type(stack).__name__, "ServerErrorMiddleware")
        self.assertEqual(type(stack.app).__name__, "StrictTrustedHostMiddleware")
        self.assertEqual(type(stack.app.app).__name__, "CORSMiddleware")
        self.assertEqual(type(stack.app.app.app).__name__, "BaseHTTPMiddleware")

    async def test_forwarded_host_cannot_change_url_or_cookie_scope(self):
        response = await self.api.get("/api/auth/browser/bootstrap", headers={
            **self.HTTPS_HEADERS, "X-LV-Client": "web", "Origin": self.WEB_ORIGIN,
            "X-Forwarded-Host": "attacker.invalid", "Forwarded": "host=attacker.invalid;proto=http",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Domain=", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])

    async def bootstrap(self, **headers):
        response = await self.api.get("/api/auth/browser/bootstrap", headers={
            **self.HTTPS_HEADERS, "X-LV-Client": "web", **headers,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response, {
            **self.HTTPS_HEADERS, "X-LV-Client": "web", "Origin": self.WEB_ORIGIN,
            "Cookie": response.headers["set-cookie"].split(";", 1)[0],
            "X-CSRF-Token": response.json()["csrf_token"],
        }

    async def test_trusted_private_http_peer_requires_explicit_https_claim(self):
        self.assertEqual((await self.api.get("/api/", headers=self.HTTPS_HEADERS)).status_code, 200)
        for headers in ({}, {"X-Forwarded-Proto": "http"}, {"X-Forwarded-Proto": "https,http"},
                        {"Forwarded": "proto=https;host=landvilla.in"}):
            with self.subTest(headers=headers):
                response = await self.api.get("/api/", headers=headers)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["detail"], "HTTPS required")

    async def test_untrusted_peers_cannot_claim_https(self):
        for peer in ("172.28.240.19", "172.28.240.2", "127.0.0.1", "203.0.113.20"):
            with self.subTest(peer=peer):
                async with self.client(peer) as client:
                    response = await client.get("/api/", headers={
                        **self.HTTPS_HEADERS, "X-Forwarded-For": self.WEB_PEER,
                        "X-Forwarded-Host": "api", "Forwarded": "proto=https",
                    })
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["detail"], "HTTPS required")

    async def test_invalid_host_rejected_before_browser_guard_or_throttle(self):
        for host in ("attacker.invalid", "landvilla.in", "www.api", "api.attacker.invalid", "",
                     "api:8000/health?ignored=", "api:8000#fragment", "api:invalid", "api:0", "api:65536",
                     "api:", "api:8000:9000", "api/health", "api@attacker.invalid"):
            with self.subTest(host=host), patch.object(f.browser_sessions, "guard", AsyncMock()) as guard, patch.object(f.identity, "throttle", AsyncMock()) as throttle:
                response = await self.api.post("/api/auth/logout", headers={
                    **self.HTTPS_HEADERS, "Host": host, "X-Forwarded-Host": "api",
                })
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("location", response.headers)
                guard.assert_not_awaited()
                throttle.assert_not_awaited()
        preflight = await self.api.options("/api/me/profile", headers={
            "Host": "attacker.invalid", "Origin": "http://localhost:8081",
            "Access-Control-Request-Method": "PATCH",
        })
        self.assertEqual(preflight.status_code, 400)

    async def test_duplicate_or_missing_host_rejected(self):
        with patch.object(f.browser_sessions, "guard", AsyncMock()) as guard:
            duplicate = await self.api.get("/health", headers=[("Host", "api"), ("Host", "attacker.invalid")])
            self.assertEqual(duplicate.status_code, 400)
            request = self.api.build_request("GET", "/health")
            del request.headers["host"]
            self.assertEqual((await self.api.send(request)).status_code, 400)
            guard.assert_not_awaited()

    async def test_internal_host_port_and_loopback_health(self):
        self.assertEqual((await self.api.get("/api/", headers={**self.HTTPS_HEADERS, "Host": "api:8000"})).status_code, 200)
        async with self.client("127.0.0.1") as local:
            response = await local.get("http://127.0.0.1:8000/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})
            self.assertEqual((await local.head("http://127.0.0.1:8000/health")).status_code, 200)
            self.assertEqual((await local.get("http://127.0.0.1:8000/health", headers={"Host": "attacker.invalid"})).status_code, 400)

    async def test_authenticated_client_identity_supplies_rate_bucket(self):
        with patch.object(f.identity, "throttle", AsyncMock()) as throttle:
            response = await self.api.post("/api/auth/logout", headers=self.HTTPS_HEADERS)
        self.assertEqual(response.status_code, 200)
        throttle.assert_awaited_once_with("ingress:203.0.113.10", 120, 60)

    async def test_bootstrap_limit_separates_verified_visitors(self):
        for _ in range(30):
            self.api.cookies.clear()
            response=await self.api.get("/api/auth/browser/bootstrap",headers={**self.HTTPS_HEADERS,"Origin":self.WEB_ORIGIN})
            self.assertEqual(response.status_code,200)
        self.api.cookies.clear()
        limited=await self.api.get("/api/auth/browser/bootstrap",headers={**self.HTTPS_HEADERS,"Origin":self.WEB_ORIGIN})
        self.assertEqual(limited.status_code,429)
        self.api.cookies.clear()
        other=await self.api.get("/api/auth/browser/bootstrap",headers={**self.HTTPS_HEADERS,"Origin":self.WEB_ORIGIN,"X-LV-Client-IP":"203.0.113.11"})
        self.assertEqual(other.status_code,200)

    async def test_origin_bootstrap_secure_cookie_csrf_and_logout_over_internal_http(self):
        response, headers = await self.bootstrap(Origin=self.WEB_ORIGIN)
        cookie = response.headers["set-cookie"]
        for attribute in ("__Host-lv_session=", "HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age="):
            self.assertIn(attribute, cookie)
        self.assertNotIn("Domain=", cookie)
        self.assertNotIn("session_token", response.json())
        self.assertEqual((await self.api.post("/api/auth/browser/google-nonce", headers=headers)).status_code, 200)
        for changed in ({"X-CSRF-Token": "wrong"}, {"X-CSRF-Token": ""}, {"Origin": "https://attacker.invalid"},
                        {"Origin": "http://landvilla.in"}, {"Origin": "null"}, {"Origin": ""},
                        {"Sec-Fetch-Site": "cross-site"}, {"Authorization": "Bearer owner-token"}):
            with self.subTest(changed=changed):
                rejected = await self.api.post("/api/auth/browser/google-nonce", headers={**headers, **changed})
                self.assertEqual(rejected.status_code, 403)
        logout = await self.api.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout.status_code, 200)
        for attribute in ("__Host-lv_session=", "Max-Age=0", "Secure", "HttpOnly", "Path=/", "SameSite=lax"):
            self.assertIn(attribute, logout.headers["set-cookie"])

    async def test_referer_bootstrap_fallback_preserved_without_synthesizing_origin(self):
        await self.bootstrap(Referer=self.WEB_ORIGIN + "/account")
        for headers in ({}, {"Referer": "https://attacker.invalid/account"}, {"Referer": "http://landvilla.in/account"},
                        {"Referer": self.WEB_ORIGIN + "/account", "Origin": "https://attacker.invalid"}):
            with self.subTest(headers=headers):
                response = await self.api.get("/api/auth/browser/bootstrap", headers={
                    **self.HTTPS_HEADERS, "X-LV-Client": "web", **headers,
                })
                self.assertEqual(response.status_code, 403)
