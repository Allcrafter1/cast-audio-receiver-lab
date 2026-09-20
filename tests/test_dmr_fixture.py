import importlib.util
import io
from pathlib import Path
import unittest
import wave
import shutil

spec = importlib.util.spec_from_file_location("dmr_fixture",
    Path(__file__).parents[1] / "tools/test_default_media.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DmrFixtureTests(unittest.TestCase):
    def test_invalid_encoding_is_rejected(self):
        with self.assertRaises(ValueError):
            module.encoded_fixture(True, "unknown")

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required for encoded fixtures")
    def test_encoded_silent_fixtures_are_bounded(self):
        for audio_format in ("mp3", "flac"):
            with self.subTest(audio_format=audio_format):
                content = module.encoded_fixture(True, audio_format)
                self.assertGreater(len(content), 100)
                self.assertLessEqual(len(content), 1024 * 1024)
                self.assertTrue(content.startswith(b"ID3" if audio_format == "mp3" else b"fLaC"))

    def test_silent_fixture_has_real_duration_and_no_nonzero_samples(self):
        with wave.open(io.BytesIO(module.fixture(silent=True)), "rb") as audio:
            self.assertEqual(audio.getnframes() / audio.getframerate(), 8)
            self.assertEqual(audio.getsampwidth(), 2)
            samples = audio.readframes(audio.getnframes())
            self.assertEqual(samples, bytes(len(samples)))

    def test_default_fixture_remains_a_quiet_tone(self):
        with wave.open(io.BytesIO(module.fixture()), "rb") as audio:
            self.assertTrue(any(audio.readframes(audio.getnframes())))
