import unittest
import asyncio
from types import SimpleNamespace
import importlib.util
from unittest.mock import AsyncMock

from cast_audio_lab.backend import MediaMetadata
from cast_audio_lab.dlna import DlnaAudioBackend


class FakeDmr:
    def __init__(self):
        self.calls = []
        self.has_volume_mute = True
        self.volume_level = 0.5
        self.is_volume_muted = False
        self.transport_state = None
        self.media_position = 0
        self.can_play = True

    async def async_update(self): self.calls.append(("update",))
    async def construct_play_media_metadata(self, url, title, **kwargs):
        self.calls.append(("metadata", url, title, kwargs)); return "<DIDL/>"
    async def async_set_transport_uri(self, url, title, metadata):
        self.calls.append(("load", url, title, metadata))
    async def async_wait_for_can_play(self): self.calls.append(("wait",))
    async def async_play(self): self.calls.append(("play",))
    async def async_pause(self): self.calls.append(("pause",))
    async def async_stop(self): self.calls.append(("stop",))
    async def async_seek_abs_time(self, position):
        self.calls.append(("seek", position.total_seconds()))
    async def async_set_volume_level(self, level): self.calls.append(("volume", level))
    async def async_mute_volume(self, muted): self.calls.append(("mute", muted))


class DlnaBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_stopped_preload_survives_until_explicit_play(self):
        profile = FakeDmr()
        profile.transport_state = SimpleNamespace(name="STOPPED")
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=AsyncMock(return_value=profile))
        await backend.load("http://source/", "audio/mpeg", False, 0)
        backend._load_started -= 60
        try:
            await asyncio.sleep(1.1)
            self.assertEqual(backend.status().state, "PAUSED")
            self.assertIsNone(backend.status().idle_reason)
            self.assertFalse(backend._poll_task.done())
            self.assertNotIn(("play",), profile.calls)
            await backend.play()
            self.assertEqual(backend.status().state, "BUFFERING")
            self.assertFalse(backend._awaiting_play)
            profile.transport_state.name = "PLAYING"
            await asyncio.sleep(1.1)
            self.assertEqual(backend.status().state, "PLAYING")
        finally:
            await backend.shutdown()

    async def test_https_uses_local_relay_before_device_load(self):
        profile = FakeDmr()
        profile.sink_protocol_info = ["http-get:*:audio/mpeg:*"]
        relay = AsyncMock()
        relay.prepare.return_value = ("http://local/media/opaque.mp3", "audio/mpeg")
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml",
            profile_factory=AsyncMock(return_value=profile), relay_factory=lambda *a, **k: relay)
        await backend.load("https://source/audio", "audio/webm", True, 0)
        self.assertIn(("load", "http://local/media/opaque.mp3", "Cast audio", "<DIDL/>"), profile.calls)
        self.assertEqual(backend.status().url, "https://source/audio")
        await backend.stop()
        relay.close.assert_awaited_once()

    async def test_accepted_load_is_not_claimed_as_playing_before_device_feedback(self):
        profile = FakeDmr()
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=AsyncMock(return_value=profile))
        await backend.load("http://source/", "audio/mpeg", True, 0)
        self.assertEqual(backend.status().state, "BUFFERING")
        await backend.shutdown()

    @unittest.skipUnless(importlib.util.find_spec("async_upnp_client"), "DLNA extra not installed")
    async def test_play_readiness_timeout_returns_error_without_fake_playing(self):
        profile = FakeDmr()
        profile.can_play = False
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=AsyncMock(return_value=profile))
        with self.assertRaises(RuntimeError):
            await backend.load("http://source/", "audio/mpeg", True, 0)
        self.assertNotIn(("play",), profile.calls)
        self.assertEqual(backend.status().idle_reason, "ERROR")
        await backend.shutdown()

    @unittest.skipUnless(importlib.util.find_spec("async_upnp_client"), "DLNA extra not installed")
    async def test_rejected_load_is_recoverable_and_cleans_buffering(self):
        from async_upnp_client.exceptions import UpnpActionError
        profile = FakeDmr()
        profile.async_set_transport_uri = AsyncMock(side_effect=UpnpActionError(
            error_code=716, error_desc="private-url-must-not-escape"))
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=AsyncMock(return_value=profile))
        with self.assertRaisesRegex(RuntimeError, r"DLNA load failed \(UPnP 716\)") as caught:
            await backend.load("http://private-source/", "audio/mpeg", True, 0)
        self.assertNotIn("private", str(caught.exception))
        self.assertEqual(backend.status().state, "IDLE")
        self.assertEqual(backend.status().idle_reason, "ERROR")
        profile.async_set_transport_uri.side_effect = None
        await backend.load("http://another-source/", "audio/mpeg", True, 0)
        await backend.shutdown()

    @unittest.skipUnless(importlib.util.find_spec("async_upnp_client"), "DLNA extra not installed")
    async def test_failed_remote_stop_still_cleans_local_session(self):
        from async_upnp_client.exceptions import UpnpActionError
        profile = FakeDmr()
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=AsyncMock(return_value=profile))
        await backend.load("http://source/", "audio/mpeg", True, 0)
        profile.async_stop = AsyncMock(side_effect=UpnpActionError(error_code=701))
        await backend.stop()
        self.assertEqual(backend.status().state, "IDLE")
        self.assertIsNone(backend._poll_task)

    async def test_failed_initial_update_does_not_cache_broken_profile(self):
        from unittest.mock import AsyncMock
        broken = FakeDmr()
        broken.async_update = AsyncMock(side_effect=OSError("unavailable"))
        good = FakeDmr()
        factory = AsyncMock(side_effect=[broken, good])
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=factory)
        with self.assertRaises(OSError):
            await backend._connect()
        self.assertIsNone(backend._profile)
        self.assertIs(await backend._connect(), good)
        await backend.shutdown()

    async def test_load_controls_and_metadata_use_upstream_profile(self):
        profile = FakeDmr()
        async def factory(url):
            self.assertEqual(url, "http://192.0.2.2/device.xml"); return profile
        backend = DlnaAudioBackend("http://192.0.2.2/device.xml", profile_factory=factory)
        await backend.set_metadata(MediaMetadata(title="Song", artist="Artist", artwork_url="http://cover"))
        await backend.load("http://media/song", "audio/mpeg", True, 12)
        await backend.pause(); await backend.seek(20); await backend.set_volume(0.4, True)
        await backend.shutdown()
        self.assertIn(("load", "http://media/song", "Song", "<DIDL/>"), profile.calls)
        self.assertIn(("seek", 12.0), profile.calls)
        self.assertIn(("seek", 20.0), profile.calls)
        self.assertIn(("volume", 0.4), profile.calls)
        metadata = next(call for call in profile.calls if call[0] == "metadata")
        self.assertEqual(metadata[3]["override_mime_type"], "audio/mpeg")
        self.assertEqual(metadata[3]["meta_data"]["artist"], "Artist")


if __name__ == "__main__": unittest.main()
