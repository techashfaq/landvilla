"""HTTP boundary regressions using the existing offline fake database fixture."""
import unittest
from unittest.mock import patch, AsyncMock
import test_regressions as f
from fastapi import HTTPException


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

    async def test_sensitive_write_throttled_before_route(self):
        with patch.object(f.server, "PRODUCTION", True), patch.object(f.server.identity, "throttle", AsyncMock(side_effect=HTTPException(429, "Too many attempts", headers={"Retry-After": "60"}))):
            response = await self.api.post("https://test/api/uploads")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "60")
