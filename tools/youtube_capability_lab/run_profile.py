#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Isolated lab receiver with a silent protocol player, never an audio renderer.

Requires websockets; all certs are read from an explicit external path. The root
operator owns deployment and phone actions. This helper never invokes ADB/SSH.
Raw receiver logs are private files. JSON stdout includes fixed labels/counts,
never media URLs, tokens, metadata, certificate contents, or raw peer messages.
"""
from __future__ import annotations
import argparse
import asyncio
import contextlib
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import signal
import time
import uuid


def event(kind, **fields):
    print(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                      "event": kind, **fields}), flush=True)


class SilentPlayer:
    """Acknowledge commands without fetching/decoding media or opening audio."""
    def __init__(self, websocket):
        self.websocket = websocket
        self.session = None
        self.media_id = None
        self.state = "IDLE"
        self.level, self.muted, self.revision = 0.25, False, 0
        self.position, self.changed = 0.0, time.monotonic()
        self.duration = None
        self.sequence = 0

    def current_time(self):
        elapsed = time.monotonic() - self.changed if self.state == "PLAYING" else 0
        return self.position + elapsed

    async def report(self):
        if self.session is None:
            return
        value = {"type": "state", "sessionId": self.session,
                 "playerState": self.state, "currentTime": self.current_time(),
                 "volume": self.level, "muted": self.muted,
                 "volumeRevision": self.revision}
        if self.media_id is not None:
            value["mediaSessionId"] = self.media_id
        if self.duration is not None:
            value["duration"] = self.duration
        if self.state == "IDLE":
            value["idleReason"] = "CANCELLED"
        await self.websocket.send(json.dumps(value))

    async def ticker(self):
        while True:
            await asyncio.sleep(1)
            await self.report()

    async def receive(self):
        async for raw in self.websocket:
            message = json.loads(raw)
            command = message.get("type")
            if command not in {"load", "play", "pause", "seek", "stop", "volume"}:
                continue
            if message["sessionId"] != self.session:
                self.session = message["sessionId"]
                self.media_id, self.state = None, "IDLE"
                self.position, self.duration = 0.0, None
            self.position, self.changed = self.current_time(), time.monotonic()
            self.sequence += 1
            details = {}
            if command == "load":
                media = message["media"]
                streams = media.get("streams", [])
                self.media_id = media.get("mediaSessionId")
                self.duration = media.get("duration")
                self.position = float(media.get("startTime", 0))
                self.state = "PLAYING" if media.get("autoplay", True) else "PAUSED"
                details = {"stream_count": len(streams),
                           "audio_mimes": sum(str(s.get("contentType", "")).startswith("audio/") for s in streams),
                           "video_mimes": sum(str(s.get("contentType", "")).startswith("video/") for s in streams),
                           "media_generation_present": isinstance(self.media_id, int)}
            elif command == "play":
                self.state = "PLAYING"
            elif command == "pause":
                self.state = "PAUSED"
            elif command == "seek":
                self.position = float(message["position"])
            elif command == "stop":
                self.state = "IDLE"
            elif command == "volume":
                # A real backend initializes from its actual output. This silent
                # backend explicitly starts at 25%, rather than borrowing 100%.
                if not message.get("initialize", False):
                    self.level, self.muted = float(message["level"]), bool(message["muted"])
                self.revision = message.get("volumeRevision", self.revision)
            event("silent_player_command", command=command, sequence=self.sequence,
                  session_tag=hashlib.sha256(self.session.encode()).hexdigest()[:10],
                  audio_verified=False, **details)
            await self.report()


async def run(args):
    from websockets.asyncio.client import connect
    loop = asyncio.get_running_loop()
    current = asyncio.current_task()
    loop.add_signal_handler(signal.SIGTERM, current.cancel)
    profiles = json.loads(args.profiles.read_text())
    if args.profile not in profiles:
        raise SystemExit("unknown-profile")
    profile = profiles[args.profile]
    directory = args.run_root.resolve() / args.profile
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    if any(directory.glob("receiver.pid")):
        raise SystemExit("profile-already-has-pid-remove-stale-file-only-after-checking-process")
    boolean = lambda value: "true" if value else "false"
    model = json.dumps(profile.get("model", "Audio Speaker"))
    config = (f"[device]\nmodel = {model}\n[device.capabilities]\n"
              f"display_supported = {boolean(profile.get('eureka_display', profile['display']))}\n"
              f"multizone_supported = {boolean(profile.get('multizone', True))}\n"
              f"cloud_groups_supported = {boolean(profile.get('cloud_groups', False))}\n"
              "[network]\nbind_host = \"0.0.0.0\"\nplayer_bind_host = \"127.0.0.1\"\nplayer_port = 0\n"
              "[volume]\nlevel = 0.25\nmuted = false\n"
              "[cast.device_capabilities]\n"
              f"display_supported = {boolean(profile.get('api_display', False))}\n")
    (directory / "config.toml").write_text(config)
    # An explicit epoch gives each live attempt a fresh Cast identity and name,
    # preventing a sender from selecting an old cached route/port after restart.
    epoch = os.environ.get("CAST_LAB_IDENTITY_EPOCH", "").strip()
    seed = "cast-hybrid-lab-20261108/" + args.profile
    friendly_name = "Audio Lab Probe " + args.profile
    if epoch:
        seed += "/" + epoch
        friendly_name += " [" + hashlib.sha256(epoch.encode()).hexdigest()[:8] + "]"
    installation = uuid.uuid5(uuid.NAMESPACE_URL, seed)
    (directory / "installation_id").write_text(str(installation))
    identity_path = directory / "lab-identity.json"
    identity_path.write_text(json.dumps({"friendly_name":friendly_name, "epoch":epoch}) + "\n")
    identity_path.chmod(0o600)
    environment = os.environ.copy()
    environment.update({"CAST_LAB_MDNS_CA": str(int(profile["mdns_ca"])),
                        "CAST_LAB_DEVICE_CAPABILITIES": str(int(profile["device_capabilities"]))})
    for key, envkey in (("mdns_icon", "CAST_LAB_MDNS_ICON"),
                        ("device_icon_url", "CAST_LAB_DEVICE_ICON_URL")):
        environment.pop(envkey, None)
        if key in profile:
            environment[envkey] = profile[key]
    log_path = directory / "receiver.log"
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    descriptor = os.open(log_path, flags, 0o600)
    process = None
    try:
        with os.fdopen(descriptor, "wb") as log:
            process = await asyncio.create_subprocess_exec(
                str(args.binary.resolve()), "--certs", str(args.certs.resolve()),
                "--data-dir", str(directory), "--log-level", "info",
                stdin=asyncio.subprocess.DEVNULL, stdout=log, stderr=log, env=environment)
        (directory / "receiver.pid").write_text(str(process.pid))
        bridge = None
        for _ in range(200):
            if process.returncode is not None:
                raise RuntimeError("receiver-exited-before-ready")
            text = re.sub(r"\x1b\[[0-9;]*m", "", log_path.read_text(errors="replace"))
            match = re.search(r"register=ws://[^: ]+:(\d+)/player", text)
            if match:
                bridge = int(match.group(1))
                break
            await asyncio.sleep(0.1)
        if bridge is None:
            raise RuntimeError("receiver-not-ready")
        options = {"open_timeout": 10, "close_timeout": 2}
        if "proxy" in inspect.signature(connect).parameters:
            options["proxy"] = None
        async with connect(f"ws://127.0.0.1:{bridge}/player", **options) as websocket:
            await websocket.send(json.dumps({"type": "register", "player": {
                "protocolVersion": 2, "playerId": "cast-hybrid-lab-" + args.profile,
                "name": friendly_name,
                "capabilities": {"volumeRevisions": True, "localAudioCache": False,
                                 "audioCodecs": ["aac", "mp3", "opus", "flac", "vorbis"],
                                 "controlRequests": ["play", "pause", "seek", "stop", "volume"]}}}))
            event("lab_profile_registered", profile=args.profile, receiver_pid=process.pid,
                  friendly_name=friendly_name, epoch=epoch,
                  purpose=profile["purpose"], mdns_ca=profile["mdns_ca"],
                  device_capabilities=profile["device_capabilities"],
                  output="silent-protocol-acknowledger", audio_verified=False,
                  private_log=str(log_path))
            player = SilentPlayer(websocket)
            ticker = asyncio.create_task(player.ticker())
            try:
                await player.receive()
            finally:
                ticker.cancel()
                await asyncio.gather(ticker, return_exceptions=True)
    finally:
        if process is not None and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                process.send_signal(signal.SIGINT)
            try:
                await asyncio.wait_for(process.wait(), 8)
            except TimeoutError:
                process.kill()
                await process.wait()
        (directory / "receiver.pid").unlink(missing_ok=True)
        event("lab_profile_stopped", profile=args.profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--certs", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--profiles", type=Path, default=Path(__file__).with_name("profiles.json"))
    parser.add_argument("--run-root", type=Path, default=Path("/tmp/cast-hybrid-lab-runs-20261108"))
    args = parser.parse_args()
    for value in (args.binary, args.certs, args.profiles):
        if not value.is_file():
            parser.error("one required input file is absent")
    try:
        asyncio.run(run(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except Exception as error:
        event("lab_failure", exception_type=type(error).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
