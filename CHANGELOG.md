# Changelog

## 0.6.0.dev17 — release-preparation candidate (not deployed)

- Add Home Assistant icon/logo derived from the existing speaker SVG, with
  reviewed binary export pins and app-store README/changelog. Branding is live
  in the private HA store without changing its dev16 playback runtime.
- Verify an isolated AirPlay source build with corrected OpenSSL and rebuilt
  native archives; preserve the currently tested upstream runtime executable.

- Add repeatable native-source evidence checks for the upstream OpenSSL gitlink
  mismatch, without replacing the tested AirPlay binary.
- Check reachable Git history as well as isolated source exports in CI; include
  regressions for private material present only in an older commit. These checks
  are bounded safeguards, not automatic permission to publish.

- Keep DLNA preloaded media ready while the renderer reports STOPPED; do not
  confuse autoplay=false with cancellation. On explicit Play, report buffering
  until the renderer confirms playback. Add a regression test.
- Record successful user YT Music/DLNA acceptance for dev16 and retain concrete
  native-source, clean-export and distribution gates before publication.

## 0.6.0.dev16 — DLNA discovery and local media compatibility

- Add bounded SSDP renderer discovery and disabled import in the management UI,
  using the existing async-upnp-client dependency. Detect existing targets.
- Handle UPnP failures without crashing/re-registering the Cast speaker. Wait
  for real transport feedback before reporting PLAYING; bound initial buffering.
- Add DLNA-only local HTTP file serving with correct HEAD/byte-range support.
  HTTPS, loopback sources and incompatible audio types use bounded FFmpeg
  preparation; copy supported formats, otherwise encode MP3. Direct compatible
  HTTP playback remains unchanged. This fallback buffers a finite item first;
  it adds startup latency and does not support infinite live conversion.
- Physical Samsung test: converted WebM/Opus from Cast through HA to MP3, reached
  actual TV playback and clean stop. User subsequently confirmed YT Music works.
- Add relay HTTP/cancellation/conversion, discovery/import and error regression
  tests. Real FFmpeg conversion is also tested inside the container build.

## 0.6.0.dev15 — DLNA endpoint correction

- Allow correcting a DLNA description URL without deleting/recreating the Cast
  speaker. Explain that a full UPnP description URL, not a bare IP, is required.
- Validate edited routes against duplicate target rules; reject invalid target
  updates without changing saved configuration.
- Retry initial UPnP discovery after failed initialization rather than caching a
  partially initialized profile. Add regression tests.
- Physical Samsung control/discovery succeeds at its advertised XML URL.
  Actual playback and source-format compatibility remain separate test gates.

## 0.6.0.dev14 — HA audio and ingress correction

- Enable Supervisor audio mapping and provide a real non-login UID/GID 1000
  account with a writable home for PulseAudio clients. Verified on HA using a
  synthetic silent Cast stream; mpv feeds the physical analog stereo sink.
- Preserve same-origin cookies for HA Ingress requests, while keeping direct
  LAN management login-free. Disable request caching and explain expired or
  rejected ingress sessions. Add executed JavaScript request-helper regression.
- Full Python suite: 222 tests, 9 environment skips. Audible playback and
  embedded-browser user acceptance remain manual checks.

## 0.6.0.dev13 — private review candidate

- Fix old-mpv `loadfile` argument compatibility without retrying unrelated
  playback failures; clear buffering gates on command errors. Add a real silent
  decoder test to the container build.
- Prevent queued player notifications from replaying a pre-seek snapshot or
  crossing a WebSocket reconnection. Physical YT Music UI acceptance remains a
  separate check.
- Group DLNA/Sonos controls independently and verify mobile/desktop layout.
- Default the maintained frontend bridge to loopback and disable the inherited
  browser player in normal builds; retain an explicit development Cargo feature.
  Pin and apply the review overlay in both OCI and CI builds.
- Update airplay-cli to verified v0.5.4, retain v0.5.3 rollback pins, pass upstream
  tests and the physical reference-RAOP persistent-control/recovery test.
- Rewrite project identity/provenance documentation; package third-party notices
  in wheels/images and record Debian/FFmpeg/mpv build versions. Correct stale
  libraop/OpenSSL notice evidence without claiming a complete source-rights audit.
