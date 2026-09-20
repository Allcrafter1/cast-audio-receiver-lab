"""Minimal receiving side of YouTube's undocumented Lounge protocol.

The protocol is not a public YouTube API and may change without notice.  This
module deliberately separates its command model from discovery (DIAL or Cast)
and from media URL resolution so those pieces can be replaced independently.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Protocol

from cast_audio_lab.backend import AudioBackend, MediaMetadata, PlaybackStatus


LOG = logging.getLogger(__name__)
LOUNGE_BASE = "https://www.youtube.com/api/lounge"
LOUNGE_BIND = f"{LOUNGE_BASE}/bc/bind"


class LoungeError(RuntimeError):
    """A Lounge request or response was unusable."""


class LoungeHttpError(LoungeError):
    def __init__(self, status: int, body: bytes = b"") -> None:
        super().__init__(f"Lounge HTTP {status}: {body[:256]!r}")
        self.status = status


class LoungeFrameDecoder:
    """Incrementally decode ``<UTF-8-byte-count>\\n<JSON>`` frames."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self._buffer.extend(data)
        frames: list[bytes] = []
        while True:
            while self._buffer[:1] in (b"\r", b"\n"):
                del self._buffer[:1]
            newline = self._buffer.find(b"\n")
            if newline < 0:
                break
            try:
                length = int(self._buffer[:newline].strip())
            except ValueError as exc:
                raise LoungeError("invalid Lounge frame length") from exc
            if length <= 0:
                del self._buffer[: newline + 1]
                continue
            start = newline + 1
            end = start + length
            if len(self._buffer) < end:
                break
            frames.append(bytes(self._buffer[start:end]))
            del self._buffer[:end]
        return frames

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)


@dataclass(slots=True, frozen=True)
class LoungeCommand:
    index: int
    name: str
    args: Any = None


def parse_command_frame(frame: bytes | str) -> list[LoungeCommand]:
    """Parse the command array carried by one Lounge frame."""

    try:
        value = json.loads(frame)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LoungeError("invalid Lounge command JSON") from exc
    if not isinstance(value, list):
        raise LoungeError("Lounge frame is not a command array")
    commands: list[LoungeCommand] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], int)
            or not isinstance(item[1], list)
            or not item[1]
            or not isinstance(item[1][0], str)
        ):
            continue
        commands.append(
            LoungeCommand(
                index=item[0],
                name=item[1][0],
                args=item[1][1] if len(item[1]) > 1 else None,
            )
        )
    return commands


@dataclass(slots=True, frozen=True)
class AudioSource:
    url: str
    content_type: str = "audio/webm"
    duration: float | None = None
    title: str | None = None


class YouTubeAudioResolver(Protocol):
    async def resolve(
        self, video_id: str, credential_transfer_token: str | None = None
    ) -> AudioSource: ...


class YtDlpAudioResolver:
    """Resolve a YouTube video ID through the optional ``yt-dlp`` package."""

    async def resolve(
        self, video_id: str, credential_transfer_token: str | None = None
    ) -> AudioSource:
        del credential_transfer_token  # Reserved for a future Innertube resolver.
        return await asyncio.to_thread(self._resolve_sync, video_id)

    @staticmethod
    def _resolve_sync(video_id: str) -> AudioSource:
        try:
            import yt_dlp  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LoungeError(
                "YouTube audio resolution needs the optional 'yt-dlp' package"
            ) from exc

        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(watch_url, download=False)
        if not isinstance(info, dict) or not isinstance(info.get("url"), str):
            raise LoungeError(f"yt-dlp returned no playable URL for {video_id}")
        content_type = info.get("http_headers", {}).get("Content-Type")
        if not isinstance(content_type, str):
            extension = info.get("ext")
            content_type = {
                "m4a": "audio/mp4",
                "mp4": "audio/mp4",
                "opus": "audio/ogg",
                "webm": "audio/webm",
            }.get(extension, "audio/webm")
        duration = info.get("duration")
        return AudioSource(
            url=info["url"],
            content_type=content_type,
            duration=float(duration) if isinstance(duration, (int, float)) else None,
            title=info.get("title") if isinstance(info.get("title"), str) else None,
        )


