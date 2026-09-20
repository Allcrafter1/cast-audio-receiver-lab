"""AirPlay output built around Music Assistant's ``cliairplay`` binary.

The module owns process plumbing, not the AirPlay protocol.  FFmpeg converts an
arbitrary Cast media URL to a persistent PCM stream and cliairplay handles
RAOP/AirPlay 2, pairing, timing, metadata and device-specific route selection.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import tempfile
import math
from urllib.parse import urlsplit
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .backend import ControlRequest, MediaMetadata, NullAudioBackend
from .artwork import prepare_square_artwork


LOG = logging.getLogger(__name__)
_LINE_RE = re.compile(r"^\[(?P<kind>STATUS|EVENT)\]\s+(?P<body>.*)$")


@dataclass(frozen=True, slots=True)
class AirPlayTarget:
    """A stable output selection, independent from the advertised Cast name."""

    host: str
    port: int = 7000
    protocol: str = "auto"
    device_id: str = ""
    name: str = ""
    credentials: str | None = field(default=None, repr=False)
    legacy_secret: str | None = field(default=None, repr=False)
    password: str | None = field(default=None, repr=False)
    interface: str | None = None
    txt: Mapping[str, str] = field(default_factory=dict)


def load_airplay_target(path: Path) -> AirPlayTarget:
    """Load an explicit route; pairing secrets need not be CLI arguments."""
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("AirPlay configuration must be a JSON object")
    allowed = set(AirPlayTarget.__dataclass_fields__)
    if set(data) - allowed:
        raise ValueError("AirPlay configuration contains unsupported fields")
    for name in allowed - {"port", "txt"}:
        if name in data and not isinstance(data[name], str):
            raise ValueError(f"AirPlay field {name} must be a string")
    if not data.get("host", "").strip():
        raise ValueError("AirPlay configuration requires host")
    port = data.get("port", 7000)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("AirPlay port must be between 1 and 65535")
    if data.get("protocol", "auto") not in {"auto", "raop", "airplay2", "airplay2-compat"}:
        raise ValueError("unsupported AirPlay protocol")
    txt = data.get("txt", {})
    if not isinstance(txt, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in txt.items()):
        raise ValueError("AirPlay txt must map strings to strings")
    return AirPlayTarget(**data)


@dataclass(frozen=True, slots=True)
class CliAirPlayEvent:
    kind: str
    name: str
    values: Mapping[str, str]
    raw: str


EventHandler = Callable[[CliAirPlayEvent], Awaitable[None] | None]


def parse_cliairplay_line(line: str) -> CliAirPlayEvent | None:
    """Parse cliairplay's stable line-oriented status/event interface."""

    match = _LINE_RE.match(line.strip())
    if not match:
        return None
    fields = match.group("body").split()
    if not fields:
        return None
    values: dict[str, str] = {}
    positional: list[str] = []
    for value in fields:
        if "=" in value:
            key, item = value.split("=", 1)
            values[key] = item
        else:
            positional.append(value)
    name = " ".join(positional)
    if not name and values:
        name = next(iter(values))
    return CliAirPlayEvent(
        kind=match.group("kind").lower(),
        name=name,
        values=values,
        raw=line.rstrip(),
    )


