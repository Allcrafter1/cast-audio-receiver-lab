import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("source_inventory", Path(__file__).parents[1]/"tools/source_inventory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceInventoryTests(unittest.TestCase):
    def test_selects_build_sources_without_state_or_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"Cargo.toml").write_text("manifest")
            (root/"crates/new/src").mkdir(parents=True)
            (root/"crates/new/src/lib.rs").write_text("private source content")
            with patch.object(module, "git", side_effect=[
                b"Cargo.toml\0crates/new/src/lib.rs\0crates/deleted.rs\0.state/key.pem\0tools/private.py\0", b"abc\n"]):
                result = module.inventory(root)
            self.assertEqual(set(result["files"]), {"Cargo.toml", "crates/new/src/lib.rs", "crates/deleted.rs"})
            self.assertIsNone(result["files"]["crates/deleted.rs"])
            self.assertNotIn("private source content", str(result))
            self.assertNotIn(directory, str(result))

    def test_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"Cargo.toml").symlink_to(root/"outside")
            with patch.object(module, "git", return_value=b"Cargo.toml\0"):
                with self.assertRaises(ValueError):
                    module.inventory(root)

    def test_comparison_reports_changed_missing_and_added(self):
        result = module.compare({"base_commit": "a", "files": {"same": "1", "changed": "1", "left": "2"}},
                                {"base_commit": "a", "files": {"same": "1", "changed": "2", "right": "2"}})
        self.assertEqual(result, {"same_base": True, "only_left": ["left"], "only_right": ["right"], "different": ["changed"]})