- Prepare bounded, explicit hash-pinned bundle artifact acquisition with atomic
  private import and synthetic rejection tests. No real bundle publication,
  automatic download URL or signing identity is introduced.
- Build/update the private HA App successfully; verify ingress/LAN health,
  closed LAN bridge, restart and preserved speaker identities. This is not a
  public release or universal hardware-compatibility claim.

## 0.6.0.dev12 — supervised and versioned modular runtime

- Add one deterministic supervisor for the Rust frontend and Python speaker
  manager, with readiness ordering and bounded process-group shutdown.
- Centralize shipped outputs in a small static registry; no dynamic plugin ABI.
- Add player protocol v2 with typed output-origin controls. Play, pause, stop,
  seek and volume enter canonical state handling; next/previous also reach the
  active YouTube Lounge session.
- Add allowlist-only `/health`, `/status` and `/api/support` operational APIs.
- Add opt-in direct-pull DLNA and Sonos output adapters behind the same registry.
  Their control/state logic is covered with simulated devices; physical-device
  and source-format interoperability are explicitly still unverified.
- Move the standalone Python Cast/DIAL receiver into an explicitly historical
  research package excluded from the normal wheel.
- Add a pinned amd64 OCI build recipe, thin Home Assistant add-on preview,
  dependency-update CI and upstream release monitoring. These are development
  packaging assets, not yet a published or hardware-accepted release.
- Publish the maintained Vibecast source on a dedicated fork branch and build
  from its immutable commit; retain the complete upstream patch as a verified
  fallback. Home Assistant now separates its dynamically allocated ingress
  listener from the user-configurable trusted-LAN management port.
- Hash-lock the complete CPython 3.12 amd64 container runtime and isolated wheel
  build tools; verify an offline install, package imports and clean installed
  entrypoints. Add a root-only state bootstrap that prepares only the App's
  dedicated directories and drops permanently to UID/GID 1000 before runtime.
- Add a reproducible, secret-free local HA test-repository exporter and a
  replaceable read-only certificate input through `/share`.
- Validate a real Home Assistant OS/Supervisor source build, start, ingress,
  LAN health endpoint, restart and persistent route identity. The final private
  773-window certificate bundle was then imported through `/share` without
  embedding it in the image; hardware AirPlay and update/rollback remain open.
- Add an allowlisted, text-only public-source exporter with a complete hash
  manifest. Its fresh export excludes private state/artifacts and passes the
  full suite. A private GitHub staging repository now exercises real CI without
  declaring the project publicly released.
- Python suite: 201 tests complete successfully with 20 environment-dependent
  skips in the current development environment. Targeted
  Rust gate: 110 tests pass with one explicit live-network probe ignored.

## 0.6.0.dev11 — processed Cast/Home Assistant artwork

- Background square-cover delivery through the existing manager HTTP service;
  bounded URL cache, shared converter policy, and original-image fallback.
- Add a narrow artwork-only bridge report, guarded by session/source identity,
  without altering playback state, position or queue.
- Add cache, cancellation, HTTP and Rust regressions plus an opt-in real
  Cast/mpv/FFmpeg artwork test. See docs/artwork-dev11.md for limitations.
- Close the reported song distortion as user-confirmed intentional source audio.

## 0.6.0.dev10 — AirPlay buffering intent and artwork reuse

- Preserve play intent across repeated seeks during buffering; preserve pause
  requested before the transport reports started. Both regressions fail on dev9.
- Reuse the single prepared cover for an unchanged URL within a transport;
  rebuild if absent or changed, and clear reuse state on transport teardown.
- Audio distortion remains unconfirmed: historical logs show a source connection
  reset and truncated decoding, not proof of a cover-induced audio defect.

## 0.6.0.dev9 — lossless artwork crop pipeline

- Generalize artwork preparation into `prepare_square_artwork`, shared by
  output adapters and future Cast/Home Assistant image serving.
- Decode/crop to a lossless PNG intermediate and JPEG-encode only once at the
  final bounded output. This removes the avoidable double-JPEG softness while
  retaining conservative embedded-letterbox detection and the 512px/1MiB cap.
- Use Lanczos resampling when a larger source must be reduced to the 512px cap.
- AirPlay now uses the shared converter; no playback or transport changes.
- Manager dev9 is deployed with the existing three routes and the Rust frontend
  left untouched; receiver rendering still needs manual confirmation.

