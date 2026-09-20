"""Historical DIAL service retained as a backup research path."""

from __future__ import annotations

import asyncio
import html
import logging
import socket
import struct
import urllib.parse
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .lounge import LoungeCredentials


LOG = logging.getLogger(__name__)
DIAL_SERVICE = "urn:dial-multiscreen-org:service:dial:1"
DIAL_DEVICE = "urn:dial-multiscreen-org:device:dial:1"
SSDP_GROUP = "239.255.255.250"
SSDP_PORT = 1900


@dataclass(slots=True, frozen=True)
class DialIdentity:
    name: str
    device_id: str
    address: str
    port: int
    brand: str = "OpenSource"
    model: str = "AudioReceiver"

    @property
    def application_url(self) -> str:
        return f"http://{self.address}:{self.port}/apps/"

    @property
    def description_url(self) -> str:
        return f"http://{self.address}:{self.port}/device-desc.xml"


def parse_msearch(data: bytes) -> str | None:
    try:
        lines = data.decode("iso-8859-1").replace("\r\n", "\n").split("\n")
    except UnicodeDecodeError:
        return None
    if not lines or lines[0].strip().upper() != "M-SEARCH * HTTP/1.1":
        return None
    headers: dict[str, str] = {}
    for line in lines[1:]:
        key, separator, value = line.partition(":")
        if separator:
            headers[key.strip().lower()] = value.strip()
    if headers.get("man", "").lower() != '"ssdp:discover"':
        return None
    target = headers.get("st")
    if target not in (DIAL_SERVICE, "ssdp:all"):
        return None
    return target


def ssdp_response(identity: DialIdentity, target: str) -> bytes:
    return (
        "HTTP/1.1 200 OK\r\n"
        f"LOCATION: {identity.description_url}\r\n"
        f"ST: {target}\r\n"
        "SERVER: Python/3 UPnP/1.0 CastAudioReceiverLab/0.2\r\n"
        f"USN: uuid:{identity.device_id}::{target}\r\n"
        "CACHE-CONTROL: max-age=1800\r\n"
        "EXT:\r\n\r\n"
    ).encode("ascii")


def device_description(identity: DialIdentity) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<root xmlns="urn:schemas-upnp-org:device-1-0">'
        "<specVersion><major>1</major><minor>0</minor></specVersion>"
        "<device>"
        f"<deviceType>{DIAL_DEVICE}</deviceType>"
        f"<friendlyName>{html.escape(identity.name)}</friendlyName>"
        "<manufacturer>Open source</manufacturer>"
        "<modelName>Cast Audio Receiver Lab</modelName>"
        f"<UDN>uuid:{html.escape(identity.device_id)}</UDN>"
        "<serviceList><service>"
        f"<serviceType>{DIAL_SERVICE}</serviceType>"
        "<serviceId>urn:dial-multiscreen-org:serviceId:dial</serviceId>"
        "<controlURL></controlURL><eventSubURL></eventSubURL><SCPDURL></SCPDURL>"
        "</service></serviceList>"
        "</device></root>"
    ).encode()


def youtube_status(
    identity: DialIdentity,
    credentials: LoungeCredentials | None,
    *,
    running: bool,
) -> bytes:
    additional_fields = (
        "<theme>cl</theme>"
        "<testYWRkaXR>c0ef1ca</testYWRkaXR>"
        f"<brand>{html.escape(identity.brand)}</brand>"
        f"<model>{html.escape(identity.model)}</model>"
        f"<deviceId>{html.escape(identity.device_id)}</deviceId>"
    )
    if running and credentials is not None:
        additional_fields += (
            f"<screenId>{html.escape(credentials.screen_id)}</screenId>"
            f"<loungeToken>{html.escape(credentials.lounge_token)}</loungeToken>"
        )
    additional = f"<additionalData>{additional_fields}</additionalData>"
    run_link = '<link rel="run" href="run"/>' if running else ""
    state = "running" if running else "stopped"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<service xmlns="urn:dial-multiscreen-org:schemas:dial" dialVer="2.1">'
        "<name>YouTube</name>"
        '<options allowStop="true"/>'
        f"<state>{state}</state>"
        f"{run_link}"
        f"{additional}</service>"
    ).encode()


class _SsdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, identity: DialIdentity) -> None:
        self.identity = identity
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, address: tuple[str, int]) -> None:
        target = parse_msearch(data)
        if target is not None and self.transport is not None:
            self.transport.sendto(ssdp_response(self.identity, target), address)

    def error_received(self, exc: Exception) -> None:
        LOG.debug("SSDP socket error: %s", exc)


