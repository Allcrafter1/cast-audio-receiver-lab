"""Real local WebSocket regression; requires the existing [bridge] extra."""
import asyncio
import json
import unittest

try:
    from websockets.asyncio.server import serve
except ImportError:
    serve = None

from cast_audio_lab.backend import NullAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer, run_player


@unittest.skipIf(serve is None, "requires bridge extra")
class BridgeReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_abrupt_bridge_restart_stops_old_playback_and_registers_again(self):
        backend = NullAudioBackend()
        reconnected = asyncio.Event()
        registrations = []

        async def handler(socket):
            registrations.append(json.loads(await socket.recv()))
            if len(registrations) == 1:
                await socket.send(json.dumps({"type": "load", "sessionId": "old",
                    "media": {"streams": [{"url": "https://example.invalid/test"}], "autoplay": True}}))
                async with asyncio.timeout(3):
                    while backend.status().state != "PLAYING":
                        await asyncio.sleep(.01)
                socket.transport.abort()
            else:
                self.assertEqual(backend.status().state, "IDLE")
                reconnected.set()
                await socket.wait_closed()

        async with serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            player = VibecastAudioPlayer(f"ws://127.0.0.1:{port}", "stable-test", "Test", backend)
            task = asyncio.create_task(run_player(player))
            try:
                await asyncio.wait_for(reconnected.wait(), 5)
                self.assertEqual(len(registrations), 2)
                self.assertEqual(registrations[0]["player"], registrations[1]["player"])
                self.assertIsNone(player.session_id)
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
