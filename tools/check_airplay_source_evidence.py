#!/usr/bin/env python3
"""Verify historical native-source evidence without modifying a checkout.

This is not binary reproducibility or licence clearance. In particular, the
recursive checkout's OpenSSL source still needs an explicit release correction.
Only public commit IDs, hashes and booleans are returned; no runtime state read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


DEFAULT_RECORD = Path(__file__).resolve().parents[1] / "config/airplay-native-source-evidence.json"


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.DEVNULL, timeout=30
    ).decode().strip()


def verify(root, record):
    root = Path(root)
    proxy = root / record["openssl_proxy_path"]
    source = proxy / "openssl"
    introduction = record["binary_introduction_commit"]
    current = record["openssl_proxy_commit"]
    candidate = record["matching_version_source_commit"]
    archive = proxy / "targets/linux/x86_64/libcrypto.a"
    with archive.open("rb") as stream:
        archive_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    checks = {
        "airplay_revision": git(root, "rev-parse", "HEAD") == record["airplay_commit"],
        "proxy_revision": git(proxy, "rev-parse", "HEAD") == current,
        "original_gitlink": git(proxy, "rev-parse", current + ":openssl") == record["recorded_source_commit"],
        "introduction_gitlink": git(proxy, "rev-parse", introduction + ":openssl") == candidate,
        "unchanged_archive_tree_and_recipe": not git(proxy, "diff", "--name-only", introduction, current,
                                                       "--", "targets/linux/x86_64", "build.sh"),
        "archive_hash": archive_hash == record["libcrypto_sha256"],
    }
    version = dict(line.split("=", 1) for line in git(source, "show", candidate + ":VERSION.dat").splitlines()
                   if "=" in line)
    checks["source_version"] = ".".join(version.get(key, "") for key in ("MAJOR", "MINOR", "PATCH")) == record["openssl_version"]
    return {"checks": checks, "passed": all(checks.values()),
            "binary_reproducibility_verified": False,
            "source_override_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD)
    args = parser.parse_args()
    try:
        result = verify(args.checkout, json.loads(args.record.read_text()))
    except (OSError, ValueError, subprocess.SubprocessError):
        parser.exit(2, "Source evidence unavailable: check the complete pinned upstream checkout.\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
