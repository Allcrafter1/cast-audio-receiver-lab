# SPDX-License-Identifier: MPL-2.0
import asyncio
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientSession, ClientTimeout
from zeroconf import NonUniqueNameException

from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget, cliairplay_argv, dacp_identity
from cast_audio_lab.dacp import DacpServer, volume_feedback
from cast_audio_lab.vibecast_player import VibecastAudioPlayer


async def events(backend, text):
    reader = asyncio.StreamReader()
    reader.feed_data(text.encode())
    reader.feed_eof()
    await backend._read_events(reader)


class DacpTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_waits_for_goodbye_before_closing_mdns_socket(self):
        server = DacpServer('AABB', AsyncMock(), AsyncMock())
        goodbye = asyncio.get_running_loop().create_future()
        zc = Mock(async_unregister_service=AsyncMock(return_value=goodbye), async_close=AsyncMock())
        server.zeroconf, server.service = zc, object()
        closing = asyncio.create_task(server.close())
        try:
            await asyncio.sleep(0)
            zc.async_close.assert_not_awaited()
        finally:
            goodbye.set_result(None)
            await closing
        zc.async_close.assert_awaited_once()

    def test_legacy_dacp_identity_is_full_width_without_changing_hap_pairing_identity(self):
        for protocol, expected in [('raop', '0000AABBCCDDEEFF'), ('auto', 'AABBCCDDEEFF'),
                                   ('airplay2', 'AABBCCDDEEFF')]:
            target = AirPlayTarget('127.0.0.1', protocol=protocol, device_id='AA:BB:CC:DD:EE:FF')
            identity = dacp_identity(target)
            argv = cliairplay_argv('cliairplay', target, Path('/tmp/test'), volume=.5, latency_ms=2000)
            self.assertEqual(identity, expected)
            self.assertEqual(argv[argv.index('--dacp') + 1], identity)
            if protocol == 'raop':
                self.assertEqual(identity, f'{int(identity, 16):016X}')

    def test_volume_formats_and_invalid_values(self):
        for query, expected in [({'dmcp.volume': '42'}, (.42, False)),
                                ({'dmcp.device-volume': '-15'}, (.5, False)),
                                ({'dmcp.device-volume': '-144'}, (0, True)),
                                ({'dmcp.device-busy': '1'}, None)]:
            self.assertEqual(volume_feedback(query), expected)
        for key in ('dmcp.volume', 'dmcp.device-volume'):
            for value in ('nan', 'inf', '-inf', 'bad', '101', '-145'):
                with self.assertRaises(ValueError):
                    volume_feedback({key: value})

    async def test_real_http_authenticated_feedback_controls_and_cleanup(self):
        backend = AirPlayAudioBackend(AirPlayTarget('127.0.0.1'))
        backend._command = AsyncMock()
        backend._status.state = 'PLAYING'
        statuses, controls = [], []
        backend.add_status_listener(statuses.append)
        backend.add_control_listener(controls.append)
        diagnostics = Mock()
        server = DacpServer('AABBCCDDEEFF', backend._receiver_volume, backend._receiver_control,
                            diagnostic=diagnostics)
        zc = Mock(async_register_service=AsyncMock(), async_unregister_service=AsyncMock(),
                  async_close=AsyncMock())
        with patch('cast_audio_lab.dacp.AsyncZeroconf', return_value=zc):
            await server.start('127.0.0.1', 5000)
        self.addAsyncCleanup(server.close)
        service = zc.async_register_service.await_args.args[0]
        self.assertEqual(service.name, 'iTunes_Ctrl_AABBCCDDEEFF._dacp._tcp.local.')
        self.assertEqual(service.port, server.runner.addresses[0][1])
        self.assertEqual(service.parsed_addresses(), ['127.0.0.1'])
        self.assertEqual(service.properties[b'OSsi'], b'0x1F5')
        self.assertEqual(service.properties[b'Ver'], b'131075')
        base = f'http://127.0.0.1:{service.port}/ctrl-int/1/'
        headers = {'Active-Remote': server.active_remote}
        async with ClientSession(timeout=ClientTimeout(total=5)) as client:
            for token in ('', 'wrong', 'ü'):
                async with client.get(base + 'pause', headers={'Active-Remote': token}) as response:
                    self.assertEqual(response.status, 403)
            self.assertFalse(controls)
            server.peer = '192.0.2.1'
            async with client.get(base + 'pause', headers=headers) as response:
                self.assertEqual(response.status, 403)
            server.peer = '127.0.0.1'
            self.assertEqual([c.args[0] for c in diagnostics.call_args_list],
                             ['dacp_rejected_token', 'dacp_rejected_peer'])
            self.assertNotIn(server.active_remote, str(diagnostics.call_args_list))
            for _ in range(2):
                async with client.get(base + 'setproperty?dmcp.device-volume=-15', headers=headers) as response:
                    self.assertEqual(response.status, 204)
            self.assertEqual(len(statuses), 1)
            self.assertEqual(backend.status().volume, .5)
            backend._command.assert_not_awaited()  # No echo for absolute feedback.
            for command in ('play', 'pause', 'playpause', 'stop', 'nextitem', 'previtem'):
                async with client.get(base + command, headers=headers) as response:
                    self.assertEqual(response.status, 204)
            self.assertEqual([c.command for c in controls],
                             ['play', 'pause', 'pause', 'stop', 'next', 'previous'])
            self.assertEqual(backend.status().state, 'PLAYING')  # Controller applies requests.
            for command in ('volumeup', 'volumedown', 'mutetoggle'):
                async with client.get(base + command, headers=headers) as response:
                    self.assertEqual(response.status, 204)
            self.assertTrue(backend.status().muted)
            self.assertEqual(backend._command.await_count, 3)
            for path, status in [('setproperty?dmcp.volume=nan', 400), ('unknown', 404),
                                 ('setproperty?dmcp.device-busy=1', 204)]:
                async with client.get(base + path, headers=headers) as response:
                    self.assertEqual(response.status, status)
        await server.close()
        await server.close()
        zc.async_unregister_service.assert_awaited_once_with(service)
        zc.async_close.assert_awaited_once()

    async def test_advertisement_failure_closes_listener(self):
        server = DacpServer('AABB', AsyncMock(), AsyncMock())
        zc = Mock(async_register_service=AsyncMock(side_effect=RuntimeError('test')),
                  async_unregister_service=AsyncMock(), async_close=AsyncMock())
        with patch('cast_audio_lab.dacp.AsyncZeroconf', return_value=zc):
            with self.assertRaises(RuntimeError):
                await server.start('127.0.0.1', 5000)
        self.assertIsNone(server.runner)
        self.assertIsNone(server.zeroconf)
        zc.async_close.assert_awaited_once()

    async def test_duplicate_advertisement_never_withdraws_other_session(self):
        server = DacpServer('AABB', AsyncMock(), AsyncMock())
        zc = Mock(async_register_service=AsyncMock(side_effect=NonUniqueNameException()),
                  async_unregister_service=AsyncMock(), async_close=AsyncMock())
        with patch('cast_audio_lab.dacp.AsyncZeroconf', return_value=zc):
            with self.assertRaises(RuntimeError):
                await server.start('127.0.0.1', 5000)
        self.assertIsNone(server.runner)
        zc.async_unregister_service.assert_not_awaited()
        zc.async_close.assert_awaited_once()

    def test_native_receives_matching_identity_and_token(self):
        argv = cliairplay_argv('cliairplay', AirPlayTarget('127.0.0.1', device_id='AA:BB:CC:DD:EE:FF'),
                              Path('/tmp/test-command'), volume=.5, latency_ms=2000, active_remote='12345')
        self.assertEqual(argv[argv.index('--dacp') + 1], 'AABBCCDDEEFF')
        self.assertEqual(argv[argv.index('--activeremote') + 1], '12345')

    async def test_feedback_and_buttons_reach_the_cast_player_bridge(self):
        backend = AirPlayAudioBackend(AirPlayTarget('127.0.0.1'))
        backend._command = AsyncMock()
        backend._status.url = 'test'
        backend._status.state = 'PLAYING'
        player = VibecastAudioPlayer('ws://127.0.0.1', 'test', 'test', backend)
        player.session_id = 'session'
        player._websocket = object()
        player._send = AsyncMock()
        await backend._receiver_volume(.3, False)
        await asyncio.sleep(0)
        report = player._send.await_args.args[0]
        self.assertEqual(report['volume'], .3)
        self.assertEqual(report['sessionId'], 'session')
        backend._command.assert_not_awaited()
        for control in ('pause', 'play', 'next', 'previous', 'stop'):
            await backend._receiver_control(control)
            await asyncio.sleep(0)
            report = player._send.await_args.args[0]
            self.assertEqual(report['type'], 'controlRequest')
            self.assertEqual(report['control']['command'], control)
        # The existing frontend sends Play/Pause back to the adapter; verify
        # those commands actually drive the native sender, not only the UI.
        for control, action in (('pause', 'ACTION=PAUSE'), ('play', 'ACTION=PLAY')):
            await player.handle_message({'type': control, 'sessionId': 'session'})
            self.assertIn(action, [arg for call in backend._command.await_args_list for arg in call.args])
        player._websocket = None
        await backend.shutdown()


