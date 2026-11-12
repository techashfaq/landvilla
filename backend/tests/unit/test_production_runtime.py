import json
import logging
import unittest
from unittest.mock import AsyncMock, Mock
from production_runtime import validate_environment, SafeJSONFormatter, dependency_readiness


class ProductionRuntime(unittest.IsolatedAsyncioTestCase):
    def environment(self):
        return dict(APP_ENV="production", CLIENT_IP_MODE="signed-v1", WEB_API_IP_KEY="a" * 64, MONGO_URL="mongodb+srv://synthetic.invalid/landvilla_prod", DB_NAME="landvilla_prod", CORS_ORIGINS="https://web.example", WEB_APP_ORIGINS="https://web.example", TRUSTED_HOSTS="api,127.0.0.1", S3_ENDPOINT="https://r2.example", S3_BUCKET="landvilla-property-media-prod", S3_ACCESS_KEY_ID="synthetic", S3_SECRET_ACCESS_KEY="synthetic", STORAGE_PROVIDER="cloudflare_r2", IDENTITY_ENABLED="true", OTP_HMAC_SECRET="synthetic" * 8, FORWARDED_ALLOW_IPS="172.28.240.18")

    def test_configuration_rejects_unsafe_origins_and_seeding(self):
        validate_environment(self.environment())
        for key, value in [("CORS_ORIGINS", "http://web.example"), ("TRUSTED_HOSTS", "*"), ("SEED_ON_STARTUP", "true"), ("S3_ENDPOINT", "https://user:secret@r2.example"), ("STORAGE_PROVIDER", "emergent")]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_environment({**self.environment(), key: value})

    def test_production_requires_every_critical_setting(self):
        for name in self.environment():
            if name == "APP_ENV":
                continue
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                validate_environment({**self.environment(), name: ""})

    def test_public_origins_are_https_only_and_well_formed(self):
        invalid = ("http://landvilla.in", "https://user:secret@landvilla.in", "https://landvilla.in/path",
                   "https://landvilla.in?query=1", "https://landvilla.in#fragment", "https://*.landvilla.in",
                   "https://landvilla.in:invalid", "https://landvilla.in:65536", "https://landvilla.in:0",
                   "https://bad_host.example", "https://landvilla.in,", "https://landvilla.in/")
        for name in ("CORS_ORIGINS", "WEB_APP_ORIGINS"):
            for value in invalid:
                with self.subTest(name=name, value=value), self.assertRaises(RuntimeError):
                    validate_environment({**self.environment(), name: value})

    def test_proxy_trust_requires_exact_rfc1918_addresses(self):
        for value in ("10.12.1.2", "172.16.0.1", "172.31.255.254", "192.168.1.2", "10.1.1.2,172.28.240.18"):
            with self.subTest(value=value):
                validate_environment({**self.environment(), "FORWARDED_ALLOW_IPS": value})
        for value in ("*", "10.0.0.0/8", "172.28.240.18/32", "web", "127.0.0.1", "::1", "fc00::1",
                      "169.254.169.254", "100.64.0.1", "8.8.8.8", "0.0.0.0", "224.0.0.1",
                      "172.15.0.1", "172.32.0.1", "172.28.240.018", "172.28.240.18:3000", "172.28.240.18,", ",172.28.240.18"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_environment({**self.environment(), "FORWARDED_ALLOW_IPS": value})

    def test_trusted_hosts_are_explicit_and_include_probe_host(self):
        for value in ("api,127.0.0.1", "api.example.test,127.0.0.1", "172.28.240.19,127.0.0.1"):
            with self.subTest(value=value):
                validate_environment({**self.environment(), "TRUSTED_HOSTS": value})
        for value in ("api", "*,127.0.0.1", "*.example.test,127.0.0.1", "https://api,127.0.0.1",
                      "api:8000,127.0.0.1", "api/,127.0.0.1", "api,,127.0.0.1", "bad host,127.0.0.1",
                      "api.,127.0.0.1", "API,127.0.0.1", "bad_host,127.0.0.1", "-api,127.0.0.1",
                      "api-,127.0.0.1", "api..test,127.0.0.1", "999.1.1.1,127.0.0.1", "::1,127.0.0.1"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_environment({**self.environment(), "TRUSTED_HOSTS": value})

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
        self.assertEqual([call.args for call in db.command.await_args_list], [("ping",), ("hello",)])
        storage.head_bucket.assert_called_once_with(Bucket="test")
        storage.put_object.assert_not_called()

    async def test_storage_failure_fails_readiness(self):
        db = Mock(command=AsyncMock(side_effect=[{}, {"msg": "isdbgrid", "logicalSessionTimeoutMinutes": 30}]))
        with self.assertRaises(RuntimeError):
            await dependency_readiness(db, Mock(head_bucket=Mock(side_effect=RuntimeError("secret"))), "test")


class TargetValidation(unittest.TestCase):
    def settings(self):
        return ProductionRuntime().environment()

    def test_production_target_and_tls_rejections(self):
        valid=self.settings()
        validate_environment(valid)
        for change in ({"DB_NAME":"landvilla_dev"},{"S3_BUCKET":"landvilla-dev"},
                       {"MONGO_URL":"mongodb://db.invalid/landvilla_prod"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_prod?tls=false"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_prod?tlsInsecure=true"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_dev"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_prod?tls=true&tls=false"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_prod?retryWrites=true;tls=false"},
                       {"MONGO_URL":"mongodb+srv://db.invalid/landvilla_prod?retryWrites=true;tlsInsecure=true"},
                       {"WEB_API_IP_KEY":"e"*64},
                       {"CLIENT_IP_MODE":""}, {"WEB_API_IP_KEY":""}):
            with self.subTest(names=list(change)),self.assertRaises(RuntimeError): validate_environment({**valid,**change})

    def test_rehearsal_only_accepts_exact_local_targets(self):
        valid={**self.settings(),"DEPLOYMENT_TIER":"rehearsal","DB_NAME":"landvilla_rehearsal",
               "S3_BUCKET":"landvilla-property-media-rehearsal","S3_ENDPOINT":"http://storage:9000",
               "MONGO_URL":"mongodb://mongo:27017/landvilla_rehearsal?replicaSet=lv_rehearsal",
               "CORS_ORIGINS":"https://localhost:8443","WEB_APP_ORIGINS":"https://localhost:8443"}
        validate_environment(valid)
        for change in ({"DB_NAME":"landvilla_prod"},{"S3_BUCKET":"landvilla-property-media-prod"},
                       {"MONGO_URL":"mongodb+srv://external.invalid/landvilla_rehearsal"},
                       {"S3_ENDPOINT":"https://external.invalid"},{"DEPLOYMENT_TIER":"production"}):
            with self.subTest(names=list(change)),self.assertRaises(RuntimeError): validate_environment({**valid,**change})
