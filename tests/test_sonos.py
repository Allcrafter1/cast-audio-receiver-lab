import unittest

from cast_audio_lab.backend import MediaMetadata
from cast_audio_lab.sonos import SonosAudioBackend, _seconds, _timestamp


class FakeSonos:
    def __init__(self):
        self.calls, self.volume, self.mute = [], 100, False
    def play_uri(self, url, **kwargs): self.calls.append(("load", url, kwargs))
    def play(self): self.calls.append(("play",))
    def pause(self): self.calls.append(("pause",))
    def stop(self): self.calls.append(("stop",))
    def seek(self, position): self.calls.append(("seek", position))
    def get_current_transport_info(self): return {"current_transport_state": "PLAYING"}
    def get_current_track_info(self): return {"position": "0:00:01", "duration": "0:03:00"}


class SonosBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_load_controls_and_volume_use_soco_device(self):
        device = FakeSonos()
        backend = SonosAudioBackend("192.0.2.3", device_factory=lambda host: device)
        await backend.set_metadata(MediaMetadata(title="Song"))
        await backend.load("http://media/song", "audio/mpeg", True, 12)
        await backend.pause(); await backend.seek(20); await backend.set_volume(0.4, True)
        await backend.shutdown()
        self.assertIn(("load", "http://media/song", {"title": "Song", "start": True}), device.calls)
        self.assertIn(("seek", "0:00:12"), device.calls)
        self.assertIn(("seek", "0:00:20"), device.calls)
        self.assertEqual(device.volume, 40)
        self.assertTrue(device.mute)

    def test_time_conversion_is_bounded(self):
        self.assertEqual(_timestamp(3661.9), "1:01:01")
        self.assertEqual(_seconds("1:01:01"), 3661.0)
        self.assertIsNone(_seconds("unknown"))


if __name__ == "__main__": unittest.main()

