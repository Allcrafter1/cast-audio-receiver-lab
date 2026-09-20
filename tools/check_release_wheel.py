#!/usr/bin/env python3
"""Fail if a runtime wheel is incomplete or contains historical receiver code."""

import argparse
from pathlib import Path
import zipfile


REQUIRED = {
    "cast_audio_lab/runtime.py",
    "cast_audio_lab/output_registry.py",
    "cast_audio_lab/dlna.py",
    "cast_audio_lab/sonos.py",
    "cast_audio_lab/web/index.html",
}
HISTORICAL = {
    "auth.py",
    "lounge.py",
    "mdns.py",
    "protocol.py",
    "server.py",
    "tls.py",
    "wire.py",
    "youtube_dial.py",
    "youtube_receiver.py",
}


def validate(path: Path) -> dict[str, int]:
    if path.is_symlink() or path.suffix != ".whl":
        raise ValueError("expected a regular wheel file")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    missing = sorted(REQUIRED - names)
    leaked = sorted(name for name in names if name.rsplit("/", 1)[-1] in HISTORICAL)
    if missing:
        raise ValueError(f"runtime wheel is missing {missing[0]}")
    if leaked:
        raise ValueError(f"runtime wheel contains historical module {leaked[0]}")
    return {"files": len(names), "historical_modules": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    print(validate(args.wheel))
