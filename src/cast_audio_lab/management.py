"""Direct local-network speaker administration."""
import argparse
import asyncio
import contextlib
import ipaddress
import json
from pathlib import Path
import signal
import time
import uuid
import tempfile
from urllib.parse import urlsplit

from aiohttp import web

from . import __version__
from .artwork_cache import ArtworkCache
from .airplay_discovery import discover_airplay
from .dlna_discovery import discover_dlna
from .route_manager import RouteManager
from .routes import Route, RouteStore, validate_routes
from .output_registry import is_singleton

ASSETS = Path(__file__).with_name("web")


async def serve(app, host: str, ports: list[int]) -> None:
    """Serve one application on the LAN and optional HA ingress listeners."""

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    try:
        for port in dict.fromkeys(ports):
            await web.TCPSite(runner, host, port).start()
        await stop.wait()
    finally:
        await runner.cleanup()


def create_app(manager, *, discover=discover_airplay, discover_renderers=discover_dlna, ha_ingress=False):
    candidates = {}
    scan_lock = asyncio.Lock()
    artwork_temp = tempfile.TemporaryDirectory(prefix='cast-artwork-')
    artwork_cache = ArtworkCache(Path(artwork_temp.name))

    @web.middleware
    async def security(request, handler):
        try:
            origin = request.headers.get("Origin")
            public_image = request.method in {'GET', 'HEAD'} and request.path.startswith('/artwork/')
            ingress_request = ha_ingress and bool(request.headers.get("X-Ingress-Path"))
            if (not public_image and not ingress_request and origin is not None
                    and origin != "http://" + request.host):
                raise web.HTTPForbidden(text="cross-origin request rejected")
            if (not public_image and not ingress_request
                    and request.headers.get("Sec-Fetch-Site") == "cross-site"):
                raise web.HTTPForbidden(text="cross-site request rejected")
            if request.path.startswith("/api/"):
                if request.method in {"POST", "PATCH", "DELETE"} and request.content_type != "application/json":
                    raise web.HTTPUnsupportedMediaType(text="JSON required")
            response = await handler(request)
        except web.HTTPException as exc:
            response = web.json_response({"error": exc.text}, status=exc.status)
        except (ValueError, TypeError, KeyError):
            response = web.json_response({"error": "Invalid configuration or request"}, status=400)
        except (OSError, RuntimeError):
            response = web.json_response({"error": "Operation failed; private diagnostics require local access"}, status=503)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "SAMEORIGIN" if ha_ingress else "DENY",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'" if ha_ingress else "default-src 'none'; img-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        return response

    app = web.Application(middlewares=[security], client_max_size=32768)

    async def prepare_artwork(request):
        # Only our local adapters submit sources; browsers can read opaque
        # finished image IDs but cannot turn this endpoint into a URL proxy.
        if not request.remote or not ipaddress.ip_address(request.remote).is_loopback:
            raise web.HTTPForbidden(text='local adapter required')
        body = await request.json()
        if not isinstance(body, dict) or set(body) != {'source'} or not isinstance(body['source'], str):
            raise ValueError('invalid artwork request')
        ident = await artwork_cache.prepare(body['source'])
        if ident is None:
            raise web.HTTPServiceUnavailable(text='Artwork unavailable')
        return web.json_response({'path': f'/artwork/{ident}.jpg'})

    async def image(request):
        path = artwork_cache.get(request.match_info['id'])
        if path is None:
            raise web.HTTPNotFound()
        return web.Response(body=path.read_bytes(), content_type='image/jpeg',
                            headers={'Access-Control-Allow-Origin': '*'})

    async def asset(request):
        name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/favicon.svg": "favicon.svg"}[request.path]
        return web.Response(body=(ASSETS/name).read_bytes(), content_type={"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css", "favicon.svg": "image/svg+xml"}[name])

    async def listing(request):
        async with manager.lock:
            return web.json_response({"version": __version__, "routes": manager.public(), "max_routes": 32})

    async def health(request):
        result = await manager.health()
        return web.json_response(result, status=200 if result["ready"] else 503)

    async def status(request):
        return web.json_response({"version": __version__, **manager.status()})

    async def support(request):
        return web.json_response(manager.support_snapshot(version=__version__))

    async def patch_route(request):
        body = await request.json()
        if not isinstance(body, dict) or set(body) - {"name", "enabled", "target"} or not body:
            raise ValueError("invalid route update")
        async with manager.lock:
            route = next((r for r in manager.routes if r.id == request.match_info["id"]), None)
            if route is None:
                raise web.HTTPNotFound()
            if "target" in body and route.backend != "dlna":
                raise ValueError("target editing is currently supported only for DLNA")
            changed = Route.parse(dict(route.private(), **body))
            routes = validate_routes([
                (changed if r.id == route.id else r).private() for r in manager.routes
            ])
            await manager.replace(routes)
            return web.json_response(changed.public())

    async def add_route(request):
        body = await request.json()
        if not isinstance(body, dict) or set(body) - {"name", "candidate_id", "backend", "target"}:
            raise ValueError("invalid route creation")
        route = {"id": str(uuid.uuid4()), "name": body.get("name"), "enabled": False}
        if "candidate_id" in body:
            if "backend" in body:
                raise ValueError("choose one target")
            candidate = candidates.get(body["candidate_id"])
            if candidate is None or candidate[0] < time.monotonic():
                raise web.HTTPConflict(text="Discovery expired; scan again")
            route.update(backend=candidate[1], target=candidate[2])
        else:
            backend = body.get("backend")
            if backend == "mpv":
                if "target" in body:
                    raise ValueError("local output has no target")
                route["backend"] = "mpv"
            elif backend in {"dlna", "sonos"}:
                route.update(backend=backend, target=body.get("target"))
            else:
                raise ValueError("select a discovered target")
        async with manager.lock:
            if is_singleton(route["backend"]) and any(
                r.backend == route["backend"] for r in manager.routes
            ):
                raise web.HTTPConflict(
                    text="Diese lokale Ausgabe existiert bereits. Bitte die vorhandene Ausgabe verwenden."
                )
            routes = validate_routes([r.private() for r in manager.routes]+[route])
            await manager.replace(routes)
            return web.json_response(routes[-1].public(), status=201)

    async def delete_route(request):
        async with manager.lock:
            route = next((r for r in manager.routes if r.id == request.match_info["id"]), None)
            if route is None:
                raise web.HTTPNotFound()
            await manager.replace([r for r in manager.routes if r.id != route.id])
            (manager.store.directory / f"target-{route.id}.json").unlink(missing_ok=True)
            return web.json_response({"deleted": route.id})

    async def scan(request):
        if await request.json() != {}:
            raise ValueError("scan body must be empty")
        if scan_lock.locked():
            raise web.HTTPConflict(text="Scan already running")
        async with scan_lock:
            try:
                async with asyncio.timeout(12):
                    devices = await discover(timeout=4, include_virtual=False)
            except TimeoutError:
                raise web.HTTPGatewayTimeout(text="Discovery timed out") from None
            candidates.clear()
            result = []
            async with manager.lock:
                own = {route.id.replace("-", "").lower() for route in manager.routes}
                for device in devices[:64]:
                    if device.bridge_generated or device.device_id.replace("-", "").replace(":", "").lower() in own:
                        continue
                    for service, protocol in ((device.raop, "raop"), (device.airplay, "auto")):
                        if service is None:
                            continue
                        try:
                            route = Route.parse({"id": str(uuid.uuid4()), "name": device.name,
                                "backend": "airplay", "target": {"host": service.address, "port": service.port,
                                "protocol": protocol, "device_id": device.device_id, "txt": service.properties}})
                        except ValueError:
                            continue
                        try:
                            validate_routes([r.private() for r in manager.routes]+[route.private()])
                            imported = False
                        except ValueError:
                            imported = True
                        ident = str(uuid.uuid4())
                        if not imported:
                            candidates[ident] = (time.monotonic()+180, "airplay", route.target)
                        result.append(dict(route.public(), candidate_id=ident, already_imported=imported))
            return web.json_response({"candidates": result})

    async def scan_dlna(request):
        if await request.json() != {}:
            raise ValueError("scan body must be empty")
        if scan_lock.locked():
            raise web.HTTPConflict(text="Scan already running")
        async with scan_lock:
            try:
                async with asyncio.timeout(15):
                    devices = await discover_renderers(timeout=4)
            except TimeoutError:
                raise web.HTTPGatewayTimeout(text="DLNA discovery timed out") from None
            except ImportError:
                raise web.HTTPServiceUnavailable(text="DLNA dependency unavailable") from None
            candidates.clear()
            result = []
            async with manager.lock:
                for device in devices[:32]:
                    try:
                        route = Route.parse({"id": str(uuid.uuid4()), "name": device["name"],
                            "backend": "dlna", "target": device["target"]})
                    except (ValueError, KeyError, TypeError):
                        continue
                    try:
                        validate_routes([r.private() for r in manager.routes] + [route.private()])
                        imported = False
                    except ValueError:
                        imported = True
                    ident = str(uuid.uuid4())
                    if not imported:
                        candidates[ident] = (time.monotonic()+180, "dlna", route.target)
                    result.append(dict(route.public(), candidate_id=ident, already_imported=imported))
            return web.json_response({"candidates": result})

    async def lifecycle(app):
        try:
            await manager.start()
            yield
        finally:
            try:
                await manager.close()
            finally:
                await artwork_cache.close()
                artwork_temp.cleanup()

    app.cleanup_ctx.append(lifecycle)
    for path in ("/", "/app.js", "/style.css", "/favicon.svg"):
        app.router.add_get(path, asset)
    app.router.add_get("/health", health)
    app.router.add_get("/status", status)
    app.router.add_get("/api/support", support)
    app.router.add_get("/api/routes", listing)
    app.router.add_post("/api/routes", add_route)
    app.router.add_patch("/api/routes/{id}", patch_route)
    app.router.add_delete("/api/routes/{id}", delete_route)
    app.router.add_post("/api/scan", scan)
    app.router.add_post("/api/scan/dlna", scan_dlna)
    app.router.add_post('/api/artwork', prepare_artwork)
    app.router.add_get('/artwork/{id:[0-9a-f]{32}}.jpg', image)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--bridge", default="ws://127.0.0.1:8010/player")
    parser.add_argument("--cliairplay", default="cliairplay")
    parser.add_argument('--artwork-public-url', help='LAN URL of this manager, e.g. http://192.168.1.5:8788; requires artwork-capable frontend')
    parser.add_argument('--ha-ingress', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--ingress-port', type=int, help=argparse.SUPPRESS)
    parser.add_argument("--import-target", type=Path, help="offline import of existing private AirPlay config; exits")
    parser.add_argument("--import-local", action="store_true", help="offline import of existing local output; exits")
    parser.add_argument("--player-id", help="preserve an existing player UUID on offline import")
    parser.add_argument("--name", help="speaker name for offline import")
    args = parser.parse_args()
    try:
        bind_address = ipaddress.ip_address(args.host)
        if (not (bind_address.is_loopback or bind_address.is_private) or
                not 1 <= args.port <= 65535):
            raise ValueError("management binds only loopback or private LAN addresses")
        if args.ingress_port is not None and not 1 <= args.ingress_port <= 65535:
            raise ValueError("invalid ingress port")
        if args.ingress_port is not None and not args.ha_ingress:
            raise ValueError("ingress port requires Home Assistant ingress mode")
        store = RouteStore(args.state_dir)
        if args.import_target or args.import_local:
            if args.import_target and args.import_local:
                raise ValueError("choose one import type")
            store.acquire()
            try:
                value = {"id": args.player_id or str(uuid.uuid4()), "name": args.name,
                         "backend": "airplay" if args.import_target else "mpv", "enabled": False}
                if args.import_target:
                    value["target"] = json.loads(args.import_target.read_text())
                existing = store.load()
                if args.import_local and any(r.backend == "mpv" for r in existing):
                    raise ValueError("local output already configured")
                routes = validate_routes([r.private() for r in existing]+[value])
                store.save(routes)
                print("Imported disabled speaker", routes[-1].id)
            finally:
                store.release()
            return
        if args.player_id or args.name:
            raise ValueError("name/player-id only apply to offline import")
        manager = RouteManager(store, bridge=args.bridge, cliairplay=args.cliairplay)
        if args.artwork_public_url:
            if not (bind_address.is_unspecified or bind_address.is_loopback):
                raise ValueError('artwork processing requires wildcard or loopback binding')
            parsed = urlsplit(args.artwork_public_url)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
                raise ValueError('artwork public URL must be an HTTP(S) origin')
            loopback = '[::1]' if bind_address.version == 6 else '127.0.0.1'
            internal_host = loopback if bind_address.is_unspecified else f'[{args.host}]' if bind_address.version == 6 else args.host
            manager.artwork_endpoint = f'http://{internal_host}:{args.port}/api/artwork'
            manager.artwork_public_url = args.artwork_public_url.rstrip('/')
        app = create_app(manager, ha_ingress=args.ha_ingress)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    try:
        asyncio.run(
            serve(
                app,
                args.host,
                [args.port, *([args.ingress_port] if args.ingress_port else [])],
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
