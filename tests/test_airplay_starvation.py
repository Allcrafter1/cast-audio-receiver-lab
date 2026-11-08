# SPDX-License-Identifier: MPL-2.0
import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget


class AirPlayStarvationTests(unittest.IsolatedAsyncioTestCase):
    def backend(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        backend._track_started = True
        backend._autoplay = True
        backend._status.state = 'PLAYING'
        backend._track_start = 40
        backend._decoded_bytes = 176400 * 10
        backend._pcm_read_pending = True
        return backend

    def observe(self, backend, elapsed, now):
        with patch('cast_audio_lab.airplay.time.monotonic', return_value=now):
            backend._observe_native_progress(elapsed)

    async def test_frozen_native_clock_waits_for_remaining_pcm_and_margin(self):
        b = self.backend()
        self.observe(b, 8, 100)
        self.observe(b, 8, 103.9)
        self.assertEqual(b.status().state, 'PLAYING')
        self.observe(b, 8, 104)
        self.assertEqual(b.status().state, 'BUFFERING')
        self.assertEqual(b.status().current_time, 50)
        b._decoded_bytes += 176400
        self.observe(b, 8, 105)
        self.assertEqual(b.status().state, 'BUFFERING')
        self.observe(b, 9, 106)
        self.assertEqual(b.status().state, 'PLAYING')
        self.assertEqual(b._position_at_change, 50)

    async def test_native_progress_and_large_runway_prevent_false_starvation(self):
        b = self.backend()
        b._decoded_bytes = 176400 * 100
        self.observe(b, 8, 100)
        self.observe(b, 8, 160)
        self.assertEqual(b.status().state, 'PLAYING')
        b._decoded_bytes = 176400 * 10
        self.observe(b, 9, 161)
        self.observe(b, 9, 163)
        self.assertEqual(b.status().state, 'PLAYING')

    async def test_backpressure_pause_finished_and_unstarted_are_not_starvation(self):
        for field, value in (('_pcm_read_pending', False), ('_autoplay', False),
                             ('_input_finished', True), ('_track_started', False)):
            with self.subTest(field=field):
                b = self.backend()
                self.observe(b, 8, 100)
                setattr(b, field, value)
                self.observe(b, 8, 200)
                self.assertEqual(b.status().state, 'PLAYING')
        b = self.backend()
        self.observe(b, 8, 100)
        b._status.state = 'PAUSED'
        self.observe(b, 8, 200)
        self.assertEqual(b.status().state, 'PAUSED')

    async def test_invalid_or_absent_native_clock_does_not_invent_starvation(self):
        b = self.backend()
        for elapsed in (float('nan'), float('inf'), -1, 999):
            self.observe(b, elapsed, 200)
            self.assertEqual(b.status().state, 'PLAYING')
        self.assertIsNone(b._native_elapsed)

    async def test_clock_rollback_restarts_observation_instead_of_using_old_deadline(self):
        b = self.backend()
        self.observe(b, 8, 100)
        self.observe(b, 2, 200)
        self.observe(b, 2, 209)
        self.assertEqual(b.status().state, 'PLAYING')

    async def test_invalid_sample_during_starvation_cannot_strand_buffering(self):
        for invalid in (float('nan'), float('inf'), -1):
            with self.subTest(invalid=invalid):
                b = self.backend()
                self.observe(b, 8, 100)
                self.observe(b, 8, 104)
                self.observe(b, invalid, 105)
                self.assertEqual(b.status().state, 'BUFFERING')
                self.assertTrue(b._input_starved)
                self.observe(b, 9, 106)
                self.assertEqual(b.status().state, 'PLAYING')

    async def test_remote_pause_and_toggle_while_starved_preserve_pause_intent(self):
        for command in ('pause', 'toggle_play_pause'):
            with self.subTest(command=command):
                b = self.backend()
                b._status.url = 'https://example.test/audio'
                self.observe(b, 8, 100)
                self.observe(b, 8, 104)
                await b._apply_remote_command(command)
                self.assertEqual(b.status().state, 'PAUSED')
                self.assertFalse(b._autoplay)
                self.observe(b, 9, 200)
                self.assertEqual(b.status().state, 'PAUSED')
                await b._apply_remote_command('play')
                self.assertTrue(b._autoplay)
                self.assertIsNone(b._native_elapsed)

    async def test_pause_resume_and_track_cleanup_reset_deadline(self):
        b = self.backend()
        b._status.url = 'https://example.test/audio'
        b._command = AsyncMock()
        b._send_progress = AsyncMock()
        self.observe(b, 8, 100)
        await b.pause()
        self.assertIsNone(b._native_elapsed)
        self.observe(b, 8, 200)
        self.assertEqual(b.status().state, 'PAUSED')
        await b.play()
        self.observe(b, 8, 300)
        self.assertEqual(b.status().state, 'PLAYING')
        await b._stop_track()
        self.assertIsNone(b._native_elapsed)
        self.assertFalse(b._input_starved)

    async def test_load_seek_and_stop_discard_previous_track_evidence(self):
        b = self.backend()
        for name in ('_prepare_transport', '_start_pipeline', '_send_metadata',
                     '_wait_for_audio', '_command', '_progress_updates'):
            setattr(b, name, AsyncMock())
        self.observe(b, 8, 100)
        await b.load('https://example.test/audio', 'audio/mp4', True, 40)
        self.assertIsNone(b._native_elapsed)
        b._native_elapsed = 8
        b._input_starved = True
        await b.seek(50)
        self.assertIsNone(b._native_elapsed)
        self.assertFalse(b._input_starved)
        b._native_elapsed = 9
        await b.stop()
        self.assertIsNone(b._native_elapsed)
        self.assertEqual(b.status().state, 'IDLE')

    async def test_pcm_wait_flag_excludes_destination_backpressure_and_cancellation(self):
        b = self.backend()
        b._pcm_read_pending = False
        reader = asyncio.StreamReader()
        drain_started = asyncio.Event()
        release_drain = asyncio.Event()
        async def drain():
            drain_started.set()
            await release_drain.wait()
        writer = Mock(drain=drain)
        pump = asyncio.create_task(b._pump_pcm(reader, writer))
        try:
            await asyncio.sleep(0)
            self.assertTrue(b._pcm_read_pending)
            reader.feed_data(bytes(1024))
            await drain_started.wait()
            self.assertFalse(b._pcm_read_pending)
            release_drain.set()
            await asyncio.sleep(0)
            self.assertTrue(b._pcm_read_pending)
        finally:
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)
        self.assertFalse(b._pcm_read_pending)

    async def test_native_event_stream_drives_starvation_state(self):
        b = self.backend()
        self.observe(b, 8, 100)
        reader = asyncio.StreamReader()
        reader.feed_data(b'[STATUS] playing elapsed_ms=8000\n')
        reader.feed_eof()
        with patch('cast_audio_lab.airplay.time.monotonic', return_value=104):
            await b._read_events(reader)
        self.assertEqual(b.status().state, 'BUFFERING')

    async def native_event(self, backend, elapsed_ms):
        reader = asyncio.StreamReader()
        reader.feed_data(f'[STATUS] playing elapsed_ms={elapsed_ms}\n'.encode())
        reader.feed_eof()
        await backend._read_events(reader)

    async def test_clean_decoder_eof_after_starvation_finishes_without_another_pcm_read(self):
        for intermediate_progress in (False, True):
            with self.subTest(intermediate_progress=intermediate_progress):
                b = self.backend()
                self.observe(b, 8, 100)
                self.observe(b, 8, 104)
                self.assertEqual(b.status().state, 'BUFFERING')
                b._decoder = Mock(wait=AsyncMock(return_value=0))
                source = asyncio.StreamReader()
                source.feed_data(bytes(176400))
                source.feed_eof()

                async def drain():
                    if not b._input_finished:
                        return
                    if intermediate_progress:
                        await self.native_event(b, 10000)
                        self.assertEqual(b.status().state, 'PLAYING')
                        self.assertIsNone(b.status().idle_reason)
                    await self.native_event(b, 11000)

                await asyncio.wait_for(b._pump_pcm(source, Mock(drain=drain)), 1)
                self.assertEqual(b.status().state, 'IDLE')
                self.assertEqual(b.status().idle_reason, 'FINISHED')
                self.assertEqual(b.status().current_time, 51)
                self.assertFalse(b._input_starved)

    async def test_terminal_native_clock_preserves_pause_error_and_unstarted_track(self):
        for state, autoplay, started in (('PAUSED', False, True), ('IDLE', True, True),
                                         ('BUFFERING', True, False), ('BUFFERING', False, True)):
            with self.subTest(state=state, autoplay=autoplay, started=started):
                b = self.backend()
                b._input_finished = True
                b._status.state = state
                b._status.idle_reason = 'ERROR' if state == 'IDLE' else None
                b._autoplay = autoplay
                b._track_started = started
                await self.native_event(b, 11000)
                self.assertEqual(b.status().state, state)
                self.assertEqual(b.status().idle_reason, 'ERROR' if state == 'IDLE' else None)
