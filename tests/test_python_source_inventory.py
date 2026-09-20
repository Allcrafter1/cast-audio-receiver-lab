import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.python_source_inventory import inventory, source_archive


class PythonSourceInventoryTests(unittest.TestCase):
    def test_checked_inventory_matches_current_container_wheels(self):
        root = Path(__file__).resolve().parents[1]
        wheels = json.loads((root / "config/container-linux-x86_64-cp312.wheels.json").read_text())
        record = json.loads((root / "config/container-python-source-references.json").read_text())
        self.assertEqual({(p["name"], p["version"], p["sha256"]) for p in wheels},
                         {(p["name"], p["version"], p["wheel_sha256"]) for p in record["packages"]})
        self.assertTrue(all(p["sources"] for p in record["packages"]))

    def test_source_download_verified_without_execution(self):
        class Response(io.BytesIO):
            def geturl(self):
                return "https://files.pythonhosted.org/example.tar.gz"
        body = b"opaque-source-bytes"
        self.metadata["urls"][1]["size"] = len(body)
        self.metadata["urls"][1]["digests"]["sha256"] = hashlib.sha256(body).hexdigest()
        report = inventory([self.wheel], lambda *_: self.metadata)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sources.zip"
            with self.assertRaises(ValueError):
                source_archive(report, target, lambda *a, **k: Response(b"wrong"))
            self.assertFalse(target.exists())
            result = source_archive(report, target, lambda *a, **k: Response(body))
            self.assertTrue(result["source_archives_downloaded"])
            self.assertFalse(result["embedded_native_source_coverage_verified"])
            with zipfile.ZipFile(target) as archive:
                self.assertEqual(archive.read("example.tar.gz"), body)
            with self.assertRaises(FileExistsError):
                source_archive(report, target, lambda *a, **k: Response(body))

    def setUp(self):
        self.wheel = {"name": "example", "version": "1", "filename": "example.whl", "sha256": "a" * 64}
        self.metadata = {"urls": [
            {"filename": "example.whl", "packagetype": "bdist_wheel", "digests": {"sha256": "a" * 64}},
            {"filename": "example.tar.gz", "packagetype": "sdist", "digests": {"sha256": "b" * 64},
             "url": "https://files.pythonhosted.org/packages/example.tar.gz", "size": 42}]}

    def test_verified_wheel_with_source_reference(self):
        result = inventory([self.wheel], lambda *_: self.metadata)
        self.assertEqual(result["packages"][0]["sources"][0]["sha256"], "b" * 64)
        self.assertFalse(result["source_archives_downloaded"])

    def test_missing_source_is_not_silently_cleared(self):
        self.metadata["urls"].pop()
        result = inventory([self.wheel], lambda *_: self.metadata)
        self.assertEqual(result["packages"][0]["status"], "no-sdist-review-required")

    def test_mismatch_or_untrusted_source_rejected(self):
        bad = copy.deepcopy(self.metadata)
        bad["urls"][0]["digests"]["sha256"] = "c" * 64
        with self.assertRaises(ValueError):
            inventory([self.wheel], lambda *_: bad)
        for url in ("http://files.pythonhosted.org/x", "https://other.invalid/x",
                    "https://files.pythonhosted.org/x?secret=x"):
            bad = copy.deepcopy(self.metadata)
            bad["urls"][1]["url"] = url
            with self.assertRaises(ValueError):
                inventory([self.wheel], lambda *_: bad)
