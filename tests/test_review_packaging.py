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

    def test_network_output_buttons_belong_to_their_own_group(self):
        groups = Groups()
        groups.feed((ROOT / "src/cast_audio_lab/web/index.html").read_text())
        self.assertIn({"dlna-name", "dlna-url", "add-dlna"}, groups.groups)
        self.assertIn({"sonos-name", "sonos-host", "add-sonos"}, groups.groups)

    def test_source_notices_are_present_and_packaged(self):
        for name in ["Vibecast-MIT.txt", "Chromium-BSD.txt", "airplay-cli-GPL.txt",
                     "airplay-cli-THIRD_PARTY_NOTICES.md", "libraop-upstream-statement.txt"]:
            self.assertTrue((ROOT / "licenses" / name).is_file())
        self.assertIn('"licenses/*"', (ROOT / "pyproject.toml").read_text())
        self.assertIn("/usr/share/doc/cast-audio-receiver/licenses/", (ROOT / "Containerfile").read_text())
