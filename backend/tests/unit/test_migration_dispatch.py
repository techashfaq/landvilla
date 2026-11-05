"""R1: ordinary seed paths must not provision opt-in identity indexes."""
import asyncio
import contextlib
import io
import os
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import test_regressions as fixtures
from test_security_review import migration_module

seed = fixtures.seed
server = fixtures.server


class MigrationDispatch(unittest.IsolatedAsyncioTestCase):
    def assert_no_identity(self, db):
        for coll, field in (("users", "mobile"), ("users", "google_sub"),
                            ("otp_challenges", "challenge_id"), ("otp_challenges", "expires_at"),
                            ("auth_limits", "expires_at")):
            self.assertFalse(any(list(i.get("key", [])) == [(field, 1)]
                                 for i in db.raw[coll].index_information().values()))
        self.assertIsNone(db.raw.schema_migrations.find_one({"version": "002_identity_indexes"}))

    def environments(self):
        for name in ("development", "production", None, "staging"):
            for database in ("landvilla_dev", "wrong_database"):
                env = dict(os.environ, DB_NAME=database, IDENTITY_ENABLED="false", SEED_ON_STARTUP="true")
                if name is None:
                    env.pop("APP_ENV", None)
                else:
                    env["APP_ENV"] = name
                yield name, database, env

    async def test_run_migrations_never_dispatches_identity(self):
        for name, database, env in self.environments():
            with self.subTest(environment=name, database=database), patch.dict(os.environ, env, clear=True):
                db = fixtures.MemoryDB()
                self.assertEqual(await seed.run_migrations(db), ["001_indexes"])
                self.assertEqual(await seed.run_migrations(db), [])
                self.assert_no_identity(db)

    async def test_seed_all_reference_data_without_identity(self):
        for name, database, env in self.environments():
            with self.subTest(environment=name, database=database), patch.dict(os.environ, env, clear=True):
                db = fixtures.MemoryDB()
                first = await seed.seed_all(db, include_demo=False)
                self.assertEqual(first["migrations_applied"], ["001_indexes"])
                cities = db.raw.cities.count_documents({})
                self.assertGreater(cities, 0)
                self.assertGreater(db.raw.localities.count_documents({}), 0)
                await seed.seed_all(db, include_demo=False)
                self.assertEqual(db.raw.cities.count_documents({}), cities)
                self.assert_no_identity(db)

    async def test_startup_seeding_without_identity(self):
        for name, database, env in self.environments():
            with self.subTest(environment=name, database=database), patch.dict(os.environ, env, clear=True):
                db = fixtures.MemoryDB()
                db.command = AsyncMock(return_value={"ok": 1})
                with patch.object(server, "db", db), patch.object(fixtures.marketplace, "db", db), patch.object(server, "SEED_DEMO", False), patch.object(server, "SEED_TEST_SESSIONS", False):
                    await server.startup()
                db.command.assert_awaited_once_with("ping")
                self.assertGreater(db.raw.cities.count_documents({}), 0)
                self.assert_no_identity(db)
        # Calling startup directly tests the dispatcher even for configurations
        # that production server import rejects before startup is reached.

    async def test_existing_identity_indexes_and_marker_preserved(self):
        db = fixtures.MemoryDB()
        await seed.m002_identity_indexes(db)  # explicit in-memory provisioning only
        await db.schema_migrations.insert_one({"version": "002_identity_indexes", "sentinel": "preserve"})
        before = {name: db.raw[name].index_information() for name in ("users", "otp_challenges", "auth_limits")}
        await seed.seed_all(db, include_demo=False)
        for name, indexes in before.items():
            for key, value in indexes.items():
                self.assertEqual(db.raw[name].index_information()[key], value)
        self.assertEqual(db.raw.schema_migrations.find_one({"version": "002_identity_indexes"})["sentinel"], "preserve")

    def test_standalone_seed_entrypoint_without_identity(self):
        for name, database, env in self.environments():
            with self.subTest(environment=name, database=database), patch.dict(os.environ, env, clear=True):
                db = fixtures.MemoryDB()
                client = Mock()
                client.__getitem__ = Mock(return_value=db)
                with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=client), patch("dotenv.load_dotenv"), patch.object(sys, "argv", ["seed.py"]), contextlib.redirect_stdout(io.StringIO()):
                    runpy.run_path(str(Path(seed.__file__)), run_name="__main__")
                client.close.assert_called_once()
                self.assertGreater(db.raw.cities.count_documents({}), 0)
                self.assert_no_identity(db)

    def test_dedicated_cli_missing_environment_and_uri_fail_closed(self):
        module = migration_module()
        for env in ({"DB_NAME": "landvilla_dev", "MONGO_URL": "synthetic"},
                    {"APP_ENV": "development", "DB_NAME": "landvilla_dev", "MONGO_URL": ""},
                    {"APP_ENV": "development", "DB_NAME": "wrong_database", "MONGO_URL": "synthetic"}):
            with self.subTest(keys=sorted(env)), patch.dict(os.environ, env, clear=True), patch("dotenv.load_dotenv"), patch("motor.motor_asyncio.AsyncIOMotorClient") as client, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(["--apply", "--confirm-database", "landvilla_dev"]), 2)
                client.assert_not_called()
