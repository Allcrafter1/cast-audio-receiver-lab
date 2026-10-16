# SPDX-License-Identifier: MPL-2.0
"""Real IPC smoke tests, silent, skipped when mpv is not installed."""
import asyncio
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import wave

from cast_audio_lab.mpv_backend import MpvAudioBackend


@unittest.skipUnless(shutil.which("mpv"), "real mpv is not installed")
class MpvIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rapid_replacement_without_waiting_for_first_file_loaded(self):
        spawn = asyncio.create_subprocess_exec
        async def silent(*args, **kwargs):
            return await spawn(*args, "--ao=null", **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "silence.wav"
            with wave.open(str(media), "wb") as audio:
                audio.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0" * 44100 * 4 * 5)
            backend = MpvAudioBackend()
            with patch("cast_audio_lab.mpv_backend.asyncio.create_subprocess_exec", silent):
                try:
                    for _ in range(30):
                        await backend.load(str(media), "audio/wav", False, 1)
                        await backend.load(str(media), "audio/wav", False, 3)
                        async with asyncio.timeout(3):
                            while backend._loading:
                                await asyncio.sleep(.005)
                        actual = await backend._command("get_property", "time-pos")
                        self.assertAlmostEqual(actual, 3, delta=.15)
                        self.assertAlmostEqual(backend.status().current_time, 3, delta=.15)
                        self.assertEqual(backend.status().state, "PAUSED")
                        self.assertIsNone(backend.status().idle_reason)
                        await backend.stop()
                finally:
                    await backend.shutdown()

    async def test_real_decoder_offset_pause_seek_eof_and_stop(self):
        spawn = asyncio.create_subprocess_exec

        async def silent(*args, **kwargs):
            return await spawn(*args, "--ao=null", **kwargs)

        async def until(predicate):
            async with asyncio.timeout(8):
                while not predicate():
                    await asyncio.sleep(.025)

        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / "silence.wav"
            with wave.open(str(media), "wb") as audio:
                audio.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0" * 44100 * 4 * 5)
            backend = MpvAudioBackend()
            with patch("cast_audio_lab.mpv_backend.asyncio.create_subprocess_exec", silent):
                try:
                    await backend.load(str(Path(directory) / "missing.wav"), "audio/wav", True, 2)
                    await until(lambda: backend.status().idle_reason == "ERROR")
                    await backend.play()
                    await backend.pause()
                    self.assertEqual(backend.status().state, "IDLE")
                    self.assertEqual(backend.status().idle_reason, "ERROR")
                    # Fresh LOAD, not unpause, must recover the real decoder.
                    await backend.load(str(media), "audio/wav", False, 2)
                    await until(lambda: not backend._loading)
                    self.assertEqual(backend.status().state, "PAUSED")
                    self.assertAlmostEqual(backend.status().current_time, 2, delta=.15)
                    # Replace a live decoder repeatedly. Old end-file/property
                    # events must not finish or poison the next selection.
                    for index in range(12):
                        autoplay = index % 2 == 0
                        await backend.load(str(media), "audio/wav", autoplay, 2)
                        await until(lambda: not backend._loading)
                        await asyncio.sleep(.03)
                        self.assertEqual(backend.status().state,
                                         "PLAYING" if autoplay else "PAUSED")
                        self.assertIsNone(backend.status().idle_reason)
                        self.assertAlmostEqual(backend.status().current_time, 2, delta=.25)
                    await backend.seek(3)
                    await until(lambda: not backend._seeking)
                    self.assertAlmostEqual(backend.status().current_time, 3, delta=.15)
                    await backend.play()
                    await until(lambda: backend.status().idle_reason == "FINISHED")
                    await backend.load(str(media), "audio/wav", True, 0)
                    await until(lambda: not backend._loading)
                    await backend.stop()
                    self.assertEqual(backend.status().state, "IDLE")
                    await backend.set_volume(.27, True)
                    old_process = backend._process
                    old_process.kill()
                    await until(lambda: backend.status().idle_reason == "ERROR")
                    await backend.load(str(media), "audio/wav", False, 1)
                    await until(lambda: not backend._loading)
                    self.assertNotEqual(backend._process.pid, old_process.pid)
                    self.assertEqual(backend.status().state, "PAUSED")
                    self.assertAlmostEqual(backend.status().volume, .27)
                    self.assertTrue(backend.status().muted)
                finally:
                    await backend.shutdown()
