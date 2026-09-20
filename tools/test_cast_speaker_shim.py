import json
import unittest

from cast_speaker_shim import (
    ANTI_XSSI_PREFIX,
    Identity,
    dial_ssdp_response,
    derive_base_station,
    normalize_device_id,
    parse_dial_msearch,
    rewrite_eureka_payload,
)


IDENTITY = Identity(
    friendly_name="Lab Speaker",
    instance_name="Lab Speaker",
    model_name="Audio Lab",
    device_id="0123456789abcdef0123456789abcdef",
    advertise_host="lab-speaker.local",
    advertise_address="192.0.2.10",
    base_station="021122334455",
)


class IdentityTests(unittest.TestCase):
    def test_normalize_device_id(self):
        self.assertEqual(
            normalize_device_id("01234567-89AB-CDEF-0123-456789ABCDEF"),
            IDENTITY.device_id,
        )

    def test_rejects_invalid_device_id(self):
        with self.assertRaises(ValueError):
            normalize_device_id("not-an-id")

    def test_base_station_is_locally_administered_unicast(self):
        value = derive_base_station("ffffffffffffffffffffffffffffffff")
        first = int(value[:2], 16)
        self.assertEqual(first & 0x02, 0x02)
        self.assertEqual(first & 0x01, 0)


class EurekaRewriteTests(unittest.TestCase):
    def test_rewrites_airreceiver_response(self):
        source = {
            "name": "TV",
            "device_info": {
                "capabilities": {
                    "display_supported": True,
                    "multizone_supported": False,
                },
                "model_name": "AirReceiver",
                "ssdp_udn": "old-id",
                "public_key": "unchanged",
            },
            "net": {"ip_address": "192.0.2.20", "online": True},
        }
        result = json.loads(rewrite_eureka_payload(json.dumps(source).encode(), IDENTITY))
        self.assertEqual(result["name"], "Lab Speaker")
        self.assertFalse(result["device_info"]["capabilities"]["display_supported"])
        self.assertTrue(result["device_info"]["capabilities"]["multizone_supported"])
        self.assertEqual(result["device_info"]["public_key"], "unchanged")
        self.assertEqual(result["net"]["ip_address"], "192.0.2.10")

    def test_preserves_xssi_prefix_and_wrapped_shape(self):
        source = {"data": {"name": "TV", "device_info": {"capabilities": {}}}}
        body = ANTI_XSSI_PREFIX + json.dumps(source).encode()
        result = rewrite_eureka_payload(body, IDENTITY)
        self.assertTrue(result.startswith(ANTI_XSSI_PREFIX))
        decoded = json.loads(result[len(ANTI_XSSI_PREFIX) :])
        self.assertEqual(decoded["data"]["name"], "Lab Speaker")

    def test_leaves_non_json_unchanged(self):
        self.assertEqual(rewrite_eureka_payload(b"not json", IDENTITY), b"not json")

    def test_optional_provisioning_overrides(self):
        identity = Identity(
            **{
                **IDENTITY.__dict__,
                "setup_state": 60,
                "wifi_ssid": "Lab WLAN",
            }
        )
        source = {"setup": {"setup_state": 52}, "wifi": {"ssid": "UNKNOWN"}}
        result = json.loads(rewrite_eureka_payload(json.dumps(source).encode(), identity))
        self.assertEqual(result["setup"]["setup_state"], 60)
        self.assertEqual(result["wifi"]["ssid"], "Lab WLAN")


class DialSsdpTests(unittest.TestCase):
    def test_parses_dial_search(self):
        request = (
            b"M-SEARCH * HTTP/1.1\r\n"
            b'MAN: "ssdp:discover"\r\n'
            b"ST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n"
        )
        self.assertEqual(
            parse_dial_msearch(request),
            "urn:dial-multiscreen-org:service:dial:1",
        )

    def test_response_uses_advertised_endpoint_and_uuid(self):
        response = dial_ssdp_response(
            IDENTITY, 8008, "urn:dial-multiscreen-org:service:dial:1"
        ).decode("ascii")
        self.assertIn("LOCATION: http://192.0.2.10:8008/ssdp/device-desc.xml", response)
        self.assertIn("uuid:01234567-89ab-cdef-0123-456789abcdef", response)


if __name__ == "__main__":
    unittest.main()
