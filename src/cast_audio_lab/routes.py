"""Validated private route configuration; identity is independent of names."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
import uuid

from .output_registry import output_definition, validate_output_target

MAX_ROUTES = 32


def text(value, label, maximum=128):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError(f"invalid {label}")
    return value.strip()


@dataclass(frozen=True)
class Route:
    id: str
    name: str
    backend: str
    enabled: bool = False
    target: dict | None = None

    @classmethod
    def parse(cls, data):
        if not isinstance(data, dict) or set(data) - {"id", "name", "backend", "enabled", "target"}:
            raise ValueError("unknown route field")
        try:
            ident = str(uuid.UUID(data["id"]))
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ValueError("invalid route identity") from None
        backend = data.get("backend")
        output_definition(backend)
        if type(data.get("enabled", False)) is not bool:
            raise ValueError("invalid enabled flag")
        target = validate_output_target(backend, data.get("target"))
        return cls(ident, text(data.get("name"), "speaker name", 80), backend, data.get("enabled", False), target)

    def private(self):
        return dict(id=self.id, name=self.name, backend=self.backend, enabled=self.enabled, target=self.target)

    def public(self):
        result = self.private()
        result["target"] = ({k: self.target[k] for k in ("host", "port", "protocol", "device_id")}
                            if self.target else None)
        return result


def validate_routes(values):
    if not isinstance(values, list) or len(values) > MAX_ROUTES:
        raise ValueError("invalid route count")
    routes = [Route.parse(value) for value in values]
    ids, devices, endpoints = set(), set(), set()
    for route in routes:
        if route.id in ids:
            raise ValueError("duplicate route identity")
        ids.add(route.id)
        if route.target:
            device = route.target["device_id"].lower().replace(":", "").replace("-", "")
            endpoint = (route.target["host"].lower(), route.target["port"])
            if device in devices or endpoint in endpoints:
                raise ValueError("target already imported")
            devices.add(device)
            endpoints.add(endpoint)
    return routes


def atomic_json(path: Path, value):
    """Atomic visibility; failed writes before replace leave prior config intact."""
    fd, temporary = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(value, output, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class RouteStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.stat().st_mode & 0o077:
            raise ValueError("manager state directory must have permissions 0700")
        self.path = self.directory / "routes.json"
        self._lock = None

    def acquire(self):
        if self._lock is not None:
            raise ValueError("state lock already acquired")
        import fcntl
        lock = self.directory / "manager.lock"
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise ValueError("another manager owns this state directory") from None
        self._lock = fd

    def release(self):
        if self._lock is not None:
            os.close(self._lock)
            self._lock = None

    def load(self):
        if self.path.is_symlink():
            raise ValueError("route config cannot be a symlink")
        try:
            if self.path.stat().st_size > 1024 * 1024:
                raise ValueError("route config is too large")
            value = json.loads(self.path.read_text())
        except FileNotFoundError:
            return []
        if not isinstance(value, dict) or set(value) != {"version", "routes"} or type(value["version"]) is not int or value["version"] != 1:
            raise ValueError("unsupported route config version")
        return validate_routes(value["routes"])

    def save(self, routes):
        validated = validate_routes([route.private() for route in routes])
        atomic_json(self.path, {"version": 1, "routes": [route.private() for route in validated]})
