#!/usr/bin/env python3
"""Inventory explicitly downloaded wheels and emit exact artifact requirements.

Does not download, import, execute or install their contents. Hashes establish
artifact identity, not safety. Use one platform/interpreter's wheelhouse at a time.
"""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import zipfile


def inventory(directory):
    result, seen = [], set()
    for path in sorted(Path(directory).glob("*.whl")):
        if path.is_symlink():
            raise ValueError("wheel symlink requires explicit review")
        with zipfile.ZipFile(path) as archive:
            # Some build tools vendor complete distributions (including nested
            # dist-info directories). Only the wheel's root metadata identifies
            # the artifact being inventoried.
            metadata = [
                entry
                for entry in archive.infolist()
                if entry.filename.endswith(".dist-info/METADATA")
                and entry.filename.count("/") == 1
            ]
            if len(metadata) != 1 or metadata[0].file_size > 1024*1024:
                raise ValueError("invalid or oversized wheel metadata")
            data = BytesParser().parsebytes(archive.read(metadata[0]))
        name, version = data.get("Name", ""), data.get("Version", "")
        if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version)):
            raise ValueError("invalid requirement metadata")
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in seen:
            raise ValueError("multiple wheels for one distribution; select one target environment")
        seen.add(normalized)
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        result.append(dict(name=name, version=version, filename=path.name, sha256=digest,
                           license=data.get("License-Expression") or data.get("License")))
    if not result:
        raise ValueError("no wheels")
    return sorted(result, key=lambda item: item["name"].lower())


def requirements(items):
    return "\n".join(f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}" for item in items)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--requirements", action="store_true")
    args = parser.parse_args()
    values = inventory(args.directory)
    print(requirements(values) if args.requirements else json.dumps(values, indent=2))
