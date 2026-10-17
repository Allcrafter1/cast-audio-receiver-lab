# SPDX-License-Identifier: MPL-2.0
import asyncio
import os
import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget
from cast_audio_lab.backend import MediaMetadata


class PersistentAirPlayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # These lifecycle tests stub the PCM pipeline. Real buffering and DACP
        # are exercised separately in test_airplay_feedback.py.
        for name in ('AirPlayAudioBackend._wait_for_audio', 'DacpServer.start'):
            stub = patch('cast_audio_lab.airplay.' + name, new_callable=AsyncMock)
            stub.start()
            self.addCleanup(stub.stop)

    async def test_oversized_child_lines_are_discarded_without_losing_following_events(self):
        b = self.backend()
        for method, suffix in ((b._read_events, b'[STATUS] flushed\n'),
                               (b._read_ffmpeg_log, b'normal diagnostic\n')):
            reader = asyncio.StreamReader(limit=64)
            reader.feed_data(b'x' * 100000 + b'\n' + suffix)
            reader.feed_eof()
            await method(reader)
            self.assertTrue(reader.at_eof())
        self.assertTrue(b._flushed.is_set())
        await b.shutdown()

    async def test_cancellation_during_sender_or_decoder_spawn_reaps_unassigned_child(self):
        for phase in ('sender', 'decoder'):
            with self.subTest(phase=phase):
                b = self.backend()
                if phase == 'decoder':
                    b._cli = Mock(returncode=None, stdin=Mock(), stdout=None, stderr=None,
                                  wait=AsyncMock(return_value=0))
                    b._prepare_transport = AsyncMock()
                spawn, children = subprocess.Popen, []
                def cancelling_spawn(*args, **kwargs):
                    process = spawn(*args, **kwargs)
                    children.append(process)
                    asyncio.current_task().cancel()
                    return process
                argv = [sys.executable, '-c', 'import time; time.sleep(60)']
                function = 'cliairplay_argv' if phase == 'sender' else 'ffmpeg_pcm_argv'
                with patch('cast_audio_lab.airplay.' + function, return_value=argv), \
                        patch('asyncio.base_subprocess.subprocess.Popen', side_effect=cancelling_spawn):
                    task = asyncio.create_task(b.load('test', 'audio/webm', True, 0))
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(task, 3)
                self.assertEqual(len(children), 1)
                self.assertIsNotNone(children[0].poll())
                self.assertIsNone(b._cli)
                self.assertIsNone(b._decoder)
                self.assertIsNone(b._temporary_directory)
                await b.shutdown()

    async def test_cancelled_track_teardown_still_reaps_before_pipeline_closes(self):
        b = self.backend()
        entered, release = asyncio.Event(), asyncio.Event()
        async def wait():
            entered.set()
            await release.wait()
            return 0
        decoder = Mock(returncode=None, stdin=None, stdout=None, stderr=None,
                       wait=AsyncMock(side_effect=wait))
        b._decoder = decoder
        task = asyncio.create_task(b._stop_track())
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        pipeline = asyncio.create_task(b._stop_pipeline())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertFalse(pipeline.done(), 'detached decoder must remain owned during cancellation')
        release.set()
        await pipeline
        decoder.wait.assert_awaited_once()

    async def test_play_after_terminal_failure_keeps_idle_until_fresh_load(self):
        b = self.backend()
        b._status.url = 'old'
        b._status.idle_reason = 'ERROR'
        with patch.object(b, '_command', new_callable=AsyncMock) as command:
            await b.play()
            await b.pause()
            command.assert_not_awaited()
        self.assertEqual(b.status().state, 'IDLE')
        self.assertEqual(b.status().idle_reason, 'ERROR')

    async def test_command_partial_write_and_backpressure_do_not_drop_suffix(self):
        b = self.backend()
        b._command_fd = 123
        written = bytearray()
        calls = 0
        def write(fd, payload):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise BlockingIOError()
            count = min(4, len(payload))
            written.extend(payload[:count])
            return count
        with patch('cast_audio_lab.airplay.os.write', side_effect=write):
            await b._command('ACTION=PAUSE', 'PROGRESS=17')
        self.assertEqual(written, b'ACTION=PAUSE\nPROGRESS=17\n')

    async def test_broken_command_pipe_reports_error_instead_of_fake_pause(self):
        b = self.backend()
        b._command_fd = 123
        b._status.state = 'PLAYING'
        with patch('cast_audio_lab.airplay.os.write', side_effect=BrokenPipeError()), \
                patch('cast_audio_lab.airplay.os.close'):
            with self.assertRaises(OSError):
                await b.pause()
        self.assertEqual(b.status().state, 'IDLE')
        self.assertEqual(b.status().idle_reason, 'ERROR')
        self.assertTrue(b._transport_failed.is_set())
        await b._stop_pipeline()

    async def test_broken_control_channel_retires_running_sender(self):
        b = self.backend()
        sender = await asyncio.create_subprocess_exec(sys.executable, '-c',
            'import time; time.sleep(60)', stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        reader, writer = os.pipe()
        os.close(reader)
        b._cli = sender
        b._command_fd = writer
        b._status.state = 'PLAYING'
        try:
            with self.assertRaises(OSError):
                await b.pause()
            await asyncio.wait_for(b._stop_pipeline(), 3)
            self.assertIsNotNone(sender.returncode)
            self.assertIsNone(b._cli)
            self.assertIsNone(b._command_fd)
            self.assertEqual(b.status().idle_reason, 'ERROR')
        finally:
            await b.shutdown()

    async def test_broken_stop_pipe_still_reaps_sender_and_closes_descriptor(self):
        b = self.backend()
        reader, writer = os.pipe()
        os.close(reader)
        b._command_fd = writer
        sender = Mock(returncode=None, stdin=None, stdout=None, stderr=None,
                      wait=AsyncMock(return_value=0))
        b._cli = sender
        await b.stop()
        sender.wait.assert_awaited_once()
        self.assertIsNone(b._cli)
        self.assertIsNone(b._command_fd)
        with self.assertRaises(OSError):
            os.fstat(writer)
        self.assertEqual(b.status().idle_reason, 'CANCELLED')

    async def test_remote_play_requests_recovery_without_fake_playing_state(self):
        b = self.backend()
        b._status.url = 'old'
        b._status.idle_reason = 'ERROR'
        controls = []
        b.add_control_listener(controls.append)
        await b._apply_remote_command('play')
        self.assertEqual([control.command for control in controls], ['play'])
        self.assertEqual(b.status().state, 'IDLE')
        self.assertEqual(b.status().idle_reason, 'ERROR')

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

    async def test_failed_flush_diagnostic_identifies_fallback_stage(self):
        b = self.backend()
        b._cli = Mock(returncode=None)
        b._cli.stdin.transport.get_write_buffer_size.return_value = 0
        with patch.object(b, '_stop_track', new_callable=AsyncMock), \
                patch.object(b, '_flush_transport', side_effect=TimeoutError), \
                patch.object(b, '_stop_pipeline', new_callable=AsyncMock), \
                self.assertLogs('cast_audio_lab.airplay', level='DEBUG') as logs:
            await b._prepare_transport(True)
        output = '\n'.join(logs.output)
        self.assertIn('event=transport_prepare mode=warm', output)
        self.assertIn('event=warm_transition result=cold_fallback stage=first_flush', output)

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

    async def test_sender_error_wakes_flush_and_keeps_safe_reason(self):
        b = self.backend()
        b._cli = Mock(returncode=None)
        with patch.object(b, '_command', new_callable=AsyncMock), \
                self.assertLogs('cast_audio_lab.airplay', level='DEBUG') as logs:
            task = asyncio.create_task(b._flush_transport())
            await asyncio.sleep(0)
            await self.events(
                b,
                '[STATUS] error code=flush_failed http=453 detail=private-value\n',
            )
            with self.assertRaisesRegex(RuntimeError, 'during flush'):
                await task
        output = '\n'.join(logs.output)
        self.assertIn('event=sender_error phase=flushing sender_code=flush_failed sender_http=453', output)
        self.assertNotIn('private-value', output)

    async def test_startup_exit_waits_for_structured_sender_reason(self):
        b = self.backend()
        b._cli = Mock(returncode=1)

        async def report_reason():
            await asyncio.sleep(0)
            await self.events(
                b,
                '[STATUS] error code=connect_failed http=401 detail=private-value\n',
            )

        reporter = asyncio.create_task(report_reason())
        with patch('cast_audio_lab.airplay.os.open', side_effect=OSError), \
                self.assertLogs('cast_audio_lab.airplay', level='WARNING') as logs:
            with self.assertRaisesRegex(
                RuntimeError, 'code=connect_failed http=401'
            ):
                await b._open_command_pipe(Path('/not-used'))
        await reporter
        self.assertNotIn('private-value', '\n'.join(logs.output))

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
