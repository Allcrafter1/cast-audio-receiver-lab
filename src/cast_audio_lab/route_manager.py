"""Own only explicitly configured adapter processes, not the Rust frontend."""
import asyncio
import contextlib
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import sys
import time
from urllib.parse import urlsplit

from .output_registry import adapter_arguments


class RouteManager:
    def __init__(self, store, *, bridge="ws://127.0.0.1:8010/player", cliairplay="cliairplay", spawn=None):
        self.store, self.bridge, self.cliairplay = store, bridge, cliairplay
        self.spawn = spawn or asyncio.create_subprocess_exec
        self.routes = []
        self.tasks, self.states = {}, {}
        self.lock = asyncio.Lock()
        self.closed = False
        self.started_at = None
        self.artwork_endpoint = None
        self.artwork_public_url = None

    def command(self, route):
        argv = [sys.executable, "-m", "cast_audio_lab.vibecast_player", "--bridge", self.bridge,
                "--player-id", route.id, "--name="+route.name, "--backend", route.backend]
        if self.artwork_endpoint and self.artwork_public_url:
            argv += ['--artwork-endpoint', self.artwork_endpoint,
                     '--artwork-public-url', self.artwork_public_url]
        argv += adapter_arguments(
            route.backend, route, self.store.directory, self.cliairplay
        )
        return argv

    async def start(self):
        self.store.acquire()
        try:
            self.routes = self.store.load()
            self.started_at = time.monotonic()
            self._start_missing()
        except BaseException:
            self.store.release()
            raise

    def _start_missing(self):
        for route in self.routes:
            if route.enabled and route.id not in self.tasks:
                self.states[route.id] = {"state": "starting", "pid": None, "restarts": 0}
                self.tasks[route.id] = asyncio.create_task(self._run(route))

    async def replace(self, routes):
        # Called while lock is held by the API: persist before touching playback.
        if self.closed:
            raise RuntimeError("manager is shutting down")
        self.store.save(routes)
        wanted = {route.id: route for route in routes}
        previous = {route.id: route for route in self.routes}
        changed = [ident for ident in self.tasks if wanted.get(ident) != previous.get(ident)]
        for ident in changed:
            self.tasks[ident].cancel()
        results = await asyncio.gather(*(self.tasks[ident] for ident in changed), return_exceptions=True)
        if any(isinstance(result, Exception) for result in results):
            # Do not create a second adapter if ownership cleanup was uncertain.
            raise RuntimeError("adapter cleanup failed; restart requires operator inspection")
        for ident in changed:
            del self.tasks[ident]
            self.states.pop(ident, None)
        self.routes = routes
        self._start_missing()

    def public(self):
        return [dict(route.public(), process=self.states.get(route.id, {"state": "disabled", "pid": None, "restarts": 0}))
                for route in self.routes]

    async def _bridge_reachable(self, timeout=0.35):
        parsed = urlsplit(self.bridge)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname or not parsed.port:
            return False
        try:
            async with asyncio.timeout(timeout):
                reader, writer = await asyncio.open_connection(parsed.hostname, parsed.port)
            del reader
            writer.close()
            await writer.wait_closed()
            return True
        except (OSError, TimeoutError, ValueError):
            return False

    async def health(self):
        bridge_ready = await self._bridge_reachable()
        enabled = [route for route in self.routes if route.enabled]
        route_states = [self.states.get(route.id, {}).get("state") for route in enabled]
        routes_ready = all(state == "running" for state in route_states)
        manager_ready = self.started_at is not None and not self.closed
        return {
            "schema": 1,
            "ready": manager_ready and bridge_ready and routes_ready,
            "manager": "ready" if manager_ready else "stopped",
            "frontend_bridge": "ready" if bridge_ready else "unreachable",
            "enabled_routes": len(enabled),
            "running_routes": sum(state == "running" for state in route_states),
        }

    def status(self):
        uptime = 0.0 if self.started_at is None else max(0.0, time.monotonic() - self.started_at)
        routes = []
        for route in self.routes:
            process = self.states.get(route.id, {"state": "disabled", "restarts": 0})
            item = {
                "id": route.id,
                "name": route.name,
                "backend": route.backend,
                "enabled": route.enabled,
                "state": process.get("state", "unknown"),
                "restarts": int(process.get("restarts", 0)),
            }
            if process.get("error"):
                item["error"] = process["error"]
            if "exit_code" in process:
                item["exit_code"] = process["exit_code"]
            routes.append(item)
        return {"schema": 1, "uptime_seconds": round(uptime, 3), "routes": routes}

    def support_snapshot(self, *, version):
        """Return an allowlist-only diagnostic record safe for issue review.

        Route names, stable ids, endpoints, PIDs, media data, URLs and private
        target properties are intentionally absent.
        """
        routes = []
        for index, route in enumerate(self.routes, start=1):
            process = self.states.get(route.id, {"state": "disabled", "restarts": 0})
            item = {
                "route": index,
                "backend": route.backend,
                "enabled": route.enabled,
                "state": process.get("state", "unknown"),
                "restarts": int(process.get("restarts", 0)),
            }
            if process.get("error"):
                item["error"] = process["error"]
            if "exit_code" in process:
                item["exit_code"] = process["exit_code"]
            routes.append(item)
        return {
            "schema": 1,
            "application": {"name": "cast-audio-receiver-lab", "version": version},
            "runtime": {"python": sys.version.split()[0], "platform": sys.platform},
            "routes": routes,
        }

    async def _drain(self, stream, handler):
        while chunk := await stream.read(8192):
            record = logging.LogRecord("adapter", logging.INFO, "", 0,
                                       chunk.decode(errors="replace").rstrip(), (), None)
            handler.emit(record)

    async def _stop(self, process):
        # Each adapter gets its own process group; decoder descendants inherit it.
        for sig, timeout in ((signal.SIGINT, 8), (signal.SIGTERM, 2), (signal.SIGKILL, 2)):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, sig)
            if process.returncode is None:
                try:
                    await asyncio.wait_for(asyncio.shield(process.wait()), timeout)
                except TimeoutError:
                    continue
            # Parent may have exited leaving helpers in this owned group.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            return
        raise RuntimeError("owned adapter did not terminate")

    async def _run(self, route):
        restarts = 0
        while True:
            process = pump = handler = None
            started = time.monotonic()
            try:
                handler = RotatingFileHandler(self.store.directory / f"route-{route.id}.log",
                                              maxBytes=1024*1024, backupCount=1, encoding="utf-8")
                os.chmod(handler.baseFilename, 0o600)
                handler.setFormatter(logging.Formatter("%(message)s"))
                spawn = asyncio.create_task(self.spawn(*self.command(route), stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT, start_new_session=True))
                try:
                    process = await asyncio.shield(spawn)
                except asyncio.CancelledError:
                    process = await spawn
                    raise
                self.states[route.id] = {"state": "running", "pid": process.pid, "restarts": restarts}
                pump = asyncio.create_task(self._drain(process.stdout, handler))
                code = await process.wait()
                self.states[route.id] = {"state": "backoff", "pid": None, "restarts": restarts, "exit_code": code}
            except (OSError, ValueError):
                self.states[route.id] = {"state": "backoff", "pid": None, "restarts": restarts, "error": "adapter_start_failed"}
            finally:
                try:
                    if process:
                        await self._stop(process)
                except Exception:
                    self.states[route.id] = {"state": "error", "pid": process.pid if process else None,
                                             "restarts": restarts, "error": "adapter_cleanup_failed"}
                    raise
                finally:
                    if pump:
                        pump.cancel()
                        await asyncio.gather(pump, return_exceptions=True)
                    if handler:
                        handler.close()
            restarts = 0 if time.monotonic() - started > 60 else restarts + 1
            await asyncio.sleep(min(60, 2 ** min(restarts-1, 6)))

    async def close(self):
        async with self.lock:
            self.closed = True
            for task in self.tasks.values():
                task.cancel()
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
            self.tasks.clear()
            self.store.release()
