#!/usr/bin/env python3
"""Transparent TCP proxy for reversible Cast discovery experiments.

The proxy does not terminate TLS or inspect Cast messages. It only gives an
existing receiver a distinct IP/port endpoint so sender-side discovery and
deduplication behavior can be tested independently.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib


async def copy_stream(
    source: asyncio.StreamReader, destination: asyncio.StreamWriter
) -> None:
    try:
        while chunk := await source.read(64 * 1024):
            destination.write(chunk)
            await destination.drain()
    finally:
        with contextlib.suppress(ConnectionError, OSError):
            destination.write_eof()


async def handle_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
) -> None:
    peer = client_writer.get_extra_info("peername")
    print(f"[cast-proxy] connection from {peer}", flush=True)
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            upstream_host, upstream_port
        )
    except OSError as error:
        print(f"[cast-proxy] upstream connection failed: {error}", flush=True)
        client_writer.close()
        await client_writer.wait_closed()
        return

    tasks = {
        asyncio.create_task(copy_stream(client_reader, upstream_writer)),
        asyncio.create_task(copy_stream(upstream_reader, client_writer)),
    }
    _done, pending = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    upstream_writer.close()
    client_writer.close()
    await asyncio.gather(
        upstream_writer.wait_closed(),
        client_writer.wait_closed(),
        return_exceptions=True,
    )
    print(f"[cast-proxy] disconnected {peer}", flush=True)


async def run(args: argparse.Namespace) -> None:
    server = await asyncio.start_server(
        lambda reader, writer: handle_connection(
            reader, writer, args.upstream_host, args.upstream_port
        ),
        args.listen_host,
        args.listen_port,
    )
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(
        f"[cast-proxy] listening on {addresses}; "
        f"forwarding to {args.upstream_host}:{args.upstream_port}",
        flush=True,
    )
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=8009)
    parser.add_argument("upstream_host")
    parser.add_argument("--upstream-port", type=int, default=8009)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
