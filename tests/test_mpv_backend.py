import unittest
from unittest.mock import AsyncMock
from cast_audio_lab.mpv_backend import MpvAudioBackend


class MpvEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_load_releases_feedback_gates(self):
        b = MpvAudioBackend()
        b._loading = True
        b._seeking = True
        await b._event({"event": "end-file", "reason": "error", "file_error": "loading failed"})
        self.assertFalse(b._loading)
        self.assertFalse(b._seeking)
        self.assertEqual(b.status().idle_reason, "ERROR")

    async def test_old_position_during_load_is_ignored(self):
        b = MpvAudioBackend()
        b._loading = True
        b._status.state = "BUFFERING"
        await b._event({"event": "property-change", "name": "time-pos", "data": 213})
        self.assertEqual(b.status().current_time, 0)

    async def test_pause_survives_cache_feedback(self):
        b = MpvAudioBackend()
        b._command = AsyncMock()
        await b.pause()
        await b._event({"event": "property-change", "name": "paused-for-cache", "data": False})
        self.assertEqual(b.status().state, "PAUSED")
        self.assertFalse(b._autoplay)

    async def test_rejected_seek_reopens_paused_media(self):
        b = MpvAudioBackend()
        b._status.url = "https://example.invalid/audio"
        b._status.content_type = "audio/webm"
        b._status.state = "PAUSED"
        b._command = AsyncMock(side_effect=ValueError("not seekable"))
        b.load = AsyncMock()
        await b.seek(42)
        b.load.assert_awaited_once_with(b._status.url, "audio/webm", False, 42)

    async def test_eof_and_failure_differ(self):
        b = MpvAudioBackend()
        await b._event({"event": "end-file", "reason": "error"})
        self.assertEqual(b.status().idle_reason, "ERROR")
        await b._event({"event": "end-file", "reason": "eof"})
        self.assertEqual(b.status().idle_reason, "FINISHED")

    async def test_replace_stop_does_not_finish_new_load(self):
        b = MpvAudioBackend()
        b._status.state = "BUFFERING"
        await b._event({"event": "end-file", "reason": "stop"})
        self.assertEqual(b.status().state, "BUFFERING")
        self.assertIsNone(b.status().idle_reason)

    async def test_feedback_uses_decoder_position_and_volume(self):
        b = MpvAudioBackend()
        for name, data in [("time-pos", 63.25), ("volume", 42), ("mute", True)]:
            await b._event({"event": "property-change", "name": name, "data": data})
        s = b.status()
        self.assertEqual(s.current_time, 63.25)
        self.assertEqual(s.volume, .42)
        self.assertTrue(s.muted)
