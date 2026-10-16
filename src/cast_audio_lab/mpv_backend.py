# SPDX-License-Identifier: MPL-2.0
"""mpv JSON IPC output with decoder-owned position and EOF feedback."""
import asyncio
import json
import logging
import math
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from .backend import NullAudioBackend

LOGGER = logging.getLogger(__name__)


class MpvAudioBackend(NullAudioBackend):
    local_audio_cache = True

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
        self._closing = False
        self._cleanup_task = None
        self._preparing_load = False
        self._entry_id = None
        self._replaced_entry_id = None

    def _current_position(self):
        return self._position_at_change

    async def _start(self):
        if self._cleanup_task is not None and not self._cleanup_task.done():
            await asyncio.shield(self._cleanup_task)
        if self._writer is not None:
            return
        if self._reader_task is not None:
            await asyncio.gather(self._reader_task, return_exceptions=True)
        await self._dispose()
        try:
            await self._spawn()
        except BaseException:
            await self._dispose()
            raise

    async def _spawn(self):
        volume, muted = self._status.volume, self._status.muted
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
        await self._command("set_property", "volume", volume * 100)
        await self._command("set_property", "mute", muted)

    async def _command(self, *args):
        if self._writer is None:
            raise OSError("mpv IPC is disconnected")
        self._serial += 1
        ident = self._serial
        future = asyncio.get_running_loop().create_future()
        self._pending[ident] = future
        try:
            async with asyncio.timeout(5):
                self._writer.write((json.dumps({"command": args, "request_id": ident}) + "\n").encode())
                await self._writer.drain()
                result = await future
            if result.get("error") != "success":
                raise ValueError("mpv command failed: " + str(result.get("error")))
            return result.get("data")
        except OSError:
            future.cancel()
            self._loading = self._seeking = False
            self._status.state = "IDLE"
            self._status.idle_reason = "ERROR"
            self._emit_status()
            await self._dispose()
            raise
        finally:
            self._pending.pop(ident, None)

    async def _read(self, reader):
        try:
            while raw := await reader.readline():
                message = json.loads(raw)
                if not isinstance(message, dict):
                    raise ValueError("mpv IPC message must be an object")
                future = self._pending.get(message.get("request_id"))
                if future is not None and not future.done():
                    future.set_result(message)
                await self._event(message)
        except (OSError, ValueError, TypeError):
            LOGGER.warning("mpv IPC reader failed")
        finally:
            if not self._closing:
                if not self._preparing_load:
                    self._loading = self._seeking = False
                    self._status.state = "IDLE"
                    self._status.idle_reason = "ERROR"
                    self._emit_status()
                await self._dispose()

    async def _event(self, message):
        event = message.get("event")
        if event == "start-file":
            self._entry_id = message.get("playlist_entry_id")
            return
        if event == "property-change":
            name, value = message.get("name"), message.get("data")
            if value is None:
                return
            if (self._loading or self._seeking) and name in {"time-pos", "pause", "paused-for-cache"}:
                return
            if name in {"time-pos", "volume"}:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    return
                try:
                    value = float(value)
                except (ValueError, OverflowError):
                    return
                if not math.isfinite(value):
                    return
            elif name in {"pause", "mute", "paused-for-cache"} and not isinstance(value, bool):
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
            if (not self._loading and self._status.state == "IDLE"
                    or self._entry_id is not None and self._entry_id == self._replaced_entry_id):
                return
            LOGGER.info("mpv file-loaded")
            self._loading = False
            self._status.state = "PLAYING" if self._autoplay else "PAUSED"
            self._status.idle_reason = None
        elif event == "playback-restart":
            if self._loading:
                return
            self._seeking = False
            if self._status.state != "IDLE":
                self._status.state = "PLAYING" if self._autoplay else "PAUSED"
        elif event == "end-file":
            reason = message.get("reason")
            entry = message.get("playlist_entry_id")
            LOGGER.info("mpv end-file reason=%s error=%s entry=%s loading=%s position=%.3f",
                        reason, message.get("file_error", message.get("error")),
                        message.get("playlist_entry_id"), self._loading,
                        self._current_position())
            if entry is not None and (entry == self._replaced_entry_id
                    or self._entry_id is not None and entry != self._entry_id):
                return
            if self._loading and reason == "eof" and entry is None:
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
        try:
            self._preparing_load = True
            try:
                await self._start()
            finally:
                self._preparing_load = False
            # Old IPC teardown may publish ERROR while _start waits for it.
            # Initialize the new selection only after that reader has exited.
            self._autoplay = autoplay
            self._loading = True
            self._replaced_entry_id = self._entry_id
            self._seeking = False
            self._status.url, self._status.content_type = url, content_type
            self._status.idle_reason = None
            self._status.state = "BUFFERING"
            self._set_position(max(0, start_time))
            await self._command("set_property", "pause", not autoplay)
            options = {"start": str(max(0, start_time))}
            source = urlsplit(url)
            if source.hostname == "127.0.0.1" and source.path.startswith("/manifest/") and "/cache-" in source.path:
                # Retention lives in the receiver; mpv only needs a short runway.
                options.update({"cache-secs": "30", "demuxer-max-bytes": "512KiB",
                                "stream-buffer-size": "64KiB"})
            try:
                await self._command("loadfile", url, "replace", -1, options)
            except ValueError as exc:
                # mpv before 0.38 has no insertion-index argument. Retry only
                # argument rejection, never media/network failures.
                if str(exc) != "mpv command failed: invalid parameter":
                    raise
                await self._command("loadfile", url, "replace", options)
        except (OSError, ValueError, TimeoutError):
            self._loading = self._seeking = False
            self._status.state = "IDLE"
            self._status.idle_reason = "ERROR"
            self._emit_status()
            raise

    async def play(self):
        if self._status.state == "IDLE":
            # A failed decoder needs a new LOAD. The owning app can obtain a
            # fresh URL; unpausing mpv cannot resurrect the failed stream.
            return
        await self._command("set_property", "pause", False)
        self._autoplay = True
        self._status.state = "BUFFERING" if self._loading else "PLAYING"

    async def pause(self):
        if self._status.state == "IDLE":
            return
        await self._command("set_property", "pause", True)
        self._autoplay = False
        self._status.state = "PAUSED"

    async def seek(self, position):
        old_position = self._current_position()
        self._seeking = True
        self._set_position(max(0, position))
        try:
            await self._command("seek", max(0, position), "absolute+exact")
        except ValueError:
            self._seeking = False
            # Some network demuxers reject in-place seeks. Reopen the same
            # media with a start offset, preserving paused state and volume.
            if not self._status.url:
                self._set_position(old_position)
                raise
            await self.load(self._status.url, self._status.content_type,
                            self._status.state != "PAUSED", max(0, position))
        except (OSError, asyncio.CancelledError):
            self._seeking = False
            self._set_position(old_position)
            raise

    async def set_volume(self, level, muted):
        await self._start()
        await self._command("set_property", "volume", max(0, min(1, level)) * 100)
        await self._command("set_property", "mute", bool(muted))
        self._status.volume = max(0, min(1, level))
        self._status.muted = bool(muted)

    async def stop(self):
        self._loading = False
        self._seeking = False
        self._replaced_entry_id = self._entry_id
        try:
            if self._writer:
                await self._command("stop")
        except (OSError, ValueError):
            await self._dispose()
        finally:
            await super().stop()

    async def shutdown(self):
        await self._dispose()

    async def _dispose(self):
        if self._cleanup_task is None or self._cleanup_task.done():
            self._closing = True
            self._cleanup_task = asyncio.create_task(
                self._dispose_resources(asyncio.current_task()))
        await asyncio.shield(self._cleanup_task)

    async def _dispose_resources(self, initiator):
        self._closing = True
        task = self._reader_task
        writer, self._writer = self._writer, None
        process, self._process = self._process, None
        temp, self._temp = self._temp, None
        for future in self._pending.values():
            if not future.done():
                future.set_exception(OSError("mpv IPC disconnected"))
        try:
            if task is not None and task is not initiator:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if writer is not None:
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), 1)
                except (OSError, TimeoutError):
                    pass
            if process is not None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), 2)
                except TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    await process.wait()
        finally:
            if temp is not None:
                temp.cleanup()
            if self._reader_task is task:
                self._reader_task = None
            self._entry_id = self._replaced_entry_id = None
            self._closing = False
