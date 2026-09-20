#!/usr/bin/env python3
"""Create an allowlisted source tree with reviewed branding for publication review.

This is deliberately stricter than ``git archive`` because the development
checkout predates the release layout and also contains private runtime state,
device research artifacts and generated builds.  Producing an export is not a
license or secret-clearance decision; it creates the finite tree that reviewers
must inspect before any public push.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


ROOT = Path(__file__).parents[1]
ROOT_FILES = (
    ".dockerignore",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "Containerfile",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    "repository.yaml",
)
DIRECTORIES = (
    ".github",
    "cast-audio-receiver",
    "config",
    "docs",
    "licenses",
    "patches",
    "research",
    "src",
    "tests",
    "tools",
)
IGNORED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
FORBIDDEN_SUFFIXES = {
    ".apk",
    ".bundle",
    ".crt",
    ".der",
    ".gz",
    ".jks",
    ".key",
    ".log",
    ".p12",
    ".pcap",
    ".pem",
    ".tar",
    ".whl",
    ".zip",
}
FORBIDDEN_CONTENT = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b" + "usbip" + r"server\b"),
    re.compile(r"\b192\.168\.178\.\d{1,3}\b"),
    re.compile(r"\b10\.42\.0\.24\b"),
)
MAX_TEXT_FILE = 12 * 1024 * 1024
# Only these visually reviewed, reproducible project images bypass text checks.
# Updating an image requires reviewing the rendering and updating its digest.
BRANDING_SHA256 = {
    "cast-audio-receiver/icon.png": "0c22dc53aa7ef68567847f6baa973dfdc5fca25e9896e66ec38fa97e79efc2cb",
    "cast-audio-receiver/logo.png": "93f8cb766d6fa51a52999435582423bc8e1c4d388534dbdd8b8b91e753145ffd",
}


def _source_files() -> list[tuple[Path, Path]]:
    selected: list[tuple[Path, Path]] = []
    for relative in ROOT_FILES:
        source = ROOT / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"missing or unsafe release file: {relative}")
        selected.append((source, Path(relative)))
    for directory in DIRECTORIES:
        base = ROOT / directory
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"missing or unsafe release directory: {directory}")
        for source in sorted(base.rglob("*")):
            relative = source.relative_to(ROOT)
            if source.is_symlink():
                raise ValueError(f"release source contains symlink: {relative}")
            if not source.is_file():
                continue
            if IGNORED_PARTS.intersection(relative.parts):
                continue
            if source.suffix in IGNORED_SUFFIXES or any(
                part.endswith(".egg-info") for part in relative.parts
            ):
                continue
            selected.append((source, relative))
    return selected


def _validate_text(relative: Path, payload: bytes, *, allow_documentation_identifiers=False) -> str:
    if relative.as_posix() in BRANDING_SHA256:
        digest = hashlib.sha256(payload).hexdigest()
        if digest != BRANDING_SHA256[relative.as_posix()]:
            raise ValueError(f"unreviewed branding asset: {relative}")
        return digest
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ValueError(f"forbidden release artifact: {relative}")
    if len(payload) > MAX_TEXT_FILE:
        raise ValueError(f"oversized release source: {relative}")
    if b"\0" in payload:
        raise ValueError(f"binary release source: {relative}")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"non-UTF-8 release source: {relative}") from error
    for pattern in FORBIDDEN_CONTENT:
        if pattern.search(text):
            raise ValueError(f"private marker in release source: {relative}")
    if not allow_documentation_identifiers and relative.parts and relative.parts[0] == "docs":
        for address in re.findall(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", text):
            if address.upper() not in {
                "AA:BB:CC:DD:EE:FF", "02:00:00:00:00:01", "02:00:00:00:00:02"
            }:
                raise ValueError(f"non-placeholder device identifier in documentation: {relative}")
    return hashlib.sha256(payload).hexdigest()


def create(target: Path) -> dict[str, object]:
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"target is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    seen: set[Path] = set()
    for source, relative in _source_files():
        if relative in seen:
            raise ValueError(f"duplicate release path: {relative}")
        seen.add(relative)
        payload = source.read_bytes()
        digest = _validate_text(relative, payload)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        manifest.append(
            {"path": relative.as_posix(), "bytes": len(payload), "sha256": digest}
        )
    report: dict[str, object] = {
        "schema": 1,
        "files": sorted(manifest, key=lambda item: str(item["path"])),
    }
    (target / "SOURCE-MANIFEST.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    report = create(args.target.resolve())
    print(json.dumps({"files": len(report["files"]), "target": str(args.target)}))


if __name__ == "__main__":
    main()
