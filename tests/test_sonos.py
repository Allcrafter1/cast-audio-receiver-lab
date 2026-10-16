# SPDX-License-Identifier: MPL-2.0
import unittest
import asyncio
import threading

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

