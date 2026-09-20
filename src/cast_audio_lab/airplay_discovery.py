"""Discover and merge RAOP/AirPlay advertisements into physical targets."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from .airplay import AirPlayTarget


RAOP_SERVICE = "_raop._tcp.local."
AIRPLAY_SERVICE = "_airplay._tcp.local."
_MAC_RE = re.compile(r"^[0-9a-fA-F]{12}$")


@dataclass(frozen=True, slots=True)
class AirPlayService:
    service_type: str
    instance: str
    host: str
    address: str
    port: int
    properties: dict[str, str]

    @property
    def device_id(self) -> str:
        return service_device_id(self.service_type, self.instance, self.properties)

    @property
    def display_name(self) -> str:
        explicit = self.properties.get("name") or self.properties.get("fn")
        if explicit:
            return explicit
        label = self.instance.split(".", 1)[0]
        return label.split("@", 1)[-1]

    @property
    def bridge_generated(self) -> bool:
        model = self.properties.get("am", "").casefold()
        host = self.host.casefold()
        return model in {"aircast", "airupnp"} or host.endswith("-aircast")


@dataclass(slots=True)
class DiscoveredAirPlayDevice:
    device_id: str
    name: str
    raop: AirPlayService | None = None
    airplay: AirPlayService | None = None

    @property
    def bridge_generated(self) -> bool:
        return any(
            service is not None and service.bridge_generated
            for service in (self.raop, self.airplay)
        )

    def to_target(self) -> AirPlayTarget:
        service = self.airplay or self.raop
        if service is None:
            raise ValueError("discovered device contains no usable service")
        return AirPlayTarget(
            host=service.address,
            port=service.port,
            protocol="auto" if self.airplay else "raop",
            device_id=self.device_id,
            name=self.name,
            txt=service.properties,
        )


def service_device_id(
    service_type: str, instance: str, properties: dict[str, str]
) -> str:
    """Return a stable, normalized hardware identity where one is advertised."""

    lowered = {key.lower(): value for key, value in properties.items()}
    candidate = lowered.get("deviceid") or lowered.get("device_id")
    if not candidate and service_type == RAOP_SERVICE:
        prefix = instance.split("@", 1)[0].replace(":", "").replace("-", "")
        if _MAC_RE.fullmatch(prefix):
            candidate = prefix
    if candidate:
        compact = candidate.replace(":", "").replace("-", "").upper()
        if _MAC_RE.fullmatch(compact):
            return ":".join(compact[index : index + 2] for index in range(0, 12, 2))
        return candidate
    # Some third-party receivers omit deviceid. Keep them selectable without
    # pretending that their changing IP address is a hardware identity.
    return f"mdns:{instance.lower()}"


def merge_services(services: list[AirPlayService]) -> list[DiscoveredAirPlayDevice]:
    devices: dict[str, DiscoveredAirPlayDevice] = {}
    for service in services:
        device_id = service.device_id
        device = devices.setdefault(
            device_id,
            DiscoveredAirPlayDevice(device_id, service.display_name),
        )
        if service.service_type == AIRPLAY_SERVICE:
            device.airplay = service
            device.name = service.display_name
        elif service.service_type == RAOP_SERVICE:
            device.raop = service
            if not device.name:
                device.name = service.display_name
    return sorted(devices.values(), key=lambda item: item.name.casefold())


async def discover_airplay(
    timeout: float = 5.0, *, include_virtual: bool = False
) -> list[DiscoveredAirPlayDevice]:
    """Browse both service types for a bounded period."""

    try:
        from zeroconf import ServiceStateChange
        from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
    except ImportError as exc:
        raise RuntimeError("AirPlay discovery requires the 'airplay' extra") from exc

    aiozc = AsyncZeroconf()
    found: dict[tuple[str, str], AirPlayService] = {}
    pending: set[asyncio.Task[None]] = set()

    async def resolve(service_type: str, name: str) -> None:
        info = await aiozc.async_get_service_info(service_type, name, timeout=2000)
        if info is None:
            return
        addresses = info.parsed_addresses()
        if not addresses:
            return
        properties = {
            _decode(key): _decode(value)
            for key, value in info.properties.items()
        }
        found[(service_type, name)] = AirPlayService(
            service_type=service_type,
            instance=name,
            host=(info.server or "").rstrip("."),
            address=addresses[0],
            port=info.port,
            properties=properties,
        )

    def on_change(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: Any,
    ) -> None:
        del zeroconf
        if state_change in (ServiceStateChange.Added, ServiceStateChange.Updated):
            task = asyncio.create_task(resolve(service_type, name))
            pending.add(task)
            task.add_done_callback(pending.discard)
        elif state_change is ServiceStateChange.Removed:
            found.pop((service_type, name), None)

    browser = AsyncServiceBrowser(
        aiozc.zeroconf,
        [RAOP_SERVICE, AIRPLAY_SERVICE],
        handlers=[on_change],
    )
    try:
        await asyncio.sleep(max(0.1, timeout))
        if pending:
            await asyncio.gather(*tuple(pending), return_exceptions=True)
    finally:
        await browser.async_cancel()
        await aiozc.async_close()
    devices = merge_services(list(found.values()))
    if include_virtual:
        return devices
    return [device for device in devices if not device.bridge_generated]


def _decode(value: bytes | str) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover AirPlay output targets")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--include-virtual",
        action="store_true",
        help="include targets generated by known protocol bridges such as AirConnect",
    )
    args = parser.parse_args()
    devices = asyncio.run(
        discover_airplay(args.timeout, include_virtual=args.include_virtual)
    )
    output = []
    for device in devices:
        item = asdict(device)
        item["bridge_generated"] = device.bridge_generated
        output.append(item)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
