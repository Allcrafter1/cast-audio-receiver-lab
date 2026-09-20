"""Offline consistency gates for the release records we actually maintain."""
import hashlib
import json
from pathlib import Path
import re
import tomllib
import unittest

from cast_audio_lab import __version__

ROOT = Path(__file__).parents[1]


class ReleaseRecordTests(unittest.TestCase):
    def test_historical_receiver_is_outside_release_package(self):
        legacy_modules = {
            "auth.py",
            "lounge.py",
            "mdns.py",
            "protocol.py",
            "server.py",
            "tls.py",
            "wire.py",
            "youtube_dial.py",
            "youtube_receiver.py",
        }
        package = ROOT / "src" / "cast_audio_lab"
        research = (
            ROOT
            / "research"
            / "legacy_python_receiver"
            / "legacy_cast_receiver"
        )
        self.assertFalse(legacy_modules & {path.name for path in package.glob("*.py")})
        self.assertEqual(
            legacy_modules,
            legacy_modules & {path.name for path in research.glob("*.py")},
        )

    def test_package_and_project_versions_agree(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(project["project"]["version"], __version__)

    def test_recorded_complete_patches_have_exact_hashes(self):
        records = sorted((ROOT / "config").glob("vibecast-*-source.lock.json"))
        self.assertTrue(records, "no frontend source lock records")
        for path in records:
            with self.subTest(record=path.name):
                record = json.loads(path.read_text())
                patch = (ROOT / record["patch"]).resolve()
                self.assertTrue(patch.is_relative_to(ROOT.resolve()))
                self.assertEqual(patch.suffix, ".patch")
                self.assertRegex(record["upstream_commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(), record["patch_sha256"])
                if "source_repository" in record:
                    self.assertRegex(
                        record["source_repository"],
                        r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git$",
                    )
                    self.assertRegex(record["source_commit"], r"^[0-9a-f]{40}$")

    def test_wheel_manifest_and_requirements_agree(self):
        manifests = sorted((ROOT / "config").glob("*.wheels.json"))
        self.assertTrue(manifests, "no wheel inventories")
        for manifest in manifests:
            with self.subTest(manifest=manifest.name):
                lock = manifest.with_name(manifest.name.replace(".wheels.json", ".lock.txt"))
                items = json.loads(manifest.read_text())
                expected = {f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}" for item in items}
                actual = {line for line in lock.read_text().splitlines()
                          if line and not line.startswith("#")}
                self.assertEqual(actual, expected)
                self.assertEqual(len(items), len(expected))
                normalized = {re.sub(r"[-_.]+", "-", item["name"]).lower() for item in items}
                self.assertEqual(len(normalized), len(items))
                for item in items:
                    self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_container_runtime_lock_covers_declared_runtime_dependencies(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text())
        declared = list(project["project"]["dependencies"])
        declared.extend(project["project"]["optional-dependencies"]["youtube"])
        declared.extend(project["project"]["optional-dependencies"]["dlna"])
        declared.extend(project["project"]["optional-dependencies"]["sonos"])
        lock = json.loads(
            (ROOT / "config" / "container-linux-x86_64-cp312.wheels.json").read_text()
        )
        locked_names = {
            re.sub(r"[-_.]+", "-", item["name"]).lower() for item in lock
        }
        for requirement in declared:
            name = re.split(r"[<>=!~\[; ]", requirement, maxsplit=1)[0]
            normalized = re.sub(r"[-_.]+", "-", name).lower()
            with self.subTest(requirement=requirement):
                self.assertIn(normalized, locked_names)
