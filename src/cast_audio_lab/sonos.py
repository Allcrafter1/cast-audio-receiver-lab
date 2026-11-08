# SPDX-License-Identifier: MPL-2.0
"""Experimental direct Sonos output built on SoCo."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import math
from queue import Queue
import time
from pathlib import Path
from urllib.parse import urlsplit

from .backend import NullAudioBackend

LOGGER = logging.getLogger(__name__)

# Containers Sonos decodes when it pulls a URL itself. Opus/WebM (YouTube's
# usual itag 251) and Ogg (Vorbis or Opus is ambiguous) are deliberately
# absent, so they are converted by the local relay instead of failing on the
# speaker. Unknown/empty content types are converted as well.
SONOS_DIRECT_MIME = frozenset({
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/aac", "audio/x-m4a",
    "audio/flac", "audio/x-flac", "audio/wav", "audio/x-wav",
})
# The relay's copy formats Sonos can actually decode.
SONOS_RELAY_MIME = frozenset({"audio/mpeg", "audio/mp4", "audio/flac", "audio/x-flac", "audio/wav", "audio/x-wav"})
# Poll the speaker volume only every few seconds to keep SOAP traffic low.
VOLUME_POLL_INTERVAL = 5
VOLUME_EVENT_WATCHDOG = 60

def _create_device(host: str):
    try:
        from soco import SoCo
    except ImportError as error:
        raise RuntimeError("Sonos output requires SoCo") from error
    return SoCo(host)


def _track_didl(url: str, mime: str, metadata) -> str:
    """DIDL-Lite for a music track so Sonos shows artist, album and cover."""
    from soco.data_structures import DidlMusicTrack, DidlResource, to_didl_string
    from soco.exceptions import DIDLMetadataError

    fields = {"title": metadata.title or "Cast audio", "parent_id": "-1", "item_id": "-1",
              "resources": [DidlResource(uri=url, protocol_info=f"http-get:*:{mime or 'audio/mpeg'}:*")]}
    if metadata.artist:
        fields["creator"] = metadata.artist
        fields["artist"] = metadata.artist
    if metadata.album:
        fields["album"] = metadata.album
    if metadata.artwork_url:
        fields["album_art_uri"] = metadata.artwork_url
    try:
        return to_didl_string(DidlMusicTrack(**fields))
    except DIDLMetadataError:
        raise ValueError("Sonos track metadata could not be constructed") from None


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    return f"{value // 3600}:{value % 3600 // 60:02d}:{value % 60:02d}"


def _seconds(value: str) -> float | None:
    try:
        hours, minutes, seconds = (int(part) for part in value.split(":"))
        return float(hours * 3600 + minutes * 60 + seconds)
    except (AttributeError, TypeError, ValueError):
        return None


def sonos_needs_relay(url: str, content_type: str) -> bool:
    """Return whether Sonos cannot pull ``url`` directly.

    Loopback URLs are unreachable from the speaker and unsupported codecs would
    fail on its decoder. Supported remote HTTP(S) media, including live radio,
    stays direct so infinite streams are never pushed through the bounded relay.
    """
    host = urlsplit(url).hostname or ""
    try:
        loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    return loopback or mime not in SONOS_DIRECT_MIME


class _EventQueue(Queue):
    """SoCo's thread-safe queue interface, delivered on our owning event loop."""

    def __init__(self, loop, receive):
        super().__init__()
        self.loop, self.receive = loop, receive

    def put(self, event, block=True, timeout=None):
        try:
            self.loop.call_soon_threadsafe(self.receive, event)
        except RuntimeError:
            pass  # The owning event loop has already shut down.


