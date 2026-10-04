# SPDX-License-Identifier: MPL-2.0
"""Review gates: exact pins, distribution notices and independent UI sections."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class Groups(HTMLParser):
    def __init__(self):
        super().__init__()
        self.groups = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "fieldset":
            self.current = set()
            self.groups.append(self.current)
        ident = dict(attrs).get("id")
        if ident and self.current is not None:
            self.current.add(ident)

    def handle_endtag(self, tag):
        if tag == "fieldset":
            self.current = None


class ReviewPackagingTests(unittest.TestCase):
    def test_publication_waits_for_both_native_smoke_tests(self):
        workflow = (ROOT / '.github/workflows/publish-image.yml').read_text()
        self.assertIn('runner: ubuntu-24.04-arm', workflow)
        self.assertIn('ha_arch: aarch64', workflow)
        self.assertIn('push-by-digest=true', workflow)
        self.assertIn('BUILD_VERSION=${{ steps.version.outputs.tag }}', workflow)
        self.assertIn('Verify native runtime before promoting', workflow)
        self.assertIn('aiohttp, lxml, zeroconf, async_upnp_client, soco', workflow)
        self.assertNotIn('import cast_audio_lab, cryptography', workflow)
        self.assertIn('needs: image', workflow)
        self.assertIn("for arch in ('amd64', 'arm64'):", workflow)
        self.assertIn("{('linux', 'amd64'), ('linux', 'arm64')} <= platforms", workflow)
        self.assertNotIn('platforms: linux/amd64\n', workflow)

    def test_ha_audio_and_ingress_session_are_enabled(self):
        config = (ROOT / "cast-audio-receiver/config.yaml").read_text()
        self.assertIn("\naudio: true\n", config)
        container = (ROOT / "Containerfile").read_text()
        self.assertIn("useradd --uid 1000 --gid 1000 --create-home", container)
        self.assertIn("ENV HOME=/home/cast-audio", container)
        script = (ROOT / "src/cast_audio_lab/web/app.js").read_text()
        self.assertIn('credentials: "same-origin"', script)
        self.assertNotIn('credentials: "omit"', script)
        self.assertIn('cache: "no-store"', script)

    def test_frontend_overlay_is_exact_and_promoted_commit_used_by_builds(self):
        lock = json.loads((ROOT / "config/vibecast-0.6.0.dev13-overlay.lock.json").read_text())
        self.assertEqual(hashlib.sha256((ROOT / lock["patch"]).read_bytes()).hexdigest(), lock["patch_sha256"])
        current = json.loads((ROOT / "config/vibecast-frontend.lock.json").read_text())
        self.assertEqual(current["reconstruction_base"], lock["base_commit"])
        self.assertEqual(current["reconstruction_overlay_sha256"], lock["patch_sha256"])
        for path in ["Containerfile", ".github/workflows/ci.yml"]:
            text = (ROOT / path).read_text()
            self.assertIn(current["commit"], text)
            self.assertNotIn("git apply", text)

    def test_airplay_asset_and_container_pin_match(self):
        lock = json.loads((ROOT / "config/cliairplay-linux-x86_64.lock.json").read_text())
        self.assertRegex(lock["sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(lock["checksums_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(lock["source_commit"], r"^[0-9a-f]{40}$")
        container = (ROOT / "Containerfile").read_text()
        self.assertIn("ARG CLIAIRPLAY_VERSION=" + lock["version"], container)
        self.assertIn("ARG CLIAIRPLAY_SHA256=" + lock["sha256"], container)

    def test_arm64_uses_the_same_versions_with_its_own_artifacts(self):
        config = ROOT / "config"
        x86 = json.loads((config / "container-linux-x86_64-cp312.wheels.json").read_text())
        arm = json.loads((config / "container-linux-aarch64-cp312.wheels.json").read_text())
        self.assertEqual({p["name"]: p["version"] for p in x86},
                         {p["name"]: p["version"] for p in arm})
        for wheel in arm:
            self.assertNotIn("x86_64", wheel["filename"])
            self.assertTrue(wheel["filename"].endswith("-any.whl") or "aarch64" in wheel["filename"])
        native = json.loads((config / "cliairplay-linux-aarch64.lock.json").read_text())
        original = json.loads((config / "cliairplay-linux-x86_64.lock.json").read_text())
        self.assertEqual(native["version"], original["version"])
        self.assertEqual(native["source_commit"], original["source_commit"])
        self.assertIn("ARG CLIAIRPLAY_ARM64_SHA256=" + native["sha256"], (ROOT / "Containerfile").read_text())

    def test_network_output_buttons_belong_to_their_own_group(self):
        groups = Groups()
        groups.feed((ROOT / "src/cast_audio_lab/web/index.html").read_text())
        self.assertIn({"dlna-name", "dlna-url", "add-dlna"}, groups.groups)
        self.assertIn({"sonos-name", "sonos-host", "add-sonos"}, groups.groups)

    def test_source_notices_are_present_and_packaged(self):
        license_bytes = (ROOT / "LICENSE").read_bytes()
        self.assertEqual(
            hashlib.sha256(license_bytes).hexdigest(),
            "3f3d9e0024b1921b067d6f7f88deb4a60cbe7a78e76c64e3f1d7fc3b779b9d04",
        )
        self.assertIn("Mozilla Public License Version 2.0", license_bytes.decode())
        self.assertIn('license = "MPL-2.0"', (ROOT / "pyproject.toml").read_text())
        licensing = (ROOT / "LICENSING.md").read_text()
        self.assertIn("Vibecast fork", licensing)
        self.assertIn("**MIT** license", licensing)
        for name in ["Vibecast-MIT.txt", "Chromium-BSD.txt", "airplay-cli-GPL.txt",
                     "airplay-cli-THIRD_PARTY_NOTICES.md", "libraop-upstream-statement.txt"]:
            self.assertTrue((ROOT / "licenses" / name).is_file())
        self.assertIn('"licenses/*"', (ROOT / "pyproject.toml").read_text())
        container = (ROOT / "Containerfile").read_text()
        self.assertIn("COPY LICENSE LICENSING.md THIRD_PARTY_NOTICES.md", container)
        self.assertIn("/usr/share/doc/cast-audio-receiver/licenses/", container)
        self.assertIn('org.opencontainers.image.licenses="NOASSERTION"', container)
        self.assertIn('io.cast-audio-receiver.project-license="MPL-2.0"', container)

    def test_project_source_files_have_mpl_spdx_headers(self):
        suffixes = {".py", ".sh", ".js", ".cjs", ".css", ".html"}
        for directory in ("src", "tools", "tests", "research"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and path.suffix in suffixes:
                    self.assertIn(
                        "SPDX-License-Identifier: MPL-2.0",
                        path.read_text(),
                        path.relative_to(ROOT),
                    )
