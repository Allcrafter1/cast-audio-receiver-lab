import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("resource_profile",
    Path(__file__).parents[1] / "tools/resource_profile.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def record(start=1, ticks=10, pss=5):
    return dict(start=start, ticks=ticks, pss_kib=pss, rss_kib=20)


class ResourceTests(unittest.TestCase):
    def test_interval_cpu_and_shared_memory(self):
        result = module.summarize({10: record()}, {10: record(ticks=60)}, .5, 100)
        self.assertEqual(result["cpu_percent"], 100)
        self.assertEqual(result["pss_kib"], 5)
        self.assertEqual(result["rss_kib"], 20)

    def test_reused_pid_and_missing_pss_are_not_misreported(self):
        result = module.summarize({10: record()}, {10: record(start=2, ticks=900, pss=None)}, 1, 100)
        self.assertEqual(result["cpu_percent"], 0)
        self.assertEqual(result["cpu_unmatched_processes"], 1)
        self.assertEqual(result["exited_processes"], 1)
        self.assertIsNone(result["pss_kib"])

    def test_tree_selection_and_awkward_process_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, parent in ((20, 1), (21, 20), (22, 21), (99, 1)):
                path = root / str(pid)
                path.mkdir()
                fields = ["0"] * 22
                fields[0], fields[1], fields[11], fields[12], fields[19], fields[21] = "S", str(parent), "5", "8", "42", "3"
                (path / "stat").write_text(f"{pid} (private ) name) " + " ".join(fields))
                (path / "smaps_rollup").write_text("Pss: 7 kB\n")
            result = module.snapshot([20, 21], root)
            self.assertEqual(set(result), {20, 21, 22})
            self.assertEqual(result[20]["ticks"], 13)
            self.assertNotIn("private", str(result))
