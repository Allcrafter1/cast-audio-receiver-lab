"""Device-authentication extension point.

Google Cast senders require a receiver certificate chained to Google's trust
roots.  This project intentionally contains no extracted device key, replay
table, or certificate bypass.  A legitimate implementation can be supplied as
an external provider without coupling it to the protocol engine.
"""

from __future__ import annotations

import importlib
import logging
from typing import Protocol

from .wire import iter_protobuf_fields


DEVICE_AUTH_NAMESPACE = "urn:x-cast:com.google.cast.tp.deviceauth"
LOG = logging.getLogger(__name__)


class AuthProvider(Protocol):
    async def respond(
        self, challenge: bytes, receiver_tls_certificate_der: bytes
    ) -> bytes | None:
        """Return an encoded DeviceAuthMessage response, or reject it."""


class RejectingAuthProvider:
    """Safe default: fail closed when a stock sender requests attestation."""

    async def respond(
        self, challenge: bytes, receiver_tls_certificate_der: bytes
    ) -> bytes | None:
        del receiver_tls_certificate_der
        LOG.warning(
            "Sender auth challenge observed (no secret values): %s",
            describe_challenge(challenge),
        )
        return None


def describe_challenge(message: bytes) -> dict[str, int | str | bool]:
    """Summarize a DeviceAuthMessage challenge without exposing its nonce."""
    outer = _field_map(message)
    nested = outer.get(1)
    if not isinstance(nested, bytes):
        return {"valid": False, "reason": "missing_challenge"}
    challenge = _field_map(nested)
    nonce = challenge.get(2)
    return {
        "valid": True,
        "signature_algorithm": _algorithm_name(
            challenge.get(1), {0: "UNSPECIFIED", 1: "PKCS1v15", 2: "PSS"}, 1
        ),
        "hash_algorithm": _algorithm_name(
            challenge.get(3), {0: "SHA1", 1: "SHA256"}, 0
        ),
        "sender_nonce_present": isinstance(nonce, bytes) and bool(nonce),
        "sender_nonce_bytes": len(nonce) if isinstance(nonce, bytes) else 0,
    }


def load_auth_provider(spec: str | None) -> AuthProvider:
    if not spec:
        return RejectingAuthProvider()
    if ":" not in spec:
        raise ValueError("auth provider must be MODULE:ATTRIBUTE")
    module_name, attribute_name = spec.rsplit(":", 1)
    value = getattr(importlib.import_module(module_name), attribute_name)
    provider = value() if isinstance(value, type) else value
    if not hasattr(provider, "respond"):
        raise TypeError("auth provider must define async respond()")
    return provider


def _field_map(data: bytes) -> dict[int, int | bytes]:
    return {
        number: value
        for number, _wire_type, value in iter_protobuf_fields(data)
    }


def _algorithm_name(
    value: int | bytes | None, names: dict[int, str], default: int
) -> str:
    selected = value if isinstance(value, int) else default
    return names.get(selected, f"UNKNOWN_{selected}")
