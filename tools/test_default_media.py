#!/usr/bin/env python3
"""Opt-in isolated DMR/real-mpv test. Owns all test processes.

Emits a quiet tone unless --silent-fixture is selected. Silence still exercises
real decoding, clock, seeking and volume feedback, not audible output quality.

Uses existing private receiver credentials; never prints them or media URLs.
The development sender does not validate device auth: stock sender acceptance
remains a separate test. No connection to an existing Cast receiver is made.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import math
import re
import signal
import ssl
import struct
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path

from cast_audio_lab.mpv_backend import MpvAudioBackend
from cast_audio_lab.vibecast_player import VibecastAudioPlayer, run_player
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage,
    read_cast_message,
    write_cast_message,
)

PREFIX = "urn:x-cast:com.google.cast."


def fixture(silent=False):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
        wav.writeframes(bytes(22050 * 8 * 2) if silent else b"".join(
            struct.pack("<h", int(100 * math.sin(i * 440 * 2 * math.pi / 22050)))
            for i in range(22050 * 8)))
    return output.getvalue()


def encoded_fixture(silent=False, audio_format="wav"):
    if audio_format not in {"wav", "mp3", "flac"}:
        raise ValueError("unsupported fixture format")
    audio = fixture(silent)
    if audio_format == "wav":
        return audio
    # Only our bounded synthetic WAV enters this helper, never sender media.
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-f", audio_format, "pipe:1"], input=audio, capture_output=True,
        check=True, timeout=10)
    if not result.stdout or len(result.stdout) > 1024 * 1024:
        raise ValueError("unexpected encoded fixture size")
    return result.stdout


async def run(binary: Path, certs: Path, airplay_config=None, cliairplay="cliairplay", silent=False,
              audio_format="wav", artwork_check=False):
    audio = encoded_fixture(silent, audio_format)
    fixture_path = f"/tone.{audio_format}".encode()
    content_type = {"wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac"}[audio_format]
    stalled_request = asyncio.Event()
    cover = b'P6\n640 360\n255\n' + bytes((80, 140, 210)) * (640 * 360)

    async def http(reader, writer):
        try:
            request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
            path = request.split(b" ")[1]
            if path == b"/stall":
                stalled_request.set()
                # Deliberately withhold headers until mpv cancels the request.
                # The bounded wait also cleans up a failed cancellation test.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(reader.read(), 10)
                return
            body = audio if path == fixture_path else b"missing"
            status = b"200 OK" if path == fixture_path else b"404 Not Found"
            response_type = content_type
            if path == b'/cover.ppm':
                body, status, response_type = cover, b'200 OK', 'image/x-portable-pixmap'
            extra = b"Accept-Ranges: bytes\r\n"
            byte_range = re.search(rb"(?im)^Range: bytes=(\d+)-(\d*)", request)
            if path == fixture_path and byte_range:
                start = int(byte_range[1])
                end = min(int(byte_range[2]) if byte_range[2] else len(audio)-1, len(audio)-1)
                if start > end:
                    status, body = b"416 Range Not Satisfiable", b""
                else:
                    status, body = b"206 Partial Content", audio[start:end+1]
                    extra += f"Content-Range: bytes {start}-{end}/{len(audio)}\r\n".encode()
            writer.write(b"HTTP/1.1 " + status + b"\r\nContent-Type: " + response_type.encode() + b"\r\nContent-Length: "
                         + str(len(body)).encode() + b"\r\n" + extra + b"Connection: close\r\n\r\n"
                         + (b"" if request.startswith(b"HEAD ") else body))
            await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    server = await asyncio.start_server(http, "127.0.0.1", 0)
    url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}{fixture_path.decode()}"
    process = player_task = writer = None
    artwork_runner = None
    with tempfile.TemporaryDirectory(prefix="cast-dmr-test-") as directory:
        log_path = Path(directory) / "frontend.log"
        try:
            with log_path.open("wb") as log:
                process = await asyncio.create_subprocess_exec(
                    str(binary.resolve()), "--certs", str(certs.resolve()),
                    "--data-dir", directory, "--bind-host", "127.0.0.1",
                    "--player-port", "0", "--log-level", "info",
                    stdin=asyncio.subprocess.DEVNULL, stdout=log, stderr=log)
            bridge_port = None
            for _ in range(100):
                if process.returncode is not None:
                    raise RuntimeError("isolated frontend exited before bridge startup")
                text = re.sub(r"\x1b\[[0-9;]*m", "", log_path.read_text(errors="replace"))
                match = re.search(r"register=ws://[^: ]+:(\d+)/player", text)
                if match:
                    bridge_port = int(match.group(1))
                    break
                await asyncio.sleep(.1)
            if bridge_port is None:
                raise RuntimeError("isolated bridge startup timed out")
            if airplay_config:
                from cast_audio_lab.airplay import AirPlayAudioBackend, load_airplay_target
                backend = AirPlayAudioBackend(load_airplay_target(airplay_config), cliairplay=cliairplay)
            else:
                backend = MpvAudioBackend()
            player = VibecastAudioPlayer(f"ws://127.0.0.1:{bridge_port}/player", str(uuid.uuid4()),
                                         "Audio Lab DMR Test", backend)
            if artwork_check:
                from aiohttp import web
                from cast_audio_lab.management import create_app
                from cast_audio_lab.route_manager import RouteManager
                from cast_audio_lab.routes import RouteStore
                artwork_runner = web.AppRunner(create_app(RouteManager(RouteStore(Path(directory)/'routes'))))
                await artwork_runner.setup()
                site = web.TCPSite(artwork_runner, '127.0.0.1', 0)
                await site.start()
                image_port = site._server.sockets[0].getsockname()[1]
                player.artwork_public_url = f'http://127.0.0.1:{image_port}'
                player.artwork_endpoint = player.artwork_public_url + '/api/artwork'
            player_task = asyncio.create_task(run_player(player))
            port = None
            for _ in range(100):
                if process.returncode is not None:
                    raise RuntimeError("isolated frontend exited before registration")
                text = re.sub(r"\x1b\[[0-9;]*m", "", log_path.read_text(errors="replace"))
                match = re.search(r"cast_port=(\d+)", text)
                if match:
                    port = int(match.group(1))
                    break
                await asyncio.sleep(.1)
            if port is None:
                raise RuntimeError("isolated receiver registration timed out")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            reader, writer = await asyncio.open_connection("127.0.0.1", port, ssl=context)
            serial = 0
            media_session_id = None

            async def send(namespace, destination, payload):
                await write_cast_message(writer, CastMessage("sender-dmr-test", destination,
                    PREFIX + namespace, payload_utf8=json.dumps(payload)))

            async def request(namespace, destination, payload):
                nonlocal serial
                serial += 1
                ident = serial
                if namespace == "media" and payload["type"] in {"PLAY", "PAUSE", "SEEK", "STOP"}:
                    payload = dict(payload, mediaSessionId=media_session_id)
                await send(namespace, destination, dict(payload, requestId=ident))
                async with asyncio.timeout(10):
                    while True:
                        message = await read_cast_message(reader)
                        data = json.loads(message.payload_utf8 or "{}")
                        if data.get("type") == "PING":
                            await send("tp.heartbeat", message.source_id, {"type": "PONG"})
                        if data.get("requestId") == ident:
                            if data.get("type") in {"INVALID_REQUEST", "LOAD_FAILED", "LAUNCH_ERROR"} and payload["type"] != "QUEUE_LOAD":
                                raise RuntimeError(f"{payload['type']} rejected: {data['type']}")
                            return data

            await send("tp.connection", "receiver-0", {"type": "CONNECT"})
            launched = await request("receiver", "receiver-0", {"type": "LAUNCH", "appId": "CC1AD845"})
            transport = launched["status"]["applications"][0]["transportId"]
            await send("tp.connection", transport, {"type": "CONNECT"})

            async def state(predicate, label):
                values = []
                try:
                    async with asyncio.timeout(15):
                        while True:
                            reply = await request("media", transport, {"type": "GET_STATUS"})
                            values = reply.get("status", [])
                            if values and predicate(values[0]):
                                print("PASS", label, flush=True)
                                return values[0]
                            await asyncio.sleep(.1)
                except TimeoutError:
                    status = values[0] if values else {}
                    print("FAIL", label, {key: status.get(key) for key in
                        ("playerState", "currentTime", "idleReason")},
                        "backend", backend.status().state, backend.status().current_time, flush=True)
                    raise

            async def load(source=url, autoplay=False, start=0, live=False):
                return await request("media", transport, {"type": "LOAD", "autoplay": autoplay,
                    "currentTime": start, "media": {"contentId": source, "contentType": content_type,
                    "streamType": "LIVE" if live else "BUFFERED",
                    **({} if live else {"duration": 8}),
                    "metadata": {"metadataType": 3, "title": "DMR test",
                    "artist": "Fixture artist", "albumName": "Fixture album",
                    **({'images': [{'url': url.rsplit('/', 1)[0] + '/cover.ppm'}]} if artwork_check else {})}}})

            await load(start=1)
            first = await state(lambda s: s["playerState"] == "PAUSED" and abs(s["currentTime"]-1)<.3,
                                "load-autoplay-false-start-position")
            media_session_id = first["mediaSessionId"]
            metadata = first["media"]["metadata"]
            assert first["media"].get("mediaCategory") == "AUDIO", "audio reported as non-audio"
            assert metadata.get("metadataType") == 3, "music metadata type was lost"
            assert metadata.get("artist") == "Fixture artist", "artist was lost"
            assert metadata.get("albumName") == "Fixture album", "album was lost"
            assert backend.metadata.artist == "Fixture artist", "output artist was lost"
            assert backend.metadata.album == "Fixture album", "output album was lost"
            print("PASS music-metadata-roundtrip", flush=True)
            if artwork_check:
                cropped = await state(lambda s: '/artwork/' in s['media']['metadata']['images'][0]['url'],
                                      'processed-cover-cast-status')
                from aiohttp import ClientSession
                async with ClientSession() as client:
                    async with client.get(cropped['media']['metadata']['images'][0]['url']) as image:
                        assert image.status == 200 and image.content_type == 'image/jpeg'
                        data = await image.read()
                probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=width,height', '-of', 'json', 'pipe:0'],
                    input=data, capture_output=True, check=True, timeout=5)
                dimensions = json.loads(probe.stdout)['streams'][0]
                assert dimensions['width'] == dimensions['height'] == 360
                assert cropped['playerState'] == 'PAUSED' and abs(cropped['currentTime'] - 1) < .3
                print('PASS processed-cover-http-square-clock-preserved', flush=True)
            await request("media", transport, {"type": "SEEK", "currentTime": 3})
            await state(lambda s: s["playerState"] == "PAUSED" and abs(s["currentTime"]-3)<.3,
                        "paused-seek")
            await request("media", transport, {"type": "PLAY"})
            await state(lambda s: s["playerState"] == "PLAYING" and s["currentTime"]>3.2, "play-position")
            await request("media", transport, {"type": "PAUSE"})
            await state(lambda s: s["playerState"] == "PAUSED", "pause")
            await request("receiver", "receiver-0", {"type": "SET_VOLUME", "volume": {"level": .4, "muted": False}})
            await state(lambda s: abs(s.get("volume", {}).get("level", -1)-.4)<.01
                        and abs(backend.status().volume-.4)<.01, "sender-volume")
            await backend.set_volume(.3, False)
            await state(lambda s: abs(s.get("volume", {}).get("level", -1)-.3)<.01, "backend-volume-feedback")
            rejected = await request("media", transport, {"type": "QUEUE_LOAD", "items": []})
            assert rejected["type"] == "INVALID_REQUEST"
            await state(lambda s: s["playerState"] == "PAUSED", "queue-rejection-preserves-playback")
            await load(autoplay=True, start=7)
            await state(lambda s: s.get("idleReason") == "FINISHED", "natural-end")
            # A finite local fixture marked LIVE tests the protocol/control policy,
            # not endless network-radio behavior or ICY metadata extraction.
            await load(live=True)
            live_status = await state(lambda s: s["playerState"] == "PAUSED", "live-paused-load")
            assert live_status["media"].get("streamType") == "LIVE"
            assert live_status["media"].get("isLiveMedia") is True
            assert not (live_status.get("supportedMediaCommands", 0) & 2), "LIVE advertises seek"
            await request("media", transport, {"type": "PLAY"})
            await state(lambda s: s["playerState"] == "PLAYING", "live-play")
            await request("media", transport, {"type": "PAUSE"})
            await state(lambda s: s["playerState"] == "PAUSED", "live-pause")
            await load(source=url.replace("/tone.", "/missing."), autoplay=True)
            await state(lambda s: s.get("idleReason") == "ERROR", "http-error")
            await load(autoplay=True)
            await state(lambda s: s["playerState"] == "PLAYING", "recovery-after-error")
            await load(source=url.rsplit("/", 1)[0]+"/stall", autoplay=True)
            await asyncio.wait_for(stalled_request.wait(), 5)
            await load(autoplay=False)
            await state(lambda s: s["playerState"] == "PAUSED", "replacement-of-stalled-source")
            stalled_request.clear()
            await load(source=url.rsplit("/", 1)[0]+"/stall", autoplay=True)
            await asyncio.wait_for(stalled_request.wait(), 5)
            await request("receiver", "receiver-0", {"type": "STOP", "sessionId": transport})
            for _ in range(50):
                if backend.status().state == "IDLE":
                    break
                await asyncio.sleep(.1)
            assert backend.status().state == "IDLE"
            print("PASS receiver-stop-stalled-source", flush=True)
            relaunched = await request("receiver", "receiver-0", {"type": "LAUNCH", "appId": "CC1AD845"})
            transport = relaunched["status"]["applications"][0]["transportId"]
            await send("tp.connection", transport, {"type": "CONNECT"})
            await load(autoplay=True)
            await state(lambda s: s["playerState"] == "PLAYING", "relaunch-after-stop")
            await send("tp.connection", transport, {"type": "CLOSE"})
            for _ in range(50):
                if backend.status().state == "IDLE":
                    break
                await asyncio.sleep(.1)
            assert backend.status().state == "IDLE"
            print("PASS app-disconnect", flush=True)
        finally:
            if writer:
                writer.close()
                with contextlib.suppress(OSError):
                    await writer.wait_closed()
            if player_task:
                player_task.cancel()
                await asyncio.gather(player_task, return_exceptions=True)
            if artwork_runner:
                await artwork_runner.cleanup()
            if process and process.returncode is None:
                process.send_signal(signal.SIGINT)
                try:
                    await asyncio.wait_for(process.wait(), 10)
                except TimeoutError:
                    process.kill()
                    await process.wait()
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--certs", type=Path, required=True)
    parser.add_argument("--airplay-config", type=Path, help="opt in to audio on this explicit AirPlay target")
    parser.add_argument("--cliairplay", default="cliairplay")
    parser.add_argument("--silent-fixture", action="store_true", help="decode zero-valued PCM; no audible test tone")
    parser.add_argument('--artwork-check', action='store_true', help='test real square conversion, HTTP serving and Cast feedback; needs new frontend and FFmpeg')
    parser.add_argument("--fixture-format", choices=("wav", "mp3", "flac"), default="wav",
                        help="MP3/FLAC fixtures require FFmpeg; no external media is fetched")
    args = parser.parse_args()
    asyncio.run(run(args.binary, args.certs, args.airplay_config, args.cliairplay,
                    args.silent_fixture, args.fixture_format, args.artwork_check))
