from pathlib import Path
import subprocess
import re
import tarfile
import tempfile
import unittest

from tools.package_airplay_source import COMPONENTS, PROJECT, package, safe_member


class AirplaySourcePackageTests(unittest.TestCase):
    def test_git_recipe_and_archive_component_pins_agree(self):
        recipe = (PROJECT / "tools/build_airplay_source_candidate.sh").read_text()
        recorded = re.findall(r'^export_source (\S+) ([0-9a-f]{40}) "\$cast_output/([^"\n]+)"',
                              recipe, re.MULTILINE)
        self.assertEqual(recorded, COMPONENTS)

    def test_source_archive_uses_committed_files_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL)
            git("init")
            (repo / "source.c").write_text("/* committed */")
            (repo / "lib.a").write_bytes(b"not-source")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")
            revision = git("rev-parse", "HEAD").decode().strip()
            (repo / "source.c").write_text("private-working-tree-change")
            (repo / "untracked.secret").write_text("must-not-include")
            components = [(".", revision, "airplay")]
            a = package(repo, root / "a.tar.gz", components=components)
            b = package(repo, root / "b.tar.gz", components=components)
            self.assertEqual(a["sha256"], b["sha256"])
            with tarfile.open(root / "a.tar.gz") as archive:
                self.assertEqual(archive.extractfile("airplay/source.c").read(), b"/* committed */")
                self.assertNotIn("airplay/lib.a", archive.getnames())
                self.assertNotIn("airplay/untracked.secret", archive.getnames())
                self.assertIn("SOURCE-COMPONENTS.json", archive.getnames())
            with self.assertRaises(FileExistsError):
                package(repo, root / "a.tar.gz", components=components)
            with self.assertRaises(subprocess.CalledProcessError):
                package(repo, root / "failed.tar.gz", components=[(".", "missing-revision", "airplay")])
            self.assertFalse((root / "failed.tar.gz").exists())

    def test_rejects_escaping_paths_and_links(self):
        for name in ("../bad", "/absolute"):
            with self.assertRaises(ValueError):
                safe_member(tarfile.TarInfo(name))
        link = tarfile.TarInfo("include/link")
        link.type = tarfile.SYMTYPE
        for target in ("../../outside", "/outside"):
            link.linkname = target
            with self.assertRaises(ValueError):
                safe_member(link)
        link.linkname = "../source.c"
        self.assertTrue(safe_member(link))
