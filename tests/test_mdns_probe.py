import unittest

from research.legacy_python_receiver.legacy_cast_receiver.mdns import build_announcement
from tools.probe_mdns import parse_packet


class MdnsProbeTests(unittest.TestCase):
    def test_parses_cast_announcement_and_sanitizes_ids(self):
        packet = build_announcement(
            "Kitchen Lab",
            "cast-lab",
            "192.0.2.50",
            8009,
            "00000000-0000-0000-0000-000000000001",
        )
        records = parse_packet(packet)
        txt = next(record["txt"] for record in records if "txt" in record)
        self.assertEqual("4", txt["ca"])
        self.assertNotIn("id", txt)
        self.assertNotIn("cd", txt)
        address = next(
            record["address"] for record in records if "address" in record
        )
        self.assertEqual("192.0.2.50", address)


if __name__ == "__main__":
    unittest.main()
