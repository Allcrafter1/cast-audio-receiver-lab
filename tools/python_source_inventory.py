#!/usr/bin/env python3
"""Collect exact PyPI source references for a reviewed wheel inventory.

Reads public metadata only: never installs/imports packages or executes their
build hooks. Source distributions are references, not proof that bundled native
libraries are fully covered. Missing source archives stay explicit in the report.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile
from urllib.parse import quote, urlsplit
from urllib.request import urlopen


def get_metadata(name, version):
    url = "https://pypi.org/pypi/" + quote(name, safe="") + "/" + quote(version, safe="") + "/json"
    with urlopen(url, timeout=30) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("oversized package metadata")
    return json.loads(raw)


def inventory(wheels, fetch=get_metadata):
    result = []
    for wheel in wheels:
        metadata = fetch(wheel["name"], wheel["version"])
        files = metadata.get("urls", [])
        matched = [item for item in files if item.get("filename") == wheel["filename"]
                   and item.get("digests", {}).get("sha256") == wheel["sha256"]]
        if len(matched) != 1:
            raise ValueError("pinned wheel does not match upstream metadata: " + wheel["name"])
        sources = []
        for item in files:
            if item.get("packagetype") != "sdist":
                continue
            url = urlsplit(item.get("url", ""))
            digest = item.get("digests", {}).get("sha256", "")
            filename = item.get("filename", "")
            if (url.scheme != "https" or url.netloc != "files.pythonhosted.org"
                    or url.query or url.fragment or not re.fullmatch(r"[a-f0-9]{64}", digest)
                    or not filename or Path(filename).name != filename
                    or type(item.get("size")) is not int or item["size"] <= 0):
                raise ValueError("invalid upstream source reference")
            sources.append({"filename": filename, "url": item["url"], "sha256": digest,
                            "size": item["size"]})
        result.append({"name": wheel["name"], "version": wheel["version"],
                       "wheel_sha256": wheel["sha256"], "wheel_verified_against_pypi": True,
                       "sources": sources, "status": "sdist-referenced" if sources else "no-sdist-review-required"})
    return {"schema": 1, "packages": result, "source_archives_downloaded": False,
            "embedded_native_source_coverage_verified": False}


def source_archive(report, destination, fetch=urlopen):
    """Fetch pinned sdists without executing their package/build code."""
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    sources = [source for package in report["packages"] for source in package["sources"]]
    if any(not package["sources"] for package in report["packages"]):
        raise ValueError("missing source distributions require review")
    if sum(source["size"] for source in sources) > 256 * 1024 * 1024:
        raise ValueError("source download budget exceeded")
    # Collect verified bytes before creating the exclusive final artifact.
    # Each file is bounded; sdists are stored unopened, not extracted/executed.
    files = {}
    for source in sources:
        name = source["filename"]
        if name in files or Path(name).name != name or source["size"] > 64 * 1024 * 1024:
            raise ValueError("duplicate or oversized source archive")
        with fetch(source["url"], timeout=30) as response:
            if urlsplit(response.geturl()).netloc != "files.pythonhosted.org" or urlsplit(response.geturl()).scheme != "https":
                raise ValueError("unexpected source redirect")
            body = response.read(source["size"] + 1)
        if len(body) != source["size"] or hashlib.sha256(body).hexdigest() != source["sha256"]:
            raise ValueError("source archive digest or size mismatch")
        files[name] = body
    result = dict(report, source_archives_downloaded=True)
    files["SOURCE-REFERENCES.json"] = (json.dumps(result, indent=2) + "\n").encode()
    with zipfile.ZipFile(destination, mode="x", compression=zipfile.ZIP_STORED) as archive:
        for name, body in sorted(files.items()):
            entry = zipfile.ZipInfo(name)  # stable timestamp, no local filenames
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, body)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-archive", type=Path, help="also download/hash-check sdists into a new ZIP")
    args = parser.parse_args()
    result = inventory(json.loads(args.wheels.read_text()))
    if args.source_archive:
        result = source_archive(result, args.source_archive)
    with args.output.open("x") as destination:
        json.dump(result, destination, indent=2)
        destination.write("\n")
    print(json.dumps({"packages": len(result["packages"]),
                      "missing_sdist": [p["name"] for p in result["packages"] if not p["sources"]]}))
