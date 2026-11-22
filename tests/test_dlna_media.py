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


# --- progressive streaming (instant start for HLS / long items) ---
from cast_audio_lab.dlna import should_stream
from cast_audio_lab.dlna_media import stream_encoding


class StreamPolicyTests(unittest.TestCase):
    def test_stream_encoding_copies_supported_codecs_and_transcodes_the_rest(self):
        self.assertEqual(stream_encoding("aac", {"audio/aac", "audio/mpeg"})[:2], ("audio/aac", "adts"))
        self.assertEqual(stream_encoding("aac", {"audio/aac"})[2], ["-c:a", "copy"])
        self.assertEqual(stream_encoding("mp3", {"audio/mpeg"})[:2], ("audio/mpeg", "mp3"))
        self.assertEqual(stream_encoding("aac", {"audio/mpeg"})[2][:2], ["-c:a", "libmp3lame"])
        # unknown/unsupported codec: transcode to AAC when accepted (Yamaha rejects length-less MP3)
        self.assertEqual(stream_encoding("opus", {"audio/aac", "audio/mpeg"})[:3],
                         ("audio/aac", "adts", ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]))
        self.assertEqual(stream_encoding("", {"audio/mpeg"})[0], "audio/mpeg")

    def test_hls_long_and_unbounded_items_stream_short_files_stay_prepared(self):
        self.assertTrue(should_stream("application/x-mpegURL", 180.0))
        self.assertFalse(should_stream("audio/mp4", None))  # unknown length keeps the file path
        self.assertTrue(should_stream("audio/mp4", 9700.0))
        self.assertFalse(should_stream("audio/mpeg", 240.0))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class StreamRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_relay_streams_aac_immediately_and_bit_exact(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tone.aac"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                            "-c:a", "aac", "-b:a", "96k", "-f", "adts", str(source)], check=True)
            app = web.Application()
            calls = {"n": 0}

            async def late(request):  # 404 twice, like a just-registered bridge manifest
                if request.method == "HEAD":  # like the CDN behind the bridge: HEAD never succeeds
                    raise web.HTTPNotFound()
                calls["n"] += 1
                if calls["n"] <= 2:
                    raise web.HTTPNotFound()
                return web.FileResponse(source)
            app.router.add_route("*", "/tone.aac", late)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = site._server.sockets[0].getsockname()[1]
            relay = DlnaMediaRelay("127.0.0.1", bind_host="127.0.0.1")
            try:
                url, mime, codec = await relay.stream(f"http://127.0.0.1:{port}/tone.aac", {"audio/aac", "audio/mpeg"})
                self.assertEqual((mime, codec), ("audio/aac", "aac"))
                async with ClientSession() as http:
                    async with http.get(url) as response:
                        self.assertEqual(response.headers["Content-Type"], "audio/aac")
                        self.assertNotIn("Content-Length", response.headers)
                        self.assertNotIn("chunked", response.headers.get("Transfer-Encoding", ""))
                        self.assertIn("DLNA.ORG_OP=00", response.headers["contentFeatures.dlna.org"])
                        body = await response.read()
                    self.assertEqual(body, source.read_bytes())  # copied, not re-encoded
                    async with http.get(url.replace("/stream/", "/stream/x")) as response:
                        self.assertEqual(response.status, 404)
            finally:
                await relay.close()
                await runner.cleanup()


class HlsTrimTests(unittest.TestCase):
    PLAYLIST = "\n".join([
        "#EXTM3U", "#EXT-X-VERSION:7", "#EXT-X-TARGETDURATION:10", "#EXT-X-MEDIA-SEQUENCE:0",
        "#EXT-X-PLAYLIST-TYPE:VOD", '#EXT-X-MAP:URI="https://cdn/init.mp4"',
        "#EXTINF:10.0,", "https://cdn/s0.m4s", "#EXTINF:10.0,", "https://cdn/s1.m4s",
        "#EXTINF:10.0,", "https://cdn/s2.m4s", "#EXTINF:4.5,", "https://cdn/s3.m4s", "#EXT-X-ENDLIST"])

    def test_trims_to_the_segment_containing_start_and_keeps_init_map(self):
        from cast_audio_lab.dlna_media import trim_hls
        text, skipped = trim_hls(self.PLAYLIST, 26.0)
        self.assertEqual(skipped, 20.0)
        self.assertIn('#EXT-X-MAP:URI="https://cdn/init.mp4"', text)
        self.assertNotIn("s0.m4s", text)
        self.assertNotIn("s1.m4s", text)
        self.assertIn("https://cdn/s2.m4s", text)
        self.assertIn("#EXT-X-MEDIA-SEQUENCE:2", text)
        self.assertTrue(text.rstrip().endswith("#EXT-X-ENDLIST"))

    def test_start_zero_beyond_end_and_non_media_playlists(self):
        from cast_audio_lab.dlna_media import trim_hls
        self.assertEqual(trim_hls(self.PLAYLIST, 0)[1], 0.0)
        self.assertIn("s3.m4s", trim_hls(self.PLAYLIST, 9999)[0])  # never trims away the last segment
        self.assertIsNone(trim_hls("not a playlist", 5))
        self.assertIsNone(trim_hls("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nv.m3u8", 5))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class SizedMp3Tests(unittest.IsolatedAsyncioTestCase):
    async def test_sized_cbr_mp3_announces_length_and_serves_ranges(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tone.aac"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=4",
                            "-c:a", "aac", "-f", "adts", str(source)], check=True)
            app = web.Application()
            app.router.add_get("/tone.aac", lambda request: web.FileResponse(source))
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = site._server.sockets[0].getsockname()[1]
            relay = DlnaMediaRelay("127.0.0.1", bind_host="127.0.0.1")
            try:
                url, mime, codec = await relay.stream(f"http://127.0.0.1:{port}/tone.aac", {"audio/mpeg"}, 0.0, 4.0)
                self.assertEqual((mime, codec), ("audio/mpeg", "mp3-cbr"))
                async with ClientSession() as http:
                    async with http.head(url) as response:
                        self.assertEqual(response.headers["Content-Length"], "160000")
                        self.assertIn("DLNA.ORG_OP=01", response.headers["contentFeatures.dlna.org"])
                    async with http.get(url) as response:
                        self.assertEqual(response.status, 200)
                        body = await response.read()
                    self.assertEqual(len(body), 160000)
                    self.assertEqual(body[:2][0], 0xFF)  # MP3 frame sync, no ID3 header
                    async with http.get(url, headers={"Range": "bytes=80000-"}) as response:
                        self.assertEqual(response.status, 206)
                        self.assertEqual(response.headers["Content-Range"], "bytes 80000-159999/160000")
                        self.assertEqual(len(await response.read()), 80000)
            finally:
                await relay.close()
                await runner.cleanup()
