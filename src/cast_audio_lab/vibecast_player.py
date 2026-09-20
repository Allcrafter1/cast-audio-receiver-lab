"""Audio player adapter for Vibecast's external-player WebSocket protocol."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import platform
import uuid
from pathlib import Path
from typing import Any
from websockets.exceptions import ConnectionClosed

from .backend import (
    AudioBackend,
    CommandAudioBackend,
    ControlRequest,
    MediaMetadata,
    PlaybackStatus,
)
from .output_registry import create_output_backend, output_names

LOGGER = logging.getLogger(__name__)


class VibecastAudioPlayer:
    """Register one Linux audio output as a Cast receiver in Vibecast."""

    def __init__(self, url: str, player_id: str, name: str, backend: AudioBackend,
                 *, artwork_endpoint=None, artwork_public_url=None) -> None:
        self.url = url
        self.player_id = player_id
        self.name = name
        self.backend = backend
        self.session_id: str | None = None
        self._websocket: Any = None
        self._last_event_state = None
        self.artwork_endpoint = artwork_endpoint
        self.artwork_public_url = artwork_public_url
        self._artwork_task = None
        backend.add_status_listener(self._backend_status_changed)
        backend.add_control_listener(self._backend_control_requested)

    def registration(self) -> dict[str, object]:
        return {
            "type": "register",
            "player": {
                "protocolVersion": 2,
                "playerId": self.player_id,
                "name": self.name,
                "capabilities": {
                    "platform": f"Linux {platform.machine()}",
                    "drm": [],
                    # YouTube currently builds a DASH manifest containing video
                    # plus audio. mpv receives it with video output disabled.
                    "videoCodecs": ["h264", "vp9", "av1"],
                    "audioCodecs": ["opus", "aac"],
                    "maxResolution": {"width": 1920, "height": 1080},
                    "hdrFormats": [],
                    "frameRates": [24, 25, 30, 50, 60],
                    "subtitleFormats": [],
                    "hdcpLevel": None,
                    "controlRequests": [
                        "play", "pause", "stop", "seek", "volume", "next", "previous"
                    ],
                },
            },
        }

    async def run(self) -> None:
        from websockets.asyncio.client import connect
        from websockets.exceptions import ConnectionClosed

        async for websocket in connect(self.url, open_timeout=10):
            self._websocket = websocket
            LOGGER.info("connected to Vibecast player bridge at %s", self.url)
            try:
                await websocket.send(json.dumps(self.registration(), separators=(",", ":")))
                reporter = asyncio.create_task(self._periodic_reports())
                try:
                    async for raw_message in websocket:
                        await self.handle_message(json.loads(raw_message))
                finally:
                    reporter.cancel()
                    await asyncio.gather(reporter, return_exceptions=True)
            except (ConnectionClosed, OSError, ValueError, json.JSONDecodeError) as exc:
                LOGGER.warning("Vibecast player connection interrupted: %s", exc)
            finally:
                await self._cancel_artwork()
                self._websocket = None
                self.session_id = None
                await self.backend.stop()

    async def handle_message(self, message: dict[str, Any]) -> None:
        command = message.get("type")
        if command in {"settingsSnapshot", "settingsUpdateResult"}:
            return
        session_id = message.get("sessionId")
        if not isinstance(session_id, str):
            return

        try:
            LOGGER.info("player command=%s session=%s", command, session_id)
            if command == "load":
                await self._load(session_id, message.get("media"))
                return
            # Receiver volume is restored at app launch, before the first load
            # establishes a playback session. It is output-wide, not track-local.
            if command == "volume":
                await self.backend.set_volume(
                    float(message.get("level", 1.0)), bool(message.get("muted", False))
                )
                await self._send_backend_state(session_id)
                return
            if session_id != self.session_id:
                return
            if command == "play":
                await self.backend.play()
            elif command == "pause":
                await self.backend.pause()
            elif command == "seek":
                await self.backend.seek(float(message.get("position", 0.0)))
            elif command == "stop":
                await self._cancel_artwork()
                await self.backend.stop()
                self.session_id = None
            await self._send_backend_state(session_id)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            LOGGER.exception("player command %s failed", command)
            await self._send(
                {
                    "type": "error",
                    "sessionId": session_id,
                    "code": "PLAYBACK_COMMAND_FAILED",
                    "message": str(exc),
                }
            )

    async def _load(self, session_id: str, media: Any) -> None:
        if not isinstance(media, dict):
            raise ValueError("load command has no media object")
        streams = media.get("streams")
        if not isinstance(streams, list) or not streams or not isinstance(streams[0], dict):
            raise ValueError("load command has no playable stream")
        stream = streams[0]
        url = stream.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("stream has no URL")

        await self._cancel_artwork()
        self.session_id = session_id
        LOGGER.info("load session=%s title=%r start=%s", session_id,
                    media.get("title"), media.get("startTime", 0.0))
        await self._send_state(session_id, "BUFFERING")
        images = media.get("images") or []
        metadata = media.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        images = metadata.get("images") or images
        artwork = images[0].get("url", "") if images and isinstance(images[0], dict) else ""
        await self.backend.set_metadata(
            MediaMetadata(
                title=str(metadata.get("title") or media.get("title") or ""),
                artist=str(metadata.get("artist") or metadata.get("albumArtist")
                           or metadata.get("subtitle") or media.get("subtitle") or ""),
                album=str(metadata.get("albumName") or ""),
                artwork_url=str(artwork),
                duration=_optional_float(media.get("duration")),
            )
        )
        await self.backend.load(
            url,
            str(stream.get("contentType") or "application/octet-stream"),
            bool(media.get("autoplay", True)),
            float(media.get("startTime", 0.0)),
        )
        await self._send_backend_state(session_id)

        if self.artwork_endpoint and self.artwork_public_url and artwork:
            self._artwork_task = asyncio.create_task(self._prepare_artwork(
                session_id, str(artwork)))

    async def _cancel_artwork(self):
        task, self._artwork_task = self._artwork_task, None
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _prepare_artwork(self, session_id, source):
        from aiohttp import ClientSession, ClientTimeout, ClientError
        try:
            async with ClientSession(timeout=ClientTimeout(total=25)) as client:
                async with client.post(self.artwork_endpoint, json={'source': source}) as response:
                    response.raise_for_status()
                    result = await response.json()
            path = result['path']
            if not isinstance(path, str) or not path.startswith('/artwork/'):
                return
            if self.session_id == session_id:
                await self._send({'type': 'artwork', 'sessionId': session_id,
                                  'sourceUrl': source,
                                  'url': self.artwork_public_url.rstrip('/') + path})
        except (ClientError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            LOGGER.warning('Processed artwork unavailable; original metadata retained')

    async def _periodic_reports(self) -> None:
        while True:
            await asyncio.sleep(1)
            if self.session_id is not None:
                await self._send_backend_state(self.session_id)

    def _backend_status_changed(self, status: PlaybackStatus) -> None:
        # Position properties arrive many times per second. The periodic
        # reporter supplies position; push control/EOF transitions immediately.
        key = (status.state, status.idle_reason, status.volume, status.muted)
        if key == self._last_event_state:
            return
        self._last_event_state = key
        if self.session_id is not None and self._websocket is not None:
            asyncio.create_task(self._report_current_status(self.session_id, self._websocket))

    async def _report_current_status(self, session_id: str, websocket: Any) -> None:
        # A callback is queued, not sent synchronously. A seek, replacement load
        # or reconnect can happen before it runs. Never replay its old snapshot
        # into a newer playback state (even when the session ID is unchanged).
        if self.session_id != session_id or self._websocket is not websocket:
            return
        try:
            await self._send_backend_state(session_id)
        except (OSError, RuntimeError, ConnectionClosed):
            LOGGER.debug("Status notification interrupted; connection loop handles recovery")

    def _backend_control_requested(self, request: ControlRequest) -> None:
        if self.session_id is None or self._websocket is None:
            return
        control: dict[str, object] = {"command": request.command}
        if request.position is not None:
            control["position"] = request.position
        if request.level is not None:
            control["level"] = request.level
        if request.muted is not None:
            control["muted"] = request.muted
        asyncio.create_task(self._send({
            "type": "controlRequest",
            "sessionId": self.session_id,
            "control": control,
        }))

    async def _send_backend_state(self, session_id: str) -> None:
        await self._send_status(session_id, self.backend.status())

    async def _send_status(self, session_id: str, status: PlaybackStatus) -> None:
        await self._send_state(
            session_id,
            status.state,
            current_time=status.current_time,
            idle_reason=status.idle_reason,
            volume=status.volume,
            muted=status.muted,
        )

    async def _send_state(
        self,
        session_id: str,
        state: str,
        current_time: float = 0.0,
        idle_reason: str | None = None,
        volume: float | None = None,
        muted: bool | None = None,
    ) -> None:
        message: dict[str, object] = {
            "type": "state",
            "sessionId": session_id,
            "playerState": state,
            "currentTime": max(0.0, current_time),
        }
        if idle_reason:
            message["idleReason"] = idle_reason
        if volume is not None:
            message["volume"] = volume
        if muted is not None:
            message["muted"] = muted
        await self._send(message)

    async def _send(self, message: dict[str, object]) -> None:
        if self._websocket is not None:
            await self._websocket.send(json.dumps(message, separators=(",", ":")))


def _optional_float(value: object) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Expose a Linux audio player through Vibecast")
    parser.add_argument("--bridge", default="ws://127.0.0.1:8010/player")
    parser.add_argument("--name", default="Audio Lab Laptop")
    parser.add_argument("--player-id")
    parser.add_argument(
        "--backend", choices=["command", *output_names()], default="command"
    )
    parser.add_argument("--player-command", default="mpv --no-video --audio-display=no {url}")
    parser.add_argument("--airplay-config", type=Path, help="explicit AirPlay target JSON; keep pairing credentials private")
    parser.add_argument("--target-config", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--cliairplay", default="cliairplay")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--airplay-latency", type=int, default=600)
    parser.add_argument("--airplay-reconnect-on-load", action="store_true",
                        help="fallback to separate AirPlay connections for each load/seek")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument('--artwork-endpoint')
    parser.add_argument('--artwork-public-url')
    return parser


def create_output(args: argparse.Namespace) -> tuple[AudioBackend, str]:
    if args.backend == "airplay":
        from .airplay import load_airplay_target

        if args.airplay_config is None:
            raise ValueError("--backend airplay requires --airplay-config")
        target = load_airplay_target(args.airplay_config)
        if not args.player_id and not target.device_id.strip():
            raise ValueError("AirPlay requires device_id in configuration or explicit --player-id")
        stable_id = target.device_id.strip().lower().replace(":", "").replace("-", "")
        player_id = args.player_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cast-audio-lab:airplay:{stable_id}"))
        return create_output_backend(args.backend, args), player_id
    if args.airplay_config is not None:
        raise ValueError("--airplay-config requires --backend airplay")
    if args.target_config is not None and args.backend not in {"dlna", "sonos"}:
        raise ValueError("--target-config requires --backend dlna or sonos")
    backend = (
        create_output_backend(args.backend, args)
        if args.backend in output_names()
        else CommandAudioBackend(args.player_command)
    )
    player_id = args.player_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cast-audio-lab:{args.name}"))
    return backend, player_id


async def run_player(player: VibecastAudioPlayer) -> None:
    try:
        await player.run()
    finally:
        await player._cancel_artwork()
        await player.backend.shutdown()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        backend, player_id = create_output(args)
    except (OSError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    player = VibecastAudioPlayer(args.bridge, player_id, args.name, backend,
        artwork_endpoint=args.artwork_endpoint, artwork_public_url=args.artwork_public_url)
    try:
        asyncio.run(run_player(player))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
