# Astra technical review and correction round — 2026-09-20

## Objective

Review and correct the latest manual-acceptance findings, adopt the reviewed
airplay-cli release and prepare the agreed release boundaries without
redesigning the working receiver. Deliver small, reviewable changes with
regression evidence.
This is a private staging round: do **not** publish the repository, image,
authentication material or a Music Assistant announcement.

Read `AGENTS.md` and the newest section of `docs/WORKING-PLAN.md` first. Preserve
unrelated user work and the tested behavior: YouTube Music reception, Default
Media Receiver, HA status/cleanup, square artwork, persistent AirPlay, certificate
rotation and stable route identities. Never print or commit certificate/key
bodies, signed media URLs, private hosts or account data.

## Phase 0 — baseline and evidence

1. Record the exact source/fork commits, dependency/image versions and current
   automated results before editing. Treat the dirty research workspace as user
   state; use the clean private staging/export workflow for publication-shaped
   checks.
2. Preserve the relevant HA log evidence. The local-output failure occurs after
   successful YouTube resolution and reports
   `PLAYBACK_COMMAND_FAILED: mpv command failed: invalid parameter`.
3. Confirm which mpv version is installed in the HA/container build and reproduce
   its JSON IPC rejection with a minimal test. Do not guess from the laptop's mpv.

## Phase 1 — airplay-cli v0.5.4 update

Update the tested/published candidate from Music Assistant airplay-cli v0.5.3 to
the latest release v0.5.4. Do not merely change a version string:

- pin annotated tag `v0.5.4`, target commit
  `431c5c582eef9307c4e39c50a0ea65e970bc1128`;
- pin `cliairplay-linux-x86_64` SHA-256
  `1ac56a15fb548f07a1dae94be16d4bea308420a0ec0cd04238023e44345fc1c9`;
- pin release `SHA256SUMS` SHA-256
  `0df2ba3ac02f5c8f48fcd05f219480968aeb19566be5d3a26d6e7480fb29f235`;
- update Containerfile, lock/provenance records, maintenance/packaging docs and
  third-party inventory together; preserve the previous pin for rollback.

Review the two upstream changes rather than assuming SemVer compatibility:

1. PR #74 follows the receiver's PTP clock for standalone HomePods on HomePod
   OS 27+ (`AudioAccessory*`, `igl=1`, no group/stereo IDs), adds a shared-memory
   layout change and `CLIAIRPLAY_PTP_FOLLOW=0|1` override. Unknown/pre-27
   versions intentionally retain prior behavior.
2. PR #75 raises the shared-PTP followed-clock table from four to eight and
   changes that shared-memory layout to v3. This affects only shared PTP with
   five or more standalone OS-27 HomePods by intent.

Treat the shared-memory layout bump as an operational compatibility boundary:
verify whether this project ever starts/attaches a shared PTP daemon. If it does,
upgrade and restart daemon and clients as one versioned unit and test that no
v0.5.3 daemon survives an update. If it does not, document the path as currently
unused instead of inventing support code.

First run the upstream static/unit checks available for the exact source. Then
prove our adapter contract: `--check`, startup arguments, stdin PCM, command
FIFO, status parsing, metadata/artwork/progress, volume, pause/resume, seek/
flush, track replacement, clean disconnect/reconnect, persistent-session reuse,
failure cleanup and no orphan child. Run the existing Redmi/RAOP acceptance if
available without user interaction. HomePod/PTP hardware claims remain
unverified unless real hardware is actually tested; specifically record tests
still needed for standalone OS 27, pre-27/grouped behavior, shared daemon and
more-than-four receivers. A failed new candidate must roll back cleanly to
v0.5.3 rather than prompting unrelated workarounds.

## Phase 2 — local mpv compatibility bug

Investigate `MpvAudioBackend.load()` and the exact `loadfile` signature supported
by the packaged mpv. Implement the smallest compatible invocation or explicit
version/capability fallback. Requirements:

- load, autoplay/paused load and non-zero start position work;
- a compatibility fallback triggers only for the identified invalid-parameter
  response and does not swallow URL/decoder/network errors;
- replacement load does not let an old `end-file` event finish the new item;
- seek fallback continues to preserve state/volume;
- add unit coverage and, where practical, an integration test against the exact
  packaged mpv binary;
- distinguish "mpv accepted and decoded the load" from "HA has an audible host
  audio device" in status and acceptance notes.

## Phase 3 — intermittent AirPlay seek feedback

Add correlation-level diagnostics around one seek: sender command/generation,
Python requested position, decoder generation, FLUSH/restart, periodic progress,
airplay-cli receiver events and Rust report/canonical-state application. Logs
must not include URLs or private target data.

Create a deterministic regression test in which an old periodic/event report
arrives after a newer seek/load. Identify the actual winning stale path before
fixing it. Prefer a monotonically increasing track/seek generation or a narrow
pending-seek guard; do not add arbitrary sleeps/debounce, recreate the transport
on every seek, or globally ignore real backend position. Acceptance:

- the old position cannot be published after the accepted new seek generation;
- the requested position remains visible while the replacement decoder buffers;
- real progress resumes from the new point after start;
- pause/play, rapid repeated seeks, track changes and persistent transport still
  pass existing tests.

If the stale value originates solely in receiver firmware and cannot be hidden
without lying about state, document that evidence rather than adding a risky
workaround.

## Phase 4 — management UI grouping

Keep the existing visual language. Put DLNA and Sonos in separate semantic
subgroups/cards/fieldsets, each containing its own name, address and add button.
Use a responsive grid/flex rule so labels/buttons remain paired on desktop and
mobile. Add a lightweight DOM/static test for group membership/order and retain
keyboard labels/focus behavior. Do not expand experimental protocol claims.

## Phase 5 — one user-facing interface

In the maintained Vibecast fork, decouple the player-bridge bind address from
the Cast/eureka listener address:

- Cast/eureka remain LAN reachable as required for discovery and control.
- The product's player bridge defaults to loopback.
- `/player` WebSocket and required `/license` and `/manifest` proxy routes remain
  functional for internal adapters/media.
- The embedded Shaka browser page and `/player.js` are disabled in the normal
  product build. They may remain behind an explicit development-only option,
  default off, if that is simpler and useful upstream.
- Opening the product manager must never register a `Browser` player or advertise
  an extra receiver.

Test loopback connectivity, rejected LAN access, Python adapter registration,
proxy route generation/access and clean shutdown/reconnect. Update the fork in a
reviewable commit, then update this product's immutable fork pin/source lock and
complete reconstruction patch. Do not hide the old page only with CSS or leave
the listener publicly exposed.

## Phase 6 — README, origin, licence and attribution cleanup

Rewrite the README around this project's identity:

1. Goal: modular Linux audio receiver/bridge, initially excellent YouTube Music
   and generic direct-media Cast input, with local/AirPlay outputs.
2. `What comes from Vibecast`: CastV2/runtime/app foundation and exact upstream
   base/fork commits under MIT.
3. `What this project adds`: audio-speaker identity, external output protocol,
   per-output management, YouTube queue/performance/control work, local mpv,
   persistent AirPlay, artwork, supervisor/health/diagnostics, HA packaging and
   experimental network outputs.
4. Clearly identify the separate maintained fork and historical Python research.
5. Supported versus experimental/unverified hardware, fragile service/auth
   boundaries, AI-assisted origin, contribution invitation and no endorsement.
6. Present one management UI only; call port 8010/internal bridge an
   implementation detail, not a user destination.

