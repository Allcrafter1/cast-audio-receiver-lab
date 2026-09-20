# Working plan

## Architecture and publication decision gate — 2026-09-19

This section is the authoritative next-phase plan. Do not start the Home
Assistant package before the architecture/repository/configuration/packaging
review below has been discussed and agreed. Historical sections remain evidence,
not an instruction to reopen completed work.

### Product goal and modularity

- Primary deliverable is a maintainable open-source Linux project. A Home
  Assistant App/add-on is one deployment of that project, not the core product.
- Keep input, normalized playback/session state, and output responsibilities
  separate enough to add another input or output without rewriting the whole
  receiver. Avoid a general plugin framework or speculative abstraction layer.
- Current inputs: YouTube Music through the Cast frontend and direct HTTP(S)
  LOAD through the Default Media Receiver. Later Spotify/Deezer/etc. inputs are
  extension possibilities, not current commitments. Spotify Cast and Bluetooth
  remain out of scope.
- Current outputs: local mpv and persistent AirPlay. Evaluate a DLNA output using
  maintained upstream components before deciding whether it belongs in the first
  public release. Evaluate Sonos separately; do not equate generic DLNA support
  with complete Sonos behavior.
- WiiM Voice is a separate project and must not enter this repository's scope.
- Google Home adoption/groups are closed as a direct target: practical testing
  showed they cannot provide the required integration. A future group feature
  would receive once centrally and distribute through our own local outputs;
  it is a separate routing/synchronization milestone, not Google group emulation.

### Required review before packaging

- Explain and review the actual components, process ownership, audio/metadata/
  artwork/control flows, coupling and maintenance debt. Small, behavior-preserving
  corrections may be made; discuss substantial refactors first.
- Decide the minimum stable contracts between inputs, session/control state and
  outputs. Preserve working YouTube queue semantics and AirPlay behavior. Do not
  create an unneeded dynamic plugin ABI.
- Propose repository layout, minimal user configuration, reproducible OCI/Linux
  packaging, maintenance/diagnostics and only then the HA wrapper.
- Review attribution, licenses, upstream modifications, AI disclosure, fragile
  dependencies and publication blockers. Thank actual upstream/research authors
  even where attribution is optional; never imply endorsement.

### Configuration policy

Prefer automatic, safe defaults and expose only settings users plausibly need.
For bind address, state paths, internal ports, binary locations, log level,
local audio target and public artwork URL, document purpose and decide whether
each is internal/autodetected, an advanced option, or a normal user option.
Web UI port and replaceable private authentication-bundle location are known
user-facing requirements. Container/HA configuration must not expose every
internal implementation detail.

### Packaging, maintenance and diagnostics

- First establish one supervised runtime and reproducible OCI image; a normal
  Linux service/installer and HA App/add-on should consume the same release
  rather than maintain different receiver implementations.
- Compare one-repository versus split-repository costs. Prefer the smallest
  repository set that preserves clear source, adapter and packaging boundaries.
- Pin versions/build inputs by component. Use established GitHub dependency
  update mechanisms and CI before writing a custom updater. Production updates
  remain reviewed, tested and reversible rather than unattended.
- Define `/health` for liveness/readiness, `/status` for safe operational state,
  structured local logs with stable event/error categories, and an explicitly
  allowlisted/redacted support bundle. No credentials, signed media URLs,
  personal playback history or pairing secrets in public diagnostics.
- Before packaging, verify whether the existing frontend/player protocol can
  express receiver-origin volume/play/pause/seek/track commands back to the
  active Cast application. Fix a structural gap before freezing packaging;
  hardware/user acceptance may follow later.

### Updated acceptance and backlog

- Dev11 square artwork in Home Assistant: USER-CONFIRMED PASS.
- Default Media Receiver from Home Assistant: sufficient first-release scope.
  Do not promise universal Cast-app compatibility; community tests/contributions
  may extend it later.
- Multiple physical outputs, Yamaha/other AirPlay receivers, native AirPlay 2 /
  HomePod and small-hardware resource profiling are deferred until packaging can
  run on representative target hardware.
- Approx. 2026-09-19 22:10 Europe/Berlin: one AirPlay playback start failed;
  reconnect recovered it. Preserve as a single incident, inspect retained logs,
  and do not change transport behavior without recurrence or concrete evidence.
- Future research backlog: on a user-owned rooted Chromecast, investigate the
  original device-authentication/certificate lifecycle so the project need not
  depend on AirReceiver-derived research forever. This does not block release.
  Research must remain bounded to owned hardware and must not publish secrets.
- User would prefer distributing the currently extracted authentication material.
  Publication is NOT approved by this plan: distinguish public certificates from
  private TLS/device/authentication keys, establish rights and security impact,
  and keep private material outside Git/artifacts until that review is resolved.
  Support a replaceable private runtime bundle meanwhile.

### Immediate sequence

1. [done] Consolidate this plan and record/analyse the AirPlay incident.
2. [done] Complete code/architecture review; see
   `docs/architecture-review-2026-09-19.md`.
3. [done, awaiting discussion] Present recommended core/adapter boundary,
   repository layout, minimal config, packaging, maintenance/diagnostics and HA
   deployment sequence with trade-offs.
4. [mostly done] Agreed refactors: supervisor, static output registry,
   versioned output-control return path, maintained Vibecast fork, historical
   Python separation and operational APIs. The first four local code changes
   are complete in dev12. The maintained fork is now published at immutable
   commit `f28befe02fe930db300294d6bf49cdf5fec5a747` on branch
   `cast-audio-receiver-dev12`; the complete upstream patch remains a fallback.
5. [partly accepted] OCI/HA packaging and dependency automation exist. Complete
   CPython container/build artifact locks and offline verification are done. A
   secret-free local source repository passed real Supervisor build, install,
   ingress/LAN, restart and state-persistence checks. Published-image scan,
   install, update and rollback acceptance remain.
6. [done for the planned horizon] Certificate collection contains 773 distinct,
   gap-free windows through 2030-12-06. Independent reconstruction matched it
   byte-for-byte. The final bundle passed the real HA App import/start path while
   the previous input was retained for rollback. Future sender acceptance and
   redistribution rights remain separate, unresolved questions.

### Current release blockers and deferred hardware acceptance

- Prepare and review a clean public source export and Git history; do not publish
  the dirty research workspace or private bundle/state/log artifacts.
- Complete redistribution/source-notice review, especially the documented
  airplay-cli/libraop ambiguity, before shipping a combined public image.
- Publish, inventory/scan and test the intended image's update and rollback path.
- Run end-to-end AirPlay from the HA App on a physical target. Yamaha/other RAOP,
  HomePod/AirPlay 2, DLNA, Sonos, concurrent routes and smaller/ARM hardware stay
  explicitly unverified until those devices/platforms are available.
- Test receiver-origin controls with a real output and YouTube Music. The v2
  architecture carries them, but automated protocol coverage is not a physical
  compatibility claim.
- Only after the public repository is documented and usable, link it in relevant
  Music Assistant discussions with the experimental/revocable caveat.

### Dev12 architecture implementation — 2026-09-20

- **Done:** one `cast-audio-receiver` supervisor owns frontend then manager
  startup and manager-first bounded shutdown. The same entrypoint is intended
  for native Linux, OCI and the later Home Assistant wrapper.
- **Done:** static output registry owns target validation, singleton policy,
  backend construction and adapter arguments for local mpv and AirPlay.
- **Done:** player wire protocol v2 carries explicit output-origin play, pause,
  stop, seek, volume, next and previous requests. State reports remain
  observations. The Rust core applies canonical controls and forwards queue
  navigation to YouTube Lounge. Legacy v1 registration remains accepted but
  cannot inject v2 controls.
- **Done:** `/health`, `/status` and allowlist-only `/api/support`; support data
  excludes route names/IDs, target addresses/properties, URLs, media data,
  PIDs and credentials.
- **Done:** standalone Python Cast/DIAL/Lounge receiver moved to
  `research/legacy_python_receiver`; it is retained and tested but no longer
  installed or exposed as the normal runtime.
- **Implemented, hardware test pending:** direct-pull DLNA/UPnP and Sonos
  outputs are registered, configurable and covered by simulated-device tests.
  They deliberately do not add a proxy/transcoder yet; see
  `docs/network-outputs.md` for compatibility limits.
- **Done as development infrastructure:** amd64 OCI build recipe, thin Home
  Assistant ingress wrapper, CI, Dependabot and upstream release watcher.
  Complete Python runtime/build wheel locks now install offline with exact
  hashes. Publication, image SBOM/scan and real HA update/rollback acceptance
  are still open.
- **Done in packaging source:** Home Assistant repository metadata is at the
  Git root; `ingress_port: 0` uses Supervisor's collision-free allocation while
  a separate configurable `web_port` serves the trusted LAN. Options and the
  allocated port are read through the authenticated self-info API, avoiding a
  dependency on direct access to Supervisor's root-owned options file.
- **Verified:** 200 Python tests complete successfully (19 explicit environment
  skips in the current development environment). A clean dev12 wheel contains
  no historical modules, installs over the complete offline runtime lock and
  exposes the expected entrypoints. The
  targeted Rust gate passes 110 tests; one explicit live-network probe is
  ignored. No live household receiver was changed by these tests.
- **Home Assistant acceptance passed for the source-build path:** the laptop
  receiver stayed stopped; a generated secret-free test repository was accepted
  and built by a real HAOS/Supervisor. Install, root bootstrap, privilege drop,
  dynamic ingress, direct LAN health, App restart and persistent speaker ID/state
  passed. The final private 773-window bundle was supplied separately through
  `/share`, imported with mode 0600 and the Cast frontend returned ready.
- **Next:** publish/scan/inventory the intended image; test update and rollback;
  run physical AirPlay, DLNA and Sonos acceptance where targets are available.
- **Private source staging:** an allowlisted UTF-8-only export with per-file hash
  manifest excludes `.state`, generated artifacts, device captures, key/cert
  file types and known private host markers. The exported tree independently
  passes all 200 tests and was pushed as a new-history private GitHub repository
  at `Allcrafter1/cast-audio-receiver-lab`. CI is the next acceptance gate; this
  is not yet a public release or redistribution clearance.
- **Authentication distribution decision remains explicit:** the user requires a
  normally installed receiver to be functional with the complete bundle. Local
  and HA acceptance already satisfy that through the private `/share` input.
  Repository rules keep authentication material in ignored private state; public
  Git history/image inclusion requires a separate rights/security review rather
  than silently publishing reusable credentials. Packaging must make this split
  obvious and avoid presenting a nonfunctional install as complete.

## Certificate continuation — 2026-09-19

User requested detached resumption on the existing rooted A50. No old collector
running; device/USB/root/instrumentation/power checks passed. Revalidated current
479-window seed through2029-04-27, zero duplicates/gaps. New private job
`.state/airreceiver-a50/collection-resume-20260919` preserves the old failed
April27 artifacts. Two-window pilot extended verified coverage to2029-05-01
with restoration checks; detached continuation targets2030-12-06, not2033.
Pilot exited0 with481 unique certificates/no gaps. Automatic time and USB
stay-awake restored to1/0. Background supervisor371146 and collector371147
started19:25UTC; supervisor is reparented to PID1 with its own session, so SSH
disconnect does not own its lifetime. At handoff it is validating resume inputs;
do not claim further progress beyond the481-window pilot without new receipts.
See docs/certificate-continuation-20260919.md for monitoring and safe stopping.
Collection does not activate a new runtime bundle. Seventeen existing collection
and cryptographic-window regression tests pass; no capture algorithm changed.

