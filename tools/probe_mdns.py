#!/usr/bin/env python3
"""Send a unicast-response mDNS query and sanitize Cast TXT metadata."""

from __future__ import annotations

import argparse
import json
import socket
import struct
from typing import Any

from research.legacy_python_receiver.legacy_cast_receiver.mdns import (
    MDNS_PORT,
    SERVICE_NAME,
    encode_dns_name,
)


def query_packet() -> bytes:
    return (
        struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
        + encode_dns_name(SERVICE_NAME)
        + struct.pack(">HH", 12, 0x8001)  # PTR, request unicast response
    )


def probe(host: str, timeout: float) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query_packet(), (host, MDNS_PORT))
        packet, source = sock.recvfrom(9000)
    finally:
        sock.close()
    return {
        "source_address": source[0],
        "records": parse_packet(packet),
    }


def parse_packet(packet: bytes) -> list[dict[str, Any]]:
    if len(packet) < 12:
        raise ValueError("truncated DNS header")
    _, _, questions, answers, authority, additional = struct.unpack(
        ">HHHHHH", packet[:12]
    )
    offset = 12
    for _ in range(questions):
        _, offset = _read_name(packet, offset)
        offset += 4
    records: list[dict[str, Any]] = []
    for _ in range(answers + authority + additional):
        name, offset = _read_name(packet, offset)
        if offset + 10 > len(packet):
            raise ValueError("truncated DNS record")
        record_type, record_class, ttl, size = struct.unpack(
            ">HHIH", packet[offset : offset + 10]
        )
        offset += 10
        start, end = offset, offset + size
        if end > len(packet):
            raise ValueError("truncated DNS record data")
        record: dict[str, Any] = {
            "name": name,
            "type": record_type,
            "class": record_class & 0x7FFF,
            "ttl": ttl,
        }
        if record_type == 12:
            record["ptr"], _ = _read_name(packet, start)
        elif record_type == 33 and size >= 6:
            priority, weight, port = struct.unpack(">HHH", packet[start : start + 6])
            target, _ = _read_name(packet, start + 6)
            record["srv"] = {
                "priority": priority,
                "weight": weight,
                "port": port,
                "target": target,
            }
        elif record_type == 16:
            record["txt"] = _parse_txt(packet[start:end])
        elif record_type == 1 and size == 4:
            record["address"] = socket.inet_ntoa(packet[start:end])
        records.append(record)
        offset = end
    return records


def _read_name(packet: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    next_offset: int | None = None
    seen: set[int] = set()
    while True:
        if offset >= len(packet) or offset in seen:
            raise ValueError("invalid compressed DNS name")
        seen.add(offset)
        length = packet[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise ValueError("truncated DNS pointer")
            pointer = ((length & 0x3F) << 8) | packet[offset + 1]
            if next_offset is None:
                next_offset = offset + 2
            offset = pointer
            continue
        offset += 1
        end = offset + length
        if end > len(packet):
            raise ValueError("truncated DNS label")
        labels.append(packet[offset:end].decode("utf-8", errors="replace"))
        offset = end
    return ".".join(labels) + ".", next_offset or offset


def _parse_txt(data: bytes) -> dict[str, str]:
    output: dict[str, str] = {}
    offset = 0
    while offset < len(data):
        size = data[offset]
        offset += 1
        item = data[offset : offset + size].decode("utf-8", errors="replace")
        offset += size
        key, separator, value = item.partition("=")
        if key not in {"id", "cd"}:
            output[key] = value if separator else ""
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe sanitized _googlecast._tcp metadata"
    )
    parser.add_argument("host")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    try:
        report = probe(args.host, args.timeout)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"mDNS probe failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
