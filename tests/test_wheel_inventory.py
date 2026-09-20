import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("wheel_inventory",
    Path(__file__).parents[1] / "tools/wheel_inventory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WheelInventoryTests(unittest.TestCase):
    def wheel(self, directory, filename, name="example", version="1.2"):
        with zipfile.ZipFile(Path(directory) / filename, "w") as archive:
            archive.writestr("example.dist-info/METADATA",
                f"Name: {name}\nVersion: {version}\nLicense-Expression: MIT\n\n")

    def test_artifact_identity_without_importing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.wheel(directory, "example.whl")
            items = module.inventory(directory)
            self.assertEqual(items[0]["license"], "MIT")
            self.assertEqual(len(items[0]["sha256"]), 64)
            self.assertIn("example==1.2 --hash=sha256:", module.requirements(items))
            self.assertNotIn(directory, str(items))

    def test_duplicate_normalized_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.wheel(directory, "a.whl", name="Example_Package")
            self.wheel(directory, "b.whl", name="example-package")
            with self.assertRaises(ValueError):
                module.inventory(directory)

    def test_nested_vendored_metadata_is_not_the_wheel_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.whl"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    "example.dist-info/METADATA",
                    "Name: example\nVersion: 1.2\nLicense-Expression: MIT\n\n",
                )
                archive.writestr(
                    "example/_vendor/other-9.0.dist-info/METADATA",
                    "Name: other\nVersion: 9.0\n\n",
                )
            self.assertEqual(module.inventory(directory)[0]["name"], "example")

    def test_requirement_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.wheel(directory, "a.whl", version="1.2 --index-url=bad")
            with self.assertRaises(ValueError):
                module.inventory(directory)
