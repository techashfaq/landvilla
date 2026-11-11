import json
import logging
import unittest
from unittest.mock import AsyncMock, Mock
from production_runtime import validate_environment, SafeJSONFormatter, dependency_readiness


class ProductionRuntime(unittest.IsolatedAsyncioTestCase):
    def environment(self):
        return dict(APP_ENV="production", MONGO_URL="synthetic", DB_NAME="test", CORS_ORIGINS="https://web.example", WEB_APP_ORIGINS="https://web.example", TRUSTED_HOSTS="api.example,127.0.0.1", S3_ENDPOINT="https://r2.example", S3_BUCKET="test", S3_ACCESS_KEY_ID="synthetic", S3_SECRET_ACCESS_KEY="synthetic", STORAGE_PROVIDER="cloudflare_r2", IDENTITY_ENABLED="true", OTP_HMAC_SECRET="synthetic" * 8, FORWARDED_ALLOW_IPS="127.0.0.1")

    def test_configuration_rejects_unsafe_origins_and_seeding(self):
        validate_environment(self.environment())
        for key, value in [("CORS_ORIGINS", "http://web.example"), ("TRUSTED_HOSTS", "*"), ("SEED_ON_STARTUP", "true"), ("S3_ENDPOINT", "https://user:secret@r2.example"), ("STORAGE_PROVIDER", "emergent")]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_environment({**self.environment(), key: value})

    def test_logs_omit_messages_and_exception_data(self):
        record = logging.LogRecord("test", 40, "", 1, "secret-token", (), None)
        record.event = "http_request"
        result = SafeJSONFormatter().format(record)
        self.assertNotIn("secret-token", result)
        self.assertEqual(json.loads(result)["event"], "http_request")

    async def test_readiness_requires_transaction_topology(self):
        db = Mock(command=AsyncMock(side_effect=[{}, {"logicalSessionTimeoutMinutes": 30}]))
        with self.assertRaises(RuntimeError):
            await dependency_readiness(db)

    async def test_readiness_checks_storage_without_writes(self):
        db = Mock(command=AsyncMock(side_effect=[{}, {"setName": "rs", "logicalSessionTimeoutMinutes": 30}]))
        storage = Mock()
        await dependency_readiness(db, storage, "test")
        storage.head_bucket.assert_called_once_with(Bucket="test")
        storage.put_object.assert_not_called()

    async def test_storage_failure_fails_readiness(self):
        db = Mock(command=AsyncMock(side_effect=[{}, {"msg": "isdbgrid", "logicalSessionTimeoutMinutes": 30}]))
        with self.assertRaises(RuntimeError):
            await dependency_readiness(db, Mock(head_bucket=Mock(side_effect=RuntimeError("secret"))), "test")
