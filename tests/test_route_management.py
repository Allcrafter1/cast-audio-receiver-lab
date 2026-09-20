import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock
import uuid

from cast_audio_lab.routes import Route, RouteStore, validate_routes
from cast_audio_lab.route_manager import RouteManager
from cast_audio_lab.airplay_discovery import AirPlayService, DiscoveredAirPlayDevice

try:
    from aiohttp.test_utils import TestClient, TestServer
    from cast_audio_lab.management import create_app
except ImportError:
    TestClient = None


def route(**changes):
    return Route.parse(dict(id=str(uuid.uuid4()), name="Test speaker", backend="mpv", **changes))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = RouteStore(self.temp.name)

    def test_roundtrip_and_stable_identity(self):
        original = route()
        self.store.save([original])
        changed = replace(original, name="Renamed")
        self.store.save([changed])
        self.assertEqual(self.store.load(), [changed])
        self.assertEqual(changed.id, original.id)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_failed_save_preserves_previous(self):
        original = route()
        self.store.save([original])
        with patch("cast_audio_lab.routes.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                self.store.save([replace(original, name="new")])
        self.assertEqual(self.store.load(), [original])
        self.assertEqual(list(Path(self.temp.name).glob(".config-*")), [])

    def test_exclusive_owner(self):
        self.store.acquire()
        self.addCleanup(self.store.release)
        with self.assertRaises(ValueError):
            RouteStore(self.temp.name).acquire()
        with self.assertRaises(ValueError):
            self.store.acquire()

    def test_validation(self):
        original = route()
        for bad in (dict(original.private(), enabled=1), dict(original.private(), command="sh"),
                    dict(original.private(), name="bad\nname")):
            with self.assertRaises(ValueError):
                Route.parse(bad)
        with self.assertRaises(ValueError):
            validate_routes([original.private(), original.private()])


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RouteStore(self.temp.name)
        self.children = []

        async def spawn(*args, **kwargs):
            child = await asyncio.create_subprocess_exec(sys.executable, "-c",
                "import time; time.sleep(60)", **kwargs)
            self.children.append(child)
            return child

        self.manager = RouteManager(self.store, spawn=spawn)
        await self.manager.start()

    async def asyncTearDown(self):
        await self.manager.close()
        self.assertTrue(all(p.returncode is not None for p in self.children))
        self.temp.cleanup()

    async def wait_running(self, count):
        async with asyncio.timeout(5):
            while sum(s["state"] == "running" for s in self.manager.states.values()) != count:
                await asyncio.sleep(.01)

    async def test_independent_routes_rename_disable(self):
        first, second = route(enabled=True), route(enabled=True)
        await self.manager.replace([first, second])
        await self.wait_running(2)
        first_pid = self.manager.states[first.id]["pid"]
        second_pid = self.manager.states[second.id]["pid"]
        await self.manager.replace([replace(first, name="renamed"), second])
        await self.wait_running(2)
        self.assertNotEqual(self.manager.states[first.id]["pid"], first_pid)
        self.assertEqual(self.manager.states[second.id]["pid"], second_pid)
        await self.manager.replace([replace(first, enabled=False), second])
        await self.wait_running(1)
        self.assertEqual(self.manager.public()[0]["process"]["state"], "disabled")

    async def test_crash_restarts_same_identity(self):
        first = route(enabled=True)
        await self.manager.replace([first])
        await self.wait_running(1)
        old = self.children[0]
        old.kill()
        async with asyncio.timeout(5):
            while len(self.children) < 2:
                await asyncio.sleep(.02)
        await self.wait_running(1)
        self.assertEqual(self.manager.routes[0].id, first.id)
        self.assertNotEqual(self.manager.states[first.id]["pid"], old.pid)

    async def test_failed_cleanup_does_not_start_replacement(self):
        first = route(enabled=True)
        await self.manager.replace([first])
        await self.wait_running(1)
        original_stop = self.manager._stop
        async def uncertain_stop(process):
            await original_stop(process)
            raise RuntimeError("simulated uncertain cleanup")
        with patch.object(self.manager, "_stop", uncertain_stop):
            with self.assertRaises(RuntimeError):
                await self.manager.replace([replace(first, name="changed")])
        self.assertEqual(len(self.children), 1)
        self.assertEqual(self.manager.states[first.id]["state"], "error")

    async def test_health_and_support_are_bounded_and_redacted(self):
        first = route(enabled=True)
        await self.manager.replace([first])
        await self.wait_running(1)
        with patch.object(self.manager, "_bridge_reachable", AsyncMock(return_value=True)):
            health = await self.manager.health()
        self.assertTrue(health["ready"])
        self.assertEqual(health["running_routes"], 1)
        support = self.manager.support_snapshot(version="test")
        serialized = json.dumps(support)
        self.assertNotIn(first.id, serialized)
        self.assertNotIn(first.name, serialized)
        self.assertNotIn("pid", serialized.lower())
        self.assertEqual(support["routes"][0]["backend"], "mpv")


@unittest.skipUnless(TestClient, "management extra not installed")
class HTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RouteStore(self.temp.name)
        self.manager = RouteManager(self.store)
        service = AirPlayService("_raop._tcp.local.", "device", "receiver.local", "192.0.2.1", 6000,
                                 {"secret": "private-test-value"})
        async def discovery(**kwargs):
            return [DiscoveredAirPlayDevice("AA:BB:CC:DD:EE:FF", "Target", raop=service)]
        self.client = TestClient(TestServer(create_app(self.manager, discover=discovery)))
        await self.client.start_server()
        self.headers = {"Host": "localhost:8788"}

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def test_security_boundaries(self):
        for headers, status in (({"Host": "192.168.1.50:8788"}, 200),
                                ({"Host": "receiver-host:8788"}, 200),
                                (dict(self.headers, Origin="http://evil.example"), 403)):
            response = await self.client.get("/api/routes", headers=headers)
            self.assertEqual(response.status, status)
        response = await self.client.post("/api/routes", headers=self.headers,
            data="x" * 40000)
        self.assertEqual(response.status, 415)
        response = await self.client.post("/api/routes", headers=self.headers,
            json={"name": "x" * 40000, "backend": "mpv"})
        self.assertEqual(response.status, 413)

    async def test_ha_ingress_is_explicit_and_frameable(self):
        other_store = RouteStore(Path(self.temp.name) / "ingress")
        other = RouteManager(other_store)
        ingress = TestClient(TestServer(create_app(other, discover=AsyncMock(return_value=[]), ha_ingress=True)))
        await ingress.start_server()
        try:
            response = await ingress.get(
                "/api/routes",
                headers={
                    "Origin": "http://homeassistant.local:8123",
                    "Sec-Fetch-Site": "cross-site",
                    "X-Ingress-Path": "/api/hassio_ingress/token",
                },
            )
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        finally:
            await ingress.close()

    async def test_processed_cover_readable_cross_origin_but_processing_is_not(self):
        async def convert(cache, source):
            ident = 'a' * 32
            (cache.directory / (ident + '.jpg')).write_bytes(b'jpeg fixture')
            cache.entries[source] = (ident, cache.clock() + cache.ttl)
            return ident
        with patch('cast_audio_lab.management.ArtworkCache.prepare', convert):
            response = await self.client.post('/api/artwork', json={'source': 'https://example.test/art'})
            self.assertEqual(response.status, 200)
            path = (await response.json())['path']
        headers = {'Origin': 'http://homeassistant.local:8123', 'Sec-Fetch-Site': 'cross-site'}
        response = await self.client.get(path, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.read(), b'jpeg fixture')
        self.assertEqual(response.content_type, 'image/jpeg')
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        response = await self.client.post('/api/artwork', headers=headers,
            json={'source': 'https://example.test/art'})
        self.assertEqual(response.status, 403)
        response = await self.client.get('/artwork/' + 'b' * 32 + '.jpg', headers=headers)
        self.assertEqual(response.status, 404)

    async def test_disabled_creation_rename_persistence(self):
        response = await self.client.post("/api/routes", headers=self.headers,
            json={"name": "Kitchen", "backend": "mpv"})
        self.assertEqual(response.status, 201)
        item = await response.json()
        self.assertFalse(item["enabled"])
        response = await self.client.patch("/api/routes/"+item["id"], headers=self.headers,
            json={"name": "New kitchen"})
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())["id"], item["id"])
        self.assertEqual(self.store.load()[0].name, "New kitchen")
        self.assertEqual(self.manager.tasks, {})

    async def test_dlna_target_correction_preserves_route_identity(self):
        response = await self.client.post("/api/routes", json={"name": "TV", "backend": "dlna",
            "target": {"description_url": "http://192.0.2.2"}})
        ident = (await response.json())["id"]
        url = "http://192.0.2.2:52235/dmr/device.xml"
        response = await self.client.patch("/api/routes/" + ident,
            json={"target": {"description_url": url}})
        self.assertEqual(response.status, 200)
        item = await response.json()
        self.assertEqual(item["id"], ident)
        self.assertEqual(item["target"]["description_url"], url)
        self.assertEqual(self.store.load()[0].target["port"], 52235)
        response = await self.client.patch("/api/routes/" + ident,
            json={"target": {"description_url": "file:///etc/passwd"}})
        self.assertEqual(response.status, 400)
        self.assertEqual(self.store.load()[0].target["description_url"], url)

    async def test_dlna_discovery_import_preserves_backend_and_starts_disabled(self):
        store = RouteStore(Path(self.temp.name) / "dlna-discovery")
        manager = RouteManager(store)
        discovery = AsyncMock(return_value=[{"name": "TV", "target": {
            "description_url": "http://192.0.2.2:123/device.xml", "device_id": "uuid:tv"}}])
        client = TestClient(TestServer(create_app(manager, discover_renderers=discovery)))
        await client.start_server()
        try:
            response = await client.post("/api/scan/dlna", json={})
            self.assertEqual(response.status, 200)
            candidate = (await response.json())["candidates"][0]
            response = await client.post("/api/routes", json={"name": "TV", "candidate_id": candidate["candidate_id"]})
            self.assertEqual(response.status, 201)
            created = await response.json()
            self.assertEqual(created["backend"], "dlna")
            self.assertFalse(created["enabled"])
            response = await client.post("/api/scan/dlna", json={})
            self.assertTrue((await response.json())["candidates"][0]["already_imported"])
            self.assertEqual(len(store.load()), 1)
        finally:
            await client.close()

    async def test_local_duplicate_rejected_then_delete_allows_replacement(self):
        first = await self.client.post("/api/routes", headers=self.headers,
            json={"name":"Local", "backend":"mpv"})
        ident = (await first.json())["id"]
        second = await self.client.post("/api/routes", headers=self.headers,
            json={"name":"Other name", "backend":"mpv"})
        self.assertEqual(second.status, 409)
        deleted = await self.client.delete("/api/routes/"+ident, headers=self.headers, json={})
        self.assertEqual(deleted.status, 200)
        self.assertEqual(self.store.load(), [])
        repeated = await self.client.delete("/api/routes/"+ident, headers=self.headers, json={})
        self.assertEqual(repeated.status, 404)
        replacement = await self.client.post("/api/routes", headers=self.headers,
            json={"name":"Replacement", "backend":"mpv"})
        self.assertEqual(replacement.status, 201)

    async def test_manual_dlna_and_sonos_outputs_are_disabled_and_validated(self):
        dlna = await self.client.post(
            "/api/routes", headers=self.headers,
            json={"name": "Renderer", "backend": "dlna", "target": {
                "description_url": "http://192.168.1.20:49152/device.xml"}},
        )
        self.assertEqual(dlna.status, 201)
        self.assertFalse((await dlna.json())["enabled"])
        sonos = await self.client.post(
            "/api/routes", headers=self.headers,
            json={"name": "Sonos", "backend": "sonos", "target": {
                "host": "192.168.1.21"}},
        )
        self.assertEqual(sonos.status, 201)
        invalid = await self.client.post(
            "/api/routes", headers=self.headers,
            json={"name": "Public", "backend": "sonos", "target": {
                "host": "8.8.8.8"}},
        )
        self.assertEqual(invalid.status, 400)

    async def test_delete_airplay_removes_only_its_target_file(self):
        response = await self.client.post("/api/scan", headers=self.headers, json={})
        candidate = (await response.json())["candidates"][0]
        response = await self.client.post("/api/routes", headers=self.headers,
            json={"name":"Target", "candidate_id":candidate["candidate_id"]})
        ident = (await response.json())["id"]
        self.manager.command(self.manager.routes[0])
        target = self.store.directory / f"target-{ident}.json"
        self.assertTrue(target.exists())
        response = await self.client.delete("/api/routes/"+ident, headers=self.headers, json={})
        self.assertEqual(response.status, 200)
        self.assertFalse(target.exists())
        self.assertEqual(self.store.load(), [])

    async def test_assets_and_private_paths(self):
        response = await self.client.get("/", headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertIn("default-src 'none'", response.headers["Content-Security-Policy"])
        html = await response.text()
        self.assertNotIn('id="login"', html)
        self.assertNotIn('id="admin" hidden', html)
        response = await self.client.get("/routes.json", headers=self.headers)
        self.assertEqual(response.status, 404)

    async def test_health_status_and_support_endpoints(self):
        with patch.object(self.manager, "_bridge_reachable", AsyncMock(return_value=True)):
            response = await self.client.get("/health", headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertTrue((await response.json())["ready"])
        response = await self.client.get("/status", headers=self.headers)
        self.assertEqual(response.status, 200)
        self.assertIn("version", await response.json())
        response = await self.client.get("/api/support", headers=self.headers)
        self.assertEqual(response.status, 200)
        text = await response.text()
        self.assertNotIn("private-test-value", text)
        self.assertNotIn(str(self.store.directory), text)

    async def test_scan_import_hides_private_fields_and_rejects_duplicates(self):
        response = await self.client.post("/api/scan", headers=self.headers, json={})
        body = await response.json()
        self.assertNotIn("private-test-value", json.dumps(body))
        candidate = body["candidates"][0]
        response = await self.client.post("/api/routes", headers=self.headers,
            json={"name": "Imported", "candidate_id": candidate["candidate_id"]})
        self.assertEqual(response.status, 201)
        self.assertNotIn("private-test-value", await response.text())
        self.assertEqual(self.store.load()[0].target["txt"]["secret"], "private-test-value")
        response = await self.client.post("/api/routes", headers=self.headers,
            json={"name": "Duplicate", "candidate_id": candidate["candidate_id"]})
        self.assertEqual(response.status, 400)
        response = await self.client.post("/api/scan", headers=self.headers, json={})
        self.assertTrue((await response.json())["candidates"][0]["already_imported"])


if __name__ == "__main__":
    unittest.main()
