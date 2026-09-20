"""Runnable YouTube Music receiver using DIAL and YouTube Lounge."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from pathlib import Path

from cast_audio_lab.backend import AudioBackend, CommandAudioBackend, NullAudioBackend
from .lounge import LoungeClient, LoungeCommandEngine, YtDlpAudioResolver
from .server import _local_ipv4
from .youtube_dial import DialIdentity, YouTubeDialServer, new_device_id


LOG = logging.getLogger(__name__)


async def run(args: argparse.Namespace) -> None:
    backend: AudioBackend
    if args.player_command:
        backend = CommandAudioBackend(args.player_command)
    else:
        backend = NullAudioBackend()

    state_directory = Path(args.state_dir).expanduser()
    state_directory.mkdir(parents=True, exist_ok=True)
    device_id_path = state_directory / "youtube-device-id"
    if device_id_path.exists():
        device_id = device_id_path.read_text().strip()
    else:
        device_id = new_device_id()
        device_id_path.write_text(device_id)

    engine = LoungeCommandEngine(
        backend,
        YtDlpAudioResolver(),
        autoplay_on_set_playlist=not args.no_autoplay,
    )
    lounge = LoungeClient(args.name, device_id, engine)
    credentials = await lounge.bootstrap()
    address = args.advertise_address or _local_ipv4()
    identity = DialIdentity(args.name, device_id, address, args.http_port)
    dial = YouTubeDialServer(
        identity,
        lambda: lounge.credentials,
        lounge.register_pairing_code,
    )
    await dial.start(advertise=not args.no_ssdp)
    LOG.info(
        "YouTube screen ready (screen ID length %d); autoplay-on-playlist=%s",
        len(credentials.screen_id),
        not args.no_autoplay,
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    lounge_task = asyncio.create_task(lounge.run())
    stop_task = asyncio.create_task(stop.wait())
    try:
        done, _ = await asyncio.wait(
            {lounge_task, stop_task}, return_when=asyncio.FIRST_COMPLETED
        )
        if lounge_task in done:
            lounge_task.result()
    finally:
        lounge.stop()
        lounge_task.cancel()
        await asyncio.gather(lounge_task, return_exceptions=True)
        stop_task.cancel()
        await asyncio.gather(stop_task, return_exceptions=True)
        await dial.close()
        await backend.shutdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Experimental audio-only YouTube Music DIAL receiver"
    )
    parser.add_argument("--name", default="YouTube Audio Lab")
    parser.add_argument("--http-port", type=int, default=3600)
    parser.add_argument("--advertise-address")
    parser.add_argument("--no-ssdp", action="store_true")
    parser.add_argument("--state-dir", default=".state")
    parser.add_argument(
        "--player-command",
        help='argv template, for example: "mpv --no-video {url}"',
    )
    parser.add_argument(
        "--no-autoplay",
        action="store_true",
        help="wait for an explicit play command after setPlaylist",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
