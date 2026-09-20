import asyncio
import json
import unittest

from cast_audio_lab.backend import NullAudioBackend
from research.legacy_python_receiver.legacy_cast_receiver.lounge import (
    AudioSource,
    LoungeClient,
    LoungeCommand,
    LoungeCommandEngine,
    LoungeCredentials,
    LoungeError,
    LoungeFrameDecoder,
    LoungeOutgoing,
    parse_command_frame,
)


class FakeResolver:
    def __init__(self) -> None:
        self.video_ids: list[str] = []

    async def resolve(
        self, video_id: str, credential_transfer_token: str | None = None
    ) -> AudioSource:
        self.video_ids.append(video_id)
        return AudioSource(
            f"https://media.example/{video_id}.opus",
            "audio/ogg",
            123.0,
            "Test",
        )


class LoungeFramingTests(unittest.TestCase):
    def test_incremental_utf8_frames(self) -> None:
        payload = json.dumps(
            [[7, ["remoteConnected", {"name": "Küche"}]]],
            ensure_ascii=False,
        ).encode()
        wire = str(len(payload)).encode() + b"\n" + payload
        decoder = LoungeFrameDecoder()
        self.assertEqual(decoder.feed(wire[:8]), [])
        self.assertEqual(decoder.feed(wire[8:]), [payload])
        self.assertEqual(decoder.buffered_bytes, 0)

    def test_rejects_invalid_length(self) -> None:
        with self.assertRaises(LoungeError):
            LoungeFrameDecoder().feed(b"nope\n{}")

    def test_parse_commands_ignores_malformed_entries(self) -> None:
        commands = parse_command_frame(
            b'[[0,["c","session"]],["bad"],[1,["play",{}]]]'
        )
        self.assertEqual(
            commands,
            [
                LoungeCommand(0, "c", "session"),
                LoungeCommand(1, "play", {}),
            ],
        )


class LoungeEngineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.backend = NullAudioBackend()
        self.resolver = FakeResolver()
        self.engine = LoungeCommandEngine(self.backend, self.resolver)

    async def test_set_playlist_autoplays_selected_audio(self) -> None:
        messages = await self.engine.handle(
            LoungeCommand(
                4,
                "setPlaylist",
                {
                    "videoIds": "first,second",
                    "videoId": "second",
                    "currentIndex": "1",
                    "currentTime": "12.5",
                },
            )
        )
        self.assertEqual(self.resolver.video_ids, ["second"])
        status = self.backend.status()
        self.assertEqual(status.state, "PLAYING")
        self.assertEqual(status.url, "https://media.example/second.opus")
        self.assertGreaterEqual(status.current_time, 12.5)
        now_playing = next(item for item in messages if item.name == "nowPlaying")
        self.assertEqual(now_playing.args["videoId"], "second")
        self.assertEqual(now_playing.args["state"], 1)

    async def test_explicit_play_after_no_autoplay(self) -> None:
        engine = LoungeCommandEngine(
            self.backend, self.resolver, autoplay_on_set_playlist=False
        )
        await engine.handle(
            LoungeCommand(1, "setPlaylist", {"videoIds": "one", "videoId": "one"})
        )
        self.assertEqual(self.backend.status().state, "PAUSED")
        await engine.handle(LoungeCommand(2, "play", {}))
        self.assertEqual(self.backend.status().state, "PLAYING")

    async def test_session_commands_are_not_suppressed_as_duplicates(self) -> None:
        await self.engine.handle(LoungeCommand(5, "c", "sid"))
        await self.engine.handle(LoungeCommand(5, "S", "gsid"))
        self.assertEqual(self.engine.session_id, "sid")
        self.assertEqual(self.engine.gsession_id, "gsid")

    async def test_next_resolves_next_queue_item(self) -> None:
        await self.engine.handle(
            LoungeCommand(
                1,
                "setPlaylist",
                {"videoIds": "one,two", "videoId": "one", "currentIndex": "0"},
            )
        )
        await self.engine.handle(LoungeCommand(2, "next", {}))
        self.assertEqual(self.resolver.video_ids, ["one", "two"])
        self.assertEqual(self.engine.queue.current_video_id, "two")


class FakeLoungeClient(LoungeClient):
    def __init__(self, engine, responses):
        super().__init__("Kitchen", "device-1", engine)
        self.responses = list(responses)
        self.requests = []

    async def _request(self, method, url, form=None):
        self.requests.append((method, url, form))
        return self.responses.pop(0) if self.responses else b""


class LoungeClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.backend = NullAudioBackend()
        self.engine = LoungeCommandEngine(self.backend, FakeResolver())

    async def test_bootstrap_parses_live_style_bind_frame(self) -> None:
        commands = b'[[0,["c","sid-1"]],[1,["S","gsid-1"]]]'
        bind = str(len(commands)).encode() + b"\n" + commands
        client = FakeLoungeClient(
            self.engine,
            [
                b"screen-1",
                b'{"screens":[{"loungeToken":"token-1"}]}',
                bind,
            ],
        )
        credentials = await client.bootstrap()
        self.assertEqual(credentials, LoungeCredentials("screen-1", "token-1"))
        self.assertEqual(self.engine.session_id, "sid-1")
        self.assertEqual(self.engine.gsession_id, "gsid-1")
        self.assertEqual(client.requests[2][2], {"count": 0})

    async def test_outgoing_form_uses_expected_lounge_keys(self) -> None:
        client = FakeLoungeClient(self.engine, [b""])
        client.credentials = LoungeCredentials("screen-1", "token-1")
        self.engine.session_id = "sid-1"
        self.engine.gsession_id = "gsid-1"
        await client.send(
            [
                LoungeOutgoing(
                    "onStateChange",
                    {"state": 1, "hasNext": True},
                    command_id=7,
                )
            ]
        )
        method, url, form = client.requests[0]
        self.assertEqual(method, "POST")
        self.assertIn("SID=sid-1", url)
        self.assertIn("gsessionid=gsid-1", url)
        self.assertIn("AID=7", url)
        self.assertIn(("count", 1), form)
        self.assertIn(("ofs", 0), form)
        self.assertIn(("req0__sc", "onStateChange"), form)
        self.assertIn(("req0_state", "1"), form)
        self.assertIn(("req0_hasNext", "true"), form)

    async def test_dial_pairing_registration_uses_permanent_access(self) -> None:
        client = FakeLoungeClient(self.engine, [b""])
        client.credentials = LoungeCredentials("screen-1", "token-1")

        await client.register_pairing_code("pair-123")

        method, url, form = client.requests[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/pairing/register_pairing_code"))
        self.assertEqual(
            form,
            {
                "access_type": "permanent",
                "app": "lb-v4",
                "pairing_code": "pair-123",
                "screen_id": "screen-1",
                "screen_name": "Kitchen",
                "device_id": "device-1",
            },
        )


if __name__ == "__main__":
    unittest.main()
