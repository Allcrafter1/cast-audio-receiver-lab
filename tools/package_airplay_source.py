#!/usr/bin/env python3
"""Assemble pinned public AirPlay sources, never private runtime material.

No downloads, working-tree source, Git database, compiled archives or runtime
credentials are included. This is a rebuildable source candidate, not proof of
byte identity with the separately downloaded upstream executable.
"""
import argparse
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import subprocess
import tarfile
import tempfile

COMPONENTS = [
    (".", "431c5c582eef9307c4e39c50a0ea65e970bc1128", "airplay"),
    ("libraop", "81c2182649da8645ac2a58b78e9f370c79a4165b", "airplay/libraop"),
    ("libraop/crosstools", "41544c653760a205cbf6cebfdeda4a9394cc6455", "airplay/libraop/crosstools"),
    ("libraop/dmap-parser", "2f8ee61e2427a177beea919d72dde8931084fe51", "airplay/libraop/dmap-parser"),
    ("libraop/libcodecs", "3234c96680fbe9f45047936a14df10edca822e5e", "airplay/libraop/libcodecs"),
    ("libraop/libcodecs/alac", "30e526563714325ff384968e116060c4ed606f06", "airplay/libraop/libcodecs/alac"),
    ("libraop/libmdns", "d7f58bf2791c3c25fd729d739a9267ce9db5b696", "airplay/libraop/libmdns"),
    ("libraop/libmdns/mdnssd", "16402f3293b8bf09b8274ba7188202953d8e4f40", "airplay/libraop/libmdns/mdnssd"),
    ("libraop/libopenssl/openssl", "c1eeb9406b6142148f267594197d853403d10208", "openssl"),
]
PROJECT = Path(__file__).resolve().parents[1]
BINARY_SUFFIXES = {".a", ".o", ".so", ".dll", ".dylib", ".exe", ".lib"}


def safe_member(member):
    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("unsafe source archive path")
    if not (member.isfile() or member.isdir() or member.issym()):
        raise ValueError("unsupported source archive member")
    if member.issym():
        target = posixpath.normpath(posixpath.join(str(path.parent), member.linkname))
        if member.linkname.startswith("/") or target == ".." or target.startswith("../"):
            raise ValueError("escaping source symlink")
    return not (path.suffix.lower() in BINARY_SUFFIXES or path.parts[0] in {"bin", "build"})


def _package(checkout, destination, *, components):
    checkout, destination = Path(checkout), Path(destination)
    # Exclusive create: never overwrite an existing release artifact.
    with destination.open("xb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w|") as result:
                names = set()
                def add_bytes(name, payload):
                    member = tarfile.TarInfo(name)
                    member.size, member.mode = len(payload), 0o644
                    result.addfile(member, io.BytesIO(payload))
                for relative, revision, prefix in components:
                    with tempfile.TemporaryFile() as raw:
                        subprocess.run(["git", "-C", str(checkout / relative), "archive", revision],
                                       stdout=raw, check=True, timeout=120)
                        raw.seek(0)
                        with tarfile.open(fileobj=raw) as source:
                            for member in source:
                                if not safe_member(member) or member.isdir():
                                    continue
                                original = member.name
                                member = copy.copy(member)
                                member.name = prefix + "/" + original
                                if member.name in names:
                                    raise ValueError("duplicate source path")
                                names.add(member.name)
                                member.uid = member.gid = member.mtime = 0
                                member.uname = member.gname = ""
                                member.pax_headers = {}
                                result.addfile(member, source.extractfile(original) if member.isfile() else None)
                add_bytes("SOURCE-COMPONENTS.json", json.dumps({
                    "schema": 1, "components": components,
                    "openssl_original_gitlink": "8ddacec11481a37302c19f4454e23299af399f83",
                    "openssl_override_reason": "Matching 3.5.4 source from preceding proxy commit; see audit",
                    "prebuilt_binaries_included": False,
                }, indent=2).encode() + b"\n")
                add_bytes("BUILD-README.txt", b"""AirPlay v0.5.4 Linux x86_64 source candidate

Sources come from the immutable commits in SOURCE-COMPONENTS.json, not local
working-tree files. Existing binary archives and top-level build outputs are
excluded. Component copyright and license notices are preserved in their trees;
the later libraop statement and OpenSSL Apache notice are included alongside.

Build on Linux x86_64 with GCC/G++, make, Perl, Python 3, binutils and libc
development headers installed. From this extracted directory run:

    bash build_exported_airplay.sh .

This rebuilds OpenSSL, ALAC and mdnssd, links the candidate and runs upstream
tests. Tests require local socket support. No downloads, installation, private
Cast credentials or running project instance are required. The candidate is
airplay/bin/cliairplay-linux-x86_64. It is NOT automatically substituted for the
project's tested upstream executable; build against the deployment libc and
repeat device acceptance before choosing to replace that executable.

The OpenSSL source correction and its limits are documented in
airplay-native-source-audit.md. Byte identity with the upstream release binary
is not claimed. This covers the native AirPlay component, not all dependencies
of the complete Cast Audio Receiver container.
""")
                for filename in ("tools/build_exported_airplay.sh", "docs/airplay-native-source-audit.md",
                                 "licenses/libraop-upstream-statement.txt", "licenses/OpenSSL-3.5.4-Apache.txt"):
                    add_bytes(Path(filename).name, (PROJECT / filename).read_bytes())
    with destination.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": destination.stat().st_size, "sha256": digest, "components": len(components)}


def package(checkout, destination, *, components=COMPONENTS):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(prefix="airplay-source-", dir=destination.parent) as folder:
        candidate = Path(folder) / "source.tar.gz"
        report = _package(checkout, candidate, components=components)
        # Same filesystem, atomic publication and no accidental overwrite.
        os.link(candidate, destination)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.checkout, args.destination), indent=2))
