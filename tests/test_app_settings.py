# SPDX-License-Identifier: MPL-2.0
import asyncio
import copy
import json
import logging
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import uuid

from aiohttp.test_utils import TestClient, TestServer
from cast_audio_lab.management import create_app
from cast_audio_lab.route_manager import RouteManager
from cast_audio_lab.routes import Route, RouteStore
from cast_audio_lab.settings_ipc import PREFIX, SettingsRelay, validate_update

APP = {"appKey": "youtube", "displayName": "YouTube", "revision": 2, "settings": [
    {"key": "web_volume_compatibility", "label": "Web volume compatibility", "kind": "boolean",
     "value": True, "default": True, "writable": True}]}
UPDATE = {"appKey": "youtube", "expectedRevision": 2,
          "changes": {"web_volume_compatibility": False}}


class SettingsRelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_update_revision_conflict_and_disconnect(self):
        sent = asyncio.Queue()
        player = SimpleNamespace(_websocket=object(), _send=sent.put)
        relay = SettingsRelay(player)
        relay.receive({"type": "settingsSnapshot", "apps": [copy.deepcopy(APP)]})
        self.assertEqual(await relay.request({"operation": "get"}), {"apps": [APP]})
        for status in ("applied", "conflict", "rejected"):
            request = {"operation": "update", "requestId": "a" * 32, "body": UPDATE}
            pending = asyncio.create_task(relay.request(request))
            self.assertEqual(await sent.get(), {"type": "settingsUpdate", "requestId": "a" * 32, **UPDATE})
            result = {"type": "settingsUpdateResult", "requestId": "a" * 32, "status": status, "app": APP}
            relay.receive(result)
            self.assertEqual(await pending, result)
        pending = asyncio.create_task(relay.request(request))
        await sent.get()
        relay.disconnect()
        with self.assertRaises(RuntimeError):
            await pending
        with self.assertRaises(RuntimeError):
            await relay.request({"operation": "get"})
        self.assertEqual(relay.pending, {})

    async def test_stdio_response_does_not_leak_exception_details(self):
        player = SimpleNamespace(_websocket=None)
        relay = SettingsRelay(player)
        reader = asyncio.StreamReader()
        reader.feed_data((json.dumps({"operation": "get", "requestId": "a" * 32}) + "\n[]\n").encode())
        reader.feed_eof()
        output = []
        await relay.serve(reader, output.append)
        self.assertEqual(json.loads(output[0][len(PREFIX):]),
                         {"requestId": "a" * 32, "error": "settings_unavailable"})
        self.assertEqual(len(output), 2)

    async def test_expired_queued_update_is_not_sent_to_receiver(self):
        player = SimpleNamespace(_websocket=object(), _send=AsyncMock())
        relay = SettingsRelay(player)
        relay.receive({"type": "settingsSnapshot", "apps": [APP]})
        reader = asyncio.StreamReader()
        reader.feed_data((json.dumps({"operation": "update", "requestId": "b" * 32,
                                     "expiresAt": time.monotonic() - 1, "body": UPDATE}) + "\n").encode())
        reader.feed_eof()
        output = []
        await relay.serve(reader, output.append)
        player._send.assert_not_awaited()
        self.assertEqual(json.loads(output[0][len(PREFIX):])["error"], "settings_unavailable")

    def test_update_envelope_is_bounded_and_preserves_typed_values(self):
        self.assertEqual(validate_update(UPDATE), UPDATE)
        for body in (None, {}, dict(UPDATE, expectedRevision=True), dict(UPDATE, changes={}),
                     dict(UPDATE, changes={"key": []}), dict(UPDATE, expectedRevision=-1),
                     dict(UPDATE, changes={"key": float("nan")})):
            with self.assertRaises(ValueError):
                validate_update(body)


class SettingsManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.manager = RouteManager(RouteStore(self.directory.name))
        self.route = Route.parse({"id": str(uuid.uuid4()), "name": "Speaker", "backend": "mpv", "enabled": True})
        self.manager.routes = [self.route]
        self.manager.store.save([self.route])
        self.before = self.manager.store.path.read_bytes()
        self.requests = asyncio.Queue()
        sent = self.requests
        class Writer:
            def write(self, data):
                sent.put_nowait(json.loads(data))
            async def drain(self):
                pass
        self.manager.processes[self.route.id] = SimpleNamespace(returncode=None, stdin=Writer())

    async def test_real_stdio_process_roundtrip_uses_receiver_acknowledgement(self):
        code = """
import asyncio, copy
from cast_audio_lab.settings_ipc import SettingsRelay
app = %r
class Player:
    _websocket = object()
    async def _send(self, message):
        assert message['type'] == 'settingsUpdate'
        app['revision'] += 1
        app['settings'][0]['value'] = message['changes']['web_volume_compatibility']
        relay.receive({'type': 'settingsUpdateResult', 'requestId': message['requestId'],
                       'status': 'applied', 'app': copy.deepcopy(app)})
relay = SettingsRelay(Player())
relay.receive({'type': 'settingsSnapshot', 'apps': [copy.deepcopy(app)]})
asyncio.run(relay.run_stdio())
""" % APP
        child = await asyncio.create_subprocess_exec(sys.executable, "-c", code,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        self.manager.processes[self.route.id] = child
        pump = asyncio.create_task(self.manager._drain(child.stdout, logging.NullHandler(), self.route.id))
        try:
            snapshot = await self.manager.settings_request(self.route.id)
            self.assertEqual(snapshot, {"apps": [APP]})
            result = await self.manager.settings_request(self.route.id, UPDATE)
            self.assertEqual(result["status"], "applied")
            self.assertEqual(result["app"]["revision"], 3)
            self.assertFalse(result["app"]["settings"][0]["value"])
            self.assertEqual((await self.manager.settings_request(self.route.id))["apps"], [result["app"]])
        finally:
            child.stdin.close()
            await asyncio.wait_for(child.wait(), 3)
            await pump
        self.assertEqual(child.returncode, 0)
        self.assertEqual(self.manager.store.path.read_bytes(), self.before)

    async def test_route_scoped_replies_and_process_death_cleanup(self):
        task = asyncio.create_task(self.manager.settings_request(self.route.id, UPDATE))
        request = await self.requests.get()
        result = {"status": "applied", "app": APP}
        reply = json.dumps({"requestId": request["requestId"], "result": result})
        self.manager._settings_response("different-route", reply)
        self.assertFalse(task.done())
        # IPC responses bypass private logs as well as shared diagnostics.
        reader = asyncio.StreamReader()
        reader.feed_data((PREFIX + reply + "\n").encode()); reader.feed_eof()
        handler = logging.Handler()
        handler.emit = lambda record: self.fail("settings response entered log")
        await self.manager._drain(reader, handler, self.route.id)
        self.assertEqual(await task, result)
        self.assertEqual(self.manager.store.path.read_bytes(), self.before)
        task = asyncio.create_task(self.manager.settings_request(self.route.id))
        await self.requests.get()
        self.manager._settings_disconnected(self.route.id)
        with self.assertRaises(RuntimeError):
            await task
        self.assertEqual(self.manager.settings_pending, {})

    async def test_timeout_cleans_pending_without_replay(self):
        with patch("cast_audio_lab.route_manager.SETTINGS_TIMEOUT", .01):
            with self.assertRaises(RuntimeError):
                await self.manager.settings_request(self.route.id, UPDATE)
        self.assertEqual(self.manager.settings_pending, {})
        self.assertEqual(self.requests.qsize(), 1)

    async def test_http_roundtrip_conflicts_validation_origin_and_offline(self):
        self.manager.start = AsyncMock()
        self.manager.close = AsyncMock()
        client = TestClient(TestServer(create_app(self.manager)))
        self.addAsyncCleanup(client.close)
        await client.start_server()
        endpoint = f"/api/routes/{self.route.id}/settings"
        async def respond(result):
            request = await self.requests.get()
            self.manager._settings_response(self.route.id, json.dumps({"requestId": request["requestId"], "result": result}))
            return request
        responder = asyncio.create_task(respond({"apps": [APP]}))
        response = await client.get(endpoint)
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), {"apps": [APP]})
        self.assertEqual((await responder)["operation"], "get")
        for status, code in (("applied", 200), ("conflict", 409), ("rejected", 400)):
            responder = asyncio.create_task(respond({"status": status, "app": APP}))
            response = await client.patch(endpoint, json=UPDATE)
            self.assertEqual(response.status, code)
            self.assertEqual((await responder)["body"], UPDATE)
        self.assertEqual((await client.patch(endpoint, json={})).status, 400)
        self.assertEqual((await client.patch(endpoint, json=UPDATE, headers={"Origin": "http://untrusted"})).status, 403)
        self.assertEqual((await client.get("/api/routes/unknown/settings")).status, 404)
        self.manager._settings_disconnected(self.route.id)
        self.assertEqual((await client.get(endpoint)).status, 503)
        self.assertEqual(self.manager.store.path.read_bytes(), self.before)
