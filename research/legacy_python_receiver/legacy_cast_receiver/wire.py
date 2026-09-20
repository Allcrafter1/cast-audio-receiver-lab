"""Minimal protobuf and Cast V2 framing for the historical receiver."""

from __future__ import annotations

import asyncio
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterator


MAX_FRAME_SIZE = 1024 * 1024


class WireError(ValueError):
    pass


class PayloadType(IntEnum):
    STRING = 0
    BINARY = 1


@dataclass(slots=True)
class CastMessage:
    source_id: str
    destination_id: str
    namespace: str
    payload_type: PayloadType = PayloadType.STRING
    payload_utf8: str = ""
    payload_binary: bytes = b""
    protocol_version: int = 0

    def encode(self) -> bytes:
        parts = [
            _field_varint(1, self.protocol_version),
            _field_bytes(2, self.source_id.encode()),
            _field_bytes(3, self.destination_id.encode()),
            _field_bytes(4, self.namespace.encode()),
            _field_varint(5, int(self.payload_type)),
        ]
        if self.payload_type == PayloadType.STRING:
            parts.append(_field_bytes(6, self.payload_utf8.encode()))
        else:
            parts.append(_field_bytes(7, self.payload_binary))
        return b"".join(parts)

    @classmethod
    def decode(cls, data: bytes) -> "CastMessage":
        values: dict[int, int | bytes] = {}
        for number, _wire_type, value in _iter_fields(data):
            values[number] = value

        try:
            payload_type = PayloadType(int(values.get(5, 0)))
            source = _as_bytes(values[2]).decode()
            destination = _as_bytes(values[3]).decode()
            namespace = _as_bytes(values[4]).decode()
        except (KeyError, UnicodeDecodeError, ValueError) as exc:
            raise WireError(f"invalid CastMessage: {exc}") from exc

        return cls(
            protocol_version=int(values.get(1, 0)),
            source_id=source,
            destination_id=destination,
            namespace=namespace,
            payload_type=payload_type,
            payload_utf8=(
                _as_bytes(values.get(6, b"")).decode()
                if payload_type == PayloadType.STRING
                else ""
            ),
            payload_binary=(
                _as_bytes(values.get(7, b""))
                if payload_type == PayloadType.BINARY
                else b""
            ),
        )


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise WireError("negative varints are not supported")
    output = bytearray()
    while value > 0x7F:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def decode_varint(data: bytes, offset: int = 0) -> tuple[int, int]:
    value = 0
    shift = 0
    for index in range(offset, min(len(data), offset + 10)):
        byte = data[index]
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index + 1
        shift += 7
    raise WireError("truncated or oversized varint")


def encode_length_delimited_field(number: int, value: bytes) -> bytes:
    return _field_bytes(number, value)


def encode_varint_field(number: int, value: int) -> bytes:
    return _field_varint(number, value)


def iter_protobuf_fields(data: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    """Expose the generic reader for small nested Cast messages."""
    yield from _iter_fields(data)


def frame(message: CastMessage) -> bytes:
    encoded = message.encode()
    if len(encoded) > MAX_FRAME_SIZE:
        raise WireError("Cast frame exceeds size limit")
    return struct.pack(">I", len(encoded)) + encoded


async def read_cast_message(
    reader: asyncio.StreamReader, max_size: int = MAX_FRAME_SIZE
) -> CastMessage:
    header = await reader.readexactly(4)
    (size,) = struct.unpack(">I", header)
    if size == 0 or size > max_size:
        raise WireError(f"invalid Cast frame length: {size}")
    return CastMessage.decode(await reader.readexactly(size))


async def write_cast_message(
    writer: asyncio.StreamWriter, message: CastMessage
) -> None:
    writer.write(frame(message))
    await writer.drain()


def _field_varint(number: int, value: int) -> bytes:
    return encode_varint((number << 3) | 0) + encode_varint(value)


def _field_bytes(number: int, value: bytes) -> bytes:
    return (
        encode_varint((number << 3) | 2)
        + encode_varint(len(value))
        + value
    )


def _iter_fields(data: bytes) -> Iterator[tuple[int, int, int | bytes]]:
    offset = 0
    while offset < len(data):
        key, offset = decode_varint(data, offset)
        number, wire_type = key >> 3, key & 0x07
        if not number:
            raise WireError("protobuf field number zero")
        if wire_type == 0:
            value, offset = decode_varint(data, offset)
        elif wire_type == 1:
            end = offset + 8
            if end > len(data):
                raise WireError("truncated fixed64 field")
            value, offset = data[offset:end], end
        elif wire_type == 2:
            size, offset = decode_varint(data, offset)
            end = offset + size
            if end > len(data):
                raise WireError("truncated length-delimited field")
            value, offset = data[offset:end], end
        elif wire_type == 5:
            end = offset + 4
            if end > len(data):
                raise WireError("truncated fixed32 field")
            value, offset = data[offset:end], end
        else:
            raise WireError(f"unsupported protobuf wire type: {wire_type}")
        yield number, wire_type, value


def _as_bytes(value: int | bytes) -> bytes:
    if not isinstance(value, bytes):
        raise WireError("expected length-delimited protobuf value")
    return value
