# SPDX-License-Identifier: MPL-2.0
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

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg/ffprobe required')
    async def test_real_opus_webm_becomes_sonos_mp3_with_correct_format(self):
        import json
        from cast_audio_lab.sonos import SONOS_RELAY_MIME
        generator = await asyncio.create_subprocess_exec(
            'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2',
            '-c:a', 'libopus', '-f', 'webm', 'pipe:1',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        webm, errors = await generator.communicate()
        self.assertEqual(generator.returncode, 0, errors.decode())
        async def audio(request):
            return web.Response(body=webm, content_type='audio/webm')
        app = web.Application(); app.router.add_get('/audio', audio)
        source = TestServer(app); await source.start_server()
        relay = DlnaMediaRelay('127.0.0.1', bind_host='127.0.0.1')
        try:
            url, mime = await relay.prepare(str(source.make_url('/audio')), 'audio/webm; codecs=opus', SONOS_RELAY_MIME)
            self.assertEqual(mime, 'audio/mpeg')
            async with ClientSession() as client:
                async with client.get(url) as response:
                    mp3 = await response.read()
                    self.assertEqual(response.headers['Content-Length'], str(len(mp3)))
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'result.mp3'; path.write_bytes(mp3)
                probe = await asyncio.create_subprocess_exec('ffprobe', '-v', 'error', '-show_streams',
                    '-show_format', '-of', 'json', str(path), stdout=asyncio.subprocess.PIPE)
                result, _ = await probe.communicate()
                self.assertEqual(probe.returncode, 0)
                data = json.loads(result)
                self.assertEqual(data['streams'][0]['codec_name'], 'mp3')
                self.assertEqual(data['streams'][0]['sample_rate'], '44100')
                self.assertEqual(data['streams'][0]['channels'], 2)
                self.assertAlmostEqual(float(data['format']['duration']), 2, delta=.1)
        finally:
            await relay.close(); await source.close()


class CleanupFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_cleanup_failure_removes_files_and_keeps_runner_for_retry(self):
        from types import SimpleNamespace
        relay = DlnaMediaRelay('127.0.0.1')
        relay._temp = tempfile.TemporaryDirectory(prefix='cast-relay-test-')
        directory = Path(relay._temp.name)
        path = directory / 'track.mp3'; path.write_bytes(b'audio')
        relay._files['track.mp3'] = (path, 'audio/mpeg', True)
        relay._base = 'http://127.0.0.1:1234'
        runner = SimpleNamespace(cleanup=AsyncMock(side_effect=[RuntimeError('close failed'), None]))
        relay._runner = runner
        with self.assertRaises(RuntimeError):
            await relay.close()
        self.assertFalse(directory.exists())
        self.assertFalse(relay._files)
        self.assertIsNone(relay._base)
        self.assertIs(relay._runner, runner)
        await relay.close()
        self.assertIsNone(relay._runner)
        self.assertEqual(runner.cleanup.await_count, 2)

    async def test_next_start_retries_failed_http_cleanup_before_new_listener(self):
        from types import SimpleNamespace
        relay = DlnaMediaRelay('127.0.0.1', bind_host='127.0.0.1')
        old = SimpleNamespace(cleanup=AsyncMock(side_effect=[RuntimeError('close failed'), None]))
        relay._runner, relay._base = old, 'http://old'
        with self.assertRaises(RuntimeError):
            await relay.close()
        try:
            await relay._start()
            self.assertEqual(old.cleanup.await_count, 2)
            self.assertIsNot(relay._runner, old)
            self.assertTrue(relay._base.startswith('http://127.0.0.1:'))
        finally:
            await relay.close()

    async def test_sonos_and_dlna_stop_state_survives_relay_cleanup_failure(self):
        from types import SimpleNamespace
        from cast_audio_lab.sonos import SonosAudioBackend
        from cast_audio_lab.dlna import DlnaAudioBackend
        sonos = SonosAudioBackend('192.0.2.3', device_factory=lambda _: SimpleNamespace(stop=lambda: None))
        dlna = DlnaAudioBackend('http://192.0.2.3/device.xml')
        for backend in (sonos, dlna):
            with self.subTest(backend=type(backend).__name__):
                relay = SimpleNamespace(close=AsyncMock(side_effect=[RuntimeError('close failed'), None]))
                backend._relay = relay
                backend._status.state = 'PLAYING'
                try:
                    await backend.stop()
                except RuntimeError:
                    pass  # Sonos propagates; DLNA translates its Stop error.
                self.assertEqual(backend.status().state, 'IDLE')
                self.assertIs(backend._relay, relay)
                await backend.shutdown()
                self.assertIsNone(backend._relay)
                self.assertEqual(relay.close.await_count, 2)
