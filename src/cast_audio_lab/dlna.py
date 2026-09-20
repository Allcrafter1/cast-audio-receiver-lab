"""Experimental DLNA DMR output built on async-upnp-client."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
from pathlib import Path

from .backend import NullAudioBackend


async def _create_profile(description_url: str):
    try:
        from async_upnp_client.aiohttp import AiohttpRequester
        from async_upnp_client.client_factory import UpnpFactory
        from async_upnp_client.profiles.dlna import DmrDevice
    except ImportError as error:
        raise RuntimeError("DLNA output requires async-upnp-client") from error
    device = await UpnpFactory(AiohttpRequester(timeout=10)).async_create_device(
        description_url
    )
    return DmrDevice(device, event_handler=None)


class DlnaAudioBackend(NullAudioBackend):
    """Control a pull-based DMR; signed source URLs remain device-visible."""

    def __init__(self, description_url: str, *, profile_factory=_create_profile):
        super().__init__()
        self.description_url = description_url
        self._profile_factory = profile_factory
        self._profile = None
        self._poll_task = None

    async def _connect(self):
        if self._profile is None:
            self._profile = await self._profile_factory(self.description_url)
            await self._profile.async_update()
        return self._profile

    async def load(self, url, content_type, autoplay, start_time):
        profile = await self._connect()
        meta = {
            key: value
            for key, value in {
                "artist": self.metadata.artist,
                "album": self.metadata.album,
                "album_art_uri": self.metadata.artwork_url,
            }.items()
            if value
        }
        didl = await profile.construct_play_media_metadata(
            url,
            self.metadata.title or "Cast audio",
            override_mime_type=content_type,
            override_dlna_features="*",
            meta_data=meta,
        )
        self._status.state = "BUFFERING"
        self._emit_status()
        await profile.async_set_transport_uri(
            url, self.metadata.title or "Cast audio", didl
        )
        if autoplay:
            await profile.async_wait_for_can_play()
            await profile.async_play()
        if start_time > 0:
            await profile.async_seek_abs_time(timedelta(seconds=max(0, start_time)))
        await super().load(url, content_type, autoplay, start_time)
        self._start_polling()

    async def play(self):
        await (await self._connect()).async_play()
        await super().play()

    async def pause(self):
        await (await self._connect()).async_pause()
        await super().pause()

    async def seek(self, position):
        await (await self._connect()).async_seek_abs_time(
            timedelta(seconds=max(0, position))
        )
        await super().seek(position)

    async def set_volume(self, level, muted):
        profile = await self._connect()
        await profile.async_set_volume_level(max(0.0, min(1.0, level)))
        if profile.has_volume_mute:
            await profile.async_mute_volume(bool(muted))
        await super().set_volume(level, muted)

    async def stop(self):
        await self._cancel_polling()
        if self._profile is not None:
            await self._profile.async_stop()
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
        while self._profile is not None and self._status.url:
            try:
                await asyncio.sleep(1)
                await self._profile.async_update()
                failures = 0
                state = getattr(self._profile.transport_state, "name", "")
                position = self._profile.media_position
                if position is not None:
                    self._set_position(float(position))
                if self._profile.volume_level is not None:
                    self._status.volume = float(self._profile.volume_level)
                if self._profile.is_volume_muted is not None:
                    self._status.muted = bool(self._profile.is_volume_muted)
                mapped = {
                    "PLAYING": "PLAYING",
                    "TRANSITIONING": "BUFFERING",
                    "PAUSED_PLAYBACK": "PAUSED",
                }.get(state)
                if mapped:
                    self._status.state = mapped
                    self._emit_status()
                elif (
                    state in {"STOPPED", "NO_MEDIA_PRESENT"}
                    and self._status.state != "IDLE"
                ):
                    duration = self.metadata.duration
                    finished = duration is not None and self._current_position() >= duration - 2
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


def load_dlna_target(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("description_url"), str):
        raise ValueError("invalid DLNA target file")
    return value
