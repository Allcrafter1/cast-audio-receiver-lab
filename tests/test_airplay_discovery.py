import unittest

from cast_audio_lab.airplay_discovery import (
    AIRPLAY_SERVICE,
    RAOP_SERVICE,
    AirPlayService,
    merge_services,
    service_device_id,
)


class AirPlayDiscoveryTests(unittest.TestCase):
    def test_extracts_raop_mac(self):
        self.assertEqual(
            service_device_id(
                RAOP_SERVICE,
                "AABBCCDDEEFF@Yamaha._raop._tcp.local.",
                {},
            ),
            "AA:BB:CC:DD:EE:FF",
        )

    def test_merges_raop_and_airplay_by_device_id(self):
        raop = AirPlayService(
            RAOP_SERVICE,
            "AABBCCDDEEFF@Receiver._raop._tcp.local.",
            "receiver.local",
            "192.0.2.10",
            5000,
            {"am": "RX-V6A", "cn": "0,1"},
        )
        airplay = AirPlayService(
            AIRPLAY_SERVICE,
            "Receiver._airplay._tcp.local.",
            "receiver.local",
            "192.0.2.10",
            7000,
            {"deviceid": "AA:BB:CC:DD:EE:FF", "name": "Living Room"},
        )
        devices = merge_services([raop, airplay])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "Living Room")
        target = devices[0].to_target()
        self.assertEqual(target.protocol, "auto")
        self.assertEqual(target.port, 7000)

    def test_keeps_name_only_receiver_selectable(self):
        value = service_device_id(
            AIRPLAY_SERVICE,
            "Odd Receiver._airplay._tcp.local.",
            {},
        )
        self.assertTrue(value.startswith("mdns:"))

    def test_marks_airconnect_output_as_bridge_generated(self):
        service = AirPlayService(
            RAOP_SERVICE,
            "CCCC69A6DD3F@Living Room+._raop._tcp.local.",
            "instance-aircast.local",
            "192.0.2.50",
            5000,
            {"am": "aircast"},
        )
        device = merge_services([service])[0]
        self.assertTrue(device.bridge_generated)


if __name__ == "__main__":
    unittest.main()
