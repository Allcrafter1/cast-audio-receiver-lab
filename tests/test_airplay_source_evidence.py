import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_airplay_source_evidence import verify


class SourceEvidenceTests(unittest.TestCase):
    def test_history_evidence_does_not_claim_binary_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "proxy/targets/linux/x86_64/libcrypto.a"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"synthetic archive")
            record = {
                "openssl_proxy_path": "proxy", "airplay_commit": "airplay",
                "openssl_proxy_commit": "proxy", "binary_introduction_commit": "introduction",
                "matching_version_source_commit": "candidate", "recorded_source_commit": "old",
                "openssl_version": "3.5.4", "libcrypto_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            }
            replies = ["airplay", "proxy", "old", "candidate", "", "MAJOR=3\nMINOR=5\nPATCH=4"]
            with patch("tools.check_airplay_source_evidence.git", side_effect=replies):
                result = verify(root, record)
            self.assertTrue(result["passed"])
            self.assertFalse(result["binary_reproducibility_verified"])
            self.assertTrue(result["source_override_required"])
            archive.write_bytes(b"changed archive")
            with patch("tools.check_airplay_source_evidence.git", side_effect=replies):
                self.assertFalse(verify(root, record)["passed"])
            replies[4] = "targets/linux/x86_64/libcrypto.a"
            with patch("tools.check_airplay_source_evidence.git", side_effect=replies):
                self.assertFalse(verify(root, record)["checks"]["unchanged_archive_tree_and_recipe"])