@dataclass(slots=True, frozen=True)
class LoungeOutgoing:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    command_id: int | None = None


@dataclass(slots=True)
class LoungeQueue:
    video_ids: list[str] = field(default_factory=list)
    index: int = 0
    current_video_id: str | None = None
    duration: float | None = None

    @property
    def has_previous(self) -> bool:
        return self.index > 0

    @property
    def has_next(self) -> bool:
        return self.index + 1 < len(self.video_ids)


class LoungeCommandEngine:
    """Translate Lounge remote commands into the shared audio backend."""

    def __init__(
        self,
        backend: AudioBackend,
        resolver: YouTubeAudioResolver,
        *,
        autoplay_on_set_playlist: bool = True,
    ) -> None:
        self.backend = backend
        self.resolver = resolver
        self.autoplay_on_set_playlist = autoplay_on_set_playlist
        self.queue = LoungeQueue()
        self.last_command_index = -1
        self.session_id: str | None = None
        self.gsession_id: str | None = None

    async def handle(self, command: LoungeCommand) -> list[LoungeOutgoing]:
        if command.name == "c":
            self.session_id = command.args if isinstance(command.args, str) else None
            return []
        if command.name == "S":
            self.gsession_id = (
                command.args if isinstance(command.args, str) else None
            )
            return []
        if command.index <= self.last_command_index:
            return []
        self.last_command_index = command.index

        args = command.args if isinstance(command.args, dict) else {}
        if command.name in ("setPlaylist", "updatePlaylist"):
            await self._set_playlist(args)
        elif command.name == "play":
            await self.backend.play()
        elif command.name == "pause":
            await self.backend.pause()
        elif command.name == "stopVideo":
            await self.backend.stop()
        elif command.name == "seekTo":
            await self.backend.seek(_number(args.get("newTime")))
        elif command.name == "next":
            await self._move(1)
        elif command.name == "previous":
            await self._move(-1)
        elif command.name == "setVolume":
            await self._set_volume(args)
        elif command.name == "getNowPlaying":
            return self.status_messages(command.index)
        else:
            return []
        return self.status_messages(command.index)

    async def _set_playlist(self, args: dict[str, Any]) -> None:
        raw_ids = args.get("videoIds")
        if isinstance(raw_ids, str):
            self.queue.video_ids = [
                item for item in raw_ids.split(",") if _valid_video_id(item)
            ]
        if not self.queue.video_ids:
            await self.backend.stop()
            self.queue = LoungeQueue()
            return

        requested_id = args.get("videoId")
        requested_index = _integer(args.get("currentIndex"), self.queue.index)
        if isinstance(requested_id, str) and requested_id in self.queue.video_ids:
            requested_index = self.queue.video_ids.index(requested_id)
        requested_index = max(0, min(requested_index, len(self.queue.video_ids) - 1))
        candidate = (
            requested_id
            if isinstance(requested_id, str) and _valid_video_id(requested_id)
            else self.queue.video_ids[requested_index]
        )

        # A queue-only update should not restart an already playing item.
        status = self.backend.status()
        if (
            candidate == self.queue.current_video_id
            and status.state != "IDLE"
            and not isinstance(requested_id, str)
        ):
            self.queue.index = requested_index
            return

        self.queue.index = requested_index
        self.queue.current_video_id = candidate
        source = await self.resolver.resolve(
            candidate,
            args.get("ctt") if isinstance(args.get("ctt"), str) else None,
        )
        self.queue.duration = source.duration
        start_time = _number(args.get("currentTime"))
        await self.backend.set_metadata(
            MediaMetadata(
                title=source.title or "",
                item_id=candidate,
                duration=source.duration,
            )
        )
        await self.backend.load(
            source.url,
            source.content_type,
            self.autoplay_on_set_playlist,
            start_time,
        )

    async def _move(self, offset: int) -> None:
        if not self.queue.video_ids:
            return
        target = max(
            0, min(self.queue.index + offset, len(self.queue.video_ids) - 1)
        )
        if target == self.queue.index:
            return
        video_id = self.queue.video_ids[target]
        self.queue.index = target
        self.queue.current_video_id = video_id
        source = await self.resolver.resolve(video_id)
        self.queue.duration = source.duration
        await self.backend.set_metadata(
            MediaMetadata(
                title=source.title or "",
                item_id=video_id,
                duration=source.duration,
            )
        )
        await self.backend.load(source.url, source.content_type, True, 0.0)

    async def _set_volume(self, args: dict[str, Any]) -> None:
        status = self.backend.status()
        level = status.volume
        raw_volume = args.get("volume")
        if raw_volume is not None:
            level = _number(raw_volume) / 100.0
        muted = _boolean(args.get("muted"), status.muted)
        await self.backend.set_volume(level, muted)

    def status_messages(self, command_id: int | None = None) -> list[LoungeOutgoing]:
        status = self.backend.status()
        state = _player_state(status)
        common: dict[str, Any] = {
            "state": state,
            "currentTime": status.current_time,
            "seekableStartTime": 0,
        }
        if self.queue.duration is not None:
            common.update(
                {
                    "duration": self.queue.duration,
                    "seekableEndTime": self.queue.duration,
                    "loadedTime": self.queue.duration,
                }
            )
        now_playing = {
            **common,
            "currentIndex": self.queue.index,
        }
        if self.queue.current_video_id:
            now_playing["videoId"] = self.queue.current_video_id
        return [
            LoungeOutgoing(
                "onHasPreviousNextChanged",
                {
                    "hasPrevious": self.queue.has_previous,
                    "hasNext": self.queue.has_next,
                },
                command_id,
            ),
            LoungeOutgoing("nowPlaying", now_playing, command_id),
            LoungeOutgoing("onStateChange", common, command_id),
        ]


