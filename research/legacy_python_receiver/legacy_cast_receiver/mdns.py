"""Historical hand-written mDNS advertiser for the Python receiver prototype."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import struct
import uuid
from dataclasses import dataclass, field


LOG = logging.getLogger(__name__)
MULTICAST_ADDRESS = "224.0.0.251"
MDNS_PORT = 5353
SERVICE_NAME = "_googlecast._tcp.local."


def encode_dns_name(name: str) -> bytes:
    labels = name.rstrip(".").split(".")
    encoded = bytearray()
    for label in labels:
        raw = label.encode("utf-8")
        if len(raw) > 63:
            raise ValueError("DNS label exceeds 63 bytes")
        encoded.append(len(raw))
        encoded.extend(raw)
    encoded.append(0)
    return bytes(encoded)


def build_announcement(
    friendly_name: str,
    host_name: str,
    address: str,
    port: int,
    device_id: str,
) -> bytes:
    service = SERVICE_NAME
    instance = f"{friendly_name}.{service}"
    host = f"{host_name.rstrip('.')}.local."
    txt = {
        "id": device_id.replace("-", ""),
        "cd": device_id.replace("-", ""),
        "fn": friendly_name,
        "md": "Cast Audio Lab",
        "ca": "4",  # AUDIO_OUT
        "st": "0",
        "ve": "05",
        "nf": "1",
        "rs": "Ready to cast audio",
    }
    records = [
        _record(service, 12, 4500, encode_dns_name(instance)),
        _record(instance, 33, 120, struct.pack(">HHH", 0, 0, port) + encode_dns_name(host)),
        _record(instance, 16, 4500, _encode_txt(txt)),
        _record(host, 1, 120, ipaddress.IPv4Address(address).packed),
    ]
    return struct.pack(">HHHHHH", 0, 0x8400, 0, len(records), 0, 0) + b"".join(records)


@dataclass(slots=True)
class MdnsAdvertiser:
    friendly_name: str
    address: str
    port: int
    device_id: str = ""
    interval: float = 30.0
    _socket: socket.socket | None = field(init=False, default=None, repr=False)
    _task: asyncio.Task[None] | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.device_id:
            self.device_id = str(uuid.uuid4())

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", MDNS_PORT))
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            socket.inet_aton(MULTICAST_ADDRESS) + socket.inet_aton("0.0.0.0"),
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        sock.setblocking(False)
        self._socket = sock
        self._task = asyncio.create_task(self._run(loop))

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._socket:
            self._socket.close()
            self._socket = None

    async def _run(self, loop: asyncio.AbstractEventLoop) -> None:
        assert self._socket is not None
        packet = build_announcement(
            self.friendly_name,
            socket.gethostname().split(".")[0],
            self.address,
            self.port,
            self.device_id,
        )
        service_wire = encode_dns_name(SERVICE_NAME)
        await loop.sock_sendto(
            self._socket, packet, (MULTICAST_ADDRESS, MDNS_PORT)
        )
        while True:
            try:
                query, source = await asyncio.wait_for(
                    loop.sock_recvfrom(self._socket, 9000),
                    timeout=self.interval,
                )
                if service_wire in query:
                    await loop.sock_sendto(self._socket, packet, source)
            except TimeoutError:
                await loop.sock_sendto(
                    self._socket, packet, (MULTICAST_ADDRESS, MDNS_PORT)
                )
            except OSError:
                LOG.exception("mDNS receive/send failed")
                return


def _record(name: str, record_type: int, ttl: int, rdata: bytes) -> bytes:
    return (
        encode_dns_name(name)
        + struct.pack(">HHIH", record_type, 0x8001, ttl, len(rdata))
        + rdata
    )


def _encode_txt(values: dict[str, str]) -> bytes:
    output = bytearray()
    for key, value in values.items():
        item = f"{key}={value}".encode()
        if len(item) > 255:
            raise ValueError("mDNS TXT item exceeds 255 bytes")
        output.append(len(item))
        output.extend(item)
    return bytes(output)
