#!/usr/bin/env python3
"""Read-only Cast device-auth behavior probe.

The report intentionally omits signatures and certificate bodies. It performs
the same fresh challenge a sender would perform and reports only properties
needed for interoperability research.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import ssl
from datetime import datetime
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from research.legacy_python_receiver.legacy_cast_receiver.auth import DEVICE_AUTH_NAMESPACE
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    PayloadType,
    encode_length_delimited_field,
    encode_varint_field,
    iter_protobuf_fields,
    read_cast_message,
    write_cast_message,
)


def build_challenge(nonce: bytes) -> bytes:
    # AuthChallenge: PKCS#1 v1.5, fresh sender nonce, SHA-256.
    challenge = b"".join(
        (
            encode_varint_field(1, 1),
            encode_length_delimited_field(2, nonce),
            encode_varint_field(3, 1),
        )
    )
    # DeviceAuthMessage.challenge
    return encode_length_delimited_field(1, challenge)


async def probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    nonce = __import__("secrets").token_bytes(16)

    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            host,
            port,
            ssl=context,
            server_hostname=host,
        ),
        timeout=timeout,
    )
    try:
        ssl_object = writer.get_extra_info("ssl_object")
        if ssl_object is None:
            raise RuntimeError("connection did not negotiate TLS")
        tls_certificate = ssl_object.getpeercert(binary_form=True)
        if not tls_certificate:
            raise RuntimeError("receiver supplied no TLS certificate")
        await write_cast_message(
            writer,
            CastMessage(
                source_id="sender-0",
                destination_id="receiver-0",
                namespace=DEVICE_AUTH_NAMESPACE,
                payload_type=PayloadType.BINARY,
                payload_binary=build_challenge(nonce),
            ),
        )
        response = await asyncio.wait_for(read_cast_message(reader), timeout)
        report = analyze_response(response, nonce, tls_certificate)
        report["tls_version"] = ssl_object.version()
        report["tls_cipher"] = ssl_object.cipher()[0]
        return report
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


def analyze_response(
    message: CastMessage, nonce: bytes, tls_certificate_der: bytes
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "namespace_ok": message.namespace == DEVICE_AUTH_NAMESPACE,
        "binary_payload": message.payload_type == PayloadType.BINARY,
        "tls_certificate": _certificate_summary(tls_certificate_der),
    }
    if message.payload_type != PayloadType.BINARY:
        report["result"] = "not_binary"
        return report

    outer = _collect_fields(message.payload_binary)
    if 3 in outer:
        error = _collect_fields(_first_bytes(outer[3]))
        report["result"] = "auth_error"
        report["error_type"] = _first_int(error.get(1), 0)
        return report
    if 2 not in outer:
        report["result"] = "missing_response"
        return report

    response = _collect_fields(_first_bytes(outer[2]))
    report["auth_response_field_numbers"] = sorted(response)
    report["intermediate_certificates"] = [
        _certificate_summary(value) for value in response.get(3, [])
        if isinstance(value, bytes)
    ]
    signature = _first_bytes(response.get(1, []))
    client_certificate_der = _first_bytes(response.get(2, []))
    returned_nonce = _first_bytes(response.get(5, []))
    signature_algorithm = _first_int(response.get(4), 1)
    hash_algorithm = _first_int(response.get(6), 0)
    report.update(
        {
            "result": "response",
            "signature_bytes": len(signature),
            "signature_algorithm": {
                0: "UNSPECIFIED",
                1: "RSASSA_PKCS1v15",
                2: "RSASSA_PSS",
            }.get(signature_algorithm, f"UNKNOWN_{signature_algorithm}"),
            "hash_algorithm": {
                0: "SHA1",
                1: "SHA256",
            }.get(hash_algorithm, f"UNKNOWN_{hash_algorithm}"),
            "sender_nonce_present": bool(returned_nonce),
            "sender_nonce_matches": returned_nonce == nonce,
            "intermediate_certificate_count": len(response.get(3, [])),
            "crl_present": bool(_first_bytes(response.get(7, []))),
        }
    )
    if client_certificate_der:
        report["client_auth_certificate"] = _certificate_summary(
            client_certificate_der
        )
    report["certificate_chain_trust_checked"] = False
    report["signature_valid_for_returned_nonce_and_tls_certificate"] = _verify_signature(
        signature,
        client_certificate_der,
        returned_nonce + tls_certificate_der,
        signature_algorithm,
        hash_algorithm,
    )
    report["signature_valid_for_challenge_nonce_and_tls_certificate"] = _verify_signature(
        signature,
        client_certificate_der,
        nonce + tls_certificate_der,
        signature_algorithm,
        hash_algorithm,
    )
    report["signature_valid_for_tls_certificate_only"] = _verify_signature(
        signature,
        client_certificate_der,
        tls_certificate_der,
        signature_algorithm,
        hash_algorithm,
    )
    return report


def _verify_signature(
    signature: bytes,
    certificate_der: bytes,
    signed_data: bytes,
    signature_algorithm: int,
    hash_algorithm: int,
) -> bool | None:
    if not signature or not certificate_der:
        return None
    try:
        certificate = x509.load_der_x509_certificate(certificate_der)
        public_key = certificate.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            return None
        digest = hashes.SHA256() if hash_algorithm == 1 else hashes.SHA1()
        if signature_algorithm == 1:
            scheme: padding.AsymmetricPadding = padding.PKCS1v15()
        elif signature_algorithm == 2:
            scheme = padding.PSS(
                mgf=padding.MGF1(digest),
                salt_length=padding.PSS.MAX_LENGTH,
            )
        else:
            return None
        public_key.verify(signature, signed_data, scheme, digest)
        return True
    except Exception:
        return False


def _certificate_summary(der: bytes) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "sha256": hashlib.sha256(der).hexdigest(),
        "der_bytes": len(der),
    }
    try:
        certificate = x509.load_der_x509_certificate(der)
        public_key_der = certificate.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        not_before = certificate.not_valid_before_utc if hasattr(certificate, "not_valid_before_utc") else certificate.not_valid_before
        not_after = certificate.not_valid_after_utc if hasattr(certificate, "not_valid_after_utc") else certificate.not_valid_after
        summary.update(
            {
                "subject": certificate.subject.rfc4514_string(),
                "certificate_signature_oid": certificate.signature_algorithm_oid.dotted_string,
                "extension_oids": [extension.oid.dotted_string for extension in certificate.extensions],
                "issuer": certificate.issuer.rfc4514_string(),
                "subject_public_key_sha256": hashlib.sha256(
                    public_key_der
                ).hexdigest(),
                "not_before": _iso(not_before),
                "not_after": _iso(not_after),
            }
        )
    except ValueError:
        summary["parseable_x509"] = False
    return summary


def _iso(value: datetime) -> str:
    return value.isoformat()


def _collect_fields(data: bytes) -> dict[int, list[int | bytes]]:
    output: dict[int, list[int | bytes]] = {}
    for number, _wire_type, value in iter_protobuf_fields(data):
        output.setdefault(number, []).append(value)
    return output


def _first_bytes(values: list[int | bytes] | None) -> bytes:
    if not values or not isinstance(values[0], bytes):
        return b""
    return values[0]


def _first_int(values: list[int | bytes] | None, default: int) -> int:
    if not values or not isinstance(values[0], int):
        return default
    return values[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe public Cast device-auth behavior without saving credentials"
    )
    parser.add_argument("host", help="IP address of your receiver")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        report = asyncio.run(probe(args.host, args.port, args.timeout))
    except (TimeoutError, OSError, RuntimeError) as exc:
        raise SystemExit(f"probe failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
