import importlib.util
import hashlib
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prepare",ROOT/"deploy/rehearsal/prepare.py")
prepare=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class FixtureTLS(unittest.TestCase):
    def test_repeated_setup_keeps_running_mail_trust_and_rejects_partial_state(self):
        with tempfile.TemporaryDirectory(dir=ROOT/".cache") as directory:
            path=Path(directory)
            prepare.prepare_tls(path)
            before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()}
            prepare.prepare_tls(path)
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir()})
        with tempfile.TemporaryDirectory(dir=ROOT/".cache") as directory:
            path=Path(directory)
            (path/"ca.crt").write_text("incomplete test fixture")
            with self.assertRaises(RuntimeError): prepare.prepare_tls(path)
