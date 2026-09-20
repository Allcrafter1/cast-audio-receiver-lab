from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.check_release_wheel import HISTORICAL, REQUIRED, validate


class ReleaseWheelTests(unittest.TestCase):
    def make_wheel(self, directory, *, extra=(), missing=()):
        path = Path(directory) / "fixture.whl"
        with zipfile.ZipFile(path, "w") as archive:
            for name in (REQUIRED - set(missing)) | set(extra):
                archive.writestr(name, "fixture")
        return path

    def test_clean_runtime_wheel(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate(self.make_wheel(directory))["historical_modules"], 0)

    def test_historical_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_wheel(
                directory, extra={"cast_audio_lab/" + next(iter(HISTORICAL))}
            )
            with self.assertRaisesRegex(ValueError, "historical module"):
                validate(path)

    def test_missing_runtime_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_wheel(directory, missing={next(iter(REQUIRED))})
            with self.assertRaisesRegex(ValueError, "is missing"):
                validate(path)


if __name__ == "__main__":
    unittest.main()
