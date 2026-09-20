"""mpv JSON IPC output with decoder-owned position and EOF feedback."""
import asyncio
import json
import logging
import tempfile
from pathlib import Path

from .backend import NullAudioBackend

LOGGER = logging.getLogger(__name__)


class MpvAudioBackend(NullAudioBackend):
    def __init__(self):
        super().__init__()
        self._process = None
        self._writer = None
        self._reader_task = None
        self._temp = None
        self._pending = {}
        self._serial = 0
        self._autoplay = True
        self._loading = False
        self._seeking = False

    def _current_position(self):
        return self._position_at_change

    async def _start(self):
        if self._writer is not None:
            return
        self._temp = tempfile.TemporaryDirectory(prefix="cast-mpv-")
        socket = str(Path(self._temp.name) / "ipc")
        self._process = await asyncio.create_subprocess_exec(
            "mpv", "--idle=yes", "--no-video", "--audio-display=no",
            "--ytdl=no", "--no-terminal", "--volume=100",
            "--input-ipc-server=" + socket,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                reader, self._writer = await asyncio.open_unix_connection(socket)
                break
            except (FileNotFoundError, ConnectionRefusedError):
                await asyncio.sleep(.05)
        else:
            raise OSError("mpv IPC did not start")
        self._reader_task = asyncio.create_task(self._read(reader))
        for i, prop in enumerate(["time-pos", "pause", "volume", "mute", "paused-for-cache"]):
            await self._command("observe_property", i, prop)

    async def _command(self, *args):
        self._serial += 1
        ident = self._serial
        future = asyncio.get_running_loop().create_future()
        self._pending[ident] = future
        try:
            self._writer.write((json.dumps({"command": args, "request_id": ident}) + "\n").encode())
            await self._writer.drain()
            result = await asyncio.wait_for(future, 5)
            if result.get("error") != "success":
                raise ValueError("mpv command failed: " + str(result.get("error")))
            return result.get("data")
        finally:
            self._pending.pop(ident, None)

    async def _read(self, reader):
        while raw := await reader.readline():
            message = json.loads(raw)
            future = self._pending.get(message.get("request_id"))
            if future is not None and not future.done():
                future.set_result(message)
            await self._event(message)

    async def _event(self, message):
        event = message.get("event")
        if event == "property-change":
            name, value = message.get("name"), message.get("data")
            if value is None:
                return
            if (self._loading or self._seeking) and name in {"time-pos", "pause", "paused-for-cache"}:
                return
            if name == "time-pos":
                self._set_position(float(value))
            elif name == "volume":
                self._status.volume = float(value) / 100
            elif name == "mute":
                self._status.muted = bool(value)
            elif name == "pause" and self._status.state != "IDLE":
                self._autoplay = not bool(value)
                self._status.state = "PAUSED" if value else "PLAYING"
            elif name == "paused-for-cache" and self._status.state == "PLAYING" and value:
                self._status.state = "BUFFERING"
            elif name == "paused-for-cache" and self._status.state == "BUFFERING" and not value:
                self._status.state = "PLAYING" if self._autoplay else "PAUSED"
        elif event == "file-loaded":
            LOGGER.info("mpv file-loaded")
            self._loading = False
            self._status.state = "PLAYING" if self._autoplay else "PAUSED"
        elif event == "playback-restart":
            self._seeking = False
            if self._status.state != "IDLE":
                self._status.state = "PLAYING" if self._autoplay else "PAUSED"
        elif event == "end-file":
            reason = message.get("reason")
            LOGGER.info("mpv end-file reason=%s error=%s entry=%s loading=%s position=%.3f",
                        reason, message.get("file_error", message.get("error")),
                        message.get("playlist_entry_id"), self._loading,
                        self._current_position())
            if self._loading and reason == "eof":
                return
            # Replacement/stop events must not finish the newly loaded item.
            if reason not in {"eof", "error"}:
                return
            self._loading = False
            self._seeking = False
            self._status.state = "IDLE"
            self._status.idle_reason = "FINISHED" if reason == "eof" else "ERROR"
        else:
            return
        self._emit_status()

    async def load(self, url, content_type, autoplay, start_time):
        await self._start()
        self._autoplay = autoplay
        self._loading = True
        self._seeking = False
        self._status.url, self._status.content_type = url, content_type
        self._status.idle_reason = None
        self._status.state = "BUFFERING"
        self._set_position(max(0, start_time))
        await self._command("set_property", "pause", not autoplay)
        await self._command("loadfile", url, "replace", -1, {"start": str(max(0, start_time))})

    async def play(self):
        await self._command("set_property", "pause", False)
        self._autoplay = True
        self._status.state = "BUFFERING" if self._loading else "PLAYING"

    async def pause(self):
        await self._command("set_property", "pause", True)
        self._autoplay = False
        self._status.state = "PAUSED"

    async def seek(self, position):
        self._seeking = True
        self._set_position(max(0, position))
        try:
            await self._command("seek", max(0, position), "absolute+exact")
        except ValueError:
            # Some network demuxers reject in-place seeks. Reopen the same
            # media with a start offset, preserving paused state and volume.
            if not self._status.url:
                raise
            await self.load(self._status.url, self._status.content_type,
                            self._status.state != "PAUSED", max(0, position))

    async def set_volume(self, level, muted):
        await self._start()
        await self._command("set_property", "volume", max(0, min(1, level)) * 100)
        await self._command("set_property", "mute", bool(muted))
        self._status.volume = max(0, min(1, level))
        self._status.muted = bool(muted)

    async def stop(self):
        self._loading = False
        self._seeking = False
        if self._writer:
            await self._command("stop")
        await super().stop()

    async def shutdown(self):
        if self._process:
            self._process.terminate()
            await self._process.wait()
        if self._reader_task:
            self._reader_task.cancel()
            await asyncio.gather(self._reader_task, return_exceptions=True)
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        if self._temp:
            self._temp.cleanup()