## 0.6.0.dev8 — higher-quality shared artwork encoding

- Use FFmpeg JPEG quantizer 2 for both initial square artwork and the optional
  embedded-border refinement, within the existing 512px/1MiB bounds.
- Keep the crop policy in the shared artwork module; no playback or decoder
  changes. The source image's actual detail still limits maximum quality.

## 0.6.0.dev7 — conservative embedded-cover crop

- Refine existing square AirPlay artwork when the source itself contains
  symmetric black letterbox bands and colored side padding.
- Keep original artwork on ambiguous/dark/asymmetric images or bounded conversion
  failure; no playback-path dependency or new package.
- Add synthetic and real saved-cover regression checks. Cast/Home Assistant still
  receive original URLs pending a separate shared image endpoint.
- Deployed as the Python manager dev7 with existing route state preserved; active
  Cast frontend remains dev6.

## Post-dev6 tooling (no runtime change)

- Preserve support inventory when a requested binary is missing or unreadable;
  report fixed-label errors without private paths. Regression tested.
- Extend silent DMR tests with stalled HTTP load replacement and stop/relaunch;
  all18 checks pass on deployed dev6 without changing receiver behavior.

## 0.6.0.dev6 — audio category and installation verification

- Correct explicit audio MIME types from VIDEO to AUDIO in loading/resolved
  Cast media status; preserve the previous fallback for ambiguous containers.
  Reproduced on dev5; 30 core tests and17 silent real-decoder checks pass,
  including LIVE control policy. Complete source snapshot and dev5 rollback.
  Deployed with unchanged routes; live management browser check passes.
- Add a CPython3.13 Linux x86_64 wheel hash lock; fresh offline installation,
  pip check and all137 installed-package tests pass. Live dependencies unchanged.

## 0.6.0.dev5 — DMR music metadata

- Preserve sender metadata type, artist and album through normalized Cast status
  and the external-player boundary; keep legacy YouTube/provider behavior.
- Forward supplied music artist/album to AirPlay's existing metadata fields.
- Silent real-mpv regression reproduces loss on dev4 and passes on dev5; all14
  integration checks pass. 138 Rust tests and134 Python tests pass on Linux.
- Complete snapshot/source lock, installed-wheel test and live UI verification;
  deployed with unchanged routes/bundle and retained dev4 rollback.

## 0.6.0.dev4 — square AirPlay artwork and resource diagnostics

- Center-crop AirPlay covers to 1:1, maximum 512px without upscaling or padding.
  Cast/HA still receive original artwork URLs; their normalization remains open.
- Add real FFmpeg synthetic-image regressions and read-only Linux process-tree
  RSS/PSS/interval-CPU sampling without commands, environment or media history.
- Include management's aiohttp version in the support inventory.
- Refresh platform application status on app-channel CLOSE; reproduced with a
  failing regression before the fix. 135 Rust tests pass; one live probe ignored.
- Add silent real-decoder DMR fixtures; 13 integration cases pass. 129 Python
  tests pass on Linux. Complete current Rust patch/source lock reconstructs all
  109 build inputs; dev4 deployed with rollback and existing routes preserved.

## 0.6.0.dev3 — terminal status and speaker management

- Add terminal Cast media status before app teardown; regression reproduced and
  fixed. Broadcast refreshed receiver state after connection loss.
- Add field-presence diagnostics for generic media LOAD without source URLs.
- Add speaker deletion, duplicate-local creation prevention and SVG favicon.
- Preserve existing configurations and refresh lists across browsers.
- 121 Python tests and live UI checks pass; HA/YT status acceptance remains open.

## 0.6.0.dev2 — direct LAN management

- Remove management login/token backend and frontend completely.
- Listen on all IPv4 interfaces by default; load speaker list on page open.
- Migrate existing Laptop/AirPlay routes into persistent manager ownership with
  unchanged IDs and target, fixing the empty speaker list.

## 0.6.0.dev1 — speaker management (not deployed)

- Add optional aiohttp management service and plain HTML/JS speaker UI.
- Persist stable route IDs, independent names and private target config atomically.
- Explicit disabled imports, duplicate protection, isolated adapter supervision.
- Token/Host/Origin checks, loopback-only configurable port, bounded bodies and CSP.
- Add eleven config/process/API tests and tested dependency constraints.
- Existing live0.5.0 playback remains unchanged; real migration/HA packaging pending.
- Allow explicitly selected private-LAN test binding without a token (`--no-auth`).

