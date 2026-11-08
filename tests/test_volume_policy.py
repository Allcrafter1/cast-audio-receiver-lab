# SPDX-License-Identifier: MPL-2.0
"""Shared startup policy and both directions of output volume feedback."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from cast_audio_lab.backend import NullAudioBackend, CommandAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer
from cast_audio_lab.sonos import SonosAudioBackend
from cast_audio_lab.dlna import DlnaAudioBackend
from cast_audio_lab.mpv_backend import MpvAudioBackend


class VolumePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_device_level_wins_even_above_25_percent_without_writing(self):
        backend = NullAudioBackend()
        backend.read_volume = AsyncMock(return_value=(.72, False))
        backend.set_volume = AsyncMock()
        await backend.initialize_volume()
        self.assertEqual(backend.status().volume, .72)
        backend.set_volume.assert_not_awaited()

    async def test_zero_mute_unknown_invalid_and_read_error_use_25_unmuted(self):
        for value in (None, (0, False), (.8, True), (.6, None), (float('nan'), False),
                      (float('inf'), False), (-.1, False), (1.1, False), (True, False),
                      OSError('unavailable')):
            with self.subTest(value=value):
                backend = NullAudioBackend()
                backend.read_volume = AsyncMock(**({'side_effect': value} if isinstance(value, Exception)
                                                   else {'return_value': value}))
                backend.set_volume = AsyncMock(wraps=backend.set_volume)
                await backend.initialize_volume()
                backend.set_volume.assert_awaited_once_with(.25, False)
                self.assertEqual((backend.status().volume, backend.status().muted), (.25, False))

    async def test_query_timeout_falls_back_but_cancellation_propagates(self):
        backend = NullAudioBackend()
        entered = asyncio.Event()
        async def read():
            entered.set()
            await asyncio.Event().wait()
        backend.read_volume = read
        real_timeout = asyncio.timeout
        with patch('cast_audio_lab.backend.asyncio.timeout', lambda _: real_timeout(.01)):
            await backend.initialize_volume()
        self.assertEqual(backend.status().volume, .25)
        task = asyncio.create_task(backend.initialize_volume())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_load_without_launch_initializes_and_write_failure_blocks_audio(self):
        backend = NullAudioBackend()
        backend.set_volume = AsyncMock(side_effect=OSError('write failed'))
        backend.load = AsyncMock()
        player = VibecastAudioPlayer('ws://unused', 'p', 'test', backend)
        player._send = AsyncMock()
        await player.handle_message({'type': 'load', 'sessionId': 's', 'media': {
            'mediaSessionId': 1, 'streams': [{'url': 'http://media/song'}]}})
        backend.load.assert_not_awaited()
        self.assertEqual(player._send.call_args.args[0]['type'], 'error')

    async def test_launch_track_changes_stop_takeover_and_explicit_commands(self):
        backend = NullAudioBackend()
        backend.read_volume = AsyncMock(return_value=(.63, False))
        backend.set_volume = AsyncMock(wraps=backend.set_volume)
        player = VibecastAudioPlayer('ws://unused', 'p', 'test', backend)
        player._send = AsyncMock()
        await player.handle_message({'type': 'volume', 'sessionId': 's', 'level': 1,
                                     'initialize': True, 'volumeRevision': 1})
        self.assertEqual(player._send.call_args.args[0]['volume'], .63)
        self.assertEqual(player._send.call_args.args[0]['volumeRevision'], 1)
        # Explicit pre-load command must not be mistaken for launch restoration.
        await player.handle_message({'type': 'volume', 'sessionId': 's', 'level': .9,
                                     'muted': True, 'initialize': False, 'volumeRevision': 2})
        media = {'mediaSessionId': 1, 'streams': [{'url': 'http://media/song'}]}
        await player.handle_message({'type': 'load', 'sessionId': 's', 'media': media})
        await player.handle_message({'type': 'load', 'sessionId': 's', 'media': {**media, 'mediaSessionId': 2}})
        backend.read_volume.assert_awaited_once()
        self.assertEqual((backend.status().volume, backend.status().muted), (.9, True))
        await player.handle_message({'type': 'stop', 'sessionId': 's'})
        backend.read_volume.return_value = (0, False)
        await player.handle_message({'type': 'load', 'sessionId': 's', 'media': media})
        self.assertEqual((backend.status().volume, backend.status().muted), (.25, False))
        backend.read_volume.return_value = (.4, False)
        await player.handle_message({'type': 'volume', 'sessionId': 'new', 'level': 1,
                                     'initialize': True, 'volumeRevision': 3})
        self.assertEqual(backend.status().volume, .4)
        # Receiver feedback is reported without an echo write, including mute/zero.
        player.session_id = 'new'
        player._websocket = object()
        backend.set_volume.reset_mock()
        backend._status.volume, backend._status.muted = 0, True
        backend._emit_status()
        await asyncio.sleep(.01)
        report = player._send.call_args.args[0]
        self.assertEqual((report['volume'], report['muted'], report['volumeRevision']), (0, True, 3))
        backend.set_volume.assert_not_awaited()

    async def test_invalid_initialization_flag_never_writes_volume(self):
        backend = NullAudioBackend()
        backend.set_volume = AsyncMock()
        player = VibecastAudioPlayer('ws://unused', 'p', 'test', backend)
        player._send = AsyncMock()
        for flag in (None, 1, 'false'):
            await player.handle_message({'type': 'volume', 'sessionId': 's', 'level': 1,
                                         'initialize': flag})
            self.assertEqual(player._send.call_args.args[0]['type'], 'error')
        backend.set_volume.assert_not_awaited()

    async def test_legacy_launch_is_safe_and_following_command_is_not_capped(self):
        backend = NullAudioBackend()
        player = VibecastAudioPlayer('ws://unused', 'p', 'test', backend)
        player._send = AsyncMock()
        await player.handle_message({'type': 'volume', 'sessionId': 's', 'level': 1})
        self.assertEqual(backend.status().volume, .25)
        await player.handle_message({'type': 'volume', 'sessionId': 's', 'level': .8})
        self.assertEqual(backend.status().volume, .8)

    async def test_uncontrolled_command_output_cannot_claim_safe_start(self):
        backend = CommandAudioBackend('player {url}')
        with self.assertRaises(RuntimeError):
            await backend.initialize_volume()
        with self.assertRaises(RuntimeError):
            await backend.set_volume(.25, False)

    async def test_mpv_reads_live_properties_only_if_connected(self):
        backend = MpvAudioBackend()
        self.assertIsNone(await backend.read_volume())
        backend._writer = object()
        backend._command = AsyncMock(side_effect=[37, False])
        self.assertEqual(await backend.read_volume(), (.37, False))

    async def test_network_volume_feedback_survives_natural_end_until_stop(self):
        device = SimpleNamespace(volume=30, mute=False, stop=lambda: None,
            get_current_transport_info=lambda: {'current_transport_state': 'STOPPED'},
            get_current_track_info=lambda: {'position': '0:00:03', 'duration': '0:00:03'})
        profile = SimpleNamespace(volume_level=.3, is_volume_muted=False,
            transport_state=SimpleNamespace(name='STOPPED'), media_position=3,
            async_update=AsyncMock(), async_stop=AsyncMock())
        sonos = SonosAudioBackend('192.0.2.3', device_factory=lambda _: device)
        dlna = DlnaAudioBackend('http://renderer/device')
        dlna._profile, dlna._seen_playing = profile, True
        from cast_audio_lab.backend import MediaMetadata
        try:
            with patch('cast_audio_lab.sonos.VOLUME_POLL_INTERVAL', 1):
                for backend in (sonos, dlna):
                    backend.metadata = MediaMetadata(duration=3)
                    backend._status.url, backend._status.state = 'http://media/song', 'PLAYING'
                    backend._set_position(3)
                    backend._start_polling()
                await asyncio.sleep(1.1)
                for backend in (sonos, dlna):
                    self.assertEqual(backend.status().idle_reason, 'FINISHED')
                    self.assertFalse(backend._poll_task.done())
                device.volume, device.mute = 0, True
                profile.volume_level, profile.is_volume_muted = 0, True
                await asyncio.sleep(1.1)
                for backend in (sonos, dlna):
                    self.assertEqual((backend.status().volume, backend.status().muted), (0, True))
        finally:
            await sonos.shutdown()
            await dlna.shutdown()
        self.assertIsNone(sonos._poll_task)
        self.assertIsNone(dlna._poll_task)

    async def test_dlna_adopts_actual_level_and_applies_shared_fallback(self):
        profile = SimpleNamespace(volume_level=.6, is_volume_muted=False,
            has_volume_mute=True, async_update=AsyncMock(), async_set_volume_level=AsyncMock(),
            async_mute_volume=AsyncMock())
        backend = DlnaAudioBackend('http://renderer/device', profile_factory=AsyncMock(return_value=profile))
        await backend.initialize_volume()
        self.assertEqual(backend.status().volume, .6)
        profile.async_set_volume_level.assert_not_awaited()
        profile.is_volume_muted = True
        await backend.initialize_volume()
        profile.async_set_volume_level.assert_awaited_once_with(.25)
        profile.async_mute_volume.assert_awaited_once_with(False)


class SonosEventsTests(unittest.IsolatedAsyncioTestCase):
    def make_backend(self):
        self.subscription = SimpleNamespace(is_subscribed=True, unsubscribe=lambda: None)
        self.event_queue = None
        def subscribe(**kwargs):
            self.assertTrue(kwargs['auto_renew'])
            self.event_queue = kwargs['event_queue']
            return self.subscription
        self.device = SimpleNamespace(volume=43, mute=False, stop=lambda: None,
            renderingControl=SimpleNamespace(subscribe=subscribe))
        return SonosAudioBackend('192.0.2.3', device_factory=lambda _: self.device)

    async def test_zero_or_muted_sonos_is_physically_set_to_25_unmuted(self):
        backend = self.make_backend()
        for level, muted in ((0, False), (80, True)):
            self.device.volume, self.device.mute = level, muted
            await backend.initialize_volume()
            self.assertEqual((self.device.volume, self.device.mute), (25, False))
        await backend.shutdown()

    async def test_threaded_event_updates_immediately_without_write_or_poll(self):
        backend = self.make_backend()
        try:
            await backend._subscribe_volume()
            await asyncio.to_thread(self.event_queue.put, SimpleNamespace(variables={
                'volume': {'Master': '18'}, 'mute': {'Master': '1'}}))
            await asyncio.sleep(0)
            self.assertEqual((backend.status().volume, backend.status().muted), (.18, True))
            self.assertEqual((self.device.volume, self.device.mute), (43, False))
            backend.read_volume = AsyncMock()
            await backend._refresh_volume()
            backend.read_volume.assert_not_awaited()
            old_queue = self.event_queue
            await backend.stop()
            await asyncio.to_thread(old_queue.put, SimpleNamespace(variables={'volume': {'Master': '99'}}))
            await asyncio.sleep(0)
            self.assertEqual(backend.status().volume, .18)
        finally:
            await backend.shutdown()

    async def test_missing_notify_renewal_failure_and_silence_use_fallback(self):
        backend = self.make_backend()
        try:
            await backend._subscribe_volume()
            await backend._refresh_volume()  # SUBSCRIBE without any NOTIFY
            self.assertEqual(backend.status().volume, .43)
            backend._receive_volume(backend._event_generation, SimpleNamespace(
                variables={'volume': {'Master': '22'}}))
            await asyncio.to_thread(self.subscription.auto_renew_fail, OSError('offline'))
            await asyncio.sleep(0)
            await backend._refresh_volume()
            self.assertEqual(backend.status().volume, .43)
            backend._events_ready = True
            backend._last_volume_event = 0
            backend._subscription_started = 0
            queue = self.event_queue
            await backend._refresh_volume()
            self.assertIsNot(self.event_queue, queue, 'watchdog must renew a silent event path')
            backend.read_volume = AsyncMock(side_effect=RuntimeError('no volume'))
            await backend._refresh_volume()  # failure must not terminate playback
        finally:
            await backend.shutdown()

    async def test_cancelled_subscription_is_cleaned_before_stop(self):
        import threading
        backend = self.make_backend()
        entered, release = threading.Event(), threading.Event()
        original = self.device.renderingControl.subscribe
        unsubscribed = []
        self.subscription.unsubscribe = lambda: unsubscribed.append(True)
        def delayed(**kwargs):
            entered.set()
            release.wait(2)
            return original(**kwargs)
        self.device.renderingControl.subscribe = delayed
        task = asyncio.create_task(backend._subscribe_volume())
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 1))
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            stopping = asyncio.create_task(backend.stop())
            await asyncio.sleep(.01)
            release.set()
            await asyncio.wait_for(stopping, 1)
            self.assertEqual(unsubscribed, [True])
            self.assertIsNone(backend._subscription)
        finally:
            release.set()
            await backend.shutdown()
