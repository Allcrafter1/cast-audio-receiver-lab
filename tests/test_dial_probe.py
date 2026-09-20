import unittest

from tools.probe_dial import (
    DIAL_ST,
    _parse_youtube_status,
    discovery_request,
    parse_ssdp,
)


class DialProbeTests(unittest.TestCase):
    def test_discovery_request(self):
        request = discovery_request()
        self.assertIn(b"M-SEARCH * HTTP/1.1\r\n", request)
        self.assertIn(f"ST: {DIAL_ST}\r\n".encode(), request)
        self.assertTrue(request.endswith(b"\r\n\r\n"))

    def test_parse_response_case_insensitively(self):
        status, headers = parse_ssdp(
            b"HTTP/1.1 200 OK\r\n"
            b"LOCATION: http://192.0.2.1:1234/device.xml\r\n"
            b"ST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n"
        )
        self.assertEqual("HTTP/1.1 200 OK", status)
        self.assertEqual(
            "http://192.0.2.1:1234/device.xml", headers["location"]
        )

    def test_youtube_status_redacts_screen_id(self):
        body = b"""<service xmlns="urn:dial-multiscreen-org:schemas:dial">
          <options allowStop="true"/>
          <state>running</state>
          <link rel="run" href="run"/>
          <additionalData><screenId>secret-screen</screenId><theme>cl</theme></additionalData>
        </service>"""
        status = _parse_youtube_status(body)
        self.assertEqual("running", status["state"])
        self.assertEqual(["screenId", "theme"], status["additional_data_keys"])
        self.assertEqual(len("secret-screen"), status["screen_id_length"])
        self.assertNotIn("secret-screen", str(status))


if __name__ == "__main__":
    unittest.main()
