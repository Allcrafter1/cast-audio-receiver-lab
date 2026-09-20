#!/usr/bin/env python3
"""Read-only Rust build-source hashes, without source content or private state.

Lists Git-visible workspace manifests and crate files, including new providers.
Not a reproducible-build guarantee: toolchain, environment and external inputs
must be pinned separately. Symlinks are rejected rather than followed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=15)


def inventory(root):
    root = Path(root)
    names = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0")
    files = {}
    for name in sorted(set(names)):
        if not name or not (name in {"Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "build.rs"}
                            or name.startswith(("crates/", ".cargo/"))):
            continue
        path = root / name
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root):
            raise ValueError("build-source symlink requires explicit review")
        if not path.is_file():
            files[name] = None  # tracked deletion is significant
            continue
        with path.open("rb") as source:
            files[name] = hashlib.file_digest(source, "sha256").hexdigest()
    return {"base_commit": git(root, "rev-parse", "HEAD").decode().strip(), "files": files}


def compare(left, right):
    a, b = left["files"], right["files"]
    return {"same_base": left["base_commit"] == right["base_commit"],
            "only_left": sorted(a.keys()-b.keys()), "only_right": sorted(b.keys()-a.keys()),
            "different": sorted(name for name in a.keys() & b.keys() if a[name] != b[name])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--compare", type=Path, help="previous JSON inventory; prints differences only")
    args = parser.parse_args()
    result = inventory(args.root)
    if args.compare:
        result = compare(result, json.loads(args.compare.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))
