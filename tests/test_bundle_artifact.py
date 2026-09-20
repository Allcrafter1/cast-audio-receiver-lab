import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import Request

from cast_audio_lab.bundle_artifact import acquire, read_manifest, _HTTPSRedirects


class Response(io.BytesIO):
    def geturl(self):
        return "https://example.invalid/fixture"


class BundleArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.body = b'{"synthetic_fixture":true}'
        self.manifest = self.root / "manifest.json"
        self.target = self.root / "private" / "bundle.json"
        self.spec = {"schema_version": 1, "version": "test-1", "size": len(self.body),
                     "sha256": hashlib.sha256(self.body).hexdigest(),
                     "url": "https://example.invalid/fixture"}

    def pin(self):
        raw = json.dumps(self.spec).encode()
        self.manifest.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def fetch(self, body=None):
        return lambda *a, **kw: Response(self.body if body is None else body)

    def test_verified_import_is_private(self):
        self.assertEqual(acquire(self.manifest, self.pin(), self.target, opener=self.fetch()), "test-1")
        self.assertEqual(self.target.read_bytes(), self.body)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)

    def test_corruption_truncation_and_oversize_preserve_existing(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b"existing")
        for body in [b"wrong", self.body[:-1], self.body + b"x"]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                acquire(self.manifest, self.pin(), self.target, opener=self.fetch(body))
            self.assertEqual(self.target.read_bytes(), b"existing")
            self.assertFalse(list(self.target.parent.glob(".artifact-*")))

    def test_withdrawn_or_untrusted_manifest_never_fetches(self):
        def forbidden(*a, **kw):
            self.fail("must not fetch")
        with self.assertRaises(ValueError):
            acquire(self.manifest, self.pin()[::-1], self.target, opener=forbidden)
        self.spec["withdrawn"] = True
        with self.assertRaises(ValueError):
            acquire(self.manifest, self.pin(), self.target, opener=forbidden)

    def test_unavailable_remote_does_not_expose_signed_url(self):
        def missing(*a, **kw):
            raise OSError("https://private.invalid?token=SECRET")
        with self.assertRaises(ValueError) as caught:
            acquire(self.manifest, self.pin(), self.target, opener=missing)
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_bad_urls_and_sizes_are_rejected(self):
        for url in [42, [], "http://example.invalid/x", "https://u:p@example.invalid/x", "https://example.invalid/x?token=x"]:
            self.spec["url"] = url
            with self.assertRaises(ValueError):
                read_manifest(self.manifest, self.pin())
        self.spec["url"] = "https://example.invalid/x"
        for size in [0, -1, True, 50_000_000]:
            self.spec["size"] = size
            with self.assertRaises(ValueError):
                read_manifest(self.manifest, self.pin())

    def test_verified_but_invalid_json_is_not_installed(self):
        self.body = b"not-json"
        self.spec.update(size=len(self.body), sha256=hashlib.sha256(self.body).hexdigest())
        with self.assertRaises(ValueError):
            acquire(self.manifest, self.pin(), self.target, opener=self.fetch())
        self.assertFalse(self.target.exists())

    def test_symlink_destination_is_rejected(self):
        self.target.parent.mkdir()
        self.target.symlink_to(self.root / "elsewhere")
        with self.assertRaises(ValueError):
            acquire(self.manifest, self.pin(), self.target, opener=self.fetch())

    def test_redirect_cannot_downgrade_https(self):
        with self.assertRaises(ValueError):
            _HTTPSRedirects().redirect_request(Request(self.spec["url"]), None, 302,
                                              "redirect", {}, "http://example.invalid/bundle")

    def test_download_has_total_time_budget(self):
        with patch("cast_audio_lab.bundle_artifact.time.monotonic", side_effect=[0, 61]):
            with self.assertRaisesRegex(ValueError, "download rejected"):
                acquire(self.manifest, self.pin(), self.target, opener=self.fetch())
        self.assertFalse(self.target.exists())
