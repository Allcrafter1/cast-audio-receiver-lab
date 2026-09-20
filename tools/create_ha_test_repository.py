#!/usr/bin/env python3
"""Create a clean local-build Home Assistant App repository for acceptance tests.

The generated repository contains source and build records, never private state
or an authentication bundle. It is intentionally separate from the eventual
public source export and lets Supervisor exercise its own image builder.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).parents[1]
APP = "cast-audio-receiver"
FILES = (
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "config/container-build-cp312.lock.txt",
    "config/container-linux-x86_64-cp312.lock.txt",
)


def create(target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"target is not empty: {target}")
    app = target / APP
    app.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "repository.yaml", target / "repository.yaml")
    shutil.copy2(ROOT / "Containerfile", app / "Dockerfile")
    shutil.copytree(
        ROOT / "src",
        app / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", "*.egg-info"),
    )
    for relative in FILES:
        destination = app / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copy2(ROOT / APP / "DOCS.md", app / "DOCS.md")

    # A missing image key tells Supervisor to build the adjacent Dockerfile.
    config = (ROOT / APP / "config.yaml").read_text().splitlines()
    config = [line for line in config if not line.startswith("image:")]
    (app / "config.yaml").write_text("\n".join(config) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    create(args.target.resolve())


if __name__ == "__main__":
    main()