## Unreleased — reproducible source preparation

- Record user acceptance of0.5.0 YouTube Music regression.
- Add read-only Rust build-source inventory/comparison and3 tests.
- Recover five already-deployed changes missing from local source; no runtime
  behavior change. Add complete0.5.0 patch, source lock and reconstruction guide.
- Fresh checkout reproduces109 build-input hashes; compiler selection documented.
  Full environment/bit-identical reproducibility and release audit remain open.
- Fresh-source tests exposed an existing installation-ID first-start race.
  Candidate uses existing bounded retry on initial parse failure; regression
  added.133 Rust tests pass,1 opt-in live probe ignored. Not deployed yet.
- 107 Python tests pass locally;1 optional bridge test skipped locally.

## 0.5.0 — initial active Default Media Receiver

- Add CC1AD845 HTTP(S) single-item LOAD provider; retain original URLs, metadata,
  initial position and autoplay. No yt-dlp request for direct audio URLs.
- Reject unsupported queue loads and live seeking explicitly.
- Opt-in isolated test through real mpv and Redmi RAOP passes initial paused
  position, paused seek, play/pause, bidirectional volume status, natural EOF,
  HTTP404, recovery, receiver STOP, relaunch and app disconnect.
- Fix adapter exit on abnormal bridge WebSocket closure. Regression fails before
  fix and passes afterward: old playback stopped and same identity re-registered.
- Correct live-seek regression to supply required mediaSessionId and assert the
  specific live-seek rejection, rather than merely a generic parse failure.
- 104 Python tests pass locally with1 bridge-extra test skipped; that real
  WebSocket regression passes on Linux with the bridge dependency installed.
- DMR frontend deployed; stock-sender/HA acceptance remains pending. Existing
  private credentials unchanged. No certificate material included in snapshot.

## Unreleased — collection recovery and publication preparation

- Prepare active Rust Default Media Receiver provider for single HTTP(S) LOAD;
  preserve metadata/start/autoplay and reject invalid URLs/timing.
- Explicitly reject unsupported DMR QUEUE_LOAD; disable unsupported LIVE seek.
- Add provider and core regression coverage; not yet deployed or sender-tested.
- DMR-1 snapshot:47 Rust provider/core/platform tests and43 YouTube tests pass
  (one opt-in live test ignored). No external dependency upgrade.
- Offline/locked release build succeeded; old binary retained for rollback.
  Running frontend not restarted; direct-URL decoder acceptance remains open.

- Audit distinct TLS certificates/time windows and repeatability for one date.
- Bound reference-app readiness polling; separate time-restored/readiness events.
- Keep unlocked USB phone awake during collection with restoration; retain guards.
- Add duplicate/key-count diagnostics and read-only support version/hash inventory.
- Draft maintenance, DMR integration and AI-assisted project-origin documentation;
  record publication/credits/UI/HA requirements. No GitHub or community post.
- 104 local tests pass. Runtime AirPlay remains user-confirmed0.4.9.

## 0.4.9 — persistent AirPlay transport

- Keep cliairplay/PCM stdin alive on load and seek; replace only the decoder.
- Await FLUSH acknowledgement; discard any buffered Python write tail with a
  second barrier. Reconnect on dead transport or bounded flush/drain failure.
- Detect natural completion from decoded PCM count and transport elapsed time;
  tail silence permits clock progress without closing stdin. Pause gates finish.
- Isolate old startup/EOF events and transport failures from the next track.
- Add --airplay-reconnect-on-load rollback and explicit physical test utility.
- 100 local tests pass; first Redmi test retained one connection across pause,
  paused seek, next, natural completion and short remainder. YT Music test pending.
- 24 staged Linux tests pass. Physical dead-helper recovery also passed;
  persistent mode deployed to Audio Lab AirPlay, rollback remains available.

## 0.4.8 — AirPlay progress, artwork and truncated-stream guard

- Refresh progress/duration after audio readiness and every two seconds; update
  on pause/play. Upstream RAOP ignores progress before streaming starts.
- Fetch HTTPS artwork asynchronously through existing FFmpeg into a bounded
  temporary JPEG; cancel/reap helper on track replacement. No new dependency.
