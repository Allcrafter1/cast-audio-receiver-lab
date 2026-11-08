# Reconstructing the Rust frontend

## Current 0.7.0.dev3 cumulative source

Start at public commit `83ba470158189de3bc223701decdc4c502d47644` from
`https://github.com/Allcrafter1/vibecast.git` and apply only
`patches/vibecast-0.7.0.dev3-current.patch`. The exact digest is in
`config/vibecast-frontend.lock.json`. Containerfile and CI use this same patch.
Do not stack any of the historical overlays below on top of it.

The same 139 inventoried inputs are now committed at
`1a040ed9483745e4532e1c79ec32138198be5710` and published as the source-only
[cast-audio-0.7.0-dev3 prerelease](https://github.com/Allcrafter1/vibecast/releases/tag/cast-audio-0.7.0-dev3).
`published_source_commit` records this equivalence; the current build recipe
continues to use the verified base plus snapshot. This source publication does
not publish or promote the product image.

The cumulative source includes the accepted dev1 work, TuneIn, PR #16/#17
frontend integration, the PR #18 follow-ups and the shared-runtime dual identity
implementation. A clean archive plus this one patch was reconstructed separately
and all **139 inventoried inputs** matched the working source. The local review
build uses Rust 1.98.0 and Zig targeting glibc 2.36 (highest referenced symbol
GLIBC_2.34); release CI retains its pinned 1.98.1 toolchain.

Source-review CI vendors registry dependencies into `registry-vendor`, keeping
the deliberately patched `vendor/mdns-sd` path dependency intact. Upstream
Apache-2.0/MIT notices and the description of local changes stay with it.

The installed candidate and remaining acceptance gates are in
[TESTING.md](TESTING.md). The records below describe earlier builds, not the
active source lock or current deployment.

## Historical local PR #18 investigation candidate

Use base `85918111ac68cbf837bf58835b5fd066615963ad` from the maintained fork,
then apply these local review patches in order, once each:

1. `patches/vibecast-tunein-review-20261107.patch`
2. `patches/vibecast-tunein-autostart-20261107.patch`
3. `patches/vibecast-speaker-discovery-review-20261107.patch`
4. `patches/vibecast-owner-continuity-review-20261107.patch`
5. `patches/vibecast-youtube-lifecycle-review-20261107.patch`
6. `patches/vibecast-youtube-controls-review-20261108.patch`
7. `patches/vibecast-android-diagnostics-20261108.patch`
8. `patches/vibecast-mdns-app-discovery-20261108.patch`

The third patch changes only five files for speaker defaults, truthful app
availability and non-blocking MDX startup. Its SHA-256 is
`79361f203dc91da0ecbca59ddeeaea6c0157f95dc47d590b58ec49e73b2219c5`.
The fourth patch adds bounded same-owner continuity and Lounge worker cleanup;
its SHA-256 is
`e6c448bb116af04dc757f8c4276b74e93ab6748edb5f174a2e081cd386c65afd`.
The fifth patch isolates receiver app storage and corrects discovery handshake
and explicit cloud-channel teardown. Its SHA-256 is
`7875e3c35707b05123e2ae015866fc6051585345e8d689d140500a7a2268a3f1`;
its 114 reconstructed inputs and test/build records are retained in
`.state/youtube-lifecycle-20261107-1/`.
The sixth patch adds the ordinary-YouTube selection/original-audio corrections;
its SHA-256 is
`5c523656dc80a1d6241262813ee737bfa109274a5bdbbaadc8618f4cd447c1bf`.
The seventh patch adds bounded pre-launch diagnostics without changing protocol
responses or playback; its SHA-256 is
`bd4a186db30196391e6c520937d219dd1121be2ed6bcea2a27fe5ac43ff5fd14`.
Their frozen records are `.state/youtube-controls-20261108-1/` and
`.state/youtube-android-diagnostics-20261108-1/`. The diagnostic deployment was
rolled back to the controls build for comparison; it remains part of the ordered
source recipe for the following candidate.

The eighth patch adds application-subtype DNS-SD discovery from the shared app
registry. Its SHA-256 is
`c4e6f2da1440a5b11cf08561d4ed49fa440261fa3192b6d8d839b455de0b91da`.
It keeps one service instance and daemon per receiver, the stable device
identity and audio-only `ca=199428` profile. It changes no playback, YouTube
Music, reconnect or ownership rules. The private candidate is
`0.7.0.dev1+local.20261108.mdnsapps`, with freeze record
`.state/mdns-app-discovery-20261108-1/`. Independent reconstruction from the base
and all eight patches matches **136 source inputs** exactly, including **22
vendored files**. The release build and all **14 silent binary checks** pass.
The candidate is active on the test laptop; the loaded `/proc/PID/exe` SHA-256
is `02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b`,
matching the frozen binary. Its highest referenced glibc symbol version is
`GLIBC_2.34`. All 28 installed Python files match, both routes are ready, and
both receiver identities retain `ca=199428` / `display_supported=false`. The
preceding container is retained as
`cast-audio-receiver-before-mdns-app-discovery-20261108-1`. Ordinary Android
sender acceptance is not met: the phone retest lists both apps and confirms
Music playback, but ordinary YouTube selection still fails with transient entry
removal. Build and installation checks do not establish ordinary YouTube casting.

This overlay includes a narrowly patched, vendored `mdns-sd` **0.20.1**, rather
than relying on a modified Cargo registry cache. The original crates.io archive
has SHA-256
`fb75febbe5fa1837a52fdbd1c735e168286c5c645fc2ddd31526f65c49941c2e`,
matching the pre-patch Cargo.lock checksum. Its licence remains **Apache-2.0 OR
MIT**, with both upstream licence texts retained. The local changes add multiple
subtype PTRs for the same instance, answer the requested subtype even when the
base PTR is already known, and announce/withdraw all subtype PTRs together. The
legacy single-subtype API remains compatible. The frozen source manifest
includes the vendored directory and licences, plus the root Cargo patch/lock
inputs; the earlier 114-file inventory alone is insufficient for this candidate.

The earlier local records `.state/pr18-review-20261107-1/` and
`.state/pr18-continuity-20261107-1/` distinguish the initial five-file review
from the follow-up. All 114 frontend inputs match those earlier frozen candidates,
with forward/reverse patch checks. These overlays are not part of the public release
lock below. See [the investigation](youtube-discovery-pr18.md) for validation,
deployment status and the remaining legacy browser-cache boundaries.

## Historical 0.7.0.dev1 maintained source

Check out public dev26 base `83ba470158189de3bc223701decdc4c502d47644`
from `https://github.com/Allcrafter1/vibecast.git`, then apply
`patches/vibecast-0.7.0.dev1-current.patch` exactly once. Its SHA-256 and base
are recorded in `config/vibecast-frontend.lock.json`; Container and source-review
CI follow the same recipe. The matching maintained-fork commit is recorded for
review.

The cumulative snapshot includes the post-dev26 reliability and credential
work, CTT-aware InnerTube prefetch, complete request-recipe forwarding, bounded
audio recovery, iPad/mobile session reconnection and Home Assistant controls for
the real YouTube Music queue. Do **not** stack the old dev27 snapshot,
`vibecast-load-recovery-20261002.patch`, dev13 or another historical snapshot on
top. The previous reconstruction instructions below are historical fallbacks.

## Historical dev27 snapshot

The earlier `patches/vibecast-0.6.0.dev27-current.patch` reconstructs the
credential-transfer candidate documented in `youtube-ctt-dev27.md`. It remains
historical evidence and must not be applied with the current snapshot.

## Historical dev13 private review overlay

Start at the dev12 maintained commit below, then apply
`patches/vibecast-dev13-internal-bridge.patch` once. Its exact digest/base are in
`config/vibecast-0.6.0.dev13-overlay.lock.json`. OCI and CI use this same input.
The patch disables the normal browser page and separates bridge/Cast binding;
it contains no authentication material. The source changes are local review
work, not a newly published fork revision. Do not apply it on top of itself or
assume the old dev12 binary hash identifies the dev13 build.

## Historical dev12 source

The primary source is the reviewable maintained fork commit
`f28befe02fe930db300294d6bf49cdf5fec5a747` in
`https://github.com/Allcrafter1/vibecast.git`, based on upstream
`b4616f8f399be706a1409ed21922aa2df892e303`. OCI and CI builds use that immutable
fork commit. `patches/vibecast-0.6.0.dev12-complete.patch` remains a hash-locked
fallback that reconstructs the same 109 build inputs from the upstream base; it
is not stacked with historical patches.

## Historical dev11 snapshot

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
