# SPDX-License-Identifier: MPL-2.0
"""Output-local HTTP media compatibility for finite DLNA audio items.

Old renderers need Content-Length and byte ranges, so prepare a bounded file
before advertising it. This is deliberately not a generic URL proxy or live
radio transcoder. Only an opaque current/previous media path is exposed.
"""
import asyncio
import contextlib
import ipaddress
from pathlib import Path
import secrets
import socket
import tempfile
from urllib.parse import urlsplit

from aiohttp import web
import logging
import re

LOGGER = logging.getLogger(__name__)

MAX_MEDIA_BYTES = 64 * 1024 * 1024
STREAM_PROBE_TIMEOUT = 15
STREAM_READY_TIMEOUT = 15
SIZED_MP3_BITRATE = 320000
SIZED_MP3_BYTES_PER_SECOND = SIZED_MP3_BITRATE // 8
SIZED_MP3_CODEC = ["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100", "-ac", "2",
                   "-write_xing", "0", "-id3v2_version", "0"]
STREAM_CHUNK = 64 * 1024
# Streamed (progressive) output: codec -> (mime, ffmpeg muxer). Copy keeps the
# source audio bit-exact; only unknown codecs are transcoded to MP3.
STREAM_COPY = {"aac": ("audio/aac", "adts"), "mp3": ("audio/mpeg", "mp3")}
PREPARE_TIMEOUT = 90
COPY_FORMATS = {
    "audio/mpeg": ("mp3", "mp3"),
    "audio/mp4": ("ipod", "m4a"),
    "audio/flac": ("flac", "flac"),
    "audio/x-flac": ("flac", "flac"),
    "audio/wav": ("wav", "wav"),
    "audio/x-wav": ("wav", "wav"),
    "audio/webm": ("webm", "webm"),
    "audio/ogg": ("ogg", "ogg"),
}


def renderer_mime_types(profile):
    return {entry.split(":", 3)[2].split(";", 1)[0].lower()
            for entry in (getattr(profile, "sink_protocol_info", None) or [])
            if len(entry.split(":", 3)) == 4}


def needs_relay(url, content_type, supported):
    mime = content_type.split(";", 1)[0].strip().lower()
    parsed = urlsplit(url)
    loopback = parsed.hostname == "localhost"
    try:
        loopback = loopback or ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        pass
    return loopback or parsed.scheme == "https" or bool(supported and mime not in supported and "*" not in supported)


def encoding(content_type, supported):
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in COPY_FORMATS and (mime in supported or "*" in supported):
        muxer, suffix = COPY_FORMATS[mime]
        return mime, muxer, suffix, ["-c:a", "copy"]
    return "audio/mpeg", "mp3", "mp3", ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def trim_hls(playlist, start):
    """Drop media segments wholly before `start` seconds of a VOD HLS playlist.

    Returns (playlist, seconds_skipped) or None when the text is not a
    simple media playlist. Header tags (EXT-X-MAP, KEY, VERSION ...) are kept.
    """
    lines = playlist.splitlines()
    if not lines or lines[0].strip() != "#EXTM3U" or any(l.startswith("#EXT-X-STREAM-INF") for l in lines):
        return None
    head, segments, pending, inf = [], [], [], None
    for line in lines:
        if line.startswith("#EXTINF:"):
            try:
                inf = float(line[8:].split(",", 1)[0])
            except ValueError:
                return None
            pending.append(line)
        elif line and not line.startswith("#"):
            if inf is None:
                return None
            segments.append((inf, pending + [line]))
            pending, inf = [], None
        elif segments or pending:
            pending.append(line)  # per-segment tags (e.g. DISCONTINUITY) and trailing ENDLIST
        else:
            head.append(line)
    skipped, keep = 0.0, 0
    while keep < len(segments) - 1 and skipped + segments[keep][0] <= start:
        skipped += segments[keep][0]
        keep += 1
    body = [l for _, seg in segments[keep:] for l in seg] + pending
    for i, line in enumerate(head):
        if line.startswith("#EXT-X-MEDIA-SEQUENCE:"):
            try:
                head[i] = f"#EXT-X-MEDIA-SEQUENCE:{int(line.split(':', 1)[1]) + keep}"
            except ValueError:
                pass
    return "\n".join(head + body) + "\n", skipped


