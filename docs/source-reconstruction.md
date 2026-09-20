# Reconstructing the Rust frontend

## Current dev12 source

The primary source is the reviewable maintained fork commit
`f28befe02fe930db300294d6bf49cdf5fec5a747` in
`https://github.com/Allcrafter1/vibecast.git`, based on upstream
`b4616f8f399be706a1409ed21922aa2df892e303`. OCI and CI builds use that immutable
fork commit. `patches/vibecast-0.6.0.dev12-complete.patch` remains a hash-locked
fallback that reconstructs the same 109 build inputs from the upstream base; it
is not stacked with historical patches.

## Current dev11 snapshot

`patches/vibecast-0.6.0.dev11-complete.patch` is the single full patch on the
same upstream commit used below. It adds the artwork-only bridge report and
matching active-cover update to dev6. A fresh checkout reconstructs all109
build files exactly; hashes are in `config/vibecast-0.6.0.dev11-source.lock.json`.
The eight-crate deterministic gate (the seven below plus vibecast-bridge) passes
158 tests, with one live YouTube probe ignored. See WORKING-PLAN for deployment
and end-to-end acceptance; source reconstruction is not a binary-build guarantee.

## Previous dev6 snapshot

Use `patches/vibecast-0.6.0.dev6-complete.patch` alone on upstream
`b4616f8f399be706a1409ed21922aa2df892e303`. It includes dev5, the observer
regression and explicit-audio category correction. Do not stack their supplements
on top. All109 build files match a fresh patched checkout. Source hashes are in
`config/vibecast-0.6.0.dev6-source.lock.json`. Deployment status is recorded in
WORKING-PLAN.md, separately from source reconstruction.

## Previous dev5 snapshot

`patches/vibecast-0.6.0.dev5-complete.patch` is the single current patch for the
same upstream base below. It includes dev4 plus additive DMR music-metadata
preservation. `config/vibecast-0.6.0.dev5-source.lock.json` records hashes.
All109 build files match across a fresh patched clone, local source and remote
build.138 tests in the listed seven-crate deterministic gate pass; one live
probe ignored. Release build and14 silent DMR checks pass. This does not close
the full build-environment, license or independent security audit gates.

Post-deployment test supplement:
`patches/vibecast-0.6.0.dev5-observer-test.patch` applies AFTER the complete dev5
patch. It adds only a second-connection owner-disconnect/takeover regression;
29 core tests pass with it. No runtime source or binary changed. The dev5 source
lock intentionally records the actual original build, while the current working
test source includes this additional test. Do not compare its hash map to the
release lock without accounting for the supplement.

## Previous dev4 snapshot

Use **only** `patches/vibecast-0.6.0.dev4-complete.patch` on a fresh checkout of
`b4616f8f399be706a1409ed21922aa2df892e303` for the dev4 candidate. It incorporates
the earlier audio/YouTube/DMR changes, installation-ID race fix, terminal status,
LOAD diagnostics and app-CLOSE receiver-status refresh. Do not add historical
snapshots or the separate installation-ID patch on top.

A new local clone plus this one patch reproduces all 109 inventoried build-source
files exactly. Reverse-apply check also passes. The recorded hash map does not
include private runtime inputs and does not establish a hermetic binary build.
Dev4's seven-crate deterministic gate below passes 135 tests; one opt-in live
YouTube probe is ignored. Existing audio-only resolver dead-code warnings remain;
this is not a warning-free Clippy result or a full workspace test claim.

The older instructions below describe how the 0.5.0 snapshot was first audited.
Their source identity and deployment statements are historical.

## Historical 0.5.0 reconstruction

The single `patches/vibecast-0.5.0-complete.patch` supersedes the historical
partial snapshots for this release. Apply it ONCE to upstream commit
`b4616f8f399be706a1409ed21922aa2df892e303`; do not stack all patches.
The source lock in `config/vibecast-0.5.0-source.lock.json` records its digest,
the observed compiler and the deployed binary identity. No credentials are
part of this source patch. A full redistribution/license/security audit is still
required before public release; a pattern scan is not that audit.

## What was verified

Read-only build-source inventory found five remote changes missing locally:
Cast diagnostic field logging (algorithm IDs and nonce length, not contents),
mDNS capabilities, DEVICE_INFO capabilities, the corresponding test, and exact
speaker names without an upstream suffix. These already ran in the accepted
Linux frontend. Local copies now match; no runtime behavior changed in this audit.

A fresh local Git clone on the build host plus the complete patch reproduces
all109 inventoried files byte for byte, including the new DMR provider. The
inventory includes Git-visible crate files/assets, root Cargo files, toolchain
file and .cargo configuration; it excludes private state and tools. This checks
source identity, not every possible build-time external input.

## Procedure

The unmodified reconstructed0.5.0 test run exposed a first-start concurrency bug:
one process can initially read an empty installation_id while another writes it.
The existing bounded read retry only covered the create loser. The separate
`patches/vibecast-after-0.5.0-installation-id.patch` extends that same retry to
initial parse failure and adds a regression. Apply it AFTER the complete patch
to reproduce the candidate, not the accepted0.5.0 binary.133 Rust tests pass on
that candidate;1 explicit live YouTube probe remains ignored. No candidate binary
deployed during this audit; existing runtime installation identity is untouched.

Use a fresh checkout, preserving the working installation. Verify the upstream
commit and patch digest against the source lock. In that fresh checkout:

```sh
git rev-parse HEAD
git apply --check /path/to/lab/patches/vibecast-0.5.0-complete.patch
git apply /path/to/lab/patches/vibecast-0.5.0-complete.patch
```

Inspect build-source hashes without exporting source content or private state:

```sh
python /path/to/lab/tools/source_inventory.py /path/to/frontend
python /path/to/lab/tools/source_inventory.py /path/to/reconstructed \
  --compare /private/previous-source-inventory.json
```

Use the recorded compiler, Cargo.lock and a prepared dependency cache. Run Cargo
FROM the reconstructed checkout: `--manifest-path` alone does not make rustup
select that directory's toolchain. On the test host the shell default was1.87.0,
but the actual frontend used stable1.98.1. The locked dependencies reject1.87.0.
Upstream's `channel="stable"` is floating, so explicitly selecting the recorded
toolchain matters for later reproduction. Do not downgrade dependencies merely
to make the unrelated default compiler work.

```sh
rustc --version --verbose
cargo test --offline --locked -p vibecast-apps-default-media \
  -p vibecast-apps-youtube -p vibecast-core -p vibecast-player-api \
  -p vibecast-discovery -p vibecast-messages -p vibecast-platform --lib
cargo build --offline --locked -p vibecast-cli --release
```

Offline commands require dependencies/toolchain already provisioned. Preparation
on a new host is a separate step, not an invitation to update the running host.
The verification run reuses the existing Cargo dependency/artifact cache; it is
not a hermetic clean-room build. Full OS/linker/library pinning, Python dependency
locks, architecture-specific AirPlay binaries and public release automation are
still open. A fresh binary's differing hash alone is not proof of changed source.
