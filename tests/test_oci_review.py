import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.inspect_oci_review import inspect


class OciReviewTests(unittest.TestCase):
    def fixture(self, path, *, wrong_subject=False, corrupt=False, missing_sbom=False):
        with tarfile.open(path, "w") as archive:
            def add(name, raw):
                item = tarfile.TarInfo(name)
                item.size = len(raw)
                archive.addfile(item, io.BytesIO(raw))
            def blob(value):
                raw = json.dumps(value).encode()
                digest = hashlib.sha256(raw).hexdigest()
                add("blobs/sha256/" + digest, raw + b" " if corrupt else raw)
                return {"digest": "sha256:" + digest}
            image = blob({"config": blob({"architecture": "amd64"}), "layers": []})
            layers = []
            for kind in (["https://slsa.dev/provenance/v0.2"] if missing_sbom else
                         ["https://spdx.dev/Document", "https://slsa.dev/provenance/v0.2"]):
                layer = blob({"predicateType": kind,
                    "subject": [{"digest": {"sha256": "0" * 64 if wrong_subject else image["digest"][7:]}}],
                    "predicate": {"packages": [{"name": "example", "versionInfo": "1", "licenseDeclared": "MIT"}],
                                  "secret_fixture": "must-not-print-provenance"}})
                layer["mediaType"] = "application/vnd.in-toto+json"
                layers.append(layer)
            attestation = blob({"layers": layers})
            add("index.json", json.dumps({"manifests": [image, attestation]}).encode())

    def test_bounded_summary_matches_subject_without_dumping_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.tar"
            self.fixture(path)
            result = inspect(path)
            self.assertEqual(result["package_count"], 1)
            self.assertFalse(result["runtime_layers_verified"])
            self.assertNotIn("must-not-print", str(result))
            verified = inspect(path, verify_blobs=True)
            self.assertTrue(verified["runtime_layers_verified"])
            self.assertEqual(verified["verified_blob_count"], 5)
            self.assertFalse(verified["runtime_contents_reviewed"])

    def test_rejects_corrupt_unreferenced_blob_and_duplicate_member(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.tar"
            for name in ("blobs/sha256/" + "0" * 64, "index.json"):
                self.fixture(path)
                with tarfile.open(path, "a") as archive:
                    member = tarfile.TarInfo(name)
                    member.size = 2
                    archive.addfile(member, io.BytesIO(b"{}"))
                with self.assertRaises(ValueError):
                    inspect(path, verify_blobs=True)

    def test_rejects_mismatches_and_missing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.tar"
            for options in ({"wrong_subject": True}, {"corrupt": True}, {"missing_sbom": True}):
                with self.subTest(options=options):
                    self.fixture(path, **options)
                    with self.assertRaises(ValueError):
                        inspect(path)
