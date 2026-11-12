"""Offline evidence-integrity checks; no scanner/image/network execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("image_security", ROOT / "scripts/scan-rehearsal-images.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)
IMAGE = "sha256:" + "a" * 64
COMMIT = "b" * 40


class ImageSecurityEvidence(unittest.TestCase):
    def setUp(self):
        self.image = {"Id": IMAGE, "Os": "linux", "Architecture": "amd64", "RootFS": {"Layers": ["sha256:" + "c" * 64]},
                      "Config": {"Labels": {"org.opencontainers.image.revision": COMMIT}, "Env": ["NEVER_RECORD=value"]}}
        self.artifact = {"Id": IMAGE, "revision": COMMIT}
        self.package = {"id": "package-id", "name": "zlib", "version": "1.0", "purl": "pkg:apk/alpine/zlib@1.0",
                        "locations": [{"path": "/lib/apk/db/installed", "layerID": "sha256:" + "c" * 64}]}
        self.sbom = {"source": {"type": "image", "metadata": {"imageID": IMAGE, "os": "linux", "architecture": "amd64", "layers": ["layer"]}},
                     "artifacts": [self.package], "descriptor": {"name": "syft"}}
        self.report = {"source": {"type": "image", "target": {"imageID": IMAGE}}, "matches": [
            {"artifact": {"id": "package-id", "name": "zlib", "version": "1.0", "type": "apk"},
             "vulnerability": {"id": "CVE-fixture", "severity": "High", "fix": {"state": "not-fixed", "versions": []}},
             "matchDetails": [{"found": {"versionConstraint": "< 2.0"}}]}]}

    def test_exact_runtime_identity_and_no_environment_capture(self):
        identity = scanner.image_identity(self.image, IMAGE, self.artifact, COMMIT)
        self.assertNotIn("Config", identity)
        self.assertNotIn("NEVER_RECORD", json.dumps(identity))
        for mutation in ({"Id": "sha256:" + "d" * 64}, {"Os": "windows"}, {"RootFS": {"Layers": []}}):
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                scanner.image_identity({**self.image, **mutation}, IMAGE, self.artifact, COMMIT)

    def test_vendor_reference_must_match_an_observed_manifest(self):
        reference = "vendor/image:1@sha256:" + "d" * 64
        with self.assertRaises(RuntimeError):
            scanner.image_identity(self.image, reference, None, COMMIT)
        metadata = {**self.image, "RepoDigests": ["vendor/image@sha256:" + "d" * 64]}
        scanner.image_identity(metadata, reference, None, COMMIT)
        with self.assertRaises(RuntimeError):
            scanner.image_identity(metadata, "vendor/image:latest", None, COMMIT)

    def test_sbom_wrong_image_platform_or_empty_catalog_rejected(self):
        scanner.validate_sbom(self.sbom, self.image)
        for key, value in (("imageID", "wrong"), ("os", "windows"), ("layers", [])):
            sbom = copy.deepcopy(self.sbom)
            sbom["source"]["metadata"][key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                scanner.validate_sbom(sbom, self.image)
        with self.assertRaises(RuntimeError):
            scanner.validate_sbom({**self.sbom, "artifacts": []}, self.image)

    def test_no_ignored_matches_or_unknown_packages(self):
        for report in ({**self.report, "ignoredMatches": [{"reason": "unfixed"}]},
                       {**self.report, "source": {"type": "image", "target": {"imageID": "wrong"}}}):
            with self.assertRaises(RuntimeError):
                scanner.summarize_matches(report, self.sbom, self.image, Path("sbom.json"))
        sbom = {**self.sbom, "artifacts": []}
        with self.assertRaises(RuntimeError):
            scanner.summarize_matches(self.report, sbom, self.image, Path("sbom.json"))

    def test_provenance_ranges_and_unfixed_high_remain_blocking(self):
        records = scanner.summarize_matches(self.report, self.sbom, self.image, Path("sbom.json"))
        self.assertEqual(records[0]["location_provenance"], self.package["locations"])
        self.assertEqual(records[0]["match_details"][0]["found"]["versionConstraint"], "< 2.0")
        self.assertEqual(scanner.gate(records), "FAIL")
        self.assertEqual(scanner.gate([{"severity": "Critical"}]), "FAIL")
        self.assertEqual(scanner.gate([{"severity": "Medium"}]), "PASS")

    def test_file_evidence_checksum_covers_exact_bytes(self):
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory, patch.object(scanner, "WORK", Path(directory)):
            target = Path(directory) / "test.json"
            record = scanner.write_evidence(target, {"safe": True})
            self.assertEqual(record["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(record["bytes"], len(target.read_bytes()))
            self.assertEqual(record["path"], "test.json")


if __name__ == "__main__":
    unittest.main()
