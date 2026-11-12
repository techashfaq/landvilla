"""Raw ASGI coverage, including bytes HTTP clients refuse to construct."""
import unittest
from fastapi import FastAPI, WebSocket
from production_runtime import add_production_host_middleware


class HostASGI(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.application = FastAPI()
        self.called = False

        @self.application.get("/health")
        async def health():
            self.called = True
            return {"status": "ok"}

        @self.application.websocket("/socket")
        async def socket(websocket: WebSocket):
            self.called = True
            await websocket.accept()
            await websocket.close(code=1000)

        add_production_host_middleware(self.application, {
            "APP_ENV": "production", "TRUSTED_HOSTS": "api,127.0.0.1",
        })

    async def call(self, kind, headers):
        self.called = False
        messages = []
        path = "/health" if kind == "http" else "/socket"
        scope = dict(type=kind, asgi={"version": "3.0", "spec_version": "2.3"},
                     http_version="1.1", method="GET", scheme="http" if kind == "http" else "ws",
                     path=path, raw_path=path.encode(), root_path="", query_string=b"",
                     headers=headers, client=("172.30.250.10", 1234), server=("api", 8000), subprotocols=[])

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False} if kind == "http" else {"type": "websocket.connect"}

        async def send(message):
            messages.append(message)

        await self.application(scope, receive, send)
        return messages

    async def test_raw_invalid_http_host_rejected_before_route(self):
        for value in (b"\xff", b"api\x00", b"api\t", b"api\r\n", b"api:8000/health?", b"bad_host",
                      b"-api", b"api-", b"api..test", b"api:65536", b"api:0", b"api:", b"api:+80", b"api: 80",
                      b"api@evil.invalid", b"api#health", b"[::1]", b"API", b"api.", b"evil.invalid"):
            with self.subTest(value=value):
                events = await self.call("http", [(b"host", value)])
                self.assertEqual(events[0]["status"], 400)
                self.assertFalse(self.called)

    async def test_websocket_invalid_missing_duplicate_host_closes_with_policy_violation(self):
        invalid = [[], [(b"host", b"api"), (b"host", b"api")]]
        invalid += [[(b"host", value)] for value in (b"\xff", b"api:8000/path", b"api:", b"api:65536", b"evil.invalid")]
        for headers in invalid:
            with self.subTest(headers=headers):
                events = await self.call("websocket", headers)
                self.assertEqual(events, [{"type": "websocket.close", "code": 1008}])
                self.assertFalse(self.called)

    async def test_accepted_internal_and_probe_hosts_for_http_and_websocket(self):
        for kind in ("http", "websocket"):
            for host in (b"api", b"api:8000", b"127.0.0.1", b"127.0.0.1:8000"):
                with self.subTest(kind=kind, host=host):
                    events = await self.call(kind, [(b"host", host)])
                    self.assertTrue(self.called)
                    self.assertEqual(events[0]["type"], "http.response.start" if kind == "http" else "websocket.accept")


if __name__ == "__main__":
    unittest.main()
