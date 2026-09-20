from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from tools.create_ha_test_repository import create


class HomeAssistantTestRepositoryTests(unittest.TestCase):
    def test_export_is_local_build_and_contains_no_private_bundle(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            create(root)
            app = root / "cast-audio-receiver"
            config = yaml.safe_load((app / "config.yaml").read_text())

            self.assertNotIn("image", config)
            self.assertEqual(config["options"]["certificate_path"],
                             "/share/cast-audio-receiver/certs.json")
            self.assertTrue((app / "Dockerfile").is_file())
            self.assertTrue((app / "src" / "cast_audio_lab" / "runtime.py").is_file())
            self.assertFalse(any(root.rglob("certs.json")))
            self.assertFalse(any(path.name == ".state" for path in root.rglob("*")))
            self.assertFalse(any(path.name == "__pycache__" for path in root.rglob("*")))
            self.assertFalse(any(path.suffix == ".pyc" for path in root.rglob("*")))
            self.assertFalse(any(path.name.endswith(".egg-info") for path in root.rglob("*")))

    def test_refuses_to_overlay_existing_directory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "keep").write_text("user data")
            with self.assertRaisesRegex(ValueError, "not empty"):
                create(root)


if __name__ == "__main__":
    unittest.main()
