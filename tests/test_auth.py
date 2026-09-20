import unittest

from research.legacy_python_receiver.legacy_cast_receiver.auth import describe_challenge
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    encode_length_delimited_field,
    encode_varint_field,
)


class AuthTests(unittest.TestCase):
    def test_challenge_summary_does_not_expose_nonce(self):
        nonce = bytes(range(16))
        challenge = b"".join(
            (
                encode_varint_field(1, 1),
                encode_length_delimited_field(2, nonce),
                encode_varint_field(3, 1),
            )
        )
        message = encode_length_delimited_field(1, challenge)
        summary = describe_challenge(message)
        self.assertEqual(
            {
                "valid": True,
                "signature_algorithm": "PKCS1v15",
                "hash_algorithm": "SHA256",
                "sender_nonce_present": True,
                "sender_nonce_bytes": 16,
            },
            summary,
        )
        self.assertNotIn(nonce.hex(), str(summary))


if __name__ == "__main__":
    unittest.main()
