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

MAX_MEDIA_BYTES = 64 * 1024 * 1024
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
            return
        host = self.bind_host or await asyncio.to_thread(local_address_for, self.target_host)
        app = web.Application()
        app.router.add_get("/media/{name}", self._serve)
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
        if self._process is not None and self._process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                self._process.kill()
            await self._process.wait()
        if self._runner:
            runner, self._runner = self._runner, None
            await runner.cleanup()
        self._files.clear()
        if self._temp:
            self._temp.cleanup()
            self._temp = None
        self._base = None
