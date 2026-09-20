"""TLS Cast channel server."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import socket
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .auth import DEVICE_AUTH_NAMESPACE, AuthProvider, load_auth_provider
from cast_audio_lab.airplay import AirPlayAudioBackend, AirPlayTarget
from cast_audio_lab.backend import (
    AudioBackend,
    CommandAudioBackend,
    NullAudioBackend,
    PlaybackStatus,
)
from .lounge import LoungeClient, LoungeCommandEngine, YtDlpAudioResolver
from .mdns import MdnsAdvertiser
from .protocol import CastProtocolEngine
from .tls import TlsIdentity, create_tls_identity
from .wire import (
    CastMessage,
    PayloadType,
    WireError,
    read_cast_message,
    write_cast_message,
)


LOG = logging.getLogger(__name__)


@dataclass(eq=False, slots=True)
class _CastClient:
    writer: asyncio.StreamWriter
    receiver_senders: set[str] = field(default_factory=set)
    media_senders: set[str] = field(default_factory=set)
    write_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class CastAudioServer:
    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        identity: TlsIdentity,
        backend: AudioBackend,
        auth_provider: AuthProvider,
        youtube_screen_id: Callable[[], str | None] | None = None,
        youtube_device_id: Callable[[], str | None] | None = None,
    ) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.identity = identity
        self.backend = backend
        self.auth_provider = auth_provider
        self.youtube_screen_id = youtube_screen_id
        self.youtube_device_id = youtube_device_id
        self._server: asyncio.Server | None = None
        self.engine = CastProtocolEngine(
            self.name,
            self.backend,
            youtube_screen_id=self.youtube_screen_id,
            youtube_device_id=self.youtube_device_id,
        )
        self._engine_lock = asyncio.Lock()
        self._clients: set[_CastClient] = set()
        self._broadcast_task: asyncio.Task[None] | None = None
        self.backend.add_status_listener(self._backend_status_changed)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
            ssl=self.identity.context,
        )
        sockets = ", ".join(str(sock.getsockname()) for sock in self._server.sockets or [])
        LOG.info("Cast TLS channel listening on %s", sockets)

    async def close(self) -> None:
        self.backend.remove_status_listener(self._backend_status_changed)
        if self._broadcast_task:
            self._broadcast_task.cancel()
            await asyncio.gather(self._broadcast_task, return_exceptions=True)
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        await self.backend.shutdown()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        LOG.info("Sender connected: %s", peer)
        client = _CastClient(writer)
        self._clients.add(client)
        try:
            while True:
                message = await read_cast_message(reader)
                if message.namespace == "urn:x-cast:com.google.cast.receiver":
                    client.receiver_senders.add(message.source_id)
                elif message.namespace == "urn:x-cast:com.google.cast.media":
                    client.media_senders.add(message.source_id)
                if message.namespace == DEVICE_AUTH_NAMESPACE:
                    if message.payload_type != PayloadType.BINARY:
                        LOG.warning("Non-binary device-auth challenge from %s", peer)
                        break
                    response = await self.auth_provider.respond(
                        message.payload_binary,
                        self.identity.certificate_der,
                    )
                    if response is None:
                        LOG.warning(
                            "Device attestation unavailable; stock sender %s "
                            "will reject this receiver",
                            peer,
                        )
                        break
                    await self._write(
                        client,
                        CastMessage(
                            source_id=message.destination_id,
                            destination_id=message.source_id,
                            namespace=DEVICE_AUTH_NAMESPACE,
                            payload_type=PayloadType.BINARY,
                            payload_binary=response,
                        ),
                    )
                    continue
                async with self._engine_lock:
                    responses = await self.engine.handle(message)
                for response in responses:
                    await self._write(client, response)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        except WireError as exc:
            LOG.warning("Invalid Cast frame from %s: %s", peer, exc)
        except Exception:
            LOG.exception("Unhandled sender error for %s", peer)
        finally:
            self._clients.discard(client)
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
            LOG.info("Sender disconnected: %s", peer)

    async def _write(self, client: _CastClient, message: CastMessage) -> None:
        async with client.write_lock:
            await write_cast_message(client.writer, message)

    def _backend_status_changed(self, status: PlaybackStatus) -> None:
        del status
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_status())

    async def _broadcast_status(self) -> None:
        # Collapse changes made in one command into one coherent snapshot.
        await asyncio.sleep(0)
        clients = tuple(self._clients)
        for client in clients:
            try:
                for sender_id in tuple(client.receiver_senders):
                    await self._write(
                        client, self.engine.receiver_status_for(sender_id)
                    )
                if self.engine.state.app_id:
                    for sender_id in tuple(client.media_senders):
                        await self._write(
                            client, self.engine.media_status_for(sender_id)
                        )
            except (ConnectionError, OSError):
                self._clients.discard(client)


async def run(args: argparse.Namespace) -> None:
    state_directory = Path(args.state_dir).expanduser()
    state_directory.mkdir(parents=True, exist_ok=True)
    identity = create_tls_identity(state_directory, args.name)
    backend: AudioBackend
    if args.airplay_host:
        backend = AirPlayAudioBackend(
            AirPlayTarget(
                host=args.airplay_host,
                port=args.airplay_port,
                protocol=args.airplay_protocol,
                device_id=args.airplay_device_id or "",
                name=args.airplay_target_name or "",
                credentials=args.airplay_credentials,
                legacy_secret=args.airplay_legacy_secret,
            ),
            cliairplay=args.cliairplay,
            ffmpeg=args.ffmpeg,
            latency_ms=args.airplay_latency,
        )
    elif args.player_command:
        backend = CommandAudioBackend(args.player_command)
    else:
        backend = NullAudioBackend()
    auth_provider = load_auth_provider(args.auth_provider)
    lounge: LoungeClient | None = None
    lounge_task: asyncio.Task[None] | None = None
    if args.youtube:
        device_id_path = state_directory / "youtube-device-id"
        if device_id_path.exists():
            youtube_device_id = device_id_path.read_text().strip()
        else:
            youtube_device_id = str(uuid.uuid4())
            device_id_path.write_text(youtube_device_id)
        lounge_engine = LoungeCommandEngine(
            backend,
            YtDlpAudioResolver(),
            autoplay_on_set_playlist=not args.no_youtube_autoplay,
        )
        lounge = LoungeClient(args.name, youtube_device_id, lounge_engine)
        credentials = await lounge.bootstrap()
        LOG.info(
            "YouTube MDX screen ready (screen ID length %d)",
            len(credentials.screen_id),
        )

    def youtube_screen_id() -> str | None:
        if lounge is None or lounge.credentials is None:
            return None
        return lounge.credentials.screen_id

    def youtube_device_id() -> str | None:
        return lounge.device_id if lounge is not None else None

    server = CastAudioServer(
        args.name,
        args.bind,
        args.port,
        identity,
        backend,
        auth_provider,
        youtube_screen_id=youtube_screen_id if lounge is not None else None,
        youtube_device_id=youtube_device_id if lounge is not None else None,
    )
    advertiser: MdnsAdvertiser | None = None
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    await server.start()
    if not args.no_mdns:
        address = args.advertise_address or _local_ipv4()
        cast_device_id_path = state_directory / "cast-device-id"
        if cast_device_id_path.exists():
            cast_device_id = cast_device_id_path.read_text().strip()
        else:
            cast_device_id = str(uuid.uuid4())
            cast_device_id_path.write_text(cast_device_id)
        advertiser = MdnsAdvertiser(
            args.name, address, args.port, device_id=cast_device_id
        )
        await advertiser.start()
        LOG.info(
            "Advertising %s at %s:%d as audio-only Cast target",
            args.name,
            address,
            args.port,
        )
    if args.auth_provider:
        LOG.info("External device-auth provider loaded")
    else:
        LOG.warning(
            "No device-auth provider configured: protocol tests work, "
            "but stock Google Cast senders will fail attestation"
        )
    if lounge is not None:
        lounge_task = asyncio.create_task(lounge.run())
    try:
        await stop.wait()
    finally:
        if lounge is not None:
            lounge.stop()
        if lounge_task is not None:
            lounge_task.cancel()
            await asyncio.gather(lounge_task, return_exceptions=True)
        if advertiser:
            await advertiser.close()
        await server.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Experimental audio-only Cast V2 receiver"
    )
    parser.add_argument("--name", default="Cast Audio Lab")
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--advertise-address")
    parser.add_argument("--no-mdns", action="store_true")
    parser.add_argument("--state-dir", default=".state")
    parser.add_argument(
        "--player-command",
        help='argv template, for example: "mpv --no-video {url}"',
    )
    airplay = parser.add_argument_group("AirPlay output")
    airplay.add_argument("--airplay-host", help="selected AirPlay receiver IP")
    airplay.add_argument("--airplay-port", type=int, default=7000)
    airplay.add_argument(
        "--airplay-protocol",
        default="auto",
        choices=("auto", "raop", "airplay2", "airplay2-compat"),
    )
    airplay.add_argument("--airplay-device-id", help="stable MAC/device ID")
    airplay.add_argument("--airplay-target-name")
    airplay.add_argument("--airplay-credentials")
    airplay.add_argument("--airplay-legacy-secret")
    airplay.add_argument("--airplay-latency", type=int, default=600)
    airplay.add_argument("--cliairplay", default="cliairplay")
    airplay.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument(
        "--auth-provider",
        help="legitimate external provider as MODULE:ATTRIBUTE",
    )
    parser.add_argument(
        "--youtube",
        action="store_true",
        help="enable YouTube app 233637DE and its Lounge audio engine",
    )
    parser.add_argument(
        "--no-youtube-autoplay",
        action="store_true",
        help="wait for explicit Play instead of autoplaying a YouTube playlist",
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


def _local_ipv4() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return str(sock.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()
