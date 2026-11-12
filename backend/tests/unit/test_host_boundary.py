"""Raw ASGI Host regressions, including bytes rejected by HTTP client libraries."""
import unittest

from fastapi import FastAPI
from production_runtime import add_production_host_middleware


class HostBoundary(unittest.IsolatedAsyncioTestCase):
    def middleware(self, destination):
        application = FastAPI()
        add_production_host_middleware(application, {
            "APP_ENV": "production", "TRUSTED_HOSTS": "api,127.0.0.1",
        })
        registered = application.user_middleware[0]
        return registered.cls(destination, *registered.args, **registered.kwargs)

    async def exchange(self, kind, headers):
        called = []
        messages = []

        async def destination(scope, receive, send):
            called.append(scope)

        async def receive():
            return {"type": "websocket.connect" if kind == "websocket" else "http.request"}

        async def send(message):
            messages.append(message)

        scope = {"type": kind, "headers": headers, "path": "/api/auth/me", "method": "GET",
                 "scheme": "ws" if kind == "websocket" else "http", "query_string": b"",
                 "server": ("api", 8000), "client": ("172.28.240.18", 45678)}
        await self.middleware(destination)(scope, receive, send)
        return called, messages

    async def test_missing_duplicate_non_ascii_and_control_hosts_rejected(self):
        cases = [[], [(b"host", b"api"), (b"host", b"api")],
                 [(b"host", b"api"), (b"host", b"attacker.invalid")]]
        cases.extend([[(b"host", value)] for value in (
            b"api\xff", b"api\x00", b"api\r\nInjected: yes", b"api\t", b" api", b"api ",
            b"api:8000/health?ignored=", b"api:8000#fragment", b"api:8000\\health", b"api%2fhealth",
            b"api:65536", b"api:0", b"api:", b"api:+80", b"api:-80", b"api:80:90",
            b"api:123456", b"api:abc", b"api.", b"API", b"bad_host", b"-api", b"api-",
            b"api..internal", b"[::1]", b"landvilla.in", b"www.api", b"api.attacker.invalid",
        )])
        for headers in cases:
            with self.subTest(headers=headers):
                called, messages = await self.exchange("http", headers)
                self.assertFalse(called)
                self.assertEqual(messages[0]["type"], "http.response.start")
                self.assertEqual(messages[0]["status"], 400)
                self.assertEqual(messages[1]["body"], b"Invalid host header")

    async def test_valid_internal_and_probe_host_authorities_pass(self):
        for host in (b"api", b"api:1", b"api:8000", b"api:65535", b"127.0.0.1", b"127.0.0.1:8000"):
            for kind in ("http", "websocket"):
                with self.subTest(host=host, kind=kind):
                    called, messages = await self.exchange(kind, [(b"host", host)])
                    self.assertEqual(len(called), 1)
                    self.assertFalse(messages)

    async def test_websocket_rejection_uses_close_without_http_extension(self):
        for headers in ([], [(b"host", b"api"), (b"host", b"api")], [(b"host", b"api\xff")],
                        [(b"host", b"api:")], [(b"host", b"attacker.invalid")],
                        [(b"host", b"api:8000/health?ignored=")]):
            with self.subTest(headers=headers):
                called, messages = await self.exchange("websocket", headers)
                self.assertFalse(called)
                self.assertEqual(messages, [{"type": "websocket.close", "code": 1008}])

    async def test_lifespan_scope_is_unchanged(self):
        called = []

        async def destination(scope, receive, send):
            called.append(scope)

        scope = {"type": "lifespan"}
        await self.middleware(destination)(scope, None, None)
        self.assertEqual(called, [scope])
