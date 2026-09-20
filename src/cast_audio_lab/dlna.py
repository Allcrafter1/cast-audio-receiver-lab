"""Experimental DLNA DMR output built on async-upnp-client."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
import time
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from .backend import NullAudioBackend

LOGGER = logging.getLogger(__name__)


def upnp_command(method):
    """Translate library failures into the shared player's recoverable errors."""
    @wraps(method)
    async def command(self, *args, **kwargs):
        try:
            return await method(self, *args, **kwargs)
        except Exception as error:
            from async_upnp_client.exceptions import UpnpError
            if not isinstance(error, (UpnpError, OSError, RuntimeError)):
                raise
            code = getattr(error, "error_code", None)
            detail = f"UPnP {int(code)}" if isinstance(code, int) else type(error).__name__
            LOGGER.warning("DLNA command=%s failed category=%s", method.__name__, detail)
            if method.__name__ in {"load", "stop"}:
                await self._cancel_polling()
                self._status.state = "IDLE"
                self._status.idle_reason = "ERROR"
                self._emit_status()
            # A failed remote Stop must not prevent local session cleanup.
            if method.__name__ == "stop":
                return
            raise RuntimeError(f"DLNA {method.__name__} failed ({detail})") from None
    return command


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

    def __init__(self, description_url: str, *, profile_factory=_create_profile, relay_factory=None, ffmpeg="ffmpeg"):
        super().__init__()
        self.description_url = description_url
        self._profile_factory = profile_factory
        self._profile = None
        self._poll_task = None
        self._load_started = 0.0
        self._seen_playing = False
        self._awaiting_play = False
        self._relay = None
        self._relay_factory = relay_factory
        self._ffmpeg = ffmpeg

    async def _connect(self):
        if self._profile is None:
            profile = await self._profile_factory(self.description_url)
            await profile.async_update()
            self._profile = profile
        return self._profile

    @upnp_command
    async def load(self, url, content_type, autoplay, start_time):
        await self._cancel_polling()
        profile = await self._connect()
        if getattr(profile.transport_state, "name", "") in {"PLAYING", "PAUSED_PLAYBACK", "TRANSITIONING"}:
            await profile.async_stop()
        self._status.state = "BUFFERING"
        self._status.url = url
        self._status.content_type = content_type
        self._status.idle_reason = None
        self._set_position(max(0, start_time))
        self._seen_playing = False
        self._awaiting_play = not autoplay
        self._emit_status()
        from .dlna_media import DlnaMediaRelay, needs_relay, renderer_mime_types
        supported = renderer_mime_types(profile)
        use_relay = needs_relay(url, content_type, supported)
        if use_relay:
            if self._relay is None:
                factory = self._relay_factory or DlnaMediaRelay
                self._relay = factory(urlsplit(self.description_url).hostname, ffmpeg=self._ffmpeg)
            started = time.monotonic()
            url, content_type = await self._relay.prepare(url, content_type, supported)
            LOGGER.info("DLNA local media prepared mime=%s elapsed_ms=%d", content_type,
                        (time.monotonic() - started) * 1000)
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
        self._load_started = time.monotonic()
        await profile.async_set_transport_uri(url, self.metadata.title or "Cast audio", didl)
        if autoplay:
            await profile.async_wait_for_can_play()
            if not profile.can_play:
                raise RuntimeError("renderer did not become ready to play")
            await profile.async_play()
        if start_time > 0:
            await profile.async_seek_abs_time(timedelta(seconds=max(0, start_time)))
        # SOAP acknowledgement is not confirmation that the decoder is playing.
        self._status.state = "BUFFERING" if autoplay else "PAUSED"
        self._emit_status()
        self._start_polling()

    @upnp_command
    async def play(self):
        await (await self._connect()).async_play()
        self._awaiting_play = False
        self._load_started = time.monotonic()
        self._status.state = "BUFFERING"
        self._emit_status()

    @upnp_command
    async def pause(self):
        await (await self._connect()).async_pause()
        await super().pause()

    @upnp_command
    async def seek(self, position):
        await (await self._connect()).async_seek_abs_time(
            timedelta(seconds=max(0, position))
        )
        await super().seek(position)

    @upnp_command
    async def set_volume(self, level, muted):
        profile = await self._connect()
        await profile.async_set_volume_level(max(0.0, min(1.0, level)))
        if profile.has_volume_mute:
            await profile.async_mute_volume(bool(muted))
        await super().set_volume(level, muted)

    @upnp_command
    async def stop(self):
        self._awaiting_play = False
        await self._cancel_polling()
        try:
            if self._profile is not None:
                await self._profile.async_stop()
        finally:
            if self._relay is not None:
                await self._relay.close()
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
                if position is not None and state in {"PLAYING", "PAUSED_PLAYBACK"}:
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
                    if state == "TRANSITIONING" and not self._seen_playing and time.monotonic() - self._load_started >= 15:
                        self._status.state = "IDLE"
                        self._status.idle_reason = "ERROR"
                        self._emit_status()
                        return
                    if state == "PLAYING":
                        self._seen_playing = True
                        self._awaiting_play = False
                    self._status.state = mapped
                    self._emit_status()
                elif (
                    state in {"STOPPED", "NO_MEDIA_PRESENT"}
                    and self._status.state != "IDLE"
                ):
                    if state == "STOPPED" and self._awaiting_play:
                        # SetAVTransportURI without Play is a valid preload,
                        # not EOF or cancellation. Keep it ready indefinitely.
                        self._status.state = "PAUSED"
                        self._emit_status()
                        continue
                    if not self._seen_playing and self._status.state == "BUFFERING":
                        if time.monotonic() - self._load_started < 15:
                            continue
                        self._status.state = "IDLE"
                        self._status.idle_reason = "ERROR"
                        self._emit_status()
                        return
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
