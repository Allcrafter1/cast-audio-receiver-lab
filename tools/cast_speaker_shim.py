#!/usr/bin/env python3
"""Expose an existing Cast receiver through an audio-only lab endpoint.

This tool deliberately keeps the Cast TLS stream opaque.  It forwards port
8009 byte-for-byte, proxies the unencrypted setup API on port 8008, and edits
only the public device-description JSON returned by ``/setup/eureka_info``.
No receiver credentials are copied or loaded by this process.

The shim is an interoperability experiment, not a complete multizone
implementation.  Advertising multizone support only lets us test whether the
sender proceeds to the backend's existing multizone handlers.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import re
import signal
import socket
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass


ANTI_XSSI_PREFIX = b")]}'\n"
MAX_HTTP_REQUEST = 2 * 1024 * 1024
MAX_HTTP_RESPONSE = 16 * 1024 * 1024
HOP_BY_HOP_HEADERS = {
    b"connection",
    b"keep-alive",
    b"proxy-authenticate",
    b"proxy-authorization",
    b"te",
    b"trailer",
    b"transfer-encoding",
    b"upgrade",
}
DIAL_SERVICE = "urn:dial-multiscreen-org:service:dial:1"
SSDP_GROUP = "239.255.255.250"
SSDP_PORT = 1900


@dataclass(frozen=True)
class Identity:
    friendly_name: str
    instance_name: str
    model_name: str
    device_id: str
    advertise_host: str
    advertise_address: str
    base_station: str
    capabilities: int = 4100  # AirReceiver's 4101 with VIDEO_OUT removed.
    setup_state: int | None = None
    wifi_ssid: str | None = None


def normalize_device_id(value: str) -> str:
    normalized = value.replace("-", "").lower()
    if not re.fullmatch(r"[0-9a-f]{32}", normalized):
        raise ValueError("device ID must contain exactly 32 hexadecimal digits")
    return normalized


def derive_base_station(device_id: str) -> str:
    # Locally administered, unicast MAC-like value; used only as public TXT data.
    raw = bytearray.fromhex(device_id[:12])
    raw[0] = (raw[0] | 0x02) & 0xFE
    return raw.hex().upper()


def rewrite_eureka_payload(body: bytes, identity: Identity) -> bytes:
    """Rewrite a setup response, returning the original bytes if it is not JSON."""
    prefix = ANTI_XSSI_PREFIX if body.startswith(ANTI_XSSI_PREFIX) else b""
    encoded = body[len(prefix) :]
    try:
        payload = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body
    if not isinstance(payload, dict):
        return body

    # Some Cast revisions wrap the response in a top-level ``data`` object.
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return body

    data["name"] = identity.friendly_name
    device_info = data.setdefault("device_info", {})
    if isinstance(device_info, dict):
        capabilities = device_info.setdefault("capabilities", {})
        if isinstance(capabilities, dict):
            capabilities["display_supported"] = False
            capabilities["multizone_supported"] = True
        device_info["model_name"] = identity.model_name
        device_info["ssdp_udn"] = identity.device_id

    network = data.get("net")
    if isinstance(network, dict):
        network["ip_address"] = identity.advertise_address

    if identity.setup_state is not None:
        setup = data.setdefault("setup", {})
        if isinstance(setup, dict):
            setup["setup_state"] = identity.setup_state

    if identity.wifi_ssid is not None:
        wifi = data.setdefault("wifi", {})
        if isinstance(wifi, dict):
            wifi["ssid"] = identity.wifi_ssid

    return prefix + json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def parse_http_message_head(head: bytes) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    lines = head.split(b"\r\n")
    start_line = lines[0]
    headers: list[tuple[bytes, bytes]] = []
    for line in lines[1:]:
        if not line:
            continue
        name, separator, value = line.partition(b":")
        if not separator:
            raise ValueError("malformed HTTP header")
        headers.append((name.strip(), value.strip()))
    return start_line, headers


def header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes | None:
    target = name.lower()
    for key, value in headers:
        if key.lower() == target:
            return value
    return None


def parse_dial_msearch(data: bytes) -> str | None:
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
    return target if target in {DIAL_SERVICE, "ssdp:all"} else None


def dial_ssdp_response(identity: Identity, setup_port: int, target: str) -> bytes:
    dial_uuid = str(uuid.UUID(hex=identity.device_id))
    location = (
        f"http://{identity.advertise_address}:{setup_port}/ssdp/device-desc.xml"
    )
    return (
        "HTTP/1.1 200 OK\r\n"
        f"LOCATION: {location}\r\n"
        f"ST: {target}\r\n"
        "SERVER: UPnP/1.0 DLNADOC/1.50 AirReceiver/1.0.5.13\r\n"
        f"USN: uuid:{dial_uuid}::{target}\r\n"
        "CACHE-CONTROL: max-age=1800\r\n"
        "EXT:\r\n\r\n"
    ).encode("ascii")


def rewrite_dial_description(
    body: bytes, upstream_base: bytes, advertised_base: bytes, identity: Identity
) -> bytes:
    body = body.replace(upstream_base, advertised_base)
    dial_uuid = str(uuid.UUID(hex=identity.device_id)).encode("ascii")
    return re.sub(
        rb"<UDN>uuid:[^<]+</UDN>",
        b"<UDN>uuid:" + dial_uuid + b"</UDN>",
        body,
    )


class DialSsdpProtocol(asyncio.DatagramProtocol):
    def __init__(self, identity: Identity, setup_port: int) -> None:
        self.identity = identity
        self.setup_port = setup_port
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, address: tuple[str, int]) -> None:
        target = parse_dial_msearch(data)
        if target is None or self.transport is None:
            return
        self.transport.sendto(
            dial_ssdp_response(self.identity, self.setup_port, target), address
        )
        print(f"[ssdp] advertised DIAL to {address}", flush=True)


async def start_ssdp(
    identity: Identity, setup_port: int
) -> asyncio.DatagramTransport:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        with contextlib.suppress(OSError):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(("", SSDP_PORT))
    membership = socket.inet_aton(SSDP_GROUP) + socket.inet_aton(
        identity.advertise_address
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_IF,
        socket.inet_aton(identity.advertise_address),
    )
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: DialSsdpProtocol(identity, setup_port), sock=sock
    )
    return transport


async def read_http_request(
    reader: asyncio.StreamReader,
) -> tuple[bytes, list[tuple[bytes, bytes]], bytes]:
    head = await reader.readuntil(b"\r\n\r\n")
    if len(head) > MAX_HTTP_REQUEST:
        raise ValueError("HTTP request headers too large")
    start_line, headers = parse_http_message_head(head[:-4])
    length_value = header_value(headers, b"content-length")
    length = int(length_value) if length_value else 0
    if length < 0 or length > MAX_HTTP_REQUEST - len(head):
        raise ValueError("HTTP request body too large")
    body = await reader.readexactly(length) if length else b""
    return start_line, headers, body


async def read_http_response(reader: asyncio.StreamReader) -> tuple[
    bytes, list[tuple[bytes, bytes]], bytes
]:
    head = await reader.readuntil(b"\r\n\r\n")
    if len(head) > MAX_HTTP_RESPONSE:
        raise ValueError("HTTP response headers too large")
    start_line, headers = parse_http_message_head(head[:-4])
    length_value = header_value(headers, b"content-length")
    if length_value is not None:
        length = int(length_value)
        if length < 0 or length > MAX_HTTP_RESPONSE - len(head):
            raise ValueError("HTTP response body too large")
        body = await reader.readexactly(length) if length else b""
    else:
        remaining = MAX_HTTP_RESPONSE - len(head)
        chunks: list[bytes] = []
        while chunk := await reader.read(min(64 * 1024, remaining + 1)):
            chunks.append(chunk)
            remaining -= len(chunk)
            if remaining < 0:
                raise ValueError("HTTP response body too large")
        body = b"".join(chunks)
    return start_line, headers, body


def serialize_http_message(
    start_line: bytes, headers: list[tuple[bytes, bytes]], body: bytes
) -> bytes:
    filtered = [
        (name, value)
        for name, value in headers
        if name.lower() not in HOP_BY_HOP_HEADERS
        and name.lower() not in {b"content-length", b"content-encoding"}
    ]
    filtered.extend(
        [
            (b"Content-Length", str(len(body)).encode("ascii")),
            (b"Connection", b"close"),
        ]
    )
    lines = [start_line, *(name + b": " + value for name, value in filtered)]
    return b"\r\n".join(lines) + b"\r\n\r\n" + body


async def handle_setup_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
    identity: Identity,
    rewrite_device_info: bool = True,
    advertised_setup_port: int = 8008,
) -> None:
    peer = client_writer.get_extra_info("peername")
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        request_line, headers, request_body = await read_http_request(client_reader)
        request_parts = request_line.split(b" ", 2)
        if len(request_parts) != 3:
            raise ValueError("malformed HTTP request line")
        method, raw_target, version = request_parts

        forwarded_headers = [
            (name, value)
            for name, value in headers
            if name.lower() not in HOP_BY_HOP_HEADERS
            and name.lower() not in {b"host", b"content-length", b"accept-encoding"}
        ]
        forwarded_headers.extend(
            [
                (b"Host", f"{upstream_host}:{upstream_port}".encode("ascii")),
                (b"Accept-Encoding", b"identity"),
            ]
        )
        upstream_reader, upstream_writer = await asyncio.open_connection(
            upstream_host, upstream_port
        )
        upstream_writer.write(
            serialize_http_message(
                b" ".join((method, raw_target, version)),
                forwarded_headers,
                request_body,
            )
        )
        await upstream_writer.drain()
        status_line, response_headers, response_body = await read_http_response(
            upstream_reader
        )

        path = urllib.parse.urlsplit(raw_target.decode("ascii", "replace")).path
        upstream_base = f"http://{upstream_host}:{upstream_port}".encode("ascii")
        advertised_base = (
            f"http://{identity.advertise_address}:{advertised_setup_port}"
        ).encode("ascii")
        response_headers = [
            (name, value.replace(upstream_base, advertised_base))
            for name, value in response_headers
        ]
        if path == "/ssdp/device-desc.xml":
            response_body = rewrite_dial_description(
                response_body, upstream_base, advertised_base, identity
            )
            print(f"[setup] rewrote DIAL description for {peer}", flush=True)
        if rewrite_device_info and path in {"/setup/eureka_info", "/setup/device_info"}:
            response_body = rewrite_eureka_payload(response_body, identity)
            print(f"[setup] rewrote {path} for {peer}", flush=True)
        else:
            print(f"[setup] forwarded {method.decode()} {path} for {peer}", flush=True)

        client_writer.write(
            serialize_http_message(status_line, response_headers, response_body)
        )
        await client_writer.drain()
    except (asyncio.IncompleteReadError, OSError, ValueError) as error:
        print(f"[setup] request from {peer} failed: {error}", flush=True)
        with contextlib.suppress(ConnectionError, OSError):
            client_writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            )
            await client_writer.drain()
    finally:
        if upstream_writer is not None:
            upstream_writer.close()
            with contextlib.suppress(Exception):
                await upstream_writer.wait_closed()
        client_writer.close()
        with contextlib.suppress(Exception):
            await client_writer.wait_closed()


async def copy_stream(
    source: asyncio.StreamReader, destination: asyncio.StreamWriter
) -> int:
    byte_count = 0
    try:
        while chunk := await source.read(64 * 1024):
            byte_count += len(chunk)
            destination.write(chunk)
            await destination.drain()
    finally:
        with contextlib.suppress(ConnectionError, OSError):
            destination.write_eof()
    return byte_count


async def handle_cast_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
) -> None:
    peer = client_writer.get_extra_info("peername")
    print(f"[cast] opaque TLS connection from {peer}", flush=True)
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            upstream_host, upstream_port
        )
    except OSError as error:
        print(f"[cast] upstream connection failed: {error}", flush=True)
        client_writer.close()
        await client_writer.wait_closed()
        return

    client_to_upstream = asyncio.create_task(
        copy_stream(client_reader, upstream_writer)
    )
    upstream_to_client = asyncio.create_task(
        copy_stream(upstream_reader, client_writer)
    )
    tasks = {client_to_upstream, upstream_to_client}
    _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    results = await asyncio.gather(
        client_to_upstream, upstream_to_client, return_exceptions=True
    )
    upstream_writer.close()
    client_writer.close()
    await asyncio.gather(
        upstream_writer.wait_closed(),
        client_writer.wait_closed(),
        return_exceptions=True,
    )
    counts = {
        "client_to_upstream": results[0] if isinstance(results[0], int) else "?",
        "upstream_to_client": results[1] if isinstance(results[1], int) else "?",
    }
    print(
        f"[cast] disconnected {peer}; "
        f"bytes c->u={counts['client_to_upstream']} "
        f"u->c={counts['upstream_to_client']}",
        flush=True,
    )


def fetch_backend_identity(host: str, port: int) -> tuple[str | None, str | None]:
    url = f"http://{host}:{port}/setup/eureka_info?options=detail"
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            body = response.read(MAX_HTTP_RESPONSE)
        if body.startswith(ANTI_XSSI_PREFIX):
            body = body[len(ANTI_XSSI_PREFIX) :]
        payload = json.loads(body)
        data = payload.get("data", payload)
        device_info = data.get("device_info", {})
        return data.get("name"), device_info.get("ssdp_udn")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[shim] could not read backend identity: {error}", flush=True)
        return None, None


async def start_mdns(
    identity: Identity, cast_port: int, subtypes: list[str]
) -> list[asyncio.subprocess.Process]:
    address_process = await asyncio.create_subprocess_exec(
        "avahi-publish-address",
        "-R",
        identity.advertise_host,
        identity.advertise_address,
        start_new_session=True,
    )
    txt = [
        f"id={identity.device_id}",
        f"cd={identity.device_id}",
        f"bs={identity.base_station}",
        f"fn={identity.friendly_name}",
        f"md={identity.model_name}",
        f"ca={identity.capabilities}",
        "ve=05",
        "st=0",
        "nf=1",
        "ic=/setup/icon.png",
        "rm=",
        "rs=",
    ]
    subtype_args = [
        argument
        for subtype in subtypes
        for argument in ("--subtype", subtype)
    ]
    service_process = await asyncio.create_subprocess_exec(
        "avahi-publish-service",
        "-H",
        identity.advertise_host,
        *subtype_args,
        identity.instance_name,
        "_googlecast._tcp",
        str(cast_port),
        *txt,
        start_new_session=True,
    )
    return [address_process, service_process]


async def run(args: argparse.Namespace) -> None:
    backend_name, backend_id = await asyncio.to_thread(
        fetch_backend_identity, args.upstream_host, args.setup_upstream_port
    )
    friendly_name = args.name or backend_name or "Audio Lab Speaker"
    raw_device_id = args.device_id or backend_id
    if raw_device_id is None:
        raw_device_id = uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"cast-speaker-shim:{args.advertise_address}:{friendly_name}",
        ).hex
    device_id = normalize_device_id(raw_device_id)
    identity = Identity(
        friendly_name=friendly_name,
        instance_name=args.instance_name or f"{friendly_name} Speaker",
        model_name=args.model,
        device_id=device_id,
        advertise_host=args.advertise_host,
        advertise_address=args.advertise_address,
        base_station=args.base_station or derive_base_station(device_id),
        capabilities=args.capabilities,
        setup_state=args.setup_state,
        wifi_ssid=args.wifi_ssid,
    )

    setup_server = await asyncio.start_server(
        lambda reader, writer: handle_setup_connection(
            reader,
            writer,
            args.upstream_host,
            args.setup_upstream_port,
            identity,
            not args.passthrough_eureka,
            args.setup_port,
        ),
        args.listen_host,
        args.setup_port,
    )
    cast_server = await asyncio.start_server(
        lambda reader, writer: handle_cast_connection(
            reader, writer, args.upstream_host, args.cast_upstream_port
        ),
        args.listen_host,
        args.cast_port,
    )
    dial_server: asyncio.AbstractServer | None = None
    if args.enable_dial:
        dial_server = await asyncio.start_server(
            lambda reader, writer: handle_setup_connection(
                reader,
                writer,
                args.upstream_host,
                args.dial_upstream_port,
                identity,
                False,
                args.dial_port,
            ),
            args.listen_host,
            args.dial_port,
        )
    mdns_processes: list[asyncio.subprocess.Process] = []
    if not args.no_mdns:
        mdns_processes = await start_mdns(identity, args.cast_port, args.subtype)
    ssdp_transport: asyncio.DatagramTransport | None = None
    if args.enable_dial and not args.no_ssdp:
        try:
            ssdp_transport = await start_ssdp(identity, args.dial_port)
            print(
                f"[ssdp] DIAL discovery on {identity.advertise_address}:{SSDP_PORT}",
                flush=True,
            )
        except OSError as error:
            print(f"[ssdp] could not start DIAL discovery: {error}", flush=True)

    print(
        f"[shim] {identity.friendly_name!r} at {identity.advertise_address}; "
        f"ca={identity.capabilities}, id={identity.device_id}",
        flush=True,
    )
    print(
        f"[shim] setup :{args.setup_port} and Cast TLS :{args.cast_port} -> "
        f"{args.upstream_host}",
        flush=True,
    )
    if args.enable_dial:
        print(
            f"[shim] YouTube DIAL :{args.dial_port} -> "
            f"{args.upstream_host}:{args.dial_upstream_port}",
            flush=True,
        )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signum, stop_event.set)
    servers = [setup_server, cast_server]
    if dial_server is not None:
        servers.append(dial_server)
    async with contextlib.AsyncExitStack() as stack:
        for server in servers:
            await stack.enter_async_context(server)
        await stop_event.wait()

    if ssdp_transport is not None:
        ssdp_transport.close()

    for process in mdns_processes:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.terminate()
    for process in mdns_processes:
        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()

    # start_server owns a task per accepted connection.  Cancel any connection
    # still kept open by a sender so shutdown remains deterministic.
    current_task = asyncio.current_task()
    remaining_tasks = [
        task
        for task in asyncio.all_tasks()
        if task is not current_task and not task.done()
    ]
    for task in remaining_tasks:
        task.cancel()
    await asyncio.gather(*remaining_tasks, return_exceptions=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream_host", help="IP of the existing Cast receiver")
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--advertise-address", required=True)
    parser.add_argument("--advertise-host", default=socket.gethostname() + ".local")
    parser.add_argument("--name", help="friendly name; defaults to backend name")
    parser.add_argument("--instance-name", help="DNS-SD instance name")
    parser.add_argument("--model", default="AirReceiver Speaker Lab")
    parser.add_argument("--device-id", help="defaults to the backend Cast ID")
    parser.add_argument("--base-station", help="12 hex digits for the bs TXT field")
    parser.add_argument("--capabilities", type=int, default=4100)
    parser.add_argument(
        "--setup-state",
        type=int,
        help="override only the public setup_state in eureka_info",
    )
    parser.add_argument(
        "--wifi-ssid",
        help="override only the public Wi-Fi SSID in eureka_info",
    )
    parser.add_argument("--setup-port", type=int, default=8008)
    parser.add_argument("--cast-port", type=int, default=8009)
    parser.add_argument("--setup-upstream-port", type=int, default=8008)
    parser.add_argument("--cast-upstream-port", type=int, default=8009)
    parser.add_argument("--dial-port", type=int, default=3600)
    parser.add_argument("--dial-upstream-port", type=int, default=3600)
    parser.add_argument(
        "--enable-dial",
        action="store_true",
        help="also proxy and advertise the optional YouTube DIAL receiver",
    )
    parser.add_argument(
        "--passthrough-eureka",
        action="store_true",
        help="forward setup device information unchanged for control experiments",
    )
    parser.add_argument(
        "--subtype",
        action="append",
        default=[],
        help=(
            "additional DNS-SD subtype (repeatable), for example "
            "_2DB7CC49._sub._googlecast._tcp"
        ),
    )
    parser.add_argument("--no-mdns", action="store_true")
    parser.add_argument("--no-ssdp", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
