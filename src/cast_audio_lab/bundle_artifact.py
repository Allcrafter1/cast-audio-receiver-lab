"""Explicit, hash-pinned artifact acquisition; no embedded distribution URL.

The caller must obtain the manifest digest through a trusted release channel.
This checks artifact integrity, not device identity validity or redistribution
rights. The frontend remains responsible for validating the bundle contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

MAX_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024


def _https(url: str) -> None:
    if not isinstance(url, str):
        raise ValueError("artifact URL must be a string")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("artifact transport must use HTTPS without credentials")


class _HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _https(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_manifest(path: Path, expected_sha256: str) -> dict:
    with path.open("rb") as source:
        raw = source.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("manifest size or trusted digest mismatch")
    try:
        manifest = json.loads(raw)
        if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
                or manifest["schema_version"] != 1):
            raise ValueError()
        if manifest.get("withdrawn", False):
            raise ValueError("artifact version has been withdrawn")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", manifest["version"]):
            raise ValueError()
        if not re.fullmatch(r"[a-f0-9]{64}", manifest["sha256"]):
            raise ValueError()
        if type(manifest["size"]) is not int or not 0 < manifest["size"] <= MAX_BYTES:
            raise ValueError()
        _https(manifest["url"])
        if urlsplit(manifest["url"]).query or urlsplit(manifest["url"]).fragment:
            raise ValueError("manifest requires a stable, unsigned artifact URL")
    except (KeyError, TypeError, ValueError, RecursionError):
        raise ValueError("invalid or withdrawn artifact manifest") from None
    return manifest


def acquire(manifest_path: Path, manifest_sha256: str, destination: Path, *, opener=None) -> str:
    """Verify before replacing; failures retain the current local artifact.

    Run explicitly during installation/update, never on each receiver startup.
    A withdrawn remote release does not disable an already installed artifact.
    """
    manifest = read_manifest(manifest_path, manifest_sha256)
    parent = destination.parent
    if destination.is_symlink() or any(p.is_symlink() for p in (parent, *parent.parents)):
        raise ValueError("artifact destination must not use symlinks")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fetch = opener or build_opener(_HTTPSRedirects()).open
    fd, temporary_name = tempfile.mkstemp(prefix=".artifact-", dir=parent)
    temporary = Path(temporary_name)
    try:
        digest = hashlib.sha256()
        count = 0
        deadline = time.monotonic() + 60
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            try:
                with fetch(manifest["url"], timeout=30) as response:
                    _https(response.geturl())
                    while chunk := response.read(64 * 1024):
                        if time.monotonic() > deadline:
                            raise ValueError("artifact download exceeded time budget")
                        count += len(chunk)
                        if count > manifest["size"]:
                            raise ValueError("artifact exceeds pinned size")
                        digest.update(chunk)
                        output.write(chunk)
            except (OSError, ValueError):
                # Exceptions from HTTP clients can contain signed URLs. Do not
                # expose them through logs, diagnostics or CLI tracebacks.
                raise ValueError("artifact unavailable or download rejected; local copy unchanged") from None
            output.flush()
            os.fsync(output.fileno())
        if count != manifest["size"] or digest.hexdigest() != manifest["sha256"]:
            raise ValueError("artifact size or digest mismatch; local copy unchanged")
        # The downloaded format is JSON. Do not print its contents on failure.
        try:
            value = json.loads(temporary.read_bytes())
            if not isinstance(value, (dict, list)) or not value:
                raise ValueError()
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError("artifact is not a nonempty JSON bundle") from None
        os.replace(temporary, destination)
        directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return manifest["version"]
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--manifest-sha256", required=True, help="trusted release-pinned manifest digest")
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        version = acquire(args.manifest, args.manifest_sha256, args.destination)
    except (OSError, ValueError):
        raise SystemExit("Bundle import failed; check manifest pin, availability and destination permissions.") from None
    print(f"Artifact {version} imported; frontend validation is still required.")


if __name__ == "__main__":
    main()
