"""Own the Cast frontend and speaker manager as one runtime.

The supervisor contains no playback logic.  Its only job is deterministic
startup order, signal handling and bounded child-process cleanup so OCI, Linux
services and Home Assistant can run the same application entrypoint.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
from pathlib import Path
import signal
import sys


class RuntimeSupervisor:
    def __init__(
        self,
        frontend_command: list[str],
        manager_command: list[str],
        *,
        bridge_host: str = "127.0.0.1",
        bridge_port: int = 8010,
        startup_timeout: float = 30.0,
        spawn=None,
        probe=None,
    ) -> None:
        self.frontend_command = frontend_command
        self.manager_command = manager_command
        self.bridge_host = bridge_host
        self.bridge_port = bridge_port
        self.startup_timeout = startup_timeout
        self.spawn = spawn or asyncio.create_subprocess_exec
        self.probe = probe or self._probe_bridge
        self.frontend = None
        self.manager = None
        self.stop_event = asyncio.Event()

    async def _probe_bridge(self) -> bool:
        try:
            reader, writer = await asyncio.open_connection(
                self.bridge_host, self.bridge_port
            )
            del reader
            writer.close()
            await writer.wait_closed()
            return True
        except OSError:
            return False

    async def _spawn(self, command: list[str]):
        return await self.spawn(
            *command,
            stdin=asyncio.subprocess.DEVNULL,
            start_new_session=True,
        )

    async def _wait_ready(self) -> None:
        async with asyncio.timeout(self.startup_timeout):
            while True:
                if self.frontend.returncode is not None:
                    raise RuntimeError(
                        f"Cast frontend exited during startup ({self.frontend.returncode})"
                    )
                if await self.probe():
                    return
                await asyncio.sleep(0.1)

    async def run(self) -> int:
        self.frontend = await self._spawn(self.frontend_command)
        try:
            await self._wait_ready()
            self.manager = await self._spawn(self.manager_command)
            frontend_wait = asyncio.create_task(self.frontend.wait())
            manager_wait = asyncio.create_task(self.manager.wait())
            stop_wait = asyncio.create_task(self.stop_event.wait())
            done, pending = await asyncio.wait(
                {frontend_wait, manager_wait, stop_wait},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if stop_wait in done:
                return 0
            if frontend_wait in done:
                return frontend_wait.result() or 1
            return manager_wait.result() or 1
        finally:
            await self.shutdown()

    def request_stop(self) -> None:
        self.stop_event.set()

    async def _stop_process(self, process, *, graceful: float = 10.0) -> None:
        if process is None or process.returncode is not None:
            return
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGINT)
        try:
            await asyncio.wait_for(process.wait(), graceful)
            return
        except TimeoutError:
            pass
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), 3.0)
            return
        except TimeoutError:
            pass
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.wait()

    async def shutdown(self) -> None:
        # Manager first: it owns adapters, decoders and AirPlay transports.
        await self._stop_process(self.manager)
        await self._stop_process(self.frontend)


def default_data_dir() -> Path:
    state = os.environ.get("XDG_STATE_HOME")
    if state:
        return Path(state) / "cast-audio-receiver"
    return Path.home() / ".local" / "state" / "cast-audio-receiver"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", default="vibecast")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--certs", type=Path)
    parser.add_argument("--model", default="Audio Speaker")
    parser.add_argument("--bridge-port", type=int, default=8010, help=argparse.SUPPRESS)
    parser.add_argument("--web-host", default="0.0.0.0", help=argparse.SUPPRESS)
    parser.add_argument("--web-port", type=int, default=8788)
    parser.add_argument("--artwork-public-url")
    parser.add_argument("--ha-ingress", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ingress-port", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--cliairplay", default="cliairplay", help=argparse.SUPPRESS)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--startup-timeout", type=float, default=30.0, help=argparse.SUPPRESS)
    return parser


def runtime_commands(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    data_dir = args.data_dir.resolve()
    frontend_dir = data_dir / "frontend"
    manager_dir = data_dir / "speakers"
    frontend_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    manager_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(frontend_dir, 0o700)
    os.chmod(manager_dir, 0o700)
    certs = (args.certs or data_dir / "private" / "certs.json").resolve()
    frontend = [
        args.frontend,
        "--certs",
        str(certs),
        "--data-dir",
        str(frontend_dir),
        "--model",
        args.model,
        "--bind-host",
        "0.0.0.0",
        "--player-port",
        str(args.bridge_port),
        "--log-level",
        args.log_level.lower(),
    ]
    manager = [
        sys.executable,
        "-m",
        "cast_audio_lab.management",
        "--state-dir",
        str(manager_dir),
        "--bridge",
        f"ws://127.0.0.1:{args.bridge_port}/player",
        "--host",
        args.web_host,
        "--port",
        str(args.web_port),
        "--cliairplay",
        args.cliairplay,
    ]
    if args.artwork_public_url:
        manager += ["--artwork-public-url", args.artwork_public_url]
    if getattr(args, "ha_ingress", False):
        manager.append("--ha-ingress")
        ingress_port = getattr(args, "ingress_port", None)
        if ingress_port is not None:
            manager += ["--ingress-port", str(ingress_port)]
    return frontend, manager


async def run(args: argparse.Namespace) -> int:
    frontend, manager = runtime_commands(args)
    supervisor = RuntimeSupervisor(
        frontend,
        manager,
        bridge_port=args.bridge_port,
        startup_timeout=args.startup_timeout,
    )
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, supervisor.request_stop)
    return await supervisor.run()


def main() -> None:
    args = build_parser().parse_args()
    ports = [args.web_port, args.bridge_port]
    if args.ingress_port is not None:
        ports.append(args.ingress_port)
    if any(not 1 <= port <= 65535 for port in ports):
        raise SystemExit("ports must be between 1 and 65535")
    try:
        code = asyncio.run(run(args))
    except (OSError, RuntimeError, TimeoutError) as error:
        print(f"runtime failed: {error}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
