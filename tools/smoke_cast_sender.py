#!/usr/bin/env python3
"""Exercise the receiver with a development sender that skips device auth.

This is an end-to-end protocol/decoder test, not a substitute for validation
with a stock Google sender.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import ssl

from research.legacy_python_receiver.legacy_cast_receiver.protocol import (
    CONNECTION_NAMESPACE,
    DEFAULT_MEDIA_RECEIVER_APP_ID,
    MEDIA_NAMESPACE,
    RECEIVER_NAMESPACE,
)
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    read_cast_message,
    write_cast_message,
)


async def run(host: str, port: int, url: str) -> None:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    reader, writer = await asyncio.open_connection(host, port, ssl=context)
    sender_id = "sender-smoke"

    async def send(namespace: str, destination: str, payload: dict) -> None:
        await write_cast_message(
            writer,
            CastMessage(
                source_id=sender_id,
                destination_id=destination,
                namespace=namespace,
                payload_utf8=json.dumps(payload, separators=(",", ":")),
            ),
        )

    async def response(request_id: int) -> dict:
        for _ in range(20):
            message = await asyncio.wait_for(read_cast_message(reader), timeout=5)
            if message.payload_utf8:
                payload = json.loads(message.payload_utf8)
                if payload.get("requestId") == request_id:
                    return payload
        raise RuntimeError(f"no response for request {request_id}")

    try:
        await send(CONNECTION_NAMESPACE, "receiver-0", {"type": "CONNECT"})
        await send(
            RECEIVER_NAMESPACE,
            "receiver-0",
            {
                "type": "LAUNCH",
                "appId": DEFAULT_MEDIA_RECEIVER_APP_ID,
                "requestId": 1,
            },
        )
        launched = await response(1)
        app = launched["status"]["applications"][0]
        transport_id = app["transportId"]
        await send(CONNECTION_NAMESPACE, transport_id, {"type": "CONNECT"})
        await send(
            MEDIA_NAMESPACE,
            transport_id,
            {
                "type": "LOAD",
                "requestId": 2,
                "autoplay": True,
                "media": {
                    "contentId": url,
                    "contentType": "audio/wav",
                    "metadata": {
                        "metadataType": 3,
                        "title": "Cast receiver smoke test",
                        "artist": "cast-audio-receiver-lab",
                    },
                },
            },
        )
        loaded = await response(2)
        print(json.dumps(loaded, indent=2))
    finally:
        writer.close()
        # A status broadcast may race TLS close in this deliberately tiny
        # client; the receiver response above is the assertion that matters.
        with contextlib.suppress(ConnectionError, OSError, ssl.SSLError):
            await writer.wait_closed()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("url")
    parser.add_argument("--port", type=int, default=8009)
    args = parser.parse_args()
    asyncio.run(run(args.host, args.port, args.url))


if __name__ == "__main__":
    main()
