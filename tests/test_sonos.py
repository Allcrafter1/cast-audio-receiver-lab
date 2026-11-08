# SPDX-License-Identifier: MPL-2.0
import unittest
import asyncio
import threading
from unittest.mock import patch
import xml.etree.ElementTree as ET

from cast_audio_lab.backend import MediaMetadata
from cast_audio_lab.sonos import SonosAudioBackend, _seconds, _timestamp, sonos_needs_relay


class FakeSonos:
    def __init__(self):
        self.calls, self.volume, self.mute = [], 23, False
    def play_uri(self, url, **kwargs): self.calls.append(("load", url, kwargs))
    def play(self): self.calls.append(("play",))
    def pause(self): self.calls.append(("pause",))
    def stop(self): self.calls.append(("stop",))
    def seek(self, position): self.calls.append(("seek", position))
    def get_current_transport_info(self): return {"current_transport_state": "PLAYING"}
    def get_current_track_info(self): return {"position": "0:00:01", "duration": "0:03:00"}


class SonosBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_thread_load_cannot_finish_after_stop(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device)
        entered, release = threading.Event(), threading.Event()
        def delayed_load(*args, **kwargs):
            entered.set()
            release.wait(2)
            device.calls.append(("load_finished",))
        device.play_uri = delayed_load
        task = asyncio.create_task(backend.load("http://media/new", "audio/mpeg", True, 0))
        stopping = None
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 1))
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            stopping = asyncio.create_task(backend.stop())
            await asyncio.sleep(.05)
            self.assertNotIn(("stop",), device.calls,
                             "Stop raced ahead of a still-running remote Load")
            release.set()
            await asyncio.wait_for(stopping, 1)
            self.assertEqual(device.calls, [("load_finished",), ("stop",)])
        finally:
            release.set()
            if stopping:
                await asyncio.gather(stopping, return_exceptions=True)
            await backend.shutdown()

    async def test_replacement_cancels_old_feedback_before_remote_load(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device)
        cancelled = asyncio.Event()
        async def stale_poll():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        backend._poll_task = asyncio.create_task(stale_poll())
        await asyncio.sleep(0)
        original = device.play_uri
        def load(*args, **kwargs):
            self.assertTrue(cancelled.is_set(), "old feedback still active during replacement")
            original(*args, **kwargs)
        device.play_uri = load
        try:
            await backend.load("http://media/new", "audio/mpeg", True, 0)
        finally:
            await backend.shutdown()

    async def test_play_after_terminal_feedback_restarts_monitor(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device)
        backend._status.url = "http://media/song"
        backend._status.idle_reason = "FINISHED"
        try:
            await backend.play()
            self.assertIsNone(backend.status().idle_reason)
            self.assertIsNotNone(backend._poll_task)
            self.assertFalse(backend._poll_task.done())
        finally:
            await backend.shutdown()

    async def test_load_controls_and_volume_use_soco_device(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda host: device)
        await backend.set_metadata(MediaMetadata(title="Song"))
        await backend.load("http://media/song", "audio/mpeg", True, 12)
        await backend.pause(); await backend.seek(20); await backend.set_volume(0.4, True)
        await backend.shutdown()
        load = next(call for call in device.calls if call[0] == "load")
        self.assertEqual(load[1], "http://media/song")
        self.assertTrue(load[2]["start"])
        self.assertIn("Song", load[2]["meta"])
        self.assertIn("object.item.audioItem.musicTrack", load[2]["meta"])
        self.assertIn(("seek", "0:00:12"), device.calls)
        self.assertIn(("seek", "0:00:20"), device.calls)
        self.assertEqual(device.volume, 40)
        self.assertTrue(device.mute)

    async def test_launch_volume_restore_adopts_speaker_level(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device)
        try:
            await backend.initialize_volume()  # shared policy, not a volume write
            self.assertEqual(device.volume, 23, "launch restore must not blast the speaker")
            self.assertAlmostEqual(backend.status().volume, 0.23)
            await backend.load("http://media/song", "audio/mpeg", True, 0)
            await backend.set_volume(0.3, False)  # real sender change during a session
            self.assertEqual(device.volume, 30)
        finally:
            await backend.shutdown()

    async def test_initialize_adopts_speaker_volume_without_writing(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device)
        try:
            await backend.initialize_volume()
            await backend.load("http://media/song", "audio/mpeg", True, 0)
            self.assertEqual(device.volume, 23)
            self.assertAlmostEqual(backend.status().volume, 0.23)
        finally:
            await backend.shutdown()

    async def test_youtube_opus_is_converted_by_local_relay(self):
        device = FakeSonos()
        relays = []

        class FakeRelay:
            def __init__(self, host, *, ffmpeg):
                self.host, self.prepared, self.closed = host, [], False
                relays.append(self)
            async def prepare(self, url, content_type, supported):
                self.prepared.append((url, content_type, supported))
                return "http://192.0.2.1:4000/media/abc.mp3", "audio/mpeg"
            async def close(self): self.closed = True

        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda _: device, relay_factory=FakeRelay)
        await backend.set_metadata(MediaMetadata(title="Song", artist="Band", album="LP",
                                                 artwork_url="http://art/cover.jpg"))
        source = "https://rr1.googlevideo.com/videoplayback?itag=251&sig=x"
        await backend.load(source, "audio/webm; codecs=opus", True, 0)
        load = next(call for call in device.calls if call[0] == "load")
        self.assertEqual(load[1], "http://192.0.2.1:4000/media/abc.mp3")
        self.assertIn("audio/mpeg", load[2]["meta"])
        self.assertIn("Band", load[2]["meta"])
        self.assertIn("http://art/cover.jpg", load[2]["meta"])
        self.assertEqual(relays[0].host, "192.0.2.3")
        self.assertEqual(relays[0].prepared[0][0], source)
        self.assertNotIn("audio/webm", relays[0].prepared[0][2])
        self.assertEqual(backend.status().url, source)
        await backend.shutdown()
        self.assertTrue(relays[0].closed)

    def test_relay_decision(self):
        self.assertTrue(sonos_needs_relay("https://x.googlevideo.com/v?itag=251", "audio/webm"))
        self.assertTrue(sonos_needs_relay("http://media/x.ogg", "audio/ogg"))
        self.assertTrue(sonos_needs_relay("http://media/x", ""))
        self.assertTrue(sonos_needs_relay("http://127.0.0.1:8000/tts.mp3", "audio/mpeg"))
        self.assertFalse(sonos_needs_relay("https://radio.example/live", "audio/mpeg"))
        self.assertFalse(sonos_needs_relay("https://x.googlevideo.com/v?itag=140", "audio/mp4"))

    async def test_metadata_escapes_fields_and_falls_back_without_repeating_play(self):
        from cast_audio_lab.sonos import _track_didl
        metadata = MediaMetadata(title='Song & <title>', artist='Bänd & Co', album='A < B',
                                 artwork_url='http://art/cover?a=1&b=2')
        root = ET.fromstring(_track_didl('http://media/song?a=1&b=2', 'audio/mpeg', metadata))
        self.assertEqual(root.find('.//{http://purl.org/dc/elements/1.1/}title').text, metadata.title)
        self.assertEqual(root.find('.//{urn:schemas-upnp-org:metadata-1-0/upnp/}artist').text, metadata.artist)
        device = FakeSonos()
        backend = SonosAudioBackend('192.0.2.3', device_factory=lambda _: device)
        await backend.set_metadata(metadata)
        try:
            with patch('cast_audio_lab.sonos._track_didl', side_effect=ValueError('unsupported')):
                await backend.load('http://media/song', 'audio/mpeg', True, 0)
            loads = [call for call in device.calls if call[0] == 'load']
            self.assertEqual(len(loads), 1)
            self.assertEqual(loads[0][2], {'title': metadata.title, 'start': True})
        finally:
            await backend.shutdown()

    async def test_soco_didl_error_uses_title_only_fallback(self):
        from soco.exceptions import DIDLMetadataError
        device = FakeSonos()
        backend = SonosAudioBackend('192.0.2.3', device_factory=lambda _: device)
        await backend.set_metadata(MediaMetadata(title='Track'))
        try:
            with patch('soco.data_structures.to_didl_string', side_effect=DIDLMetadataError('bad metadata')):
                await backend.load('http://media/song', 'audio/mpeg', True, 0)
            self.assertIn(('load', 'http://media/song', {'title': 'Track', 'start': True}), device.calls)
        finally:
            await backend.shutdown()

    async def test_supported_radio_does_not_create_a_bounded_relay(self):
        device = FakeSonos()
        def unexpected_relay(*args, **kwargs):
            self.fail('supported live radio must remain direct')
        backend = SonosAudioBackend('192.0.2.3', device_factory=lambda _: device,
                                    relay_factory=unexpected_relay)
        try:
            await backend.load('https://radio.example/live', 'audio/mpeg', True, 0)
            self.assertEqual(device.calls[0][1], 'https://radio.example/live')
        finally:
            await backend.shutdown()

    def test_time_conversion_is_bounded(self):
        self.assertEqual(_timestamp(3661.9), "1:01:01")
        self.assertEqual(_seconds("1:01:01"), 3661.0)
        self.assertIsNone(_seconds("unknown"))


if __name__ == "__main__": unittest.main()

