"""Cast V2 JSON namespaces needed by an audio-only receiver."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cast_audio_lab.backend import AudioBackend, MediaMetadata, PlaybackStatus
from .wire import CastMessage, PayloadType


LOG = logging.getLogger(__name__)

CONNECTION_NAMESPACE = "urn:x-cast:com.google.cast.tp.connection"
HEARTBEAT_NAMESPACE = "urn:x-cast:com.google.cast.tp.heartbeat"
RECEIVER_NAMESPACE = "urn:x-cast:com.google.cast.receiver"
MEDIA_NAMESPACE = "urn:x-cast:com.google.cast.media"
DEFAULT_MEDIA_RECEIVER_APP_ID = "CC1AD845"
YOUTUBE_APP_ID = "233637DE"
YOUTUBE_MUSIC_APP_ID = "2DB7CC49"
YOUTUBE_APP_IDS = frozenset((YOUTUBE_APP_ID, YOUTUBE_MUSIC_APP_ID))
YOUTUBE_MDX_NAMESPACE = "urn:x-cast:com.google.youtube.mdx"


@dataclass(slots=True)
class ReceiverState:
    friendly_name: str
    volume: float = 1.0
    muted: bool = False
    app_id: str | None = None
    session_id: str | None = None
    transport_id: str | None = None
    media_session_id: int = 1
    media: dict[str, Any] = field(default_factory=dict)


class CastProtocolEngine:
    def __init__(
        self,
        friendly_name: str,
        backend: AudioBackend,
        youtube_screen_id: Callable[[], str | None] | None = None,
        youtube_device_id: Callable[[], str | None] | None = None,
    ) -> None:
        self.state = ReceiverState(friendly_name=friendly_name)
        self.backend = backend
        self.youtube_screen_id = youtube_screen_id
        self.youtube_device_id = youtube_device_id

    async def handle(self, message: CastMessage) -> list[CastMessage]:
        if message.payload_type != PayloadType.STRING:
            return []
        try:
            payload = json.loads(message.payload_utf8)
        except (json.JSONDecodeError, TypeError):
            LOG.warning("Ignoring invalid JSON on %s", message.namespace)
            return []
        if not isinstance(payload, dict):
            return []

        if message.namespace == CONNECTION_NAMESPACE:
            return await self._connection(message, payload)
        if message.namespace == HEARTBEAT_NAMESPACE:
            return await self._heartbeat(message, payload)
        if message.namespace == RECEIVER_NAMESPACE:
            return await self._receiver(message, payload)
        if message.namespace == MEDIA_NAMESPACE:
            return await self._media(message, payload)
        if message.namespace == YOUTUBE_MDX_NAMESPACE:
            return await self._youtube_mdx(message, payload)
        LOG.debug("Ignoring unsupported namespace %s", message.namespace)
        return []

    async def _connection(
        self, message: CastMessage, payload: dict[str, Any]
    ) -> list[CastMessage]:
        if payload.get("type") == "CLOSE":
            return []
        # CONNECT establishes a virtual channel and has no protocol response.
        return []

    async def _heartbeat(
        self, message: CastMessage, payload: dict[str, Any]
    ) -> list[CastMessage]:
        if payload.get("type") != "PING":
            return []
        return [self._json_reply(message, {"type": "PONG"})]

    async def _receiver(
        self, message: CastMessage, payload: dict[str, Any]
    ) -> list[CastMessage]:
        kind = payload.get("type")
        request_id = payload.get("requestId")
        if kind == "GET_STATUS":
            return [self._receiver_status(message, request_id)]
        if kind == "SET_VOLUME":
            volume = payload.get("volume") or {}
            if isinstance(volume, dict):
                level = _float_or(volume.get("level"), self.state.volume)
                muted = bool(volume.get("muted", self.state.muted))
                self.state.volume = max(0.0, min(1.0, level))
                self.state.muted = muted
                await self.backend.set_volume(self.state.volume, muted)
            return [self._receiver_status(message, request_id)]
        if kind == "LAUNCH":
            app_id = payload.get("appId")
            youtube_available = (
                app_id in YOUTUBE_APP_IDS
                and self.youtube_screen_id is not None
                and self.youtube_screen_id() is not None
            )
            if app_id != DEFAULT_MEDIA_RECEIVER_APP_ID and not youtube_available:
                return [
                    self._json_reply(
                        message,
                        {
                            "type": "LAUNCH_ERROR",
                            "requestId": request_id,
                            "reason": "APP_NOT_FOUND",
                        },
                    )
                ]
            self.state.app_id = app_id
            self.state.session_id = str(uuid.uuid4())
            self.state.transport_id = f"web-{uuid.uuid4()}"
            return [self._receiver_status(message, request_id)]
        if kind == "STOP":
            await self.backend.stop()
            self.state.app_id = None
            self.state.session_id = None
            self.state.transport_id = None
            return [self._receiver_status(message, request_id)]
        return []

    async def _youtube_mdx(
        self, message: CastMessage, payload: dict[str, Any]
    ) -> list[CastMessage]:
        if (
            self.state.app_id not in YOUTUBE_APP_IDS
            or payload.get("type") != "getMdxSessionStatus"
            or self.youtube_screen_id is None
        ):
            return []
        screen_id = self.youtube_screen_id()
        if not screen_id:
            return []
        response: dict[str, Any] = {
            "type": "mdxSessionStatus",
            "data": {"screenId": screen_id},
        }
        if self.youtube_device_id is not None:
            device_id = self.youtube_device_id()
            if device_id:
                response["data"]["deviceId"] = device_id
        if payload.get("requestId") is not None:
            response["requestId"] = payload["requestId"]
        return [self._json_reply(message, response)]

    async def _media(
        self, message: CastMessage, payload: dict[str, Any]
    ) -> list[CastMessage]:
        kind = payload.get("type")
        request_id = payload.get("requestId")

        if kind == "LOAD":
            media = payload.get("media")
            if not isinstance(media, dict) or not isinstance(
                media.get("contentId"), str
            ):
                return [
                    self._json_reply(
                        message,
                        {
                            "type": "LOAD_FAILED",
                            "requestId": request_id,
                        },
                    )
                ]
            self.state.media = media
            await self.backend.set_metadata(metadata_from_cast(media))
            await self.backend.load(
                media["contentId"],
                str(media.get("contentType", "audio/mpeg")),
                bool(payload.get("autoplay", True)),
                _float_or(payload.get("currentTime"), 0.0),
            )
            return [self._media_status(message, request_id)]
        if kind == "GET_STATUS":
            return [self._media_status(message, request_id)]
        if kind == "PLAY":
            await self.backend.play()
        elif kind == "PAUSE":
            await self.backend.pause()
        elif kind == "STOP":
            await self.backend.stop()
        elif kind == "SEEK":
            await self.backend.seek(_float_or(payload.get("currentTime"), 0.0))
        elif kind == "SET_VOLUME":
            volume = payload.get("volume") or {}
            if isinstance(volume, dict):
                self.state.volume = max(
                    0.0,
                    min(
                        1.0,
                        _float_or(volume.get("level"), self.state.volume),
                    ),
                )
                self.state.muted = bool(
                    volume.get("muted", self.state.muted)
                )
                await self.backend.set_volume(
                    self.state.volume,
                    self.state.muted,
                )
        else:
            return []
        return [self._media_status(message, request_id)]

    def _receiver_status(
        self, message: CastMessage, request_id: Any
    ) -> CastMessage:
        playback = self.backend.status()
        status: dict[str, Any] = {
            "volume": {
                "level": playback.volume,
                "muted": playback.muted,
                "stepInterval": 0.05,
            },
            "applications": [],
            "isActiveInput": True,
            "standBy": False,
        }
        if self.state.app_id:
            is_youtube = self.state.app_id in YOUTUBE_APP_IDS
            is_youtube_music = self.state.app_id == YOUTUBE_MUSIC_APP_ID
            namespaces = [{"name": MEDIA_NAMESPACE}]
            if is_youtube:
                namespaces.insert(0, {"name": YOUTUBE_MDX_NAMESPACE})
            status["applications"] = [
                {
                    "appId": self.state.app_id,
                    "displayName": (
                        "YouTube Music"
                        if is_youtube_music
                        else (
                            "YouTube"
                            if is_youtube
                            else "Default Media Receiver"
                        )
                    ),
                    "isIdleScreen": False,
                    "sessionId": self.state.session_id,
                    "statusText": (
                        "YouTube Music ready"
                        if is_youtube
                        else "Ready to play audio"
                    ),
                    "transportId": self.state.transport_id,
                    "namespaces": namespaces,
                    "universalAppId": self.state.app_id,
                }
            ]
        response: dict[str, Any] = {"type": "RECEIVER_STATUS", "status": status}
        if request_id is not None:
            response["requestId"] = request_id
        return self._json_reply(message, response)

    def _media_status(
        self, message: CastMessage, request_id: Any
    ) -> CastMessage:
        playback = self.backend.status()
        item = self._media_status_item(playback)
        response: dict[str, Any] = {"type": "MEDIA_STATUS", "status": [item]}
        if request_id is not None:
            response["requestId"] = request_id
        return self._json_reply(message, response)

    def _media_status_item(self, playback: PlaybackStatus) -> dict[str, Any]:
        item: dict[str, Any] = {
            "mediaSessionId": self.state.media_session_id,
            "playbackRate": 1,
            "playerState": playback.state,
            "currentTime": playback.current_time,
            "supportedMediaCommands": 15,
            "volume": {
                "level": playback.volume,
                "muted": playback.muted,
            },
        }
        if self.state.media:
            item["media"] = self.state.media
        if playback.state == "IDLE" and playback.idle_reason:
            item["idleReason"] = playback.idle_reason
        return item

    def receiver_status_for(self, destination_id: str) -> CastMessage:
        """Build an unsolicited receiver status for a connected sender."""

        request = CastMessage(
            source_id=destination_id,
            destination_id="receiver-0",
            namespace=RECEIVER_NAMESPACE,
            payload_utf8="{}",
        )
        return self._receiver_status(request, None)

    def media_status_for(self, destination_id: str) -> CastMessage:
        """Build an unsolicited media status for a connected sender."""

        request = CastMessage(
            source_id=destination_id,
            destination_id=self.state.transport_id or "receiver-0",
            namespace=MEDIA_NAMESPACE,
            payload_utf8="{}",
        )
        return self._media_status(request, None)

    @staticmethod
    def _json_reply(
        request: CastMessage, payload: dict[str, Any]
    ) -> CastMessage:
        return CastMessage(
            source_id=request.destination_id,
            destination_id=request.source_id,
            namespace=request.namespace,
            payload_type=PayloadType.STRING,
            payload_utf8=json.dumps(payload, separators=(",", ":")),
        )


def _float_or(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def metadata_from_cast(media: dict[str, Any]) -> MediaMetadata:
    """Translate Cast's metadata dialect into the output-neutral model."""

    raw = media.get("metadata")
    metadata = raw if isinstance(raw, dict) else {}
    artwork_url = ""
    images = metadata.get("images")
    if isinstance(images, list) and images and isinstance(images[0], dict):
        value = images[0].get("url")
        artwork_url = value if isinstance(value, str) else ""
    duration_value = media.get("duration")
    duration = (
        float(duration_value)
        if isinstance(duration_value, (int, float))
        else None
    )
    return MediaMetadata(
        title=_string(metadata.get("title")),
        artist=_string(metadata.get("artist")),
        album=_string(metadata.get("albumName")),
        artwork_url=artwork_url,
        item_id=_string(media.get("contentId")),
        duration=duration,
    )


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""
