#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Verify one isolated profile: mDNS, unauthenticated Cast info and Eureka.

No app launch, device auth, playback, ADB, SSH or account operations. Only the
known profile service is resolved. HTTP port discovery reads sockets owned by
the exact lab PID, then probes loopback; it does not scan the LAN or other PIDs.
"""
from __future__ import annotations
import argparse
import asyncio
import contextlib
import ipaddress
import json
from pathlib import Path
import ssl
import uuid

from wire import CastMessage, read_cast_message, write_cast_message

SERVICE = "_googlecast._tcp.local."


class ProbeFailure(RuntimeError):
    pass


async def resolve_profile(profile, directory, timeout, interface=None):
    from zeroconf import ServiceStateChange
    from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
    installation = uuid.UUID((directory / "installation_id").read_text().strip())
    device = uuid.uuid5(installation, ("cast-hybrid-lab-" + profile))
    service_name = "vibecast-" + device.hex + "." + SERVICE
    friendly = "Audio Lab Probe " + profile
    identity_path = directory / "lab-identity.json"
    if identity_path.exists():
        friendly = json.loads(identity_path.read_text())["friendly_name"]
    zeroconf = AsyncZeroconf(**({"interfaces": [interface]} if interface else {}))
    found = asyncio.Event()
    target = {}
    pending = set()

    async def resolve():
        info = await zeroconf.async_get_service_info(SERVICE, service_name, timeout=2000)
        if info is None:
            return
        properties = {key.decode(): (value or b"").decode(errors="replace")
                      for key, value in info.properties.items()}
        if properties.get("fn") != friendly:
            return
        addresses = [address for address in info.parsed_addresses()
                     if ipaddress.ip_address(address).version == 4]
        if addresses:
            target.update({"host": addresses[0], "cast_port": info.port,
                           "mdns_ca": int(properties["ca"]), "model": properties.get("md"),
                           "friendly_name":friendly})
            found.set()

    def on_change(zeroconf, service_type, name, state_change):
        if name != service_name:
            return
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            task = asyncio.create_task(resolve())
            pending.add(task)
            task.add_done_callback(pending.discard)

    browser = AsyncServiceBrowser(zeroconf.zeroconf, [SERVICE], handlers=[on_change])
    # Targeted resolution also works before the next PTR announcement arrives.
    task = asyncio.create_task(resolve())
    pending.add(task)
    task.add_done_callback(pending.discard)
    try:
        await asyncio.wait_for(found.wait(), timeout)
        return target
    except TimeoutError:
        raise ProbeFailure("exact-profile-not-discovered")
    finally:
        await browser.async_cancel()
        for task in tuple(pending):
            task.cancel()
        await asyncio.gather(*tuple(pending), return_exceptions=True)
        await zeroconf.async_close()


async def device_info(host, port):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=context), 5)
    async def send(namespace, value):
        await write_cast_message(writer, CastMessage(
            "sender-hybrid-lab-info", "receiver-0", namespace, payload_utf8=json.dumps(value)))
    try:
        await send("urn:x-cast:com.google.cast.tp.connection", {"type":"CONNECT"})
        namespace = "urn:x-cast:com.google.cast.receiver.discovery"
        await send(namespace, {"type":"GET_DEVICE_INFO", "requestId":1})
        async with asyncio.timeout(6):
            while True:
                message = await read_cast_message(reader)
                value = json.loads(message.payload_utf8 or "{}")
                if value.get("type") == "PING":
                    await send("urn:x-cast:com.google.cast.tp.heartbeat", {"type":"PONG"})
                if message.namespace == namespace and value.get("requestId") == 1:
                    return value
    finally:
        writer.close()
        with contextlib.suppress(OSError, TimeoutError):
            await asyncio.wait_for(writer.wait_closed(), 1)


def owned_ports(pid):
    root = Path("/proc") / str(pid)
    inodes = set()
    for path in (root / "fd").iterdir():
        with contextlib.suppress(OSError):
            value = path.readlink().as_posix()
            if value.startswith("socket:["):
                inodes.add(value[8:-1])
    ports = set()
    for table in ("tcp", "tcp6"):
        for line in (root / "net" / table).read_text().splitlines()[1:]:
            columns = line.split()
            if len(columns) > 9 and columns[3] == "0A" and columns[9] in inodes:
                ports.add(int(columns[1].split(":")[1], 16))
    if not ports or len(ports) > 32:
        raise ProbeFailure("lab-owned-listeners-unavailable")
    return sorted(ports)


async def get_eureka(port):
    reader = writer = None
    try:
        async with asyncio.timeout(1.0):
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"GET /setup/eureka_info?params=name,device_info HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            await writer.drain()
            header = await reader.readuntil(b"\r\n\r\n")
            if not header.startswith(b"HTTP/1.1 200"):
                return None
            length = next((int(line.split(b":", 1)[1].strip())
                           for line in header.split(b"\r\n")
                           if line.lower().startswith(b"content-length:")), None)
            if length is None or not 0 < length <= 1024 * 1024:
                return None
            payload = await reader.readexactly(length)
            return json.loads(payload)
    except (OSError, ValueError, TimeoutError, asyncio.IncompleteReadError):
        return None
    finally:
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError, TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), 0.2)


async def run(args):
    profiles = json.loads(args.profiles.read_text())
    profile = profiles[args.profile]
    directory = args.run_root / args.profile
    target = await resolve_profile(args.profile, directory, args.timeout, args.interface)
    info = await device_info(target["host"], target["cast_port"])
    if target["mdns_ca"] != profile["mdns_ca"]:
        raise ProbeFailure("mdns-mask-mismatch")
    if info.get("deviceCapabilities") != profile["device_capabilities"]:
        raise ProbeFailure("device-info-mask-mismatch")
    if info.get("friendlyName") != target["friendly_name"]:
        raise ProbeFailure("device-info-profile-mismatch")
    pid = int((directory / "receiver.pid").read_text().strip())
    ports = [args.eureka_port] if args.eureka_port else owned_ports(pid)
    eureka, eureka_port = None, None
    for port in ports:
        if port == target["cast_port"]:
            continue
        candidate = await get_eureka(port)
        if isinstance(candidate, dict) and candidate.get("name") == target["friendly_name"]:
            eureka, eureka_port = candidate, port
            break
    if eureka is None:
        raise ProbeFailure("lab-eureka-not-found")
    capabilities = eureka.get("device_info", {}).get("capabilities", {})
    expected_display = profile.get("eureka_display", profile["display"])
    if capabilities.get("display_supported") is not expected_display:
        raise ProbeFailure("eureka-display-mismatch")
    for key, expected in (("multizone_supported", profile.get("multizone", True)),
                          ("cloud_groups_supported", profile.get("cloud_groups", False))):
        if capabilities.get(key) is not expected:
            raise ProbeFailure("eureka-group-flag-mismatch")
    print(json.dumps({"event":"synthetic_profile_verified", "profile":args.profile,
                      "host":target["host"], "cast_port":target["cast_port"],
                      "eureka_port":eureka_port,
                      "eureka_port_source":"explicit" if args.eureka_port else "lab-pid-owned-listener",
                      "mdns_ca":target["mdns_ca"], "device_capabilities":info["deviceCapabilities"],
                      "eureka_display":expected_display,
                      "query_interface":args.interface or "all",
                      "native_sender_verified":False, "device_auth_verified":False,
                      "audio_verified":False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profiles", type=Path, default=Path(__file__).with_name("profiles.json"))
    parser.add_argument("--run-root", type=Path, default=Path("/runs"))
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--eureka-port", type=int)
    parser.add_argument("--interface", help="Explicit local IPv4 interface for LAN-only DNS-SD verification")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except ProbeFailure as error:
        print(json.dumps({"event":"synthetic_profile_failed", "profile":args.profile,
                          "reason":str(error), "native_sender_verified":False, "audio_verified":False}))
        raise SystemExit(1)
    except Exception as error:
        print(json.dumps({"event":"synthetic_profile_failed", "profile":args.profile,
                          "exception_type":type(error).__name__,
                          "native_sender_verified":False, "audio_verified":False}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
