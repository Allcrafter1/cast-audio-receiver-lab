# SPDX-License-Identifier: MPL-2.0
"""Session-scoped AirPlay receiver feedback and controls (DACP/DMCP)."""
from __future__ import annotations

import asyncio
import hmac
import ipaddress
import math
import secrets
import socket
from collections.abc import Awaitable, Callable

from aiohttp import web
from zeroconf import Error as ZeroconfError, IPVersion, ServiceInfo
from zeroconf.asyncio import AsyncZeroconf


def volume_feedback(query) -> tuple[float, bool] | None:
    """Accept the two receiver absolute-volume formats, without echoing them."""
    for key in ('dmcp.device-volume', 'dmcp.volume'):
        if key not in query:
            continue
        value = float(query[key])
        if not math.isfinite(value):
            raise ValueError('non-finite volume')
        if key == 'dmcp.device-volume':
            if value == -144:
                return 0.0, True
            if not -30 <= value <= 0:
                raise ValueError('invalid device volume')
            return (value + 30) / 30, False
        if not 0 <= value <= 100:
            raise ValueError('invalid volume')
        return value / 100, False
    return None


class DacpServer:
    def __init__(self, dacp_id: str, callback: Callable[[float, bool], Awaitable[None]],
                 control: Callable[[str], Awaitable[None]]):
        self.dacp_id = dacp_id
        self.active_remote = str(secrets.randbelow(2**32 - 1) + 1)
        self.callback = callback
        self.control = control
        self.peer = ''
        self.runner = None
        self.zeroconf = None
        self.service = None

    async def start(self, host: str, port: int) -> None:
        # Select the interface used for this receiver. UDP connect performs
        # routing only; it sends no packet and opens no receiver session.
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_DGRAM)
        family, _, _, _, remote = addresses[0]
        with socket.socket(family, socket.SOCK_DGRAM) as route:
            route.connect(remote)
            local = route.getsockname()[0]
        self.peer = str(ipaddress.ip_address(remote[0].split('%')[0]))
        app = web.Application(client_max_size=1024)
        app.router.add_get('/ctrl-int/1/{command}', self.handle, allow_head=False)
        self.runner = web.AppRunner(app, access_log=None, shutdown_timeout=1)
        try:
            await self.runner.setup()
            site = web.TCPSite(self.runner, local, 0)
            await site.start()
            bound_port = self.runner.addresses[0][1]
            self.zeroconf = AsyncZeroconf(
                interfaces=[local],
                ip_version=IPVersion.V4Only if family == socket.AF_INET else IPVersion.V6Only)
            self.service = ServiceInfo(
                '_dacp._tcp.local.',
                f'iTunes_Ctrl_{self.dacp_id}._dacp._tcp.local.',
                addresses=[ipaddress.ip_address(local.split('%')[0]).packed],
                port=bound_port,
                properties={'txtvers': '1', 'Ver': '131077', 'DbId': self.dacp_id},
                server=f'cast-dacp-{self.dacp_id.lower()}.local.')
            await self.zeroconf.async_register_service(self.service)
        except ZeroconfError as exc:
            await self.close()
            raise RuntimeError('DACP advertisement failed') from exc
        except BaseException:
            await self.close()
            raise

    async def handle(self, request: web.Request) -> web.Response:
        # Only the current receiver/session can change this output's state.
        if request.remote != self.peer or not hmac.compare_digest(
                request.headers.get('Active-Remote', '').encode('utf-8'), self.active_remote.encode('ascii')):
            raise web.HTTPForbidden()
        command = request.match_info['command']
        controls = {'play': 'play', 'pause': 'pause', 'playpause': 'toggle_play_pause',
                    'stop': 'stop', 'nextitem': 'next', 'previtem': 'previous',
                    'mutetoggle': 'mutetoggle', 'volumeup': 'volumeup', 'volumedown': 'volumedown'}
        if command in controls:
            await self.control(controls[command])
            return web.Response(status=204)
        if command != 'setproperty':
            raise web.HTTPNotFound()
        try:
            feedback = volume_feedback(request.query)
        except (TypeError, ValueError):
            raise web.HTTPBadRequest() from None
        if feedback is not None:
            await self.callback(*feedback)
        # Receivers also send busy/prevent-playback setproperty notifications.
        return web.Response(status=204)

    async def close(self) -> None:
        zc, self.zeroconf = self.zeroconf, None
        runner, self.runner = self.runner, None
        try:
            if zc is not None:
                try:
                    if self.service is not None:
                        await zc.async_unregister_service(self.service)
                finally:
                    await zc.async_close()
        finally:
            self.service = None
            if runner is not None:
                await runner.cleanup()
