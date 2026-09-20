import hashlib
import unittest
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from tools.check_cast_crl import check


class CastCrlTests(unittest.TestCase):
    def test_detects_subject_public_key_hash_in_opaque_blob(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(7)
            .not_valid_before(datetime(2020, 1, 1))
            .not_valid_after(datetime(2030, 1, 1))
            .sign(key, hashes.SHA256())
        )
        spki = cert.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        report = check(cert, b"prefix" + hashlib.sha256(spki).digest())
        self.assertTrue(report["revoked"])
