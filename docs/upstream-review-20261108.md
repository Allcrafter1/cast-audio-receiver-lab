# Upstream review — 2026-11-08

Review of [watcher issue #12](https://github.com/Allcrafter1/cast-audio-receiver-lab/issues/12)
and [Python PR #19](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/19).

## Decisions

| Component | Decision | Remaining boundary |
| --- | --- | --- |
| Maintained Vibecast | Commit and publish the verified dev3 source as a prerelease | Does not publish a product image or upgrade an installation |
| Vibecast upstream main | Review through `4cde20b3f49b296debec8cb9a2badb51c7bae940`; no wholesale merge | Overlapping YouTube/discovery changes require separate regression work |
| AirPlay CLI | Prepare v0.5.9 with both Linux asset hashes and rebuilt source evidence | Physical AirPlay 2 acceptance and native ARM64 execution remain unverified; deployed laptop runtime is unchanged |
| Python image | Retain the coherent 3.12 environment; do not merge PR #19 as written | A 3.15 migration needs new dependency/wheel/source inventories and matching CI coverage |

## Vibecast publication and upstream comparison

The maintained fork's commit
[`1a040ed9483745e4532e1c79ec32138198be5710`](https://github.com/Allcrafter1/vibecast/commit/1a040ed9483745e4532e1c79ec32138198be5710)
is published as [cast-audio-0.7.0-dev3](https://github.com/Allcrafter1/vibecast/releases/tag/cast-audio-0.7.0-dev3),
a source-only prerelease, not `latest`. All 139 inventoried source inputs match
the dev3 build. The audio branch advanced by fast-forward; upstream `main`
remained at `b4616f8`. Its main-only release workflow is not triggered by this
branch/tag publication. Existing container and Home Assistant pins are unchanged.

The upstream comparison contains 15 commits after `b4616f8`:

- [YouTube #97](https://github.com/emilsvennesson/vibecast/pull/97) changes the
  InnerTube client to ANDROID and adds Lounge seek/stop/previous/opening-batch
  handling. Our audio resolver uses the maintained extraction/credential paths;
  the controls already have local coverage. Replacing them wholesale would
  discard independently tested audio behavior.
- [YouTube #98](https://github.com/emilsvennesson/vibecast/pull/98) introduces
  MDX replies, persistent screens, refresh and credential-transfer context,
  plus generic relaunch and discovery changes. These overlap with our owner
  continuity, per-output storage and dual identities. In particular it changes
  mDNS `cd` from a certificate digest to a per-device cloud ID and removes the
  digest parameter through receiver/FFI interfaces. That is a protocol change,
  not an interchangeable patch to apply beside our certificate lifecycle code.
  Sender-specific regression tests are needed before selectively adopting it.
- DAZN #94 and SponsorBlock #78 add features outside this audio maintenance
  request; they are not imported. DASH/proxy extensions accompanying video
  support are likewise not substituted for the tested audio cache path.
- [Installation-ID retry #102](https://github.com/emilsvennesson/vibecast/pull/102)
  is a small independent candidate: increase the wait for a concurrently created
  UUID from 100 ms to two seconds. It is documented for a focused follow-up,
  not silently included in the already verified dev3 source publication.
- Dependency/crypto API, Android/Gradle, documentation and upstream release
  commits are reviewed separately from runtime fixes; no mass dependency or
  upstream release-automation replacement is performed.

The watcher now compares upstream main to the explicit last-reviewed commit,
not to the immutable historical dev12 provenance record. Its output distinguishes
reviewed from merged. New commits after that review still create a report.

## AirPlay 0.5.4 → 0.5.9

[Release notes](https://github.com/music-assistant/airplay-cli/releases/tag/v0.5.9)
and the [complete comparison](https://github.com/music-assistant/airplay-cli/compare/v0.5.4...v0.5.9)
cover 15 commits. Relevant corrections include malformed pairing replies,
legacy Apple TV pairing, transient HomePod controls, refused start anchors,
START acknowledgement with no input, clock adjustments, buffered pause/resume,
and PTP peer/group lifecycle. Existing CLI arguments and the persistent command
contract used by our adapter remain supported; no adapter rewrite is needed.

- Source commit: `0a58c239d5fb3cf8927b9707a71c6fe897266b6a`.
- x86_64 release SHA-256: `affa85c5b3edff370f7c08f921d6a3095444acbc10579a3d12713e3b1ebe0425`.
- aarch64 release SHA-256: `37fcc7dc59e4878f465afd2520923baefeb2c9b761c29f4d7fe5b2815bb3b354`.
- Both match the release SHA256SUMS and GitHub asset digests. ELF symbol-version
  inspection finds a maximum GLIBC requirement of 2.34 for both architectures.
  x86_64 `--check` and the actual native sender DACP/RTSP test pass. Reading an
  ARM64 ELF is not native ARM64 execution or a hardware acceptance test.
- Upstream `make test STATIC=1` passes. The independent nine-component source
  export rebuilds OpenSSL, ALAC and mDNS from source, builds the sender, passes
  upstream tests and `--check`. Release binary byte identity is not claimed.
- The prior OpenSSL source-association correction remains applicable and is
  independently checked against the unchanged submodule/artifact hashes.
  Both architecture locks, Containerfile, source recipes, source artifact
  inventory and upstream notices are updated together.

No test here establishes physical HomePod, Sonos, Yamaha or AirPlay 2 acceptance.
The update is prepared for the next product candidate; it is not hot-swapped
into the running receiver by this review.

## Python PR #19 failure

The [failed amd64 job](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/41261737567/job/124716215940)
installs `container-linux-x86_64-cp312.lock.txt` inside Python 3.15. With
`--only-binary=:all:` it cannot install the pinned `aiohttp==3.14.3` for that
interpreter. ARM64 fails in the corresponding stage. The passing Python jobs
exercise only 3.11, 3.12 and 3.13, so they do not validate the proposed 3.15 image.

Do not weaken `--require-hashes` or allow an unreviewed source-build fallback.
The new consistency regression checks every Python FROM against the locked
CPython ABI; the exact image-only PR19 mutation fails that check. Both container
pip stages also reject an interpreter mismatch with a direct diagnostic. Python
3.12 stays selected; Dependabot remains enabled and unchanged. A future 3.15
upgrade must update the build/runtime locks, both architecture wheel inventories,
source references, CI interpreter matrix and container checks as one change.

## Validation of the maintenance change

The isolated maintenance branch passes 371 Python tests (373 discovered, two
host-mpv skips), including the actual v0.5.9 native DACP/RTSP probe. The combined
dev3 development tree passes 433 tests (435 discovered, the same two skips).
The source-export validation and shell syntax check pass. The x86_64 release
binary also passes `--check` in the existing laptop container image with no
network; the active sender's hash is unchanged before/after that isolated test.
GitHub's native ARM64 container job is a separate pending gate when this review
is initially submitted; physical AirPlay playback is still not claimed.
