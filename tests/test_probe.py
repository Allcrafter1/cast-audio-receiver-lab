import unittest

from research.legacy_python_receiver.legacy_cast_receiver.wire import iter_protobuf_fields
from tools.probe_auth import build_challenge


class ProbeTests(unittest.TestCase):
    def test_challenge_contains_requested_algorithms_and_nonce(self):
        nonce = bytes(range(16))
        outer = list(iter_protobuf_fields(build_challenge(nonce)))
        self.assertEqual(1, outer[0][0])
        challenge = outer[0][2]
        self.assertIsInstance(challenge, bytes)
        fields = {number: value for number, _, value in iter_protobuf_fields(challenge)}
        self.assertEqual(1, fields[1])
        self.assertEqual(nonce, fields[2])
        self.assertEqual(1, fields[3])


if __name__ == "__main__":
    unittest.main()