class YouTubeDialServer:
    def __init__(
        self,
        identity: DialIdentity,
        credentials: Callable[[], LoungeCredentials | None],
        register_pairing_code: Callable[[str], Awaitable[None]],
    ) -> None:
        self.identity = identity
        self._credentials = credentials
        self._register_pairing_code = register_pairing_code
        self._http: asyncio.Server | None = None
        self._ssdp: asyncio.DatagramTransport | None = None
        self._running = False

    async def start(self, *, advertise: bool = True) -> None:
        self._http = await asyncio.start_server(
            self._handle_http, "0.0.0.0", self.identity.port
        )
        if advertise:
            loop = asyncio.get_running_loop()
            sock = _ssdp_socket()
            transport, _ = await loop.create_datagram_endpoint(
                lambda: _SsdpProtocol(self.identity), sock=sock
            )
            self._ssdp = transport
        LOG.info(
            "YouTube DIAL application listening at %sYouTube",
            self.identity.application_url,
        )

    async def close(self) -> None:
        if self._ssdp is not None:
            self._ssdp.close()
        if self._http is not None:
            self._http.close()
            await self._http.wait_closed()

    async def _handle_http(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        try:
            method, path, body = await _read_request(reader)
            code, headers, response_body = await self._route(method, path, body)
        except (ValueError, asyncio.IncompleteReadError):
            method, path = "INVALID", "-"
            code, headers, response_body = 400, {}, b"Bad Request"
        LOG.info(
            "DIAL HTTP %s %s from %s -> %d",
            method,
            urllib.parse.urlsplit(path).path,
            peer[0] if isinstance(peer, tuple) and peer else "unknown",
            code,
        )
        reason = {
            200: "OK",
            201: "Created",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
        }[code]
        response_headers = {
            "Content-Length": str(len(response_body)),
            "Connection": "close",
            **headers,
        }
        head = f"HTTP/1.1 {code} {reason}\r\n" + "".join(
            f"{key}: {value}\r\n" for key, value in response_headers.items()
        )
        writer.write(head.encode("iso-8859-1") + b"\r\n" + response_body)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def _route(
        self, method: str, path: str, body: bytes
    ) -> tuple[int, dict[str, str], bytes]:
        clean_path = urllib.parse.urlsplit(path).path
        if method == "GET" and clean_path == "/device-desc.xml":
            return (
                200,
                {
                    "Content-Type": 'text/xml; charset="utf-8"',
                    "Application-URL": self.identity.application_url,
                },
                device_description(self.identity),
            )
        if method == "GET" and clean_path == "/apps/YouTube":
            return (
                200,
                {"Content-Type": 'text/xml; charset="utf-8"'},
                youtube_status(
                    self.identity,
                    self._credentials(),
                    running=self._running,
                ),
            )
        if method == "POST" and clean_path == "/apps/YouTube":
            fields = urllib.parse.parse_qs(body.decode(), keep_blank_values=True)
            LOG.info("YouTube DIAL launch fields: %s", sorted(fields))
            pairing_code = fields.get("pairingCode", [""])[0]
            theme = fields.get("theme", ["cl"])[0]
            if not pairing_code or theme != "cl":
                return 400, {}, b"Bad Request"
            try:
                await self._register_pairing_code(pairing_code)
            except Exception:
                LOG.exception("YouTube DIAL pairing failed")
                return 500, {}, b"Pairing failed"
            self._running = True
            return (
                201,
                {"Location": self.identity.application_url + "YouTube/run"},
                b"",
            )
        if method == "DELETE" and clean_path == "/apps/YouTube/run":
            self._running = False
            return 200, {}, b""
        return 404, {}, b"Not Found"


def new_device_id() -> str:
    return str(uuid.uuid4())


def _ssdp_socket() -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", SSDP_PORT))
    membership = struct.pack(
        "=4s4s",
        socket.inet_aton(SSDP_GROUP),
        socket.inet_aton("0.0.0.0"),
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    sock.setblocking(False)
    return sock


async def _read_request(
    reader: asyncio.StreamReader,
) -> tuple[str, str, bytes]:
    line = await reader.readline()
    parts = line.decode("iso-8859-1").strip().split()
    if len(parts) != 3:
        raise ValueError("bad HTTP request line")
    method, path, _ = parts
    headers: dict[str, str] = {}
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, separator, value = line.decode("iso-8859-1").partition(":")
        if separator:
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length < 0 or length > 64 * 1024:
        raise ValueError("invalid HTTP body length")
    body = await reader.readexactly(length) if length else b""
    return method.upper(), path, body
