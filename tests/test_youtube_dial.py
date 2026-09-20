import unittest
import xml.etree.ElementTree as ET

from research.legacy_python_receiver.legacy_cast_receiver.lounge import (
    LoungeCredentials,
)
from research.legacy_python_receiver.legacy_cast_receiver.youtube_dial import (
    DIAL_SERVICE,
    DialIdentity,
    YouTubeDialServer,
    device_description,
    parse_msearch,
    ssdp_response,
    youtube_status,
)


class YouTubeDialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = DialIdentity(
            "Küche & Musik", "test-device-id", "192.0.2.10", 3600
        )

    def test_parses_dial_search_case_insensitively(self) -> None:
        request = (
            "M-SEARCH * HTTP/1.1\r\n"
            'Man: "ssdp:discover"\r\n'
            f"St: {DIAL_SERVICE}\r\n\r\n"
        ).encode()
        self.assertEqual(parse_msearch(request), DIAL_SERVICE)

    def test_ignores_unrelated_search(self) -> None:
        request = (
            "M-SEARCH * HTTP/1.1\r\n"
            'MAN: "ssdp:discover"\r\n'
            "ST: urn:example\r\n\r\n"
        ).encode()
        self.assertIsNone(parse_msearch(request))

    def test_ssdp_points_to_description(self) -> None:
        response = ssdp_response(self.identity, DIAL_SERVICE).decode()
        self.assertIn("LOCATION: http://192.0.2.10:3600/device-desc.xml", response)
        self.assertIn("USN: uuid:test-device-id", response)

    def test_device_description_is_valid_xml(self) -> None:
        root = ET.fromstring(device_description(self.identity))
        values = [element.text for element in root.iter()]
        self.assertIn("Küche & Musik", values)

    def test_youtube_status_exposes_lounge_identity(self) -> None:
        root = ET.fromstring(
            youtube_status(
                self.identity,
                LoungeCredentials("s" * 64, "lounge-token"),
                running=True,
            )
        )
        values = {
            element.tag.rsplit("}", 1)[-1]: element.text
            for element in root.iter()
        }
        self.assertEqual(values["state"], "running")
        self.assertEqual(values["screenId"], "s" * 64)
        self.assertEqual(values["loungeToken"], "lounge-token")
        self.assertEqual(values["testYWRkaXR"], "c0ef1ca")
        self.assertEqual(values["brand"], "OpenSource")
        self.assertEqual(values["model"], "AudioReceiver")
        self.assertEqual(root.attrib["dialVer"], "2.1")

    def test_youtube_status_is_stopped_before_launch(self) -> None:
        root = ET.fromstring(
            youtube_status(
                self.identity,
                LoungeCredentials("s" * 64, "lounge-token"),
                running=False,
            )
        )
        values = {
            element.tag.rsplit("}", 1)[-1]: element.text
            for element in root.iter()
        }
        self.assertEqual(values["state"], "stopped")
        self.assertNotIn("screenId", values)
        self.assertNotIn("loungeToken", values)
        self.assertFalse(
            any(
                element.tag.rsplit("}", 1)[-1] == "link"
                for element in root.iter()
            )
        )


class YouTubeDialLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pairing_codes: list[str] = []

        async def register_pairing_code(code: str) -> None:
            self.pairing_codes.append(code)

        self.server = YouTubeDialServer(
            DialIdentity(
                "Audio Lab", "test-device-id", "192.0.2.10", 3600
            ),
            lambda: LoungeCredentials("s" * 64, "lounge-token"),
            register_pairing_code,
        )

    async def _state(self) -> tuple[str | None, bool]:
        code, _, body = await self.server._route(
            "GET", "/apps/YouTube", b""
        )
        self.assertEqual(code, 200)
        root = ET.fromstring(body)
        elements = {
            element.tag.rsplit("}", 1)[-1]: element for element in root.iter()
        }
        return (
            elements["state"].text,
            "link" in elements,
        )

    async def test_launch_and_stop_change_reported_state(self) -> None:
        self.assertEqual(await self._state(), ("stopped", False))

        code, headers, _ = await self.server._route(
            "POST",
            "/apps/YouTube",
            b"pairingCode=pair-123&theme=cl",
        )
        self.assertEqual(code, 201)
        self.assertEqual(
            headers["Location"],
            "http://192.0.2.10:3600/apps/YouTube/run",
        )
        self.assertEqual(self.pairing_codes, ["pair-123"])
        self.assertEqual(await self._state(), ("running", True))

        code, _, _ = await self.server._route(
            "DELETE", "/apps/YouTube/run", b""
        )
        self.assertEqual(code, 200)
        self.assertEqual(await self._state(), ("stopped", False))


if __name__ == "__main__":
    unittest.main()