- Count PCM output; short/empty streams cannot report FINISHED merely because
  FFmpeg exits zero. Log duration, decoded seconds and safe error categories.
- Report unexpected sender exits/PCM pipe failures instead of false playback.
- 91 local tests pass; physical receiver acceptance pending.

## 0.4.7 — AirPlay end-of-track and transition feedback

- Forward decoded input EOF to cliairplay and translate its drained EOF to
  FINISHED, guarded against teardown EOF; decoder failure remains ERROR.
- Freeze requested position in BUFFERING during load/seek until START ack.
- Send PROGRESS with DURATION and after START; avoid relabeling the old stream.
- 88 local tests pass. Hardware queue advance/progress acceptance pending.

## 0.4.6 — AirPlay pipeline teardown (2026-09-13)

- Drain decoder output during shutdown to prevent backpressure deadlocks on skip.
- Bound termination waits; send terminal STOP on pipeline replacement.
- Add real-process cleanup/reuse regression; 86 local tests pass.
- User confirms initial Cast-to-AirPlay audio and fast play/pause; artwork,
  progress and skip/reconnect acceptance remain open.

## 0.4.5 — first audible RAOP reference test (2026-09-13)

- Correct --txt to one argv argument and pass RAOP capability flags separately.
- Confirm missing et triggered an upstream crash; advertised et=0,1 connects
  successfully without rebuilding the upstream binary.
- User confirmed direct test tone on Redmi AirReceiver RAOP6000. Separate
  Audio Lab AirPlay Cast route started for full-path testing; laptop unchanged.
-85 tests pass. Full Cast playback/control/EOF and7000 mode remain unverified.

## 0.4.4 — AirPlay external-player wiring (2026-09-13)

- Add explicit AirPlay JSON route to the active Vibecast player adapter; reuse
  existing cliairplay/FFmpeg backend. Target-derived IDs survive Cast renaming.
- Clean partial/cancelled pipeline starts, respect mute at startup, contain
  backend RuntimeError and shut backend down on adapter exit.
- Hide pairing fields from repr and omit raw upstream diagnostics from logs.
- Add configuration/lifecycle tests and hardware acceptance checklist. No live
  output switch and no claim of physical AirPlay end-to-end acceptance.
- 84 Python tests pass locally; nine bridge tests pass in isolated Linux staging.
  Pin/provision agreed cliairplay v0.5.3 x86_64 with release digest verification,
  license/notices and successful binary self-test; no global installation.

## Certificate collection safety and confirmed offline playback (2026-09-13)

- User confirmed Linux receiver connection/playback with the offline identity.
- Add resumable sequential collection, private immutable checkpoints, exact
  coverage-end scheduling, identity/gap checks and stop-on-first-failure behavior.
- Add exclusive per-phone pilot lock and clean up USB forwarding on UI-restore
  failure. Keep the phone-local clock/network restoration watchdog.
- 14 certificate/collection tests pass, including synthetic resume, failed-pilot
  coverage protection and power/thermal guards. Initial live collection/resume
  passed; six contiguous windows through Sep24 installed and locally probed.
- Narrow app-generation boundary to Dec6,2030. Start independent collection toward
  that boundary with private checkpoints; multi-year coverage is not yet complete.

## Offline certificate generation and acceptance test (2026-09-13)

- Implement bounded offline USB pilot and reversible omission of cks2 cache only.
- Obtain new current, next and Jan2027 TLS windows; offline device identity differs
  from online identity; user confirmed real YouTube Music connection and playback.
- Add validated private manifest merger and five tests. Deploy two-window test
  bundle Sep12–16 on Linux; retain original manifest for rollback.
- Record unsuccessful Dec2032 handshake probe; do not promise multi-year coverage.

## Certificate pilot: explicit receiver start (2026-09-13)

- Require UI Ready To Cast, pressing the actual START button after app restart.
- Add optional nonsecret native-call/time observation and bounded PID polling.
- Confirm unchanged TLS window even after explicit Start with future app time;
  keep installed manifest unchanged and restore phone after each attempt.

## Certificate-window pilot (2026-09-13)

- Add bounded Android date pilot with normal restoration and phone-local watchdog.
- Re-capture current material and test two future dates, including reversible
  Cast-config isolation; all return the existing Sep12–14 window.
