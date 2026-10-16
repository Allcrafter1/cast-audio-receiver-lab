# SPDX-License-Identifier: MPL-2.0
import asyncio
import shlex
import sys
import subprocess
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cast_audio_lab.backend import CommandAudioBackend, MediaMetadata


class CommandBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_seek_reloads_at_requested_offset_and_preserves_pause(self):
        backend = CommandAudioBackend("test --start={start_time} {url}")
        backend._status.url = 'https://example.invalid/audio'
        backend._status.content_type = 'audio/webm'
        backend._status.state = 'PAUSED'
        backend.load = AsyncMock()
        await backend.seek(42)
        backend.load.assert_awaited_once_with(backend._status.url, 'audio/webm', False, 42)

    async def test_unsupported_seek_does_not_fake_new_position(self):
        backend = CommandAudioBackend('test {url}')
        backend._status.url = 'https://example.invalid/audio'
        backend._status.state = 'PAUSED'
        backend._set_position(7)
        with self.assertRaises(ValueError):
            await backend.seek(42)
        self.assertEqual(backend.status().current_time, 7)

    async def test_cancellation_during_actual_spawn_reaps_unassigned_child(self):
        backend = CommandAudioBackend(
            f'{shlex.quote(sys.executable)} -c "import time; time.sleep(60)" {{url}}')
        spawn = subprocess.Popen
        children = []
        def cancelling_spawn(*args, **kwargs):
            process = spawn(*args, **kwargs)
            children.append(process)
            asyncio.current_task().cancel()
            return process
        with patch('asyncio.base_subprocess.subprocess.Popen', side_effect=cancelling_spawn):
            task = asyncio.create_task(backend.load('test', 'audio/webm', True, 0))
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertIsNone(backend._process)
        await backend.shutdown()

    async def test_play_after_decoder_exit_does_not_resurrect_old_url(self):
        backend = CommandAudioBackend(f'{shlex.quote(sys.executable)} -c "pass" {{url}}')
        await backend.load("test", "audio/webm", True, 0)
        await asyncio.wait_for(backend._watch_task, 2)
        await backend.play()
        await backend.pause()
        self.assertEqual(backend.status().state, "IDLE")
        self.assertEqual(backend.status().idle_reason, "FINISHED")

    async def test_cancelled_termination_remains_owned_until_reaped(self):
        backend = CommandAudioBackend("test {url}")
        entered, release = asyncio.Event(), asyncio.Event()
        async def wait():
            entered.set()
            await release.wait()
            return 0
        process = Mock(returncode=None, wait=AsyncMock(side_effect=wait))
        backend._process = process
        stopping = asyncio.create_task(backend.stop())
        await entered.wait()
        stopping.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await stopping
        self.assertFalse(backend._cleanup_task.done())
        again = asyncio.create_task(backend.stop())
        await asyncio.sleep(0)
        self.assertFalse(again.done())
        release.set()
        await again
        process.terminate.assert_called_once()
        process.wait.assert_awaited_once()
        self.assertEqual(backend.status().idle_reason, "CANCELLED")
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
