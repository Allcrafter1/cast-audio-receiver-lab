#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Isolated TuneIn Cast/bridge smoke test, with no audio output.

Requires cryptography and websockets. Creates its own temporary test identity,
receiver, loopback fixture and fake player; never uses production credentials
or an existing receiver. The default checks direct HTTP media without fetching
external services. --live-station explicitly enables the public TuneIn station
lookup. Resolved media URLs are validated in memory, never printed or fetched.
This tests receiver routing and controls, not decoding or stock-sender trust.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
from datetime import datetime, timedelta, timezone
import io
import inspect
import json
from pathlib import Path
import re
import signal
import ssl
import sys
import tempfile
from urllib.parse import urlsplit
import uuid
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.legacy_python_receiver.legacy_cast_receiver.wire import (
    CastMessage, read_cast_message, write_cast_message,
)

PREFIX = "urn:x-cast:com.google.cast."


class SmokeFailure(RuntimeError):
    """A fixed diagnostic that cannot contain remote URLs or credentials."""


def require(condition, label):
    if not condition:
        raise SmokeFailure(label)


def test_identity(directory):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TuneIn smoke fixture")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
            .sign(key, hashes.SHA256()))
    public = cert.public_bytes(serialization.Encoding.PEM).decode()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
    # No device-auth exchange is requested. These fixed synthetic signatures and
    # CRL prevent any production-bundle dependency or automatic Google CRL fetch.
    manifest = {"cpu": public, "ica": public, "crl": base64.b64encode(b"test").decode(),
                "certs": [{"pu": public, "pr": private,
                           "sig_sha1": "dGVzdA==", "sig_sha256": "dGVzdA=="}]}
    path = directory / "test-certs.json"
    path.write_text(json.dumps(manifest))
    path.chmod(0o600)
    context = ssl.create_default_context(cadata=public)
    return path, context


class FakePlayer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.session = None
        self.media_id = None
        self.state = "IDLE"
        self.level, self.muted, self.revision = 1.0, False, 0
        self.loads = []
        self.commands = []
        self.task = None

    def check(self):
        if self.task.done():
            self.task.result()
            raise SmokeFailure("fake-player-disconnected")

    async def report(self):
        if self.session is None:
            return
        value = {"type": "state", "sessionId": self.session, "playerState": self.state,
                 "currentTime": 0, "volume": self.level, "muted": self.muted,
                 "volumeRevision": self.revision}
        if self.media_id is not None:
            value["mediaSessionId"] = self.media_id
        if self.state == "IDLE":
            value["idleReason"] = "CANCELLED"
        await self.websocket.send(json.dumps(value))

    async def serve(self):
        async for raw in self.websocket:
            message = json.loads(raw)
            command = message.get("type")
            if command not in {"load", "play", "pause", "stop", "volume"}:
                continue
            session = message["sessionId"]
            if session != self.session:
                self.session, self.media_id, self.state = session, None, "IDLE"
            self.commands.append(command)
            if command == "load":
                media = message["media"]
                require(bool(media.get("streams")), "bridge-load-without-stream")
                for stream in media["streams"]:
                    source = urlsplit(stream["url"])
                    require(source.scheme in {"http", "https"} and bool(source.hostname)
                            and source.username is None and source.password is None,
                            "bridge-load-invalid-stream-url")
                    require(bool(stream.get("contentType")), "bridge-load-without-mime")
                self.loads.append(media)
                self.media_id = media.get("mediaSessionId")
                require(isinstance(self.media_id, int), "bridge-load-without-generation")
                self.state = "PLAYING" if media.get("autoplay", True) else "PAUSED"
            elif command == "play":
                self.state = "PLAYING"
            elif command == "pause":
                self.state = "PAUSED"
            elif command == "stop":
                self.state = "IDLE"
            elif command == "volume":
                self.level, self.muted = message["level"], message["muted"]
                self.revision = message.get("volumeRevision", self.revision)
            await self.report()