- Reject insufficient future validity; do not replace working runtime bundle.
- Record restored phone state and actual intermediate expiry (December2032).

## Controls-17 diagnostic cleanup (2026-09-13)

- Record Nest Audio reproduction; stop special handling of extreme-speed selection.
- Remove temporary selection POST timing; move verbose command/selection traces
  to DEBUG and avoid building diagnostic JSON at normal INFO level.
- Retain test-only regression coverage and queue handling; no playback change.
- Audit existing certificate rotation; add synthetic validity-boundary, gap and
  clock-rollback coverage without changing real clocks or credentials.

## Controls-16.1 regression boundary (2026-09-13)

- Add state/feedback regression for repeated index1 queue insertions across
  playback start, followed by an explicit selection; 43 YouTube tests pass.
- Record user-confirmed ~1s UI pacing workaround and bounded reference-comparison
  experiment. No runtime behavior change or timing-based suppression.

## Controls-16 queue-addition selection guard (2026-09-13)

- Identify delayed VIDEO_ADDED events displacing the last PLAYLIST_SET selection.
- Preserve current selection for additions to the same queue when its slot stays
  unchanged; retain queue enrichment and correct nowPlaying feedback.
- Keep explicit selections and ambiguous cases unchanged. Add regression cases
  for delayed additions, reselection, loading and unmatched queue identities.
- Record the user's permanent five-title manual test order.

## Controls-15 event correlation preparation (2026-09-13)

- Record rapid-only reproduction and the limit of arrival-order cancellation.
- Add allowlisted event-kind/count and outgoing selection/ack diagnostics.
- Prepare stale-update guard location and regression criteria; no speculative
  event filtering or playback behavior change.

## Controls-14 selection interpretation diagnostics (2026-09-13)

- Analyze rapid-selection logs: final parsed selection matches actual load in
  inspected burst; original selection fields are insufficiently logged to assign cause.
- Log allowlisted videoId/eventVideoId/currentIndex alongside parsed selection
  and incoming sequence; add explicit final commit diagnostics. No selection rule change.
- Test mismatch visibility and exclusion of unrelated credential/event fields.
- Record confirmed queue/session behavior and sender-disabled loading controls.

## Controls-13 interruptible selection (2026-09-13)

- Receive new selections and controls while resolving audio. New selection drops
  obsolete resolution; retain pending seek/pause intent and duplicate coalescing.
- Reuse matching next-item preparation; preserve extractor format checks/options.
- Replace blocking extractor with Tokio-owned child, process-group cancellation,
  35-second timeout and asynchronous reaping. No persistent worker/pool.
- Add controlled A/B/C, prefetch, Stop/disconnect tests and Linux process-tree
  cancellation/timeout tests. Isolate the stale DASH fixture test from live yt-dlp
  and align it with the already-existing audio metadata behavior.

## Scope and readiness audit after Controls-12 (2026-09-13)

- Record user-confirmed Android hardware volume feedback.
- Prioritize YouTube Music and Default Media Receiver; native alternatives first
  for other services. Add persistent collaboration rules in AGENTS.md.
- Promote future-window TLS coverage/rotation to required pre-AirPlay milestone.
- Specify cancellation refactor and queue regression criteria; implementation
  awaits agreement because command and subprocess coordination must change.

## Controls-12 platform volume subscription (2026-09-13)

- Keep receiver-0 and app-session subscriptions independently: app CONNECT no
  longer suppresses device volume broadcasts for the same sender ID.
- Publish device status when volume changes through the media namespace too.
- Add an active-session volume regression that times out on Controls-11.
- Reconcile the working plan: explicitly restore newest-selection cancellation;
  defer worker/pool, format racing, shared probe stream and metadata consolidation.

## Controls-11 volume feedback and persistence (2026-09-13)

- Replace hardcoded YouTube Lounge volume replies with actual receiver level/mute.
- Forward optional backend volume/mute reports through the player bridge and
  synchronize receiver, media coordinator and YouTube session state.
- Persist volume per receiver with atomic file replacement; restore on launch.
  A saved zero level becomes 10% and unmuted when starting a new session only.
- Preserve Audio-10 queue preparation and format checks. Live sender UI test pending.
- Architecture/resource trade-offs recorded in docs/architecture-review-11.md.

## Audio-10 transition dispatch (2026-09-12)

