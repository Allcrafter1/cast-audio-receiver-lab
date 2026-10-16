# SPDX-License-Identifier: MPL-2.0
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from aiohttp.test_utils import TestClient, TestServer

from cast_audio_lab.management import create_app
from cast_audio_lab.output_registry import validate_output_target
from cast_audio_lab.route_manager import RouteManager
from cast_audio_lab.routes import RouteStore


class ManagementReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_other_protocol_scan_preserves_unexpired_import_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = RouteManager(RouteStore(Path(directory)))
            dlna = AsyncMock(return_value=[{"name": "Renderer", "target": {
                "description_url": "http://192.168.1.20/device.xml", "device_id": "renderer"}}])
            app = create_app(manager, discover=AsyncMock(return_value=[]), discover_renderers=dlna)
            async with TestClient(TestServer(app)) as client:
                response = await client.post("/api/scan/dlna", json={})
                candidate = (await response.json())["candidates"][0]
                response = await client.post("/api/scan", json={})
                self.assertEqual(response.status, 200)
                response = await client.post("/api/routes", json={
                    "name": "Renderer", "candidate_id": candidate["candidate_id"]})
                self.assertEqual(response.status, 201)
                self.assertEqual((await response.json())["backend"], "dlna")

    def test_dlna_rejects_zero_port_instead_of_saving_unplayable_target(self):
        with self.assertRaises(ValueError):
            validate_output_target("dlna", {"description_url": "http://192.168.1.20:0/device.xml"})