class Sender:
    def __init__(self, reader, writer, player):
        self.reader, self.writer, self.player = reader, writer, player
        self.serial = 0
        self.media_id = None

    async def send(self, namespace, destination, payload):
        await write_cast_message(self.writer, CastMessage(
            "sender-tunein-smoke", destination, PREFIX + namespace,
            payload_utf8=json.dumps(payload)))

    async def request(self, namespace, destination, payload, expect_error=False):
        self.player.check()
        self.serial += 1
        ident = self.serial
        payload = dict(payload, requestId=ident)
        if namespace == "media" and payload["type"] in {"PLAY", "PAUSE", "STOP", "SET_VOLUME"}:
            payload["mediaSessionId"] = self.media_id
        await self.send(namespace, destination, payload)
        async with asyncio.timeout(30):
            while True:
                message = await read_cast_message(self.reader)
                value = json.loads(message.payload_utf8 or "{}")
                if value.get("type") == "PING":
                    await self.send("tp.heartbeat", message.source_id, {"type": "PONG"})
                if value.get("type") in {"INVALID_REQUEST", "LOAD_FAILED", "LAUNCH_ERROR"}:
                    if expect_error and value.get("requestId") == ident:
                        return value
                    raise SmokeFailure("cast-request-rejected")
                if value.get("requestId") == ident and message.namespace == PREFIX + namespace:
                    if not expect_error:
                        return value

    async def launch(self, app_id):
        value = await self.request("receiver", "receiver-0", {"type": "LAUNCH", "appId": app_id})
        apps = value["status"].get("applications", [])
        require(len(apps) == 1 and apps[0]["appId"] == app_id, "wrong-launched-app")
        transport = apps[0]["transportId"]
        await self.send("tp.connection", transport, {"type": "CONNECT"})
        self.media_id = None
        return transport

    async def state(self, transport, predicate, label):
        async with asyncio.timeout(45):
            while True:
                self.player.check()
                value = await self.request("media", transport, {"type": "GET_STATUS"})
                values = value.get("status", [])
                if values and predicate(values[0]):
                    self.media_id = values[0].get("mediaSessionId")
                    print("PASS", label, flush=True)
                    return values[0]
                await asyncio.sleep(.05)


async def log_port(process, path, pattern):
    async with asyncio.timeout(15):
        while True:
            require(process.returncode is None, "isolated-frontend-exited")
            text = re.sub(r"\x1b\[[0-9;]*m", "", path.read_text(errors="replace"))
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
            await asyncio.sleep(.05)


