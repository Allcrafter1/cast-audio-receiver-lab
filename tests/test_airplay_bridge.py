import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget, load_airplay_target
from cast_audio_lab.backend import MediaMetadata
from cast_audio_lab.vibecast_player import VibecastAudioPlayer, build_parser, create_output, run_player


class AirPlayConfigurationTests(unittest.TestCase):
    def test_identity_survives_cast_rename(self):
        with tempfile.TemporaryDirectory() as d:
            config = Path(d) / 'target.json'
            config.write_text(json.dumps({'host': '192.0.2.1', 'device_id': 'AA:BB:CC:DD:EE:FF', 'port': 5000, 'protocol': 'raop'}))
            first = build_parser().parse_args(['--backend', 'airplay', '--airplay-config', str(config), '--name', 'Kitchen'])
            second = build_parser().parse_args(['--backend', 'airplay', '--airplay-config', str(config), '--name', 'Music'])
            backend, identity = create_output(first)
            self.assertIsInstance(backend, AirPlayAudioBackend)
            self.assertEqual(backend.target.port, 5000)
            self.assertEqual(identity, create_output(second)[1])

    def test_missing_route_and_ignored_route_are_rejected(self):
        for argv in [['--backend', 'airplay'], ['--backend', 'mpv', '--airplay-config', 'target.json']]:
            with self.assertRaises(ValueError):
                create_output(build_parser().parse_args(argv))

    def test_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'target.json'
            for value in [[], {}, {'host': 'x', 'port': True}, {'host': 'x', 'port': 70000}, {'host': 'x', 'txt': {'x': 3}}, {'host': 'x', 'unexpected': 'x'}]:
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    load_airplay_target(path)

    def test_pairing_secrets_not_in_repr(self):
        target = AirPlayTarget('example.test', credentials='private-auth', password='private-password', legacy_secret='private-secret')
        self.assertNotIn('private-', repr(target))


class AirPlayLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_artwork_reuses_file_but_new_url_is_converted(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        backend._temporary_directory = tempfile.TemporaryDirectory()
        async def convert(url, path, ffmpeg):
            path.write_bytes(b'image')
            return True
        try:
            with patch('cast_audio_lab.airplay.prepare_square_artwork', side_effect=convert) as converter, patch.object(backend, '_command', new_callable=AsyncMock):
                backend.metadata = MediaMetadata(artwork_url='https://example.invalid/one')
                await backend._deliver_artwork()
                await backend._deliver_artwork()
                self.assertEqual(converter.await_count, 1)
                backend.metadata = MediaMetadata(artwork_url='https://example.invalid/two')
                await backend._deliver_artwork()
                self.assertEqual(converter.await_count, 2)
                (Path(backend._temporary_directory.name) / 'cover.jpg').unlink()
                await backend._deliver_artwork()
                self.assertEqual(converter.await_count, 3)
        finally:
            await backend.shutdown()

    async def test_progress_waits_for_audio_and_sends_duration_after_seek(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        backend.metadata = MediaMetadata(duration=180)
        backend._status.state = 'PAUSED'
        backend._set_position(75)
        with patch.object(backend, '_command', new_callable=AsyncMock) as command:
            await backend._send_progress()
            command.assert_not_awaited()
            backend._audio_ready = True
            await backend._send_progress()
            command.assert_awaited_once_with('DURATION=180', 'PROGRESS=75')

    async def test_truncated_successful_decoder_is_not_finished(self):
        for duration, expected in [(20, False), (1, True)]:
            backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'), persistent=False)
            backend.metadata = MediaMetadata(duration=duration)
            backend._status.state = 'PLAYING'
            backend._decoder = Mock(wait=AsyncMock(return_value=0))
            source = asyncio.StreamReader()
            source.feed_data(b'\0' * 176400)
            source.feed_eof()
            destination = Mock(drain=AsyncMock())
            await backend._pump_pcm(source, destination)
            self.assertEqual(backend._input_finished, expected)
            destination.close.assert_called_once()
            if not expected:
                self.assertEqual(backend.status().idle_reason, 'ERROR')

    async def test_artwork_cancellation_reaps_helper_without_sending_art(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        backend.metadata = MediaMetadata(artwork_url='https://example.invalid/cover')
        backend._temporary_directory = tempfile.TemporaryDirectory()
        started = asyncio.Event()
        process = Mock(returncode=None)
        async def wait():
            started.set()
            if process.returncode is None:
                await asyncio.Event().wait()
            return process.returncode
        process.wait = wait
        process.kill.side_effect = lambda: setattr(process, 'returncode', -9)
        with patch('cast_audio_lab.airplay.asyncio.create_subprocess_exec', new=AsyncMock(return_value=process)), patch.object(backend, '_command', new_callable=AsyncMock) as command:
            task = asyncio.create_task(backend._deliver_artwork())
            await started.wait()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            process.kill.assert_called_once()
            command.assert_not_awaited()
        backend._temporary_directory.cleanup()

    async def test_load_and_seek_hold_requested_position_until_started(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        await backend.set_metadata(MediaMetadata(duration=180))
        with patch.object(backend, '_start_pipeline', new_callable=AsyncMock), patch.object(backend, '_command', new_callable=AsyncMock) as command:
            await backend.load('test', 'audio/mpeg', True, 0)
            self.assertEqual(backend.status().state, 'BUFFERING')
            self.assertEqual(backend.status().current_time, 0)
            self.assertTrue(any('PROGRESS=0' in call.args for call in command.await_args_list))
            reader = asyncio.StreamReader()
            reader.feed_data(b'[STATUS] started\n')
            reader.feed_eof()
            await backend._read_events(reader)
            self.assertEqual(backend.status().state, 'PLAYING')
            await backend.seek(75)
            self.assertEqual(backend.status().state, 'BUFFERING')
            self.assertEqual(backend.status().current_time, 75)

    async def test_eof_requires_completed_input_and_emits_finished_once(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'), persistent=False)
        backend._status.state = 'PLAYING'
        for completed, expected in [(False, 'PLAYING'), (True, 'IDLE')]:
            backend._input_finished = completed
            reader = asyncio.StreamReader()
            reader.feed_data(b'[STATUS] eof\n[STATUS] eof\n')
            reader.feed_eof()
            await backend._read_events(reader)
            self.assertEqual(backend.status().state, expected)
        self.assertEqual(backend.status().idle_reason, 'FINISHED')

    async def test_stop_drains_backpressured_decoder_and_allows_reuse(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        for _ in range(2):
            child = await asyncio.create_subprocess_exec(
                sys.executable, '-c',
                'import os,time; os.write(1, b"x" * 1048576); time.sleep(30)',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            backend._decoder = child
            await asyncio.sleep(0.15)
            await asyncio.wait_for(backend._stop_pipeline(), 5)
            self.assertIsNotNone(child.returncode)
            self.assertIsNone(backend._decoder)

    async def test_decoder_diagnostics_do_not_expose_signed_urls(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        reader = asyncio.StreamReader()
        reader.feed_data(b'failed https://example.invalid/audio?token=private-token\nmore details\n')
        reader.feed_eof()
        with self.assertLogs('cast_audio_lab.airplay', level='WARNING') as logs:
            await backend._read_ffmpeg_log(reader)
        self.assertEqual(len(logs.output), 1)
        self.assertNotIn('private-token', str(logs.output))

    async def test_partial_start_reaps_process_and_removes_fifo(self):
        # A harmless local child replaces cliairplay; no network/audio target used.
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'), cliairplay=sys.executable)
        observed = {}

        async def fail(path):
            observed['process'] = backend._cli
            observed['directory'] = path.parent
            raise RuntimeError('simulated command-pipe failure')

        with patch.object(backend, '_open_command_pipe', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'simulated'):
                await backend.load('https://example.invalid/audio', 'audio/mpeg', True, 0)
        self.assertIsNotNone(observed['process'].returncode)
        self.assertFalse(observed['directory'].exists())
        self.assertIsNone(backend._cli)
        self.assertEqual(backend._reader_tasks, [])
        self.assertEqual(backend.status().idle_reason, 'ERROR')

    async def test_cancelled_start_also_cleans_up(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'), cliairplay=sys.executable)
        entered = asyncio.Event()
        observed = {}

        async def block(path):
            observed['process'] = backend._cli
            observed['directory'] = path.parent
            entered.set()
            await asyncio.Event().wait()

        with patch.object(backend, '_open_command_pipe', side_effect=block):
            task = asyncio.create_task(backend.load('https://example.invalid/audio', 'audio/mpeg', True, 0))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertIsNotNone(observed['process'].returncode)
        self.assertFalse(observed['directory'].exists())

    async def test_bridge_reports_runtime_failure_and_accepts_next_load(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        player = VibecastAudioPlayer('ws://example.invalid', 'test', 'Test', backend)
        player._send = AsyncMock()
        message = {'type': 'load', 'sessionId': 's1', 'media': {'streams': [{'url': 'https://example.invalid/audio'}]}}
        with patch.object(backend, '_start_pipeline', side_effect=RuntimeError('simulated unavailable target')):
            with self.assertLogs('cast_audio_lab.vibecast_player', level='ERROR'):
                await player.handle_message(message)
        self.assertEqual(player._send.await_args.args[0]['type'], 'error')
        with patch.object(backend, '_start_pipeline', new_callable=AsyncMock):
            await player.handle_message(message)
        self.assertEqual(player._send.await_args.args[0]['playerState'], 'BUFFERING')
        await backend.shutdown()

    async def test_adapter_exit_shuts_backend_down(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1'))
        player = VibecastAudioPlayer('ws://example.invalid', 'test', 'Test', backend)
        player.run = AsyncMock(side_effect=RuntimeError('bridge failure'))
        backend.shutdown = AsyncMock()
        with self.assertRaises(RuntimeError):
            await run_player(player)
        backend.shutdown.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
