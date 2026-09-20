import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cast_audio_lab import container_bootstrap
from cast_audio_lab.bundle_artifact import read_manifest


class ContainerBootstrapTests(unittest.TestCase):
    def test_prepares_only_known_state_directories(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            unrelated = root / "options.json"
            unrelated.write_text("{}")

            container_bootstrap.prepare_state(root, os.getuid(), os.getgid())

            self.assertEqual(
                {path.name for path in root.iterdir()},
                {"options.json", "frontend", "speakers", "private"},
            )
            self.assertEqual(unrelated.read_text(), "{}")
            for name in container_bootstrap.STATE_DIRECTORIES:
                self.assertEqual((root / name).stat().st_mode & 0o777, 0o700)

    def test_refuses_a_symlink_as_owned_state_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            (root / "private").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "refusing symlink"):
                container_bootstrap.prepare_state(root, os.getuid(), os.getgid())

    def test_root_bootstrap_drops_privileges_before_exec(self):
        calls = []
        with patch.object(container_bootstrap.os, "geteuid", return_value=0), \
             patch.object(container_bootstrap, "prepare_state", side_effect=lambda path: calls.append(("prepare", path))), \
             patch.object(container_bootstrap, "import_certificate_bundle", return_value=None), \
             patch.object(container_bootstrap, "ensure_default_bundle", return_value=Path("/data/private/certs.json")), \
             patch.object(container_bootstrap.os, "chmod"), \
             patch.object(container_bootstrap.os, "chown"), \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(container_bootstrap.os, "setgroups", side_effect=lambda groups: calls.append(("groups", groups))), \
             patch.object(container_bootstrap.os, "setgid", side_effect=lambda gid: calls.append(("gid", gid))), \
             patch.object(container_bootstrap.os, "setuid", side_effect=lambda uid: calls.append(("uid", uid))), \
             patch.object(container_bootstrap.os, "execv", side_effect=lambda name, argv: calls.append(("exec", name, argv))), \
             patch.object(container_bootstrap.sys, "argv", ["bootstrap", "--example"]):
            container_bootstrap.main()

        self.assertEqual(
            calls,
            [
                ("prepare", Path("/data")),
                ("groups", []),
                ("gid", 1000),
                ("uid", 1000),
                (
                    "exec",
                    container_bootstrap.sys.executable,
                    [
                        container_bootstrap.sys.executable,
                        "-m",
                        "cast_audio_lab.container_entrypoint",
                        "--example",
                    ],
                ),
            ],
        )

    def test_packaged_default_manifest_has_expected_pin(self):
        value = read_manifest(container_bootstrap.DEFAULT_MANIFEST,
                              container_bootstrap.DEFAULT_MANIFEST_SHA256)
        self.assertEqual(value["version"], "2026.09.20")

    def test_default_download_once_and_keeps_existing_state(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            calls = []
            def fetch(manifest, pin, destination):
                calls.append(pin)
                destination.parent.mkdir()
                destination.write_bytes(b'{"synthetic":true}')
            first = container_bootstrap.ensure_default_bundle(root, acquire_artifact=fetch)
            second = container_bootstrap.ensure_default_bundle(root, acquire_artifact=fetch)
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)

    def test_default_rejects_symlink_or_empty_existing_state_without_network(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "private" / "certs.json"
            target.parent.mkdir()
            target.write_bytes(b"")
            def forbidden(*args):
                self.fail("must not replace existing state implicitly")
            with self.assertRaises(ValueError):
                container_bootstrap.ensure_default_bundle(root, acquire_artifact=forbidden)
            target.unlink()
            target.symlink_to(root / "missing")
            with self.assertRaises(ValueError):
                container_bootstrap.ensure_default_bundle(root, acquire_artifact=forbidden)

    def test_empty_ha_override_selects_default(self):
        with TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            root = Path(folder)
            (root / "options.json").write_text('{"certificate_path":""}')
            self.assertIsNone(container_bootstrap._configured_certificate_source(root))

    def test_imports_root_readable_bundle_into_private_state(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            shared = Path(temporary) / "shared.json"
            shared.write_bytes(b'{"private":"test-fixture"}')
            root.mkdir()
            (root / "options.json").write_text(
                json.dumps({"certificate_path": str(shared)})
            )
            container_bootstrap.prepare_state(root, os.getuid(), os.getgid())

            imported = container_bootstrap.import_certificate_bundle(
                root, uid=os.getuid(), gid=os.getgid()
            )

            self.assertEqual(imported, root / "private" / "certs.json")
            self.assertEqual(imported.read_bytes(), shared.read_bytes())
            self.assertEqual(imported.stat().st_mode & 0o777, 0o600)

    def test_bundle_import_rejects_symlink_and_oversize(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            root.mkdir()
            container_bootstrap.prepare_state(root, os.getuid(), os.getgid())
            regular = Path(temporary) / "regular.json"
            regular.write_text("{}")
            symlink = Path(temporary) / "link.json"
            symlink.symlink_to(regular)
            options = root / "options.json"
            options.write_text(json.dumps({"certificate_path": str(symlink)}))
            with self.assertRaisesRegex(ValueError, "regular file"):
                container_bootstrap.import_certificate_bundle(
                    root, uid=os.getuid(), gid=os.getgid()
                )

            options.write_text(json.dumps({"certificate_path": str(regular)}))
            with patch.object(
                container_bootstrap,
                "MAX_CERTIFICATE_BUNDLE_BYTES",
                1,
            ), self.assertRaisesRegex(ValueError, "size"):
                container_bootstrap.import_certificate_bundle(
                    root, uid=os.getuid(), gid=os.getgid()
                )

    def test_configured_missing_bundle_fails_instead_of_starting_unusable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "data"
            root.mkdir()
            container_bootstrap.prepare_state(root, os.getuid(), os.getgid())
            (root / "options.json").write_text(
                json.dumps({"certificate_path": str(Path(temporary) / "missing.json")})
            )

            with self.assertRaisesRegex(ValueError, "regular file"):
                container_bootstrap.import_certificate_bundle(
                    root, uid=os.getuid(), gid=os.getgid()
                )


if __name__ == "__main__":
    unittest.main()
