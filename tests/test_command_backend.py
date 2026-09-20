import asyncio
import shlex
import sys
import unittest

from cast_audio_lab.backend import CommandAudioBackend, MediaMetadata


class CommandBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_transport_is_not_track_end(self):
        backend = CommandAudioBackend(
            f'{shlex.quote(sys.executable)} -c "import sys; sys.exit(22)" {{url}}'
        )
        await backend.set_metadata(MediaMetadata(duration=213))
        await backend.load("https://example.invalid/audio", "audio/webm", True, 12)
        await asyncio.wait_for(backend._watch_task, 2)
        self.assertEqual(backend.status().idle_reason, "ERROR")
        self.assertLess(backend.status().current_time, 213)

    async def test_start_position_reaches_player_argument(self):
        backend = CommandAudioBackend(
            f'{shlex.quote(sys.executable)} -c '
            '"import sys; sys.exit(0 if sys.argv[1] == str(12.5) else 1)" '
            '{start_time} {url}'
        )
        await backend.load("https://example.invalid/audio", "audio/webm", True, 12.5)
        await asyncio.wait_for(backend._watch_task, 2)
        self.assertEqual(backend.status().idle_reason, "FINISHED")