- Allow same-queue next-index setPlaylist to consume prepared media; previous Next-only handling missed the sender's actual command.
- Dispatch local incoming commands before awaiting outbound status HTTP ACK, after updating internal state.
- Add selection regression tests, structural diagnostics and measured transition notes.

## Audio-9 next-item preparation (2026-09-12)

- Measure extractor steps; forced AAC did not improve the slow title.
- Prepare one next queue item per session and reuse on Next with bounded age;
  discard obsolete preparation and retain normal resolution on misses/errors.
- Preserve new-queue selection behavior and format checks.
- Add TTL/cancellation tests and explicit receiver-to-YT-Music feedback test plan.

## Audio-8 parallel resolution (2026-09-12)

- Overlap metadata retrieval with checked audio extraction instead of running both sequentially.
- Log metadata/audio/total resolution times without media URLs.
- Add an opt-in live resolver probe; keep format validation, queue coalescing and player behavior intact.

## Controls-7 pending selection coalescing (2026-09-12)

- Normalize repeated selection of the same pending title/index/start position into a queue update before feedback and playback dispatch.
- Preserve queue changes without triggering a second resolution/load; keep new titles, changed start positions and post-load replays intact.
- Add focused Rust regression coverage and docs/WORKING-PLAN.md. Loading-time optimization follows live duplicate-start verification.
- Persist cumulative Lounge changes in patches/vibecast-lounge-controls-7-snapshot.patch (snapshot, not additive to older Lounge patches).

## Audio-6 format availability check (2026-09-12)

- Reproduced the title-specific load failure as HTTP 403 at the media URL.
- Enable yt-dlp's upstream format availability probe before returning an audio URL.
- Preserve queue, seek and session behavior; document tests and remaining limits in docs/title-qXCwga3LUO0.md.

## Controls-5 diagnostic iteration (2026-09-12)

- Trace new-queue load requests and mpv completion/error events without signed URLs.
- Clear pending load/seek feedback gates after a playback error; regression test added.
- Document observed paired loads and successful eight-second decode of last stream.
- Double-start root cause and last live failure remain under investigation.

The project uses semantic versioning while the protocol and configuration
interfaces are still experimental.

## Unreleased

- Add one deployment guide for Home Assistant, OCI and native Linux; make the
  required private certificate input and fail-closed startup behavior explicit,
  and update the development runbook to the dev12 supervisor lifecycle.
- Pass the first clean-source GitHub CI matrix across Python 3.11--3.13, runtime
  wheel inspection, targeted Rust tests and a `linux/amd64` container build.
- Validate one real midnight certificate-window rotation in the running Home
  Assistant App: TLS/device-auth/discovery state rotated without restart and the
  receiver continued accepting Cast connections.
- Exercise the scheduled upstream watcher end-to-end; it detected the new
  airplay-cli v0.5.4 release and opened a review issue without changing the
  tested v0.5.3 runtime pin.

- Controls-4 experiment: associate sessions with their LAUNCH connection and
  stop them when that connection closes, independent of lingering subscribers.
  Reset Lounge state to BUFFERING/0 on Next and suppress old playback reports
  until the replacement player's BUFFERING report arrives. Two-sender takeover
  and actual sender disconnect still require live verification.
  ERROR/CANCELLED releases the pending-load status gate as well; see
  docs/session-controls-4.md for the intended ownership semantics.

- Controls-3: preserve play/pause intent across buffering feedback; ignore old
  position/pause events during media replacement and seeking. Activate player
  command/load diagnostics (without signed URLs). Duplicate starts and sender
  disconnect cleanup are not yet established as fixed.

- Controls-2: retain YouTube long-poll requests across position reports to avoid
  starving incoming controls; coalesce repeated position-only player events.
  Reopen media at a start offset when mpv rejects an in-place seek. Stop audio
  on player-bridge disconnect and recognize Lounge stop/stopVideo commands.
  Sender disconnect cleanup and volume feedback remain under investigation.

- Controls-1: add optional mpv JSON IPC backend for actual seeking, pause,
  volume/mute and decoder-reported position/EOF. Forward Cast receiver-level
  volume to the player. Advance the YouTube queue once on transition to FINISHED.
  Local event tests and a remote muted synthetic audio test passed; sender
  verification remains pending. Lounge's hardcoded volume response and track
  resolution latency still need further work.

