"""Real FFmpeg crop behavior; no network, sound, or image-library dependency."""
import shutil
import subprocess
import unittest
import tempfile
from pathlib import Path

from cast_audio_lab.artwork import (
    JPEG_QUALITY_ARGS,
    SQUARE_COVER_FILTER,
    embedded_bar_inset,
    prepare_square_artwork,
    remove_embedded_bars,
)


class EmbeddedBarTests(unittest.TestCase):
    def test_quality_policy_uses_high_quality_bounded_jpeg(self):
        self.assertEqual(JPEG_QUALITY_ARGS, ("-q:v", "2"))
        self.assertIn(":flags=lanczos", SQUARE_COVER_FILTER)
    def test_symmetric_black_bands(self):
        self.assertEqual(embedded_bar_inset(bytes(64*8)+bytes([100])*(64*48)+bytes(64*8)), 8)

    def test_does_not_crop_dark_asymmetric_or_unpadded_covers(self):
        for image in (bytes(4096), bytes([100])*4096,
                      bytes(64*8)+bytes([100])*(64*56), b"invalid"):
            self.assertEqual(embedded_bar_inset(image), 0)

    def test_edge_content_prevents_black_band_classification(self):
        self.assertEqual(embedded_bar_inset((bytes(63)+bytes([80]))*64), 0)


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required for image conversion")
class EmbeddedBarConversionTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_refinement_removes_black_and_colored_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"cover.ppm"
            pixels = bytearray()
            for y in range(64):
                for x in range(64):
                    pixels.extend((0, 0, 0) if y < 8 or y >= 56 else
                                  ((200, 20, 20) if 8 <= x < 56 else (20, 20, 200)))
            path.write_bytes(b"P6\n64 64\n255\n"+pixels)
            self.assertTrue(await remove_embedded_bars(path, "ffmpeg"))
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
            ], capture_output=True, check=True, timeout=5)
            self.assertEqual(len(result.stdout), 48*48*3)
            self.assertFalse((Path(directory)/"cover-refined.jpg").exists())

    async def test_missing_converter_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"cover.jpg"
            path.write_bytes(b"original")
            self.assertFalse(await remove_embedded_bars(path, str(Path(directory)/"missing")))
            self.assertEqual(path.read_bytes(), b"original")

    async def test_prepare_uses_lossless_intermediate_before_final_jpeg(self):
        """The general converter emits one final JPEG, not two lossy stages."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.ppm"
            output = Path(directory) / "cover.jpg"
            pixels = bytearray()
            for y in range(64):
                for x in range(64):
                    pixels.extend((0, 0, 0) if y < 8 or y >= 56 else
                                  ((200, 20, 20) if 8 <= x < 56 else (20, 20, 200)))
            source.write_bytes(b"P6\n64 64\n255\n" + pixels)
            self.assertTrue(await prepare_square_artwork(source, output, "ffmpeg"))
            self.assertTrue(output.is_file())
            self.assertFalse((Path(directory) / ".cover.source.png").exists())
            self.assertFalse((Path(directory) / ".cover.refined.jpg").exists())
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(output),
                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
            ], capture_output=True, check=True, timeout=5)
            self.assertEqual(len(result.stdout), 48 * 48 * 3)

    async def test_prepare_replaces_stale_output_only_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "cover.jpg"
            output.write_bytes(b"previous")
            self.assertFalse(await prepare_square_artwork(
                Path(directory) / "missing.ppm", output, str(Path(directory) / "missing")
            ))
            self.assertEqual(output.read_bytes(), b"previous")


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg required for image conversion")
class ArtworkTests(unittest.TestCase):
    def convert(self, width, height):
        side = min(width, height)
        rgb = bytearray()
        for y in range(height):
            for x in range(width):
                center = ((width-side)//2 <= x < (width+side)//2 and
                          (height-side)//2 <= y < (height+side)//2)
                rgb.extend((240, 10, 20) if center else (0, 0, 255))
        source = f"P6\n{width} {height}\n255\n".encode()+rgb
        result = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "image2pipe",
            "-vcodec", "ppm", "-i", "pipe:0", "-vf", SQUARE_COVER_FILTER,
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
        ], input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        expected_side = min(side, 512)
        self.assertEqual(len(result.stdout), expected_side*expected_side*3)
        # No blue edge strips or black padding survive the centered crop.
        self.assertEqual(result.stdout, bytes((240, 10, 20))*(expected_side**2))

    def test_landscape_preserves_full_height(self):
        self.convert(16, 8)

    def test_portrait_and_square(self):
        self.convert(8, 16)
        self.convert(8, 8)

    def test_large_cover_is_bounded(self):
        self.convert(1024, 600)
