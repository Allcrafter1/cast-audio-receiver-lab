import struct
import unittest

from research.legacy_python_receiver.legacy_cast_receiver.mdns import (
    SERVICE_NAME,
    build_announcement,
    encode_dns_name,
)


class MdnsTests(unittest.TestCase):
    def test_audio_only_announcement(self):
        packet = build_announcement(
            "Kitchen Lab",
            "cast-lab",
            "192.0.2.50",
            8009,
            "00000000-0000-0000-0000-000000000001",
        )
        _, flags, questions, answers, authority, additional = struct.unpack(
            ">HHHHHH", packet[:12]
        )
        self.assertEqual(0x8400, flags)
        self.assertEqual((0, 4, 0, 0), (questions, answers, authority, additional))
        self.assertIn(encode_dns_name(SERVICE_NAME), packet)
        self.assertIn(b"\x04ca=4", packet)
        self.assertIn(b"\xc0\x00\x02\x32", packet)


if __name__ == "__main__":
    unittest.main()
