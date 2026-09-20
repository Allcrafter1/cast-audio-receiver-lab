import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cast_audio_lab import container_bootstrap


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


if __name__ == "__main__":
    unittest.main()
