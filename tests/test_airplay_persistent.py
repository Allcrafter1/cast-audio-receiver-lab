import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget
from cast_audio_lab.backend import MediaMetadata


class PersistentAirPlayTests(unittest.IsolatedAsyncioTestCase):
    def backend(self):
        return AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))

    async def events(self, backend, text):
        reader = asyncio.StreamReader()
        reader.feed_data(text.encode())
        reader.feed_eof()
        await backend._read_events(reader)

    async def test_seek_during_buffering_preserves_play_intent(self):
        b = self.backend()
        with patch.object(b, '_start_pipeline', new_callable=AsyncMock), patch.object(b, '_command', new_callable=AsyncMock):
            try:
                await b.load('test', 'audio/mpeg', True, 0)
                await b.seek(40)
                await b.seek(90)
                await self.events(b, '[STATUS] started\n')
                self.assertEqual(b.status().state, 'PLAYING')
                self.assertAlmostEqual(b.status().current_time, 90, delta=0.1)
            finally:
                await b.shutdown()

    async def test_pause_during_buffering_survives_started_and_seek(self):
        b = self.backend()
        with patch.object(b, '_start_pipeline', new_callable=AsyncMock), patch.object(b, '_command', new_callable=AsyncMock):
            try:
                await b.load('test', 'audio/mpeg', True, 0)
                await b.pause()
                await self.events(b, '[STATUS] started\n')
                self.assertEqual(b.status().state, 'PAUSED')
                await b.seek(90)
                await self.events(b, '[STATUS] started\n')
                self.assertEqual(b.status().state, 'PAUSED')
                self.assertEqual(b.status().current_time, 90)
            finally:
                await b.shutdown()

    async def test_warm_transition_keeps_transport_and_waits_for_flush(self):
        b = self.backend()
        writer = Mock(drain=AsyncMock())
        writer.transport.get_write_buffer_size.return_value = 0
        cli = Mock(returncode=None, stdin=writer, pid=123)
        b._cli = cli
        async def ack(*lines):
            self.assertEqual(lines, ('ACTION=FLUSH',))
            await self.events(b, '[STATUS] flushed\n')
        with patch.object(b, '_stop_track', new_callable=AsyncMock) as stop, patch.object(b, '_command', side_effect=ack) as command:
            await b._prepare_transport(True)
            stop.assert_awaited_once()
            command.assert_awaited_once()
        self.assertIs(b._cli, cli)
        writer.close.assert_not_called()

    async def test_python_buffer_tail_gets_second_flush(self):
        b = self.backend()
        writer = Mock(drain=AsyncMock())
        writer.transport.get_write_buffer_size.side_effect = [8192, 0]
        b._cli = Mock(returncode=None, stdin=writer, pid=123)
        order = []
        async def flush():
            order.append('flush')
        async def drain():
            order.append('drain')
        writer.drain.side_effect = drain
        with patch.object(b, '_stop_track', new_callable=AsyncMock), patch.object(b, '_flush_transport', side_effect=flush):
            await b._prepare_transport(True)
        self.assertEqual(order, ['flush', 'drain', 'flush'])

    async def test_failed_flush_falls_back_to_full_teardown(self):
        b = self.backend()
        b._cli = Mock(returncode=None)
        b._cli.stdin.transport.get_write_buffer_size.return_value = 0
        with patch.object(b, '_stop_track', new_callable=AsyncMock), patch.object(b, '_flush_transport', side_effect=TimeoutError), patch.object(b, '_stop_pipeline', new_callable=AsyncMock) as teardown:
            await b._prepare_transport(True)
            teardown.assert_awaited_once()

    async def test_real_flush_wait_is_not_satisfied_by_old_ack(self):
        b = self.backend()
        b._cli = Mock(returncode=None)
        b._flushed.set()
        with patch.object(b, '_command', new_callable=AsyncMock):
            task = asyncio.create_task(b._flush_transport())
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            await self.events(b, '[STATUS] flushed\n')
            await asyncio.wait_for(task, 1)

    async def test_finish_uses_decoded_samples_and_transport_clock_not_duration(self):
        b = self.backend()
        b.metadata = MediaMetadata(duration=999)
        b._decoded_bytes = 176400 * 3
        b._track_start = 75
        b._input_finished = True
        b._track_started = True
        b._status.state = 'PLAYING'
        await self.events(b, '[STATUS] playing elapsed_ms=2999\n')
        self.assertEqual(b.status().state, 'PLAYING')
        b._status.state = 'PAUSED'
        await self.events(b, '[STATUS] playing elapsed_ms=4000\n')
        self.assertEqual(b.status().state, 'PAUSED')
        b._status.state = 'PLAYING'
        await self.events(b, '[STATUS] playing elapsed_ms=3000\n')
        self.assertEqual(b.status().idle_reason, 'FINISHED')
        self.assertEqual(b.status().current_time, 78)
        await self.events(b, '[STATUS] playing elapsed_ms=5000\n')
        self.assertEqual(b.status().current_time, 78)

    async def test_old_elapsed_or_eof_cannot_complete_new_unstarted_track(self):
        b = self.backend()
        b._input_finished = True
        b._decoded_bytes = 176400
        b._status.state = 'BUFFERING'
        await self.events(b, '[STATUS] playing elapsed_ms=999999\n[STATUS] eof\n[STATUS] started\n')
        self.assertEqual(b.status().state, 'BUFFERING')
        self.assertFalse(b._track_started)

    async def test_decoder_eof_keeps_pipe_open_and_padding_out_of_sample_count(self):
        b = self.backend()
        b.metadata = MediaMetadata(duration=1)
        b._status.state = 'PLAYING'
        b._track_started = True
        b._decoder = Mock(wait=AsyncMock(return_value=0))
        reader = asyncio.StreamReader()
        reader.feed_data(bytes(176400))
        reader.feed_eof()
        async def drain():
            if b._input_finished:
                await self.events(b, '[STATUS] playing elapsed_ms=1000\n')
        writer = Mock(drain=AsyncMock(side_effect=drain))
        await asyncio.wait_for(b._pump_pcm(reader, writer), 1)
        self.assertEqual(b._decoded_bytes, 176400)
        self.assertEqual(b.status().idle_reason, 'FINISHED')
        writer.close.assert_not_called()

    async def test_cancelled_warm_load_cleans_transport(self):
        b = self.backend()
        blocked = asyncio.Event()
        async def prepare(_):
            blocked.set()
            await asyncio.Event().wait()
        with patch.object(b, '_prepare_transport', side_effect=prepare), patch.object(b, '_stop_pipeline', new_callable=AsyncMock) as teardown:
            task = asyncio.create_task(b.load('test', 'audio/mpeg', True, 0))
            await blocked.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            teardown.assert_awaited_once()

    async def test_failed_old_transport_status_does_not_poison_cold_fallback(self):
        b = self.backend()
        async def prepare(_):
            b._status.state = 'IDLE'
            b._status.idle_reason = 'ERROR'
        with patch.object(b, '_prepare_transport', side_effect=prepare), patch.object(b, '_start_pipeline', new_callable=AsyncMock), patch.object(b, '_command', new_callable=AsyncMock):
            await b.load('test', 'audio/mpeg', True, 0)
            await self.events(b, '[STATUS] started\n')
            self.assertEqual(b.status().state, 'PLAYING')
            self.assertIsNone(b.status().idle_reason)
            await b.shutdown()

    async def test_remote_controls_emit_explicit_user_intent(self):
        b = self.backend()
        controls = []
        b.add_control_listener(controls.append)
        b._status.url = "test"
        b._status.state = "PLAYING"
        await self.events(
            b,
            "[EVENT] remote command=pause\n[EVENT] remote command=next\n",
        )
        self.assertEqual([item.command for item in controls], ["pause", "next"])
        self.assertEqual(b.status().state, "PAUSED")
