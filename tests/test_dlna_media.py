import asyncio
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import wave

from aiohttp import ClientSession, web
from aiohttp.test_utils import TestClient, TestServer
from cast_audio_lab.dlna_media import DlnaMediaRelay, encoding, needs_relay


class MediaPolicyTests(unittest.TestCase):
    def test_https_or_unknown_codec_uses_compatibility_path(self):
        self.assertTrue(needs_relay("https://source/song", "audio/mpeg", {"audio/mpeg"}))
        self.assertTrue(needs_relay("http://source/song", "audio/webm", {"audio/mpeg"}))
        self.assertFalse(needs_relay("http://source/song", "audio/mpeg", {"audio/mpeg"}))
        self.assertFalse(needs_relay("http://source/song", "audio/webm", set()))
        self.assertTrue(needs_relay("http://127.0.0.1:8010/manifest/item", "audio/mpeg", {"audio/mpeg"}))
        self.assertEqual(encoding("audio/mpeg", {"audio/mpeg"})[3], ["-c:a", "copy"])
        self.assertIn("libmp3lame", encoding("audio/webm", {"audio/mpeg"})[3])


class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_head_range_and_unrelated_paths(self):
        relay = DlnaMediaRelay("127.0.0.1", bind_host="127.0.0.1")
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "fixture.mp3"
            media.write_bytes(b"0123456789")
            relay._files["opaque.mp3"] = (media, "audio/mpeg", True)
            await relay._start()
            try:
                async with ClientSession() as client:
                    async with client.head(relay._base + "/media/opaque.mp3") as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers["Content-Length"], "10")
                        self.assertIn("DLNA.ORG_CI=1", response.headers["contentFeatures.dlna.org"])
                    async with client.get(relay._base + "/media/opaque.mp3", headers={"Range": "bytes=2-5"}) as response:
                        self.assertEqual(response.status, 206)
                        self.assertEqual(await response.read(), b"2345")
                        self.assertEqual(response.headers["Content-Range"], "bytes 2-5/10")
                    async with client.get(relay._base + "/media/missing.mp3") as response:
                        self.assertEqual(response.status, 404)
            finally:
                await relay.close()

    async def test_failure_and_cancellation_remove_partial_output(self):
        relay = DlnaMediaRelay("127.0.0.1", bind_host="127.0.0.1")
        class Process:
            returncode = None
            def kill(self): self.returncode = -9
            async def wait(self):
                if self.returncode is None:
                    await asyncio.sleep(60)
                return self.returncode
        async def spawn(*args, **kwargs):
            Path(args[-1]).write_bytes(b"partial")
            return Process()
        try:
            with patch("cast_audio_lab.dlna_media.asyncio.create_subprocess_exec", spawn):
                task = asyncio.create_task(relay.prepare("https://source/song", "audio/webm", {"audio/mpeg"}))
                while relay._process is None:
                    await asyncio.sleep(0)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError): await task
            self.assertEqual(list(Path(relay._temp.name).iterdir()), [])
            self.assertIsNone(relay._process)
        finally:
            await relay.close()

    async def test_non_http_source_rejected_before_spawn(self):
        relay = DlnaMediaRelay("127.0.0.1")
        with patch("cast_audio_lab.dlna_media.asyncio.create_subprocess_exec", new_callable=AsyncMock) as spawn:
            with self.assertRaises(ValueError):
                await relay.prepare("file:///etc/passwd", "audio/mpeg", set())
            spawn.assert_not_called()

    @unittest.skipUnless(shutil.which("ffmpeg"), "real FFmpeg not installed")
    async def test_real_conversion_produces_seekable_mp3(self):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            wav.writeframes(bytes(44100 * 4 * 2))
        async def audio(request): return web.Response(body=output.getvalue(), content_type="audio/wav")
        app = web.Application(); app.router.add_get("/audio", audio)
        source = TestServer(app); await source.start_server()
        relay = DlnaMediaRelay("127.0.0.1", bind_host="127.0.0.1")
        try:
            url, mime = await relay.prepare(str(source.make_url("/audio")), "audio/wav", {"audio/mpeg"})
            self.assertEqual(mime, "audio/mpeg")
            async with ClientSession() as client:
                async with client.get(url) as response:
                    self.assertEqual(response.status, 200)
                    self.assertGreater(len(await response.read()), 1000)
                async with client.get(url, headers={"Range": "bytes=0-15"}) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(len(await response.read()), 16)
        finally:
            await relay.close(); await source.close()