class SonosAudioBackend(NullAudioBackend):
    def __init__(self, host: str, *, device_factory=_create_device, relay_factory=None, ffmpeg="ffmpeg"):
        super().__init__()
        self.host = host
        self.device = device_factory(host)
        self._poll_task = None
        self._command_lock = asyncio.Lock()
        self._pending_command = None
        self._subscription = None
        self._event_generation = 0
        self._events_ready = False
        self._last_volume_event = 0.0
        self._subscription_started = 0.0
        self._relay = None
        self._relay_factory = relay_factory
        self._ffmpeg = ffmpeg
        try:  # import once here, not on the event loop during the first load
            import soco.data_structures  # noqa: F401
        except ImportError:
            pass

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

    def _receive_volume(self, generation, event):
        if generation != self._event_generation:
            return
        try:
            values = event.variables
            if ("Master" not in values.get("volume", {})
                    and "Master" not in values.get("mute", {})):
                return
            level = float(values.get("volume", {}).get("Master", self._status.volume * 100)) / 100
            mute = values.get("mute", {}).get("Master")
            if not math.isfinite(level) or not 0 <= level <= 1 or mute not in (None, "0", "1", 0, 1):
                return
            if "volume" not in values and "mute" not in values:
                return
            self._status.volume = level
            if mute is not None:
                self._status.muted = mute in ("1", 1)
            self._events_ready = True
            self._last_volume_event = time.monotonic()
            self._emit_status()
        except (AttributeError, TypeError, ValueError):
            return

    async def _subscribe_volume(self):
        if self._subscription is not None:
            return
        self._subscription_started = time.monotonic()
        self._event_generation += 1
        generation = self._event_generation
        loop = asyncio.get_running_loop()
        queue = _EventQueue(loop, lambda event: self._receive_volume(generation, event))
        def subscribe():
            self._subscription = self.device.renderingControl.subscribe(
                auto_renew=True, event_queue=queue)
            self._subscription.auto_renew_fail = lambda error: loop.call_soon_threadsafe(
                self._volume_subscription_failed, generation)
        try:
            await self._call(subscribe)
        except RuntimeError:
            LOGGER.info("Sonos volume events unavailable; using polling fallback")

    def _volume_subscription_failed(self, generation):
        if generation == self._event_generation:
            self._events_ready = False

    async def _unsubscribe_volume(self):
        self._event_generation += 1
        self._events_ready = False
        # _call also waits for an interrupted subscribe before cleanup.
        def unsubscribe():
            subscription, self._subscription = self._subscription, None
            if subscription is not None:
                subscription.unsubscribe()
        try:
            await self._call(unsubscribe)
        except RuntimeError:
            LOGGER.info("Sonos volume subscription cleanup failed")

    async def read_volume(self):
        volume, muted = await self._call(lambda: (self.device.volume, self.device.mute))
        return float(volume) / 100, muted

    async def load(self, url, content_type, autoplay, start_time):
        await self._cancel_polling()
        self._status.state = "BUFFERING"
        self._status.idle_reason = None
        self._emit_status()
        play_url, play_mime = url, (content_type or "").split(";", 1)[0].strip().lower()
        if sonos_needs_relay(url, content_type):
            if self._relay is None:
                from .dlna_media import DlnaMediaRelay
                factory = self._relay_factory or DlnaMediaRelay
                self._relay = factory(self.host, ffmpeg=self._ffmpeg)
            started = time.monotonic()
            play_url, play_mime = await self._relay.prepare(url, content_type or "", SONOS_RELAY_MIME)
            LOGGER.info("Sonos local media prepared mime=%s elapsed_ms=%d", play_mime,
                        (time.monotonic() - started) * 1000)
        try:
            meta = {"meta": _track_didl(play_url, play_mime, self.metadata)}
        except (ImportError, TypeError, ValueError):
            LOGGER.warning("Sonos track metadata unavailable; using title only")
            meta = {"title": self.metadata.title or "Cast audio"}
        await self._call(self.device.play_uri, play_url, start=autoplay, **meta)
        if start_time > 0:
            await self._call(self.device.seek, _timestamp(start_time))
        await super().load(url, content_type, autoplay, start_time)
        await self._subscribe_volume()
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
        percent = round(max(0, min(1, level)) * 100)
        def write():
            self.device.volume = percent
            self.device.mute = bool(muted)
        await self._call(write)
        await super().set_volume(percent / 100, bool(muted))

    async def _refresh_volume(self):
        now = time.monotonic()
        healthy = (self._events_ready and self._subscription is not None
                   and self._subscription.is_subscribed
                   and now - self._last_volume_event < VOLUME_EVENT_WATCHDOG)
        if healthy:
            return
        # A successful SUBSCRIBE does not prove the callback port is reachable.
        try:
            level, muted = await self.read_volume()
            if math.isfinite(level) and 0 <= level <= 1:
                self._status.volume, self._status.muted = level, muted
                self._emit_status()
        except (RuntimeError, TypeError, ValueError):
            LOGGER.debug("Sonos volume fallback read failed")
        if now - self._subscription_started >= VOLUME_EVENT_WATCHDOG:
            await self._unsubscribe_volume()
            await self._subscribe_volume()

    async def stop(self):
        await self._cancel_polling()
        await self._unsubscribe_volume()
        try:
            await self._call(self.device.stop)
        finally:
            try:
                if self._relay is not None:
                    await self._relay.close()
                    self._relay = None
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
        cycle = 0
        while self._status.url:
            try:
                await asyncio.sleep(1)
                transport, track = await asyncio.gather(
                    asyncio.to_thread(self.device.get_current_transport_info),
                    asyncio.to_thread(self.device.get_current_track_info),
                )
                failures = 0
                cycle += 1
                if cycle % VOLUME_POLL_INTERVAL == 0:
                    await self._refresh_volume()
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
                    # Keep receiver volume feedback alive until Cast Stop.
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
