# SPDX-License-Identifier: MPL-2.0
"""Private process relay for the receiver's typed, player-scoped settings.

The receiver owns validation, revisions and persistence. This module only carries
snapshots and update acknowledgements over the already owned adapter process.
"""
import asyncio
import json
import math
import sys
import time
from websockets.exceptions import ConnectionClosed

PREFIX = "CAST_AUDIO_SETTINGS "
TIMEOUT = 4.0


def validate_update(body):
    if (not isinstance(body, dict)
            or set(body) != {"appKey", "expectedRevision", "changes"}
            or not isinstance(body["appKey"], str) or not 0 < len(body["appKey"]) <= 128
            or type(body["expectedRevision"]) is not int
            or not 0 <= body["expectedRevision"] < 2**64
            or not isinstance(body["changes"], dict) or not 0 < len(body["changes"]) <= 32
            or any(not isinstance(key, str) or not 0 < len(key) <= 128
                   or (value is not None and type(value) not in {str, bool, int, float})
                   or (isinstance(value, str) and len(value) > 1024)
                   or (type(value) is float and not math.isfinite(value))
                   for key, value in body["changes"].items())):
        raise ValueError("invalid settings update")
    return body


class SettingsRelay:
    def __init__(self, player):
        self.player = player
        self.apps = None
        self.pending = {}

    def receive(self, message):
        if message.get("type") == "settingsSnapshot":
            self.apps = message["apps"]
        elif message.get("type") == "settingsUpdateResult":
            app = message["app"]
            if self.apps is not None:
                self.apps = [app if value["appKey"] == app["appKey"] else value
                             for value in self.apps]
            future = self.pending.get(message.get("requestId"))
            if future is not None and not future.done():
                future.set_result(message)

    def disconnect(self):
        self.apps = None
        for future in self.pending.values():
            if not future.done():
                future.set_exception(RuntimeError("settings unavailable"))

    async def request(self, request):
        if self.player._websocket is None or self.apps is None:
            raise RuntimeError("settings unavailable")
        if request.get("operation") == "get":
            return {"apps": self.apps}
        if request.get("operation") != "update":
            raise ValueError("invalid operation")
        body = validate_update(request.get("body"))
        ident = request["requestId"]
        future = asyncio.get_running_loop().create_future()
        self.pending[ident] = future
        try:
            await self.player._send({"type": "settingsUpdate", "requestId": ident, **body})
            async with asyncio.timeout(TIMEOUT - 1):
                return await future
        finally:
            self.pending.pop(ident, None)

    async def serve(self, reader, emit):
        while raw := await reader.readline():
            ident = None
            try:
                request = json.loads(raw)
                ident = request.get("requestId")
                if not isinstance(ident, str) or len(ident) != 32:
                    raise ValueError("invalid request id")
                # Requests may queue behind a slow update. Never begin an
                # expired mutation after management has already timed out.
                expires = request.get("expiresAt")
                if type(expires) not in {int, float} or not time.monotonic() < expires:
                    raise RuntimeError("settings request expired")
                result = await self.request(request)
                response = {"requestId": ident, "result": result}
            except (ValueError, TypeError, KeyError, AttributeError, OSError, RuntimeError, TimeoutError, ConnectionClosed):
                response = {"requestId": ident, "error": "settings_unavailable"}
            line = PREFIX + json.dumps(response, ensure_ascii=False, separators=(",", ":"))
            if len(line.encode()) > 60000:
                line = PREFIX + json.dumps({"requestId": ident, "error": "settings_unavailable"})
            emit(line)

    async def run_stdio(self):
        reader = asyncio.StreamReader(limit=32768)
        transport, _ = await asyncio.get_running_loop().connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
        try:
            await self.serve(reader, lambda line: print(line, flush=True))
        finally:
            transport.close()
