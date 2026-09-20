import importlib.util
import unittest

from cast_audio_lab.dlna_discovery import description_location, parse_renderer


class DiscoveryTests(unittest.TestCase):
    def test_only_same_local_responder_can_supply_location(self):
        headers = {"location": "http://192.0.2.2:123/device.xml", "_host": "192.0.2.2"}
        self.assertEqual(description_location(headers), headers["location"])
        for url in ["http://127.0.0.1/", "http://192.0.2.3/", "http://8.8.8.8/",
                    "file:///tmp/device", "http://user:pass@192.0.2.2/device.xml"]:
            self.assertIsNone(description_location(dict(headers, location=url)))

    @unittest.skipUnless(importlib.util.find_spec("defusedxml"), "DLNA extra not installed")
    def test_renderer_identity_and_name_are_parsed(self):
        xml = b'''<root xmlns="urn:schemas-upnp-org:device-1-0"><device>
        <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
        <friendlyName>Test &amp; TV</friendlyName><UDN>uuid:test-renderer</UDN>
        </device></root>'''
        item = parse_renderer(xml, "http://192.0.2.2:123/device.xml")
        self.assertEqual(item["name"], "Test & TV")
        self.assertEqual(item["target"]["device_id"], "uuid:test-renderer")
        self.assertIsNone(parse_renderer(xml.replace(b"MediaRenderer", b"MediaServer"),
                                         "http://192.0.2.2:123/device.xml"))
