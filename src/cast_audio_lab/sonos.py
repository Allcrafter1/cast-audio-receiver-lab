# SPDX-License-Identifier: MPL-2.0
"""Experimental direct Sonos output built on SoCo."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from .backend import NullAudioBackend


def _create_device(host: str):
    try:
        from soco import SoCo
    except ImportError as error:
        raise RuntimeError("Sonos output requires SoCo") from error
    return SoCo(host)


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600}:{value % 3600 // 60:02d}:{value % 60:02d}"


def _seconds(value: str) -> float | None:
    try:
        hours, minutes, seconds = (int(part) for part in value.split(":"))
        return float(hours * 3600 + minutes * 60 + seconds)
    except (AttributeError, TypeError, ValueError):
        return None


class SonosAudioBackend(NullAudioBackend):
    def __init__(self, host: str, *, device_factory=_create_device):
        super().__init__()
        self.device = device_factory(host)
        self._poll_task = None
        self._command_lock = asyncio.Lock()
        self._pending_command = None

    async def _call(self, function, *args, **kwargs):
        # Cancelling to_thread only cancels its waiter, not the device request.
        # Keep ownership and order Stop after that request has actually ended.
        async with self._command_lock:
            pending = self._pending_command
            if pending is not None:
                try:
                    await asyncio.shield(pending)
                except Exception:
                    pass
            task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
            self._pending_command = task
            try:
                return await asyncio.shield(task)
            except Exception as error:
                raise RuntimeError(f"Sonos command failed ({type(error).__name__})") from None
            finally:
                if task.done():
                    self._pending_command = None

    async def load(self, url, content_type, autoplay, start_time):
        await self._cancel_polling()
        self._status.state = "BUFFERING"
        self._status.idle_reason = None
        self._emit_status()
        await self._call(
            self.device.play_uri,
            url,
            title=self.metadata.title or "Cast audio",
            start=autoplay,
        )
        if start_time > 0:
            await self._call(self.device.seek, _timestamp(start_time))
        await super().load(url, content_type, autoplay, start_time)
        self._start_polling()

    async def play(self):
        await self._call(self.device.play)
        self._status.idle_reason = None
        await super().play()
        self._start_polling()

    async def pause(self):
        await self._call(self.device.pause)
        await super().pause()

    async def seek(self, position):
        await self._call(self.device.seek, _timestamp(position))
        await super().seek(position)

    async def set_volume(self, level, muted):
        await self._call(
            setattr,
            self.device,
            "volume",
            round(max(0, min(1, level)) * 100),
        )
        await self._call(setattr, self.device, "mute", bool(muted))
        await super().set_volume(level, muted)

    async def stop(self):
        await self._cancel_polling()
        try:
            await self._call(self.device.stop)
        finally:
            await super().stop()

    def _start_polling(self):
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._poll())

    async def _cancel_polling(self):
        task, self._poll_task = self._poll_task, None
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _poll(self):
        failures = 0
        while self._status.url:
            try:
                await asyncio.sleep(1)
                transport, track = await asyncio.gather(
                    asyncio.to_thread(self.device.get_current_transport_info),
                    asyncio.to_thread(self.device.get_current_track_info),
                )
                failures = 0
                position = _seconds(track.get("position"))
                if position is not None:
                    self._set_position(position)
                state = transport.get("current_transport_state")
                mapped = {
                    "PLAYING": "PLAYING",
                    "TRANSITIONING": "BUFFERING",
                    "PAUSED_PLAYBACK": "PAUSED",
                }.get(state)
                if mapped:
                    self._status.state = mapped
                    self._emit_status()
                elif state == "STOPPED" and self._status.state != "IDLE":
                    duration = _seconds(track.get("duration")) or self.metadata.duration
                    finished = (
                        duration is not None
                        and self._current_position() >= duration - 2
                    )
                    self._status.state = "IDLE"
                    self._status.idle_reason = "FINISHED" if finished else "CANCELLED"
                    self._emit_status()
                    return
            except asyncio.CancelledError:
                raise
            except Exception:
                failures += 1
                if failures >= 3:
                    self._status.state = "IDLE"
                    self._status.idle_reason = "ERROR"
                    self._emit_status()
                    return

    async def shutdown(self):
        await self.stop()


def load_sonos_target(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("host"), str):
        raise ValueError("invalid Sonos target file")
    return value
