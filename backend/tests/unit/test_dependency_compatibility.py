"""Offline dependency-compatibility probes, retained in the regression suite.

No provider access: existing MemoryDB fixture, mocked storage and OTP delivery.
Run with the independently installed requirements-test environment, from repo root.
"""
import hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests/unit"))
import test_regressions as fixture
import test_runtime_http as production
from starlette import formparsers
from starlette.datastructures import UploadFile


class IndependentCompatibility(unittest.IsolatedAsyncioTestCase):
    WEB_PEER = production.ProductionProxyHTTP.WEB_PEER
    WEB_ORIGIN = production.ProductionProxyHTTP.WEB_ORIGIN
    HTTPS_HEADERS = production.ProductionProxyHTTP.HTTPS_HEADERS
    async def asyncSetUp(self):
        await production.ProductionProxyHTTP.asyncSetUp(self)
        from starlette.middleware.cors import CORSMiddleware
        from starlette.middleware import Middleware
        self.application.user_middleware = [
            Middleware(CORSMiddleware, **{**item.kwargs, "allow_origins": [self.WEB_ORIGIN]})
            if item.cls is CORSMiddleware else item for item in self.application.user_middleware]
        self.application.middleware_stack = None
    asyncTearDown = production.ProductionProxyHTTP.asyncTearDown
    client = production.ProductionProxyHTTP.client
    bootstrap = production.ProductionProxyHTTP.bootstrap

    async def login(self):
        bootstrap, headers = await self.bootstrap(Origin=self.WEB_ORIGIN)
        with patch.object(fixture.identity, "provider_ready"), \
                patch.object(fixture.identity, "deliver", new_callable=AsyncMock) as delivery:
            request = await self.api.post("/api/auth/otp/request", headers=headers,
                                          json={"identifier": "owner@example.com"})
        self.assertEqual(request.status_code, 200, request.text)
        delivery.assert_awaited_once()
        verified = await self.api.post("/api/auth/otp/verify", headers=headers, json={
            "challenge_id": request.json()["challenge_id"], "code": delivery.await_args.args[2],
        })
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertNotIn("session_token", verified.json())
        self.assertEqual(verified.json()["user"]["user_id"], "owner")
        self.assertNotEqual(bootstrap.headers["set-cookie"], verified.headers["set-cookie"])
        headers.update(Cookie=verified.headers["set-cookie"].split(";", 1)[0],
                       **{"X-CSRF-Token": verified.json()["csrf_token"]})
        return verified, headers

    async def test_authenticated_full_route_upload_spool_rollover_and_file_response(self):
        _, headers = await self.login()
        # Synthetic JPEG signature accepted by the unchanged app. Larger than the
        # installed framework's spool threshold, smaller than its 8 MiB app limit.
        payload = b"\xff\xd8\xff" + b"\x00" * (formparsers.MultiPartParser.spool_max_size + 17)
        self.assertGreater(len(payload), 1024 * 1024)
        self.assertLess(len(payload), fixture.marketplace.UPLOAD_RULES["property_photo"][1])
        observed = []
        original_read = UploadFile.read

        async def observed_read(upload, size=-1):
            if upload.filename == "synthetic.jpg":
                observed.append(bool(getattr(upload.file, "_rolled", False)))
            return await original_read(upload, size)

        def storage_put(path, data, content_type, provider):
            self.assertEqual(data, payload)
            self.assertEqual(content_type, "image/jpeg")
            self.assertEqual(provider, "cloudflare_r2")
            return {"path": path}

        with patch.object(UploadFile, "read", observed_read), \
                patch.object(fixture.marketplace, "_put", side_effect=storage_put) as put, \
                patch.dict(os.environ, STORAGE_PROVIDER="cloudflare_r2"):
            response = await self.api.post("/api/uploads", headers=headers,
                data={"kind": "property_photo"}, files={"file": ("synthetic.jpg", payload, "image/jpeg")})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(observed, [True], "The successful application read must follow real disk rollover")
        put.assert_called_once()
        self.assertEqual(response.headers["access-control-allow-origin"], self.WEB_ORIGIN)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        stored = await self.db.files.find_one({"id": response.json()["id"]})
        self.assertEqual(stored["owner_id"], "owner")
        self.assertEqual(stored["size"], len(payload))
        self.assertEqual(stored["sha256"], hashlib.sha256(payload).hexdigest())
        with patch.object(fixture.marketplace, "_get", return_value=(payload, "image/jpeg")) as get:
            downloaded = await self.api.get(response.json()["url"], headers=self.HTTPS_HEADERS)
        get.assert_called_once()
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, payload)
        self.assertEqual(downloaded.headers["content-type"], "image/jpeg")
        self.assertEqual(downloaded.headers["cache-control"], "public, max-age=86400")

    async def test_production_cors_cookie_authentication_and_csrf_remain_compatible(self):
        preflight = await self.api.options("/api/uploads", headers={
            **self.HTTPS_HEADERS, "Origin": self.WEB_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-token,x-lv-client",
        })
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight.headers["access-control-allow-origin"], self.WEB_ORIGIN)
        self.assertEqual(preflight.headers["access-control-allow-credentials"], "true")
        login, headers = await self.login()
        for attribute in ("__Host-lv_session=", "Secure", "HttpOnly", "SameSite=lax", "Path=/"):
            self.assertIn(attribute, login.headers["set-cookie"])
        self.assertNotIn("Domain=", login.headers["set-cookie"])
        profile = await self.api.get("/api/me/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.headers["cache-control"], "no-store")
        self.assertEqual(profile.json()["user_id"], "owner")
        with patch.object(fixture.marketplace, "_put") as storage:
            denied = await self.api.post("/api/uploads", headers={**headers, "X-CSRF-Token": "wrong"},
                data={"kind": "property_photo"}, files={"file": ("synthetic.jpg", b"\xff\xd8\xff", "image/jpeg")})
        self.assertEqual(denied.status_code, 403)
        storage.assert_not_called()
        rejected = await self.api.options("/api/uploads", headers={
            **self.HTTPS_HEADERS, "Origin": "https://untrusted.invalid",
            "Access-Control-Request-Method": "POST",
        })
        self.assertEqual(rejected.status_code, 400)
        self.assertNotIn("access-control-allow-origin", rejected.headers)
        logout = await self.api.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout.status_code, 200)
        self.assertIn("Max-Age=0", logout.headers["set-cookie"])
        self.assertEqual((await self.api.get("/api/me/profile", headers=headers)).status_code, 401)

    async def test_actual_application_lifespan_hooks_run_with_identity_fixture_without_seeding(self):
        ping = AsyncMock(return_value={"ok": 1})
        client = Mock()
        with patch.object(fixture.server.db, "command", ping, create=True), \
                patch.object(fixture.server, "client", client), \
                patch.object(fixture.server, "seed_all", new_callable=AsyncMock) as seed, \
                patch.dict(os.environ, IDENTITY_ENABLED="true", SEED_ON_STARTUP="false"):
            async with self.application.router.lifespan_context(self.application):
                ping.assert_awaited_once_with("ping")
                client.close.assert_not_called()
            client.close.assert_called_once_with()
            seed.assert_not_awaited()

    async def test_actual_openapi_and_pydantic_validation_response(self):
        schema = self.application.openapi()
        self.assertTrue(schema["openapi"].startswith("3."))
        upload = schema["paths"]["/api/uploads"]["post"]
        self.assertIn("multipart/form-data", upload["requestBody"]["content"])
        self.assertIn("200", upload["responses"])
        self.assertIn("/api/auth/otp/verify", schema["paths"])
        _, headers = await self.login()
        response = await self.api.post("/api/auth/otp/verify", headers=headers, json={
            "challenge_id": "short-private-id", "code": "synthetic-invalid-private-code",
        })
        self.assertEqual(response.status_code, 422, response.text)
        self.assertNotIn("short-private-id", response.text)
        self.assertNotIn("synthetic-invalid-private-code", response.text)
        for error in response.json()["detail"]:
            self.assertEqual(set(error), {"loc", "msg", "type"})
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")


if __name__ == "__main__":
    unittest.main(verbosity=2)
