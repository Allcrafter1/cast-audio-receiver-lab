import unittest
from unittest.mock import patch

from tools.check_public_history import inspect


class HistoryTests(unittest.TestCase):
    def test_scans_old_blob_not_only_current_tree(self):
        def git(root, *args):
            if args[0] == "rev-list": return b"new\nold\n"
            if args[0] == "ls-tree":
                oid = b"1" if args[-1] == "new" else b"2"
                return b"100644 blob " + oid + b"\tconfig.txt\0"
            if args[1] == "-s": return b"100"
            return b"safe" if args[-1] == "1" else b"-----BEGIN PRIVATE " + b"KEY-----"
        with patch("tools.check_public_history.run_git", side_effect=git):
            result = inspect("unused")
        self.assertFalse(result["passed"])
        self.assertEqual(result["checked_blobs"], 2)
        self.assertEqual(len(result["issues"]), 1)
        self.assertNotIn("BEGIN", str(result))

    def test_empty_repository_is_not_cleared(self):
        with patch("tools.check_public_history.run_git", return_value=b""):
            self.assertFalse(inspect("unused")["passed"])

    def test_symlink_requires_review(self):
        with patch("tools.check_public_history.run_git", side_effect=[
            b"commit\n", b"120000 blob 1\tlink\0"
        ]):
            result = inspect("unused")
        self.assertFalse(result["passed"])
        self.assertEqual(result["checked_blobs"], 0)
