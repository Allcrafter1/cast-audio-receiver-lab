# Dependency artifact locks

The OCI amd64/CPython 3.12 runtime has a separate complete Python artifact lock:
`config/container-linux-x86_64-cp312.lock.txt` and its metadata/licence inventory
`config/container-linux-x86_64-cp312.wheels.json`. It includes the YouTube
extractor stack and optional DLNA/Sonos adapters. Project-wheel build tools are
isolated in `config/container-build-cp312.lock.txt` with the matching
`config/container-build-cp312.wheels.json`; they are not runtime dependencies.
CI verifies that every direct Python runtime dependency declared by the project
is represented in the container lock. These locks do not cover Debian packages
or the base image.

`management-linux-x86_64-cp312.lock.txt` pins the 17 selected runtime wheels for
the CPython 3.12 Linux x86_64 management/bridge/AirPlay-discovery environment.
The accompanying `.wheels.json` records filenames, digests and declared licenses
from wheel METADATA. It was generated from the already-tested version constraints,
not by upgrading packages. Total downloaded artifacts were about 9.1 MiB.

The container lock was verified in a new CPython 3.12 virtual environment with
an offline `--require-hashes` installation, `pip check`, and imports of all major
runtime adapters. A separate CPython 3.13 Linux x86_64 management lock
is now available as `management-linux-x86_64-cp313.lock.txt` with its own wheel
inventory. A fresh environment on the laptop passed offline hash-locked install,
`pip check`, and all 137 tests without skips using the installed dev5 wheel
(import verified from site-packages). The live environment was not replaced.
Use python3.13 and the cp313 lock in the commands below for that target.

## Recreate the verified environment

For that exact interpreter/platform, prepare a wheelhouse from public PyPI:

```sh
python3.12 -m pip download --index-url https://pypi.org/simple \
  --only-binary=:all: --require-hashes \
  -r config/management-linux-x86_64-cp312.lock.txt --dest /private/wheelhouse
python3.12 -m venv /private/test-environment
/private/test-environment/bin/python -m pip install --no-index \
  --find-links /private/wheelhouse --require-hashes \
  -r config/management-linux-x86_64-cp312.lock.txt
/private/test-environment/bin/python -m pip check
PYTHONPATH=src /private/test-environment/bin/python -m unittest discover -s tests
```

Do not reuse architecture/interpreter-specific hashes on ARM, macOS or a different
CPython version. Wheel compatibility also depends on libc/platform tags. New
targets require their own download, tests and lock. Dependencies of the lab wheel
are covered here, but the lab wheel itself and build tools are separate artifacts.
FFmpeg/mpv, Rust dependencies/toolchain, airplay-cli and yt-dlp/EJS/Deno are not
covered by this runtime lock. This is not a complete release SBOM or safety audit.

## Updating deliberately

1. Reproduce the failing boundary on the pinned release.
2. Download candidate versions into a separate target-specific wheelhouse; never
   run an unbounded upgrade in the production environment.
3. Run `tools/wheel_inventory.py WHEELHOUSE` to inspect artifact/license metadata,
   and `--requirements` to obtain exact requirement/hash lines. The tool reads
   archives without importing, installing or executing them. It rejects multiple
   distributions with the same normalized name to avoid mixing target builds.
4. Review upstream changes and license/advisory changes separately. A matching
   hash only proves artifact identity, not trust or compatibility.
5. Install into a fresh environment, run `pip check`, unit/integration and target
   acceptance tests, then update locks, version and release provenance together.

Keep package files' license notices when redistributing them. Wheel METADATA
summaries do not replace the license texts contained in the wheels. Public
support reports should contain selected names/versions/hashes, not unrestricted
environment dumps, private index URLs or authentication data.
