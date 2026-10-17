# SPDX-License-Identifier: MPL-2.0
"""Wire-level discovery/HTTP checks; optional pinned native RTSP sender probe."""
import asyncio
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from aiohttp import ClientSession, ClientTimeout
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from cast_audio_lab.airplay import AirPlayTarget, cliairplay_argv, dacp_identity
from cast_audio_lab.dacp import DacpServer


class DacpWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_discovery_then_receiver_http_commands(self):
        # A receiver resolves the numeric 64-bit DACP identity advertised by
        # RTSP, then uses SRV/TXT/A records to reach the HTTP return channel.
        target = AirPlayTarget('127.0.0.1', protocol='raop', device_id=secrets.token_hex(6))
        volume, control = AsyncMock(), AsyncMock()
        server = DacpServer(dacp_identity(target), volume, control)
        self.addAsyncCleanup(server.close)
        await asyncio.wait_for(server.start('127.0.0.1', 5000), 5)
        client = AsyncZeroconf(interfaces=['127.0.0.1'], ip_version=IPVersion.V4Only)
        self.addAsyncCleanup(client.async_close)
        name = f'iTunes_Ctrl_{int(dacp_identity(target), 16):016X}._dacp._tcp.local.'
        info = AsyncServiceInfo('_dacp._tcp.local.', name)
        self.assertTrue(await info.async_request(client.zeroconf, 3000))
        self.assertEqual(info.parsed_addresses(), ['127.0.0.1'])
        self.assertEqual(info.properties[b'OSsi'], b'0x1F5')
        async with ClientSession(timeout=ClientTimeout(total=3)) as http:
            for command in ('setproperty?dmcp.device-volume=-15', 'nextitem', 'pause'):
                async with http.get(f'http://{info.parsed_addresses()[0]}:{info.port}/ctrl-int/1/{command}',
                                    headers={'Active-Remote': server.active_remote}) as response:
                    self.assertEqual(response.status, 204)
        volume.assert_awaited_once_with(.5, False)
        self.assertEqual([c.args[0] for c in control.await_args_list], ['next', 'pause'])

    @unittest.skipUnless(os.environ.get('CLIAIRPLAY_TEST_BINARY'), 'optional pinned native sender probe')
    async def test_native_rtsp_headers_match_discovery_identity_and_session(self):
        captured = asyncio.get_running_loop().create_future()
        async def receive(reader, writer):
            try:
                while True:
                    raw = await reader.readuntil(b'\r\n\r\n')
                    lines = raw.decode().split('\r\n')
                    headers = dict(line.split(': ', 1) for line in lines[1:] if ': ' in line)
                    await reader.readexactly(int(headers.get('Content-Length', '0')))
                    if not captured.done() and 'DACP-ID' in headers:
                        captured.set_result(headers)
                    writer.write(('RTSP/1.0 200 OK\r\nCSeq: ' + headers['CSeq'] +
                                  '\r\nContent-Length: 0\r\n\r\n').encode())
                    await writer.drain()
            except (asyncio.IncompleteReadError, ConnectionError):
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        listener = await asyncio.start_server(receive, '127.0.0.1', 0)
        async with listener:
            target = AirPlayTarget('127.0.0.1', port=listener.sockets[0].getsockname()[1],
                                   protocol='raop', device_id='AA:BB:CC:DD:EE:FF', txt={'et': '0'})
            server = DacpServer(dacp_identity(target), AsyncMock(), AsyncMock())
            with tempfile.TemporaryDirectory() as directory:
                pipe = Path(directory) / 'commands'
                os.mkfifo(pipe)
                argv = cliairplay_argv(os.environ['CLIAIRPLAY_TEST_BINARY'], target, pipe,
                                      volume=.5, latency_ms=2000, active_remote=server.active_remote)
                process = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE,
                              stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                try:
                    headers = await asyncio.wait_for(captured, 5)
                    self.assertEqual(headers['DACP-ID'], server.dacp_id)
                    self.assertEqual(headers['DACP-ID'], '0000AABBCCDDEEFF')
                    self.assertEqual(headers['Active-Remote'], server.active_remote)
                finally:
                    if process.returncode is None:
                        process.terminate()
                    try:
                        await asyncio.wait_for(process.communicate(), 3)
                    except TimeoutError:
                        process.kill()
                        await process.communicate()
