import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("release",Path(__file__).resolve().parents[1]/"scripts/record-release.py")
release=importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ArtifactIdentity(unittest.TestCase):
    def test_tag_alone_cannot_substitute_revision_or_tested_image(self):
        commit="a"*40
        identity="sha256:"+"b"*64
        image={"Os":"linux","Id":identity,"Config":{"Labels":{"org.opencontainers.image.revision":commit}},
               "Created":"2026-11-12T00:00:00Z","Architecture":"amd64"}
        self.assertEqual(release.image_record(image,"api:"+commit,commit,identity)["image_id"],identity)
        for changed in ({**image,"Config":{"Labels":None}}, {**image,"Os":"windows"},
                        {**image,"Id":"sha256:"+"c"*64}):
            with self.assertRaises(RuntimeError): release.image_record(changed,"api:"+commit,commit,identity)
        with self.assertRaises(RuntimeError): release.image_record(image,"api:"+commit,"d"*40,identity)
