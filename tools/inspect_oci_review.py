#!/usr/bin/env python3
"""Verify OCI JSON descriptors and summarize embedded SBOM/provenance.

Reads only bounded JSON metadata from an OCI tar, never extracts or executes
layers. Runtime layer integrity/contents and licence clearance are separate
checks. Does not print provenance build arguments or environment values.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

MAX_JSON = 32 * 1024 * 1024


def inspect(path, *, verify_blobs=False):
    packages = set()
    statements = []
    images = []
    visited = set()
    blob_count = 0
    with tarfile.open(path, "r:*") as archive:
        names = set()
        for member in archive.getmembers():
            if member.name in names:
                raise ValueError("duplicate OCI archive member")
            names.add(member.name)
            if verify_blobs and member.name.startswith("blobs/sha256/") and not member.isdir():
                expected = member.name.removeprefix("blobs/sha256/")
                if not member.isfile() or not re.fullmatch(r"[0-9a-f]{64}", expected):
                    raise ValueError("invalid OCI blob member")
                with archive.extractfile(member) as stream:
                    actual = hashlib.file_digest(stream, "sha256").hexdigest()
                if actual != expected:
                    raise ValueError("OCI blob digest mismatch")
                blob_count += 1
        def read(name, digest=None):
            member = archive.getmember(name)
            if not member.isfile() or not 0 < member.size <= MAX_JSON:
                raise ValueError("invalid OCI JSON member")
            with archive.extractfile(member) as stream:
                raw = stream.read(MAX_JSON + 1)
            if len(raw) != member.size:
                raise ValueError("truncated OCI JSON member")
            if digest and hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("OCI JSON digest mismatch")
            return json.loads(raw)

        def descriptor(item):
            digest = item.get("digest", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ValueError("unsupported OCI descriptor digest")
            return read("blobs/sha256/" + digest[7:], digest[7:])

        def visit(item, depth=0):
            if depth > 5 or len(visited) > 100:
                raise ValueError("unexpected OCI index complexity")
            digest = item.get("digest")
            if digest in visited:
                return
            visited.add(digest)
            document = descriptor(item)
            if "manifests" in document:
                for child in document["manifests"]:
                    visit(child, depth + 1)
                return
            if verify_blobs:
                for referenced in [document.get("config"), *document.get("layers", [])]:
                    if referenced is None:
                        continue
                    blob_digest = referenced.get("digest", "")
                    if not re.fullmatch(r"sha256:[0-9a-f]{64}", blob_digest):
                        raise ValueError("unsupported OCI blob digest")
                    member = archive.getmember("blobs/sha256/" + blob_digest[7:])
                    if "size" in referenced and member.size != referenced["size"]:
                        raise ValueError("OCI blob size mismatch")
            attestations = [layer for layer in document.get("layers", [])
                            if layer.get("mediaType") == "application/vnd.in-toto+json"]
            if not attestations:
                images.append({"digest": digest, "platform": item.get("platform", {})})
            for layer in attestations:
                statement = descriptor(layer)
                kind = statement.get("predicateType", "")
                subjects = [subject.get("digest", {}).get("sha256")
                            for subject in statement.get("subject", [])]
                statements.append({"type": kind, "subjects": subjects})
                if kind == "https://spdx.dev/Document":
                    for package in statement.get("predicate", {}).get("packages", []):
                        packages.add((package.get("name", ""), package.get("versionInfo", ""),
                                      package.get("licenseDeclared", "NOASSERTION")))

        for item in read("index.json").get("manifests", []):
            visit(item)
    image_digests = {image["digest"][7:] for image in images}
    if not images or not statements:
        raise ValueError("review image lacks images or attestations")
    if any(not item["subjects"] or not set(item["subjects"]).issubset(image_digests)
           for item in statements):
        raise ValueError("attestation does not refer to a reviewed image manifest")
    sbom = any(item["type"] == "https://spdx.dev/Document" for item in statements)
    provenance = any(item["type"].startswith("https://slsa.dev/provenance/") for item in statements)
    if not sbom or not provenance or not packages:
        raise ValueError("review image requires a populated SPDX SBOM and provenance")
    return {"images": images, "attestation_types": sorted({item["type"] for item in statements}),
            "package_count": len(packages),
            "packages": [dict(zip(("name", "version", "declared_license"), item)) for item in sorted(packages)],
            "runtime_layers_verified": verify_blobs, "verified_blob_count": blob_count,
            "runtime_contents_reviewed": False, "licence_review_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--verify-blobs", action="store_true",
                        help="Stream-check all blob hashes, without executing or extracting layers")
    args = parser.parse_args()
    result = inspect(args.archive, verify_blobs=args.verify_blobs)
    if args.summary:
        result.pop("packages")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
