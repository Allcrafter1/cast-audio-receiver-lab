import json
import unittest
import uuid

from cast_audio_lab.backend import NullAudioBackend
from research.legacy_python_receiver.legacy_cast_receiver.protocol import (
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    HEARTBEAT_NAMESPACE,
    MEDIA_NAMESPACE,
    RECEIVER_NAMESPACE,
    YOUTUBE_APP_ID,
    YOUTUBE_MDX_NAMESPACE,
    YOUTUBE_MUSIC_APP_ID,
    CastProtocolEngine,
)
from research.legacy_python_receiver.legacy_cast_receiver.wire import CastMessage


def message(namespace, payload, destination="receiver-0"):
    return CastMessage(
        source_id="sender-0",
        destination_id=destination,
        namespace=namespace,
        payload_utf8=json.dumps(payload),
    )


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = NullAudioBackend()
        self.engine = CastProtocolEngine("Kitchen Lab", self.backend)

    async def test_ping_pong(self):
        responses = await self.engine.handle(
            message(HEARTBEAT_NAMESPACE, {"type": "PING"})
        )
        self.assertEqual("PONG", json.loads(responses[0].payload_utf8)["type"])

    async def test_launch_default_media_receiver(self):
        responses = await self.engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {
                    "type": "LAUNCH",
                    "appId": DEFAULT_MEDIA_RECEIVER_APP_ID,
                    "requestId": 7,
                },
            )
        )
        response = json.loads(responses[0].payload_utf8)
        self.assertEqual("RECEIVER_STATUS", response["type"])
        self.assertEqual(7, response["requestId"])
        app = response["status"]["applications"][0]
        self.assertEqual(DEFAULT_MEDIA_RECEIVER_APP_ID, app["appId"])
        self.assertTrue(app["transportId"].startswith("web-"))
        uuid.UUID(app["transportId"].removeprefix("web-"))

    async def test_rejects_unknown_app(self):
        responses = await self.engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {"type": "LAUNCH", "appId": "NOT_REAL", "requestId": 8},
            )
        )
        self.assertEqual(
            "LAUNCH_ERROR", json.loads(responses[0].payload_utf8)["type"]
        )

    async def test_launch_youtube_requires_screen_provider(self):
        responses = await self.engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {"type": "LAUNCH", "appId": YOUTUBE_APP_ID, "requestId": 11},
            )
        )
        self.assertEqual(
            "LAUNCH_ERROR", json.loads(responses[0].payload_utf8)["type"]
        )

    async def test_youtube_mdx_returns_lounge_screen_id(self):
        engine = CastProtocolEngine(
            "Kitchen Lab",
            self.backend,
            youtube_screen_id=lambda: "screen-123",
            youtube_device_id=lambda: "device-123",
        )
        launch = await engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {"type": "LAUNCH", "appId": YOUTUBE_APP_ID, "requestId": 12},
            )
        )
        app = json.loads(launch[0].payload_utf8)["status"]["applications"][0]
        self.assertEqual(app["displayName"], "YouTube")
        self.assertIn({"name": YOUTUBE_MDX_NAMESPACE}, app["namespaces"])

        response = await engine.handle(
            message(
                YOUTUBE_MDX_NAMESPACE,
                {"type": "getMdxSessionStatus", "requestId": 13},
                destination=engine.state.transport_id,
            )
        )
        payload = json.loads(response[0].payload_utf8)
        self.assertEqual(payload["type"], "mdxSessionStatus")
        self.assertEqual(payload["data"]["screenId"], "screen-123")
        self.assertEqual(payload["data"]["deviceId"], "device-123")
        self.assertEqual(payload["requestId"], 13)

    async def test_youtube_music_uses_observed_app_id_and_display_name(self):
        engine = CastProtocolEngine(
            "Kitchen Lab", self.backend, youtube_screen_id=lambda: "screen-123"
        )
        response = await engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {
                    "type": "LAUNCH",
                    "appId": YOUTUBE_MUSIC_APP_ID,
                    "requestId": 14,
                },
            )
        )
        app = json.loads(response[0].payload_utf8)["status"]["applications"][0]
        self.assertEqual(app["appId"], "2DB7CC49")
        self.assertEqual(app["displayName"], "YouTube Music")
        self.assertIn({"name": YOUTUBE_MDX_NAMESPACE}, app["namespaces"])

        mdx = await engine.handle(
            message(
                YOUTUBE_MDX_NAMESPACE,
                {"type": "getMdxSessionStatus", "requestId": 15},
                destination=engine.state.transport_id,
            )
        )
        self.assertEqual(
            json.loads(mdx[0].payload_utf8)["data"]["screenId"], "screen-123"
        )

    async def test_unsolicited_status_uses_backend_volume(self):
        await self.backend.set_volume(0.35, True)
        response = json.loads(
            self.engine.receiver_status_for("sender-7").payload_utf8
        )
        self.assertEqual(response["status"]["volume"]["level"], 0.35)
        self.assertTrue(response["status"]["volume"]["muted"])

    async def test_load_audio_and_pause(self):
        await self.engine.handle(
            message(
                RECEIVER_NAMESPACE,
                {"type": "LAUNCH", "appId": DEFAULT_MEDIA_RECEIVER_APP_ID},
            )
        )
        load = await self.engine.handle(
            message(
                MEDIA_NAMESPACE,
                {
                    "type": "LOAD",
                    "requestId": 9,
                    "autoplay": True,
                    "media": {
                        "contentId": "https://example.test/song.mp3",
                        "contentType": "audio/mpeg",
                    },
                },
                destination=self.engine.state.transport_id,
            )
        )
        load_status = json.loads(load[0].payload_utf8)
        self.assertEqual("PLAYING", load_status["status"][0]["playerState"])
        pause = await self.engine.handle(
            message(MEDIA_NAMESPACE, {"type": "PAUSE", "requestId": 10})
        )
        pause_status = json.loads(pause[0].payload_utf8)
        self.assertEqual("PAUSED", pause_status["status"][0]["playerState"])


if __name__ == "__main__":
    unittest.main()
