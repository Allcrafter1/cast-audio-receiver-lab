import argparse
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cast_audio_lab.runtime import RuntimeSupervisor, runtime_commands


class FakeProcess:
    next_pid = 8000

    def __init__(self):
        self.pid = FakeProcess.next_pid
        FakeProcess.next_pid += 1
        self.returncode = None
        self.waiter = asyncio.Event()

    async def wait(self):
        await self.waiter.wait()
        return self.returncode

    def exit(self, code=0):
        self.returncode = code
        self.waiter.set()


class RuntimeCommandTests(unittest.TestCase):
    def test_defaults_keep_private_bundle_outside_release(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                data_dir=Path(directory), certs=None, frontend="/opt/vibecast",
                model="Audio Speaker", bridge_port=8010, web_host="0.0.0.0",
                web_port=8788, cliairplay="/opt/cliairplay",
                artwork_public_url="http://192.0.2.2:8788", log_level="INFO",
                ha_ingress=True, ingress_port=43124,
            )
            frontend, manager = runtime_commands(args)
        self.assertIn(str(Path(directory) / "private" / "certs.json"), frontend)
        self.assertIn("ws://127.0.0.1:8010/player", manager)
        self.assertIn("http://192.0.2.2:8788", manager)
        self.assertIn("43124", manager)


class RuntimeSupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_order_and_graceful_reverse_shutdown(self):
        processes = []

        async def spawn(*_command, **_kwargs):
            process = FakeProcess()
            processes.append(process)
            return process

        async def probe():
            return True

        supervisor = RuntimeSupervisor(
            ["frontend"], ["manager"], spawn=spawn, probe=probe
        )

        async def fake_stop(process, *, graceful=10.0):
            if process and process.returncode is None:
                process.exit()
            stopped.append(process)

        stopped = []
        with patch.object(supervisor, "_stop_process", fake_stop):
            task = asyncio.create_task(supervisor.run())
            async with asyncio.timeout(1):
                while len(processes) < 2:
                    await asyncio.sleep(0)
            supervisor.request_stop()
            self.assertEqual(await task, 0)
        self.assertEqual(stopped, [processes[1], processes[0]])

    async def test_frontend_failure_prevents_manager_start(self):
        frontend = FakeProcess()
        frontend.exit(7)
        spawned = []

        async def spawn(*_command, **_kwargs):
            spawned.append(frontend)
            return frontend

        supervisor = RuntimeSupervisor(
            ["frontend"], ["manager"], spawn=spawn, probe=lambda: asyncio.sleep(0, False)
        )
        with patch.object(supervisor, "_stop_process", return_value=None):
            with self.assertRaises(RuntimeError):
                await supervisor.run()
        self.assertEqual(len(spawned), 1)


if __name__ == "__main__":
    unittest.main()