class BufferedStartTests(unittest.IsolatedAsyncioTestCase):
    def backend(self):
        backend = AirPlayAudioBackend(AirPlayTarget('192.0.2.1', protocol='raop'))
        backend._prepare_transport = AsyncMock()
        backend._start_pipeline = AsyncMock()
        backend._command = AsyncMock()
        self.addAsyncCleanup(backend.shutdown)
        return backend

    async def test_load_and_warm_load_wait_for_fresh_audio_then_schedule_lead(self):
        backend = self.backend()
        for position in (0, 70):
            backend._pcm_ready.set()  # Stale readiness must not start a new track.
            backend._command.reset_mock()
            task = asyncio.create_task(backend.load('test', 'audio/mpeg', True, position))
            await asyncio.sleep(.01)
            self.assertFalse(task.done())
            self.assertFalse(any('ACTION=START' in c.args for c in backend._command.await_args_list))
            await events(backend, 'connected to receiver on port 5000, player latency is 2500 ms\n'
                         '[STATUS] route protocol=raop\n[STATUS] audio buffered_ms=8\n')
            before = int(time.time() * 1000)
            await asyncio.wait_for(task, 1)
            start = next(c.args[0] for c in backend._command.await_args_list if 'ACTION=START' in c.args)
            scheduled = int(start.split('=')[1])
            self.assertGreaterEqual(scheduled, before + 2600)
            self.assertLessEqual(scheduled, int(time.time() * 1000) + 2600)
            self.assertEqual(backend.status().current_time, position)
            await backend._stop_track()

    async def test_failure_before_audio_aborts_without_start(self):
        for name in ('_transport_failed', '_decode_failed'):
            backend = self.backend()
            task = asyncio.create_task(backend.load('test', 'audio/mpeg', True, 0))
            await asyncio.sleep(.01)
            getattr(backend, name).set()
            with self.assertRaises(RuntimeError):
                await asyncio.wait_for(task, 1)
            self.assertFalse(any('ACTION=START' in c.args for c in backend._command.await_args_list))
            self.assertEqual(backend.status().idle_reason, 'ERROR')

    async def test_auto_route_uses_raop_lead_but_leaves_airplay2_scheduler_intact(self):
        for protocol in ('raop', 'airplay2'):
            backend = self.backend()
            backend._route_protocol = 'auto'
            task = asyncio.create_task(backend.load('test', 'audio/mpeg', True, 0))
            await asyncio.sleep(.01)
            await events(backend, f'[STATUS] route protocol={protocol}\n[STATUS] audio buffered_ms=8\n')
            await asyncio.wait_for(task, 1)
            start = next(c.args[0] for c in backend._command.await_args_list if 'ACTION=START' in c.args)
            self.assertEqual(start == 'START_UNIX_MS=0', protocol == 'airplay2')

    async def test_stop_cancels_pending_readiness(self):
        backend = self.backend()
        task = asyncio.create_task(backend.load('test', 'audio/mpeg', True, 0))
        await asyncio.sleep(.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(backend._start_pending)

    async def test_start_ack_waits_for_audible_time_and_preserves_pause(self):
        for paused in (False, True):
            backend = self.backend()
            backend._status.state = 'BUFFERING'
            backend._autoplay = True
            backend._start_pending = True
            backend._set_position(12)
            await events(backend, f'[STATUS] started at_unix_ms={int(time.time() * 1000) + 50}\n')
            self.assertEqual(backend.status().state, 'BUFFERING')
            self.assertEqual(backend.status().current_time, 12)
            if paused:
                await backend.pause()
            await asyncio.gather(*backend._aux_tasks)
            self.assertEqual(backend.status().state, 'PAUSED' if paused else 'PLAYING')
            self.assertAlmostEqual(backend.status().current_time, 12, delta=.1)

    async def test_toggle_during_buffering_requests_pause_not_play(self):
        backend = self.backend()
        backend._status.state = 'BUFFERING'
        backend._autoplay = True
        controls = []
        backend.add_control_listener(controls.append)
        await backend._receiver_control('toggle_play_pause')
        self.assertEqual(controls[0].command, 'pause')
