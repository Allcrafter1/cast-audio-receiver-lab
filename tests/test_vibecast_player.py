import asyncio
import unittest

from cast_audio_lab.backend import ControlRequest, NullAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer


class VibecastAudioPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = NullAudioBackend()
        self.player = VibecastAudioPlayer(
            "ws://example.invalid/player", "stable-id", "Kitchen", self.backend
        )
        self.sent = []

        async def capture(message):
            self.sent.append(message)

        self.player._send = capture

    def test_registration_has_audio_and_youtube_compatible_codecs(self):
        player = self.player.registration()["player"]
        self.assertEqual(player["protocolVersion"], 2)
        self.assertEqual(player["name"], "Kitchen")
        self.assertEqual(player["capabilities"]["audioCodecs"], ["opus", "aac"])
        self.assertIn("vp9", player["capabilities"]["videoCodecs"])
        self.assertIn("next", player["capabilities"]["controlRequests"])

    async def test_load_and_controls_are_reported(self):
        await self.player.handle_message(
            {
                "type": "load",
                "sessionId": "s1",
                "media": {
                    "streams": [{"url": "https://example.test/a.mpd", "contentType": "application/dash+xml"}],
                    "autoplay": True,
                    "startTime": 2,
                    "title": "Track",
                },
            }
        )
        self.assertEqual(self.backend.status().state, "PLAYING")
        self.assertEqual(self.player.session_id, "s1")
        self.assertEqual(self.sent[0]["playerState"], "BUFFERING")
        self.assertEqual(self.sent[-1]["playerState"], "PLAYING")

        await self.player.handle_message({"type": "pause", "sessionId": "s1"})
        self.assertEqual(self.backend.status().state, "PAUSED")

    async def test_actual_volume_is_in_status(self):
        await self.backend.set_volume(0.5, True)
        await self.player._send_backend_state("s1")
        self.assertEqual(self.sent[-1]["volume"], 0.5)
        self.assertTrue(self.sent[-1]["muted"])

    async def test_music_metadata_reaches_output_without_losing_album(self):
        await self.player._load("s1", {
            "streams": [{"url": "https://example.test/audio", "contentType": "audio/mpeg"}],
            "title": "Legacy title", "subtitle": "Legacy subtitle", "duration": 42,
            "metadata": {"metadataType": 3, "title": "Track", "artist": "Artist",
                "albumArtist": "Album artist", "albumName": "Album",
                "images": [{"url": "https://example.test/art"}]},
        })
        self.assertEqual(self.backend.metadata.title, "Track")
        self.assertEqual(self.backend.metadata.artist, "Artist")
        self.assertEqual(self.backend.metadata.album, "Album")
        self.assertEqual(self.backend.metadata.duration, 42)
        self.assertEqual(self.backend.metadata.artwork_url, "https://example.test/art")

    async def test_legacy_youtube_metadata_remains_compatible(self):
        await self.player._load("s1", {
            "streams": [{"url": "https://example.test/audio"}],
            "title": "YT title", "subtitle": "YT author",
            "images": [{"url": "https://example.test/yt"}],
        })
        self.assertEqual(self.backend.metadata.title, "YT title")
        self.assertEqual(self.backend.metadata.artist, "YT author")
        self.assertEqual(self.backend.metadata.album, "")
        self.assertEqual(self.backend.metadata.artwork_url, "https://example.test/yt")

    async def test_volume_can_be_restored_before_first_load(self):
        await self.player.handle_message(
            {"type": "volume", "sessionId": "new-session", "level": 0.26, "muted": False}
        )
        self.assertEqual(self.backend.status().volume, 0.26)
        self.assertEqual(self.sent[-1]["volume"], 0.26)
        self.assertIsNone(self.player.session_id)

    async def test_slow_artwork_does_not_block_load_or_survive_new_track_and_stop(self):
        self.player.artwork_endpoint = 'http://127.0.0.1:8788/api/artwork'
        self.player.artwork_public_url = 'http://receiver.test:8788'
        started, cancelled = [], []
        async def slow(session_id, source):
            started.append(source)
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(source)
        self.player._prepare_artwork = slow
        def media(cover):
            return {'streams': [{'url': 'https://example.test/audio'}],
                    'images': [{'url': cover}]}
        await asyncio.wait_for(self.player._load('s1', media('first')), 1)
        await asyncio.sleep(0)
        self.assertEqual(self.backend.status().state, 'PLAYING')
        await asyncio.wait_for(self.player._load('s1', media('second')), 1)
        await asyncio.sleep(0)
        self.assertEqual(cancelled, ['first'])
        await self.player.handle_message({'type': 'stop', 'sessionId': 's1'})
        self.assertEqual(started, ['first', 'second'])
        self.assertEqual(cancelled, started)
        self.assertIsNone(self.player._artwork_task)

    async def test_output_control_is_distinct_from_state_report(self):
        self.player.session_id = "s1"
        self.player._websocket = object()
        self.player._backend_control_requested(ControlRequest("seek", position=12.5))
        await asyncio.sleep(0)
        self.assertEqual(self.sent[-1], {
            "type": "controlRequest", "sessionId": "s1",
            "control": {"command": "seek", "position": 12.5},
        })


if __name__ == "__main__":
    unittest.main()
