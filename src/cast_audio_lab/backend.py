"""Audio output backends."""

from __future__ import annotations

import asyncio
import os
import shlex
import signal
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    """Protocol-neutral media information passed to every output adapter."""

    title: str = ""
    artist: str = ""
    album: str = ""
    artwork_url: str = ""
    item_id: str = ""
    duration: float | None = None


@dataclass(slots=True)
class PlaybackStatus:
    state: str = "IDLE"
    url: str | None = None
    content_type: str = "audio/mpeg"
    current_time: float = 0.0
    volume: float = 1.0
    muted: bool = False
    idle_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ControlRequest:
    """A user action originating at the physical output device."""

    command: str
    position: float | None = None
    level: float | None = None
    muted: bool | None = None


StatusListener = Callable[[PlaybackStatus], Awaitable[None] | None]
ControlListener = Callable[[ControlRequest], Awaitable[None] | None]


class AudioBackend(Protocol):
    def add_status_listener(self, listener: StatusListener) -> None: ...

    def remove_status_listener(self, listener: StatusListener) -> None: ...

    def add_control_listener(self, listener: ControlListener) -> None: ...

    def remove_control_listener(self, listener: ControlListener) -> None: ...

    async def set_metadata(self, metadata: MediaMetadata) -> None: ...

    async def load(
        self, url: str, content_type: str, autoplay: bool, start_time: float
    ) -> None: ...

    async def play(self) -> None: ...

    async def pause(self) -> None: ...

    async def stop(self) -> None: ...

    async def seek(self, position: float) -> None: ...

    async def set_volume(self, level: float, muted: bool) -> None: ...

    def status(self) -> PlaybackStatus: ...

    async def shutdown(self) -> None: ...


class NullAudioBackend:
    """Stateful backend for protocol development and tests."""

    def __init__(self) -> None:
        self._status = PlaybackStatus()
        self.metadata = MediaMetadata()
        self._status_listeners: list[StatusListener] = []
        self._control_listeners: list[ControlListener] = []
        self._position_at_change = 0.0
        self._changed_at = time.monotonic()

    async def load(
        self, url: str, content_type: str, autoplay: bool, start_time: float
    ) -> None:
        self._status.url = url
        self._status.content_type = content_type
        self._status.idle_reason = None
        self._set_position(start_time)
        self._status.state = "PLAYING" if autoplay else "PAUSED"
        self._emit_status()

    async def set_metadata(self, metadata: MediaMetadata) -> None:
        self.metadata = metadata

    async def play(self) -> None:
        if self._status.url:
            self._set_position(self._current_position())
            self._status.state = "PLAYING"
            self._emit_status()

    async def pause(self) -> None:
        if self._status.state == "PLAYING":
            self._set_position(self._current_position())
            self._status.state = "PAUSED"
            self._emit_status()

    async def stop(self) -> None:
        self._set_position(0.0)
        self._status.state = "IDLE"
        self._status.idle_reason = "CANCELLED"
        self._emit_status()

    async def seek(self, position: float) -> None:
        self._set_position(max(0.0, position))
        self._emit_status()

    async def set_volume(self, level: float, muted: bool) -> None:
        self._status.volume = max(0.0, min(1.0, level))
        self._status.muted = muted
        self._emit_status()

    def add_status_listener(self, listener: StatusListener) -> None:
        if listener not in self._status_listeners:
            self._status_listeners.append(listener)

    def remove_status_listener(self, listener: StatusListener) -> None:
        if listener in self._status_listeners:
            self._status_listeners.remove(listener)

    def add_control_listener(self, listener: ControlListener) -> None:
        if listener not in self._control_listeners:
            self._control_listeners.append(listener)

    def remove_control_listener(self, listener: ControlListener) -> None:
        if listener in self._control_listeners:
            self._control_listeners.remove(listener)

    def status(self) -> PlaybackStatus:
        status = PlaybackStatus(
            state=self._status.state,
            url=self._status.url,
            content_type=self._status.content_type,
            current_time=self._current_position(),
            volume=self._status.volume,
            muted=self._status.muted,
            idle_reason=self._status.idle_reason,
        )
        return status

    async def shutdown(self) -> None:
        await self.stop()

    def _current_position(self) -> float:
        if self._status.state == "PLAYING":
            return self._position_at_change + time.monotonic() - self._changed_at
        return self._position_at_change

    def _set_position(self, position: float) -> None:
        self._position_at_change = position
        self._changed_at = time.monotonic()

    def _emit_status(self) -> None:
        snapshot = self.status()
        for listener in tuple(self._status_listeners):
            result = listener(snapshot)
            if result is not None:
                asyncio.create_task(result)

    def _emit_control(self, request: ControlRequest) -> None:
        for listener in tuple(self._control_listeners):
            result = listener(request)
            if result is not None:
                asyncio.create_task(result)


class CommandAudioBackend(NullAudioBackend):
    """Launch an argv template such as ``mpv --no-video {url}``.

    No shell is involved. Pause/resume use POSIX process signals; loading and
    stopping work with any long-running command-line player.
    """

    def __init__(self, command_template: str) -> None:
        super().__init__()
        self._template = shlex.split(command_template)
        if not self._template or not any("{url}" in item for item in self._template):
            raise ValueError("player command must contain a {url} placeholder")
        self._process: asyncio.subprocess.Process | None = None
        self._watch_task: asyncio.Task[None] | None = None

    async def load(
        self, url: str, content_type: str, autoplay: bool, start_time: float
    ) -> None:
        await self._terminate()
        argv = [
            item.replace("{start_time}", str(max(0.0, start_time))).replace("{url}", url)
            for item in self._template
        ]
        self._process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        self._watch_task = asyncio.create_task(self._watch_process(self._process))
        await super().load(url, content_type, True, start_time)
        if not autoplay:
            await self.pause()

    async def play(self) -> None:
        if self._process and self._process.returncode is None and os.name == "posix":
            self._process.send_signal(signal.SIGCONT)
        await super().play()

    async def pause(self) -> None:
        if self._process and self._process.returncode is None and os.name == "posix":
            self._process.send_signal(signal.SIGSTOP)
        await super().pause()

    async def stop(self) -> None:
        await self._terminate()
        await super().stop()

    async def shutdown(self) -> None:
        await self.stop()

    async def _terminate(self) -> None:
        watch_task, self._watch_task = self._watch_task, None
        if watch_task is not None and watch_task is not asyncio.current_task():
            watch_task.cancel()
            await asyncio.gather(watch_task, return_exceptions=True)
        process, self._process = self._process, None
        if not process or process.returncode is not None:
            return
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            process.kill()
            await process.wait()

    async def _watch_process(self, process: asyncio.subprocess.Process) -> None:
        returncode = await process.wait()
        if process is not self._process:
            return
        self._process = None
        if self._status.state in {"PLAYING", "PAUSED", "BUFFERING"}:
            if returncode == 0 and self.metadata.duration is not None:
                self._set_position(self.metadata.duration)
            self._status.state = "IDLE"
            self._status.idle_reason = "FINISHED" if returncode == 0 else "ERROR"
            self._emit_status()
