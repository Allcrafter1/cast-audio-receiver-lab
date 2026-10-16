# SPDX-License-Identifier: MPL-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.create_public_source_export import _validate_text, create


class PublicSourceExportTests(unittest.TestCase):
    def test_failed_write_does_not_publish_partial_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            source.write_bytes(b"reviewed source")
            target = root / "export"
            write = Path.write_bytes
            def fail_second_file(path, payload):
                if path.name == "second.txt":
                    raise OSError("disk full")
                return write(path, payload)
            with patch("tools.create_public_source_export._source_files", return_value=[
                    (source, Path("first.txt")), (source, Path("second.txt"))]), \
                    patch.object(Path, "write_bytes", fail_second_file):
                with self.assertRaisesRegex(OSError, "disk full"):
                    create(target)
            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob(".source-export-*")), [])

    def test_failed_validation_keeps_final_export_empty_and_allows_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            good, bad = root / "good.txt", root / "bad.txt"
            good.write_bytes(b"reviewed source")
            bad.write_bytes(b"invalid\0source")
            target = root / "export"
            target.mkdir()
            selected = [(good, Path("good.txt")), (bad, Path("bad.txt"))]
            with patch("tools.create_public_source_export._source_files", return_value=selected):
                with self.assertRaisesRegex(ValueError, "binary"):
                    create(target)
                self.assertEqual(list(target.iterdir()), [], "failed export became partially visible")
                bad.write_bytes(b"corrected source")
                report = create(target)
            self.assertEqual(len(report["files"]), 2)
            self.assertEqual((target / "good.txt").read_bytes(), b"reviewed source")
            self.assertEqual(list(root.glob(".source-export-*")), [])

    def test_documentation_device_identifiers_require_placeholders(self):
        path = Path("docs/device.md")
        _validate_text(path, b"Device 02:00:00:00:00:01")
        with self.assertRaisesRegex(ValueError, "device identifier"):
            _validate_text(path, b"Device 12:34:56:78:9A:BC")

    def test_only_reviewed_branding_binary_is_allowed(self):
        root = Path(__file__).parents[1]
        path = Path("cast-audio-receiver/icon.png")
        payload = (root / path).read_bytes()
        self.assertEqual(_validate_text(path, payload), hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError, "unreviewed branding"):
            _validate_text(path, payload + b"unreviewed data")
        with self.assertRaisesRegex(ValueError, "binary"):
            _validate_text(Path("unexpected.png"), payload)

    def test_export_is_allowlisted_text_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "export"
            report = create(target)
            self.assertTrue((target / "Containerfile").is_file())
            self.assertTrue((target / "LICENSING.md").is_file())
            self.assertTrue((target / "SECURITY.md").is_file())
            self.assertTrue((target / "docs/installation.md").is_file())
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
