#!/usr/bin/env python3
"""Launch a known receiver app, inspect its public status, then stop it."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import ssl
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from research.legacy_python_receiver.legacy_cast_receiver.auth import DEVICE_AUTH_NAMESPACE
from research.legacy_python_receiver.legacy_cast_receiver.protocol import (
    CONNECTION_NAMESPACE,
    HEARTBEAT_NAMESPACE,
    MEDIA_NAMESPACE,
    RECEIVER_NAMESPACE,
)
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    PayloadType,
    read_cast_message,
    write_cast_message,
)
from probe_auth import build_challenge


YOUTUBE_NAMESPACE = "urn:x-cast:com.google.youtube.mdx"


async def probe_launch(
    host: str, port: int, app_id: str, timeout: float, cleanup: bool
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
    sender_id = f"sender-{secrets.token_hex(8)}"
    try:
        await _send(
            writer,
            sender_id,
            "receiver-0",
            DEVICE_AUTH_NAMESPACE,
            build_challenge(secrets.token_bytes(16)),
        )
        auth_reply = await asyncio.wait_for(read_cast_message(reader), timeout)
        if auth_reply.namespace != DEVICE_AUTH_NAMESPACE:
            raise RuntimeError("unexpected device-auth response")
        await _send_json(
            writer,
            sender_id,
            "receiver-0",
            CONNECTION_NAMESPACE,
            {"type": "CONNECT", "origin": {}},
        )
        await _send_json(
            writer,
            sender_id,
            "receiver-0",
            RECEIVER_NAMESPACE,
            {"type": "LAUNCH", "appId": app_id, "requestId": 101},
        )
        response = await _wait_for_launch_result(
            reader, writer, sender_id, timeout
        )
        applications = response.get("status", {}).get("applications", [])
        result: dict[str, Any] = {
            "app_id_requested": app_id,
            "launch_response": response,
            "cleanup_requested": cleanup,
            "cleanup_sent": False,
        }
        if applications and applications[0].get("transportId"):
            result["transport_observation"] = await _inspect_transport(
                reader,
                writer,
                sender_id,
                applications[0]["transportId"],
                timeout=min(timeout, 4.0),
            )
            result["dial_youtube_during_cast_session"] = await asyncio.to_thread(
                _read_dial_youtube_status, host, min(timeout, 4.0)
            )
        if cleanup and applications:
            session_id = applications[0].get("sessionId")
            if session_id:
                await _send_json(
                    writer,
                    sender_id,
                    "receiver-0",
                    RECEIVER_NAMESPACE,
                    {
                        "type": "STOP",
                        "sessionId": session_id,
                        "requestId": 102,
                    },
                )
                result["cleanup_sent"] = True
        return result
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def _wait_for_launch_result(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    sender_id: str,
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
                await _send_json(
                    writer,
                    sender_id,
                    message.source_id,
                    HEARTBEAT_NAMESPACE,
                    {"type": "PONG"},
                )
                continue
            if payload.get("type") in {"RECEIVER_STATUS", "LAUNCH_ERROR"}:
                return payload


async def _inspect_transport(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    sender_id: str,
    transport_id: str,
    timeout: float,
) -> dict[str, Any]:
    await _send_json(
        writer,
        sender_id,
        transport_id,
        CONNECTION_NAMESPACE,
        {"type": "CONNECT", "origin": {}},
    )
    await _send_json(
        writer,
        sender_id,
        transport_id,
        MEDIA_NAMESPACE,
        {"type": "GET_STATUS", "requestId": 103},
    )
    await _send_json(
        writer,
        sender_id,
        transport_id,
        YOUTUBE_NAMESPACE,
        {"type": "getMdxSessionStatus"},
    )
    observation: dict[str, Any] = {
        "media_status_received": False,
        "mdx_session_status_received": False,
    }
    try:
        async with asyncio.timeout(timeout):
            while not (
                observation["media_status_received"]
                and observation["mdx_session_status_received"]
            ):
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
                    await _send_json(
                        writer,
                        sender_id,
                        message.source_id,
                        HEARTBEAT_NAMESPACE,
                        {"type": "PONG"},
                    )
                elif (
                    message.namespace == MEDIA_NAMESPACE
                    and payload.get("type") == "MEDIA_STATUS"
                ):
                    statuses = payload.get("status") or []
                    observation["media_status_received"] = True
                    observation["media_status_items"] = len(statuses)
                    observation["player_states"] = [
                        item.get("playerState")
                        for item in statuses
                        if isinstance(item, dict)
                    ]
                elif (
                    message.namespace == YOUTUBE_NAMESPACE
                    and payload.get("type") == "mdxSessionStatus"
                ):
                    data = payload.get("data") or {}
                    observation["mdx_session_status_received"] = True
                    if isinstance(data, dict):
                        observation["mdx_data_keys"] = sorted(data)
                        screen_id = data.get("screenId")
                        observation["screen_id_present"] = isinstance(
                            screen_id, str
                        ) and bool(screen_id)
                        observation["screen_id_length"] = (
                            len(screen_id) if isinstance(screen_id, str) else 0
                        )
    except TimeoutError:
        observation["timed_out"] = True
    return observation


def _read_dial_youtube_status(host: str, timeout: float) -> dict[str, Any]:
    url = f"http://{host}:8008/apps/YouTube"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(64 * 1024)
            status_code = response.status
            content_type = response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        body = exc.read(64 * 1024)
        status_code = exc.code
        content_type = exc.headers.get_content_type()
    except OSError as exc:
        return {"reachable": False, "error_type": type(exc).__name__}
    report: dict[str, Any] = {
        "reachable": True,
        "http_status": status_code,
        "content_type": content_type,
        "body_bytes": len(body),
    }
    if content_type in {"application/xml", "text/xml"}:
        try:
            root = ET.fromstring(body)
            state = next(
                (
                    element.text
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "state"
                ),
                None,
            )
            report["state"] = state
            report["run_link_present"] = any(
                element.tag.rsplit("}", 1)[-1] == "link"
                and element.attrib.get("rel") == "run"
                for element in root.iter()
            )
        except ET.ParseError:
            report["parseable_xml"] = False
    return report


async def _send_json(
    writer: asyncio.StreamWriter,
    source: str,
    destination: str,
    namespace: str,
    payload: dict[str, Any],
) -> None:
    await write_cast_message(
        writer,
        CastMessage(
            source_id=source,
            destination_id=destination,
            namespace=namespace,
            payload_utf8=json.dumps(payload, separators=(",", ":")),
        ),
    )


async def _send(
    writer: asyncio.StreamWriter,
    source: str,
    destination: str,
    namespace: str,
    payload: bytes,
) -> None:
    await write_cast_message(
        writer,
        CastMessage(
            source_id=source,
            destination_id=destination,
            namespace=namespace,
            payload_type=PayloadType.BINARY,
            payload_binary=payload,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch and inspect a receiver app without playing media"
    )
    parser.add_argument("host")
    parser.add_argument("app_id")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--no-cleanup", action="store_true")
    args = parser.parse_args()
    try:
        report = asyncio.run(
            probe_launch(
                args.host,
                args.port,
                args.app_id,
                args.timeout,
                cleanup=not args.no_cleanup,
            )
        )
    except (TimeoutError, OSError, RuntimeError) as exc:
        raise SystemExit(f"app launch probe failed: {exc}") from exc
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
