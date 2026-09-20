#!/usr/bin/env python3
"""Convert Shanocast's public replay table into a Vibecast cert manifest.

The generated manifest contains private/authentication material and must stay in
the ignored state directory.  Nothing from the table is copied into this source
file; the user supplies a local checkout of Shanocast's public patch.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from OpenSSL import crypto
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


WINDOW_START = 1_692_057_600  # 2023-08-15T00:00:00Z
WINDOW_SECONDS = 2 * 24 * 60 * 60
# The process first creates a root, intermediate and unused device certificate;
# OpenScreen's process-global serial counter therefore assigns base + 3 to TLS.
CERT_SERIAL = 0x51C9AC6 + 3
CERT_COMMON_NAME = "4aa9ca2e-c340-11ea-8000-18ba395587df"
SIGNATURE_BYTES = 256


def _array(patch: str, name: str) -> bytes:
    match = re.search(
        rf"(?:static\s+)?(?:const\s+)?(?:unsigned char|uint8_t)\s+{name}\[\]\s*=\s*\{{(.*?)\}};",
        patch,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"array {name!r} was not found in the Shanocast patch")
    return bytes(int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]{2})", match.group(1)))


def _pem(label: str, der: bytes) -> str:
    encoded = base64.encodebytes(der).decode("ascii")
    return f"-----BEGIN {label}-----\n{encoded}-----END {label}-----\n"


def _peer_certificate(key: rsa.RSAPrivateKey, start: int) -> x509.Certificate:
    # pyOpenSSL exposes the same X509 setters used by OpenScreen/BoringSSL and
    # still permits its historical SHA-1 self-signature. The certificate's
    # exact DER is covered by the captured device-auth signature.
    certificate = crypto.X509()
    certificate.set_version(2)
    certificate.set_serial_number(CERT_SERIAL)
    certificate.set_notBefore(
        datetime.fromtimestamp(start, tz=timezone.utc).strftime("%y%m%d%H%M%SZ").encode()
    )
    certificate.set_notAfter(
        datetime.fromtimestamp(start + WINDOW_SECONDS, tz=timezone.utc)
        .strftime("%y%m%d%H%M%SZ")
        .encode()
    )
    certificate.get_subject().CN = CERT_COMMON_NAME
    certificate.set_issuer(certificate.get_subject())
    pkey = crypto.PKey.from_cryptography_key(key)
    certificate.set_pubkey(pkey)
    certificate.sign(pkey, "sha1")
    return certificate.to_cryptography()


def _signature_hash(
    device_cert: x509.Certificate, signature: bytes, peer_der: bytes
) -> str:
    public_key = device_cert.public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Shanocast device certificate does not contain an RSA key")
    for name, algorithm in (("sha256", hashes.SHA256()), ("sha1", hashes.SHA1())):
        try:
            public_key.verify(signature, peer_der, padding.PKCS1v15(), algorithm)
        except InvalidSignature:
            continue
        return name
    raise ValueError("signature does not match the reproduced peer certificate")


def build_manifest(patch_path: Path, current_only: bool) -> tuple[dict[str, object], str]:
    source = patch_path.read_text(encoding="utf-8")
    device_der = _array(source, "auth_crt")
    intermediate_der = _array(source, "intermediate_crt")
    private_key_der = _array(source, "peer_key_der")
    signatures = _array(source, "signatures")
    if len(signatures) % SIGNATURE_BYTES:
        raise ValueError("Shanocast signature table length is not divisible by 256")

    key = serialization.load_der_private_key(private_key_der, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Shanocast peer key is not RSA")
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode("ascii")
    device_cert = x509.load_der_x509_certificate(device_der)

    count = len(signatures) // SIGNATURE_BYTES
    indices = range(count)
    if current_only:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        index = (now - WINDOW_START) // WINDOW_SECONDS
        if not 0 <= index < count:
            raise ValueError("the current time is outside Shanocast's replay table")
        indices = range(index, index + 1)

    certs: list[dict[str, str]] = []
    verified_hashes: set[str] = set()
    for index in indices:
        start = WINDOW_START + index * WINDOW_SECONDS
        peer_cert = _peer_certificate(key, start)
        peer_der = peer_cert.public_bytes(serialization.Encoding.DER)
        signature = signatures[index * SIGNATURE_BYTES : (index + 1) * SIGNATURE_BYTES]
        verified_hashes.add(_signature_hash(device_cert, signature, peer_der))
        encoded_signature = base64.b64encode(signature).decode("ascii")
        certs.append(
            {
                "pu": peer_cert.public_bytes(serialization.Encoding.PEM).decode("ascii"),
                "pr": key_pem,
                # Shanocast has one captured response per validity window. Modern
                # senders request SHA-256; keeping the same bytes in both required
                # manifest slots preserves Shanocast's behavior for that capture.
                "sig_sha1": encoded_signature,
                "sig_sha256": encoded_signature,
            }
        )

    manifest: dict[str, object] = {
        "cpu": _pem("CERTIFICATE", device_der),
        "ica": _pem("CERTIFICATE", intermediate_der),
        "certs": certs,
    }
    return manifest, ",".join(sorted(verified_hashes))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("patch", type=Path, help="path to shanocast.patch")
    parser.add_argument("output", type=Path, help="ignored output certs.json")
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="emit only the currently valid two-day bundle",
    )
    args = parser.parse_args()

    try:
        manifest, verified_hashes = build_manifest(args.patch, args.current_only)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"wrote {len(manifest['certs'])} verified bundle(s) to {args.output} "
        f"(captured hash: {verified_hashes})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