def cliairplay_argv(
    executable: str,
    target: AirPlayTarget,
    command_pipe: Path,
    *,
    volume: float,
    latency_ms: int,
    sample_rate: int = 44_100,
    channels: int = 2,
) -> list[str]:
    """Build an argument vector without invoking a shell."""

    if target.protocol not in {"auto", "raop", "airplay2", "airplay2-compat"}:
        raise ValueError(f"unsupported AirPlay protocol selection: {target.protocol}")
    argv = [
        executable,
        "--protocol",
        target.protocol,
        "--port",
        str(target.port),
        "--volume",
        str(round(max(0.0, min(1.0, volume)) * 100)),
        "--latency",
        str(max(100, min(3000, latency_ms))),
        "--samplerate",
        str(sample_rate),
        "--bitdepth",
        "16",
        "--channels",
        str(channels),
        "--cmdpipe",
        str(command_pipe),
    ]
    if target.device_id:
        # The pairing identity must remain stable across restarts.
        dacp_id = target.device_id.replace(":", "").replace("-", "")[-16:]
        argv.extend(("--dacp", dacp_id))
    if target.credentials:
        argv.extend(("--auth", target.credentials))
    if target.legacy_secret:
        argv.extend(("--secret", target.legacy_secret))
    if target.password:
        argv.extend(("--password", target.password))
    if target.interface:
        argv.extend(("--if", target.interface))
    if target.name:
        argv.extend(("--name", target.name))
    # The RAOP engine reads dedicated options, not the AirPlay2 --txt map.
    # In particular, omitting et falls back to 0,4 and wrongly attempts MFi
    # auth-setup against receivers advertising only 0,1.
    for key in ("et", "md", "am", "pk", "pw", "cn"):
        if key in target.txt:
            argv.extend((f"--{key}", target.txt[key]))
    if target.txt:
        # getopt consumes ONE argument for --txt. Separate argv entries become
        # positional input/host arguments and are rejected by the real CLI.
        argv.extend(("--txt", " ".join(
            f"{key}={value}" for key, value in sorted(target.txt.items())
        )))
    argv.append(target.host)
    return argv


def ffmpeg_pcm_argv(
    executable: str,
    url: str,
    *,
    start_time: float = 0.0,
    sample_rate: int = 44_100,
    channels: int = 2,
) -> list[str]:
    """Build the low-latency, codec-neutral PCM acquisition command."""

    argv = [executable, "-hide_banner", "-loglevel", "warning", "-nostdin"]
    if start_time > 0:
        # Input-side seek avoids decoding everything before the requested point.
        argv.extend(("-ss", f"{start_time:.3f}"))
    argv.extend(
        (
            "-i",
            url,
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            "-f",
            "s16le",
            "pipe:1",
        )
    )
    return argv


