import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.create_public_source_export import _validate_text, create


class PublicSourceExportTests(unittest.TestCase):
    def test_export_is_allowlisted_text_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "export"
            report = create(target)
            self.assertTrue((target / "Containerfile").is_file())
            self.assertTrue((target / "src/cast_audio_lab/runtime.py").is_file())
            self.assertTrue((target / "research/legacy_python_receiver/README.md").is_file())
            self.assertFalse((target / ".state").exists())
            self.assertFalse((target / "artifacts").exists())
            self.assertFalse((target / "node-receiver").exists())
            self.assertFalse((target / "AGENTS.md").exists())
            manifest = json.loads((target / "SOURCE-MANIFEST.json").read_text())
            self.assertEqual(report, manifest)
            for item in manifest["files"]:
                path = target / item["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                payload = path.read_bytes()
                self.assertEqual(len(payload), item["bytes"])
                self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])

    def test_refuses_private_and_binary_material(self):
        with self.assertRaisesRegex(ValueError, "private marker"):
            _validate_text(
                Path("secret.txt"), b"-----BEGIN PRIVATE " + b"KEY-----\n"
            )
        with self.assertRaisesRegex(ValueError, "binary"):
            _validate_text(Path("blob.txt"), b"text\0data")
        with self.assertRaisesRegex(ValueError, "forbidden release artifact"):
            _validate_text(Path("capture.pcap"), b"text")

    def test_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target / "existing").write_text("keep")
            with self.assertRaisesRegex(ValueError, "not empty"):
                create(target)


if __name__ == "__main__":
    unittest.main()
