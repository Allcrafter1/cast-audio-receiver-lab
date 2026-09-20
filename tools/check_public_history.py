#!/usr/bin/env python3
"""Apply the bounded source-export checks to all reachable Git history.

No automatic secret scan establishes publication clearance. This catches known
private markers and forbidden artifacts in old commits, not just the live tree.
Run in a fresh clone so all intended public refs are present. Unreachable Git
objects, other repositories, release assets and LFS content are outside scope.
"""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from tools.create_public_source_export import MAX_TEXT_FILE, _validate_text
except ModuleNotFoundError:
    from create_public_source_export import MAX_TEXT_FILE, _validate_text


def run_git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)


def inspect(root):
    commits = run_git(root, "rev-list", "--all").decode().splitlines()
    entries = set()
    for commit in commits:
        for entry in run_git(root, "ls-tree", "-rz", commit).split(b"\0"):
            if not entry:
                continue
            metadata, name = entry.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            entries.add((mode, kind, oid, name.decode("utf-8")))
    issues = []
    checked = 0
    for mode, kind, oid, name in sorted(entries):
        if mode != "100644" and mode != "100755":
            issues.append({"path": name, "reason": "non-regular Git entry requires review"})
            continue
        size = int(run_git(root, "cat-file", "-s", oid))
        if size > MAX_TEXT_FILE:
            issues.append({"path": name, "reason": "oversized historical blob"})
            continue
        try:
            _validate_text(Path(name), run_git(root, "cat-file", "blob", oid))
        except ValueError:
            # Do not echo matched content, even in a private diagnostic.
            issues.append({"path": name, "reason": "source-export safety check failed"})
        checked += 1
    return {"commits": len(commits), "path_versions": len(entries),
            "checked_blobs": checked, "issues": issues,
            "passed": bool(commits) and not issues,
            "manual_review_still_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    result = inspect(args.repository)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
