#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Behavior tests for the silent player; no sockets, receiver or phone touched."""
import asyncio
import contextlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from run_profile import SilentPlayer


class Socket:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return json.dumps(next(self.messages))
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, value):
        self.sent.append(json.loads(value))


class Behavior(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_media_generation_seek_and_secret_redaction(self):
        secret = "DO-NOT-LOG-this-signed-url-token"
        websocket = Socket([
            {"type":"volume", "sessionId":"s", "level":1.0, "muted":True,
             "initialize":True, "volumeRevision":1},
            {"type":"load", "sessionId":"s", "media":{
                "mediaSessionId":7, "streams":[{"url":"https://example.invalid/" + secret,
                                                  "contentType":"audio/mp4"}],
                "title":secret, "duration":300, "startTime":10, "autoplay":True}},
            {"type":"seek", "sessionId":"s", "position":99},
            {"type":"pause", "sessionId":"s"},
            {"type":"volume", "sessionId":"s", "level":0.3, "muted":False,
             "volumeRevision":2},
            {"type":"stop", "sessionId":"s"}])
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            await SilentPlayer(websocket).receive()
        initial, load, seek, pause, volume, stop = websocket.sent
        self.assertEqual((initial["volume"], initial["muted"], initial["volumeRevision"]),
                         (0.25, False, 1))
        self.assertEqual((load["playerState"], load["mediaSessionId"]), ("PLAYING", 7))
        self.assertGreaterEqual(seek["currentTime"], 99)
        self.assertEqual(pause["playerState"], "PAUSED")
        self.assertEqual((volume["volume"], volume["volumeRevision"]), (0.3, 2))
        self.assertEqual((stop["playerState"], stop["idleReason"]), ("IDLE", "CANCELLED"))
        self.assertNotIn(secret, log.getvalue())
        self.assertNotIn("https://", log.getvalue())
        events = [json.loads(line) for line in log.getvalue().splitlines()]
        self.assertTrue(all(value["audio_verified"] is False for value in events))
        self.assertEqual(events[1]["stream_count"], 1)

    async def test_new_media_does_not_echo_old_generation(self):
        websocket = Socket([
            {"type":"load", "sessionId":"first", "media":{
                "mediaSessionId":12, "streams":[], "autoplay":False}},
            {"type":"volume", "sessionId":"next", "level":0.2,
             "muted":False, "volumeRevision":8}])
        with contextlib.redirect_stdout(io.StringIO()):
            await SilentPlayer(websocket).receive()
        self.assertEqual(websocket.sent[0]["mediaSessionId"], 12)
        self.assertNotIn("mediaSessionId", websocket.sent[1])
        self.assertEqual(websocket.sent[1]["currentTime"], 0)


if __name__ == "__main__":
    unittest.main()
