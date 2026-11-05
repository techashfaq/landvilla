"""Security review regressions: synthetic exceptions and mocked migration only."""
import contextlib
import importlib.util
import io
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import test_regressions as fixtures
from fastapi import HTTPException, UploadFile
from botocore.exceptions import ClientError, BotoCoreError

identity = fixtures.identity
marketplace = fixtures.marketplace
MARKER = "synthetic-sensitive-marker"
KEY = "synthetic-private-object-key"


def migration_module():
    spec = importlib.util.spec_from_file_location("migration_review", Path(__file__).parents[2] / "scripts/apply_identity_indexes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SecurityReview(unittest.IsolatedAsyncioTestCase):
    @contextlib.contextmanager
    def captured(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root = logging.getLogger()
        old_disabled = root.manager.disable
        logging.disable(logging.NOTSET)
        root.addHandler(handler)
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                yield stream
        finally:
            root.removeHandler(handler)
            logging.disable(old_disabled)

    def assert_safe(self, stream):
        for value in (MARKER, KEY):
            self.assertNotIn(value, stream.getvalue())
        self.assertNotIn("Traceback", stream.getvalue())

    def test_google_exception_is_sanitized(self):
        with self.captured() as output, patch.dict(fixtures.os.environ, GOOGLE_CLIENT_IDS="unit-client"), patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError(MARKER)):
            with self.assertRaises(HTTPException) as error:
                identity.verify_google("synthetic-token")
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.detail, "Invalid Google credential")
        self.assertIn("google_credential_invalid", output.getvalue())
        self.assert_safe(output)

    def test_google_transport_error_is_generic(self):
        from google.auth.exceptions import TransportError
        with self.captured() as output, patch.dict(fixtures.os.environ, GOOGLE_CLIENT_IDS="unit-client"), patch("google.oauth2.id_token.verify_oauth2_token", side_effect=TransportError(MARKER)):
            with self.assertRaises(HTTPException) as error:
                identity.verify_google("synthetic-token")
        self.assertEqual(error.exception.status_code, 503)
        self.assert_safe(output)

    def test_plan_unicode_matches_base(self):
        self.assertEqual([(p["name_en"], p["name_hi"]) for p in marketplace.DEFAULT_PLANS], [
            ("Featured · 15 days", "फ़ीचर्ड · 15 दिन"),
            ("Featured · 30 days", "फ़ीचर्ड · 30 दिन")])
        self.assertEqual([(p["price_inr"], p["duration_days"]) for p in marketplace.DEFAULT_PLANS], [(299, 15), (499, 30)])

    def test_r2_provider_errors_do_not_log_details_or_keys(self):
        for operation in ("put", "get", "delete"):
            for error in (ClientError({"Error": {"Code": "Denied", "Message": MARKER}}, "Synthetic"), BotoCoreError()):
                client = Mock()
                getattr(client, operation + "_object").side_effect = error
                with self.captured() as output, patch.object(marketplace, "_r2_client", return_value=client), patch.dict(fixtures.os.environ, S3_BUCKET="fixture"):
                    if operation == "delete":
                        marketplace._delete_r2_object(KEY)
                    else:
                        with self.assertRaises(HTTPException) as caught:
                            if operation == "put":
                                marketplace._put(KEY, b"fixture", "image/jpeg", "cloudflare_r2")
                            else:
                                marketplace._get(KEY, "cloudflare_r2")
                        self.assertEqual(caught.exception.status_code, 503)
                self.assertIn("r2_", output.getvalue())
                self.assert_safe(output)

    async def test_upload_metadata_failure_sanitized_and_cleanup_preserved(self):
        db = SimpleNamespace(files=SimpleNamespace(insert_one=AsyncMock(side_effect=RuntimeError(MARKER))))
        cleanup = Mock()
        file = UploadFile(filename="fixture.jpg", file=io.BytesIO(b"\xff\xd8\xff\x00"), headers=fixtures.httpx.Headers({"content-type": "image/jpeg"}))
        with self.captured() as output, patch.object(marketplace, "db", db), patch.object(marketplace, "_put", return_value={"path": KEY}), patch.object(marketplace, "_delete_r2_object", cleanup), patch.dict(fixtures.os.environ, STORAGE_PROVIDER="cloudflare_r2"):
            with self.assertRaises(HTTPException) as caught:
                await marketplace.upload_file(file, "property_photo", {"user_id": "fixture"})
        self.assertEqual(caught.exception.status_code, 503)
        cleanup.assert_called_once()
        self.assertIn("upload_metadata_failed", output.getvalue())
        self.assert_safe(output)

    def test_migration_import_has_no_io(self):
        with patch("dotenv.load_dotenv") as env, patch("motor.motor_asyncio.AsyncIOMotorClient") as client, patch("asyncio.run") as run:
            migration_module()
        env.assert_not_called()
        client.assert_not_called()
        run.assert_not_called()

    def test_migration_cli_requires_both_confirmations_before_io(self):
        module = migration_module()
        for args in ([], ["--apply"], ["--confirm-database", "landvilla_dev"], ["--apply", "--confirm-database", "wrong"]):
            with self.captured(), patch("dotenv.load_dotenv") as env, patch("motor.motor_asyncio.AsyncIOMotorClient") as client:
                self.assertEqual(module.main(args), 2)
            env.assert_not_called()
            client.assert_not_called()

    def test_migration_cli_production_and_unknown_environment_refused(self):
        module = migration_module()
        for environment in ("production", "PRODUCTION", "", "staging"):
            with self.captured(), patch("dotenv.load_dotenv"), patch.dict(fixtures.os.environ, {"APP_ENV": environment, "DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"}), patch("motor.motor_asyncio.AsyncIOMotorClient") as client:
                self.assertEqual(module.main(["--apply", "--confirm-database", "landvilla_dev"]), 2)
            client.assert_not_called()

    def fake_db(self):
        db = SimpleNamespace(name="landvilla_dev", command=AsyncMock(), users=SimpleNamespace(aggregate=Mock(return_value=SimpleNamespace(to_list=AsyncMock(return_value=[])))), schema_migrations=SimpleNamespace(find_one=AsyncMock(return_value=None), insert_one=AsyncMock()))
        client = Mock()
        client.__getitem__ = Mock(return_value=db)
        return db, client

    async def test_migration_refuses_wrong_database_before_connecting(self):
        module = migration_module()
        factory = Mock()
        with self.captured():
            code = await module.apply_indexes({"APP_ENV": "development", "DB_NAME": "other", "MONGO_URL": "synthetic"}, factory, AsyncMock(), Mock())
        self.assertEqual(code, 2)
        factory.assert_not_called()

    async def test_migration_duplicates_and_actual_db_mismatch_prevent_writes(self):
        module = migration_module()
        for wrong in (True, False):
            db, client = self.fake_db()
            if wrong:
                db.name = "other"
            else:
                db.users.aggregate.return_value.to_list.return_value = [{"groups": 1}]
            migration = AsyncMock()
            with self.captured():
                code = await module.apply_indexes({"APP_ENV": "development", "DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"}, Mock(return_value=client), migration, Mock())
            self.assertEqual(code, 2)
            migration.assert_not_awaited()
            db.schema_migrations.insert_one.assert_not_awaited()
            client.close.assert_called_once()

    async def test_migration_mock_success_and_errors_are_sanitized(self):
        module = migration_module()
        for fail in (False, True):
            db, client = self.fake_db()
            migration = AsyncMock(side_effect=RuntimeError(MARKER) if fail else None)
            with self.captured() as output:
                code = await module.apply_indexes({"APP_ENV": "development", "DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"}, Mock(return_value=client), migration, lambda: "fixture-time")
            self.assertEqual(code, 1 if fail else 0)
            if fail:
                db.schema_migrations.insert_one.assert_not_awaited()
            else:
                migration.assert_awaited_once_with(db)
                db.schema_migrations.insert_one.assert_awaited_once()
            client.close.assert_called_once()
            self.assert_safe(output)

    def test_migration_confirmed_cli_uses_mocked_application_only(self):
        module = migration_module()
        with self.captured() as output, patch("dotenv.load_dotenv") as env, patch.dict(fixtures.os.environ, {"APP_ENV": "development", "DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"}), patch.object(module, "apply_indexes", new_callable=AsyncMock, return_value=0) as apply, patch("motor.motor_asyncio.AsyncIOMotorClient") as factory:
            self.assertEqual(module.main(["--apply", "--confirm-database", "landvilla_dev"]), 0)
        apply.assert_awaited_once()
        factory.assert_not_called()
        env.assert_called_once()
        self.assert_safe(output)

    def test_migration_configuration_error_is_sanitized(self):
        module = migration_module()
        with self.captured() as output, patch("dotenv.load_dotenv", side_effect=RuntimeError(MARKER)):
            self.assertEqual(module.main(["--apply", "--confirm-database", "landvilla_dev"]), 1)
        self.assertIn("identity_migration_failed_review_required", output.getvalue())
        self.assert_safe(output)

    async def test_migration_connection_and_close_errors_are_sanitized(self):
        module = migration_module()
        db, client = self.fake_db()
        db.command.side_effect = RuntimeError(MARKER)
        client.close.side_effect = RuntimeError(KEY)
        migration = AsyncMock()
        with self.captured() as output:
            code = await module.apply_indexes({"APP_ENV": "development", "DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"}, Mock(return_value=client), migration, Mock())
        self.assertEqual(code, 1)
        migration.assert_not_awaited()
        self.assertIn("identity_migration_close_failed", output.getvalue())
        self.assert_safe(output)
