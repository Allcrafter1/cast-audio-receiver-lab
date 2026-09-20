"""Prepare the dedicated container state directories, then drop privileges."""

from __future__ import annotations

import os
from pathlib import Path
import json
import shutil
import sys

from .bundle_artifact import acquire


SERVICE_UID = 1000
SERVICE_GID = 1000
STATE_DIRECTORIES = ("frontend", "speakers", "private")
MAX_CERTIFICATE_BUNDLE_BYTES = 32 * 1024 * 1024
DEFAULT_MANIFEST = Path(__file__).parent / "data" / "bundle-release.json"
DEFAULT_MANIFEST_SHA256 = "2a8edc6897c5763c97c25762cf248f3926b6725550d9a736b358ffcf87a62d51"


def _chown_tree(path: Path, uid: int, gid: int) -> None:
    """Change ownership inside one dedicated state tree without following links."""

    os.chown(path, uid, gid, follow_symlinks=False)
    for directory, names, files in os.walk(path, followlinks=False):
        base = Path(directory)
        names[:] = [name for name in names if not (base / name).is_symlink()]
        for name in [*names, *files]:
            candidate = base / name
            if not candidate.is_symlink():
                os.chown(candidate, uid, gid, follow_symlinks=False)


def prepare_state(data_dir: Path, uid: int = SERVICE_UID, gid: int = SERVICE_GID) -> None:
    """Create and own only this application's known persistent directories."""

    data_dir.mkdir(parents=True, exist_ok=True)
    for name in STATE_DIRECTORIES:
        path = data_dir / name
        if path.is_symlink():
            raise ValueError(f"refusing symlink state directory: {path}")
        path.mkdir(mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
        _chown_tree(path, uid, gid)


def _configured_certificate_source(
    data_dir: Path, options_path: Path | None = None
) -> Path | None:
    explicit = os.environ.get("CAST_AUDIO_CERTS")
    if explicit:
        return Path(explicit)
    path = options_path or data_dir / "options.json"
    try:
        options = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid Home Assistant options file") from error
    source = options.get("certificate_path") if isinstance(options, dict) else None
    if source is None or source == "":
        return None
    if not isinstance(source, str) or not source.startswith("/"):
        raise ValueError("certificate_path must be an absolute path")
    return Path(source)


def import_certificate_bundle(
    data_dir: Path,
    *,
    uid: int = SERVICE_UID,
    gid: int = SERVICE_GID,
    options_path: Path | None = None,
) -> Path | None:
    """Atomically copy a root-readable input into private unprivileged state."""

    source = _configured_certificate_source(data_dir, options_path)
    if source is None:
        return None
    destination = data_dir / "private" / "certs.json"
    if source.resolve() == destination.resolve():
        if not source.is_file() or source.is_symlink():
            raise ValueError("certificate bundle must be a regular file")
        os.chmod(destination, 0o600)
        os.chown(destination, uid, gid, follow_symlinks=False)
        return destination
    if source.is_symlink() or not source.is_file():
        raise ValueError("certificate bundle must be a regular file")
    size = source.stat().st_size
    if not 0 < size <= MAX_CERTIFICATE_BUNDLE_BYTES:
        raise ValueError("certificate bundle size is invalid")
    temporary = destination.with_suffix(".json.importing")
    try:
        with source.open("rb") as reader, temporary.open("xb") as writer:
            os.chmod(temporary, 0o600)
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        os.chown(temporary, uid, gid, follow_symlinks=False)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def ensure_default_bundle(data_dir: Path, *, acquire_artifact=None) -> Path:
    """Acquire once only; existing state never depends on remote availability."""
    destination = data_dir / "private" / "certs.json"
    if destination.is_symlink() or any(p.is_symlink() for p in destination.parents):
        raise ValueError("certificate state must not use symlinks")
    if destination.exists():
        if not destination.is_file() or not 0 < destination.stat().st_size <= MAX_CERTIFICATE_BUNDLE_BYTES:
            raise ValueError("existing certificate state is invalid; supply a replacement explicitly")
        return destination
    fetch = acquire if acquire_artifact is None else acquire_artifact
    fetch(DEFAULT_MANIFEST, DEFAULT_MANIFEST_SHA256, destination)
    return destination


def main() -> None:
    data_dir = Path(os.environ.get("CAST_AUDIO_DATA_DIR", "/data"))
    if os.geteuid() == 0:
        try:
            prepare_state(data_dir)
            imported = import_certificate_bundle(data_dir)
            if imported is None:
                imported = ensure_default_bundle(data_dir)
                os.chmod(imported, 0o600)
                os.chown(imported, SERVICE_UID, SERVICE_GID, follow_symlinks=False)
            os.environ["CAST_AUDIO_CERTS"] = str(imported)
            os.setgroups([])
            os.setgid(SERVICE_GID)
            os.setuid(SERVICE_UID)
        except (OSError, ValueError) as error:
            raise SystemExit(f"container state setup failed: {error}") from error
    elif _configured_certificate_source(data_dir) is None:
        os.environ["CAST_AUDIO_CERTS"] = str(ensure_default_bundle(data_dir))
    os.execv(
        sys.executable,
        [sys.executable, "-m", "cast_audio_lab.container_entrypoint", *sys.argv[1:]],
    )


if __name__ == "__main__":
    main()