async def exercise(sender, player, fixture_url, live_station, guide_id, switch_guide_id,
                   tunein_only=False):
    transport = await sender.launch("12F05308")
    print("PASS tunein-app-launch", flush=True)
    media = {"contentId": fixture_url, "contentType": "audio/wav", "streamType": "LIVE",
             "metadata": {"metadataType": 0, "title": "TuneIn smoke fixture"}}
    payload = {"type": "LOAD", "autoplay": True, "media": media}
    if live_station:
        payload["autoplay"] = False
        payload["currentTime"] = 37.25
        payload["media"] = {"contentId": guide_id, "contentType": "audio/mpeg", "streamType": "LIVE"}
        payload["customData"] = {"guideId": guide_id, "serial": "cast-audio-tunein-smoke",
                                 "partnerId": "qZjjnm85", "version": 1.6201}
    await sender.request("media", transport, payload)
    status = await sender.state(transport, lambda s: s["playerState"] == "PLAYING",
                                "tunein-station-load" if live_station else "tunein-fixture-load")
    require(len(player.loads) == 1, "unexpected-tunein-load-count")
    require(player.loads[-1]["streamType"] == "LIVE", "radio-not-live-at-bridge")
    require(status["media"]["streamType"] == "LIVE", "radio-not-live-at-sender")
    require(bool(player.loads[-1].get("title")), "radio-metadata-missing")
    require(not status["supportedMediaCommands"] & 2, "live-seek-advertised")
    if live_station:
        require(player.state == "PLAYING" and player.loads[-1].get("startTime") == 0
                and player.loads[-1].get("autoplay") is True,
                "native-tunein-autostart-not-normalized")
        require("play" not in player.commands, "native-tunein-required-extra-play")
        print("PASS native-tunein-autostart-at-live-edge", flush=True)
    print("PASS tunein-live-metadata-and-controls", flush=True)
    await sender.request("media", transport, {"type": "PAUSE"})
    await sender.state(transport, lambda s: s["playerState"] == player.state == "PAUSED", "tunein-pause")
    await sender.request("media", transport, {"type": "PLAY"})
    await sender.state(transport, lambda s: s["playerState"] == player.state == "PLAYING", "tunein-resume")
    await sender.request("media", transport,
                         {"type": "SET_VOLUME", "volume": {"level": .37, "muted": True}})
    await sender.state(transport, lambda s: abs(s["volume"]["level"] - .37) < .001
                        and s["volume"]["muted"] and abs(player.level - .37) < .001
                        and player.muted and player.revision > 0, "tunein-sender-volume")
    player.level, player.muted = .41, False
    await player.report()
    await sender.state(transport, lambda s: abs(s["volume"]["level"] - .41) < .001
                        and not s["volume"]["muted"], "tunein-output-volume-feedback")
    old_id = sender.media_id
    failed = await sender.request("media", transport, {"type": "LOAD", "media": {
        "contentId": "file:///invalid-tunein-fixture", "contentType": "audio/wav"}},
        expect_error=True)
    require(failed["type"] == "LOAD_FAILED" and len(player.loads) == 1,
            "invalid-tunein-load-reached-player")
    print("PASS tunein-invalid-load-rejected", flush=True)
    second = dict(payload, autoplay=False)
    second["media"] = dict(payload["media"])
    if live_station:
        second["currentTime"] = 0
        second["media"]["contentId"] = switch_guide_id or guide_id
        second["customData"] = dict(payload["customData"], guideId=switch_guide_id or guide_id)
    else:
        second["media"]["contentId"] = fixture_url.replace("/radio.wav", "/second.wav")
        second["media"]["metadata"] = {"title": "TuneIn second smoke fixture"}
    previous_plays = player.commands.count("play")
    await sender.request("media", transport, second)
    expected_state = "PLAYING" if live_station else "PAUSED"
    status = await sender.state(transport, lambda s: s["playerState"] == expected_state
                                and s.get("mediaSessionId", 0) > old_id,
                                "tunein-replacement-load-after-failure")
    require(len(player.loads) == 2 and player.loads[-1]["streamType"] == "LIVE"
            and status["media"]["streamType"] == "LIVE", "replacement-radio-invalid")
    require(player.loads[-1].get("title"), "replacement-radio-metadata-missing")
    if live_station:
        require(player.state == "PLAYING" and player.loads[-1].get("startTime") == 0
                and player.loads[-1].get("autoplay") is True,
                "replacement-native-tunein-autostart-not-normalized")
        require(player.commands.count("play") == previous_plays,
                "replacement-native-tunein-required-extra-play")
        print("PASS replacement-native-tunein-autostart-at-live-edge", flush=True)
        await sender.request("media", transport, {"type": "PAUSE"})
        await sender.state(transport, lambda s: s["playerState"] == player.state == "PAUSED",
                            "tunein-replacement-pause")
    await sender.request("media", transport, {"type": "PLAY"})
    await sender.state(transport, lambda s: s["playerState"] == player.state == "PLAYING",
                        "tunein-replacement-play")
    previous_stops = player.commands.count("stop")
    await sender.request("media", transport, {"type": "STOP"})
    await sender.state(transport, lambda s: s["playerState"] == player.state == "IDLE"
                        and player.commands.count("stop") > previous_stops, "tunein-stop")

    if tunein_only:
        return

    transport = await sender.launch("CC1AD845")
    await sender.request("media", transport, {"type": "LOAD", "autoplay": False,
                         "media": {"contentId": fixture_url, "contentType": "audio/wav",
                                   "streamType": "BUFFERED", "duration": 2,
                                   "metadata": {"title": "DMR smoke fixture"}}})
    status = await sender.state(transport, lambda s: s["playerState"] == "PAUSED",
                                "default-media-after-tunein")
    require(len(player.loads) == 3 and player.loads[-1]["streams"][0]["url"] == fixture_url,
            "default-media-stream-changed")
    require(status["media"]["streamType"] == "BUFFERED", "default-media-became-live")
    previous_stops = player.commands.count("stop")
    await sender.request("media", transport, {"type": "STOP"})
    await sender.state(transport, lambda s: s["playerState"] == player.state == "IDLE"
                        and player.commands.count("stop") > previous_stops, "default-media-stop")


