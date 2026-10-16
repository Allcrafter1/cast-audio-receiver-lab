# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
import unittest
from unittest.mock import AsyncMock

from cast_audio_lab.backend import NullAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer


class DispatchReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_takeover_stops_previous_decoder_and_can_recover(self):
        for invalid in (None, {'mediaSessionId': []}, {'streams': []},
                        {'streams': [{'url': ''}]},
                        {'streams': [{'url': 'new'}], 'startTime': float('inf')}):
            with self.subTest(media=invalid):
                backend = NullAudioBackend()
                player = VibecastAudioPlayer('ws://example.invalid', 'id', 'local', backend)
                player._send = AsyncMock()
                await player.handle_message(dict(type='load', sessionId='old', media={
                    'mediaSessionId': 1, 'streams': [{'url': 'old'}]}))
                await player.handle_message(dict(type='load', sessionId='new', media=invalid))
                self.assertEqual(backend.status().state, 'IDLE')
                self.assertIsNone(player.session_id)
                self.assertEqual(player._send.call_args.args[0]['type'], 'error')
                # Legacy (no media ID) selection must recover normally.
                await player.handle_message(dict(type='load', sessionId='legacy', media={
                    'streams': [{'url': 'recovered'}]}))
                self.assertEqual(backend.status().state, 'PLAYING')
                await player.handle_message(dict(type='stop', sessionId='old'))
                self.assertEqual(backend.status().state, 'PLAYING')
                await player.handle_message(dict(type='stop', sessionId='legacy'))
                self.assertEqual(backend.status().state, 'IDLE')

    async def test_rapid_replacements_wait_for_cancelled_load_cleanup(self):
        backend = NullAudioBackend()
        player = VibecastAudioPlayer('ws://example.invalid', 'id', 'local', backend)
        player._send = AsyncMock()
        incoming = asyncio.Queue()
        started, cleaning, release, finished = (asyncio.Event() for _ in range(4))
        seen = []
        class Socket:
            def __aiter__(self):
                return self
            async def __anext__(self):
                return json.dumps(await incoming.get())
            async def wait_closed(self):
                await asyncio.Event().wait()
            async def ping(self):
                return asyncio.get_running_loop().create_future()
        async def load(url, *_):
            seen.append(url)
            if url == 'A':
                started.set()
                await asyncio.Event().wait()
            else:
                self.assertTrue(release.is_set(), 'replacement started before cleanup completed')
                finished.set()
        async def stop():
            cleaning.set()
            await release.wait()
        backend.load, backend.stop = load, stop
        def message(kind, session='owner', title='A'):
            return dict(type=kind, sessionId=session, media=dict(streams=[dict(url=title)]))
        task = asyncio.create_task(player._serve_connection(Socket()))
        try:
            await incoming.put(message('load'))
            await asyncio.wait_for(started.wait(), 1)
            await incoming.put(message('stop', session='unrelated'))
            await asyncio.sleep(.01)
            self.assertFalse(cleaning.is_set(), 'unrelated Stop cancelled active Load')
            await incoming.put(message('load', title='B'))
            await asyncio.wait_for(cleaning.wait(), 1)
            await incoming.put(message('pause'))
            await incoming.put(message('seek'))
            await incoming.put(message('load', title='C'))
            await asyncio.sleep(.01)
            self.assertEqual(seen, ['A'])
            release.set()
            await asyncio.wait_for(finished.wait(), 1)
            self.assertEqual(seen, ['A', 'C'])
            self.assertFalse(task.done())
        finally:
            release.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