class AirPlayAudioBackend(NullAudioBackend):
    """Convert URL media to PCM and stream it to one AirPlay target.

    Keep the AirPlay transport and PCM pipe open across tracks. Only the decoder
    is replaced; acknowledged FLUSH barriers separate old and new samples.
    """

    def __init__(
        self,
        target: AirPlayTarget,
        *,
        cliairplay: str = "cliairplay",
        ffmpeg: str = "ffmpeg",
        latency_ms: int = 600,
        event_handler: EventHandler | None = None,
        persistent: bool = True,
    ) -> None:
        super().__init__()
        self.target = target
        self.cliairplay = cliairplay
        self.ffmpeg = ffmpeg
        self.latency_ms = latency_ms
        self.event_handler = event_handler
        self.persistent = persistent
        self._cli: asyncio.subprocess.Process | None = None
        self._decoder: asyncio.subprocess.Process | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._reader_tasks: list[asyncio.Task[None]] = []
        self._command_fd: int | None = None
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._lock = asyncio.Lock()
        self._input_finished = False
        self._autoplay = True
        self._aux_tasks: list[asyncio.Task[None]] = []
        self._audio_ready = False
        self._decoded_bytes = 0
        self._track_start = 0.0
        self._decoder_reader: asyncio.Task[None] | None = None
        self._flushed = asyncio.Event()
        self._track_started = False
        self._start_pending = False
        self._prepared_artwork_url: str | None = None

    async def load(
        self, url: str, content_type: str, autoplay: bool, start_time: float
    ) -> None:
        async with self._lock:
            reusable = self.persistent and self._status.idle_reason != "ERROR"
            self._track_started = False
            self._start_pending = False
            self._status.state = "BUFFERING"
            self._status.idle_reason = None
            self._set_position(max(0.0, start_time))
            self._emit_status()
            try:
                await self._prepare_transport(reusable)
                # A sender dying during FLUSH may report ERROR before the cold
                # fallback completes. That error belongs to the old transport.
                self._status.state = "BUFFERING"
                self._status.idle_reason = None
                self._input_finished = False
                self._audio_ready = False
                self._decoded_bytes = 0
                self._track_start = max(0.0, start_time)
                self._autoplay = autoplay
                LOG.info("AirPlay load start=%.3f duration=%s artwork=%s", start_time,
                         self.metadata.duration, bool(self.metadata.artwork_url))
                await self._start_pipeline(url, start_time)
                self._status.url = url
                self._status.content_type = content_type
                await self._send_metadata()
                self._start_pending = True
                await self._command("START_UNIX_MS=0", "ACTION=START")
                self._aux_tasks.append(asyncio.create_task(self._progress_updates()))
                if self.metadata.artwork_url:
                    self._aux_tasks.append(asyncio.create_task(self._deliver_artwork()))
                if not autoplay:
                    await self._command("ACTION=PAUSE")
                    self._status.state = "PAUSED"
                    self._emit_status()
            except BaseException:
                # Includes cancellation: partially started helpers must not live
                # past the failed load or prevent the next connection attempt.
                await self._stop_pipeline()
                self._status.url = None
                self._status.state = "IDLE"
                self._status.idle_reason = "ERROR"
                self._set_position(0.0)
                self._emit_status()
                raise

    async def play(self) -> None:
        self._autoplay = True
        await self._command("ACTION=PLAY")
        await super().play()
        await self._send_progress()

    async def pause(self) -> None:
        self._autoplay = False
        await self._command("ACTION=PAUSE")
        if self._status.state == "BUFFERING":
            self._status.state = "PAUSED"
            self._emit_status()
        await super().pause()
        await self._send_progress()

    async def stop(self) -> None:
        async with self._lock:
            await self._command("ACTION=STOP")
            await self._stop_pipeline()
            await super().stop()

    async def seek(self, position: float) -> None:
        status = self.status()
        if status.url:
            await self.load(
                status.url,
                status.content_type,
                status.state == "PLAYING" or (status.state == "BUFFERING" and self._autoplay),
                max(0.0, position),
            )

    async def set_volume(self, level: float, muted: bool) -> None:
        effective = 0.0 if muted else max(0.0, min(1.0, level))
        await self._command(f"VOLUME={round(effective * 100)}")
        await super().set_volume(level, muted)

    async def set_metadata(self, metadata: MediaMetadata) -> None:
        await super().set_metadata(metadata)
        # The adapter sets next-track metadata before load. Do not relabel the
        # old transport with the new title and the old position.

    async def shutdown(self) -> None:
        await self.stop()

    async def _start_pipeline(self, url: str, start_time: float) -> None:
        if self._cli is None:
            await self._start_transport()
        assert self._cli is not None and self._cli.stdin is not None
        self._decoder = await asyncio.create_subprocess_exec(
            *ffmpeg_pcm_argv(self.ffmpeg, url, start_time=start_time),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self._decoder.stdout is not None
        assert self._decoder.stderr is not None
        self._decoder_reader = asyncio.create_task(self._read_ffmpeg_log(self._decoder.stderr))
        self._pump_task = asyncio.create_task(self._pump_pcm(self._decoder.stdout, self._cli.stdin))

    async def _prepare_transport(self, reusable: bool) -> None:
        if not reusable or self._cli is None or self._cli.returncode is not None:
            await self._stop_pipeline()
            return
        await self._stop_track()
        try:
            assert self._cli.stdin is not None
            writer = self._cli.stdin
            # Canceling the pump stops new writes, but asyncio may still have
            # old bytes buffered. First FLUSH unblocks a paused/full input ring.
            # Drain the Python buffer, then FLUSH again to discard its tail.
            buffered = writer.transport.get_write_buffer_size() > 0
            await self._flush_transport()
            if buffered:
                await asyncio.wait_for(writer.drain(), 2)
                # drain() only guarantees the low watermark, not an empty pipe.
                deadline = asyncio.get_running_loop().time() + 2
                while writer.transport.get_write_buffer_size():
                    if asyncio.get_running_loop().time() >= deadline:
                        raise TimeoutError("AirPlay writer did not drain")
                    await asyncio.sleep(0.01)
                await self._flush_transport()
            LOG.info("AirPlay transport reused pid=%s", self._cli.pid)
        except (OSError, TimeoutError, RuntimeError):
            LOG.warning("AirPlay warm transition failed; reconnecting")
            await self._stop_pipeline()

    async def _flush_transport(self) -> None:
        self._flushed.clear()
        await self._command("ACTION=FLUSH")
        await asyncio.wait_for(self._flushed.wait(), 2)
        if self._cli is None or self._cli.returncode is not None:
            raise RuntimeError("AirPlay transport ended during flush")

    async def _start_transport(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory(prefix="cast-airplay-")
        self._temporary_directory = temporary_directory
        command_pipe = Path(temporary_directory.name) / "commands"
        os.mkfifo(command_pipe, 0o600)
        self._cli = await asyncio.create_subprocess_exec(
            *cliairplay_argv(
                self.cliairplay,
                self.target,
                command_pipe,
                volume=0.0 if self._status.muted else self._status.volume,
                latency_ms=self.latency_ms,
            ),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert self._cli.stdout is not None
        assert self._cli.stderr is not None
        self._reader_tasks = [
            asyncio.create_task(self._read_events(self._cli.stdout)),
            asyncio.create_task(self._read_events(self._cli.stderr)),
            asyncio.create_task(self._watch_cli(self._cli)),
        ]
        self._command_fd = await self._open_command_pipe(command_pipe)
        LOG.info("AirPlay transport created pid=%s", self._cli.pid)

    async def _open_command_pipe(self, path: Path) -> int:
        deadline = asyncio.get_running_loop().time() + 5.0
        while True:
            try:
                return os.open(path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError:
                if self._cli is None or self._cli.returncode is not None:
                    raise RuntimeError("cliairplay exited before opening command pipe")
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError("cliairplay did not open its command pipe")
                await asyncio.sleep(0.05)

    async def _watch_cli(self, process: asyncio.subprocess.Process) -> None:
        code = await process.wait()
        if process is self._cli and self._status.state in {"BUFFERING", "PLAYING", "PAUSED"}:
            LOG.warning("AirPlay sender exited unexpectedly code=%s", code)
            self._set_position(self._current_position())
            self._status.state = "IDLE"
            self._status.idle_reason = "ERROR"
            self._emit_status()

    async def _command(self, *lines: str) -> None:
        if self._command_fd is None:
            return
        payload = "".join(f"{line}\n" for line in lines).encode()
        try:
            os.write(self._command_fd, payload)
        except (BrokenPipeError, BlockingIOError, OSError) as exc:
            LOG.warning("Unable to send cliairplay command: %s", exc)

    async def _send_metadata(self) -> None:
        metadata = self.metadata
        lines = [
            f"TITLE={_one_line(metadata.title)}",
            f"ARTIST={_one_line(metadata.artist)}",
            f"ALBUM={_one_line(metadata.album)}",
            f"ITEMID={_one_line(metadata.item_id)}",
        ]
        if metadata.duration is not None:
            lines.append(f"DURATION={max(0.0, metadata.duration):.3f}")
        lines.append(f"PROGRESS={max(0, int(self._current_position()))}")
        lines.append("ACTION=SENDMETA")
        await self._command(*lines)

    async def _send_progress(self) -> None:
        if not self._audio_ready or self._status.state not in {"PLAYING", "PAUSED"}:
            return
        duration = self.metadata.duration or 0.0
        await self._command(f"DURATION={max(0, int(duration))}",
                            f"PROGRESS={max(0, int(self._current_position()))}")

    async def _progress_updates(self) -> None:
        while True:
            await asyncio.sleep(2)
            await self._send_progress()

    async def _deliver_artwork(self) -> None:
        # cliairplay supports local images, not HTTPS. The shared converter
        # keeps this protocol-specific adapter on the same square/quality
        # policy that a future Cast/HA image endpoint can reuse.
        url = self.metadata.artwork_url
        if urlsplit(url).scheme not in {"http", "https"} or not self._temporary_directory:
            return
        path = Path(self._temporary_directory.name) / "cover.jpg"
        try:
            cached = self._prepared_artwork_url == url and path.is_file()
            if cached or await prepare_square_artwork(url, path, self.ffmpeg):
                self._prepared_artwork_url = url
                # ARTWORK delivers only art: do not resend track metadata and
                # overwrite a newer position while the image was downloading.
                await self._command(f"ARTWORK={path}")
                LOG.info("AirPlay artwork submitted bytes=%d", path.stat().st_size)
            else:
                LOG.warning("AirPlay artwork unavailable")
        except (OSError, TimeoutError):
            LOG.warning("AirPlay artwork fetch failed (URL omitted)")

    async def _read_events(self, reader: asyncio.StreamReader) -> None:
        while line := await reader.readline():
            text = line.decode(errors="replace").rstrip()
            event = parse_cliairplay_line(text)
            if event is None:
                LOG.debug("cliairplay diagnostic received (content omitted)")
                continue
            if event.kind == "status" and event.name in {"route", "connected", "audio", "started", "stopped", "eof", "flushed"}:
                LOG.info("AirPlay status=%s", event.name)
            else:
                LOG.debug("cliairplay structured event received")
            if event.kind == "event" and event.name == "remote":
                await self._apply_remote_command(event.values.get("command", ""))
            if event.kind == "status" and event.name == "flushed":
                self._flushed.set()
            if event.kind == "status" and event.name == "started" and self._start_pending:
                self._start_pending = False
                self._track_started = True
                if self._status.state == "BUFFERING" and self._autoplay:
                    self._set_position(self._position_at_change)
                    self._status.state = "PLAYING"
                    self._emit_status()
                await self._command(f"PROGRESS={max(0, int(self._current_position()))}")
            if event.kind == "status" and event.name == "audio":
                self._audio_ready = True
                await self._send_progress()
            if event.kind == "status" and event.name == "playing" and self.persistent:
                try:
                    elapsed = float(event.values.get("elapsed_ms", "nan")) / 1000
                except ValueError:
                    elapsed = math.nan
                if (self._track_started and self._input_finished and self._status.state == "PLAYING"
                        and math.isfinite(elapsed) and elapsed >= self._decoded_bytes / 176400):
                    # The transport's elapsed clock subtracts its audible lag.
                    # Tail silence keeps it running past the final music frame.
                    # No metadata-duration timer or EOF on the shared stdin.
                    self._set_position(self._track_start + self._decoded_bytes / 176400)
                    self._status.state = "IDLE"
                    self._status.idle_reason = "FINISHED"
                    LOG.info("AirPlay track drained decoded_s=%.3f elapsed_s=%.3f",
                             self._decoded_bytes / 176400, elapsed)
                    self._emit_status()
            if event.kind == "status" and event.name == "eof" and self._input_finished and not self.persistent:
                # Upstream reports EOF after the receiver buffer drains, not
                # merely when FFmpeg has decoded the last sample.
                if self._status.state in {"PLAYING", "PAUSED", "BUFFERING"}:
                    self._set_position(self._current_position())
                    self._status.state = "IDLE"
                    self._status.idle_reason = "FINISHED"
                    self._emit_status()
            if self.event_handler:
                result = self.event_handler(event)
                if result is not None:
                    await result

    async def _read_ffmpeg_log(self, reader: asyncio.StreamReader) -> None:
        # Draining stderr is required: an FFmpeg process otherwise eventually
        # blocks on a full pipe and starves the AirPlay output.
        warned = False
        categories = set()
        while line := await reader.readline():
            # Fixed labels only; never print signed URLs or raw decoder lines.
            lower = line.lower()
            for needle, category in ((b'403', 'http_403'), (b'404', 'http_404'),
                    (b'429', 'http_429'), (b'timed out', 'timeout'),
                    (b'connection reset', 'connection_reset'),
                    (b'input/output error', 'io_error'),
                    (b'premature', 'truncated'), (b'invalid data', 'invalid_data')):
                if needle in lower and category not in categories:
                    categories.add(category)
                    LOG.warning("AirPlay decoder category=%s", category)
            if not warned:
                LOG.warning("ffmpeg decoder diagnostic received (URLs/content omitted)")
                warned = True

    async def _apply_remote_command(self, command: str) -> None:
        command = command.lower()
        if command == "play":
            await super().play()
            self._emit_control(ControlRequest("play"))
        elif command == "pause":
            await super().pause()
            self._emit_control(ControlRequest("pause"))
        elif command == "toggle_play_pause":
            if self._status.state == "PLAYING":
                await super().pause()
                self._emit_control(ControlRequest("pause"))
            else:
                await super().play()
                self._emit_control(ControlRequest("play"))
        elif command == "stop":
            await super().stop()
            self._emit_control(ControlRequest("stop"))
        elif command in {"next", "previous"}:
            self._emit_control(ControlRequest(command))

    async def _pump_pcm(
        self, source: asyncio.StreamReader, destination: asyncio.StreamWriter
    ) -> None:
        try:
            while chunk := await source.read(64 * 1024):
                destination.write(chunk)
                await destination.drain()
                self._decoded_bytes += len(chunk)
            decoder = self._decoder
            if decoder is not None:
                returncode = await decoder.wait()
                decoded_seconds = self._decoded_bytes / (44100 * 2 * 2)
                expected = (self.metadata.duration or 0.0) - self._track_start
                truncated = math.isfinite(expected) and expected > 3 and decoded_seconds < expected - 3
                LOG.info("AirPlay decoder ended code=%s decoded_s=%.3f expected_s=%.3f truncated=%s",
                         returncode, decoded_seconds, expected, truncated)
                if returncode != 0 or truncated or not self._decoded_bytes:
                    self._status.state = "IDLE"
                    self._status.idle_reason = "ERROR"
                    self._emit_status()
                else:
                    self._input_finished = True
            if self.persistent:
                # Keep stdin open. Supply silence after the final music sample
                # so the transport can report when that sample is audible.
                # Backpressure bounds queued silence; pause stops the clock.
                while self._input_finished and self._status.state in {"PLAYING", "PAUSED", "BUFFERING"}:
                    destination.write(bytes(4096))
                    await destination.drain()
                    await asyncio.sleep(0)
            else:
                destination.close()
        except (BrokenPipeError, ConnectionResetError):
            LOG.warning("AirPlay PCM transport closed unexpectedly")
            self._status.state = "IDLE"
            self._status.idle_reason = "ERROR"
            self._emit_status()

    async def _stop_track(self) -> None:
        self._input_finished = False
        self._audio_ready = False
        for task in self._aux_tasks:
            task.cancel()
        await asyncio.gather(*self._aux_tasks, return_exceptions=True)
        self._aux_tasks.clear()
        decoder, self._decoder = self._decoder, None
        if decoder and decoder.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                decoder.terminate()
        if self._pump_task:
            self._pump_task.cancel()
            await asyncio.gather(self._pump_task, return_exceptions=True)
            self._pump_task = None
        if self._decoder_reader:
            self._decoder_reader.cancel()
            await asyncio.gather(self._decoder_reader, return_exceptions=True)
            self._decoder_reader = None
        if decoder:
            await _reap_process(decoder)

    async def _stop_pipeline(self) -> None:
        self._track_started = False
        self._start_pending = False
        await self._stop_track()
        await self._command("ACTION=STOP")
        cli, self._cli = self._cli, None
        for task in self._reader_tasks:
            task.cancel()
        if self._reader_tasks:
            await asyncio.gather(*self._reader_tasks, return_exceptions=True)
        self._reader_tasks.clear()
        if cli:
            await _reap_process(cli)
        if self._command_fd is not None:
            os.close(self._command_fd)
            self._command_fd = None
        if self._temporary_directory:
            self._temporary_directory.cleanup()
            self._temporary_directory = None
        self._prepared_artwork_url = None


async def _reap_process(process: asyncio.subprocess.Process) -> None:
    """Drain pipes before reaping: wait alone can hang on stdout backpressure."""
    if process.stdin:
        process.stdin.close()
    async def drain(reader: asyncio.StreamReader | None) -> None:
        if reader:
            while await reader.read(64 * 1024):
                pass
    drains = [asyncio.create_task(drain(reader)) for reader in (process.stdout, process.stderr)]
    try:
        if process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 2.0)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await asyncio.wait_for(process.wait(), 2.0)
    finally:
        for task in drains:
            task.cancel()
        await asyncio.gather(*drains, return_exceptions=True)


def _one_line(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")
