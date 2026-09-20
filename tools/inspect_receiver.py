#!/usr/bin/env python3
"""Read-only inspection of Cast receiver status and app availability."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import ssl
from typing import Any

from research.legacy_python_receiver.legacy_cast_receiver.auth import DEVICE_AUTH_NAMESPACE
from research.legacy_python_receiver.legacy_cast_receiver.protocol import (
    CONNECTION_NAMESPACE,
    HEARTBEAT_NAMESPACE,
    RECEIVER_NAMESPACE,
)
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    PayloadType,
    read_cast_message,
    write_cast_message,
)
from probe_auth import build_challenge
from probe_app_launch import _inspect_transport


KNOWN_AUDIO_APP_IDS = [
    "CC1AD845",  # Default Media Receiver
    "233637DE",  # YouTube
    "2DB7CC49",  # YouTube Music
    "CC32E753",  # Spotify
]
DISCOVERY_NAMESPACE = "urn:x-cast:com.google.cast.receiver.discovery"


async def inspect(
    host: str,
    port: int,
    timeout: float,
    include_availability: bool = True,
    inspect_active_transport: bool = False,
) -> dict[str, Any]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            host, port, ssl=context, server_hostname=host
        ),
        timeout,
    )
    try:
        await write_cast_message(
            writer,
            CastMessage(
                source_id="sender-0",
                destination_id="receiver-0",
                namespace=DEVICE_AUTH_NAMESPACE,
                payload_type=PayloadType.BINARY,
                payload_binary=build_challenge(secrets.token_bytes(16)),
            ),
        )
        auth_reply = await asyncio.wait_for(read_cast_message(reader), timeout)
        if auth_reply.namespace != DEVICE_AUTH_NAMESPACE:
            raise RuntimeError("unexpected response to device-auth challenge")

        await _send_json(
            writer,
            CONNECTION_NAMESPACE,
            {"type": "CONNECT", "origin": {}},
        )
        await _send_json(
            writer,
            DISCOVERY_NAMESPACE,
            {"type": "GET_DEVICE_INFO", "requestId": 0},
        )
        try:
            device_info = await _wait_for_type(
                reader, writer, ("GET_DEVICE_INFO", "DEVICE_INFO"), min(timeout, 3.0)
            )
        except TimeoutError:
            device_info = {"type": "NO_DEVICE_INFO_RESPONSE"}
        await _send_json(
            writer,
            RECEIVER_NAMESPACE,
            {"type": "GET_STATUS", "requestId": 1},
        )
        status = await _wait_for_type(
            reader, writer, "RECEIVER_STATUS", timeout
        )
        report = {
            "cast_channel_device_info": device_info,
            "receiver_status": status,
        }
        applications = status.get("status", {}).get("applications", [])
        if (
            inspect_active_transport
            and applications
            and applications[0].get("transportId")
        ):
            report["active_transport_observation"] = await _inspect_transport(
                reader,
                writer,
                "sender-0",
                applications[0]["transportId"],
                min(timeout, 4.0),
            )
        if not include_availability:
            return report
        await _send_json(
            writer,
            RECEIVER_NAMESPACE,
            {
                "type": "GET_APP_AVAILABILITY",
                "requestId": 2,
                "appId": KNOWN_AUDIO_APP_IDS,
            },
        )
        try:
            availability = await _wait_for_type(
                reader, writer, "APP_AVAILABILITY", min(timeout, 3.0)
            )
        except TimeoutError:
            availability = {"type": "NO_APP_AVAILABILITY_RESPONSE"}
        report["known_app_availability"] = availability
        return report
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def _send_json(
    writer: asyncio.StreamWriter, namespace: str, payload: dict[str, Any]
) -> None:
    await write_cast_message(
        writer,
        CastMessage(
            source_id="sender-0",
            destination_id="receiver-0",
            namespace=namespace,
            payload_utf8=json.dumps(payload, separators=(",", ":")),
        ),
    )


async def _wait_for_type(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    expected_type: str | tuple[str, ...],
    timeout: float,
) -> dict[str, Any]:
    async with asyncio.timeout(timeout):
        while True:
            message = await read_cast_message(reader)
            if message.payload_type != PayloadType.STRING:
                continue
            try:
                payload = json.loads(message.payload_utf8)
            except json.JSONDecodeError:
                continue
            if (
                message.namespace == HEARTBEAT_NAMESPACE
                and payload.get("type") == "PING"
            ):
                await write_cast_message(
                    writer,
                    CastMessage(
                        source_id=message.destination_id,
                        destination_id=message.source_id,
                        namespace=HEARTBEAT_NAMESPACE,
                        payload_utf8='{"type":"PONG"}',
                    ),
                )
                continue
            accepted_types = (expected_type,) if isinstance(expected_type, str) else expected_type
            if payload.get("type") in accepted_types:
                return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read Cast receiver status without launching or stopping apps"
    )
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument(
        "--active-transport",
        action="store_true",
        help="request redacted media and MDX status from the running app",
    )
    args = parser.parse_args()
    try:
        report = asyncio.run(
            inspect(
                args.host,
                args.port,
                args.timeout,
                include_availability=not args.status_only,
                inspect_active_transport=args.active_transport,
            )
        )
    except (TimeoutError, OSError, RuntimeError) as exc:
        raise SystemExit(f"inspection failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
