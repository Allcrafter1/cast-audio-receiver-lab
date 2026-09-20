"""Bounded, opt-in SSDP MediaRenderer discovery using the existing UPnP stack."""
import asyncio
import ipaddress
from urllib.parse import urlsplit

from .output_registry import validate_output_target


def description_location(headers):
    """Only fetch a local IP advertised by that same responding device."""
    location = headers.get("location", "")
    try:
        parsed = urlsplit(location)
        address = ipaddress.ip_address(parsed.hostname or "")
        sender = ipaddress.ip_address(headers.get("_host", ""))
        if (parsed.scheme != "http" or parsed.username or parsed.password
                or address != sender or not (address.is_private or address.is_link_local)
                or address.is_loopback or address.is_multicast or address.is_unspecified):
            return None
        validate_output_target("dlna", {"description_url": location})
    except (ValueError, TypeError):
        return None
    return location


def parse_renderer(data, location):
    from defusedxml import ElementTree
    root = ElementTree.fromstring(data)
    ns = {"d": "urn:schemas-upnp-org:device-1-0"}
    for device in root.findall(".//d:device", ns):
        kind = device.findtext("d:deviceType", "", ns)
        if not kind.startswith("urn:schemas-upnp-org:device:MediaRenderer:"):
            continue
        name = device.findtext("d:friendlyName", "DLNA renderer", ns)
        ident = device.findtext("d:UDN", "", ns)
        target = validate_output_target("dlna", {
            "description_url": location, "device_id": ident or location,
        })
        return {"name": name[:80], "target": target}
    return None


async def discover_dlna(*, timeout=4):
    from aiohttp import ClientSession, ClientTimeout
    from async_upnp_client.search import SsdpSearchListener

    locations = set()
    def found(headers):
        if len(locations) < 32:
            location = description_location(headers)
            if location:
                locations.add(location)

    listener = SsdpSearchListener(callback=found, timeout=timeout,
        search_target="urn:schemas-upnp-org:device:MediaRenderer:1")
    try:
        await listener.async_start()
        listener.async_search()
        await asyncio.sleep(timeout)
    finally:
        listener.async_stop()
    semaphore = asyncio.Semaphore(4)
    async with ClientSession(timeout=ClientTimeout(total=3)) as session:
        async def describe(location):
            async with semaphore:
                try:
                    async with session.get(location, allow_redirects=False) as response:
                        if response.status != 200:
                            return None
                        data = bytearray()
                        async for chunk in response.content.iter_chunked(16384):
                            data.extend(chunk)
                            if len(data) > 256 * 1024:
                                return None
                    return parse_renderer(bytes(data), location)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # One unavailable/malformed advertisement must not hide others.
                    return None
        results = await asyncio.gather(*(describe(url) for url in sorted(locations)))
    unique = {}
    for result in results:
        if result:
            unique.setdefault(result["target"]["device_id"], result)
    return sorted(unique.values(), key=lambda item: item["name"].casefold())
