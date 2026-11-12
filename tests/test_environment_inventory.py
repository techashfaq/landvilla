import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location("inventory",Path(__file__).resolve().parents[1]/"scripts/inspect-production-inputs.py")
inventory=importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class EnvironmentInventory(unittest.TestCase):
    def test_names_only_no_evaluation_and_duplicate_detection(self):
        content="MONGO_URL=synthetic-sensitive-canary\nDB_NAME=one\nDB_NAME=two\nOTP_HMAC_SECRET=''\nSTORAGE_PROVIDER=$(not-executed)\n"
        status=inventory.assignment_status(content,inventory.API_REQUIRED)
        self.assertEqual(status["DB_NAME"],"DUPLICATE")
        self.assertEqual(status["OTP_HMAC_SECRET"],"EMPTY")
        self.assertEqual(status["S3_ENDPOINT"],"MISSING")
        output=io.StringIO()
        with patch.object(Path,"read_text",return_value=content),contextlib.redirect_stdout(output):
            self.assertFalse(inventory.inspect(Path("unused"),inventory.API_REQUIRED))
        self.assertNotIn("synthetic-sensitive-canary",output.getvalue())
        self.assertNotIn("not-executed",output.getvalue())
        self.assertNotIn("one",output.getvalue())

    def test_read_failure_does_not_echo_sensitive_exception(self):
        output=io.StringIO()
        with patch.object(Path,"read_text",side_effect=OSError("sensitive-canary")),contextlib.redirect_stdout(output):
            self.assertFalse(inventory.inspect(Path("unused"),inventory.API_REQUIRED))
        self.assertNotIn("sensitive-canary",output.getvalue())
