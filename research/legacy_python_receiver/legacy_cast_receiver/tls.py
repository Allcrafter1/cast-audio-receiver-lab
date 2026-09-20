"""Historical ephemeral TLS identity for the Python receiver prototype."""

from __future__ import annotations

import datetime as dt
import os
import ssl
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


@dataclass(slots=True)
class TlsIdentity:
    context: ssl.SSLContext
    certificate_der: bytes
    certificate_path: Path


def create_tls_identity(state_directory: Path, common_name: str) -> TlsIdentity:
    state_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(state_directory, 0o700)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
    )
    now = dt.datetime.now(dt.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(now + dt.timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(common_name)]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path = state_directory / "receiver-key.pem"
    certificate_path = state_directory / "receiver-cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(key_path, 0o600)
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    os.chmod(certificate_path, 0o600)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate_path, key_path)
    return TlsIdentity(
        context=context,
        certificate_der=certificate.public_bytes(serialization.Encoding.DER),
        certificate_path=certificate_path,
    )
