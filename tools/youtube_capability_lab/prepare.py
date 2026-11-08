#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Create an isolated lab-only source tree; never edits the supplied baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def replace_once(directory, relative, old, new, changes):
    path = directory / relative
    source = path.read_text()
    if source.count(old) != 1:
        raise SystemExit(f"unexpected-baseline:{relative}")
    path.write_text(source.replace(old, new))
    changes.append(relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path,
                        default=Path("/tmp/cast-hybrid-harness-20261108/frontend-source"))
    args = parser.parse_args()
    source, destination = args.source.resolve(), args.destination.resolve()
    if not str(destination).startswith("/tmp/") or destination.exists():
        raise SystemExit("destination-must-be-new-and-under-tmp")
    if source == destination or source in destination.parents:
        raise SystemExit("destination-must-not-be-inside-source")
    shutil.copytree(source, destination)
    changes = []
    replace_once(destination, "crates/vibecast-discovery/src/mdns.rs",
                 'ca: "199428".into(),',
                 'ca: std::env::var("CAST_LAB_MDNS_CA").unwrap_or_else(|_| "199428".into()),',
                 changes)
    replace_once(destination, "crates/vibecast-discovery/src/mdns.rs",
                 'ic: "/setup/icon.png".into(),',
                 'ic: std::env::var("CAST_LAB_MDNS_ICON").unwrap_or_else(|_| "/setup/icon.png".into()),',
                 changes)
    replace_once(destination, "crates/vibecast-messages/src/discovery.rs",
                 'device_capabilities: 199428,',
                 'device_capabilities: std::env::var("CAST_LAB_DEVICE_CAPABILITIES")\n'
                 '                .map(|value| value.parse().expect("invalid lab device capabilities"))\n'
                 '                .unwrap_or(199428),', changes)
    replace_once(destination, "crates/vibecast-messages/src/discovery.rs",
                 'device_icon_url: String::new(),',
                 'device_icon_url: std::env::var("CAST_LAB_DEVICE_ICON_URL").unwrap_or_default(),',
                 changes)
    manifest = {"baseline_source": str(source), "lab_only": True,
                "unchanged_defaults": True, "changed_files": []}
    for relative in sorted(set(changes)):
        manifest["changed_files"].append({"path": relative,
            "baseline_sha256": hashlib.sha256((source / relative).read_bytes()).hexdigest(),
            "lab_sha256": hashlib.sha256((destination / relative).read_bytes()).hexdigest()})
    (destination / "PATCH-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"source": str(destination), "changed_file_count": len(set(changes))}))


if __name__ == "__main__":
    main()