Follow-up at 22:40 CEST: the detached run is no longer active. It extended the
validated merged inventory to 511 unique, gap-free windows through
2029-06-30T00:00:00Z, then stopped safely while validating the next window.
The future certificate was captured, the real clock was restored, but the
current-date AirReceiver relaunch did not return to `Ready To Cast` within the
bounded wait. The unvalidated 2029-06-30 attempt was not promoted to an `.ok`
receipt. Resume later only after the owned phone is unlocked and AirReceiver is
visibly ready; do not weaken that restoration gate.

Follow-up at 23:44 CEST: after the user unlocked the A50, AirReceiver was again
visibly Ready To Cast. The failed attempt remains preserved. A new private job
`collection-resume-20260919-2` passed a bounded one-window recovery pilot and
restoration, then promoted the first detached window: 513 distinct certificates,
zero gaps, verified coverage through 2029-07-04 UTC. Supervisor375472 and
collector375474 are detached in session375472 with the supervisor reparented to
PID1; target and first-failure policy remain2030-12-06. This is active collection,
not completion or runtime activation. See `docs/certificate-continuation-20260919.md`.

The next immutable checkpoint contains 527 distinct, gap-free windows through
2029-08-01. It was copied to the local ignored `.state` backup, hash-matched
against the test host and cryptographically revalidated locally. At that point
246 two-day windows remained to the 2030-12-06 target; collection stayed active.

Final collection result at 01:51 CEST on 2026-09-20: the resumed collector
completed with return code 0 and reached the requested 2030-12-06 endpoint with
773 distinct, gap-free windows. The temporary Samsung pocket-protection change
and USB stay-awake setting were restored (`1/0`), no collector remains active,
and the final checkpoint was copied and cryptographically revalidated in the
local private backup. No runtime bundle was activated.

Earlier read-only check on 2026-09-20: while the job was still active, its newest
immutable checkpoint contained 704 distinct, gap-free windows through
2030-07-21. This interim observation is superseded by the final 773-window result
above.

Independent follow-up: docs/RELEASE-CHECKLIST.md consolidates source/history
cleanup, licenses/credits, clean rebuild, private-input separation, hardware
acceptance and HA/Music Assistant release gates. No publication performed.

## 0.6.0.dev11 — shared Cast/HA artwork (2026-09-19)

Latest user feedback supersedes the earlier sound-quality investigation:
the distortion is an intentional effect in the recording, NOT a receiver bug.
AirPlay cover improvement is accepted. Retain dev10's independently reproduced
buffering/seek corrections; do not change audio encoding to address this report.

User explicitly authorizes reusing the cover solution for Cast/Home Assistant.
Implemented opt-in manager image serving and background adapter processing,
using the same converter as AirPlay. A narrow bridge artwork report updates
only a matching active cover without playback/position/queue changes. Cache:
32 JPEGs, one-hour lifetime, one converter and four pending distinct sources.
No new dependency, permanent worker or decoder/buffer change. Original image
URLs remain on failure; missing radio metadata is not manufactured.
See docs/artwork-dev11.md for behavior, known limitations and acceptance steps.

Verification: local Python suite157 tests completed (8 FFmpeg skips);
eight Rust crates158 tests passed, one live probe ignored; release build passed.
Fresh checkout + complete dev11 patch matches all109 source files. Linux full
suite passes all157 with no skips. All20 silent end-to-end image/DMR checks pass,
including real 640x360 → 360x360 conversion, HTTP serving and MEDIA_STATUS.
Initial remote compile used a stale
vendor directory; candidate moved to an isolated full-source checkout rather
than modifying interfaces to fit the stale build. Live dev6/dev10 remained
unaffected during that failed build.

Deployed frontend370709, manager370710, adapters370716/370717 from
`.state/manager-dev11`. Management API reports dev11, both enabled routes are
running and all three route records are byte-for-byte unchanged. Previous
launch inputs retained privately in that stage's rollback.json; previous
dev6 frontend and dev10 Python stage remain available. Frontend SHA256:
`33ec9b6be5942384fe19bae275fa4a93c2c975c28c17111c144503380fefd34c`.
Do not rerun the one-shot activation script. Normal Google-sender/HA visual
acceptance remains separate from these automated checks.

Next: HA visual acceptance; continue release documentation/provenance audit.
CONTRIBUTING.md now records setup, regression expectations, safe issue reports,
scope and attribution requirements. A dev11 Python wheel was built successfully,
SHA256 `02c3ffab5bbf24357e6413d13600abc4facd18ca7456a47f00a834d427b485c7`.
The running deployment remains the tested source stage, not an installed-wheel
claim. Build tools were isolated; runtime dependencies were not upgraded.
The prior certificate inventory remains479 validated windows through2029-04-27;
no new collection, key export or clock mutation in this iteration. Future
collection and final distribution review remain separate open tasks.

## 0.6.0.dev10 — AirPlay regression investigation (2026-09-19)

Dev6/dev9 wheel comparison confirms only artwork delivery changed in the
AirPlay adapter; backend and bridge files are identical. Historical Sep14 logs
show a source connection reset and 107.894 decoded seconds versus 186 expected.
This is not current evidence of device health or proof of artwork causation.
Two deterministic tests fail before the fix: repeated seek during BUFFERING
loses play intent; pause during BUFFERING is undone by STARTED. Both now pass.
The current cover file is reused for identical URLs within a transport, avoiding
repeated image fetch/conversion on seek. No audio codec/buffer changes.
152 tests complete successfully (8 skips) outside the socket-restricted sandbox.
Deployed to the existing manager stage with dev9 rollback files retained in
`.state/dev10-rollback` on the Linux host; manager restart returned PID363367.
All 27 targeted AirPlay tests also pass on that host. Audible quality and actual
seeking still require acceptance. Next test: Neuanfang, repeated forward/backward
seeks, pause while loading, resume, then a normal title transition. If distortion
persists, compare the same source with artwork disabled under controlled logging;
do not attribute a source reset or sound quality to cover conversion without it.


## 0.6.0.dev9 — shared lossless artwork cropper

`artwork.py` now exposes `prepare_square_artwork(source, output, ffmpeg)` as a
protocol-neutral converter. It accepts local files or FFmpeg-readable URLs,
center-crops to 1:1, removes only confidently detected symmetric embedded
letterbox bands, and writes one final high-quality JPEG (maximum 512px/1MiB).
The conversion uses a bounded lossless PNG intermediate, avoiding the previous
double-JPEG recompression that could make covers look soft. AirPlay is switched
to this shared helper; Cast/Home Assistant still need the separately approved
HTTP image-serving/URL-rewrite boundary before their status can reference the
processed bytes. Local suite: 149 tests, 8 explicit FFmpeg skips. The Rust Cast
frontend is unchanged; manager dev9 is live after restart (latest observed
manager PID338212 with adapters338213/338214), and the three saved routes are
unchanged. Receiver artwork rendering remains a manual acceptance item.
The remote FFmpeg smoke check passed on the synthetic padded cover (48×48
content after refinement, no temporary files left behind). The rebuilt wheel is
`cast_audio_receiver_lab-0.6.0.dev9-py3-none-any.whl`, SHA-256
`0088d02c8db49b9acb1a65663ca6f6765ecd7f9e6172c7a20851b1258218ac88`.
Replaying the saved 480×480 AirPlay source through dev9 produced a 360×360
JPEG of 57,516 bytes (the earlier double-encoded reference was 25,051 bytes),
with visibly better fine detail; byte size alone is not treated as a quality
metric.
The full converter measured 0.36–0.38 s on three remote CPU-only runs for a
synthetic 1024×600 source (network excluded); it remains off the audio start
path.

## 0.6.0.dev8 — artwork quality correction

The prior 1:1 geometry was correct, but FFmpeg's default JPEG quantizer caused
avoidable recompression loss. Both artwork conversions now use quantizer 2 while
retaining the existing bounds. The policy remains shared in `artwork.py`; AirPlay
uses it today. Cast/Home Assistant still need a separately approved image URL
serving path before their metadata can point at processed bytes. Superseded by
dev9's lossless intermediate; the dev8 manager deployment was the baseline for
the current candidate.

## 0.6.0.dev7 — AirPlay embedded-cover refinement

The active AirPlay path now refines its existing 1:1 JPEG only when a 64×64
preview shows symmetric full-width black edge bands (2–16 rows). It then crops
both dimensions equally to remove the embedded letterbox and side padding.
Ambiguous images remain unchanged; the helper is bounded to 4 seconds/1 MiB,
and subprocesses are killed/reaped on cancellation. 144 local tests pass.
The active saved cover was independently inspected before/after: 480×480 with
embedded bars became a visually filled 360×360 square. Dev7 was deployed as
manager337583 with adapters337584/337585; the three routes and validated Cast
frontend remain unchanged. Dev8 then improved JPEG quantization in the same
manager stage. AirPlay receiver rendering still needs user acceptance. Cast/Home
Assistant image URL normalization remains a separate architecture item.

## Latest user acceptance and priorities

User confirms HA terminal status now works perfectly; mark that dev6 acceptance
case PASSED. Web UI/favicon accepted. SWR3 starts and stops, but title/cover
metadata are absent in HA; sender metadata versus stream metadata must be
distinguished from a receiver propagation bug. File progress remains uncertain.
Normal casting retains cover/progress. AirPlay geometry is now accepted by the
user, but quality was reported low; dev9 removes avoidable double-JPEG loss.
Inspect actual generated image and delivery after deployment, not only the
synthetic filter tests. User requests square covers for Cast/HA too. Shared
serving/URL rewriting remains to be designed and verified; no implementation or
deployment claim yet. Preserve working playback/cleanup.

Next manual artwork check: compare one known album on the AirPlay target after
dev9. If it is still soft, record the generated pixel dimensions and source URL
variant first; the previous inspected cover contained only 360×360 content
inside a 480×480 letterboxed image, so an algorithm cannot recover missing
detail. A later decision between requesting a larger source variant and a
controlled 512px upscale should be evidence-based rather than silently changing
the no-upscale policy.

## Post-dev6 tooling and adverse-network checks

No runtime or route change. `support_inventory.py` previously lost the entire
report when an explicitly selected binary was missing/unreadable. New fixed-label
per-binary errors retain the other inventory fields without exposing exception
paths. Two regressions fail before and pass after. Local suite141 tests passes
with four explicit FFmpeg skips.
Linux installed-package suite also passes all141 with no skips. Live dev6 manager
and both enabled adapters remained running without restart; route state unchanged.

The silent DMR fixture now includes a server withholding response headers. Actual
mpv accepts a newer valid LOAD and then STOP of another stalled LOAD, followed by
relaunch and disconnect. All18 checks pass against deployed dev6, without a
runtime fix. This verifies cancellation of the initial stalled HTTP request,
not reconnection after a mid-stream outage or every radio-server behavior.

## Current deployment — 0.6.0.dev6 audio media category

