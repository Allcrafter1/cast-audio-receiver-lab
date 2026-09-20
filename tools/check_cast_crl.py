#!/usr/bin/env python3
"""Check a Cast device certificate against Google's opaque Cast CRL."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import serialization

DEFAULT_URL = "https://clients3.google.com/cast/chromecast/device/crl"


def _manifest_cert(path: Path) -> x509.Certificate:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return x509.load_pem_x509_certificate(manifest["cpu"].encode("ascii"))


def check(cert: x509.Certificate, crl_blob: bytes) -> dict[str, object]:
    spki = cert.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = hashlib.sha256(spki).hexdigest()
    return {
        "device_subject": cert.subject.rfc4514_string(),
        "device_serial_hex": format(cert.serial_number, "x"),
        "subject_public_key_sha256": fingerprint,
        "crl_bytes": len(crl_blob),
        "revoked": bytes.fromhex(fingerprint) in crl_blob,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--crl-file", type=Path)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    blob = (
        args.crl_file.read_bytes()
        if args.crl_file
        else urllib.request.urlopen(args.url, timeout=15).read()
    )
    print(json.dumps(check(_manifest_cert(args.manifest), blob), indent=2))


if __name__ == "__main__":
    main()