async def run(binary, live_station=False, guide_id="s24861", switch_guide_id=None,
              tunein_only=False):
    from websockets.asyncio.client import connect

    data = io.BytesIO()
    with wave.open(data, "wb") as output:
        output.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        output.writeframes(bytes(8000 * 2 * 2))
    audio = data.getvalue()
    handlers, writers = set(), set()

    async def fixture(reader, writer):
        task = asyncio.current_task()
        handlers.add(task)
        writers.add(writer)
        try:
            async with asyncio.timeout(5):
                request = await reader.readuntil(b"\r\n\r\n")
                require(request.split(b" ")[1] in {b"/radio.wav", b"/second.wav"},
                        "unexpected-fixture-path")
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: audio/wav\r\nContent-Length: "
                             + str(len(audio)).encode() + b"\r\nConnection: close\r\n\r\n" + audio)
                await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
            writers.discard(writer)
            handlers.discard(task)

    with tempfile.TemporaryDirectory(prefix="cast-tunein-smoke-") as temporary:
        directory = Path(temporary)
        certs, context = test_identity(directory)
        log_path = directory / "frontend.log"
        process = server = cast_writer = player_task = None
        try:
            server = await asyncio.start_server(fixture, "127.0.0.1", 0)
            fixture_url = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}/radio.wav"
            with log_path.open("wb") as log:
                process = await asyncio.create_subprocess_exec(
                    str(binary.resolve()), "--certs", str(certs), "--data-dir", temporary,
                    "--bind-host", "127.0.0.1", "--player-port", "0", "--log-level", "info",
                    stdin=asyncio.subprocess.DEVNULL, stdout=log, stderr=log)
            bridge_port = await log_port(process, log_path, r"register=ws://[^: ]+:(\d+)/player")
            options = {"open_timeout": 10, "close_timeout": 2}
            if "proxy" in inspect.signature(connect).parameters:
                options["proxy"] = None
            async with connect(f"ws://127.0.0.1:{bridge_port}/player", **options) as websocket:
                await websocket.send(json.dumps({"type": "register", "player": {
                    "protocolVersion": 2, "playerId": str(uuid.uuid4()), "name": "TuneIn isolated smoke",
                    "capabilities": {"volumeRevisions": True, "localAudioCache": False,
                                     "audioCodecs": ["aac", "mp3", "opus"],
                                     "controlRequests": ["play", "pause", "stop", "volume"]}}}))
                player = FakePlayer(websocket)
                player_task = player.task = asyncio.create_task(player.serve())
                cast_port = await log_port(process, log_path, r"cast_port=(\d+)")
                reader, cast_writer = await asyncio.open_connection(
                    "127.0.0.1", cast_port, ssl=context, server_hostname="localhost")
                sender = Sender(reader, cast_writer, player)
                await sender.send("tp.connection", "receiver-0", {"type": "CONNECT"})
                await exercise(sender, player, fixture_url, live_station, guide_id,
                               switch_guide_id, tunein_only)
                print("PASS isolated-tunein-smoke-no-audio", flush=True)
        finally:
            if cast_writer is not None:
                cast_writer.close()
                with contextlib.suppress(OSError, TimeoutError):
                    await asyncio.wait_for(cast_writer.wait_closed(), 2)
            if player_task is not None:
                player_task.cancel()
                await asyncio.gather(player_task, return_exceptions=True)
            if process is not None and process.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    process.send_signal(signal.SIGINT)
                try:
                    await asyncio.wait_for(process.wait(), 8)
                except TimeoutError:
                    with contextlib.suppress(ProcessLookupError):
                        process.kill()
                    await process.wait()
            if server is not None:
                server.close()
                await server.wait_closed()
            for writer in tuple(writers):
                writer.close()
            for task in tuple(handlers):
                task.cancel()
            await asyncio.gather(*handlers, return_exceptions=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True, help="candidate frontend executable")
    parser.add_argument("--live-station", action="store_true",
                        help="opt in to public TuneIn station resolution; never plays audio")
    parser.add_argument("--guide-id", default="s24861", help="station for --live-station")
    parser.add_argument("--switch-guide-id", help="optional second station for --live-station")
    parser.add_argument("--tunein-only", action="store_true",
                        help="check TuneIn without the subsequent Default Media Receiver test")
    args = parser.parse_args()
    if not re.fullmatch(r"s[0-9]+", args.guide_id):
        parser.error("guide-id must be s followed by digits")
    if args.switch_guide_id is not None and not re.fullmatch(r"s[0-9]+", args.switch_guide_id):
        parser.error("switch-guide-id must be s followed by digits")
    if args.switch_guide_id is not None and not args.live_station:
        parser.error("switch-guide-id requires live-station")
    if not args.binary.is_file():
        parser.error("binary must be an existing executable file")
    try:
        asyncio.run(run(args.binary, args.live_station, args.guide_id, args.switch_guide_id,
                        args.tunein_only))
    except SmokeFailure as error:
        print("FAIL", error, file=sys.stderr)
        return 1
    except (ImportError, OSError, ValueError, TimeoutError, KeyError) as error:
        # Exception strings can contain a resolved URL or request parameters.
        print("FAIL tunein-smoke", type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