Silent real-mpv regression on the deployed dev5 binary fails because audio/wav
is returned as VIDEO. Candidate changes only explicit audio/* MIME categories
to AUDIO, including the initial loading status. Ambiguous DASH/HLS and missing
types retain the existing fallback. No decoder/resolver/buffer change.
30 core tests pass. Historical incremental supplement:
`patches/vibecast-after-dev5-audio-category.patch`, applied after dev5 complete
(independent of the observer test supplement). Debug and release binaries pass all17 silent real-mpv
DMR checks, including new LIVE-labelled load/play/pause and no-seek advertisement.
The finite LIVE-labelled fixture tests control policy, not continuous radio or
ICY extraction. Old dev5 fails the new audio-category assertion as expected.
Complete dev6 snapshot includes both supplements and reconstructs all109 build
files exactly, also matching the remote build source. Python dev6 wheel passes
all137 tests in both hash-locked environments: CPython3.12 has three FFmpeg skips;
CPython3.13 on Linux has none. Seven-crate Rust gate passes (one live probe ignored).
Deployed frontend334663, manager334664, adapters334670/334671 under
`.state/manager-dev6`; all three route configurations are unchanged, both enabled
adapters registered, Chromium management check passes. Frontend SHA256
`0507ada0d334dc6f690f2e15fdbb0cde33dd98264168456f34e30b1964264c64`.
Python wheel SHA256 `624404e438bfa1cc17277d40399a4456bedf5c7a241819061234ac9d8bd3fd08`.
Private dev5 rollback retained. Deployment's first stop waiter raced process exit
and interrupted manager restart; bounded recovery handled disappearing /proc
entries and completed deployment. This was a deployment-script issue, not a
receiver failure. Do not rerun either one-shot script. Google-sender/UI/audio
acceptance of dev6 remains pending; synthetic tests do not replace that gate.

Post-deployment test-only expansion: MP3 and FLAC generated from bounded synthetic
PCM now each pass all17 real-mpv DMR checks against the exact deployed binary.
WAV remains the default; `--fixture-format` selects other fixtures. No decoder
or installed runtime changed for this extension. Local Python suite now139 tests
(four explicit FFmpeg skips); Linux installed-wheel suite passes all139 with no
skips. Real radio/HTTPS/ICY and hardware acceptance remain
separate. This closes the synthetic MP3/FLAC gap, not all generic app compatibility.
Read-only post-restart resource sample: four processes, 114656KiB RSS and
83473–83518KiB PSS, 0–0.958% of one CPU core across five one-second intervals.
No mpv child yet: not comparable to the older five-process post-playback sample,
not a memory optimization claim, not loading peaks or small-device acceptance.

## Previous deployment — 0.6.0.dev5 metadata preservation

Dev5 ran with the validated 479-window bundle, retained unchanged in dev6.
New silent DMR test reproduced metadata loss on the previous dev4 binary: music
metadataType3 becomes generic0 after LOAD; artist/album disappear on the same path.
Additive correction preserves typed sender metadata through the existing SDK,
player bridge and Cast status; Python passes artist/album to the existing backend
fields. YouTube/other app providers retain their legacy metadata path (None),
and older player consumers can ignore the optional new object. No new dependency,
extractor change, image server or artwork URL rewriting.
138 Rust tests pass (one explicit live YouTube probe ignored), 134 Python tests
pass on Linux, and 14 silent real-mpv DMR cases pass, including both returned
Cast metadata and output artist/album. The built Python wheel also passes the
134-test suite in the fresh hash-locked environment (three local FFmpeg skips).
Live frontend326405, manager326406, adapters326412/326413; `.state/manager-dev5`.
Three routes retained, live Chromium UI check passes, old dev4 rollback retained.
Frontend SHA256 `4a2679d02f9e967bee46120a6ab98b3ee86268e222140dadb44cf0f71de36ff4`.
Single complete dev5 patch/source lock reproduces all109 files and matches the
remote build source. No Google-sender acceptance claim from the silent test.
This does not prove SWR3 supplies any missing field, nor implement ICY updates.

Post-deployment test-only follow-up: a separate Cast monitoring connection now
has a regression proving owner socket loss sends IDLE/CANCELLED, clears the app
list and permits the observer to launch a new session.29 core tests pass.
No runtime change needed. The source supplement is
`patches/vibecast-0.6.0.dev5-observer-test.patch`, applied AFTER the complete dev5
patch; the deployed binary/source lock still describes the original dev5 build.
Current working/test source differs by this test-only supplement. Future full
snapshots must include it. Added version/patch/wheel-record gates: Python suite
now137 tests, three local FFmpeg skips; Linux original environment all137 pass.
Separate CPython3.13 Linux x86_64 artifact lock also verified: fresh offline
installation, pip check and all137 tests pass against the installed dev5 wheel,
with no FFmpeg skips. Live dependency environment remains unchanged. ARM and
extractor/build-tool locks remain open; the CPython3.13 gap below is historical.

## Autonomous continuation — 0.6.0.dev4 deployed

This section supersedes conflicting task statuses in historical entries below.
The user is asleep: do not wait for manual tests; record them and continue safe
independent work. Preserve existing architecture and tuning decisions.

- **Deployed dev3:** terminal MEDIA_STATUS before session teardown, receiver
  refresh after transport disconnect, generic LOAD field-presence diagnostics.
  Frontend SHA256 `a7e8f5e5ad7d6592c8e17216e723bd4f93f2cbaaf47c80fb0fe2e3c85a3b6b98`.
  26 core tests and 13 isolated real-mpv DMR cases passed. This also contains
  the installation-ID startup race fix. HA/YT terminal-state acceptance remains
  a manual gate; it is not established by synthetic DMR testing.
- **Deployed dev3 UI:** delete, prevent duplicate local output, favicon, list
  refresh, LAN/no-login. Three existing routes retained; no live route deleted.
- **dev4 deployed:** user chose centered **1:1** artwork. AirPlay conversion
  crops before bounded scaling, no padding/upscale. Three real FFmpeg image
  tests pass on Linux; Cast/HA artwork still uses original URLs and is OPEN.
- **Resource diagnostics:** read-only RSS/PSS/interval-CPU tree sampler added;
  no persistent worker or extractor/format/buffer behavior change.
- **dev4 additional status fix:** app-channel CLOSE now refreshes platform
  application status without waiting for a socket disconnect or GET_STATUS.
  Regression fails before and passes after. 135 Rust tests pass, one explicit
  live YouTube probe ignored. All 129 Python tests pass on Linux; three FFmpeg
  tests skip locally. Thirteen isolated real-mpv DMR cases pass with silent PCM.
- **Deployment:** frontend initially PID320893, now PID320979 after bundle
  activation; manager PID320894, adapters320900/320901;
  `.state/manager-dev4`, original three routes unchanged, both enabled adapters
  registered, live Chromium UI check passes. No audible test initiated.
  Frontend hash `43b19e23c847a3ebd6a6560d1333abd3074b695b85150b45582e54124815dc19`.
  Previous dev3 source/binary/config and launch inputs retained for rollback.
- **Reconstruction:** single complete dev4 patch + source lock. Fresh clone,
  local working source and remote build match all 109 inventoried files.
  This is not a hermetic build or completed license/security audit.
- **Collection status corrected:** PID281243 has exited. Last successful
  checkpoint report is bundle-0200: 479 distinct windows, no gaps, through
  2029-04-27 UTC, one public key. Following pilot failed. Independently revalidated
  all 479 entries for key/signature/chain consistency; no duplicates or gaps.
  Thirteen silent real-mpv DMR cases pass with this larger bundle. Activated
  `.state/vibecast/certs-through-2029-04-27.json`; every prior full entry retained
  unchanged, previous bundle kept for rollback. Both adapters reconnected.
  This does not prove future Google acceptance. Collection itself remains stopped
  before the intended 2030 horizon. Failure log says UI not Ready To Cast;
  clock restoration/readiness were recorded. No new phone/clock/network mutation.
- **Dependency/package follow-up:** 17 exact CPython 3.12 Linux x86_64 wheels
  downloaded, hashed, installed offline into a fresh environment; pip check
  passes. Current wheel built and installed separately with all four UI assets.
  Three wheel-inventory tests raise the local suite to132 (three FFmpeg skips).
  CPython3.13/ARM and extractor/build-tool artifact locks remain open.
  Credits/notices inventory added; upstream license ambiguities remain a release
  gate, not silently treated as resolved by the project's GPL choice.
- **Confirmed sender limitation:** extreme rapid selection order also fails on
  Nest Audio. Do not reopen heuristic reordering without new receiver evidence.
- **HA evidence:** CC1AD845/default_media launch observed in the correct log;
  user reports successful media-library playback. SWR3 and local file are the
  specific metadata/control cases; no separate verified TTS claim is made.

### Immediate independent work and deferred acceptance

1. Done: dev4 test/staging/deployment/rollback records; square AirPlay artwork,
   diagnostic tooling and focused app-CLOSE lifecycle/status regression.
2. Done: complete dev4 source reconstruction and current runbook; historical
   standalone README/build instructions explicitly marked as historical.
3. Inspect radio/DMR metadata propagation and artwork path; avoid inventing
   sender metadata, duration or seek support. A new shared image-serving layer
   is a structural decision, not a trivial crop change.
4. Improve reproducible tests, source/dependency/license inventory and developer
   install/update instructions. Public release and HA packaging remain gated by
   full provenance/redistribution audit and real target acceptance.
5. Later manual tests: HA status after leaving YT Music; SWR3/local-file metadata
   and controls; rendered square AirPlay cover; receiver-origin feedback;
   simultaneous real outputs; Yamaha and HomePod/AirPlay 2 compatibility.

Existing publication, credits, AI disclosure, Music Assistant announcement,
configurable HA web port and deferred-project requirements below remain intact.

## 0.6.0.dev3 — execution update

DMR LAUNCH CC1AD845/default_media confirmed in correct live log at17:28:44 UTC.
User clarifies stale HA PLAYING mainly after ending YT Music; radio/file end-state
is unconfirmed. SWR3 and local file are metadata/pause test cases.
Terminal MEDIA_STATUS teardown regression fails before fix and passes after;
26 core tests pass. Rust build, 13 isolated DMR tests and deployment completed.
LOAD field-presence diagnostics deployed for sender-versus-receiver distinction.

UI deletion, duplicate-local creation guard, favicon and cross-browser list refresh
implemented and deployed0.6.0.dev3. All three existing user routes retained;
no user route deleted.121 Python tests and live Chromium UI check pass.
Details: docs/ha-status-and-ui-dev3.md. Radio metadata/control fix and artwork
normalization remain open pending evidence; no behavior changes claimed there.

## Vollständig konsolidierter Projektstand — 2026-09-13

Diese Liste ist die maßgebliche Zusammenfassung der bisher besprochenen Ziele,
Entscheidungen und offenen Punkte. Frühere Abschnitte bleiben als Verlauf erhalten.

### Bereits umgesetzt

- Audio-only Google-Cast-Empfänger auf Linux mit der bestehenden authentifizierten
  Frontend-Kette, YouTube-Music-Unterstützung, Play/Pause, Seek, Lautstärke,
  Warteschlange, automatischem Titelwechsel, Disconnect und Reconnect.
- Schnelle Titelwechsel- und Queue-Behandlung inklusive Prefetch, Koaleszierung
  doppelter Auswahl, Abbruch überholter Resolver-Vorgänge und sauberem Cleanup.
  Die verbleibende Fehlreihenfolge bei extrem schnellem Tippen wurde auch auf
  echten Nest-Audios beobachtet und ist daher möglicherweise senderseitig.
- Persistenter AirPlay-Ausgang über cliairplay/FFmpeg mit Lautstärke, Pause,
  Seek, Queue/EOF, Artwork-Grundsupport und dauerhafter Verbindung. Redmi-
  RAOP-Test ist bestätigt; Yamaha, weitere Receiver und HomePod/AirPlay 2 fehlen.
- Default-Media-Receiver-App-ID `CC1AD845` im aktiven Rust-Pfad für einzelne
  HTTP(S)-`LOAD`-Medien. HA-Mediathek-URLs und TTS/URL-Wiedergabe wurden als
  funktionierender Pfad beobachtet; die konkrete letzte HA-Session braucht noch
  eine Logkorrelation, weil der Frontend-Log keine ausreichenden Payloads enthält.
- Speaker-Manager auf dem Linux-Testhost, direkte LAN-UI ohne Login, stabile
  IDs, gespeicherte Speaker, getrennte Prozesse, Umbenennen und Aktivieren/
  Deaktivieren. Beide vorhandenen Ausgaben sind migriert und nach Neustart sichtbar.

### Jetzt zu prüfende Fehler und Funktionslücken

- Streamende im Cast-/DMR-Pfad: tatsächlichen Übergang zu `IDLE`/`STOPPED` und
  anschließende Befehlsfähigkeit gegenüber Home Assistant prüfen; veraltetes
  `PLAYING` darf nicht stehen bleiben.
- Radio-/Live-Streams aus Home Assistant: vom Sender gelieferte Dauer, Metadaten,
  Artwork, MIME/Live-Kennzeichnung und Play/Pause erfassen und nur vorhandene
  Informationen korrekt zurückmelden. Keine künstliche Duration oder Seekbarkeit.
- Artwork vereinheitlichen: Original-Seitenverhältnisse und Protokollgrenzen
  messen, schwarze/bunte Balken vermeiden, sinnvolle quadratische bzw. begrenzte
  Varianten für Cast, AirPlay und HA erzeugen, ohne unnötige Qualitätsverluste.
- DMR-Queue- und Mehrformatgrenzen klar testen: aktuell einzelne URL-LOADs,
  `QUEUE_LOAD` bewusst nicht vollständig; MP3/FLAC/HTTPS/Radio/Artwork/Duration
  und Fehlerfälle mit HA und mindestens einem weiteren Sender prüfen.
- Receiver-zu-Sender-Rückkanal: Lautstärke, Mute, Play/Pause, Seek und Trackstatus
  in YouTube Music/HA testen; Feedback und echte Zustandsänderung getrennt bewerten.

### Speaker-UI und lokales Deployment

- Löschen von Speakern mit Bestätigung, sicherem Stoppen des zugehörigen Prozesses
  und Entfernung der privaten Target-Datei implementieren.
- Doppelte lokale/mpv-Ausgaben verhindern; vorhandene lokale Route eindeutig
  wiederverwenden oder eine verständliche Meldung anzeigen.
- Favicon/eigenes Browser-Icon ergänzen und UI-Fluss weiter vereinfachen.
- LAN-Bindung ohne Login beibehalten; Port bleibt konfigurierbar. HTTP ist nur für
  vertrauenswürdige lokale Netze vorgesehen.
- Mehrere parallele Ziele mit echter Audioausgabe, Isolation, Stop/Restart und
  Ressourcenverbrauch reproduzierbar testen.

### Zertifikate und Wartung

- Private Zertifikatsfenster-Sammlung auf dem gerooteten A50 bis zur vorgesehenen
  Abdeckung fortführen, ohne Geräteuhr dauerhaft zu verändern.
- Für jedes Fenster Fingerprint, Gültigkeit, Public-Key-Zuordnung, Duplikate und
  Lücken prüfen; sicherstellen, dass nicht versehentlich immer dasselbe Zertifikat
  verwendet wird. Der aktuelle Collector läuft unabhängig weiter.
- Dokumentieren, welche Cast-/TLS-/Device-Identity-Bestandteile benötigt werden,
  woher sie stammen, wie sie erzeugt/rotiert werden und welche Annahmen fragil sind.
  Google kann die verwendete Identität jederzeit widerrufen; eine lange Laufzeit
  ist nicht garantiert.
- Private Schlüssel und gerätespezifische Geheimnisse bleiben außerhalb eines
  öffentlichen Repositories. Veröffentlichung kann nur öffentliche Artefakte,
  reproduzierbare Erzeugungs-/Installationsschritte und klar getrennte private
  Bundle-Inputs enthalten.
- Wartungsworkflow: bei Ausfall Logs und Versionsinventar sichern, Cast-/YouTube-
  Änderung von yt-dlp/Dependencies abgrenzen, Upstream-Changelog und Diff prüfen,
  isoliert testen, neuen Build erzeugen, Rollback bereithalten und erst danach
  live aktualisieren. Relevante Libraries, Upstream-Projekte und Research mit
  Version, Quelle und Lizenz nachvollziehbar dokumentieren.

### Home Assistant, Veröffentlichung und Beiträge

- Einfachen Installations-/Update-/Rollback-Prozess bauen und anschließend als
  Home-Assistant-App/Add-on/OCI-Paket ausliefern. Web-Port, State-Verzeichnis,
  Discovery, Healthchecks und Supervisor-/cgroup-Prozessbesitz konfigurierbar machen.
- Vor GitHub-Veröffentlichung Repository bereinigen, Secrets/private Logs/States
  entfernen, Source-/Lizenzprüfung abschließen, ausführliche README und Troubleshooting
  schreiben und fragile Google-Cast-/YouTube-Komponenten ausdrücklich markieren.
- README muss Architektur, Installation, Konfiguration, Dependencies, bekannte
  Grenzen, Wartung, Updateprozess und Testmatrix erklären. Alle tatsächlich
  verwendeten Projekte, Libraries und Research-Arbeiten deutlich creditieren und
  sich für deren Vorarbeit bedanken.
- KI-Unterstützung transparent dokumentieren: wesentliche Teile wurden gemeinsam
  mit GPT/Astra entwickelt, Anforderungen/Architektur praktisch erarbeitet und
  getestet; erfahrene Entwickler sollen den experimentellen Code kritisch reviewen.
  Contributions sind ausdrücklich willkommen.
- Nach öffentlicher, dokumentierter Veröffentlichung auf bestehende Music-
  Assistant-Requests/Diskussionen hinweisen. Keine eigene direkte Music-Assistant-
  Integration versprechen; Maintainer dürfen Code reviewen, übernehmen oder daraus
  eine saubere Integration entwickeln. Lokales Multiroom bleibt eine mögliche
  spätere Anwendung und wird jetzt kein eigenes Teilprojekt.

### Bewusst außerhalb des aktuellen Umfangs

Spotify-spezifischer Cast-Support trotz Spotify Connect, Google-Home-Adoption und
Google-Cast-Gruppen, Bluetooth, ESP32-Port, WiiM-Voice-Integration, permanenter
Worker-Pool, aggressive Format-/yt-dlp-Optimierung und ein vollständiger Ersatz
aller dienstspezifischen Web Receiver. Diese Punkte bleiben dokumentierte Optionen
oder mögliche Contributions.

## Aktueller Stand und Reihenfolge — 2026-09-13

Erledigt und live geprüft: Linux-Cast-Empfang für YouTube Music, mpv- und
persistenten AirPlay-Ausgang, Lautstärke/Play/Pause/Seek/Queue/Disconnect,
Speaker-Manager mit direkter LAN-UI auf dem Linux-Testhost, stabile IDs,
gespeicherte Laptop- und AirPlay-Route sowie Start/Stop/Umbenennen/Neuladen.
Die UI zeigt die beiden vorhandenen Speaker direkt ohne Login. 119 Python-Tests
und ein Chromium-Bedienungstest bestehen. Die Audio-Prozesse laufen unter dem
Manager; der Rust-Cast-Frontend-Prozess bleibt separat.

Als Nächstes in dieser Reihenfolge:

1. **Live-Regressionscheck:** Nutzer prüft YouTube Music mit beiden sichtbaren
   Routen; danach Android-Lautstärketasten, gespeicherte 50%/0%-10%, Rückmeldung
   vom Empfänger und zweiter Sender.
2. **AirPlay-End-to-End:** Yamaha/weitere RAOP-Ziele sowie HomePod/AirPlay 2,
   Artwork, Duration/Position, Queue-Übergänge und parallele Ausgaben prüfen.
3. **Cast-Kompatibilität:** Default-Media-Receiver und Registry für standardisierte
   Apps untersuchen; mit realen Android-Apps testen. Spotify bleibt wegen Spotify
   Connect außerhalb einer eigenen Cast-Sonderimplementierung. TIDAL, Qobuz,
   Pocket Casts, BubbleUPnP und Plex sind Kandidaten, keine Zusage.
4. **Wartbarkeit und Veröffentlichung:** vollständigen Rust-Neubau, Python-/CLI-
   Constraints plus plattformbezogene Hash-Locks, Source-/Lizenz-Audit,
   Versionsinventar, Update-/Rollback-Anleitung und reproduzierbare Release-Artefakte
   abschließen. Erst danach Repository öffentlich machen oder Music Assistant
   informieren.
5. **Home Assistant:** OCI/App- bzw. Add-on-Paket mit persistentem State,
   konfigurierbarem Web-Port, Discovery-/Netzwerkdokumentation, Healthchecks und
   sauberer Supervisor-/cgroup-Prozesszugehörigkeit bauen.

Parallel laufend: Die private Zertifikatsfenster-Sammlung auf dem gerooteten A50
läuft unabhängig weiter. Sie wird erst nach Validierung als austauschbares,
privates Bundle betrachtet; Schlüssel werden nicht veröffentlicht. Noch offen
sind außerdem Receiver-zu-Sender-Befehle, Ressourcenprofile auf kleiner Hardware
und die Entscheidung, ob die verbleibende schnelle Titelwahl tatsächlich vom
Sender (wie beim Nest-Test beobachtet) oder von uns verursacht wird.

Bewusst zurückgestellt: Google-Home-Adoption/Gruppen, Bluetooth, ESP32-Port,
WiiM-Voice-Integration, Worker-Pool, aggressive Format-/yt-dlp-Optimierung und
eine Spotify-Cast-Sonderlogik.

## 0.6.0.dev2 — direct LAN management and existing-route migration

User explicitly requests no management authentication. Removed token creation,
validation, CLI toggle, Authorization headers and login/connect UI. Default bind
0.0.0.0:8788; page fetches routes immediately. Same-origin and JSON/body checks
remain without credentials. Updated management regression tests pass (11).
Actual old manager state contained no routes.json; Laptop/AirPlay ran separately.
Migrated both using original UUIDs and existing RAOP target into routes.json,
preserving audio environment and frontend storage. Manager PID311139 initially,
children311140/311141 connected to frontend. Rollback backup is private under
.state/manager-dev2-migration-backup. Deployed source .state/manager-dev2-src.
Live Chromium browser test passed: direct entry, both existing speakers visible,
rename followed by page reload, disable/enable, original name restored, no JS errors.
Manager restart verified persistent routes and enabled state: PID311568,
children311569/311570. All119 Python tests pass. Listening0.0.0.0:8788 verified;
no new audio quality claim. Browser tools/libraries stayed in development cache,
not runtime dependencies. The user can test directly on the configured LAN port.


## 0.6.0.dev1 — approved speaker management implementation

User approved the route-manager/Web-UI proposal and aiohttp dependency. Implemented
private atomic versioned route config, stable UUID/name separation, explicit
discovery/import (disabled initially), per-route process supervision/backoff,
rename/enable/disable UI and authenticated loopback-only API. Rust frontend and
working live0.5.0 adapters are unchanged. New development version is not deployed.
See docs/speaker-management.md for launch, migration and exact limitations.

Eleven focused tests pass in the isolated management environment, including real
two-child isolation/restart, HTTP security and secret-free target import. JavaScript
syntax check passes. Full regression passes119 tests. A0.6.0.dev1 wheel builds
successfully with isolated build dependencies. Tested runtime dependency versions
recorded as constraints, not a wheel-hash lock. Remaining next steps: remote verification,
temporary registration, deliberate existing-ID migration, browser and real
multi-output acceptance/resource measurements. No forced takeover of live adapters.
Certificate collector last read-only process check: PID281243 still active;
no new coverage/deployment claim or phone changes this iteration.


## 0.5.0 user acceptance and source reconstruction

User confirms deployed YT Music playback/controls/disconnect/reconnect remain
working. Stock DMR/HA sender acceptance and receiver-origin YT UI controls remain
separate; do not infer them from that confirmation.

Added read-only source_inventory.py and3 tests. Compared Linux/local: same base,
five files differed (speaker capabilities/names and auth diagnostic fields).
Recovered those existing deployed changes locally, preserving playback semantics.
New complete0.5.0 patch plus source lock replaces the need to reconstruct from
historical partial patches. Fresh checkout+patch matches109 build-source hashes.
Reconstruction tests exposed an existing first-start identity-file race: initial
read could see the concurrently created file before UUID write, bypassing the
existing retry used by the create loser. Added the same bounded retry to initial
parse failure, plus an empty-file/delayed-writer test. No identity overwrite or
new dependency. Candidate patch is patches/vibecast-after-0.5.0-installation-id.patch
(apply AFTER complete0.5.0). Candidate source passes133 Rust tests,1 explicit live
probe ignored, using shared Cargo cache; not hermetic/bit reproducibility.
The running0.5.0 binary/source on the original build path remain unchanged;
candidate tested only in clean-source staging and local source. Build host uses
rustc1.98.1 from checkout's stable toolchain;
shell default1.87 fails locked dependency requirements. Documented cwd selection.
108 local Python tests:107 passed,1 optional bridge test skipped (previously
passed on Linux). Details: docs/source-reconstruction.md.

Collector read-only check still runningPID281243; last receipt2028-08-22.
No credential deployment, phone manipulation or receiver restart this iteration.
Next structural block proposed: route manager/small Web UI, documented in
docs/route-manager-proposal.md. New aiohttp dependency and managed child-process
ownership require user agreement before implementation. Certificate job continues
independently; don't interrupt it for route work. Other open gates stay recorded.

## 0.5.0 deployed — DMR and bridge restart regression

Active frontend PID293360, mpv adapter293301, AirPlay adapter293302 on Linux.
Both adapters now use complete `.state/dmr-1/src` source0.5.0. Cast ports at
last registration: Laptop39503 / AirPlay33543 (dynamic; rediscover after restart).
Same stable player IDs/names/routes and private six-window certificate bundle.
Frontend hash remains47b2c33040a79d3603aa4750ed8c02cccb6db43e205b3628ffabb054699cf7bf.

Isolated development-sender tests through real mpv and Redmi RAOP6000 passed:
HTTP audio, autoplay=false/initial position, paused seek, play/pause, sender
volume, backend-origin volume feedback, rejected queue preserving playback,
natural EOF, deliberate404, subsequent valid load, STOP, relaunch, disconnect.
Tool: tools/test_default_media.py; private temp frontend/OS-assigned ports and
quiet local WAV fixture; owns and shuts down its processes. No Google-sender
device-auth verification performed by this test, so stock acceptance remains open.

Initial test sender omitted required mediaSessionId/sessionId fields; corrected
the test, NOT receiver semantics. Also corrected the Rust live-seek test to
check specific rejection with a syntactically valid request (passed on Linux).
Snapshot regenerated/reverse-apply checked; runtime Rust build unchanged.

Real frontend restart exposed ConnectionClosedError terminating both adapters.
Small catch/reconnect fix added. Real WebSocket regression fails before and passes
after; old playback stopped and same identity registers again.105 local tests:
104 pass,1 skips because local venv lacks existing optional bridge dependency;
that test passes on Linux. Both actual adapters then survived another frontend
restart and re-registered automatically. This is not a full process supervisor.

Collector remains independentPID281243; last observed receipt through2028-06-25.
No phone manipulation, bundle replacement, publication or new dependency.
Next gate: user YT Music playback/skip/disconnect/reconnect on deployed build;
real HA/default-media sender acceptance separate. Collection final validation
and deployment still pending. Then receiver-origin YT controls, reproducible
source/dependency/license audit, route UI/multi-output and HA package as below.

## DMR implementation in verification — 2026-09-13

Added active Rust provider for CC1AD845, registered for both platform bindings.
Single-item HTTP(S) LOAD preserves contentUrl/identity, existing metadata,
autoplay and initial position without yt-dlp. Invalid sources/timing fail;
unsupported DMR QUEUE_LOAD explicitly fails without changing playback. LIVE
sources do not advertise seeking and seek commands are rejected (no DVR model).
Seven provider tests and core queue-rejection/recovery/live-seek tests added.
104 Python regressions pass; remote Rust tests pass:7 provider,25 core,15 platform
(also repeated after formatting),43 YouTube tests with1 explicit live probe
ignored. Source snapshot saved as patches/vibecast-dmr-1-snapshot.patch;
cumulative for included files, not a complete standalone lab build.
Not deployed yet; no real DMR sender acceptance claimed. Runtime remains0.4.9.

Read-only collector check: PID281243 active, latest receipt coverage end
2028-05-04 UTC. This is progress, not final horizon or deployed coverage.
Do not interfere with the phone while the independent job is running.

Release build succeeded (offline/locked,2m17s). New binary SHA256
47b2c33040a79d3603aa4750ed8c02cccb6db43e205b3628ffabb054699cf7bf.
Previous binary preserved remotely in .state/dmr-1/vibecast-before-dmr.
Build replaces the file at target/release/vibecast but NOT the running process;
an explicit future restart would select the new build. No restart performed.
Snapshot reverse-apply check passed against the matching source.

Next: isolated
direct-URL playback/controls/error tests before changing the live frontend.
Receiver-origin controls, real AirPlay hardware matrix, route UI/multi-output,
reproducibility/license audit and HA packaging remain open as recorded below.

## Collection recovery and parallel audits — current result

User unlocked A50; reference receiver Ready To Cast again. Repeat March21 capture
succeeded offline and matches previous same-date certificate. 278 original entries
were278 distinct certs/windows sharing one public key, not duplicated captures.
Patched bounded readiness retry, separate restoration log, USB keep-awake restore,
inventory duplicate diagnostics;103 regression tests plus support inventory test
pass (104 total). Two-window resume pilot passed,281 unique windows/no gaps through
2028-03-27. Old failure artifacts kept. New independent background continuation
in `.state/airreceiver-a50/collection-resume-20260913`, PID281243,
log background-run.log, target2030-12-06; verify
PID/progress before future phone work. Active receiver bundle is STILL the small
six-window bundle; validated larger deployment remains open after collection.
Details: docs/certificate-readiness-audit.md. No simultaneous phone experiments.

Maintenance workflow drafted, support_inventory.py implemented (versions/hashes,
no logs/URLs/keys). Need full clean Rust rebuild and complete dependency locks
before release automation. DMR remains planned single-item LOAD provider; broader
QUEUE_LOAD semantics require separate scope. Verified HA URL/TTS use case;
Android brands remain test candidates. No Spotify-Cast expansion.
Read-only inventory verified on Linux: imported adapter0.4.9 while installed
distribution metadata still0.4.0; tool deliberately reports both. cliairplay hash
matches pinned asset. Source-based dev installs need cleanup before release.


## Publication and maintenance requirements (user-approved)

Prepared docs/PROJECT-ORIGIN.md, docs/maintenance.md and
docs/default-media-receiver-plan.md. These are drafts/implementation plans, not
claims of public release or complete update automation. DMR initial scope can
serve direct HTTP(S) audio/TTS from HA without a new external dependency, but
upstream QUEUE_LOAD is incomplete: explicitly reject unsupported queues rather
than advertise complete generic app compatibility. Android app brands still
require actual app-ID/command tests. Full rebuild/lockfile audit remains open.

- Detailed architecture, installation, dependencies, limitations, operations,
  troubleshooting and update/rollback documentation before public release.
- Transparently explain development with AI, particularly GPT/Astra: initiator
  had practically no programming experience; requirements, behavior and
  architecture discussed together, implementation extensively tested in practice.
  Invite experimentation/review without implying professional audit or stability.
- Credit all actually used upstream projects, researchers and prior work clearly;
  retain applicable notices/licenses. No invented endorsements or unused credits.
- Mark fragile Cast authentication, YouTube extraction/control and device-specific
  compatibility explicitly. Reproducible pinned releases, diagnostic version
  inventory and focused regression tests support log-driven maintenance.
- Speaker management and small web UI; explicit imports and loop prevention.
- Multiple parallel output targets/receivers: concurrency, isolation and resource
  tests, persistence of names/IDs/routes/volume, reconnect and shutdown.
- Then OCI/Home Assistant App/add-on: configurable external web-interface port
  to avoid collisions, durable private state, health diagnostics and rollback.
- Open source and contributions welcome. No direct Music Assistant integration
  planned: experienced maintainers may review/improve/adapt this experimental work.
- Only announce to Music Assistant AFTER repo is public, documented and usable;
  no external post or repo publication currently authorized by this planning step.
- DMR welcome if bounded integration supports standard senders; Spotify-specific
  Cast implementation not required. List evidence-backed candidates vs untested.
- Current priority: reference receiver readiness and distinct certificate audit,
  accounting for phone now online; preserve failures and restore network/time.


## Product status audit after 0.4.9 user acceptance

User confirms persistent AirPlay works. GitHub API authenticated as Allcrafter1;
local repo has no remote, no upload performed. DMR CC1AD845 exists in historical
Python protocol/tests but is not registered in current Vibecast app providers;
active-path DMR integration and acceptance remain next feature work. Upstream
browser player is not a route-management UI. Routes currently explicit JSON plus
one external-player process per target, ID derived from target device identity.
No managed updater or Home Assistant App package yet.

Collector status audit: PID250663 exited; failed window2028-03-21 because app UI
not Ready To Cast. Latest bundle-0276 revalidated:278 windows, no gaps,
2026-09-12 through2028-03-21 UTC, chain expiry2032-12-14. Active bundle-0004 still
six windows through2026-09-24. Phone clock checked against Linux, within seconds.
Collection has NOT reached2030 horizon and is NOT running. Investigate stopped
pilot before resume, retain failure artifacts; no restart/deployment in this
read-only status audit. Collected validity does not guarantee sender acceptance.

Product priorities: finish certificate collection/validated deployment; active
DMR path and tests; clean reproducible repo/build with secret/license audit;
route manager and UI, multi-route resources/failure tests; real Yamaha/HomePod
acceptance and receiver-origin controls; OCI/HA App with persistent data,
network guidance, health checks, version-pinned updates and rollback.


## AirPlay 0.4.9 — persistent transport requested and implemented

User confirms 0.4.8 functions correctly, explicitly requests persistent mode.
Default now retains cliairplay and its stdin. Track-scoped decoder/artwork/progress
tasks are stopped separately. FLUSH ack separates old/new audio; Python buffered
tail requires drain plus second FLUSH. Acks/drains bounded; failure reconnects.
Next decoder starts only after barriers. STOP/disconnect still tears down all.
Completion uses valid decoded PCM count and upstream elapsed_ms (audible lag
already subtracted). Silence tail keeps the clock advancing with stdin open.
Paused/unstarted tracks and duplicate/old EOF cannot finish. Metadata duration is
only the existing truncation sanity check, not the completion timer.
Elapsed reports arrive approximately once a second: end notification can lag
by that interval; this implementation does not claim gapless AirPlay transitions.

100 local tests pass. Physical Redmi RAOP6000 first test passed pause, paused
seek, manual next, natural completion and short remainder with exactly one
connection (PID280479), six acknowledged flushes. Test utility
tools/test_persistent_airplay.py is opt-in, emits quiet tones, owns/cleans helpers.
Second physical test also passed with one connection PID280555 through all warm
transitions; killing that test-owned helper was followed by successful cold
recovery PID280600 and completed playback. 24 staged Linux tests pass. Deployed
0.4.9 as AirPlay adapterPID280615, bridge connection confirmed; no rollback flag.
YT Music user acceptance pending: skip/seek including paused, auto next, artwork,
volume and disconnect. Actual audible transition quality requires user feedback;
synthetic tests check transport/state behavior, not a microphone recording.
Rollback: --airplay-reconnect-on-load restores per-track connection/EOF behavior.
No new dependency, upstream fork, main mpv change or collector interference.


## AirPlay 0.4.8 — progress/artwork and failure evidence

User confirms automatic/manual next on 0.4.7. Remaining: inconsistent AirPlay
progress/duration, premature next, occasional failed load and missing artwork.
Logs: sorry at16:34:55/16:35:09 decoder warning then EOF without audio event;
JPG at16:40:41 and Nero at16:44:40 warning before EOF/next. Old diagnostics are
redacted too aggressively to identify network/format cause; not proven fixed.
Count PCM seconds vs expected remainder (3s tolerance), reject truncated/empty
successful decoder exits as ERROR, not FINISHED. Add fixed-label diagnostics,
sender-exit reporting, periodic duration/progress after streaming readiness.
HTTPS artwork now fetched using existing FFmpeg (8s timeout, 512px, <=1MiB),
delivered asynchronously as local ARTWORK, canceled/reaped before temp cleanup.
91 local tests and 15 isolated Linux bridge tests pass. Real HTTPS image fetch
on Linux produced a 13946-byte JPEG and issued the mocked ARTWORK command (not
proof of receiver rendering). Patched staging deployed, AirPlay adapter restarted
gracefully with SIGINT as PID280110. User progress/artwork acceptance pending.

Persistent transport is user-preferred and upstream-supported, but NOT enabled.
Required order: stop old pump; drain Python writer; FLUSH with bounded ack;
only then start new decoder and START. Keep stdin open. Reconnect on failed ack.
Natural completion must use decoded sample count plus actual playout progress,
including pause/seek; stdin EOF no longer represents individual track boundaries.
Test this separately before replacing current end-of-track path. No blind timer
based solely on advertised metadata duration. No new dependency/Upstream fork.
Sources: airplay-cli v0.5.3 README, src/ap2_session.c, src/artwork.c and pinned
libraop raopcl_set_progress. Artwork/EOF fixes intentionally separate from warm
session work so regressions can be attributed. Main mpv and collector untouched.


## AirPlay 0.4.7 — state / EOF / progress

User confirms 0.4.6 reconnect, disconnect, manual skip, volume, play/pause and
direct selection. Automatic next, transition position and AirPlay duration fail.
Implemented PCM EOF forwarding plus guarded upstream drained-EOF -> FINISHED;
BUFFERING freezes new/seek position through START acknowledgement; PROGRESS
triggers upstream duration/progress transmission. No metadata for the next title
is sent to the previous pipeline. 88 local tests pass; hardware acceptance pending.
Source checked: music-assistant/airplay-cli v0.5.3 src/cliairplay.c,
PROGRESS dispatch and RAOP/AP2 EOF drain branches. Upstream drain has a fallback
latency+2s timeout: this iteration does not promise gapless automatic transitions.
Still reconnects on load/seek by design. Warm FLUSH/refill/START requires separate
agreement and transport/decoder boundary tests; not silently implemented here.
Artwork and receiver-origin feedback remain open. Local mpv path unchanged.
Deployed airplay.py into isolated staging and restarted only AirPlay adapter as
PID275632; bridge connection confirmed. Await user end/skip/seek/duration test.


## AirPlay 0.4.6 — skip cleanup fix

User confirmed actual Cast-to-AirPlay playback and fast pause/play. Subsequent
skip stalled; adapter remained alive without children or target connection.
Fix decoder pipe backpressure during teardown: cancel original pipe readers,
drain output with bounded-memory readers and bound terminate/kill waits. Send
terminal STOP on load teardown too. New real-subprocess regression exercises
full decoder stdout and repeated cleanup. 86 local tests pass.
Deployed patched airplay.py to isolated staging; restarted only AirPlay adapter
as PID272611. Physical skip/reconnect acceptance remains pending user test.
Still open: artwork delivery, explicit track progress metadata, audible EOF and
automatic queue advance; do not equate initial playback with these being done.


## AirPlay 0.4.5 — direct audio confirmed, Cast test ready

User supplied a Redmi with two AirReceiver AirPlay modes. Discovered
Teufel(Audio) RAOP6000 and Teufel RAOP/AirPlay7000 separately. Select6000 first.
Fixed --txt argument grouping and dedicated RAOP capability forwarding (especially
et=0,1 instead of upstream's0,4 fallback triggering an invalid-free auth-setup
path).85 tests pass. Direct FFmpeg/cliairplay test tone is USER-CONFIRMED audible.

Started separate **Audio Lab AirPlay** adapterPID269116 on existing Vibecast
bridge, logs/config under `.state/airplay-redmi-20260913`. Active laptop mpv and
Samsung collection untouched. This is not full Cast->AirPlay acceptance yet.
Next user test: select Audio Lab AirPlay in YT Music and play, then pause/resume,
volume and seek. Examine EOF/automatic next separately; known older backend
status/EOF limitations have not been fixed by this plumbing step.
Details: docs/airplay-045-redmi-test.md.7000 mode remains a subsequent separate test.

## Next independent work: AirPlay 0.4.4 wiring

User requested next task while collection runs. SSH status check confirms
collectorPID250663 alive and receipts through2027-05-16 (not final horizon).
Do not interrupt phone or change the live mpv output for this work.

Implemented: active Vibecast player CLI can select existing AirPlay backend via
explicit JSON route; target ID independent of Cast display name. Partial/cancelled
startup cleanup, RuntimeError containment, muted startup and adapter exit cleanup.
No protocol rewrite or new dependency. New version0.4.4; hardware acceptance still
pending. Details and config example: docs/airplay-044-integration.md.

Verified:84 Python tests locally,9 new bridge tests on physical Linux in isolated
`.state/airplay-0.4.4-staging`. Live mpv source/process not switched. Agreed unified
cliairplay dependency provisioned locally under `.state/airplay-tools/v0.5.3`,
published digests checked and `--check` passed; GPL license/notices retained.
Pin in config/cliairplay-linux-x86_64.lock.json. No global install/privilege changes.
Next physical AirPlay test requires an explicitly selected available receiver
(IP, advertised RAOP/AirPlay port/device ID; pairing if applicable).

Order still open:
1. Finish/verify full certificate collection; final manifest deployment and real
   rotation/reconnect check (no Linux clock changes).
2. AirPlay upstream binary/CLI verification and real target E2E: controls, remote
   feedback, audible EOF/queue advance, position, teardown/reconnect and latency.
3. Generic Default Media Receiver audit/acceptance, receiver-origin commands,
   routing/import loop prevention and Home Assistant App packaging.
Avoid claiming that wiring an existing backend proves AirPlay playback/feedback.

## Active collection and deployment — 2026-09-13 12:53 UTC

- User confirmed offline identity connection/audio. Live sequential capture and
  resume both passed; six contiguous windows through Sep24 installed in Linux.
- Runtime: Controls-17, receiverPID250763, playerPID250768, Cast40679; manifest
  `.state/airreceiver-a50/collection-20260913/bundle-0004.json` on USBIP server.
  Fresh local challenge verifies signature; today's TLS window remains Sep12–14.
  Prior offline-current-next.json and original current-both.json retained.
- Background collector PID250663 is RUNNING independently of SSH, targeting
  continuous coverage through 2030-12-06. Job directory is the same collection
  directory above; collection-run-01.log, run-01.pid, per-window receipts and
  immutable bundle checkpoints. It has already progressed beyond the deployed
  prefix. Do not claim the entire multi-year collection is finished.
- Before touching phone/time again: inspect collector; do not run concurrent
  experiments. To pause safely create job/STOP and wait for stopped_safely or
  collector exit; current pilot restores phone before the next loop boundary.
- Per-phone exclusive lock, independent 90s phone watchdog, restore after EACH
  pilot, private artifacts, identity/signature/key/gap validation, external power
  and conservative <42C battery-temperature guard. First error stops collection
  for investigation; no automatic deployment of unreviewed output.
- Horizon: Dec4–6,2030 captured successfully; Dec6,7,29,31 and Jan2031/Dec2032
  fail before TLS setup. This is an observed app generation boundary, not Google
  sender rejection and not intermediate expiry. Exactly1800 days from Jan1,2026
  suggests 900 two-day entries; precomputed inventory remains a hypothesis.
- APK raw/base64/hex signature scan had no hits. Bounded live native heap scan
  found today's signatures but not last-window signatures; not proof of absence
  in encrypted/compressed storage. Keep proven sequential path running.
- 14 synthetic tests pass (including resume, failure protection, power/thermal
  guards), Python compilation and shell syntax checks passed.

Next: monitor job and investigate any failed pilot; verify final contiguous
manifest before installing it. Real midnight rotation / reconnect remains a
manual future test; do not alter the Linux host clock. AirPlay E2E follows the
certificate milestone, not a broad receiver refactor.

## Certificate milestone: offline identity user-confirmed

2026-09-13: user confirms connection and playback work as before with the deployed
offline-current-next.json. Sender acceptance gate passed for today's window.
Continue bounded future-window investigation/collection; this does not establish
future acceptance or coverage beyond the actual collected windows.

Further probes: Jan2030, Jul2030, Oct2030 and Nov2030 succeeded; late Dec2030,
Jan2031 and Dec2032 failed before a TLS context was installed. This is not an
observed sender rejection. Exact generation horizon still being narrowed.
New sequential collector uses independently restored pilots, checks every window,
resumes from verified receipts and writes immutable private checkpoints. No live
manifest mutation by the collector. 13 synthetic tests pass, including resume and
failure-no-advance. Live batch validation follows before a long collection.

Update: Jan14–16,2027 sample also captured successfully. Dec2032 TLS handshake
failed twice; no exact upper limit established. No coverage claim beyond Sep16,
2026 for the active test bundle. The user's real sender acceptance test of this
DIFFERENT identity has now passed. Detailed findings and
rollback: docs/certificate-offline-breakthrough.md. Original phone network,
automatic time and preference XML restored; no background collection running.

2026-09-13: user suggested offline mode. With Wi-Fi disabled, mobile data disable
requested, no observed default routes and USB forwarded Cast access, Sep15 produces
a new Sep14–16 TLS certificate. Offline identity DIFFERS from online; same Gen1 ICA,
device leaf expires2034, chain still Dec14,2032. Do not assume Google acceptance.
Current-date offline launch keeps old material until ONLY cks2 preference is
temporarily omitted. This produces a today-valid certificate matching the new
offline identity. Original XML/network/time are restored after each pilot.

Two windows verified (TLS keys, both signatures, device->ICA signature), merged
without gaps into private offline-current-next.json covering Sep12–16. Linux
Controls-17 now uses this TEST manifest: receiverPID248477, playerPID248482,
Cast port41965. Live local probe confirms valid TLS-only signature. Old
current-both.json untouched; rollback is same binary/args with --certs restored.
Asked user asynchronously for real YouTube Music connection/playback test NOW,
before collecting years under a potentially rejected identity. Five new merger
tests passed. Horizon pilot for Dec2032 follows while awaiting user test.

## Latest certificate follow-up: Start button checked

User's START warning confirmed: open port8009 alone does not establish UI-ready
state. Pilot now explicitly presses START and verifies Ready To Cast after launch.
Sep15 test still returns identical Sep12–14 certificate. Native observation also
confirms the app's libc time sees Sep15; exported read/SSL installation calls occur,
no observed X509_sign call. Not conclusive about earlier/alternative generation.
Exact live cert not found raw DER/PEM in native library. Future capture remains
unresolved; do not classify duplicated material as coverage or replace Linux bundle.
See docs/certificate-window-pilot.md; next investigate material selection/source,
not simply repeat app restarts or scale up date shifting. Phone time/UI restored.

## Latest certificate pilot: collection attempted, no extension achieved

2026-09-13 user-authorized rooted A50 trials: baseline, Sep14, Sep15, and Sep15
with reversible isolation of app_cast/config.json all return the same Sep12–14
TLS window. Date after restart was verified for Sep15. Both later-date trials
fail validity acceptance; no future entries deployed and Linux bundle untouched.
Device/intermediate expiry: Sep25,2033 / Dec14,2032 respectively. Do not promise
either as coverage. Clock/automatic settings and original config restored.
Details, private artifact roles, safety limits and next investigation in
docs/certificate-window-pilot.md. New capture_future_window.py is a bounded pilot,
not a validated multi-year collector. Do not start a large sweep until an actual
new window is obtained. Current installed TLS ends Sep14,2026 00:00 UTC.

## Controls-17 cleanup and next milestone

Verified: 43 YouTube + 8 security unit tests passed (one explicit YouTube live
probe ignored), four Python player tests passed. Release built and Controls-17
deployed; prior binary retained at .state/controls-17-rollback/vibecast-controls16.
Cumulative two-file snapshot patches/vibecast-controls-17-cleanup-snapshot.patch
contains Lounge source and security tests, not a complete standalone receiver.

User reproduced the same rapid-selection failure on Nest Audio. Close this
investigation as a known shared limitation, not proof of theoretical impossibility.
No further special filtering or identical manual tests planned; ~1s UI spacing
works. Retain working latest-load cancellation and narrow queue-addition handling.

Cleanup: remove temporary nowPlaying POST stopwatch/ack reports; move command and
selection/coalescing traces to DEBUG and gate diagnostic JSON construction behind
DEBUG enabled. Preserve regression and diagnostic-redaction tests (test-only code
is not part of release execution). No playback semantic change.

Next milestone audit: CertificateStore already supports time-window selection;
manager polls every60s and updates TLS/auth/discovery. Gaps return NoValidCert;
manager logs an error and keeps the old bundle, so this is NOT fail-closed expiry
handling for live endpoints. Existing validity selection checks peer certificate
dates, not a promise of complete-chain future acceptance. Do not mark certificate
coverage complete from store tests. Add synthetic boundary/gap/clock-rollback test
without touching system time or obtaining any new credential material.
Longer-term private bundle coverage/validation remains before AirPlay; planned
phone clock experiments have NOT been performed during cleanup.

## Controls-16.1: regression boundary, no new runtime policy

User reports approximately one second between UI selections works; do not equate
this with wire arrival spacing (prior burst messages were already ~1s apart).
Avoid forced timing heuristics for the extreme-speed edge case.
Added reconstructed state/feedback regression: additions insert at index1 while
Zerrissen remains index0, including one after playback starts; queue, nowPlaying
video/index, playing status and position stay correct. A following VIDEO_SELECTED
remains accepted, documenting the unresolved boundary rather than a claimed fix.
43 YouTube tests passed, one explicit live probe ignored. Test-only source change;
running Controls-16 unchanged, no rebuild/restart or new manual test required.

Useful next experiment, if investigating this edge case further: same phone/app,
same fixed title sequence on reference receiver, both rapid and ~1s between taps,
and no input after final title. Compare success/failure before changing receiver
feedback or trying a command-origin correlation. If reference also fails, that
supports a sender/shared-protocol limitation; it does not prove impossibility.
If reference succeeds consistently, inspect its feedback/event correlation.
Do not repeatedly request identical tests on unchanged code without new evidence.

## Latest finding: Controls-16 partial success, explicit follow-up selection

Fixed-order user test: Zerrissen plays briefly, then Katz & Maus. At 11:38:23.896,
24.686 and 25.701 UTC all three VIDEO_ADDED events were correctly normalized;
the active Zerrissen identity/slot/list guard succeeded even after playback began.
Zerrissen committed at 11:38:25.286. At 11:38:27.659 seq37 a new VIDEO_SELECTED
explicitly selected Katz & Maus at index1; it committed at 11:38:28.562.
Thus this is NOT a failed guard or stale resolver completion. Controls-16 remains
partial, not confirmed as resolving rapid selection. Do not broaden suppression
to VIDEO_SELECTED indiscriminately: that would break legitimate queue selection.
Next investigate correlation of this follow-up with the earlier user action or
reference receiver feedback; present logs do not distinguish delayed selection
from a deliberate new tap. No additional speculative runtime change this turn.

## Latest: Controls-16 VIDEO_ADDED selection preservation

Fixed manual test order for future runs (user request): Du wirst mir fehlen ->
zehnvonzehn -> Alles was ich hab -> Katz & Maus -> Zerrissen. Expected final
selection Zerrissen. Controls-15 reproduction instead played Katz & Maus.

New evidence: 2026-09-13 11:30:52–11:31:03 UTC: the five genuine selections are
PLAYLIST_SET, followed by VIDEO_ADDED for the first four titles. Our parser
previously discarded eventType and loaded all these as fresh selections.
Controls-16 conservatively normalizes VIDEO_ADDED to UpdatePlaylist ONLY when
the existing active title remains at its current index in the same non-null list.
This happens before CurrentMedia changes and command dispatch; report preserved
selection back to sender. VIDEO_SELECTED/PLAYLIST_SET remain authoritative.
No blanket event suppression, history blacklist or debounce. If the guard cannot
establish unchanged active identity/slot/list, retain previous behavior.
Unit regression covers four delayed additions, genuine reselection, loading and
playing, different list, changed slot, and initial empty state. See
docs/controls-16-queue-additions.md for build/deployment/manual verification status.

## Latest: Controls-15 event correlation preparation

User confirms slower selection works; the remaining failure is an intentionally
rapid burst. Do not change working cancellation, seeking, cleanup or volume.
Controls-15 adds bounded eventType/eventVideoCount diagnostics and outgoing
nowPlaying selection/ack timing. No selection filtering is enabled.

Prepared fix decision: if delayed events can be identified as updates of an
obsolete selection, reject their playback side effect BEFORE handle_internal
changes CurrentMedia or broadcasts nowPlaying, as well as before resolver dispatch.
Do not merely suppress playback.load: that would leave feedback/queue inconsistent.
Require an unambiguous correlation rule first; arrival sequence, eventDetails
presence, queue growth, and title previously selected are insufficient individually.
Do not add a blanket debounce that delays every normal selection.

Acceptance cases: rapid A/B/C then delayed A update keeps C; explicit C->A is
accepted; legitimate queue insertion/selection still works; pending same-title
enrichment, automatic Next, seek and disconnect remain intact. If wire events
cannot be distinguished, document that limitation instead of guessing user intent.
Next capture needs one deliberately rapid burst and the final intended title.
Build/test/deployment status: see docs/controls-15-event-correlation.md.

## Current investigation — Controls-14 selection diagnostics

Latest user reproduction (TOD, then the named five-title sequence): raw input
confirms Zerrissen at 13:14:12.733, sequence 26. Later sequences 28/30/32/34
explicitly select older titles; raw videoId, eventVideoId and indexed queue ID
agree. Final seq34 selects Du wirst mir fehlen and that loads at 13:14:18.597.
Thus neither missing Zerrissen input nor a parser ID/index mismatch nor stale
resolver completion explains this trace. Later eventDetails-bearing setPlaylist
messages, with growing queue length/index, displace the user's latest intent.
Investigate delayed queue enrichment/correlation and receiver feedback causality
before suppressing messages. Do not blanket-ignore eventDetails or assume these
are new user taps. No behavior change is justified by their presence alone.

User confirms Controls-13 improves rapid selection and that automatic Next,
connection, disconnect and reconnect still work. Occasionally an earlier desired
title plays. The sender disables pause/seek UI while loading; do not treat this
as a receiver defect or request that manual test again.

Analyzed session 7942df04, 2026-09-13 13:04 local: repeated incoming setPlaylist
messages supersede earlier resolutions. Last parsed selection is OjzHimoVml4,
and that is what loads (zehnvonzehn). No late old resolver completion explains
this particular burst. Existing logs did not retain raw videoId/eventVideoId
versus indexed queue selection, so sender intent versus parser interpretation
remains unresolved. Do not declare the sender at fault or change selection
precedence speculatively.

Controls-14 adds allowlisted raw-vs-parsed selection fields with incoming sequence,
and an explicit resolved-selection commit log. Playback semantics unchanged.
Next user test: rapid 3–4 selections and name the final intended title; compare
wire fields, accepted selection, cancellation and commit. Only fix semantics once
the mismatch is evidenced. TLS milestone remains before AirPlay after this gate.
See docs/controls-14-selection-trace.md.

## Current execution status — Controls-13

User approved cancellation refactor; implemented and deployed. 77 Rust unit
tests pass across YouTube/core/player API, plus the explicit live two-title
resolver probe and four Python player tests. Known metadata fixture failure is
resolved by isolating the existing audio metadata path from live extraction.
User functional regression and burst-load resource measurements are pending.
Next: rapid A/B/C selection, loading pause/seek, prepared/automatic Next,
disconnect/reconnect. Then the required TLS-window/rotation milestone before
AirPlay. Do not infer UI success or audio gaplessness from unit tests.
Details, resource sample and rollback location: docs/controls-13-cancellation.md.

## Latest decisions after Controls-12 user verification

- Android hardware volume buttons are now user-confirmed working. Controls-12
  subscription fix is accepted; retain volume regression coverage.
- Scope is NOT complete Google speaker emulation: prioritize excellent YouTube
  Music, add a generic Default Media Receiver, evaluate native alternatives before
  any additional service adapter. Other services may be community contributions.
- Plex music: evaluate official Plexamp Headless/Companion before custom Cast.
  TIDAL: prefer TIDAL Connect where supported, but availability on retail hardware
  does not establish a freely embeddable Linux receiver implementation.
- Worker/pool, format racing, shared probe bytes and metadata consolidation remain
  deferred. Do not reintroduce them as part of cancellation.
- TLS future-window coverage and rotation validation are a required pre-AirPlay
  milestone, not an optional post-AirPlay task.
- Current documented capture covers only Sep 12–14, 2026 UTC. No multi-year
  collection is established. Intermediate expiry documented as Dec 14, 2032;
  inspect actual complete chain rather than promising a horizon from the leaf.
- Immediate sequence: agree bounded cancellation refactor -> implement/test ->
  queue regression -> TLS coverage/rotation milestone -> Cast readiness audit ->
  AirPlay end-to-end. Default Media Receiver is an explicit expansion milestone,
  not an implicit prerequisite for the current YouTube-only readiness claim.

### Cancellation design — approved; Controls-13 implementation

Inspection confirms run_commands awaits resolution inline and resolver uses
spawn_blocking around a synchronous external process. Dropping only an async
task neither keeps commands flowing nor guarantees subprocess cleanup.

Proposed scope: retain architecture and extractor arguments; change the command
loop to select between new commands and one replaceable pending load result.
Track pending selection identity/start/pause intent. A newer distinct selection
invalidates old completion; Stop/disconnect cancels immediately. Adopt a matching
prefetch without restarting it. Cancel obsolete speculative work before starting
new foreground work. Use an owned asynchronous child/process-tree lifecycle,
timeout, termination and reaping; assess existing Tokio process support before
adding any dependency. No worker pool, format behavior or metadata-source change.

Tests required: A slow/B fast, A/B/C burst, late old failure/success, duplicate
selection, pause and seek while loading, Stop/disconnect, automatic Next and
prepared Next, no helper-process leaks. Also verify normal controls stay fast.
User approved the bounded refactor. Controls-13 now implements interruptible
foreground resolution, pending pause/seek intent, duplicate selection coalescing,
prefetch reuse and asynchronous extractor supervision. Existing Tokio process
feature enabled; no worker or new library added. Linux cancellation kills the
owned process group and the supervisor reaps the direct child. Detached helper
zombies, if any, are the system init/subreaper's responsibility; tests verify no
helper remains running. Deployment and live resource/function checks tracked in
docs/controls-13-cancellation.md. Do not mark sender regression complete from
controlled resolver tests alone.

### TLS milestone acceptance criteria

Inspect current private bundle validity and collection tool without printing keys.
Verify test phone identity/connectivity and capture starting automatic-time/timezone
settings before any mutation. First run a bounded future-window pilot with reliable
clock/settings restoration; validate certificate/key/signature/chain consistency.
Only then decide collection horizon/stride, handle interrupted runs, detect gaps,
and test receiver bundle rotation/time boundaries. Offline verification does not
guarantee future Google acceptance. Existing tool captures one window and does not
change system time; multi-window automation/rotation are still open. No clock
change or new material collection performed in this planning iteration.

### Autonomous work rule

After each completed task reconcile this plan and continue obvious low-risk
follow-ups/tests. Ask before substantial refactors, dependencies, architecture
changes or material trade-offs. See project AGENTS.md for persistent instructions.

## Decision audit — Controls-12 (2026-09-13, supersedes older priorities)

This is the authoritative current plan. Older sections below are experiment
history, not a request to reintroduce rejected optimizations. The early Python
receiver roadmap and native-frontend authentication-failure notes describe older
stages; the active tested path is Vibecast -> Python adapter -> persistent mpv.

### Implemented / retain

- Linux Cast speaker discovery and YouTube Music playback, local mpv output.
- Play/pause, seek, queue advance, pending duplicate-load coalescing and cleanup;
  confirmed in user tests, remain regression requirements.
- Parallel Rust metadata and checked yt-dlp audio resolution.
- Audio-9/10 next-known-item preparation, TTL and selection matching; user reports
  excellent transitions. This is NOT cancellation of foreground rapid selections.
- Controls-11 actual volume plumbing and per-device saved level/mute, with 0%
  promoted to unmuted 10% on a new session. Android hardware-button feedback
  remains a reported issue, not fully verified fixed.
- Modular backend boundary and early cliairplay/FFmpeg adapter/discovery code.
  This is NOT a proven end-to-end Vibecast -> AirPlay product.

### Active fix / next tests

1. Controls-12 separates receiver-0 subscriptions from app-session subscriptions.
   Previously an app CONNECT with the same sender ID replaced the platform
   subscription, suppressing device-wide status during an active session.
   Media SET_VOLUME also now publishes receiver status. Regression test reproduced
   the missing reply on Controls-11; Android UI verification follows deployment.
2. Test Android hardware buttons repeatedly up/down, reopen controls, reconnect,
   stored 50%, stored 0% -> 10%, and direct backend/HA volume feedback.
3. Recheck pause, seek, new queue, disconnect and second-sender takeover.

### Open, explicitly restored: newest selection wins

run_commands currently awaits foreground resolution before receiving further
commands. Selecting A -> B -> C rapidly can therefore wait for obsolete work.
This was missing as a separate actionable item in the previous recap.

Required next implementation, separate from the volume regression:
- Keep consuming control/selection events while resolution is in flight.
- A newer distinct selection invalidates/cancels the older resolution and starts
  promptly; never play an old result after the new selection.
- Bound work, prefer foreground over speculative next-item extraction, do not
  launch an unbounded race or retry an unchanged slow title repeatedly.
- Cancel and reap the external extractor PROCESS TREE, not just its Tokio task.
  Current spawn_blocking + timeout can continue until timeout after task abort.
- Preserve coalescing of duplicate pending selection, queue updates, pause/seek
  intent during loading, and immediate Stop/disconnect cancellation.
- Tests: delayed A/fast B, A/B/C burst, stale success and stale failure, repeated
  same selection, teardown, no orphan helpers, prefetch handoff and resource cap.

### Deliberately keep unchanged / defer

- Keep format validation, including the slow-title safeguard. No parallel format
  racing now; do not remove validation or force a codec as a latency shortcut.
- Keep separate mpv opening; no shared probe-byte proxy/streaming layer.
- No persistent yt-dlp worker/pool now. Reconsider only with target-device RAM
  and startup measurements; no worker prototype in the current work package.
- Keep Rust metadata and yt-dlp extraction separate and parallel; no consolidation.
- Keep startup buffering. No more aggressive minimum-buffer tuning.

### Subsequent product work, not lost

- Generic Cast compatibility: audit native app registry/default-media support;
  test app IDs, LOAD/GET_STATUS, errors, volume, metadata/artwork, queues and EOF.
  Do not claim every app available or compatible based on a speaker flag.
- Android test candidates: Pocket Casts, BubbleUPnP/local media, TIDAL, Qobuz;
  Plex and Spotify separate service-specific evaluations. Source links in audit doc.
- Wire the working frontend to cliairplay; actual Yamaha/other RAOP target test,
  HomePod/AirPlay 2 pairing and reconnect, volume feedback and output delay.
- Persistent receiver IDs independent of editable names (current default ID is
  name-derived), configured routing, rename UI/config, opt-in discovery/import,
  loop prevention against reverse bridges such as AirConnect.
- OCI/Home Assistant App packaging, persistent state, network/discovery docs,
  health diagnostics and reproducible dependency/patch versions.
- Receiver-side play/pause/volume/seek/track commands back to YT Music; distinguish
  feedback of actual state from sending a new queue command.
- Small-device per-process RSS/PSS/CPU profiling, concurrency/cache bounds.
- Isolate live yt-dlp from resolver fixture unit tests (known DASH/HLS test issue).
- Later reference-app system-time/TLS-material investigation remains separately
  recorded below; not performed in this iteration.
- Google Home adoption/groups, Bluetooth, ESP32 port and WiiM voice integration
  are not current implementation scope. Virtual/local grouping is a later route.

### Immediate order

Controls-12 Android verification -> newest-selection cancellation -> regression
of the successful queue behavior -> AirPlay end-to-end. Generic app compatibility
audit can precede implementation, but is not permission for a browser-runtime rewrite.

## Previous priority snapshot (superseded by the decision audit above)

1. Controls-11: verify volume feedback after reopening sender controls, 50%
   across disconnect/reconnect and process restart, and saved 0% -> 10% on a
   new session. Test direct receiver-side volume changes and mute separately.
2. Retain Audio-10 next-item preparation (already implemented and user-confirmed).
   Retest queue transitions, seek, pause and cleanup after volume changes.
3. Discuss rather than implement parallel format fallback, a persistent extractor
   worker and consolidation of Rust/yt-dlp metadata. Preserve validation and buffer.
   See architecture-review-11.md for measurements, limitations and recommendations.
4. Later, separate investigation requested: reference receiver app certificate
   behavior with changed system time on the user's test device, including whether
   the needed TLS material can be obtained. Validate scope, completeness and
   redistribution rights; do not assume long-term acceptance. Not executed here.

Controls-11 test caveat: the old resolve_returns_inline_dash_manifest test calls
the live external extractor and can return HLS instead of its expected fixture
DASH result. This is not a volume regression; isolate external extraction from
unit fixtures in a separate test-maintenance change. Do not hide it as a pass.

## Confirmed baseline

- Cast audio speaker discovery, playback, volume, seeking and session cleanup work in user tests.
- Audio-6 format availability checks fixed qXCwga3LUO0 in the user's test.
- This title now loads noticeably slowly; do not remove the availability safeguard blindly.

## 1. Duplicate new-queue starts — confirmed fixed

Observed two distinct Lounge setPlaylist sequence numbers arriving about 100 ms
apart for the same selected video, before the first resolution completes. Both
are processed serially as loads, so the second restarts playback seconds later.

Normalize a repeated selection during an outstanding load into a queue update
when selected video, index and start position match. Preserve queue contents and
list identity. Do not suppress a new title, changed start position or replay
after the pending-load phase. Apply normalization before both feedback and the
playback command queue so their states agree.

Test coalescing and exclusions, deploy, then ask user to select a new song from
quick selection. Verify one player load, no restart; also verify Next and seek.

Controls-7 implementation completed: normalization runs before both internal
Lounge state updates and playback dispatch. Focused regression test passes;
the existing Lounge test suite also passes (nine tests). Release build succeeded
and Controls-7 was deployed to the laptop. User confirmed the duplicate start
is fixed; later logs show pending selections coalesced correctly.

## 2. Loading latency — after duplicate-start verification

User target: 2–3 s for a fresh selection, under 1 s for prepared Next. Account
for AirPlay buffering separately; file-loaded timestamps are not audible-onset
measurements. Audio-10 fixes missed preparation for same-queue setPlaylist
advances and removes HTTP-ACK waiting before local command dispatch.
See docs/audio-10-transition-latency.md for evidence and verification needs.

User confirmed Controls-7 removes the duplicate start. Latency is now active.
Measured baseline: ordinary resolution 3.1–3.7 s; qXCwga3LUO0 about 9.4 s;
player file-loaded usually 0.1–0.25 s after load.
Audio-8 runs independent metadata retrieval and checked audio extraction in
parallel, with per-stage timings. No format checks or quality selection removed.
Expected benefit is overlapping metadata latency, not eliminating extraction.

Opt-in live Rust resolver test passed: b7l31agg58g 3.102 s,
qXCwga3LUO0 8.389 s. These are single samples, not a controlled benchmark;
network variation prevents attributing the entire difference to this change.
Resolver snapshot: patches/vibecast-audio-8-resolver-snapshot.patch is cumulative
against vendored upstream and must not be stacked on older resolver patches.
Release build and nine Lounge regression tests passed; Audio-8 deployed to
the laptop. Next: sender-side title changes and review the new stage timings.

Measure separately: Lounge arrival, resolver/format checking, player load and
first audible playback. Investigate redundant extraction and format-check cost.
Preserve working fallback for media URLs returning 403. Avoid permanent URL
caches: signed URLs expire. Optimize only against measurements.

## 3. Regression / documentation

Audio-9 now prepares one known next queue item in the background. Details and
limitations: docs/audio-9-prefetch.md. Test Next after allowing preparation,
automatic track advance, queue replacement, and session teardown. Direct
new-queue selections intentionally retain ordinary checked resolution.

### Explicit receiver-to-sender feedback test requested by user

- Change volume and mute at the receiver end; verify YT Music reflects them.
- Trigger play/pause at the receiver end; verify UI and playback state converge.
- Test receiver-side seek and track commands where supported; distinguish
  sending a command from reporting the resulting actual player state.
- Verify no feedback loops, double execution, stale position or volume jumps.
- Check both the Cast receiver control path (e.g. Home Assistant) and direct
  output/backend changes. Do not assume these paths have identical feedback.
- This is a planned test, not a claim that the reverse direction fully works.

Recheck switching to This Device, reconnect, queue advance, seeking, play/pause
and volume. Record versions, tests and remaining limitations in CHANGELOG and
per-iteration notes. AirPlay work remains outside this debugging iteration.