Keep original product code GPL-3.0-or-later and the Vibecast fork MIT unless an
actual provenance finding requires another treatment. Preserve MIT notices and
modified-source history; do not claim that root GPL relicenses third-party code.
Finish or precisely mark incomplete the source/licence inventory for the exact
FFmpeg, mpv, Rust, Python and airplay-cli artifacts. Add the missing Chromium
BSD attribution for `cast_channel.proto`. Record that current libraop upstream
now expressly puts Philippe's own code under MIT while embedded third-party code
retains its terms; the current airplay-cli notice predates that statement and
must not be repeated as if still unresolved. Retain airplay-cli's complete mixed
native notices and produce/update SBOM and corresponding-source records where
the current toolchain supports it.

Document accurately that this project does not depend on the official Google
Cast SDK or a receiver registered through its developer console. It implements
the Cast-facing path independently through the maintained Vibecast fork and
separately licensed open-source protocol material. Do not turn this factual
statement into a claim that Google/YouTube/Play terms or revocation risk cannot
apply, and do not imply Google endorsement/certification.

## Phase 7 — prepare separate authentication-bundle distribution

Implement only the product plumbing and documentation needed for the agreed
separation. **Do not upload, publish, print, commit or copy the real 773-window
bundle into a source/export/image artifact in this round.** Use synthetic bundle
fixtures for all automated download tests.

Target design:

- a dedicated minimal GitHub repository will later hold documentation and
  versioned Release Assets, not credential bytes in Git history;
- the main project consumes a small versioned manifest containing schema,
  compatibility/coverage metadata, download URL, byte size and SHA-256, with a
  verifiable signature/attestation field or clearly defined signing mechanism;
- acquisition is explicit and visible, bounded in size/time, verifies digest
  before parsing, validates the existing bundle schema/signatures, imports
  atomically with restrictive permissions and preserves the last-known-good
  bundle for rollback;
- local-file/HA `/share` BYO import remains a first-class override and never
  requires network access;
- a missing, withdrawn, truncated, oversized, redirected-to-an-untrusted-host,
  bad-digest, bad-signature or invalid-schema asset fails clearly and never
  downgrades to unverified material;
- status/support data may contain only safe bundle version/coverage/readiness,
  never certificate bodies, private keys, auth signatures, raw asset URLs with
  tokens or fingerprints that have not been explicitly allowlisted;
- source export and image secret scans must still pass.

Document origin, purpose, shared-device-identity/revocation fragility, separate
legal uncertainty, withdrawal limitations and user-supplied replacement without
claiming that separate hosting changes the underlying legal question. Keep the
provider boundary host-agnostic enough that GitHub Releases can later be replaced
with object storage without a receiver refactor. Do not create object-storage
infrastructure now; the intended first host is a separate GitHub Release because
the artifact is only about 2.74 MiB.

## Phase 8 — verification and hand-off

Run, at minimum:

- full Python suite on supported versions;
- targeted and full maintained-fork Rust tests;
- upstream/contract checks for the exact airplay-cli v0.5.4 binary and a recorded
  v0.5.3 rollback smoke test;
- clean wheel inspection and secret/source export checks;
- clean OCI build and exact packaged mpv smoke/integration test;
- HA source-build/install/start, ingress and LAN UI, restart/state persistence,
  local-load protocol success, Cast readiness and private-bundle import/rotation;
- physical AirPlay regression if the already available test receiver can be used
  without user interaction; otherwise record one concise manual test script.

Do not claim audible local HA playback without an output device. Do not claim
DLNA/Sonos/HomePod hardware compatibility without those tests.

Report:

- root cause and changed files for each bug;
- tests added and exact results;
- fork/product commits and updated immutable pins;
- exact airplay-cli v0.5.4 changes reviewed, tests actually run, and every
  deferred HomePod/PTP hardware scenario;
- remaining manual checks and release blockers;
- bundle-provider behavior tested with synthetic material and confirmation that
  the real bundle was not published or embedded;
- any architectural deviation and why it was necessary;
- confirmation that no private authentication material entered Git/artifacts.

If a fix would require a new dependency, broad protocol rewrite or weakened
security boundary, stop that item, document evidence/options, and continue with
the other independent phases.