@dataclass(slots=True)
class LoungeCredentials:
    screen_id: str
    lounge_token: str


class LoungeClient:
    """Network session for a Lounge screen.

    ``bootstrap`` obtains ephemeral screen credentials and opens the initial
    bind. ``run`` then maintains the streaming backchannel until cancelled.
    """

    def __init__(
        self,
        name: str,
        device_id: str,
        engine: LoungeCommandEngine,
        *,
        timeout: float = 65.0,
    ) -> None:
        self.name = name
        self.device_id = device_id
        self.engine = engine
        self.timeout = timeout
        self.credentials: LoungeCredentials | None = None
        self._offset = 0
        self._stopping = False

    async def bootstrap(self) -> LoungeCredentials:
        screen_id = (
            await self._request(
                "GET", f"{LOUNGE_BASE}/pairing/generate_screen_id"
            )
        ).decode().strip()
        if not screen_id:
            raise LoungeError("YouTube returned an empty screen ID")
        token_body = await self._request(
            "POST",
            f"{LOUNGE_BASE}/pairing/get_lounge_token_batch",
            {"screen_ids": screen_id},
        )
        try:
            token_json = json.loads(token_body)
            lounge_token = token_json["screens"][0]["loungeToken"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LoungeError("YouTube returned no Lounge token") from exc
        if not isinstance(lounge_token, str) or not lounge_token:
            raise LoungeError("YouTube returned an invalid Lounge token")
        self.credentials = LoungeCredentials(screen_id, lounge_token)
        await self._bind()
        return self.credentials

    async def register_pairing_code(self, pairing_code: str) -> None:
        if self.credentials is None:
            raise LoungeError("Lounge client has not been bootstrapped")
        await self._request(
            "POST",
            f"{LOUNGE_BASE}/pairing/register_pairing_code",
            {
                "access_type": "permanent",
                "app": "lb-v4",
                "pairing_code": pairing_code,
                "screen_id": self.credentials.screen_id,
                "screen_name": self.name,
                "device_id": self.device_id,
            },
        )

    async def run(self) -> None:
        if self.credentials is None:
            await self.bootstrap()
        self._stopping = False
        delay = 1.0
        while not self._stopping:
            try:
                async for frame in self._backchannel_frames():
                    outgoing = await self._process_frame(frame)
                    if outgoing:
                        await self.send(outgoing)
                delay = 1.0
            except asyncio.CancelledError:
                raise
            except LoungeHttpError as exc:
                LOG.warning(
                    "Lounge backchannel HTTP %d; rebuilding session", exc.status
                )
                recovered = False
                try:
                    if exc.status == 404:
                        await self._refresh_token()
                    if exc.status in (400, 404, 410):
                        await self._bind()
                        recovered = True
                except Exception as recovery_error:
                    LOG.warning(
                        "Lounge session recovery failed: %s", recovery_error
                    )
                if recovered:
                    delay = 1.0
                else:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30.0)
            except Exception as exc:
                LOG.warning("Lounge backchannel reconnect after error: %s", exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
                if self.engine.session_id is None or self.engine.gsession_id is None:
                    await self._bind()

    def stop(self) -> None:
        self._stopping = True

    async def send(self, messages: list[LoungeOutgoing]) -> None:
        if not messages:
            return
        params = self._base_params("1337")
        if self.engine.session_id:
            params["SID"] = self.engine.session_id
        if self.engine.gsession_id:
            params["gsessionid"] = self.engine.gsession_id
        if messages[0].command_id is not None:
            params["AID"] = str(messages[0].command_id)
        form: list[tuple[str, Any]] = [
            ("count", len(messages)),
            ("ofs", self._offset),
        ]
        self._offset += len(messages)
        for index, message in enumerate(messages):
            form.append((f"req{index}__sc", message.name))
            form.extend(
                (f"req{index}_{key}", _form_value(value))
                for key, value in message.args.items()
            )
        await self._request("POST", _url(LOUNGE_BIND, params), form)

    async def _bind(self) -> None:
        self.engine.session_id = None
        self.engine.gsession_id = None
        self.engine.last_command_index = -1
        self._offset = 0
        body = await self._request(
            "POST",
            _url(LOUNGE_BIND, self._base_params("1337")),
            {"count": 0},
        )
        decoder = LoungeFrameDecoder()
        outgoing: list[LoungeOutgoing] = []
        for frame in decoder.feed(body):
            outgoing.extend(await self._process_frame(frame))
        if not self.engine.session_id or not self.engine.gsession_id:
            raise LoungeError("initial Lounge bind returned no session IDs")
        if outgoing:
            await self.send(outgoing)

    async def _refresh_token(self) -> None:
        if self.credentials is None:
            raise LoungeError("Lounge credentials are unavailable")
        token_body = await self._request(
            "POST",
            f"{LOUNGE_BASE}/pairing/get_lounge_token_batch",
            {"screen_ids": self.credentials.screen_id},
        )
        try:
            value = json.loads(token_body)["screens"][0]["loungeToken"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LoungeError("YouTube returned no refreshed Lounge token") from exc
        if not isinstance(value, str) or not value:
            raise LoungeError("YouTube returned an invalid refreshed Lounge token")
        self.credentials.lounge_token = value

    async def _process_frame(self, frame: bytes) -> list[LoungeOutgoing]:
        outgoing: list[LoungeOutgoing] = []
        for command in parse_command_frame(frame):
            if command.name != "noop":
                LOG.info(
                    "Lounge command %s (index %d)",
                    command.name,
                    command.index,
                )
            outgoing.extend(await self.engine.handle(command))
        return outgoing

    async def _backchannel_frames(self) -> AsyncIterator[bytes]:
        if not self.engine.session_id or not self.engine.gsession_id:
            raise LoungeError("Lounge session is not bound")
        params = self._base_params("rpc")
        params.update(
            {
                "CI": "0",
                "SID": self.engine.session_id,
                "gsessionid": self.engine.gsession_id,
            }
        )
        url = _url("https://www.youtube.com/api/lounge/bc/bind", params)
        decoder = LoungeFrameDecoder()
        async for data in _stream_http_body(url, self.timeout):
            for frame in decoder.feed(data):
                yield frame

    def _base_params(self, rid: str) -> dict[str, str]:
        if self.credentials is None:
            raise LoungeError("Lounge credentials are unavailable")
        return {
            "device": "LOUNGE_SCREEN",
            "theme": "cl",
            "capabilities": "vsp",
            "mdxVersion": "2",
            "VER": "8",
            "v": "2",
            "t": "1",
            "app": "lb-v4",
            "RID": rid,
            "name": self.name,
            "id": self.device_id,
            "loungeIdToken": self.credentials.lounge_token,
            "zx": _zx(),
        }

    async def _request(
        self,
        method: str,
        url: str,
        form: dict[str, Any] | list[tuple[str, Any]] | None = None,
    ) -> bytes:
        return await asyncio.to_thread(
            _request_sync, method, url, form, self.timeout
        )


def _request_sync(
    method: str,
    url: str,
    form: dict[str, Any] | list[tuple[str, Any]] | None,
    timeout: float,
) -> bytes:
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"User-Agent": "CastAudioReceiverLab/0.2"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read(1024)
        raise LoungeHttpError(exc.code, body) from exc
    except OSError as exc:
        raise LoungeError(f"Lounge request failed: {exc}") from exc


async def _stream_http_body(
    url: str, timeout: float, redirects: int = 5
) -> AsyncIterator[bytes]:
    current = url
    for _ in range(redirects + 1):
        parsed = urllib.parse.urlsplit(current)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise LoungeError(f"unsupported backchannel URL: {current}")
        secure = parsed.scheme == "https"
        port = parsed.port or (443 if secure else 80)
        ssl_context = ssl.create_default_context() if secure else None
        reader, writer = await asyncio.open_connection(
            parsed.hostname,
            port,
            ssl=ssl_context,
            server_hostname=parsed.hostname if secure else None,
        )
        target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        request = (
            f"GET {target} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n"
            "User-Agent: CastAudioReceiverLab/0.2\r\n\r\n"
        )
        writer.write(request.encode("ascii"))
        await writer.drain()
        status_line = await asyncio.wait_for(reader.readline(), timeout)
        try:
            status = int(status_line.split()[1])
        except (IndexError, ValueError) as exc:
            writer.close()
            raise LoungeError("invalid backchannel HTTP status") from exc
        headers: dict[str, str] = {}
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout)
            if line in (b"\r\n", b"\n", b""):
                break
            key, separator, value = line.decode("iso-8859-1").partition(":")
            if separator:
                headers[key.strip().lower()] = value.strip()
        if status in (301, 302, 303, 307, 308):
            location = headers.get("location")
            await _close_writer(writer)
            if not location:
                raise LoungeError("backchannel redirect has no Location")
            current = urllib.parse.urljoin(current, location)
            continue
        if status != 200:
            await _close_writer(writer)
            raise LoungeHttpError(status)
        try:
            if headers.get("transfer-encoding", "").lower() == "chunked":
                while True:
                    line = await asyncio.wait_for(reader.readline(), timeout)
                    size_text = line.split(b";", 1)[0].strip()
                    size = int(size_text, 16)
                    if size == 0:
                        break
                    data = await asyncio.wait_for(reader.readexactly(size), timeout)
                    await asyncio.wait_for(reader.readexactly(2), timeout)
                    yield data
            else:
                while data := await asyncio.wait_for(reader.read(8192), timeout):
                    yield data
        finally:
            await _close_writer(writer)
        return
    raise LoungeError("too many backchannel redirects")


async def _close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
    except (OSError, TimeoutError):
        # Some TLS peers send application data together with close_notify.
        # Closing a cancelled backchannel must not turn cancellation into a
        # reconnecting OSError loop or hold process shutdown indefinitely.
        pass


def _url(base: str, params: dict[str, Any]) -> str:
    return f"{base}?{urllib.parse.urlencode(params)}"


def _zx() -> str:
    return f"{secrets.randbelow(2**31):x}{int(time.time() * 1000):x}"


def _valid_video_id(value: str) -> bool:
    return 1 <= len(value) <= 64 and all(
        character.isalnum() or character in "_-" for character in value
    )


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _boolean(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1")
    return default


def _form_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _player_state(status: PlaybackStatus) -> int:
    if status.state == "IDLE" and status.idle_reason:
        return 4
    return {
        "IDLE": -1,
        "PLAYING": 1,
        "PAUSED": 2,
        "BUFFERING": 3,
    }.get(status.state, -1)
