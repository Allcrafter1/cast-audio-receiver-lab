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
                    await backend.load(str(media), "audio/wav", False, 2)
                    await until(lambda: not backend._loading)
                    self.assertEqual(backend.status().state, "PAUSED")
                    self.assertAlmostEqual(backend.status().current_time, 2, delta=.15)
                    await backend.seek(3)
                    await until(lambda: not backend._seeking)
                    self.assertAlmostEqual(backend.status().current_time, 3, delta=.15)
                    await backend.play()
                    await until(lambda: backend.status().idle_reason == "FINISHED")
                    await backend.load(str(media), "audio/wav", True, 0)
                    await until(lambda: not backend._loading)
                    await backend.stop()
                    self.assertEqual(backend.status().state, "IDLE")
                finally:
                    await backend.shutdown()
