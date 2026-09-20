import unittest
from unittest.mock import patch

from research.legacy_python_receiver.legacy_cast_receiver.auth import (
    DEVICE_AUTH_NAMESPACE,
)
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    PayloadType,
    encode_length_delimited_field,
)
from tools.probe_auth import analyze_response


class AuthProbeTests(unittest.TestCase):
    def test_missing_returned_nonce_does_not_count_as_challenge_binding(self):
        response = encode_length_delimited_field(1, b"signature")
        message = CastMessage(
            source_id="receiver-0",
            destination_id="sender-0",
            namespace=DEVICE_AUTH_NAMESPACE,
            payload_type=PayloadType.BINARY,
            payload_binary=encode_length_delimited_field(2, response),
        )
        with patch("tools.probe_auth._certificate_summary", return_value={}), patch(
            "tools.probe_auth._verify_signature",
            side_effect=lambda signature, cert, data, scheme, digest: data == b"tls",
        ):
            report = analyze_response(message, b"fresh-nonce", b"tls")
        self.assertTrue(report["signature_valid_for_tls_certificate_only"])
        self.assertTrue(report["signature_valid_for_returned_nonce_and_tls_certificate"])
        self.assertFalse(report["signature_valid_for_challenge_nonce_and_tls_certificate"])
        self.assertFalse(report["sender_nonce_matches"])
        self.assertFalse(report["certificate_chain_trust_checked"])
