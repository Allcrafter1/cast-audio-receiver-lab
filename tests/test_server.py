import tempfile
import unittest
from pathlib import Path

from cast_audio_lab.backend import NullAudioBackend
from research.legacy_python_receiver.legacy_cast_receiver.auth import (
    RejectingAuthProvider,
)
from research.legacy_python_receiver.legacy_cast_receiver.server import CastAudioServer
from research.legacy_python_receiver.legacy_cast_receiver.tls import create_tls_identity


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_tls_server_can_start_and_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = create_tls_identity(Path(directory), "Cast Audio Test")
            server = CastAudioServer(
                "Cast Audio Test",
                "127.0.0.1",
                0,
                identity,
                NullAudioBackend(),
                RejectingAuthProvider(),
            )
            try:
                await server.start()
            except OSError as exc:
                self.skipTest(f"local socket binding unavailable: {exc}")
            self.assertIsNotNone(server._server)
            self.assertTrue(server._server.sockets)
            await server.close()


if __name__ == "__main__":
    unittest.main()