- HLS-2: fix deployed extractor selection: use project yt-dlp 2026.08.19 with
  EJS/Deno rather than system yt-dlp 2025.04.30. Both actual failing sender tracks
  now resolve and decode completely in standalone checks. Pin tested extractor
  dependencies and record the required runtime PATH.

- HLS-1 experiment: decode a complete 213.043-second track via yt-dlp HLS and
  direct FFmpeg input; switch the trial resolver to bounded external resolution
  and correct HLS MIME. Add {start_time} to player templates and regression tests
  for failed transport versus successful EOF. See docs/audio-debug-2026-09-12.md.

- Diagnose false track completion after HTTP 403: the experimental shell
  pipeline ignored curl's exit status. Enable pipefail in the deployed command
  and preserve transport failures in the Python playback wrapper.
- Full-track audio remains unverified: a first byte range can succeed while
  later ranges and open-ended requests fail. Previous range probes did not
  establish that the resolver or Premium session handling works.

## 0.4.3 - 2026-09-12

- Capture a single current AirReceiver TLS window on a user-owned rooted
  Android test device. Verify the active TLS key and both SHA-1/SHA-256
  certificate-only signatures before writing a private Vibecast manifest.
- Deploy and probe the captured bundle on the Linux audio receiver; document
  the Galaxy A50 result and the intermediate certificate's earlier expiry.

- Confirm via a second independent AirReceiver 5.1.7 installation that the
  Google Cast device certificate and native library are identical; document the
  separate embedded RSA key and exclude it as the live Cast identity.

- Add a read-only Cast CRL checker for rejecting revoked device-auth bundles
  before deployment.

- Add a read-only APK diagnostic utility for locating direct integer status-code
  constants; document the unsuccessful verbose-log capture and restore settings.

- Add an optional diagnostic patch logging requested Cast auth algorithms and
  nonce length, without logging nonce contents or credentials.

## 0.4.2 - 2026-09-12

- Align Cast GET_DEVICE_INFO capabilities with the audio-only mDNS advertisement;
  the upstream response still advertised video output (4101).

- Correct the auth diagnostic: distinguish challenge-nonce binding, returned-nonce
  binding and certificate-only signatures; explicitly report that trust-chain
  validation has not been performed. A successful signature check does not
  establish sender acceptance or prove another identity has been revoked.

## 0.4.1 - 2026-09-12

- Match the observed Nest Audio mDNS and Eureka audio capability profile.
- Keep ShanoCast replay responses CRL-free unless their bundle embeds one.

## 0.4.0 - 2026-09-12

### Added

- Adopt Vibecast as the pinned native CastV2 and YouTube frontend.
- Add a verified Shanocast replay-table to Vibecast bundle importer.
- Add the Linux external-player adapter with stable naming and state feedback.

### Changed

- Advertise the patched frontend as an audio receiver instead of a display.
- known AirConnect-generated RAOP targets are marked and excluded from
  automatic discovery by default to prevent bridge feedback loops

## 0.3.1 - 2026-09-12

### Added

- bounded `_raop._tcp` and `_airplay._tcp` discovery command
- merging of the two advertisements by stable device ID
- an end-to-end development Cast sender for protocol and local-audio smoke tests

## 0.3.0 - 2026-09-12

### Added

- `cliairplay` output adapter for RAOP, AirPlay 2 compatibility mode and native
  AirPlay 2
- FFmpeg URL-to-PCM pipeline with configurable AirPlay queue depth
- protocol-neutral media metadata model and AirPlay metadata forwarding
- parsing of cliairplay lifecycle and remote-control events
- shared Cast runtime state across simultaneous sender connections
- unsolicited receiver/media status broadcasts after backend changes
- persistent Cast device ID in the state directory
- GPL-3.0-or-later project license declaration

### Changed

- YouTube Music now uses the same MDX status path as the regular YouTube app
- YouTube Lounge resolves metadata before loading an output

### Known limitations

- stock Cast senders still require a configured device-auth provider
- AirPlay discovery, pairing UI and warm seek/track changes are not complete
- hardware AirPlay output has not yet been exercised in this release

## 0.2.0 - 2026-09-11

- audio-only Cast advertisement and CastV2 receiver/media protocol baseline
- pluggable device authentication boundary
- experimental YouTube DIAL/Lounge receiver
- null and external-command audio backends
