# SPDX-License-Identifier: MPL-2.0
import os
import hashlib
import io
import json
from http.client import BadStatusLine, IncompleteRead
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cast_audio_lab.container_bootstrap import import_certificate_bundle
from cast_audio_lab.bundle_artifact import acquire


class BootstrapReliabilityTests(unittest.TestCase):
    def test_http_protocol_failures_are_sanitized_and_keep_existing_artifact(self):
        for failure in (BadStatusLine("private-token"), IncompleteRead(b"partial")):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                payload = b'{"synthetic":true}'
                raw = json.dumps({"schema_version": 1, "version": "test", "size": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(), "url": "https://example.invalid/bundle"}).encode()
                manifest = root / "manifest.json"
                manifest.write_bytes(raw)
                destination = root / "certs.json"
                destination.write_bytes(b"existing")
                def fail(*args, **kwargs):
                    raise failure
                with self.assertRaisesRegex(ValueError, "download rejected") as caught:
                    acquire(manifest, hashlib.sha256(raw).hexdigest(), destination, opener=fail)
                self.assertNotIn("private-token", str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)
                self.assertEqual(destination.read_bytes(), b"existing")
                self.assertEqual(list(root.glob(".artifact-*")), [])

    def test_slow_artifact_stream_checks_budget_between_network_reads(self):
        clock = [0]
        payload = b'{"synthetic":"' + b'x' * 100 + b'"}'
        class DripResponse(io.BytesIO):
            def geturl(self):
                return "https://example.invalid/bundle"
            def read(self, size=-1):
                # A buffered HTTP read waits to fill its requested size,
                # although each individual network receive meets its timeout.
                result = super().read(size)
                clock[0] += len(result)
                return result
            def read1(self, size=-1):
                clock[0] += 1
                return super().read(1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            raw = json.dumps({"schema_version": 1, "version": "test", "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(), "url": "https://example.invalid/bundle"}).encode()
            manifest.write_bytes(raw)
            destination = root / "certs.json"
            destination.write_bytes(b"existing")
            with patch("cast_audio_lab.bundle_artifact.time.monotonic", side_effect=lambda: clock[0]):
                with self.assertRaises(ValueError):
                    acquire(manifest, hashlib.sha256(raw).hexdigest(), destination,
                            opener=lambda *a, **kw: DripResponse(payload))
            self.assertLessEqual(clock[0], 61)
            self.assertEqual(destination.read_bytes(), b"existing")

    def test_interrupted_import_does_not_block_restart_or_delete_unowned_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "private").mkdir()
            source = root / "source.json"
            source.write_bytes(b'{"synthetic":true}')
            stale = root / "private/certs.json.importing"
            stale.write_bytes(b"interrupted import")
            with patch.dict(os.environ, {"CAST_AUDIO_CERTS": str(source)}):
                imported = import_certificate_bundle(root, uid=os.getuid(), gid=os.getgid())
            self.assertEqual(imported.read_bytes(), source.read_bytes())
            self.assertEqual(stale.read_bytes(), b"interrupted import")
            self.assertEqual(imported.stat().st_mode & 0o777, 0o600)

    def test_in_place_import_still_validates_certificate_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "private").mkdir()
            source = root / "private/certs.json"
            source.write_bytes(b"")
            with patch.dict(os.environ, {"CAST_AUDIO_CERTS": str(source)}):
                with self.assertRaisesRegex(ValueError, "size"):
                    import_certificate_bundle(root, uid=os.getuid(), gid=os.getgid())