def stream_encoding(codec, supported):
    """Choose copy-to-stream when the renderer accepts the source codec."""
    if codec in STREAM_COPY:
        mime, muxer = STREAM_COPY[codec]
        if not supported or mime in supported or "*" in supported:
            return mime, muxer, ["-c:a", "copy"]
    # Yamaha MusicCast plays progressive ADTS but not length-less MP3 (tested
    # 22.11.2026), so AAC is the preferred transcode target when accepted.
    if not supported or "audio/aac" in supported or "*" in supported:
        return "audio/aac", "adts", ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]
    return "audio/mpeg", "mp3", ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "2"]


def local_address_for(host):
    # Routing lookup only: UDP connect sends no packet.
    infos = socket.getaddrinfo(host, 9, type=socket.SOCK_DGRAM)
    for family, kind, proto, _, address in infos:
        try:
            with socket.socket(family, kind, proto) as route:
                route.connect(address)
                return route.getsockname()[0]
        except OSError:
            continue
    raise OSError("no local route to DLNA renderer")


class DlnaMediaRelay:
    def __init__(self, target_host, *, ffmpeg="ffmpeg", bind_host=None):
        self.target_host = target_host
        self.ffmpeg = ffmpeg
        self.bind_host = bind_host
        self._temp = None
        self._runner = None
        self._base = None
        self._files = {}
        self._process = None
        self._stream = None  # (name, ffmpeg process, mime, transcoded)
        self._ffprobe = "ffprobe" if ffmpeg == "ffmpeg" else str(Path(ffmpeg).with_name("ffprobe"))

    async def _probe_codec(self, url):
        process = await asyncio.create_subprocess_exec(
            self._ffprobe, "-v", "error", "-protocol_whitelist", "http,https,tcp,tls,crypto",
            "-rw_timeout", "15000000", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name", "-of", "csv=p=0", url,
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            async with asyncio.timeout(STREAM_PROBE_TIMEOUT):
                out, err = await process.communicate()
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            await process.wait()
            return ""
        if not out.strip():
            # Path and first error line only; query strings may carry signatures.
            first = (err.decode(errors="ignore").strip().splitlines() or [""])[-1]
            LOGGER.warning("DLNA stream probe failed path=%s rc=%s error=%s",
                           urlsplit(url).path, process.returncode, re.sub(r"\?\S*", "", first)[:300])
            return ""
        return out.decode(errors="ignore").strip().splitlines()[0]

    async def _wait_ready(self, url):
        """Poll until the source answers 200; returns elapsed seconds or raises."""
        from aiohttp import ClientSession, ClientTimeout
        loop = asyncio.get_running_loop()
        started = loop.time()
        async with ClientSession(timeout=ClientTimeout(total=3)) as http:
            while True:
                try:
                    # GET, not HEAD: the bridge forwards HEAD upstream and CDNs
                    # (SoundCloud) do not answer HEAD with 200.
                    async with http.get(url, allow_redirects=True) as response:
                        if response.status == 200:
                            await response.content.read(64)
                            return loop.time() - started
                except Exception:
                    pass
                if loop.time() - started > STREAM_READY_TIMEOUT:
                    raise RuntimeError("DLNA stream source did not become available")
                await asyncio.sleep(0.25)

    async def stream(self, url, supported, start_time=0.0, duration=None):
        """Start progressive output immediately; no size or duration limit."""
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError("DLNA relay requires an HTTP media source")
        await self._stop_stream()
        if duration and duration > start_time and (not supported or "audio/mpeg" in supported or "*" in supported):
            return await self._sized_stream(url, start_time, duration)
        if urlsplit(url).hostname in {"127.0.0.1", "localhost", "::1"}:
            LOGGER.info("DLNA stream source url=%s", url)  # loopback bridge URL, carries no upstream signature
        waited = await self._wait_ready(url)
        if waited > 0.3:
            LOGGER.info("DLNA stream source ready after %.1fs", waited)
        codec = ""
        for attempt in range(3):  # a just-registered bridge manifest can briefly 404
            codec = await self._probe_codec(url)
            if codec:
                break
            await asyncio.sleep(0.5 * (attempt + 1))
        mime, muxer, codec_args = stream_encoding(codec, supported)
        source, protocols, seek, hls_opts = url, "http,https,tcp,tls,crypto", [], []
        if start_time > 0:
            trimmed = await self._trimmed_hls(url, start_time)
            if trimmed is not None:
                # Start at the segment boundary; skip the remainder on the output side.
                source, skipped = trimmed
                protocols = "file," + protocols
                hls_opts = ["-allowed_extensions", "ALL"]  # HLS-demuxer option, local playlist only
                rest = start_time - skipped
                seek = ["-ss", f"{rest:.3f}"] if rest > 0.05 else []
                input_seek = []
            else:
                input_seek = ["-ss", f"{start_time:.3f}"]
        else:
            input_seek = []
        process = await asyncio.create_subprocess_exec(
            self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", protocols, *hls_opts,
            "-rw_timeout", "15000000", *input_seek, "-i", source, *seek, "-map", "0:a:0", "-vn",
            *codec_args, "-f", muxer, "pipe:1",
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await self._start()
        name = secrets.token_hex(16) + ("." + muxer)
        self._stream = (name, process, mime, codec_args != ["-c:a", "copy"])
        return f"{self._base}/stream/{name}", mime, codec or "unknown"

    async def _sized_stream(self, url, start_time, duration):
        """Announce a fixed-size CBR MP3 immediately; ffmpeg starts per HTTP request."""
        waited = await self._wait_ready(url)
        if waited > 0.3:
            LOGGER.info("DLNA stream source ready after %.1fs", waited)
        await self._start()
        size = int((duration - start_time) * SIZED_MP3_BYTES_PER_SECOND)
        name = secrets.token_hex(16) + ".mp3"
        self._stream = (name, None, "audio/mpeg", True)
        self._sized = {"name": name, "url": url, "start": start_time, "size": size}
        return f"{self._base}/stream/{name}", "audio/mpeg", "mp3-cbr"

    async def _spawn_from(self, url, position):
        """ffmpeg CBR-MP3 encoder process starting at `position` seconds of the source."""
        source, protocols, hls_opts, out_seek = url, "http,https,tcp,tls,crypto", [], []
        if position > 0:
            trimmed = await self._trimmed_hls(url, position)
            if trimmed is not None:
                source, skipped = trimmed
                protocols, hls_opts = "file," + protocols, ["-allowed_extensions", "ALL"]
                rest = position - skipped
                out_seek = ["-ss", f"{rest:.3f}"] if rest > 0.05 else []
            else:
                hls_opts = ["-ss", f"{position:.3f}"]
        return await asyncio.create_subprocess_exec(
            self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-protocol_whitelist", protocols, *hls_opts, "-rw_timeout", "15000000",
            "-i", source, *out_seek, "-map", "0:a:0", "-vn", *SIZED_MP3_CODEC, "-f", "mp3", "pipe:1",
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )

    async def _serve_sized(self, request, sized):
        size = sized["size"]
        first = 0
        rng = request.headers.get("Range", "")
        if rng.startswith("bytes="):
            try:
                first = int(rng[6:].split("-", 1)[0] or 0)
            except ValueError:
                first = 0
        if first >= size:
            raise web.HTTPRequestRangeNotSatisfiable(headers={"Content-Range": f"bytes */{size}"})
        status = 206 if rng else 200
        headers = {
            "Content-Type": "audio/mpeg",
            "Content-Length": str(size - first),
            "Accept-Ranges": "bytes",
            "contentFeatures.dlna.org": "DLNA.ORG_PN=MP3;DLNA.ORG_OP=01;DLNA.ORG_CI=1;DLNA.ORG_FLAGS=01700000000000000000000000000000",
            "transferMode.dlna.org": "Streaming",
            "Cache-Control": "no-store",
        }
        if status == 206:
            headers["Content-Range"] = f"bytes {first}-{size - 1}/{size}"
        response = web.StreamResponse(status=status, headers=headers)
        response.force_close()
        await response.prepare(request)
        if request.method == "HEAD":
            return response
        position = sized["start"] + first / SIZED_MP3_BYTES_PER_SECOND
        process = await self._spawn_from(sized["url"], position)
        old, self._sized_process = getattr(self, "_sized_process", None), process
        if old is not None and old.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                old.kill()
        LOGGER.info("DLNA sized mp3 request range=%s position=%.1f", rng or "-", position)
        remaining = size - first
        try:
            await self._pump_sized(response, process, remaining)
        except ConnectionError:
            # Renderers drop the old connection on every seek/track change: expected, not an error.
            LOGGER.debug("DLNA renderer closed sized mp3 connection")
        finally:
            if process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
        return response

    async def _pump_sized(self, response, process, remaining):
        while remaining > 0:
            chunk = await process.stdout.read(min(STREAM_CHUNK, remaining))
            if not chunk:
                break
            await response.write(chunk)
            remaining -= len(chunk)
        # A CBR estimate may exceed the real output by a few frames: pad up to the announced length.
        while remaining > 0:
            pad = min(STREAM_CHUNK, remaining)
            await response.write(b"\x00" * pad)
            remaining -= pad

    async def _trimmed_hls(self, url, start_time):
        """Fetch the HLS playlist, trim it to `start_time`, store it locally."""
        from aiohttp import ClientSession, ClientTimeout
        try:
            async with ClientSession(timeout=ClientTimeout(total=10)) as http:
                async with http.get(url) as response:
                    if response.status != 200:
                        return None
                    text = await response.text(errors="ignore")
        except Exception:
            return None
        trimmed = trim_hls(text, start_time)
        if trimmed is None:
            return None
        if self._temp is None:
            self._temp = tempfile.TemporaryDirectory(prefix="cast-dlna-media-")
        path = Path(self._temp.name) / "seek.m3u8"
        path.write_text(trimmed[0])
        LOGGER.info("DLNA stream HLS trimmed start=%.1f segment_start=%.1f", start_time, trimmed[1])
        return str(path), trimmed[1]

    async def _stop_stream(self):
        self._sized = None
        proc, self._sized_process = getattr(self, "_sized_process", None), None
        if proc is not None and proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
        current, self._stream = self._stream, None
        if current is not None and current[1] is not None and current[1].returncode is None:
            with contextlib.suppress(ProcessLookupError):
                current[1].kill()
            await current[1].wait()

    async def _serve_stream(self, request):
        sized = getattr(self, "_sized", None)
        if sized is not None and sized["name"] == request.match_info["name"]:
            return await self._serve_sized(request, sized)
        current = self._stream
        if current is None or current[0] != request.match_info["name"]:
            raise web.HTTPNotFound()
        _, process, mime, converted = current
        response = web.StreamResponse(headers={
            "Content-Type": mime,
            "contentFeatures.dlna.org": (
                ("DLNA.ORG_PN=MP3;" if mime == "audio/mpeg" else "")
                + f"DLNA.ORG_OP=00;DLNA.ORG_CI={int(converted)};DLNA.ORG_FLAGS=01700000000000000000000000000000"
            ),
            "transferMode.dlna.org": "Streaming",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        })
        # Radio-style body: no Content-Length and no chunked framing (embedded
        # renderers often reject chunked); the connection closes at the end.
        response.force_close()
        # shortcut: private aiohttp switch (also used for WebSockets) that stops
        # automatic chunking on HTTP/1.1; revisit if aiohttp is upgraded.
        response._length_check = False
        await response.prepare(request)
        if request.method == "HEAD":
            return response
        while True:
            chunk = await process.stdout.read(STREAM_CHUNK)
            if not chunk:
                break
            await response.write(chunk)
        await response.write_eof()
        return response

    async def _serve(self, request):
        item = self._files.get(request.match_info["name"])
        if item is None:
            raise web.HTTPNotFound()
        path, mime, converted = item
        response = web.FileResponse(path, headers={
            "Content-Type": mime,
            "contentFeatures.dlna.org": (
                ("DLNA.ORG_PN=MP3;" if mime == "audio/mpeg" else "")
                + f"DLNA.ORG_OP=01;DLNA.ORG_CI={int(converted)};DLNA.ORG_FLAGS=01700000000000000000000000000000"
            ),
            "transferMode.dlna.org": "Streaming",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        })
        response.force_close()
        return response

    async def _start(self):
        if self._runner:
            if self._base is not None:
                return
            # A failed close invalidates the old URL. Finish that cleanup
            # before publishing another file on a replacement HTTP listener.
            await self._runner.cleanup()
            self._runner = None
        host = self.bind_host or await asyncio.to_thread(local_address_for, self.target_host)
        app = web.Application()
        app.router.add_get("/media/{name}", self._serve)
        app.router.add_route("GET", "/stream/{name}", self._serve_stream)
        app.router.add_route("HEAD", "/stream/{name}", self._serve_stream)
        runner = web.AppRunner(app, access_log=None, shutdown_timeout=2)
        await runner.setup()
        try:
            site = web.TCPSite(runner, host, 0)
            await site.start()
        except BaseException:
            await runner.cleanup()
            raise
        self._runner = runner
        port = site._server.sockets[0].getsockname()[1]
        self._base = f"http://{'[' + host + ']' if ':' in host else host}:{port}"

    async def prepare(self, url, content_type, supported):
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError("DLNA relay requires an HTTP media source")
        if self._process is not None:
            raise RuntimeError("DLNA media preparation is already running")
        if self._temp is None:
            self._temp = tempfile.TemporaryDirectory(prefix="cast-dlna-media-")
        mime, muxer, suffix, codec = encoding(content_type, supported)
        name = secrets.token_hex(16) + "." + suffix
        path = Path(self._temp.name) / name
        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
                "-protocol_whitelist", "http,https,tcp,tls,crypto",
                "-rw_timeout", "15000000", "-i", url, "-map", "0:a:0", "-vn",
                *codec, "-threads", "1", "-fs", str(MAX_MEDIA_BYTES + 1),
                "-f", muxer, str(path), stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
            )
            self._process = process
            try:
                async with asyncio.timeout(PREPARE_TIMEOUT):
                    result = await process.wait()
            except TimeoutError:
                raise RuntimeError("DLNA media preparation timed out; live/infinite sources need direct playback") from None
            if result or not path.exists() or not 0 < path.stat().st_size <= MAX_MEDIA_BYTES:
                raise RuntimeError("DLNA media preparation failed or exceeded its size limit")
            await self._start()
            while len(self._files) >= 2:
                old = next(iter(self._files))
                self._files.pop(old)[0].unlink(missing_ok=True)
            self._files[name] = (path, mime, codec != ["-c:a", "copy"])
            return f"{self._base}/media/{name}", mime
        finally:
            if process is not None and process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    process.kill()
                await process.wait()
            self._process = None
            if name not in self._files:
                path.unlink(missing_ok=True)

    async def close(self):
        await self._stop_stream()
        try:
            if self._process is not None and self._process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    self._process.kill()
                await self._process.wait()
            if self._runner:
                # Retain ownership on failure so a later shutdown can retry.
                await self._runner.cleanup()
                self._runner = None
        finally:
            self._files.clear()
            try:
                if self._temp:
                    self._temp.cleanup()
                    self._temp = None
            finally:
                self._base = None
