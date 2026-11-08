# TuneIn Radio receiver — issue 8

TuneIn support is included in `0.8.0-dev1`. It implements
[issue 8](https://github.com/Allcrafter1/cast-audio-receiver-lab/issues/8), whose
requested workflow is casting from the existing TuneIn Android app, including
TuneIn Radio Pro. Pro and a Premium subscription are different products; Premium
acceptance is not established by implementing public live radio.

## TuneIn Radio Pro — 0.8.0-dev2

The issue reporter confirmed Free works but Pro does not with 0.8.0-dev1.
Research on 2026-11-08 identified the separate Pro Cast application ID:

| Android app | Cast application ID | Official receiver URL |
| --- | --- | --- |
| TuneIn Free (`tunein.player`) | `12F05308` | `https://prod-cast.tunein.com` |
| TuneIn Radio Pro (`radiotime.player`) | `8DD9AEA2` | `https://prod-cast.tunein.com` |

Primary evidence is Google's public registry entry for
[Free](https://clients3.google.com/cast/chromecast/device/app?a=12F05308&cap=262149)
and [Pro](https://clients3.google.com/cast/chromecast/device/app?a=8DD9AEA2&cap=262149).
The latter explicitly names **TuneIn Pro**, and both use the identical URL.
The Pro ID was found by reading the published audio-capable app catalogue, then
independently fetching both entries again. The development receiver is excluded.

Version 0.8.0-dev2 registers both IDs with the same existing TuneIn provider.
There is no Android-package-name allowlist to change. Station resolution,
autostart, credentials, metadata and playback controls retain the existing flow.
Use the normal audio endpoint, rather than its YouTube-only `(YT)` alias.

Local verification passes: all 15 TuneIn unit tests, 16 isolated Cast checks
for each app ID and the complete Python suite (437 run, 13 environment skips).
Pro LAUNCH fails on the previous binary and succeeds on the corrected binary.
The optimized binary was built locally; all 136 frontend source files match
the independently reconstructed release snapshot.

The isolated smoke accepts `--app-id 8DD9AEA2 --tunein-only --live-station` to
exercise Pro availability, LAUNCH, live LOAD, metadata and controls.
These receiver-level tests do not substitute for a real Pro app. No Pro licence
or Premium subscription was available for a physical sender test; the reporter
is asked to retest after updating. Pro and Premium remain distinct products;
see [TuneIn's explanation](https://help.tunein.com/support/solutions/articles/151000172107-what-s-the-difference-between-tunein-and-tunein-pro-).

## Integrated release

TuneIn and its autostart fix are included together with the volume/Sonos work
and dual Cast identities.
TuneIn continues to use the original speaker; the video alias is YouTube-only.
The hardware observations below describe the earlier TuneIn test, not a new
stock-app acceptance run of this candidate.

## Earlier TuneIn-specific deployment

The combined candidate `0.7.0.dev1+local.20261107.tunein` is running on the
existing test laptop, now with build `tunein-autostart-20261107-1`. It retains all
combined unpublished frontend and Python changes, including the final
Sonos/DLNA and volume work. Functional acceptance is **TuneIn only**.

The user confirmed artwork, playback and switching control to/from the Web.
The initial Cast handoff required two extra Play presses: logs showed elapsed
radio time rejected as `LIVE_SEEK_UNSUPPORTED`, followed by a retry staying
paused because of `autoplay=false`. Native station LOAD now starts at time zero
with autoplay, matching the official TuneIn receiver's load/preload/play flow.
Explicit later Pause/Stop commands retain priority, including while resolving.
Direct URL loads retain their original timing/autoplay behavior.

Everything was built on the local development machine. The frontend was built
with Rust 1.98.0 and Zig for the laptop container's GLIBC 2.36 compatibility;
the binary requires at most GLIBC 2.34. SHA-256:
`16dcdc7aba9a504c2fcce314cc508f30eaace80fb695539bddcea7b1d55c7cc1`.

The complete 28-file Python/asset package was independently checked against its
wheel and again against the running container; this fix leaves those files
identical. Both existing outputs are ready, route IDs and private state are
retained, and the previous combined container is kept as
`cast-audio-receiver-before-tunein-autostart-20261107-1`. Build and deployment
manifests are in `.state/tunein-autostart-20261107-1/`. No public release or
source-version bump was made.

The compatible binary passed 15 isolated TuneIn-only smoke checks, including
native `autoplay=false` handoffs at times 37.25 and 0, both starting without a
PLAY command, and explicit Pause/Play afterward. All 15 provider tests and the
core pending-control regression pass; formatting and scoped Clippy pass.
The autostart fix awaits the user's stock-app retest. To repeat the isolated
test without the DMR regression:

```sh
python tools/test_tunein.py --tunein-only \
  --binary .state/tunein-autostart-20261107-1/vibecast \
  --live-station --guide-id s80044 --switch-guide-id s24861
```

## Protocol and scope

The dedicated app provider handles Cast application IDs `12F05308` (Free) and
`8DD9AEA2` (Pro, added in 0.8.0-dev2). The current
[official receiver](https://prod-cast.tunein.com) uses the Cast media namespace:
its LOAD interceptor takes `guideId`, `serial`, `partnerId`, `version` and an
optional `accessToken` from **top-level** `customData`. The station identifier is
not a playable media URL. A plain alias to the Default Media Receiver would not
implement this workflow.

The independent Rust implementation resolves live station IDs (`s` followed by
digits) through `https://opml.tunein.com/Tune.ashx`. Initial metadata comes from
`https://feed.tunein.com/profiles/<id>/nowPlaying`. Bearer credentials are used
only for TuneIn API requests, never attached to third-party station streams or
returned Cast metadata. Direct HTTP(S) LOADs without a guide ID are also
supported, preserving local media and signed URL escaping.

Live streams use the existing output adapters and standard Cast Play, Pause,
Stop and device volume/mute. Shared playback reports provide actual output
state. Live seeking is unsupported; elapsed time in a native station handoff
is normalized to the live edge. The provider does not add a new playback
engine or change YouTube resolution, caching or sender ownership.

This first implementation does not establish Premium/DRM compatibility, every
TuneIn ad sequence, podcasts/on-demand playback, or periodic now-playing updates.
Preroll sequences and explicitly on-demand content return a structured failure
rather than playing only an advertisement or misreporting on-demand audio as live.
Station availability, geographic restrictions and sender authentication remain
subject to the service and Cast environment. The confirmed public-live workflow
does not establish every sender version, subscription or station.

Protocol evidence was read on 2026-11-07 from the public Google app registry and
the official receiver's [linked JavaScript bundle](https://cdn-cast.tunein.com/resources/assets/js/v2.049b0be6b0e116351e0c.js)
(SHA-256 `1a5fd1ed4531ff33db766e5ac2b70ce3792d61f99151f73b1ae1e4b9115daf82`).
No proprietary receiver source
was imported into this project. The legacy custom namespaces found in older
traces are not implemented as an invented alternate protocol.

## Initial standalone build and verification

The frontend lives in `/home/codex/cast-repeat-frontend`; the maintained product
checkout is `/home/codex/cast-repeat-product`. Existing unpublished changes are
retained. This change leaves the frozen release snapshot and source lock intact;
a separately recorded TuneIn delta and review snapshot carry the new source.

```sh
cargo test --offline -p vibecast-apps-tunein -p vibecast-apps-default-media \
  -p vibecast-platform -p vibecast-core -p vibecast-apps-youtube --lib
cargo build --offline --locked --release -p vibecast-cli
```

Final local verification used an immutable source copy, Rust 1.99.0 and the
existing locked dependency cache. No dependency versions were changed.

- Rust regression gate: **402 passed, 3 existing live probes ignored**, across
  13 crates including TuneIn, YouTube, Default Media Receiver, core and platform.
- TuneIn-specific tests: **15 passed**, including numeric/string sender version,
  API and wrapper errors, credential isolation, metadata fallback, supported audio
  formats, live timing and bounded body/timeout/wrapper handling.
- Scoped TuneIn Clippy with `-D warnings` and workspace formatting passed. The
  full build retains the existing YouTube unused/dead-code warnings.
- Real isolated Cast TLS/bridge smoke: **14 checks passed**. Public stations
  `s80044` and `s24861` resolved, with metadata, Play/Pause, volume in both
  directions, failed-LOAD recovery, station replacement and DMR takeover.
- A short public `s80044` stream excerpt decoded successfully through FFmpeg
  to a null output. No speaker or audio device was opened.
- Full Python suite: **429 run, 13 skipped, one existing source-export error**
  caused by private machine markers in older working-plan notes. These notes
  were already present before this feature; all 415 other tests passed. New
  TuneIn documentation, tool and source patches pass the export text checks.

Candidate executable: `.state/tunein-review-20261107/vibecast` in the product
checkout. Binary SHA-256:
`5ae7431d57586430dd5cf8f2d2a8167d582afbe19a2ecbe107f72b1cc1e91f98`.
The adjacent `review.json` records source hashes and verification results.

Source artifacts over frontend commit `85918111ac68cbf837bf58835b5fd066615963ad`:

| Artifact | SHA-256 | Application |
| --- | --- | --- |
| `patches/vibecast-tunein-receiver.patch` | `5a2134c30763fd25ddef510e4665fca3a0e6f16017077ee90e6694ca2fc92847` | TuneIn-only delta; also applies after the existing playback/output review work. |
| `patches/vibecast-tunein-review-20261107.patch` | `6556f01e6dcfc13ce67ef1ca491f7f52551faeb204ca64e0a919ff8160c27c49` | Complete tested candidate, including the concurrent unpublished frontend changes. Apply once to the stated commit. |
| `patches/vibecast-tunein-autostart-20261107.patch` | `094d88e1655163423eec47af347f35d8decd85fa06dfd759cda3cb59b500b5af` | Additional native autostart fix and regression, applied after the complete TuneIn review snapshot above. |

Forward and reverse application checks passed. Do not stack the complete snapshot
with another cumulative review snapshot or add the TuneIn-only delta twice.
The existing release lock and container recipe remain unchanged; a future image
must explicitly adopt the reviewed candidate. This initial standalone artifact
was not deployed; the later combined laptop candidate is recorded above.

The repeatable smoke tool uses temporary synthetic credentials and an emulated
output, with no production state. Requires Python `cryptography` and `websockets`:

```sh
python tools/test_tunein.py --binary .state/tunein-review-20261107/vibecast
python tools/test_tunein.py --binary .state/tunein-review-20261107/vibecast \
  --live-station --guide-id s80044 --switch-guide-id s24861
```

The second command explicitly enables public TuneIn API access. These tests
exercise receiver routing and controls; stock Android sender trust and audible
hardware playback remain separate acceptance checks.

## Stock-app acceptance

With a candidate binary running in the intended installation, open TuneIn on
Android, play a public radio station, select the existing Cast speaker, and
check audible playback, station switching, Play/Pause, Stop, volume/mute and
reconnecting. Then cast a direct Home Assistant radio stream and a YouTube Music
track to check the other receiver paths. Record the exact candidate and app
version before closing issue 8; an isolated development sender does not validate
the stock app's device-authentication policy.
