# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import replace
import tempfile
import unittest
import uuid
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer

from cast_audio_lab.management import create_app
from cast_audio_lab.route_manager import RouteManager
from cast_audio_lab.routes import Route, RouteStore


class ManagementTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_after_persist_keeps_lock_until_reconciliation_finishes(self):
        await self.check_disconnected_transaction("PATCH")

    async def test_disconnect_during_delete_still_cleans_private_target(self):
        await self.check_disconnected_transaction("DELETE")

    async def check_disconnected_transaction(self, method):
        with tempfile.TemporaryDirectory() as directory:
            store = RouteStore(directory)
            original = Route(str(uuid.uuid4()), "Before", "mpv", enabled=True)
            store.save([original])
            manager = RouteManager(store)
            private_target = store.directory / f"target-{original.id}.json"
            private_target.write_text('{"synthetic":"private configuration"}')
            entered, release, finished = asyncio.Event(), asyncio.Event(), asyncio.Event()
            async def adapter(_route):
                try:
                    await asyncio.Future()
                finally:
                    entered.set()
                    await release.wait()
                    finished.set()
            # Keep the real RouteManager.replace persistence/reconciliation
            # path; only replace its external adapter process with a gate.
            manager._run = adapter
            async with TestClient(TestServer(create_app(manager), handler_cancellation=True)) as client:
                request = asyncio.create_task(client.request(method, f"/api/routes/{original.id}",
                    json={"name": "After"} if method == "PATCH" else {}))
                try:
                    await asyncio.wait_for(entered.wait(), 1)
                    request.cancel()
                    await asyncio.gather(request, return_exceptions=True)
                    await asyncio.sleep(.05)
                    self.assertTrue(manager.lock.locked(), "cancelled request released transaction lock before reconciliation")
                    release.set()
                    await asyncio.wait_for(finished.wait(), 1)
                    async with manager.lock:
                        self.assertEqual(manager.routes, store.load())
                        if method == "PATCH":
                            self.assertEqual(manager.routes[0].name, "After")
                        else:
                            self.assertEqual(manager.routes, [])
                            self.assertFalse(private_target.exists())
                finally:
                    release.set()

    async def test_failed_atomic_save_leaves_disk_and_running_configuration_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RouteStore(directory)
            original = Route(str(uuid.uuid4()), "Before", "mpv")
            store.save([original])
            manager = RouteManager(store)
            async with TestClient(TestServer(create_app(manager))) as client:
                with patch("cast_audio_lab.routes.os.replace", side_effect=OSError("disk unavailable")):
                    response = await client.patch(f"/api/routes/{original.id}", json={"name": "After"})
                self.assertEqual(response.status, 503)
                self.assertEqual(manager.routes, [original])
                self.assertEqual(store.load(), [original])
                response = await client.patch(f"/api/routes/{original.id}", json={"name": "Recovered"})
                self.assertEqual(response.status, 200)
                self.assertEqual(store.load(), [replace(original, name="Recovered")])
