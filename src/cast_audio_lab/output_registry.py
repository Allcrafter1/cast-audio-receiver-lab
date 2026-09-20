"""Static registry for supported managed audio outputs.

This is deliberately not a dynamic plugin loader.  It gives route validation,
process construction and the player CLI one authoritative description of each
shipped backend, while normal Python changes remain sufficient for a new one.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
import ipaddress
from pathlib import Path
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from .backend import AudioBackend

if TYPE_CHECKING:
    from .routes import Route


TargetValidator = Callable[[object], dict | None]
BackendFactory = Callable[[argparse.Namespace], AudioBackend]
ArgumentBuilder = Callable[["Route", Path, str], list[str]]


@dataclass(frozen=True, slots=True)
class OutputDefinition:
    key: str
    label: str
    singleton: bool
    validate_target: TargetValidator
    create_backend: BackendFactory
    adapter_arguments: ArgumentBuilder


def _no_target(value: object) -> None:
    if value is not None:
        raise ValueError("local output does not accept a target")
    return None


def _safe_text(value: object, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any(ord(char) < 32 for char in value)
    ):
        raise ValueError(f"invalid {label}")
    return value.strip()


def _airplay_target(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("AirPlay target must be an object")
    from .airplay import AirPlayTarget

    if set(value) - set(AirPlayTarget.__dataclass_fields__):
        raise ValueError("unknown target field")
    result = dict(value)
    host = _safe_text(result.get("host"), "target host", 253)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
            raise ValueError("invalid target host") from None
    result["host"] = host
    port = result.setdefault("port", 7000)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("invalid target port")
    if result.setdefault("protocol", "auto") not in {
        "auto",
        "raop",
        "airplay2",
        "airplay2-compat",
    }:
        raise ValueError("invalid target protocol")
    result["device_id"] = _safe_text(
        result.get("device_id"), "target device identity", 256
    )
    for key in set(result) - {"port", "txt", "host", "device_id"}:
        if (
            not isinstance(result[key], str)
            or len(result[key]) > 4096
            or any(ord(char) < 32 for char in result[key])
        ):
            raise ValueError("invalid target field")
    txt = result.setdefault("txt", {})
    if (
        not isinstance(txt, dict)
        or len(txt) > 64
        or any(
            not isinstance(key, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", key)
            or not isinstance(item, str)
            or len(item) > 4096
            or any(ord(char) < 32 for char in key + item)
            for key, item in txt.items()
        )
    ):
        raise ValueError("invalid target TXT")
    return result


def _network_host(value: object, label: str) -> str:
    host = _safe_text(value, label, 253)
    try:
        address = ipaddress.ip_address(host)
        if not (address.is_private or address.is_link_local or address.is_loopback):
            raise ValueError(f"{label} must be on the local network")
    except ValueError as error:
        if "must be on" in str(error):
            raise
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host):
            raise ValueError(f"invalid {label}") from None
    return host


def _dlna_target(value: object) -> dict:
    allowed = {"description_url", "device_id", "host", "port", "protocol"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("DLNA target requires a description URL")
    description_url = _safe_text(value.get("description_url"), "description URL", 2048)
    parsed = urlsplit(description_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("invalid DLNA description URL")
    host = _network_host(parsed.hostname, "DLNA host")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    canonical = {
        "description_url": description_url,
        "host": host,
        "port": port,
        "protocol": "dlna",
        "device_id": _safe_text(
            str(value.get("device_id") or description_url), "device identity", 2048
        ),
    }
    for key in ("host", "port", "protocol"):
        if key in value and value[key] != canonical[key]:
            raise ValueError(f"inconsistent DLNA {key}")
    return canonical


def _sonos_target(value: object) -> dict:
    allowed = {"host", "device_id", "port", "protocol"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("Sonos target requires a host")
    host = _network_host(value.get("host"), "Sonos host")
    canonical = {
        "host": host,
        "port": 1400,
        "protocol": "sonos",
        "device_id": _safe_text(
            value.get("device_id") or host, "device identity", 256
        ),
    }
    for key in ("port", "protocol"):
        if key in value and value[key] != canonical[key]:
            raise ValueError(f"inconsistent Sonos {key}")
    return canonical


def _mpv_backend(_args: argparse.Namespace) -> AudioBackend:
    from .mpv_backend import MpvAudioBackend

    return MpvAudioBackend()


def _airplay_backend(args: argparse.Namespace) -> AudioBackend:
    from .airplay import AirPlayAudioBackend, load_airplay_target

    if args.airplay_config is None:
        raise ValueError("--backend airplay requires --airplay-config")
    target = load_airplay_target(args.airplay_config)
    return AirPlayAudioBackend(
        target,
        cliairplay=args.cliairplay,
        ffmpeg=args.ffmpeg,
        latency_ms=args.airplay_latency,
        persistent=not args.airplay_reconnect_on_load,
    )


def _dlna_backend(args: argparse.Namespace) -> AudioBackend:
    from .dlna import DlnaAudioBackend, load_dlna_target

    if args.target_config is None:
        raise ValueError("--backend dlna requires --target-config")
    target = load_dlna_target(args.target_config)
    return DlnaAudioBackend(target["description_url"], ffmpeg=args.ffmpeg)


def _sonos_backend(args: argparse.Namespace) -> AudioBackend:
    from .sonos import SonosAudioBackend, load_sonos_target

    if args.target_config is None:
        raise ValueError("--backend sonos requires --target-config")
    target = load_sonos_target(args.target_config)
    return SonosAudioBackend(target["host"])


def _plain_arguments(_route: "Route", _directory: Path, _cliairplay: str) -> list[str]:
    return []


def _airplay_arguments(route: "Route", directory: Path, cliairplay: str) -> list[str]:
    # Import lazily to keep this registry independent of persistence internals.
    from .routes import atomic_json

    target = directory / f"target-{route.id}.json"
    atomic_json(target, route.target)
    return ["--airplay-config", str(target), "--cliairplay", cliairplay]


def _target_arguments(route: "Route", directory: Path, _cliairplay: str) -> list[str]:
    from .routes import atomic_json

    target = directory / f"target-{route.id}.json"
    atomic_json(target, route.target)
    return ["--target-config", str(target)]


_OUTPUTS = {
    "mpv": OutputDefinition(
        "mpv", "Local audio", True, _no_target, _mpv_backend, _plain_arguments
    ),
    "airplay": OutputDefinition(
        "airplay", "AirPlay", False, _airplay_target, _airplay_backend, _airplay_arguments
    ),
    "dlna": OutputDefinition(
        "dlna", "DLNA renderer", False, _dlna_target, _dlna_backend, _target_arguments
    ),
    "sonos": OutputDefinition(
        "sonos", "Sonos", False, _sonos_target, _sonos_backend, _target_arguments
    ),
}


def output_names() -> tuple[str, ...]:
    return tuple(_OUTPUTS)


def output_definition(name: object) -> OutputDefinition:
    try:
        return _OUTPUTS[name]  # type: ignore[index]
    except (KeyError, TypeError):
        raise ValueError("invalid output backend") from None


def validate_output_target(name: object, target: object) -> dict | None:
    return output_definition(name).validate_target(target)


def create_output_backend(name: object, args: argparse.Namespace) -> AudioBackend:
    return output_definition(name).create_backend(args)


def adapter_arguments(
    name: object, route: "Route", directory: Path, cliairplay: str
) -> list[str]:
    return output_definition(name).adapter_arguments(route, directory, cliairplay)


def is_singleton(name: object) -> bool:
    return output_definition(name).singleton
