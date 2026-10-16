# SPDX-License-Identifier: MPL-2.0
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from cast_audio_lab.backend import ControlRequest, NullAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer


class VibecastAudioPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_numeric_and_metadata_inputs_are_scoped_errors(self):
        self.backend.load = AsyncMock()
        self.backend.seek = AsyncMock()
        self.backend.set_volume = AsyncMock()
        for field, value in (("startTime", float("inf")), ("startTime", float("nan")),
                             ("images", {"url": "https://example.test/art"}),
                             ("mediaSessionId", "invalid")):
            await self.player.handle_message({"type": "load", "sessionId": "s1", "media": {
                "streams": [{"url": "https://example.test/audio"}], field: value}})
            self.assertEqual(self.sent[-1]["type"], "error")
        self.backend.load.assert_not_awaited()
        self.player.session_id = "s1"
        for command, field in (("seek", "position"), ("volume", "level")):
            for value in (float("inf"), float("nan"), True, 10 ** 400):
                await self.player.handle_message({"type": command, "sessionId": "s1", field: value})
                self.assertEqual(self.sent[-1]["type"], "error")
        self.backend.seek.assert_not_awaited()
        self.backend.set_volume.assert_not_awaited()

    async def test_media_identity_follows_status_errors_and_output_controls(self):
        self.player._websocket = object()
        for ident in (31, 32):
            await self.player.handle_message({"type": "load", "sessionId": "s1", "media": {
                "mediaSessionId": ident, "streams": [{"url": "https://example.test/audio"}]}})
            self.assertEqual(self.sent[-1].get("mediaSessionId"), ident)
        self.player._backend_control_requested(ControlRequest("seek", position=12))
        await asyncio.sleep(0)
        control = next(m for m in reversed(self.sent) if m["type"] == "controlRequest")
        self.assertEqual(control.get("mediaSessionId"), 32)
        await self.player.handle_message({"type": "stop", "sessionId": "s1"})
        self.assertIsNone(self.player.session_id)
        self.assertEqual(self.sent[-1].get("mediaSessionId"), 32,
                         "terminal Stop report must retain the ended media identity")
        self.backend.set_metadata = AsyncMock(side_effect=ValueError("https://private.test/?token=SECRET"))
        await self.player.handle_message({"type": "load", "sessionId": "s1", "media": {
            "mediaSessionId": 33, "streams": [{"url": "https://example.test/audio"}]}})
        self.assertEqual(self.sent[-1]["type"], "error")
        self.assertEqual(self.sent[-1].get("mediaSessionId"), 33)
        self.assertNotIn("SECRET", str(self.sent[-1]))

    async def test_stop_and_replacement_interrupt_load_without_socket_disconnect(self):
        import json
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                incoming = asyncio.Queue()
                entered, cancelled, stopped, loaded = (asyncio.Event() for _ in range(4))
                class Socket:
                    async def wait_closed(self):
                        await asyncio.Event().wait()
                    async def ping(self):
                        return asyncio.get_running_loop().create_future()
                    def __aiter__(self):
                        return self
                    async def __anext__(self):
                        return json.dumps(await incoming.get())
                async def load(url, *_):
                    if url.endswith("old"):
                        entered.set()
                        try:
                            await asyncio.Event().wait()
                        finally:
                            cancelled.set()
                    else:
                        self.assertTrue(stopped.is_set(), "replacement preceded old decoder cleanup")
                        loaded.set()
                async def stop():
                    stopped.set()
                self.backend.load, self.backend.stop = load, stop
                task = asyncio.create_task(self.player._serve_connection(Socket()))
                try:
                    await incoming.put({"type": "load", "sessionId": "s1", "media": {
                        "streams": [{"url": "https://example.test/old"}]}})
                    await asyncio.wait_for(entered.wait(), 1)
                    await incoming.put({"type": "load" if replacement else "stop", "sessionId": "s1",
                                        "media": {"streams": [{"url": "https://example.test/new"}]}})
                    await asyncio.wait_for(loaded.wait() if replacement else stopped.wait(), .5)
                    self.assertTrue(cancelled.is_set())
                    self.assertFalse(task.done(), "interrupting Load must not disconnect the output")
                finally:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

    async def test_title_fencing_preserves_output_wide_volume(self):
        self.player._websocket = object()
        await self.player._load("s1", {"streams": [{"url": "https://example.test/a"}]})
        self.player._backend_control_requested(ControlRequest("volume", level=.25))
        await self.player._load("s1", {"streams": [{"url": "https://example.test/b"}]})
        await asyncio.sleep(0)
        controls = [m for m in self.sent if m["type"] == "controlRequest"]
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0]["control"]["level"], .25)

    async def test_failed_reporter_cancels_waiting_receive_and_cleans_backend(self):
        entered, cancelled = asyncio.Event(), asyncio.Event()
        class Socket:
            send = AsyncMock()
            async def wait_closed(self):
                await asyncio.Event().wait()
            async def ping(self):
                return asyncio.get_running_loop().create_future()
            def __aiter__(self):
                return self
            async def __anext__(self):
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
        async def connect(*args, **kwargs):
            yield Socket()
        async def failed_reporter():
            await entered.wait()
            raise OSError("report transport failed")
        self.player._periodic_reports = failed_reporter
        self.backend.stop = AsyncMock()
        with patch("websockets.asyncio.client.connect", connect):
            await asyncio.wait_for(self.player.run(), 1)
        self.assertTrue(cancelled.is_set())
        self.backend.stop.assert_awaited_once()
        self.assertIsNone(self.player._websocket)

    async def test_queued_control_does_not_cross_title_change_in_same_session(self):
        self.player._websocket = object()
        await self.player._load("s1", {"streams": [{"url": "https://example.test/a"}]})
        self.player._backend_control_requested(ControlRequest("seek", position=90))
        await self.player._load("s1", {"streams": [{"url": "https://example.test/b"}]})
        await asyncio.sleep(0)
        self.assertFalse(any(m["type"] == "controlRequest" for m in self.sent))

    async def test_connection_close_cancels_blocked_load_and_stops_backend(self):
        import json
        from websockets.asyncio.server import serve
        entered, cancelled, stopped, closed = (asyncio.Event() for _ in range(4))
        async def blocked_load(*_):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        async def stop():
            stopped.set()
        self.backend.load = blocked_load
        self.backend.stop = stop
        async def serve_player(socket):
            await socket.recv()
            await socket.send(json.dumps({"type": "load", "sessionId": "s1", "media": {
                "streams": [{"url": "https://example.test/a"}],
            }}))
            await entered.wait()
            await socket.close()
            closed.set()
        async with serve(serve_player, "127.0.0.1", 0) as server:
            self.player.url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            task = asyncio.create_task(self.player.run())
            try:
                await asyncio.wait_for(closed.wait(), 2)
                await asyncio.wait_for(stopped.wait(), .5)
                self.assertTrue(cancelled.is_set())
                self.assertFalse(self.player._preparing_load)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_old_terminal_state_is_not_reported_during_new_load_setup(self):
        self.backend._status.state = "IDLE"
        self.backend._status.idle_reason = "FINISHED"
        self.player._websocket = object()
        entered, release = asyncio.Event(), asyncio.Event()
        async def metadata(_):
            entered.set()
            await release.wait()
        self.backend.set_metadata = metadata
        task = asyncio.create_task(self.player._load("s1", {
            "streams": [{"url": "https://example.test/new"}], "startTime": 42,
        }))
        await entered.wait()
        await self.player._send_backend_state("s1")
        self.player._backend_status_changed(self.backend.status())
        await asyncio.sleep(0)
        self.assertTrue(self.sent)
        self.assertTrue(all(m.get("playerState") == "BUFFERING" for m in self.sent))
        self.assertTrue(all(m.get("currentTime") == 42 for m in self.sent))
        release.set()
        await task
        self.assertEqual(self.sent[-1]["playerState"], "PLAYING")

    async def test_queued_output_control_does_not_cross_reconnect_or_session(self):
        self.player.session_id = "s1"
        self.player._websocket = object()
        self.player._backend_control_requested(ControlRequest("pause"))
        self.player._websocket = object()
        await asyncio.sleep(0)
        self.assertEqual(self.sent, [])
        self.player._backend_control_requested(ControlRequest("stop"))
        self.player.session_id = "s2"
        await asyncio.sleep(0)
        self.assertEqual(self.sent, [])

    async def test_metadata_failure_stops_old_audio_and_does_not_relabel_old_state(self):
        await self.backend.load("https://example.test/old", "audio/mpeg", True, 10)
        self.backend.set_metadata = AsyncMock(side_effect=OSError("metadata output failed"))
        await self.player.handle_message({"type": "load", "sessionId": "s1", "media": {
            "streams": [{"url": "https://example.test/new"}], "startTime": 42,
        }})
        self.assertIsNone(self.player.session_id)
        self.assertEqual(self.backend.status().state, "IDLE")
        self.assertFalse(self.player._preparing_load)
        self.assertEqual(self.sent[-1]["type"], "error")

    async def test_stop_failure_does_not_prevent_bridge_reconnect(self):
        class Socket:
            send = AsyncMock()
            async def ping(self):
                return asyncio.get_running_loop().create_future()
            async def wait_closed(self):
                await asyncio.Event().wait()
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration
        connections = []
        async def connect(*args, **kwargs):
            for _ in range(2):
                connections.append(Socket())
                yield connections[-1]
        self.backend.stop = AsyncMock(side_effect=OSError("decoder failed"))
        with patch("websockets.asyncio.client.connect", connect):
            await self.player.run()
        self.assertEqual(len(connections), 2)
        self.assertEqual(self.backend.stop.await_count, 2)
        self.assertIsNone(self.player._websocket)
        self.assertIsNone(self.player.session_id)

    async def test_health_requires_pong_and_stops_on_disconnect(self):
        pong = asyncio.get_running_loop().create_future()
        socket = AsyncMock()
        socket.ping.return_value = pong
        with patch("cast_audio_lab.vibecast_player.HEALTH_LOGGER") as health:
            task = asyncio.create_task(self.player._health_reports(socket))
            await asyncio.sleep(0)
            health.info.assert_not_called()
            pong.set_result(None)
            await asyncio.sleep(0)
            health.info.assert_called_once_with("responsive")
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        socket.ping.side_effect = OSError("connection failed")
        with patch("cast_audio_lab.vibecast_player.HEALTH_LOGGER") as health:
            await self.player._health_reports(socket)
            health.info.assert_called_once_with("disconnected")

    async def test_queued_notification_reads_post_seek_position(self):
        self.player.session_id = "s1"
        self.player._websocket = object()
        await self.backend.load("https://example.test/a", "audio/mpeg", False, 12)
        self.player._backend_status_changed(self.backend.status())
        await self.backend.seek(80)
        await asyncio.sleep(0)
        self.assertTrue(self.sent)
        self.assertTrue(all(m["currentTime"] == 80 for m in self.sent))

    async def test_queued_notification_does_not_cross_reconnect(self):
        self.player.session_id = "s1"
        self.player._websocket = object()
        self.player._backend_status_changed(self.backend.status())
        self.player._websocket = object()
        await asyncio.sleep(0)
        self.assertEqual(self.sent, [])

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
        self.assertFalse(self.player.registration()["player"]["capabilities"]["localAudioCache"])
        player = self.player.registration()["player"]
        self.assertEqual(player["protocolVersion"], 2)
        self.assertEqual(player["name"], "Kitchen")
        self.assertEqual(player["capabilities"]["audioCodecs"], ["opus", "aac"])
        self.assertIn("vp9", player["capabilities"]["videoCodecs"])
        self.assertIn("next", player["capabilities"]["controlRequests"])

    def test_local_cache_is_opt_in_for_receiver_side_decoders(self):
        from cast_audio_lab.mpv_backend import MpvAudioBackend
        from cast_audio_lab.airplay import AirPlayAudioBackend
        self.assertTrue(AirPlayAudioBackend.local_audio_cache)
        player = VibecastAudioPlayer("ws://example.invalid/player", "id", "local", MpvAudioBackend())
        self.assertTrue(player.registration()["player"]["capabilities"]["localAudioCache"])

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
