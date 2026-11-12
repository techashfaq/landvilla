"""Small local regressions for upgraded framework parsing and lifecycle behavior."""
import unittest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.datastructures import URL
import test_regressions as f


class FrameworkSecurity(unittest.IsolatedAsyncioTestCase):
    async def test_multipart_field_limit_rejects_oversized_non_file_part(self):
        async def form(request: Request):
            async with request.form(max_fields=2, max_part_size=32) as data:
                return JSONResponse({"fields": len(data)})

        app = Starlette(routes=[Route("/form", form, methods=["POST"])])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            response = await client.post("/form", files={"field": (None, "a" * 64)})
        self.assertEqual(response.status_code, 400)

    async def test_urlencoded_count_and_size_limits_are_enforced(self):
        async def form(request: Request):
            async with request.form(max_fields=2, max_part_size=32) as data:
                return JSONResponse({"fields": len(data)})

        app = Starlette(routes=[Route("/form", form, methods=["POST"])])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            for content in ("a=1&b=2&c=3", "a=" + "x" * 64):
                response = await client.post("/form", content=content, headers={"Content-Type": "application/x-www-form-urlencoded"})
                self.assertEqual(response.status_code, 400)

    def test_malformed_path_cannot_change_url_authority(self):
        url = URL(scope={"type": "http", "scheme": "https", "path": "@attacker.invalid",
                         "query_string": b"", "headers": [(b"host", b"api")], "server": ("api", 8000)})
        self.assertEqual(url.hostname, "api")

    async def test_existing_lifespan_still_runs_startup_and_shutdown_without_seeding(self):
        ping = AsyncMock(return_value={"ok": 1})
        client = Mock()
        with patch.object(f.server.db, "command", ping, create=True), patch.object(f.server, "client", client), \
                patch.object(f.server, "seed_all", AsyncMock()) as seed, \
                patch.dict(f.os.environ, {"IDENTITY_ENABLED": "false", "SEED_ON_STARTUP": "false"}):
            async with f.server.app.router.lifespan_context(f.server.app):
                ping.assert_awaited_once_with("ping")
                client.close.assert_not_called()
            client.close.assert_called_once_with()
            seed.assert_not_awaited()
