import unittest

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

