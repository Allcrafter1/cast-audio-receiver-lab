# Working plan

## Upstream review and source publication — 2026-11-08

The verified dev3 frontend is committed and published as source prerelease
`cast-audio-0.7.0-dev3` (`1a040ed`), with no main/latest/image promotion.
[Product PR #20](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/20)
contains the isolated AirPlay 0.5.9 candidate, Python ABI gate and watcher-review
correction; it does not silently include the pending dev3 product integration.
The same maintenance changes are present in this development working tree.
The installed laptop remains on the previously verified dev3 runtime.
[Review details and acceptance limits](upstream-review-20261108.md).

## Current: EOF Replay and endpoint names — 2026-11-08

`0.7.0-dev3` builds on the complete dev2 candidate below. It fixes the normal
YouTube app's Replay button after natural EOF, clears stale queue waits on
replay, and appends ` (YT)` to every video endpoint. No session/reconnect or
Music loop-mode policy changes. Both added regressions fail before the fix;
306 affected Rust tests and 431 Python tests pass. The candidate is installed
and hash-verified on the test laptop; both enabled routes are ready and LAN
checks confirm both endpoint names and shared state. The Android replay retest
remains pending because the USB phone is disconnected. See [validation](TESTING.md).
The isolated unexpected disconnect cannot be assigned to a specific logged
CLOSE; no speculative ownership change is made.

## Previous: production dual-identity candidate — 2026-11-08

The owner authorized the product implementation after the successful isolated
lab. `0.7.0-dev2` gives every desktop output a stable YouTube video alias while
retaining the original speaker UUID and one shared player/session/volume runtime.
Discovery and explicit-launch policies are separate so existing browser routes
remain usable. ADB product tests now verify real YouTube and Music decoding on
Audio Lab Laptop; the original lab only acknowledged silent LOADs.

The candidate includes the previously integrated volume policy, Sonos events,
metadata and common relay/transcoding work, TuneIn (including native autostart),
and accepted YouTube controls/reconnect fixes. Those are present code, not a
future feature list. Direct Sonos hardware acceptance, the latest stock TuneIn
autostart retest, broader devices and multiarchitecture publication remain
separate gates. The optional browser userscript is not silently installed, and
HA repeat/queue expansion remains outside the accepted standard-Cast scope.

See [dual identity architecture](dual-cast-identities.md) and
[current validation](TESTING.md). The entries below are chronological evidence;
their old "not deployed" and "keep mdnsapps unchanged" instructions are
superseded by this explicitly authorized product candidate.

## Historical scope: Android app discovery and YouTube cast abort

**Capability lab completed: no stable single identity, successful lab-only
dual-identity separation.**
The owner authorized autonomous ADB/capability experiments in a separate silent
lab, preserving the working Music/web deployment. The earlier phone lock and
Xiaomi input-injection restriction were resolved by the owner. The lab measured
25 profiles across all four PR #18 layers, including actual native
picker icons, selection, app LAUNCH and silent media LOAD. Historical builds
and the installed public GMS/YouTube/Music APKs were audited independently.

The owner also accepts TV presentation in ordinary YouTube if Music retains a
speaker. Four paired single-identity runs still found no stable combination: the
promising mismatch changed with session order, and full PR #18 was a TV in both
apps. A later isolated split used two UUIDs/ports with app-specific discovery and
inverse Availability responses. In both app orders Music saw/launched only the
speaker while ordinary YouTube saw/launched only the TV; matching silent LOADs
reached only the intended endpoint. Rapid UUID churn briefly left an old route
cached and the new one dimmed, then stable discovery converged and both paths
worked. Real audio, reconnect and shared backend/volume arbitration were not
verified, and no product option was implemented. Final audit confirms the lab
removed, phone USB stay-awake restored, original binary and all 28 runtime files
intact, and both enabled outputs ready. Keep the frozen mdnsapps receiver and its
identities unchanged. Do not implement a TV option without an explicit product
decision. See the [capability lab record](youtube-capability-lab.md) for measured
results and limits.

Earlier incident evidence leading to the isolated lab:

- Owner accepts ordinary YouTube web behavior as good enough and confirms Music
  still works. Do not pursue remaining web stale-session/reconnect issues now.
- After the subtype correction, the phone now lists both speakers in YouTube
  and Music; Music connects and plays audio as before. Ordinary YouTube produces
  no recognizable connection or audio on selection, temporarily loses the
  speaker entries, then shows them again after a wait. Earlier visibility changes
  remain unattributed; reliable YouTube discovery/casting is still open.
- Two user attempts reproduced the failure, including after explicit Music
  STOP. No ordinary YouTube LAUNCH/MDX was captured. The queue requests used
  Play Services transport; that does not prove passive/background intent or
  identify the originating app. The weak-ownership guard remains unchanged.
- Target confirmed: Audio Lab Laptop. Ordinary YouTube listing disappeared
  after diagnostic restart, while Music remained working. Force-stop did not
  restore it; bounded old/new-port observation found no matching connection SYNs.
- Diagnostic-only candidate is stopped/retained. Exact owner-accepted ytcontrols
  candidate restored and verified (2/2 routes, binary and 28 Python files).
  The subsequent visibility comparison did not restore either app's listing;
  no claim that diagnostics caused the issue. Speaker identity and all previous
  playback fixes remain intact.
- USB inventory: Android 15/SDK35, YouTube 21.40.162 (1561301422), Music 9.44.52
  (94452240), Play Services 26.43.30 (260400-1006944126; 264330035).
  Actual phone DNS capture includes nine ordinary-YouTube app-subtype questions
  and 25 Music app-subtype questions. A separate LAN probe receives two owned
  base PTR answers but zero YouTube and zero Music subtype PTR answers.
- Generic correction in `mdns-app-discovery-20261108-1`: derive all supported
  app subtype PTRs from AppRegistry, sharing one mDNS daemon and service identity;
  answer/suppress each requested PTR and announce/withdraw all aliases together.
  Keep ca=199428 and all playback/queue/reconnect behavior. Private candidate
  `0.7.0.dev1+local.20261108.mdnsapps` is installed; loaded `/proc` executable
  matches SHA-256 `02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b`,
  all 28 Python files match, both routes are ready, and Eureka display remains
  false. LAN probe changes from 2/0/0 to 2/2/2 base/YouTube/Music PTR answers.
  This verifies the previously missing network replies. The subsequent phone
  test confirms listing in both apps and Music playback, but ordinary YouTube
  still fails before any recorded app launch; full acceptance is not achieved.
  Rollback: `cast-audio-receiver-before-mdns-app-discovery-20261108-1`.
  Receiver logs for the test contain one Music 2DB7CC49 LAUNCH and no ordinary
  YouTube 233637DE LAUNCH. Investigate the remaining app abort without changing
  working Music, web/reconnect behavior or speaker identity.
- Public YouTube and Music APKs contain additional audio-only filters. Ordinary
  YouTube's static opt-in default is false; Music uses a separate configuration/
  account-metadata condition whose obfuscated field does not establish a
  subscription requirement. Effective phone settings are unknown. A corrected
  subtype response may not resolve every app filter or launch failure. Keep the
  speaker identity and verify listing, launch/authentication and audio separately.
  Detailed evidence and scope: [PR #18 investigation](youtube-discovery-pr18.md).
- Public fragment evidence identifies active anhv (mState7, added=true,
  hidden=false; YouTube resumed). Its actual RecyclerView binding is traced
  anic/anil -> anhx.f -> anhw -> anhk.onClick, with injected nA=false. The earlier
  anjo/anjn chooser is not needed as runtime evidence. This selection guard is
  separate from the configurable list filter: audio-only CastDevice rejects
  locally with ange, then the row can dismiss the picker, without a log phrase.
  The owner confirms normal signed-in use; account-dialog exceptions are not
  receiver-controlled. Actual row extras/branch remain uninstrumented and
  additional row/session guards exist.
- Only Music connections from the phone reached the test laptop in the observed
  interval; no ordinary YouTube TCP/LAUNCH. Two null-provider warnings came from
  the GMS persistent Cast provider and do not establish causality. Public PM
  reports MediaTransferReceiver disabled; this concerns the later conditional
  onRouteSelected guard, not the earlier UI guard, and does not reveal cached
  app configuration. The selection guard is a strong explanation, not a universal
  impossibility proof. Google's current [speaker guidance](https://support.google.com/googlehome/answer/7181830?hl=en)
  directs YouTube content through Music. Preserve the speaker identity and
  working behavior; no further code change or TV emulation.
- Public router metadata shows the owned receivers under GMS PersistentProvider
  and one deviceType2, consistent with the owner's speaker icons. The inspected
  standard MDX route builder uses deviceType1 (TV) for DIAL/cloud screens.
  This supports a native speaker route but does not expose app CastDevice extras
  or capabilities; missing extras in the public dump do not mean no CastDevice.
- No concrete missing receiver field found: existing MDX association fields
  arrive after LAUNCH, matching DIAL UUIDs are deduplicated against native Cast,
  and cloud pairing would be a separate unverified lifecycle/ownership path
  with TV presentation in the inspected builder. Keep these limits scoped to
  the inspected implementation; no general MDX impossibility claim.


## Active: ordinary YouTube selection and audio tracks — 2026-11-08

- User confirms better ordinary youtube.com startup, but selecting another video
  leaves the previous video playing until page reload. Wrong audio track on
  public video uMtsPAEEavE despite English Original being selected.
- Correct attribution: the observed Android GMS probes may originate from
  YouTube Music. They cannot establish discovery by the ordinary YouTube app.
- Receiver trace: setPlaylist/VIDEO_ADDED reaches the receiver for the new video;
  existing normalization suppresses selection. After reload VIDEO_SELECTED
  causes playback. Isolated ordinary Lounge probe confirms sender setPlaylist
  becomes setPlaylist/VIDEO_ADDED, while addVideo becomes updatePlaylist.
- The same video has English Original/default at 131407 bps, but e.g. Indonesian
  at 163104 bps. Native resolver ranked all tracks solely by bitrate.
  setAudioTrack commands also reach the receiver but are not implemented.
- User explicitly requires additive ordinary-YouTube changes, preserving all
  existing Music behavior. Keep Music's established queue guard and audio
  resolver defaults; scope the new selection/audio profile to ordinary YouTube.
  Do not change core ownership, reconnect, volume, output backends or discovery.
- New selection and original-track regressions failed before their fixes.
  Six additive regressions now pass; total 338 libraries + SDK doctest pass.
  Frozen six-patch reconstruction matches 114 inputs, only three YouTube files
  differ from the lifecycle candidate. Release build and 14 silent binary checks
  pass. Candidate 0.7.0.dev1+local.20261108.ytcontrols is active on the test laptop;
  loaded binary, 28 Python files, 2/2 routes and speaker profiles verified.
  Rollback: cast-audio-receiver-before-youtube-controls-20261108-1. HA unchanged.
  Physical title/audio retest requested; Android listing and legacy cache remain open.

## Reopened: ordinary YouTube discovery and handoff — 2026-11-07

- User clarifies explicitly: all YouTube Music paths work. Scope is ordinary
  YouTube Android listing and youtube.com signed-in/incognito reconnect.
- The deployed continuity candidate improves one same-owner case but does not
  resolve the complete incident. Two ordinary-YouTube sessions received
  playlists, followed by another no-op-only session. The persisted screen was
  unchanged across those relaunches, so repeated screen rotation alone does not
  explain every current failure; the normal browser still has earlier cache state.
- New allowlisted transport evidence shows Android gms_cast_prober reaching both
  laptop receivers and requesting Eureka, app availability, status and device
  information. These probes may be from Music; ordinary YouTube attribution
  and its discovery/filter stage remain unverified.
- Recheck current and historical advertisements, actual sender filtering and
  native YouTube identity/session lifecycle. Preserve speaker identity, all YTM
  behavior, established reconnect and true-controller takeover semantics.

## Lifecycle follow-up deployed — 2026-11-07

- User requested an explanation and continued investigation. Goal: reliable
  ordinary YouTube with speaker identity; all Music paths are a working baseline.
  Android listing and browser Cast-to-Lounge handoff are separate boundaries.
- Confirmed a general Core defect: every virtual receiver used the same app
  storage directory. Scope state by stable receiver ID for all providers;
  preserve across relaunch/restart. Do not replicate ambiguous legacy identities.
  Existing Cast IDs/settings/routes remain; old shared files remain intact.
- Public native YouTube receiver source and a separate real-service exchange
  confirm getDiscoveryDeviceId is a request and onSetDiscoveryDeviceId is its
  acknowledgement. Correct the reversed handler and announce on bind/rebind.
- Explicitly terminate the bound BrowserChannel on final Stop/takeover with a
  500 ms limit. Existing active reconnect/grace/ownership and Music behavior are
  retained. Separate probes show termination is not instant screen-offline or
  old-controller revocation; do not replace ownership rotation with global reuse.
- The new regressions fail before and pass after; 332 library tests pass, three
  pre-existing probes ignored, SDK doctest passes. Release binary passes 14
  silent Cast/bridge checks. No real YouTube acceptance is inferred from them.
- Candidate 0.7.0.dev1+local.20261107.ytlifecycle built locally with Rust 1.98/Zig,
  target GLIBC 2.36, highest required 2.34. Binary SHA-256:
  66def8aefbd873101fd26c47eaa6583f97633a94776f4f4059ba46d050e51399.
  Five ordered patches reconstruct all 114 source inputs. Records and frozen
  source: .state/youtube-lifecycle-20261107-1/. All 28 Python files are identical
  to the preceding candidate except its private version label.
- Activated on existing test laptop after ABI/import/hash preflight; readiness
  2/2, loaded /proc executable and all installed hashes pass. Both Eureka routes
  retain display=false and owned mDNS records ca=199428. Rollback container:
  cast-audio-receiver-before-youtube-lifecycle-20261107-1. HA unchanged.
- Still open: ordinary Android's final filtering decision and Chrome legacy
  cached-screen compatibility across genuine owner changes/process restarts.
  The preceding candidate did not pass acceptance. No TV capability, universal
  YouTube fix, public release, PR merge or publication is claimed.

## Continuity candidate implementation/deployment record — 2026-11-07

- User explicitly requires retaining existing YTM, mobile/iPad, reconnect and
  takeover behavior. No speculative token-mode or unconditional screen reuse.
- Browser evidence now confirms effective enableCastLoungeToken=false and a
  cached legacy screen different from the current receiver screen. Incognito
  first connect works, second connect in the same window fails. Retained vendor
  code reproduces exactly that stale-cache/repeated-screen-rotation conflict.
- Two reviewers agree on a narrow fix under the existing physical-controller
  policy: a Core-owned opaque continuity key survives app Stop/CLOSE/relaunch
  only for the last still-connected current owner and exact Cast app ID.
  Takeover or another app replaces the key; disconnected sockets lose their grant.
  No history of previous owners and no IP/UA guesses. Existing active grace and
  multisocket ownership decisions remain the authority and are not rewritten.
- Core/SDK and YouTube integration are implemented and independently reviewed.
  Stored identity reuse requires matching present keys; legacy files/missing
  keys remain fresh. Real takeover carries a new key before MDX. Invalid-screen
  replacement is bounded; transient failures preserve the saved screen. Stop
  drains the old Lounge worker, with abort guards for interrupted teardown.
- All 313 scoped Rust tests pass, with three existing ignored probes. The
  actual release binary passes 14 Cast/bridge smoke checks for TuneIn/DMR,
  controls and bidirectional volume with emulated output and no audio.
- Candidate 0.7.0.dev1+local.20261107.pr18 is active on the existing test laptop.
  Loaded /proc executable SHA-256 matches:
  bb129cbe110ea1f9dddc135bbfaf0ed7b43f76fa42212849b3b8ea73007a043b.
  All 28 live Python files/assets match the frozen package; only the version
  label differs from the preceding candidate. Imports and readiness 2/2 pass.
- Post-deployment readback confirms both Eureka routes have display=false and
  multizone=true; both owned mDNS services retain ca=199428. HA remains dev20.
  Four-patch recipe, source hashes, build/test and deployment records are in
  .state/pr18-continuity-20261107-1/. Reversible rollback container:
  cast-audio-receiver-before-speaker-continuity-20261107-1.
- Physical first and repeated ordinary-YouTube playback acceptance is pending;
  Android listing and cross-client acceptance remain unverified on this build.
  An already stale browser cache is not silently repaired. No universal fix,
  PR merge or publication is claimed.

## PR #18: installed-state audit and speaker identity — 2026-11-07

- Preserve speaker identity: mDNS and Cast DEVICE_INFO stay 199428, no VIDEO_OUT
  or TV option added. Historical v0.4.2 speaker-icon confirmation and PR author's
  Android YouTube -> Sonos Era100/AirPlay test with 199429 are documented in
  docs/youtube-discovery-pr18.md. That hardware result does not verify our
  speaker-only mode or every Android client.
- This section records the initial pre-fix audit; the active deployment above
  supersedes its laptop executable and default-capability readings.
- Audited actual installations, not only working source. At that initial audit,
  laptop loaded process SHA was exactly
  16dcdc7aba9a504c2fcce314cc508f30eaace80fb695539bddcea7b1d55c7cc1;
  all 28 installed Python files/assets matched. The preceding combined container
  retains binary 7a4d9c859784cbec61cfc236df156c0c144fed9d845a30994c4b7468ab84f4d6
  and the same 28/28 Python files. Only one laptop container is running.
- Rebuilt frozen frontend source from base plus the recorded full snapshot and
  autostart delta: all 114 input hashes match. Only TuneIn provider/tests changed
  since combined; 112 files, including discovery/config/core/YouTube, unchanged.
  Both Python package archives and manifests are byte-identical. No evidence of
  accidental last-patch source changes or a mixed active laptop installation.
- Separate HA inventory: active 0c012509 App is 0.6.0-dev20 (runtime 0.6.0.dev20),
  healthy with 2 routes and about six days uptime. Duplicate 0b4634bd dev18 is
  stopped. Latest local TuneIn deployment did not update HA. HA executable
  equality was not verified; Supervisor/API version agreement is a separate check.
- Live read-only Cast probes on all four receivers (two laptop, two HA) confirm
  DEVICE_INFO199428 and receiver availability replies. Fixed the inspection
  tool to accept the actual GET_APP_AVAILABILITY reply type as well as its legacy
  alternate. No app LAUNCH/playback or volume commands were sent by these probes.
- Concrete pre-existing installation/default bug: neither audited laptop variant
  had frontend config.toml, and Eureka reported display=true despite speaker
  mDNS. Both Eureka and streaming-header defaults are now false across the
  frontend, including missing/partial config; no per-backend workaround.
- Also correct general app availability to registry support and remove optional
  screen-online HTTP diagnostic from MDX's critical startup path. New regression
  tests reproduce the old failures; the initial discovery iteration passed
  discovery11/platform21/core115/YouTube137 (284 total, 3 explicitly ignored).
  Three existing Python probe tests and live availability reads pass. Scoped
  formatting and diff checks pass.
- Ordinary YouTube browser sessions at 21:02 and 21:11 UTC reach LAUNCH and MDX
  response in <0.6s, then only Lounge noop: no remoteConnected/setPlaylist.
  Therefore these attempts fail before resolution/decoder/output; the optional
  diagnostic's timeout did not cause these particular fast failures.
- Vendor remote.js reproduction initially suggested an old-screen cache conflict
  with fresh Lounge screen IDs and a stable Cast ID. Later effective player
  configuration and sanitized cache checks confirmed token mode false and a
  cached/current screen mismatch. The user confirmed normal-profile YTM works;
  ordinary YouTube worked on the first Incognito connection but failed on the
  second. The 21:25:20 UTC session received remoteConnected/setPlaylist, unlike
  the earlier failed attempts. The bounded continuity fix above addresses this
  confirmed handoff conflict while retaining ownership rotation. Physical
  repeated-connect acceptance and Android compatibility remain open.
- LAN-only IPv4 resolution and a raw multicast probe (90 packets/zero parse
  errors) show only the correct LAN A-records for both owned receivers. The
  earlier all-interface loopback/hotspot list was local aggregation. No mDNS
  filtering patch is justified by these observations; physical phone capture
  and Android discovery filtering remain unverified.
- Initial discovery candidate remains frozen under .state/pr18-review-20261107-1/.
  Its additive delta:
  patches/vibecast-speaker-discovery-review-20261107.patch, SHA-256
  79361f203dc91da0ecbca59ddeeaea6c0157f95dc47d590b58ec49e73b2219c5.
  Applies after full TuneIn review + autostart delta; forward/reverse checks and
  all 114 candidate input hashes pass. This delta is included in the active
  four-patch continuity candidate above. No commit or publication.

## TuneIn native Cast autostart fixed and deployed — 2026-11-07

- User confirmed artwork, playback and Web control handover, then reported
  needing two Play presses at initial Cast startup. TuneIn-only scope retained.
- Live traces show initial native LOAD rejected as LIVE_SEEK_UNSUPPORTED for
  elapsed sender time; retry resolves but stays PAUSED with autoplay=false.
  Official receiver ignores those external handoff fields, starts at time zero,
  preloads internally, then plays after load. Independent protocol review agrees.
- Narrow provider fix normalizes native guideId LOAD to live edge/autoplay.
  No core or output changes. Explicit Pause/Stop, including during resolution,
  retain priority; direct URL loads preserve their original autoplay/offset.
- Regression reproduced before the fix. All 15 TuneIn tests and existing core
  controls_during_resolution_apply_to_the_new_load pass. Formatting and scoped
  TuneIn Clippy with --no-deps/-D warnings pass. An unscoped Clippy attempt hit
  the existing async_trait double_must_use lint in settings under Rust 1.99.
- Built locally from an immutable copy using Rust 1.98.0/Zig, GLIBC target 2.36;
  highest required symbol remains 2.34. All other 112 recorded frontend files
  and all 28 combined Python runtime files are unchanged. No laptop compilation.
- Native Cast TLS/bridge smoke: 15 checks pass, including autoplay=false with
  currentTime37.25 and currentTime0 both starting without a PLAY command,
  explicit Pause/Play, volume, failed-load recovery and station replacement.
  Public stations s80044/s24861, emulated output, no speaker/audio access.
- Build tunein-autostart-20261107-1 is active on the existing test laptop;
  binary SHA-256:
  16dcdc7aba9a504c2fcce314cc508f30eaace80fb695539bddcea7b1d55c7cc1.
  ABI/import preflight, live binary/28-file hashes and readiness 2/2 pass.
  Route IDs, existing image/environment and state retained. Rollback container:
  cast-audio-receiver-before-tunein-autostart-20261107-1.
- Manifests: .state/tunein-autostart-20261107-1/. Additive source delta:
  patches/vibecast-tunein-autostart-20261107.patch, applied after the complete
  TuneIn review snapshot; forward/reverse checks pass. Previous artifacts stay
  intact. No commit/publication. User's stock-app autostart retest pending.

## Decision: standard HA Cast controls, repeat requested upstream — 2026-11-07

- User chooses the standard Google Cast integration for HA controls. Goal:
  repeat Off/One/All for the active session. Receiver Lounge repeat exists, but
  generic Cast repeatMode mapping and upstream HA/PyChromecast support remain
  necessary; no universal device/app compatibility claim or completed feature.
- Deliberately exclude active YTM playlist/queue display and browsing in HA
  from current scope. Do not add a receiver-specific HA integration for it.
- User reviewed the simplified draft and explicitly approved publication.
  Published as Allcrafter1 in Integration enhancements:
  https://github.com/orgs/home-assistant/discussions/5464
  Title: Add repeat controls to the Google Cast integration.
  GitHub creation response confirms the approved body and discussion number.
- Correct destination: home-assistant/feature-requests GitHub Discussions,
  Integration enhancements, using its current discussion template rather than
  a Core bug issue. GitHub discussion searches for cast repeat and chromecast
  repeat returned zero matches; older forum media-loop requests are related
  but broader than active-session standard repeat control.
- Documentation/draft only; no runtime changes, tests or deployment required.

## Home Assistant Cast repeat / current queue feasibility — 2026-11-07

- Read-only source audit: stock HA Cast has no REPEAT_SET feature, repeat
  property or repeat setter. Its media browser delegates to media sources / Cast
  platforms; it does not expose the running YouTube Music queue. Advertising
  additional receiver capability bits alone cannot enable either feature.
- Maintained frontend already implements Lounge Off/One/All loop modes and
  queue video IDs. Its generic Cast QueueUpdateRequest currently requires jump
  and has no repeatMode field; the Cast path therefore needs an explicit bridge
  to Lounge repeat state as well as HA/PyChromecast support for standard Cast
  repeat control. Queue display additionally needs metadata and a HA-facing API.
- Live HA entity media_player.audio_lab_laptop_3 was playing TuneIn during this
  audit, with no repeat attribute / REPEAT_SET bit. This is not a live YTM test.
- Feasible follow-up choices: extend standard Cast support across the relevant
  layers, or add a receiver-specific HA integration for active-session repeat
  and queue access. Neither implemented, deployed or functionally tested here;
  no playback commands, runtime changes or new dependencies.
- Sources: HA core components/cast/media_player.py and PyChromecast
  controllers/media.py (current upstream); Google Cast Web Receiver queueing
  documentation (QUEUE_UPDATE repeatMode).

## Combined local candidate deployed for TuneIn testing — 2026-11-07

- User authorized combining all current unpublished work, compiling on this
  machine and transferring the result to the existing test laptop. Subsequent
  user clarification limits functional acceptance to TuneIn; Sonos and other
  services are included but are not part of this listening test.
- Candidate version: `0.7.0.dev1+local.20261107.tunein`, applied only in the frozen
  Python source copy. Shared source versions, release locks, App store metadata
  and public images remain unchanged. No commit or public release.
- Frontend source still exactly matches the complete TuneIn review snapshot
  `6556f01e6dcfc13ce67ef1ca491f7f52551faeb204ca64e0a919ff8160c27c49`,
  including concurrent playback, volume and TuneIn changes. Built locally with
  Rust 1.98.0 / Zig for `x86_64-unknown-linux-gnu.2.36`; highest required GLIBC
  symbol is 2.34. No compilation took place on the laptop.
- Deployed frontend SHA-256:
  `7a4d9c859784cbec61cfc236df156c0c144fed9d845a30994c4b7468ab84f4d6`.
- Froze the complete current Python runtime, including the final Sonos/DLNA
  cleanup/metadata changes, startup-volume policy, settings IPC and all assets.
  All 28 runtime files match the wheel byte-for-byte; compileall and wheel
  inventory passed. Wheel SHA-256:
  `bf48c336b083ef3fe52ef7920de05c71cdb5ca3ea737ef944a674e07fd3ced0f`.
- Verified binary startup and complete Python imports in the laptop's existing
  immutable image with network disabled, before stopping the running service.
  Activated a new container with the full candidate package and binary mounted
  read-only; preserved image, environment, output access and persistent state.
  Old file mounts were left untouched, and stopped-state data was backed up.
- Active container remains `cast-audio-receiver`; immediate rollback container
  is `cast-audio-receiver-before-combined-20261107-1`. Activation completed at
  20:37 UTC. Both enabled outputs report ready/responsive (2/2), original route
  IDs are unchanged, all 28 live Python/asset hashes and the binary match local
  artifacts, and restart count is zero.
- Local TuneIn-only smoke: 12 checks passed using public stations `s80044` and
  `s24861`, with metadata, replacement, controls and failure recovery, without
  audio output. `tools/test_tunein.py --tunein-only` omits the later DMR check.
- All build/source/deployment manifests are retained locally under
  `.state/combined-review-20261107-1/`. Stock TuneIn Android/Pro casting to
  `Audio Lab Laptop` and audible acceptance remain pending with the user.
- Future default: compile on this local host using the compatibility toolchain;
  use the laptop for staging, runtime validation and playback, not Rust builds.

## PR #16 / #17 remainder audit — 2026-11-07 (local, not deployed)

- Rechecked every original diff hunk. Added the complete disposition table to
  `docs/network-outputs.md`, including the intentionally omitted configurable
  cap: the requested policy has a fixed 25% fallback, not a configurable ceiling.
  Relay selection/direct radio, actual relay MIME/URL in DIDL, artist/album/
  artwork, title-only fallback, early SoCo import and cleanup are all accounted
  for; no additional unrelated feature exists in these two PR diffs.
- Corrected a remaining metadata fallback gap: SoCo's DIDLMetadataError is
  normalized to the existing title-only path. A failed playback command is not
  retried, avoiding duplicate playback. Added an actual SoCo-error regression
  and a supported-radio test that forbids constructing the bounded relay.
- Hardened common relay cleanup and both Sonos/DLNA Stop paths: cleanup failure
  cannot leave local state PLAYING or retain temporary media. Failed HTTP cleanup
  keeps an owned runner for retry; subsequent start finishes that cleanup before
  publishing a fresh URL. Added failure/retry/next-start tests for both backends.
- Correction to the previous validation claim: the two real conversion tests
  were skipped without FFmpeg/ffprobe; the previous summary overstated local
  conversion verification. Supplied FFmpeg/ffprobe 7.0.2 only in a temporary
  test directory and reran the affected suite with that directory on PATH.
- Final result: 71 passed, zero skipped, 14 subtests. This includes actual
  Opus/WebM -> MP3 via HTTP relay and ffprobe checks for codec, stereo, 44.1kHz
  and duration, plus range serving, metadata, lifecycle and volume regressions.
  Compileall and diff checks pass. No project dependency/version changed.
- No GitHub merge, deployment or physical Sonos test. The earlier unrelated
  private-marker failure in full source export remains a separate known issue.

## Desktop web controls after background tab — 2026-11-07 (reload restores controls)

- Decision confirmed by user: classify the demonstrated UI and synchronous
  Cast-error/fallback defects as upstream YTM Web limitations, not receiver
  fixes. Closed for receiver workaround development absent new contrary
  evidence. See `TESTING.md` known-web-limitations section before investigating
  these symptoms again. Original Chrome detach trigger remains unknown.
- User reports delayed resynchronization after returning to YTM Web, then no
  Pause response while HA still controls playback. Audio changes are out of scope.
- Live `.110`: at19:58:05UTC remoteDisconnected, at19:58:11.94 remoteConnected
  and getNowPlaying/getVolume/getLoopMode. Feedback HTTP completes in284ms,
  followed by58/61/57ms posts; routine state posts ~50–80ms. Browser trace
  confirms onStateChange arriving every second and proxyState1/playerState1.
- Browser screen suffix a18965 matches current receiver music identity. At
  20:08:02.276 browser sends next; receiver receives it at20:08:02.522UTC.
  Pause does not reach either receiver Cast or Lounge command path.
- Expanded browser exception identifies the immediate failure:
  InvalidStateError in PresentationConnection.send, connection disconnected,
  cast_sender.js -> media.pause -> remote.js -> player.pauseVideo. The YTM
  remote script calls Cast media.pause when a Cast media object exists;
  its MDX fallback is an error callback, which a synchronous throw bypasses.
  Thus live Lounge feedback and broken Cast controls can coexist. This is not
  evidence that the new feedback queue blocks commands.
- Original desktop TCP peer `.91:61250` remains ESTABLISHED on `.110:37181`;
  no corresponding close/takeover observed in the incident interval. A Chrome
  page PresentationConnection is distinct from the browser-to-receiver socket.
  Why Chrome detached that page connection remains unknown; do not claim a
  proven background-tab suspension cause or receiver regression.
- Verified latest published pre-release through GitHub: v0.7.0-dev1, matching
  local frontend base85918111ac68cbf837bf58835b5fd066615963ad. Reviewed local
  Lounge feedback changes against that base. 46 Lounge tests pass (local mock
  ports require execution outside sandbox); this does not reproduce Chrome.
- User confirms full page reload restores controls. Reports separate missing
  current-title display until selecting a song. At20:11:17.639UTC the returning
  browser explicitly requests getNowPlaying; the next feedback POST completes
  at20:11:17.904 (264ms). Thus this instance is not simply a missing status query.
  Subsequent browser snapshot confirms valid remote videoId, state1, position,
  duration188 and matching seekable end, but index null. A direct getNowPlaying
  query did not repair the UI. Comparison of local player video_id and remote
  videoId returns [null, validRemoteId]: no locally selected video after reload.
- remoteConnected is currently ignored; periodic onStateChange omits videoId,
  while getNowPlaying returns identity plus state. Proactive reconnect snapshots
  could cover a missing query, but cannot yet be claimed to fix this observed
  case where the query did arrive. Do not implement a speculative timer/push loop.
- Inspected the exact public YTM app build from the user's exception:
  `yt_music_web.en_US.I6PQRHpqgd8.es5.O`, remote player `a5c2aafe`.
  App line15978 remoteQueueChangeDebouncer dispatches SET_REMOTE_WATCH_ENDPOINT
  only when remote videoId AND N_(store state) exist. N_ selects a preloaded
  endpoint or selected local queue item's navigationEndpoint (lines10476,
  15916–15922). With neither, remote title updates cannot initialize the UI.
  This is a concrete source-level explanation consistent with the user's
  empty-local/valid-remote observation; store internals were not live inspected.
  The branch does not use currentIndex. Repeated status pushes cannot satisfy
  the missing-local-endpoint guard. No browser injection or fake playback.
- Independently reproduced missing currentIndex in temporary Google Lounge
  receiver/sender sessions (no user account or live receiver identity reused).
  Sending currentIndex0 and4 in nowPlaying yields received messages without the
  key. Alternative unknown index keys pass through but are not consumed by YTM;
  playlistModified also does not preserve currentIndex. Do not rename fields
  speculatively. The live binary SHA matches the19:16 deployed artifact and
  contains the expected outgoing currentIndex field. Protocol test secrets
  remained in memory and were not printed. Probe: /tmp/lounge-status-probe.py.
- Exact historical cause of Chrome's page PresentationConnection detachment
  remains undetermined after reload; receiver logs contain no matching closure.
  Distinguish confirmed browser exception/missing fallback from attribution of
  the original detach. Receiver has no direct way to repair Chrome's page object.
  No receiver patch/deployment/release for this incident. Do not add unsolicited
  server disconnects, weaken sender takeover, or inject browser code as a fix.

## PR #16 / #17 output integration — 2026-11-07 (local, not deployed)

- Reviewed zero00zero's PR bodies, comments and diffs: #16 head
  `24eaab5456843ed3c5f1ba51983b06d0c484875a`, #17 head
  `afc574abbe2bd3544c3815e979be9a08ff3b62c2`. Integrated their intent rather
  than stacking the conflicting launch cap and Sonos-only adoption policies.
- Shared startup rule reads actual backend volume/mute; positive unmuted values
  (including >25%) are adopted without writing. Zero, mute, unavailable/invalid
  readings use 25% unmuted. Query timeout/cancellation and failed fallback writes
  are covered; failed writes prevent audio. Default backend/mpv startup gain is
  25%. New-session setup does not reset volume on ordinary track changes.
- Bridge Volume has an explicit initialize flag on launch versus sender writes.
  The Python adapter handles LOAD without a launch, conservative older-frontends,
  Stop/reconnect and takeover, while preserving existing volume revisions and
  deliberate pre-load user adjustments. The old frontend zero-to-10% hint is
  now 25% and includes muted startup. Actual output reads remain authoritative.
- Sonos/DLNA read physical output state; mpv reads its live player properties.
  AirPlay's existing adapter has no pre-start query, so uses the fallback;
  DACP/remote feedback remains intact and device-dependent. Free-form command
  output cannot control volume and now fails initialization/volume commands
  instead of claiming a physically safe level. Null remains simulated.
- Sonos now reuses the existing bounded DLNA relay for unsupported/loopback
  formats and sends escaped music-track DIDL with artist/album/artwork plus the
  actual play URL/MIME. Supported remote media/radio remains direct. Whole-file
  conversion latency, finite-size/time bounds and device codec limits remain.
- Sonos RenderingControl subscriptions use a thread-safe queue handoff, renewal,
  old-generation rejection and ordered unsubscribe after cancelled subscribe.
  Five-second polling is fallback until actual NOTIFY delivery or on failure;
  a 60-second silence watchdog reconciles/re-subscribes. Volume-only read errors
  do not terminate playback. Sonos and DLNA retain monitoring after natural EOF
  until Cast Stop. Existing DLNA polling, mpv events and AirPlay callbacks remain.
- Evidence: author confirms daily Sonos AirPlay use (Era 100 and “Play”) and the
  physical 100% Era 100 incident, but explicitly not direct Sonos hardware tests
  or physical acceptance of either PR fix. README/network-output docs/testing/
  packaging/changelog now distinguish those facts. No speaker was accessed here.
- Validation: full Python run 412 passed, 13 skipped, 81 subtests; one pre-existing
  source-export failure rejects private machine markers in the already-dirty
  working plan. Existing work/rollback notes are preserved, not silently removed
  to make export green. Final scoped output/player regression after refinements:
  151 passed, 2 skipped, 32 subtests. Additional final natural-EOF monitoring test:
  volume-policy suite 15 passed, 10 subtests. Metadata escaping/fallback,
  cancellation, feedback and safety cases pass. The real FFmpeg conversion
  cases were skipped in this first run; see the remainder-audit correction and
  successful real conversion run above. Compileall/diff checks pass.
- Rust core/player-api tests: 135 passed, 2 existing live probes ignored. Scoped
  Rust 2021 format checks pass. Other concurrent workspace work is preserved.
- Frontend delta is `patches/vibecast-output-volume-integration-20261107.patch`,
  SHA-256 `23d18dda663e8793ed80eb7a0eee48ef333b1b335bf2e9562d52d0ae5d0518b9`.
  Apply AFTER the playback-coordination review snapshot above base
  `85918111ac68cbf837bf58835b5fd066615963ad`; exact forward reconstruction and
  reverse-apply check passed. It contains only the three affected Rust files,
  not unrelated work. Release locks/version are deliberately unchanged.
- Status: implemented and automatically tested locally; no GitHub merge, release,
  deployment, or new physical acceptance. Remaining hardware checklist and
  known protocol/format limits are in `docs/network-outputs.md`.

## TuneIn Radio / issue 8 — 2026-11-07 (built and locally tested)

- User requested a dedicated receiver for casting from the TuneIn Android app,
  preserving all concurrent unpublished work. Work is in the maintained product
  and frontend checkouts; the historical research checkout is unchanged.
- Implemented an SDK app provider for `12F05308`, using the current official
  receiver's standard media LOAD and top-level TuneIn customData. Resolve live
  station IDs through TuneIn, retain initial metadata, and reuse shared controls.
- Retained the existing release pin and other agents' review snapshots. The
  final source includes concurrent output-volume integration without overwriting
  it. A frozen review source produced the separately stored local executable
  `.state/tunein-review-20261107/vibecast`, SHA-256
  `5ae7431d57586430dd5cf8f2d2a8167d582afbe19a2ecbe107f72b1cc1e91f98`.
- Validation: 402 Rust tests passed, 3 existing live probes ignored; TuneIn
  15/15, scoped Clippy and formatting passed. Real isolated Cast/bridge smoke
  passed all 14 checks, with public station resolution/switching, controls,
  invalid-load recovery and DMR takeover. A short real stream decoded through
  FFmpeg to null without opening an audio device.
- Python: 429 run, 13 skipped, 415 passed, one pre-existing source-export failure
  from private machine markers in older notes. New TuneIn source/export text
  checks pass; unrelated notes are preserved.
- Feature delta `patches/vibecast-tunein-receiver.patch` SHA-256
  `5a2134c30763fd25ddef510e4665fca3a0e6f16017077ee90e6694ca2fc92847`;
  full candidate `patches/vibecast-tunein-review-20261107.patch` SHA-256
  `6556f01e6dcfc13ce67ef1ca491f7f52551faeb204ca64e0a919ff8160c27c49`,
  over `85918111ac68cbf837bf58835b5fd066615963ad`; apply checks passed.
- No publication, production restart or issue closure. Stock TuneIn Android/Pro
  acceptance remains pending; Premium, on-demand, preroll sequences and periodic
  metadata refresh are outside this first live-radio implementation.
- Detailed protocol evidence, automated results and acceptance limits:
  [TuneIn receiver](tunein-receiver.md).

## Google CDN / native playback research — 2026-11-07 (no runtime changes)

- Google documents GGC caches inside ISP networks, with cache fill from other
  caches/core. Cache placement and per-playback delivery pacing are separate.
  Source: https://support.google.com/interconnect/answer/9058809
- Google's 2012 Trickle paper explicitly describes fast initial buffering then
  delivery near encoding rate, to avoid unused downloads and network bursts.
  This establishes the design principle, NOT today's exact server algorithm or
  the cause of our measured slow URLs. Historical buffer/rate constants must not
  become current receiver defaults.
  https://developers.google.com/speed/protocols/trickle-tech-report.pdf
- Current reverse-engineered SABR request schemas carry player time, time since
  seek, bandwidth estimate, buffered time ranges and prefetch state; server policy
  carries target/minimum readahead, backoff and playback cookie. Our progressive
  GET/range path does not exchange this SABR feedback. Lounge state reporting is
  a separate control path, not equivalent media-server buffer feedback.
  https://github.com/LuanRT/googlevideo/tree/c0e73b283310c771cddc5af8993f0e6b55a7578e/protos/video_streaming
- Do not assume the user's successful native YTM playback uses SABR without a
  client trace. Different formats, prebuffered targets, authentication and host
  selection remain alternatives. CTT authorization is not a fast-delivery flag.
- SABR supports audio-only but requires a transport/segment adapter and session
  bootstrap/reload integration. googlevideo has no demonstrated CTT integration;
  its mpv example limits VOD seeking to already buffered segments. Adopting it
  alone would not establish arbitrary fast seeks. No SABR rewrite authorized.
- Next evidence: compare native start and seek into an unbuffered region against
  receiver on the same title, recording protocol/request shape, format, timing
  and buffer reserve without persisting credentials. Audit resolver-to-download
  client/header consistency before controlled A/B changes. Do not infer bandwidth
  capacity from server-paced average throughput or trigger reload solely because
  a well-buffered source is slower than the access line. Keep prompt draining of
  open responses; avoid another artificial slow-reader implementation.

## Slow Googlevideo delivery investigation — 2026-11-07 (read-only probes)

- User reports gigabit access and asks for the cause rather than more playback
  workarounds. Do not equate access-line capacity with one CDN connection, or
  call this incident a proven HTTP429/rate-limit event.
- Independent `.110` probes bypassed Rust cache, receiver and mpv. yt-dlp
  resolved public `1yEfeQr4zOw`, itag251, 3,241,987 bytes; URL and request headers
  stayed only in probe memory. No tokens/cookies/signed URLs were printed/saved.
  These probes were separately resolved without the live sender CTT, so are
  evidence of independent slow delivery, not exact replay of the original URL.
- Same-URL comparison with extractor headers: Range header0–8MiB returned206,
  1,081,344 bytes after22.225s, successive5s windows ~80,364/64,556/39,468/17,777B/s.
  Query range0–8MiB returned200,1,605,632 bytes after22.388s, windows
  ~117,606/91,437/50,093/34,489B/s. Merely using query range did not remove decay.
  A1MiB header request completed in4.509s.
- Reversed-order comparison on another single fresh URL: initial1MiB8.222s;
  large request1,556,480 bytes after23.286s with windows
  ~136,299/86,621/42,413/22,328B/s; subsequent1MiB at offset1MiB took15.457s.
  Smaller requests are NOT established as a reliable cure; latency variation
  prevents attributing the difference solely to request size.
- Raw anonymous Android metadata URLs were separately rejected403 on direct
  tests; IPv4-pinned resolution/download also rejected403. Those are different
  authorization cases and cannot explain successful slow live206 responses.
  Do not infer IPv6 causality from these incomparable probes.
- Primary comparison: yt-dlp HTTP downloader uses bounded Range headers;
  YouTube.js uses range query. yt-dlp issue17612 describes throttling above a
  much larger response threshold, so it is not direct proof for our1.5–3MiB
  objects. Sources: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/downloader/http.py
  https://github.com/LuanRT/YouTube.js/blob/main/src/utils/FormatUtils.ts
  https://github.com/yt-dlp/yt-dlp/issues/17612
- Conclusion: source-delivery slowdown reproduced independently of our playback
  implementation, with burst then decay resembling pacing. Exact server/client/
  route condition remains unproven. No production settings/code/deployment changed
  in this investigation; do not replace this uncertainty with a speculative fix.

## Playback coordination follow-up — 2026-11-07 (deployed, acceptance pending)

- User confirms immediate start after the preceding cache change, but reports
  intermittent poor seeking and delayed desktop position feedback. This is not
  acceptance of the complete playback behavior. Review spans cache scheduling,
  decoder state, shared recovery and Lounge feedback, preserving other outputs.
- Live evidence: 19:01:21 seek to 79s creates reader at byte 1,228,576, but the
  reported position remains 79s until 19:01:33. During the wait, the adapter
  incorrectly reports PLAYING. At 19:00:32 Lounge reports an HTTP interruption
  while local position reports continue normally. These are distinct paths.
- Confirmed cache regression: symmetric adjacent-block exclusion also excludes
  a missing block behind the current download. Correct to directional handling.
  Investigate blocked origin-header wait and coarse 128KiB internal blocks;
  retain 8MiB HTTP requests, not tiny origin downloads. Actual decoder range
  requests remain necessary; the cache cannot observe seeks inside mpv.
- Confirmed status defects: mpv acknowledges a seek before playback restarts,
  but our state omitted the seeking flag. Initial file-loaded also precedes
  decoder restart. Keep active seeks/startup BUFFERING until playback-restart;
  explicit Pause still wins. Reassess old source-speed evidence at explicit
  seek so the corrected BUFFERING cannot trigger stale-source recovery.
- Lounge currently awaits feedback POSTs while playback reports queue in a
  bounded FIFO; try_send silently drops newest states on overflow. Fix by
  polling one in-flight POST alongside the existing event loop, coalescing
  outgoing snapshots while applying transitions locally without loss; keep
  consuming reports/worker events during reconnect. Preserve cancellation,
  real sender takeovers, volume quiet period, queue advance and retry budget.
- Implemented: directional missing-block priority, interruptible origin-header
  wait (original 15s deadline retained), internal 16KiB blocks / unchanged 8MiB
  origin requests. `begin_seek()` starts a new rate-measurement epoch, including
  atomic rejection of stale samples. Hard cache failures remain actionable.
- Real mpv 0.35.1 probe on `.110`, separate localhost origin/IPC and null audio:
  native seek ACK occurs immediately while execute-seek waits for blocked packet
  read. Reopening the same cache URL interrupts that read. Added one cancellable
  fallback after 1s without playback-restart, only for owned local cache URLs;
  preserve latest target, pause intent and volume. LOAD/Seek/Stop/shutdown cancel
  the fallback, including an in-flight reopen. No YouTube resolution, cache
  eviction or extra source-retry round. Actual modified adapter restarted near
  61s after ~1.24s while the old origin read remained blocked. Initial paused
  LOAD also emits playback-restart, validating the readiness gate.
- Lounge now polls one feedback POST concurrently with the existing event loop;
  at most one pending snapshot per six feedback kinds. Playback transitions are
  processed before coalescing outgoing snapshots. Lossless bounded ingress and
  report/worker draining during reconnect prevent the former silent BUFFERING
  loss. Safe POST stage/duration diagnostics do not log URL/body/credentials.
- Validation: combined Rust core/YouTube 252 passed, 3 existing probes ignored;
  cache subset 46 passed / 2 ignored. Combined Python playback/output regression
  128 passed, 1 skipped, 42 subtests. Scoped Clippy passes with existing baseline
  allowances; format/diff checks pass. Native null-audio reproduction and modified
  adapter test passed; this is not an audible acceptance test of every output.
- Locally compiled binary deployed on `.110` ~19:16 UTC, health 2/2 ready:
  `69812e1b849ef0f0745098a1eb1a4ab27462e1bf2b165b92d1e7ce754e15a3c7`.
  Updated mpv adapter SHA-256:
  `3b609dea09bb19678cbf3b904671bc3a31b7f1b6e83c473e86f984cf7d7e4a1f`.
  Rollbacks: `/home/test laptop/vibecast-round3-review.rollback-before-playback-coordination-20261107`
  and `/home/test laptop/mpv_backend.rollback-before-playback-coordination-20261107.py`.
  Other Python adapters unchanged; shared Rust fixes apply wherever used.
- Full frontend snapshot `patches/vibecast-playback-coordination-review-20261107.patch`
  over `85918111ac68cbf837bf58835b5fd066615963ad`, SHA-256
  `138c993cf70dba91cd40b8c6cd0335d8f16ca013e015e08f992058704d93834c`;
  reverse-apply validated. This supersedes the prior seek review snapshot as the
  current candidate, not a release lock. User asked to test reconnect, repeated
  forward/back seeking, timely position feedback and Pause during loading.
- First live logs after deployment: feedback POSTs in the sampled 19:17:39–44
  window complete in 55–249ms; a seek to 87s at 19:17:52.808 reports BUFFERING
  then PLAYING at 52.824 with subsequent advancing position. A seek during next
  title startup at 19:17:57.396 remains BUFFERING until 19:18:00.184, then advances.
  Do not turn these samples into a latency guarantee or audible user acceptance.
- Remaining scope: original YouTube source slowness is still unexplained; do not
  label it rate limiting. Active range prioritization does not solve every
  theoretical multi-reader scheduling case, and final response-tail validation
  retains its timeout. No decoder-wide/network-wide aggressive timeout or full
  yt-dlp streaming redesign. No publication; live acceptance still pending.

## Slow cold resume — 2026-11-07 evening (deployed, acceptance pending)

- User reports delayed playback after connecting, then renewed buffering.
  `.110` logs for 18:45–18:49 UTC show `1yEfeQr4zOw`, initial position 121s,
  3,241,987 bytes / 188s. Direct CTT resolution succeeds (1480ms), proactive
  refresh succeeds (229ms), then final fresh playback resolves in 147ms at
  position 138.2145s. This is not an absent retry or failed authorization.
- Both original and refreshed sources deliver approximately 14.7–16.4 KB/s
  during measured ten-second windows. No 403/429 is evidenced in this incident.
  The underlying slow-source cause is unresolved; do not attribute it to IPv6,
  rate limiting, a missing PO token or an untransformed `n` without evidence.
- Confirmed local scheduling weakness: a fresh cache starts at byte zero and
  drains an open 8MiB range before considering distant reader demand. A cold
  recovery near the end can therefore wait for redundant prefix downloading.
  Implemented prioritization of actual nonsequential reader demand while
  preserving ordinary eager sequential draining and the two-recovery budget.
  One initial missing-data priority per HTTP reader; newer demand supersedes
  older priority, adjacent blocks retain the open response, partial bytes stay
  cached. Drop/Cancel clears priority; cancellation races are guarded. A new
  target range gets its own throughput window instead of inheriting slow-prefix
  health. This needs an actual decoder range request, not an estimated byte
  position from playback time.
- ffindog's inspected main output passes the resolved URL directly to mpv, so
  its player controls range reads; it has no equivalent Rust prefix queue.
  It validates streams and uses YouTube.js decipher; later playback failures
  may skip/stop rather than perform our same-title recovery. Android client
  identity alone does not prove a JS challenge. Add only safe URL-characteristic
  booleans/format diagnostics pending actual evidence; no signed URL or tokens.
- Reproduced slow-prefix/distant-reader timeout before the fix. Afterward,
  cache suite 42 passed / 2 existing real-mpv probes ignored; broad core/YouTube
  suite 245 passed / 3 ignored. Scoped Clippy passes with the existing baseline
  allowances; formatting/diff checks pass. Tests cover partial backfill integrity,
  normal sequential requests, competing readers, cancellation and recovery.
- Locally built candidate deployed on `.110` at approximately 18:59 UTC;
  health confirms 2/2 outputs ready. Binary SHA-256:
  `9a7101484d8dde3dac84147e88a1e0760e01d7a0d37f714cb7caa074bd31c92a`.
  Rollback is `/home/test laptop/vibecast-round3-review.rollback-before-seek-priority-20261107`
  (previous volume candidate `85efe0af...`). No Python/output adapter changes.
- Full frontend review snapshot `patches/vibecast-seek-priority-review-20261107.patch`
  over `85918111ac68cbf837bf58835b5fd066615963ad`, SHA-256
  `a5806a0caec192f8ac8998875dc54b3d0e81a4dda5af2df8bf0558146bb3da0a`;
  reverse-apply check passed. Supersedes the earlier volume-only review snapshot
  as the current candidate; neither is a release source lock.
- User test requested: reconnect, same affected track and seek to about 120s.
  Live logs at 19:00:12 UTC already show the same affected title's decoder
  requesting byte 2,423,375; cache immediately prioritizes block byte 2,359,296.
  Cache completes at 19:00:48 (3,241,987 bytes). No renewed slow-source/recovery
  message in that observed window. Selected title and next-item URLs both have
  `has_n=false`, excluding an untransformed n for these new resolutions (not
  retroactively proving the original URL's properties). Audible user acceptance
  remains pending. Original source-slowness cause is unresolved; do not claim
  all playback failures solved. No release.

## Volume slider: final live findings and scope — 2026-11-07

- User confirmed: without Cast and without the console workaround, the YTM Web
  slider works normally. During Cast, the temporary browser drag guard eliminates
  the jumping. This confirms the tested workaround, not a receiver-only cure.
- User also reproduced the same fundamental slider jumping on an original Cast
  receiver, usually but not every time. Frequency/timing may differ; no controlled
  performance comparison was made. Here "skipping" refers to the volume slider
  jumping, not playlist navigation or skipped tracks.
- Together with the inspected connected-only slider feedback path, this supports
  classifying the remaining symptom as a YouTube Music Web UI defect rather than
  a bug specific to this receiver. User accepts documenting this limitation;
  stop further speculative receiver changes to work around the website.
- Receiver-side volume scaling is live-confirmed. Existing acknowledgement
  ordering and Lounge coalescing changes remain in the unreleased candidate;
  do not describe them as fixing the website's drag behavior on their own.
- A Cast receiver cannot inject JavaScript into the sender's YouTube HTTPS page
  through the Cast protocol. Google/YouTube can fix its own website; a user can
  optionally run page-local code or install an appropriate browser userscript.
  The console test is temporary and disappears on reload. The prepared helper
  is optional and not automatically installed; no permanent browser installation
  or additional deployment was requested or performed.
- No publication authorized by this acceptance of the diagnosis. Current `.110`
  candidate and review snapshot remain as recorded below. This section supersedes
  the earlier pending-test statements.

## YouTube Music Web volume correction — 2026-11-07 (unreleased)

- User authorized both web-only curve compensation and the separate feedback
  ordering fix, including a default-enabled, per-output Web UI switch. No release
  before the user's laptop test. First candidate deployed on `.110` at
  2026-11-07 10:22:24 UTC; health 2/2. User confirmed volume scaling feels correct
  but the slider still jumps. Later live findings above close the investigation
  as a website limitation with a confirmed browser workaround; do not claim a
  receiver-only fix or publish without separate authorization.
- Keep canonical receiver/output volume unchanged. App-owned SDK hooks decode
  incoming YTM Web volume and project Cast receiver/media feedback per recipient.
  Eligibility requires a desktop Chromium owner connection plus exactly one
  positively identified `youtube.m-desktop` Lounge controller. Unknown/mixed
  controllers, regular YouTube, HA and mobile retain ordinary volume. Retired
  Lounge epochs cannot re-enable a profile after takeover.
- Lounge volume feedback applies the matching forward curve. Typed YouTube
  `web_volume_compatibility` defaults true, is player-scoped and uses the existing
  settings service as sole persistence. Management relays settings through the
  owned adapter process; changing the option does not restart playback.
- Opt-in `volumeRevisions` orders output-wide volume commands and their reports.
  Python advances the applied revision after backend level/mute writes complete.
  Core rejects stale volume/mute acknowledgements while retaining playback data;
  legacy players keep their original protocol behavior. Genuine device changes
  following the latest command remain accepted. This does not claim to identify
  uncorrelated hardware echoes arriving after a backend acknowledges completion.
- Management/UI checks passed: 80 focused tests covering route/process lifecycle,
  settings HTTP/stdio round trips and conflict handling, adapter behavior, browser
  toggle revisions, and source/wheel inventory. The settings control reads live
  receiver snapshots; disabled/disconnected outputs cannot be edited. No duplicate
  settings configuration is written to route storage.
- Output audit: mpv applies cubic amplitude gain; native AirPlay maps positive
  percentages to -30 + 0.3*percent dB (zero is mute). Sonos/DLNA use the device's
  own curve. No output curve or audio cache transformation is changed. The
  generic Command backend's existing status-only volume limitation remains.
- Regular YouTube uses a different slider mapping from YTM; never apply YTM's
  exponential inverse to all Chrome senders. Research was a behavioral reference,
  not copied third-party implementation code.
- First candidate receiver SHA-256:
  `16eeb9b8d895b91544ffba4428836161e8aced683f8c920ec4a0137b799ddafe`;
  Python player `b89b768bbdaf1729033e3ef52e383f7213d46009ddf2f9c644cb7274f2dc7ed3`.
  Both enabled outputs ready, settings API reports the default-enabled option,
  live Lounge classification positively identified YTM Web at 10:23:07 UTC.
  Rollback: `/home/test laptop/web-volume-20261107-rollback`.
  New `settings_ipc.py` and UI CSS are installed into the test container as well
  as staged on the host; the existing Python file mounts remain in use.
- Broad Rust regression: 371 tests passed, three existing ignored; additional
  SDK and actual YouTube takeover-hook tests passed. Python settings/player/web
  follow-up: 37 passed, two subtests. Clippy passes with existing resolver
  dead-code/unused-variable and existing style allowances; formatting/diff checks
  pass. Build performed locally using the existing glibc-compatible Zig toolchain.
- Reproducible current frontend diff, including earlier unreleased fixes,
  is `patches/vibecast-web-volume-review-20261107.patch` over
  `85918111ac68cbf837bf58835b5fd066615963ad`, SHA-256
  `614027cc680fe1e3e98c8d29e944da7394465ff97c247fb09d848567d5010b66`.
  This is a review snapshot, not the release source lock. Includes the second
  candidate below; validate/freeze the full source set before a future image.
- Follow-up: ordering revisions solve stale player acknowledgements, but Lounge
  still posts intermediate volume values over its separate HTTP feedback path.
  Added a nonblocking web-only 330 ms quiet-period coalescing step. Playback and
  controls remain immediate; only the latest volume/mute is posted after dragging
  settles. `getVolume` cannot bypass an active quiet period. This feedback fix is
  independent of the curve toggle, since the user also reproduced jumping with
  the browser's exponential flag disabled. Safe debug logging records only
  canonical/wire volume percentages and mute, never credentials.
- Second candidate active on `.110` since 2026-11-07 10:27:53 UTC; health 2/2,
  receiver `85efe0afbbc031422cd765192fb1aec7ee905529a45eacff2cbb316f458bc0fb`.
  Python files unchanged from candidate one. First candidate binary additionally
  backed up as `web-volume-20261107-rollback/vibecast-r1`. Full YouTube suite:
  135 passed, one existing ignored; temporal regression proves latest-only volume
  feedback while Pause/playback status stay immediate and non-web feedback keeps
  its previous timing. Clippy (same baseline allowances), formatting and patch
  reverse-application checks pass. User's second slider test still shows pronounced
  jumping while holding the mouse button; no release. Curve correction remains
  accepted.
- Investigation after second test: inspected Google remote module ignores media
  status volume, but receiver-status volume updates its remote context. The
  one-second guard restarts only if rounded local volume differs from that
  context. Its timer then writes the context back to the player/UI. Do not remove
  Cast acknowledgements or indefinitely delay them: sender requests can time out.
  Requested a volume-only browser trace to distinguish direct Cast feedback,
  backend echoes and UI quantization before another behavioral change.
- Browser trace received: Cast confirmations match the requested wire levels
  (floating-point differences are insignificant). The same-millisecond `5,4`
  player events are explained by Google's remote timer: it removes its outgoing
  volume listener, calls unMute (minimum volume 5), then setVolume(4), and restores
  the listener. Likewise `22,22` is not evidence of duplicate receiver commands.
  Debug logging has a buffered replay mechanism; clustered log callbacks and
  different module-relative time origins do not prove receiver/network backlog.
- Website mechanism verified in public YTM source: disconnected updateVolume
  retains the requested UI value, while connected onVolumeChange inverse-maps
  the player's integer volume into the bound slider value. `_updateKnob` then
  rewrites immediateValue and the drag anchor even while dragging. This happens
  locally and cannot be removed by delaying receiver acknowledgements.
- Requested disconnected comparison and a temporary page-local `_updateKnob`
  guard while dragging. No further receiver deployment. A reversible optional
  helper is prepared in `tools/ytmusic-volume-drag-guard.js`; it only targets YTM
  volume sliders, preserves pointer/audio commands and feedback outside dragging,
  and is NOT injected/installed automatically. Syntax and Node harness checks
  for drag/release, repeat installation and restoration passed. User subsequently
  confirmed that the temporary guard fixes the jumping during Cast; no persistent
  browser installation was performed.

## Web-only volume scaling and feedback investigation — 2026-11-07

- Investigation only; no runtime, volume mapping or protocol changes deployed.
  `.110` still runs receiver `618191e9d33a9ecbcf73ef10995ab951c1a3511cbace9d6beb13b398dd3eee9a`
  and mpv adapter `6960d4418c9ff7b02a464a715dfa39e269ad377b81a25baf25da7f67ca866f27`.
  Runtime mpv is 0.35.1. User observes nonlinear control and slider jumps only
  on YTM Web, with HA and mobile app working satisfactorily.
- Current receiver passes Cast volume 0..1 unchanged to the output; mpv adapter
  multiplies it by 100 and divides observed properties by 100. mpv itself uses
  cubic amplitude gain, `(volume/100)^3`, verified in its exact v0.35.1 source:
  https://github.com/mpv-player/mpv/blob/v0.35.1/player/audio.c#L150
  This is signal amplitude, not perceived loudness. HA's Cast integration forwards
  the requested normalized value directly to PyChromecast, without this web
  transformation. Mobile logs show ordinary Cast SET_VOLUME too; its exact
  slider-position-to-wire mapping has NOT been measured and must not be claimed
  identical to HA solely from the user's satisfactory experience.
- User confirmed `ytcfg.get("EXPERIMENT_FLAGS").music_web_enable_exponential_volume_control`
  is true. Current public YTM application build 366b12ee maps a UI position s
  to `clamp(2^(0.03917*s+2.82823)-7.13431,0,100)` before calling setVolume.
  The remote module rounds that percentage and sends normalized Cast level.
  Web positions 25/50/75/90 consequently send about .07/.20/.47/.75. At .20,
  the receiver requests mpv20 and obtains .008 relative signal amplitude;
  HA50 instead requests mpv50 and obtains .125. The confirmed extra web curve
  combined with mpv's curve explains the strongly compressed low range.
  Incoming Cast and Lounge percentages are converted back by the web inverse
  curve. Integer percentage rounding is particularly visible near the low end.
- Primary public research references (behavior/format reference, no copied
  implementation introduced into the product):
  https://music.youtube.com/s/366b12ee/music_polymer_inlined_html.js
  https://www.youtube.com/s/player/a5c2aafe/player_es6.vflset/en_US/remote.js
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/cast/media_player.py#L542
  https://developers.google.com/cast/docs/reference/web_sender/chrome.cast.Volume
  Research snapshots are in `/tmp/ytmusic-volume-review.{html,js}` and
  `/tmp/youtube-volume-remote.js`; JS hashes respectively
  `658174644890a3a5310110d9e4f157c36d8e30beda50eca742d3477228e55a92` and
  `f9ff31fa15bb863960687675a2efca37a996f2ed31423bc1f6cf5647d18e4fd5`.
- Feedback audit: core immediately publishes each requested volume, then accepts
  any player State volume/mute as authoritative, before the media-staleness gate.
  A delayed .4 report after a newer .6 request therefore republishes .4 to Cast
  and Lounge; a later .6 report restores .6. Python's FIFO command execution
  does not order already in-flight reports in the reverse direction. Periodic
  reporting and separate mpv volume/mute notifications create intermediate
  snapshots. Existing core regression
  `correlated_old_reports_and_controls_cannot_finish_or_stop_a_replacement`
  passes and explicitly permits output-wide volume from old media reports.
  This establishes the ordering gap, not yet a captured live cause of every
  web drag jump. Do not incorrectly filter volume by mediaSessionId.
- Web remote code already suppresses volume synchronization during a restarted
  one-second interaction guard. ffindog separately debounces confirmations by
  330 ms after changes; its comments describe stale-confirmation jumping:
  https://github.com/ffindog/ytm-cast-receiver/blob/992cb673ccb94fc121d202772960c050a3928d65/ytcr-player/MpvPlayer.mjs#L545
  A debounce alone cannot distinguish a delayed command echo from a fresh
  physical volume change. Recommended ordering fix: optional output-wide volume
  command revisions, applied revision in reports, opt-in/legacy fallback;
  ignore only older volume/mute acknowledgements while preserving playback and
  genuine external controls. This is a proposed follow-up, not implemented.
- Do not globally linearize mpv or invert all incoming levels: that changes HA,
  the working app and other outputs. A web-specific compensation requires a
  reliable sender/curve selection AND matching outgoing feedback projection.
  Cast's 0..1 value does not encode the web experiment flag; controlType does
  not negotiate this curve in the inspected YTM implementation.
  A temporary browser-only comparison was offered by setting that flag false
  in the current tab (reload restores it). User confirmed that volume adjustment
  then feels more appropriate, but the slider still jumps. This isolates the
  scaling problem from the separate feedback/interaction problem without changing
  HA, the app, or the receiver's volume contract.
- Follow-up feasibility: inverse curve arithmetic is small; a correct integration
  must retain the existing logical receiver volume, decode only explicitly
  identified curve-enabled web input, and encode that same curve for web feedback
  while HA/mobile retain ordinary values. Current Cast profiles retain SDK and
  observer facts, not the YTM experiment flag; raw volume cannot identify it.
  A browser user-agent alone also cannot establish which tab/experiment/toolbar
  initiated a receiver-level change. Avoid claiming fully automatic universal
  detection. A selectable web compatibility profile or client-side removal of
  the extra curve is more honest than unconditional compensation. Include mute,
  endpoints/rounding, concurrent HA control and ownership transfer in verification.
  No implementation or runtime change made for this feasibility discussion.

## Android GMS queue requests displacing desktop — 2026-11-06 (unreleased)

- User reports that playback stalls seem resolved, but desktop Cast is repeatedly
  disconnected, especially when saying "Okay Google" (several devices respond).
  `.110` logs show three receiver-initiated takeovers without LAUNCH/MDX at 21:17:35,
  21:29:09 and 21:30:39 UTC: phone `.79` opens `com.google.android.gms-7/-8/-9`
  with Android CastSDK metadata, then sends only `QUEUE_GET_ITEM_IDS`. Core
  claims ownership from desktop `.91`, closes its app channels on both owner sockets and
  rotates the YouTube Lounge identity. This is not reconnect-grace expiry or
  a playback/HTTP failure. Voice-trigger causality awaits the controlled retest;
  the offending protocol sequence itself is captured three times.
- The iOS queue-bootstrap compatibility rule treated SDK metadata as sufficient
  evidence for a weak takeover. Play Services supplies this metadata for its
  transport, including discovery and potentially an active user selection;
  `com.google.android.gms` does not establish passive/background intent.
  The narrow guard excludes exactly `com.google.android.gms` and its
  hyphen-suffixed channel IDs from weak queue-based claims only. Preserve explicit
  LAUNCH and app/MDX handshakes, same-device companion attachment/reconnection,
  iOS queue-bootstrap takeover and revocation of displaced controllers. Do not
  classify every Android SDK connection as an observer or increase reconnect
  grace to conceal this ownership error. Rejected weak joins now log source ID.
- Protocol regression reproduced the defect before the change. It covers base
  and changing GMS suffixes, repeated fresh sockets, readable status, retained
  desktop control/playback, harmless observer CLOSE, and a subsequent deliberate
  strong claim on the same GMS socket. Existing multi-socket takeover coverage
  now uses a real GMS companion source. Full core result: 103 passed, two silent
  mpv probes ignored (already executed for the unchanged cache in the preceding
  task). Independent review found no additional defect in this narrow change.
- Scope limitation: queue bootstrap is still a compatibility heuristic for
  other SDK senders. No evidence here establishes a general network instability
  or the precise role of these GMS requests in the sender UI. It remains
  unverified whether an active sender flow expects a queue-only handoff. Verify
  ordinary Android takeover and Assistant activation before declaring acceptance;
  do not infer that rejecting this sequence is harmless solely from its source ID.
- Candidate receiver SHA-256:
  `618191e9d33a9ecbcf73ef10995ab951c1a3511cbace9d6beb13b398dd3eee9a`.
  Built locally for GLIBC 2.36; runtime-image smoke test, formatting/diff checks
  and focused Clippy (existing allowances) pass. Activated on `.110` at
  2026-11-06 21:37:19 UTC; verified container hash and 2/2 responsive routes,
  zero restarts. Python/audio adapters unchanged. Rollback:
  `/home/test laptop/vibecast-round3-review.rollback-before-system-probe-20261106`
  (previous receiver `c12b4d0e573bd1efac6f0f6f8be4730fd388f61b7906139c91da1c416b8b0dff`).
  Full frontend patch: `/tmp/vibecast-system-probe-20261106.patch`, SHA-256
  `7e5c381d95abec2f6434c0a7360b02ff6b7f4257dd3335909df1efb5adcd9e00`.
  User live test passed: desktop remains connected after Assistant activation,
  and intentionally casting from the phone still takes ownership correctly.
  Logs independently confirm the distinction: at 21:38:35 UTC the GMS-10 queue
  probe is rejected without rotation; at 21:38:38 the actual YouTube Music
  app's `getMdxSessionStatus` deliberately claims ownership and rotates Lounge.
  Further GMS queue probes at 21:38:41 remain harmless.
  This confirms the targeted scenario; not a claim that every network-related
  disconnect is eliminated. No release or GitHub push.

## Buffer-aware source recovery across outputs — 2026-11-06 (unreleased)

- The subsequent `.110` incident was genuine starvation, not an explicit pause:
  mpv reported `pause=false`, `paused-for-cache=true`, position 155.59/188.84 s
  and only 0.82 s of forward audio. There was no corresponding sender Pause.
  Video `RWBwDmeOhHY` started at 20:43:38 UTC; the first refresh resumed at
  byte 2,179,056 of 3,120,891. A second low-rate window then discarded that
  useful cache, producing decoder EOF at 77 s and the final reload. Monitoring
  was disabled on that last attempt, allowing a slow but live response to
  buffer indefinitely. These were our coordination bugs. The reason that the
  CDN delivered so slowly remains unproven; an anonymous diagnostic 403 does
  not establish that the actual CTT-authorized playback response returned 403.
- Supersedes the destructive handoff described below: retain valid bytes and
  continue downloading after a slow refreshed source. First exact-object
  refresh remains proactive. Later recovery requires BOTH unhealthy cache and
  actual output Buffering, handled in the shared receiver hub, independent of
  the output implementation. Final-attempt health stays monitored; no third
  retry is introduced. Healthy windows/new responses/completion clear health;
  refresh-in-progress suppresses competing recovery. Periodic rate checks must
  not extend the separate 30-second no-data timeout. Stop late reports are
  fenced until a new media load commits; consumed recovery rounds survive
  eviction. A slow transfer with playable audio or explicit Pause is not itself
  a reason to stop the decoder.
- mpv: track `paused-for-cache` independently so pause=false, file-loaded and
  playback-restart cannot erase a real buffering state. Explicit Pause wins.
- AirPlay uses this same cache but previously reported synthetic PLAYING
  throughout PCM starvation. Native source commit `431c5c5` confirms elapsed
  counts sent PCM minus transport lag, so a frozen native clock alone is not
  yet an underrun. The adapter requires a pending PCM input read, frozen native
  progress, exhausted decoded runway and two seconds of reserve before
  reporting Buffering. Downstream write backpressure, explicit Pause, startup
  and completed input are excluded. Fresh native progress restores Playing.
  Evidence resets per track/control lifecycle. This is a conservative inference,
  not proof of acoustic output at a speaker.
- Other-path audit: DLNA and Sonos do not advertise localAudioCache and thus do
  not use this Rust cache. DLNA normally prepares finite local media through a
  bounded relay; Sonos pulls its URL directly. Both map device TRANSITIONING to
  Buffering and report polling/transport failures. A device falsely claiming
  PLAYING with a frozen position remains a telemetry limitation; the opaque
  Command backend has no decoder-progress protocol at all. Do not add a global
  timeout based on their interpolated clocks or claim those devices were
  acoustically tested. Their control and failure regressions are included.
- ffindog comparison, reviewed at `992cb673ccb94fc121d202772960c050a3928d65`:
  main speakers pass the resolved URL directly to mpv with its own cache;
  optional HouseStream uses a separate PCM pipeline. Its error policy skips
  tracks rather than implementing our two same-title recovery attempts.
  Retain our current-title cache, seeking/repeat and request recipes, but make
  download health and decoder demand agree. Do not add the declined full
  yt-dlp streaming path or copy its track-skipping policy.
  Reference: https://github.com/ffindog/ytm-cast-receiver/tree/992cb673ccb94fc121d202772960c050a3928d65/ytcr-player
- Validation: 241 Rust tests passed, three explicit probes ignored locally.
  Both silent real-mpv tests
  passed in the actual `.110` runtime image using a locally cross-compiled
  executable: (1) paused decoder still allows full source draining; (2) ninety
  seconds of cached PCM remain playable while the origin stalls. No YouTube
  calls or physical audio output are needed for these regressions. Independent
  review caught two additional AirPlay state traps (clean EOF and invalid clock
  samples while already buffering); both are fixed and regression-covered.
  All AirPlay and mpv unit suites: 112 passed, 28 subtests. Other output/shared
  bridge suites: 48 passed, three unavailable local FFmpeg/mpv cases skipped.
  Runtime-image adapter verification: 46 passed, including both real mpv IPC
  cases and the deployed AirPlay variant. Final rate/cache/hub tests, format,
  diff checks and focused Clippy pass; Clippy retains inherited allowances
  (argument/type complexity, enum size, double-must-use, question-mark,
  unnecessary-unwrap, collapsible-if and nonminimal-bool).
- Activated at 2026-11-06 21:07:47 UTC on `.110`, ready/responsive 2/2 routes,
  zero container restarts. Verified container SHA-256:
  - receiver: `c12b4d0e573bd1efac6f0f6f8be4730fd388f61b7906139c91da1c416b8b0dff`
  - mpv adapter: `6960d4418c9ff7b02a464a715dfa39e269ad377b81a25baf25da7f67ca866f27`
  - deployed AirPlay: `e4989763be8cecc6f011fa1c01937029548573f415e3934488938ba24950f8c3`
  The laptop has an older AirPlay adapter than product HEAD. Apply only this
  starvation fix to that runtime baseline; do not silently deploy HEAD's
  unrelated DACP/startup changes. Canonical source changes are in this repo;
  the tested runtime backport is `/home/test laptop/airplay-buffercoord-20261106.py`.
  Binary rollback: `/home/test laptop/vibecast-round3-review.rollback-before-buffercoord-20261106`.
  Python rollbacks: `/home/test laptop/cast-buffercoord-20261106/{mpv_backend,airplay}.rollback.py`.
  Full frontend patch against `85918111ac68cbf837bf58835b5fd066615963ad`:
  `/tmp/vibecast-buffercoord-20261106.patch`, SHA-256
  `aa71be447f8c4b1a1e15c95ddc1aa037c6abc4cf9e75f610bf6f7c53c8543bee`.
  User subsequently reports the playback failure seems resolved. Extended
  all-output acceptance is not established by readiness alone. No GitHub push
  or release.

## Cold-start watch-page rate limit — 2026-11-06 (unreleased)

- After the slow-source candidate restart, all tested selections failed before
  audio loading: `watch_bootstrap` returned HTTP 429. No slow-source recovery
  event ran in this new session. Restart discarded the in-memory bootstrap,
  exposing the pre-existing mandatory watch-page dependency. Route readiness
  alone did not validate playback; the previous deployment acceptance was
  insufficient. Why YouTube limited the watch page is not established.
- A direct diagnostic on `.110` using the existing ANDROID client and a selected
  video returned HTTP 200, playability OK and 25 adaptive formats from the
  native player API without an API key or watch-page visitor data. This supports
  a narrow fallback when the watch bootstrap returns 429: omit these optional
  web bootstrap fields, preserve video-bound CTT and all existing player/MDX
  context, and cache that decision in memory so sibling requests do not hit the
  blocked page again. Actual player denials and API 429 remain failures. The
  optional key is also consistent with yt-dlp's native API implementation:
  https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube/_base.py
- HTTP429 was already excluded from the worker's immediate request retry, but
  the subsequent Stop still triggered two immediate Lounge reloads. Classify
  it separately and acknowledge the failure before Stop to suppress these
  reloads; later explicit Play re-enables recovery. Abort current speculative
  work after this failure. A navigation 429 does not start an anonymous player
  request or label the following title failed. A real prefetched player 429 is
  propagated only for unchanged credentials; a fresh sender CTT can resolve.
- Regressions cover concurrent cold-start player/navigation with exactly one
  rejected watch request and intact CTT, retained API denial/status, no automatic
  429 reloads, later manual Play, new selections, late events, speculative task
  cancellation, and all navigation/player-429 versus fresh-CTT combinations.
  Final affected-suite result: 237 passed, two explicit live probes ignored.
  Formatting/diff checks pass; focused strict Clippy passes with existing
  unused-video-code, argument/type-complexity and inherited core lint allowances.
- Built locally using Rust 1.98.0 and Zig targeting GLIBC 2.36; the resulting
  binary's highest required symbol version is GLIBC 2.34. Runtime-image smoke
  test passed. Activated at 2026-11-06 20:36:56 UTC on `.110`, verified host and
  container SHA-256:
  `59783dc380637293ebdf3174f2098ab238e617c614dde43e7233e4a255d06b8d`.
  Both enabled routes are ready/responsive, container restart count zero.
  Rollback: `/home/test laptop/vibecast-round3-review.rollback-before-bootstrap429-20261106`
  (SHA-256 `17cd4668c9763f83128c15cca9eb2c2a0b39aa7353e0b39c9eb11fe6b9db7aaf`).
  Full uncommitted frontend diff over `85918111ac68cbf837bf58835b5fd066615963ad`
  captured locally at `/tmp/vibecast-bootstrap429-20261106.patch`, SHA-256
  `5fada5a1c30e513ceeccf81da59cf885c6cd2dbf7c23ed81f3339d44ccfab922`.
  User confirmed audible playback after reconnecting with this candidate.
  Live decoder reports also show Playing with advancing position. CTT player
  resolution took 1,171 ms; CTT next-prefetch took 136 ms. Navigation returned
  both neighbors, and the 3,161,970-byte current cache completed. The successful
  session did not log watch429, so the live check confirms recovered playback
  but does not prove that the bootstrap fallback was exercised against YouTube;
  its CTT behavior under watch429 is covered by the regression fixtures.
  No release
  has been published; this confirms restored startup, not a long-duration
  acceptance of every slow-CDN recovery scenario.

## Slow-source handoff follow-up — 2026-11-06 (unreleased)

- Live evidence on `.110` makes the recurring automatic-advance stall
  deterministic: video `3jGEko1z420` delivered only 9,829 B/s against an
  18,259 B/s continuity threshold. The first exact-object refresh correctly
  changed CDN (`rr5` to `rr4`) and resumed at byte 393,216, but that replacement
  also remained slow. Rate monitoring was disabled after the first recovery
  attempt, so mpv repeatedly exhausted its buffer. Explicitly selecting the
  title appeared to fix the problem only because it created a fresh media,
  cache and retry context. This was not a queue, CTT, prefetch-poisoning,
  HTTP 403/429 or dead-socket failure.
- Continue monitoring the refreshed connection within the existing bounded
  two-round recovery budget. Use at most one in-place exact-object refresh;
  if its replacement is still too slow, fail the cache into the already
  reserved clean decoder/media reload. If refresh is temporarily unavailable,
  allow exactly one same-URL range reconnect before that handoff. Fast sources
  consume no recovery round, and ordinary fetch failures cannot enter the
  slow-source reconnect branch.
- Regression coverage includes slow source to fast refresh, still-slow refresh
  to clean reload, unavailable refresh with a successful single reconnect,
  unavailable refresh still slow without a reconnect loop, byte/range
  integrity, fast sources and the shared two-round budget. Final relevant Rust
  run: 346 tests, 344 passed and two explicit live/mpv probes ignored; strict
  focused Clippy, format and diff checks pass. An independent final review found
  no retry loop, budget error or fast-path regression.
- Activated the exact tested Bookworm-compatible candidate on `.110`, SHA-256
  `17cd4668c9763f83128c15cca9eb2c2a0b39aa7353e0b39c9eb11fe6b9db7aaf`.
  It executes in the actual runtime image and requires at most GLIBC 2.34.
  Management and frontend bridge are ready; both enabled routes are running and
  responsive with zero restarts. Rollback binary:
  `/home/test laptop/vibecast-round3-review.rollback-before-slow-handoff-20261106`
  (SHA-256 `dc02143c21df0cf55e1c35c4284f8602ded8105db4e7a0085303640a8f8719d7`).
  Live acceptance must use automatic queue advance because explicit selection
  bypasses the reproduced path. No GitHub push or release.

## Slow progressive-source recovery — 2026-10-27 (unreleased)

- The live James Blake incident was not a queue, decoder-output, HTTP 403/429 or
  dead-socket failure. The selected 3,734,300-byte audio object took about
  278.4 seconds to arrive for 223.83 seconds of media: roughly 13.4 KB/s against
  about 16.7 KB/s consumption. mpv consequently entered repeated buffering from
  approximately 97.4 seconds. Small continuing reads kept the existing 30-second
  body-idle timeout from firing.
- For retained current-title audio with a known finite duration and an exact-
  object refresh contract, measure bounded ten-second origin-response windows.
  If throughput is below 110% of the representation's average bitrate, spend
  the existing first recovery round on a fresh same-object recipe and resume at
  the retained byte boundary. Do not monitor deliberate gaps between response
  ranges, do not loop after the first round, and leave the final decoder reload
  available. If refresh is temporarily unavailable, reconnect the same URL and
  continue rather than turning a merely slow source into a terminal failure.
- Added regressions for actual slow drip chunks arriving faster than the idle
  timeout, exact byte-preserving refresh/resume, unavailable refresh fallback,
  fast sources not spending recovery budget, and invalid/extreme duration
  metadata disabling the rate detector. Final broad Rust run: 342 passed, two
  explicit live/mpv probes ignored. Focused strict Clippy passes after allowing
  the repository's four pre-existing lint findings; format and diff checks pass.
- Activated the Bookworm-compatible candidate on `.110`, SHA-256
  `dc02143c21df0cf55e1c35c4284f8602ded8105db4e7a0085303640a8f8719d7`.
  The source archive was verified byte-for-byte against the locally tested tree;
  the binary was executed in the actual runtime image before activation. Both
  enabled routes are running and responsive. Rollback binary:
  `/home/test laptop/vibecast-round3-review.rollback-before-slow-source-20261027`
  (SHA-256 `def6ceb689e54ab855cc0a347cd7e85591fbbd2509739482d8c7e94581de55d1`).
- A first local-host build required GLIBC 2.38/2.39 and was rejected by the
  older runtime image. It was immediately rolled back before rebuilding in the
  Bookworm ABI environment; no code/runtime failure was hidden by that event.
  Live audible James Blake acceptance is pending. No GitHub push or release.

## 0.7.0.dev1 YouTube/session/HA-controls release — 2026-10-27

- User completed live acceptance on the `.110` laptop receiver and explicitly
  authorized publication with a larger version bump. Published as GitHub
  prerelease `v0.7.0-dev1` on 2026-10-27; Python version is `0.7.0.dev1` and
  image/App version is `0.7.0-dev1`.
- Verified source commit is `e38925d425c504322e4778224d6d961f53342b43`.
  CI run `40553631443` and release run `40554760222` both succeeded. The
  release/tag and promoted `main` point to metadata-only child commit
  `548016f78c620f381e6f8dd426606b81a29154b2`.
- Public image `ghcr.io/allcrafter1/cast-audio-receiver:0.7.0-dev1` was
  anonymously verified for `linux/amd64` and `linux/arm64`; multi-architecture
  digest is
  `sha256:365fd9021c09c7f28c7aaa4d1e933befd3bf8e737c700704b22e880e94bcddb0`.
  The release also contains the image manifest/digest and an offline-buildable
  vendored Rust source archive with a passing published checksum.
- Accepted coverage includes desktop, phone and iPad playback; age-restricted
  titles; seek; Previous/Next; Repeat One; mobile/desktop/iPad takeover; a
  60-second network-reconnect grace; and Home Assistant Play, Pause, Stop, Seek,
  volume, mute and real YouTube Music queue navigation.
- Current frontend source is maintained commit
  `85918111ac68cbf837bf58835b5fd066615963ad`, reconstructed for the
  product from public base `83ba470158189de3bc223701decdc4c502d47644` plus
  `patches/vibecast-0.7.0.dev1-current.patch` (SHA-256
  `3d4119abefbeff18a0f86b90a4252cafa7a3341ce136c8fd4c6103a6a5e62204`).
- Retain CTT and opaque InnerTube context per exact video/queue slot; contextual
  prefetch cannot be poisoned by an earlier anonymous failure. Download recipes
  carry allowlisted request headers through proxy/cache/refresh without logging
  or persisting tokens, cookies or signed URLs.
- Unexpected control-socket loss permits bounded reconnection without weakening
  explicit Stop/Close or genuine sender replacement. Passive HA/status observers
  do not acquire sender ownership; displaced senders cannot control media or
  output volume. Local output controls remain serviced during Lounge rebind,
  feedback stalls and reconnect backoff.
- Automatic playback recovery remains limited to two fresh-media rounds and is
  isolated to the affected selection. The progressive cache stays demand-driven;
  no playlist archive or persistent YouTube cookie store is introduced.
- Release gates: exact source reconstruction, Rust 1.98.1 workspace tests/build,
  complete Python/browser/container CI, both native image architectures,
  anonymous GHCR readback and offline vendored-source rebuild all passed. The
  release workflow left the running `.110` test deployment untouched.
- Product code remains MPL-2.0; Vibecast stays MIT, Chromium BSD-3-Clause and
  airplay-cli GPLv3 notices remain separate. The final reference audit found
  no imported source from ffindog's unmerged reconnect PR, ffindog's MIT
  receiver or patrickkfkan's MIT `/next` implementation; credit them as
  behavioural/reproduction references without adding dependency licence files.

## dev29 DACP follow-up — 2026-10-17

- Published as a suspected fix, NOT hardware-confirmed. Paused at the user's
  request after publication; resume only for their next test cycle.
- Source: `db68ba72bcad58bd12e1d484a0bb024d22135782`. CI run 39043097031
  and release run 39043113736 succeeded, including both image architectures
  and offline source rebuild. Image manifest independently verified:
  `sha256:1af75a1841cc8334fcc2e89c6f767ad46340fc4e69afbb07e5b803fce076e43b`.
- Local final checks: 68 AirPlay tests and both real wire tests passed.
- Next acceptance: receiver-to-YTM volume, Next/Previous and Play/Pause on
  RX-V673, with new DACP diagnostics. No direct HA changes or hardware tests.
- User confirms dev28 fixes the inaudible track onset on RX-V673. Receiver
  volume and skip feedback still fail. Supplied logs confirm a legacy RAOP
  route and working YTM-origin selection, but dev28 does not expose DACP
  startup/rejection diagnostics in the shared HA log. Do not infer receipt or
  non-receipt of Yamaha callbacks from those logs.
- Correct the legacy RAOP DACP representation: use the same full-width,
  uppercase 64-bit hex identifier in RTSP headers and DNS-SD. dev28 used the
  receiver's 12-character MAC representation. Preserve literal identities on
  auto/AirPlay 2 routes because existing HAP pairing credentials depend on them.
  Match the legacy DACP TXT version and OSsi fields used by SpotConnect.
- Added safe shared diagnostics for DACP readiness/failure, rejected peer/token
  (once per reason per session), received volume and playback controls. Never
  expose the authentication token or raw HTTP request.
- Real loopback tests now exercise mDNS discovery and HTTP callbacks without
  mocking advertisement. An optional test runs the pinned v0.5.4 native binary
  against an RTSP test peer and checks the actual headers against the callback
  server identity/token. Both wire tests passed locally.
- Fixed a confirmed lifecycle bug: zeroconf register/unregister return a second
  awaitable for the actual announcement/goodbye packets. Wait for it before
  reporting readiness or closing the multicast socket, avoiding stale cached
  callback endpoints after disconnect/reconnect. Regression checks close order.
- This fixes demonstrable compatibility gaps and diagnostic blind spots;
  confirmation of the exact Yamaha failure mechanism and hardware acceptance
  remains pending. Do not report the user's feedback issue as proven resolved.

## 0.6.0.dev28 AirPlay return channel and startup — 2026-10-17

- User authorized fixes and publication including the unreleased dev27 work,
  and explicitly requested checking receiver Play/Pause and related controls.
- Confirmed the adapter/native legacy RAOP path lacked a DACP listener and
  advertisement. Added session-scoped HTTP/mDNS with receiver-IP/token checks,
  absolute-volume feedback without echo, and playback/queue control forwarding.
  Play, Pause, toggle, Stop, Next, Previous, mute and relative volume are covered;
  no claim is made for unsupported fast-forward/rewind DACP commands.
- Confirmed the adapter sent START immediately after launching the decoder,
  contrary to the pinned native sender's documented audio-ready contract.
  Native RAOP's 200 ms ASAP floor is also shorter than its normal 2250 ms
  receiver latency. Added per-track readiness/failure gating and future RAOP
  starts with latency lead; do not discard PCM or insert leading silence.
  Actual PLAYING/position start follows the native audible-time acknowledgement.
- New tests exercise real HTTP requests, rejected tokens/peers, advertisement
  cleanup, Cast bridge feedback/controls, warm-cycle readiness reset, delayed
  startup, cancellation, decoder/transport failure and auto/AP2 route handling.
  Existing lifecycle-only fixtures explicitly stub the new readiness contract.
- Local isolated publication-export run: 367 Python tests, 356 passed and
  11 explicitly skipped. Public-history audit passed across 57 commits before
  this release commit. Native multi-architecture builds and release promotion
  are gated by the GitHub workflows; this entry does not imply hardware success.
- No Yamaha hardware acceptance has been performed here. After updating check
  receiver-to-YTM volume, Play/Pause and queue navigation, first-track onset,
  next/repeat/seek and cold/warm starts. Timing is a code-level correction, not
  proof that every device-specific onset symptom has been eliminated.
- dev27 account-context forwarding is included as requested; the previously
  documented YouTube acceptance limitation remains. SpotConnect is unchanged.
- Final review also guards duplicate DACP identities: a failed registration
  must not send an mDNS goodbye for the already active sender. Regression added.

## Home Assistant music controls — implemented in 0.7.0.dev1

- The feature recorded here on 2026-10-17 is implemented, live-accepted and
  published in `v0.7.0-dev1`.
- Home Assistant can issue Play, Pause, Stop, Seek, volume, mute, Next and
  Previous against the active Cast media session.
- Next and Previous navigate the real YouTube Music Lounge queue. Passive Home
  Assistant/status observers remain separate from sender ownership and cannot
  seize or keep a superseded controller session alive.

## 0.6.0.dev27 YouTube CTT forwarding — 2026-10-16

- Implemented sender-provided, video/session-scoped CTT forwarding from Lounge
  `setPlaylist` into InnerTube `context.user.credentialTransferTokens` with
  `VIDEO` scope. Token values are neither logged nor persisted.
- Token-bearing playback uses the credential-bound InnerTube audio response,
  not anonymous `yt-dlp`. Retry, repeat and exact-object URL refresh retain the
  same context; navigation, Stop and takeover clear it. Prefetch remains
  anonymous and cannot satisfy a credential-bearing load.
- Full Rust verification ran 390 unit/integration tests: 388 passed, two
  explicit live/hardware probes ignored; SDK doctest passed. Rust 1.98/Zig
  GLIBC-compatible binary SHA-256:
  `cc51e5aee11e40b177bffa039845e924e90207ff8c9a6190f41ef6688a43e59c`.
- Complete maintained frontend is locally versioned at
  `2975e7b7d997bb896951656a004c5e94a7b8633f` and preserved as the hash-locked
  dev27 snapshot over public dev26. This local commit is not a public pin.
- Activated the compatible binary in the existing `.110` test container at
  2026-10-16 21:03 CEST. Installed hash matches the candidate; management,
  frontend bridge and both enabled routes are ready/responsive with zero
  restarts. The previous binary is retained in the timestamped rollback
  directory documented in `docs/youtube-ctt-dev27.md`.
- First live `Fuck My Computer` attempt received a CTT but YouTube rejected all
  three requests with the inappropriate-content message. Follow-up adds the
  missing content acknowledgement and MDX fields for matching credentials;
  99 YouTube tests pass, one optional live test ignored. Follow-up playback
  acceptance remains pending. See `docs/youtube-ctt-dev27.md` for binary hash.
  Store metadata stays dev26 until normal image verification/promotion.

## Cross-area reliability review, third round — 2026-10-08 (unreleased)

Continued after the user's request not to stop at the previous review results.
Adversarial follow-up covered interruption while sockets remain connected,
delayed cross-title reports, malformed output, disconnected configuration
requests, out-of-order UI responses, source-export failures, and all Rust
workspace consumers rather than only the audio crates.

Confirmed fixes and regression evidence:

- The Python player receives commands independently of executing them. Stop
  and a newer LOAD can cancel a blocked LOAD without closing the connection;
  owned cleanup completes before a replacement starts. A bounded queue fails
  closed on saturation. Tests also exercise a third selection arriving during
  cleanup, queued seek/pause, and Stop for an unrelated session.
- LOAD, State, Error and output controls carry an additive `mediaSessionId`.
  The Rust core rejects delayed title-local reports for an older selection;
  volume remains output-wide. Legacy clients omitting the field remain
  compatible but cannot gain correlation guarantees without sending it.
  Reports after Stop cannot resurrect a cleared selection or spend a retry.
- Invalid replacement loads stop the previous decoder even when validation
  fails before installing the new session. Five malformed takeover cases,
  legacy recovery and foreign/current Stop are covered. Numeric inputs reject
  non-finite values, booleans and overflow; command errors are redacted.
- mpv IPC rejects non-object events and malformed/non-finite property values.
  AirPlay drains oversized output lines in bounded chunks, discarding the
  entire oversized line rather than interpreting its tail as a command.
- Once a management edit starts persistence, HTTP cancellation cannot release
  its lock before reconciliation and private-target cleanup finish. Tests
  disconnect actual HTTP clients during PATCH and DELETE and check failed
  atomic-save recovery.
- UI responses are applied monotonically; a delayed older refresh/poll cannot
  overwrite an already applied newer configuration. Standalone Node tests
  exercise deferred responses without relying on browser timing.
- Public source export validates in a sibling staging directory before atomic
  publication. Failed validation no longer strands a partial output tree.
- Whole-workspace checking caught missing adaptations in a PrimeVideo test
  capability literal and the FFI typed-error mapping; both are corrected.

Verification so far: complete Rust workspace tests passed (379 including
doctests, 2 optional tests ignored). Python ran 356 tests, 345 passed and 11
optional/environment tests skipped; the two Node UI/helper tests also passed
explicitly. A separate real-mpv probe on the test laptop performed 30 rapid
back-to-back replacement cycles without awaiting the first file-loaded event:
final position/pause state and Stop were correct in all cycles. The probe used
null audio and did not replace the running service; it is not audible approval.
Final follow-up also corrected relative CLI `--certs` resolution against the
documented data directory. Startup rejects invalid/non-finite initial volume
and non-positive/non-finite volume steps with a typed configuration error;
valid values are preserved (including steps above one, not newly prohibited).
The final complete Rust rerun passed 381 tests including doctests, 2 ignored;
format and whitespace checks passed. The independent closing review of media
correlation, Stop/LOAD cancellation, failed replacement, configuration and
volume handling found no further confirmed defect in those reviewed paths.

Final locally cross-built binary SHA-256:
`40c8796f288715988b56373ff9272445c64fe43d5183557215e91ea7b1ca5619`.
Deployment uses separate `vibecast-round3-review` and `cast-round3-python`
staging paths, including the corrected UI file. The previous container is
retained as `cast-audio-receiver-pre-round3-review`; no active mounted files
were overwritten during staging.

Activated on the test laptop at 2026-10-08 21:54:24 UTC; container ID
`5b8aba156592b5e97e503f9c1e3ed90f1a85e5543d6f2c6974cd6f8ef21b4208`.
The active binary/player/UI hashes match the local artifacts. Both enabled
routes report fresh WebSocket responsiveness, no container restart. Against
the actually mounted Python runtime, 85 targeted tests passed, including real
mpv null-audio rapid replacement/seek/crash recovery, connected LOAD
interruption, malformed takeover, report identity and controlled output
process/pipe behavior. User desktop/mobile audible acceptance is still pending.

Known verification boundaries remain: no full Chromium run (missing system
library), no physical Sonos/DLNA/AirPlay acceptance, no proof against every
possible scheduling/network failure, and legacy player reports without media
identity remain ambiguous. No commit, release, or version/source-pin change
is authorized by this review; desktop/mobile acceptance precedes publication.

## Cross-area reliability review, second round — 2026-10-08 (unreleased)

User requested continued investigation/fixes across all areas, not only playback.
Reviewed active receiver/bridge/discovery/configuration, YouTube/cache/decoder,
output backends, management API/UI code, route persistence, certificate/artifact
startup and publication/export checks. Three independent reviewers split the
areas and cross-checked cancellation interactions. This is bounded review
coverage, not a claim that every possible bug or device behavior is eliminated.

New confirmed fixes:

- Player output controls carry a local load generation: stale title-local
  controls cannot target the next title within the same Cast session. Output
  volume remains output-wide. A connection supervisor observes socket close,
  receive, reporting and health tasks together, cancels pending backend work
  and performs cleanup instead of waiting indefinitely inside a LOAD.
- Bridge registration reserves lifecycle queue capacity before committing
  ownership; epoch comparison/claim/enqueue are atomic. Stale registration
  cannot replace a newer receiver. Manager also rejects stale epochs.
- Non-finite, non-positive and unrepresentable HTTP/poll durations produce a
  typed configuration error rather than a panic. Sub-second positive polling
  retains its existing one-second minimum. Zero is explicitly invalid.
- mDNS service validation precedes daemon startup; an owned cleanup guard
  exists before registration. Failed registration no longer leaks a daemon.
  Tests verify the individual daemon's state rather than global thread counts.
- AirPlay control FIFO writes handle short writes and bounded backpressure.
  Fatal control-channel failure retires the fd and stops the uncontrollable
  sender. No recursive STOP failure or generic stop-on-volume-error policy.
- AirPlay/Command outputs cannot claim playback after their decoder ended.
  Their cleanup retains process ownership across cancellation and drains pipes
  before final reaping. Command seek reloads via the existing {start_time}
  template preserving pause, or explicitly rejects unsupported seek instead
  of only moving its reported clock.
- Sonos replacement stops old status polling before remote LOAD. Cancelled
  threaded device commands retain ownership, so Stop waits for the outstanding
  remote operation rather than being overtaken by a late play_uri completion.
  Sonos errors are normalized without raw upstream details. Sonos/DLNA Play
  restart ended polling and clear old terminal status; DLNA resets its startup
  observation window.
- Scanning one discovery protocol preserves unexpired import choices for the
  other protocol. DLNA port zero is rejected rather than canonicalized to a
  different port than the saved URL actually uses.
- Certificate import uses unique private temporary files, never deletes a
  pre-existing abandoned import, and checks in-place size and copied bytes.
- Artifact download checks elapsed budget between network receives rather
  than buffered 64-KiB fills; HTTP protocol errors are sanitized and preserve
  the installed artifact. Each individual read retains its socket timeout.

Red/green regressions cover these failure paths. Actual subprocess tests also
confirmed Python already reaps Command/AirPlay children when cancellation
occurs inside process creation; no speculative extra spawn shielding added.
Independent second passes found no further confirmed defect in the reviewed
paths after the final corrections.

Verification: expanded 13-crate Rust suite, 312 unit/integration tests passed,
2 optional tests ignored, plus 1 doctest. Python: 341 run, 331 passed, 10 optional
skips. On the test laptop, 51 targeted player/output tests passed, including
silent real-mpv replacement/seek/crash recovery, real WebSocket close during
blocked load, and process/pipe cleanup. No real Sonos/DLNA hardware test was
performed; AirPlay command/cleanup tests use controlled helpers, not a claim
of end-to-end audible hardware acceptance. Thread tests require the normal
execution environment; sandbox-only thread hangs were not product failures.

Browser suite attempted with the CI's Node 22/Playwright versions but could
not launch because Chromium system libraries (libnspr4.so) are absent. API
tests passed; do not report the browser suite as passed. Strict Clippy remains
subject to the previously documented warnings; no lint-policy relaxation.
Generic command outputs still have no physical volume-control seam. An
unresponsive third-party Sonos thread cannot be safely force-killed: ordered
Stop waits for that library request to finish. These are explicit limits,
not proof of a new incident. No release/push before user listening acceptance.

Activated on the test laptop at 2026-10-08 21:17 UTC. Receiver binary
`vibecast-round2-review`, SHA256
`59c171a000a39f428b5869c42602a45e058e2ca3a773118f68e0533bf52a6690`;
staged Python/test archive `cast-round2-python.tar.gz`, SHA256
`57bcf03e2a127dcc9670bb25c101e6c664e299d0439fe06f29a1341292f1fa0d`.
Container `821f44107abbc7d17ee8c244d07fd0ffda832927c069e9de9414488b6adebf4e`,
rollback `cast-audio-receiver-pre-round2-review` retained. Eleven changed
runtime modules are read-only mounts from `cast-round2-python/src/cast_audio_lab/`.
No user data, prior binaries or rollback containers removed. The same 51
output/player tests passed again using the actual mounted runtime modules,
including silent mpv. Health after tests: 2/2 running/responsive, zero restarts;
no startup warning/error. Audible desktop/mobile acceptance requested and
pending. No commit, GitHub push or release.

## Broad reliability review — 2026-10-08 (unreleased)

Scope: user requested an intensive cross-layer bug review, implementation of
confirmed fixes, and regression checks for interactions between those fixes.
Reviewed Cast ownership/control correlation, generic LOAD lifecycle, YouTube
queue/repeat/cancellation, media cache/recovery, player bridge/proxy teardown,
mpv IPC, adapter reporting and subprocess supervision. Existing uncommitted
recovery changes were preserved. Builds run on the development machine.

Confirmed fixes with behavioral regression coverage:

- Reject stale Cast mediaSessionId on Play/Pause/Seek/Stop/media-volume, so
  delayed commands for a previous selection cannot control its replacement.
- Failed replacement resolution stops the previous decoder before clearing
  ownership. Otherwise old audio could continue behind an error/empty status.
- Preserve Play/Pause/Seek accepted during generic resolution and apply them
  to the resulting LOAD, not the old decoder. Independent rereview caught two
  interactions: app-owned Play must first honor pending generic controls, and
  old decoder EOF/error reports must not update the pending selection. Global
  volume reports remain accepted. Stop/new LOAD still invalidate old results.
- Reanchor current YouTube queue index when updatePlaylist reorders/removes
  earlier items; preserve an unchanged duplicate slot. Do not invent a new
  selection if the active video was removed entirely. Covers pending resolve
  as well as playing media. Reject invalid/non-finite sender positions.
- Do not send a delayed MDX identity after session cancellation/channel close.
- Fence mpv end-file by playlist entry identity, reject late file-loaded after
  Stop and old playback-restart during loading, and clear stale error state
  on the accepted file-loaded event.
- Suppress old backend reports while metadata/decoder load is being prepared;
  initial BUFFERING retains the requested resume position. Failed setup stops
  previous audio. Queued physical controls cannot cross WebSocket/session
  replacement.
- Supervise failed/closed adapter log readers rather than waiting forever for
  a child blocked on stdout. During cleanup discard/drain stdout independently
  of the failed parser, including pipe EOF, before releasing the process.
- Bound initial player registration to 10 seconds; serialize bridge starts and
  stops. Shutdown/drop cancels accepted sockets and pending HTTP handlers,
  including non-reading clients and full lifecycle event queues.
- Bound buffered upstream manifest/license documents to 16 MiB, including
  chunked/decoded bodies; progressive audio cache remains a separate path.
  Remove raw signed URLs and arbitrary upstream errors from those logs.

Tests reproduced stale control, failed-replacement audio and stale EOF bugs
before correction. Reviewers cross-checked changes across layers. Nine-crate
suite: 264 unit tests passed, 2 optional tests ignored, plus 1 passing doctest.
Python: 314 tests run, 304 passed, 10 optional tests skipped. Final run contains
no unhandled-task/subprocess destructor warnings. Public export test also
passes after replacing private operator paths in historical deployment notes
with staging-relative names; artifact hashes/rollback records are retained.

The final pending-load control regression passed 20 consecutive runs. Silent
real-mpv integration on the test laptop covers missing-source recovery,
offset/pause/seek/EOF/Stop, 12 alternating playing/paused replacements, decoder
kill/reload and volume/mute restoration. This is not audible Cast acceptance.
Clippy completed with warnings; strict warnings-as-errors is not clean due to
existing unused audio-fork resolver/video code, API/macro/style lints and newer
toolchain deprecations. No unrelated lint refactor or lint policy change made.

Five additional consecutive silent real-mpv integration runs passed on the
test laptop (60 replacement transitions, plus crash/reload in each run).
All 24 cache tests, including the optional real-mpv cache test, passed there.

Activated on the test laptop at 2026-10-08 20:56 UTC, locally built binary
`cast-broad-review-bin/vibecast`, SHA256
`ae2ca6d1ef863f91a2f0b57d86fd17d7173fbc991a4599f76e48d6711d18a65b`.
Container `08998d66a519f7eba325016aa66354b287f60e1dccbf0317ed33dfdc44348004`;
rollback retained as `cast-audio-receiver-pre-broad-review`. Three Python
runtime modules are read-only mounts from the staged
`cast-broad-review-python/src/cast_audio_lab/` directory. Verified mounted
hashes: mpv_backend `8e7ce88d78d73db1665f0463d3f23bf6380d83136abb1f1487aa0eb8daa2954f`,
vibecast_player `43ee9c9328710a3cb53e33de0673e13b3d5bc807850f1cdc3d57f53deebae5d2`,
route_manager `8f8a7f6e5cf39c725b33b924eb3d8628f7c98c89947faa52c63f81c2ec1880bc`.
Startup health: 2/2 running and responsive, both receivers advertised, no
startup warning/error observed. This health check does not prove audibility.
After activation, the silent mpv test passed using the actual mounted modules
(no alternate PYTHONPATH), and all 80 core tests passed inside the new runtime,
including the optional decoder/cache integration. Rechecked health afterward.
No GitHub push/release; desktop/mobile listening acceptance remains required
and was requested for start, title change, pause, seek, repeat and takeover.

## Forrest Gump recovery regression — 2026-10-08 (unreleased)

Incident: 20:10:15 UTC, cache body read transport error while playing
`dGuuX3vN4E4`. Early refresh ran twice and resolution completed both times,
but no replacement was accepted. Cache failed at20:10:22; decoder exhausted
its buffer at20:10:49 /157.191228s. Explicit sender PLAY at20:11:49 recovered
the same title/position. No PAUSE or HTTP429 explains this incident.

Confirmed implementation mistake: two fresh same-title yt-dlp resolutions on
.110 returned different CDN query `id` values with identical itag251, lmt,
and clen4,060,695. The previous check incorrectly treated that volatile ID as
immutable audio identity. Historical URLs were not retained, so the exact
past mismatch field cannot be reconstructed. The rejection mechanism is
reproducible and must not be attributed to an external rate limit.

Fix: ignore volatile CDN id; retain same-video binding and strict format,
revision, length and MIME checks. Reject malformed required numeric fields,
and log mismatch booleans only (no URLs/identifiers/tokens). Allow one early
cache refresh and reserve the second shared-budget attempt for a clean
same-title, position/pause-preserving decoder reload. An incompatible cache
representation must not consume both rounds without trying a clean load.
No third retry or implicit playlist skip is introduced.

Transport investigation reproduced a pacing-sensitive failure on .110 using
the same freshly extracted affected-title URL and reqwest HTTP/1: eager read
returned all4,060,695 bytes with206 in under1s; paced128KiB/7s read reset at133s
after2,539,504 bytes (`decode=true`, `ConnectionReset`, OS104; no429/403).
Historical trace also contains a seek to0 at20:08:12 after105s playback,
allowing a long interval of cached rereading before further upstream demand.
The experiment does not identify which network/origin component sent RST or
prove the historical error's unrecorded IOcause, but demonstrates that our
artificially prolonged responses can fail while a normal read succeeds.

Correction to source pacing: promptly drain an open bounded10MiB response into
the current-title cache; wait for player demand only between responses. Never
wait for an entire title before starting the decoder. Short songs will now
finish downloading in the background quickly, rather than deliberately keeping
one HTTPbody open for their playback duration. This deliberately supersedes
the Oct7 per128KiB demand pause. It avoids returning to many tiny originrequests
and preserves the32MiB current-title cap, repeat, seek and cancellation.
The user was informed of this tradeoff during implementation.

A second bounded probe reproduced the cache-rewind idle pattern: read1MiB,
hold without polling for110s, then drain; ConnectionReset104 after2,637,808
bytes at110s (decode=true, noHTTPerror). This reinforces response lifecycle
as a reproducible trigger, not a claim that every possible network reset is
preventable. Probes ran on .110 with locally compiled reqwest binaries; signed
URLs stayed in memory and temporary diagnostic source files were removed.

When draining a new range across sparse cached blocks, consume and compare
already-present bytes before appending missing suffixes. Reject changed bytes;
do not mark cache complete until the active response tail is validated. This
prevents seek/overlap misalignment while preserving bounded incremental reads.

Safe diagnostics now include response age, range, receivedbytes, decode flag
and underlying IOkind/OSerror without signed URLs or formatted errorchains.
Reference checked for the user's request to follow established downloader
practice: https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/downloader/http.py
reads open responses continuously, validates ranges and resumes on transport
failure. Our bounded current-title cache is not a copy of that downloader.

Final local verification: nine-crate suite248 unit tests passed /2 optional
tests ignored, plus1 passing doctest. Overlap tests exposed an additional
invalid-completion path; integrity failures now prohibit in-place refresh,
and fully filled but unvalidated cache bytes cannot take a completion shortcut.
Formatting/diff checks passed. All24 cache tests passed on .110, including real
mpv paused playback; current small object downloads in the background without
holding the origin response open for the pause duration.

Built locally and deployed `vibecast-native-recovery` in the operator's staging directory, SHA256
`59445cb9c8c11221cc683be7e4c56bd239efaec9b1b4276f63e530c6880bbe9f`.
Container `a17955ecc975acf7e524b72e2a50ae9b536e1f617b7cbbfdf6d6ffbea8e59f25`;
rollback `cast-audio-receiver-pre-native-recovery` retained. Python mounts
unchanged, health2/2 running and responsive. User asked to reconnect and test
Forrest Gump, seek-to-start and repeat-one; audible acceptance pending.
No GitHub push/release. Earlier `vibecast-identity-recovery` staging binary was
never activated; the active binary includes the response-lifecycle correction.

## Early recovery while decoder buffer plays — 2026-10-07 (unreleased)

Follow-up incident: "Gute Dinge" cache fetch failed at 06:10:48 UTC, but mpv
only reached false EOF at 06:11:18 at position 119.840972. The first fresh
resolution reloaded the same title/position; file-loaded at 06:11:20.483.
The ~2.1 s audible gap was consistent with waiting for decoder EOF to recover.
The original fetch error had no detailed cause logged; a separate next-title
request returned 403 at 06:12:15. Neither incident proves HTTP 429/rate limiting.

Requested change: begin bounded source recovery immediately on a fetch failure,
retain buffered/cache bytes and the current decoder load, and resume the missing
byte range. Fresh source resolution must verify the same immutable media
representation before splicing bytes. Cache recovery and decoder fallback must
share the existing two-attempt budget; successful Playing must not replenish it.
Stop, takeover and title changes must cancel the recovery. Preserve progressive
loading and repeat/seek behavior. Build locally; test on .110 before any release.

Implemented: a generic SDK source-refresh hook on the cache hint; YouTube
freshly resolves the same title and requires matching object id, itag, lmt,
clen and MIME before returning a replacement URL. Missing/duplicate identity
fields fail closed. The cache resumes at the exact retained byte offset, keeps
the pending local HTTP response open, and validates upstream range/total length.
Each fresh resolution is bounded to 30 seconds. Without a verifiable identity,
the existing decoder-level recovery remains the safe fallback instead of
splicing potentially different audio. No eager whole-song download introduced.

The hint's atomic retry count is propagated through app playback state and
replacement loads; the hub retains it after cache eviction. Both early repair
and later decoder recovery share two rounds per selection; manual Play can
start a fresh budget. Stop cancels pending resolution, and source recovery
does not issue Player Load/seek or alter pause/volume state. Added redacted
failure-stage diagnostics (headers, body, timeout, truncation, range mismatch)
without printing signed URLs. Follow-up review also caught and fixed redirect
to the old URL when a freshly resolved origin ignores Range before any bytes
have been cached. No claim that external 403/429 refusals are eliminated.

Verification: final nine-crate run 242 unit tests passed / 2 optional tests
ignored, plus one passing doctest. All 20 cache tests passed inside the .110
runtime, including six new recovery regressions and the silent real-mpv test
(paused decoder retained 786,432 / 2,880,044 bytes). Formatting and diff checks
passed. Independent read-only review found no further concrete blocker.

Built locally and deployed `vibecast-early-recovery` in the operator's staging directory, SHA256
`d412d6cc3b4e36cdfd0a9d74e01dc34a16a150e6fc7620890925d0b844b8caff`.
New container `16ff65fbf44103696d7eeacebba810786421e94b43793641947857bf68d9f905`;
rollback retained as `cast-audio-receiver-pre-early-recovery`. Existing Python
mounts unchanged; health confirms two running/responsive outputs. User listening
acceptance requested and still pending; deterministic local fault tests do not
prove every upstream failure will recover inaudibly. No GitHub push/release.

## Progressive source-request alignment — 2026-10-07 (unreleased)

User prefers progressive/native-style loading, not many artificial small
origin requests or eagerly downloading the whole song before playback.
Investigation of the prior 403 did NOT reproduce the denial: fresh same-title
URL allowed21 range requests; a separate locally compiled reqwest probe waited
180s after extraction and then consumed all21 ranges (2,622,747 bytes) with
HTTP206 over HTTP/1.1. URL lifetime was approximately six hours. These are
bounded diagnostic samples, not proof intermittent upstream errors are solved.
The exact earlier signed URL was not retained; no tokens/URLs were printed.

Verified installed yt-dlp2026.08.19 source on .110: YouTube downloader_options
uses10MiB HTTP chunks. Upstream reference also sets this policy:
https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/youtube/_video.py
The current upstream HTTP downloader uses standard Range headers, so rewriting
signed URL query parameters is not justified:
https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/downloader/http.py

Implemented larger bounded origin ranges consumed incrementally only on player
demand, reusing the active response across adjacent128KiB cache blocks. Seeks
may start another range; current-title sparse cache/repeat behavior remains.
Dedicated media HTTP client must have no total response lifetime deadline:
pausing demand is not a network stall. Preserve independent header/connect and
actual-read deadlines, cancellation, size cap, failed-cache EOF classification
and the two automatic fresh-resolution retries.

Separate audit observation: extracted http_headers are currently discarded.
No A/B failure was available to establish that this caused the incident; do
not label missing headers or request size as the proven historical403 cause.

Implementation: at most 10 MiB per upstream response, consumed one demanded
128 KiB retained block at a time. Adjacent blocks reuse the response; sparse
seek drops it and opens a new range. One transport chunk may be buffered in
addition to the 32 MiB retained cache cap; this is bounded by the 10 MiB response
range, not an unbounded speculative download queue. Native socket buffering
can also run ahead; no claim of byte-exact network pacing to playback.
The metadata and media clients share cookie/header policy but have separate
pools. Metadata retains its configured total timeout; media uses connect,
header and demanded-read deadlines only. HTTP/2 was not newly enabled.

Verification: nine Rust crate suites 233 passed / 2 ignored; all 14 cache tests
passed on .110 including silent real-mpv buffering. Paused mpv retained
786,432 of 2,880,044 test bytes. Regression coverage includes 10 MiB boundary,
sequential reuse, sparse backwards seek, demand pauses, cancellation, truncated
bodies, downstream false EOF and later upstream 403. Formatting/diff checks
passed. No source URL query rewriting or unproven header-based fix introduced.

Deployed to .110 as locally compiled `vibecast-progressive-ranges`, SHA256
`30aad90d2072756531753f8774d5c13f7b2e1845b13901d5ca525d7e5b0f694e`.
Python mounts unchanged. Retained rollback container:
`cast-audio-receiver-pre-progressive`. New container:
`70e5fae2da9a8cbacf5273abc1e96b0f90813466f57052d2f52233968a83db72`.
The historical 403 remains unproven beyond the recorded upstream refusal;
no claim that every external refusal is fixed. User audible desktop/mobile
acceptance remains pending. No GitHub push/release was performed.

## Premature EOF after HTTP 403 — 2026-10-07 (unreleased)

Incident on .110: at 05:41:02 UTC "Beste Zeit" loaded; at 05:41:29 the
next demanded audio-cache range failed with HTTP 403. After draining buffered
audio, mpv reported EOF at position 55.201934 at 05:41:58 and Lounge advanced
to "Ein gutes Ende". This is not a 429 incident. Cache readers already emit
a body error on failed download, but the decoder can still report normal EOF.

Fix: the hub checks authoritative cache failure before broadcasting or passing
EOF to the app, converts it to ERROR, and evicts the failed cache. This failure
classification remains sticky until a new load, so repeated old EOF reports
cannot advance after eviction. No duration heuristic or speculative skipping.

Per explicit user request, Lounge now allows TWO automatic fresh-resolution/
reload rounds per selection, including mid-song failures, at the reported
position and preserving pause intent. Resumed playback does not replenish the
budget. After both retries fail, the title remains in error; explicit Play can
start a new bounded attempt. Stop/takeover/new selections retain existing
cancellation behavior. Each fresh resolution retains the worker's pre-existing
bounded extractor retry; two reload rounds is not a global limit of two HTTP
requests. No external rate-limit bypass or guarantee against upstream 403.

Regressions cover a successful first audio block followed by HTTP 403, body
error rather than clean EOF, Cast ERROR for repeated false EOF, same-title
position-preserving retries, exhaustion after retry two, paused recovery,
resolver failures and manual recovery. Physical listening acceptance remains
pending; no new release or GitHub push during this fix.

Verification: combined YouTube/core tests 141 passed, 2 optional tests ignored;
formatting and diff checks passed. Built locally and deployed on .110 using
`vibecast-two-retry-eof` in the operator's staging directory, SHA256
`694e085db8c21decee04c3f053f9e5c7390d0b88c7f7ae58be81e969fba35565`.
Python mounts are unchanged from the expanded-review deployment. Previous
container is retained as `cast-audio-receiver-pre-two-retry` for rollback.

## Expanded review implementation — 2026-10-04 (unreleased)

User authorized fixing the review findings and widening the review. The prior
section below is the historical finding list, not the current open-bug status.
Changes remain uncommitted in the maintained frontend and product checkouts;
the published dev26 source pin is intentionally unchanged until acceptance.

Implemented with behavioral regressions:

- Lounge EOF/repeat and complete incoming batches reach local playback before
  fallible HTTP feedback. Tail Next waits for queue extension without cancelling
  the current resolver or inventing a decoder-load acknowledgement. Stop clears
  pending advancement and rejects late EOF. Session cancellation interrupts
  blocked Lounge feedback/rebind requests.
- Player command/report queues and WebSocket writes have deadlines and explicit
  connection teardown. Bridge stop closes registered and pre-registration
  sockets. Receiver shutdown owns and cancels/aborts its tasks; Cast listener
  shutdown closes accepted sockets and TLS handshakes have a deadline.
- Core callback queue saturation terminates the affected session instead of
  deadlocking the hub against callbacks. Session destruction cancels app and
  resolver tasks, cache work and proxy registrations. LOAD results carry an
  internal generation, so an obsolete result cannot replace a newer selection
  or restart after Stop, even when sender request IDs are reused.
- mpv IPC loss fails pending commands, clears dead handles, reaps the decoder
  and allows restart, retaining volume/mute. Failed seek releases its feedback
  gate. Bridge reconnect survives failed backend cleanup. Startup cleanup must
  finish before installing the new selection's state.
- Health now requires fresh per-route WebSocket pong evidence, not merely a
  running process and open TCP listener. Exposes responsive_routes separately
  from running_routes. This is transport readiness, not proof of audible sound
  or every application handler's progress; no automatic playback restart added.
- CI frontend tests include Cast and receiver lifecycle crates. Raw LOAD
  content IDs and free-form player error messages no longer enter Rust logs
  because those fields can contain signed media URLs.

Review included cross-checking fixes between reviewers, resolver/cache failure
paths, generic LOAD correlation, owner/observer controls, teardown and decoder
restart. Tests use deliberately full queues, failed HTTP feedback, blocked TLS,
decoder EOF/crash and failed IPC. No external throttling bypass was introduced.
No release or GitHub push is authorized by this review iteration; physical
desktop/mobile acceptance remains required before publication.

Final verification: nine Rust library crates, 225 passed / 2 ignored; Python
suite, 305 run / 10 skipped / no failures. The silent real-mpv integration
passed on .110 with the final Python sources, including decoder kill/reload,
offset, pause, seek, EOF, stop and restored volume/mute. Formatting and diff
checks passed. Targeted transport/lifecycle Clippy passed with existing
double_must_use and large_enum_variant lints allowed; strict lint is not clean
because of those pre-existing dependency-crate findings.

Activated on .110 at 2026-10-04 21:59 UTC using locally built
`vibecast-reviewed-recovery` in the operator's staging directory, SHA256
`5755d8c9553f3c8c77049d7644e1d49c9ad2f6a8dd950db7b5546ed165676ea9`.
Python mpv_backend.py, vibecast_player.py and route_manager.py are read-only
bind mounts from the staged `cast-review-python-final/src/cast_audio_lab/` directory
into the existing diagnostic image's site-packages. This is a test deployment,
not a new published image. Rollback is preserved as container
`cast-audio-receiver-pre-review`; stop/rename the test container and restart
that retained container if needed. No user data or rollback binaries removed.
Startup health: both routes running and responsive (fresh WebSocket pongs),
no startup errors observed. User desktop/mobile sound, switching, seek and
single-title-repeat acceptance requested and still pending for this new build.

## Post-dev26 transport hotfix and review — 2026-10-04

Implemented locally in the maintained frontend checkout, not yet committed,
pinned or released. A non-reading Cast peer filled the outbound socket/queue
and blocked hub progress; no new HTTP-429 was observed in the incident window.
Bound Cast enqueue to one second and socket writes to five seconds, close the
failed connection, and release its socket even if lifecycle delivery is blocked.
This is not an idle-client timeout and does not change owner-stop semantics.

Built locally and deployed to laptop .110 as `vibecast-bounded-cast`, SHA256
`5a0fa2abd84dfe32c393397fd8396e52e901df3cae4bd169d3d81e3e1c02ae81`.
Keep rollback container `cast-audio-receiver-pre-bounded-cast`.
User confirmed sound and title switching. A bounded non-reading GET_STATUS
client was disconnected while twelve healthy probes continued responding
(first 502 ms, subsequent 4–9 ms); both outputs remained ready.

Regression coverage: stalled enqueue, stalled socket write without subsequent
messages, full lifecycle queue, and healthy owner/player reports beside a slow
observer. Cast: 9 passed; core: 54 passed, 1 ignored. The broader eight-crate
library test command passed (cast, default-media, youtube, bridge, platform,
core, player-api, sdk). Formatting and diff whitespace checks passed.

Open review findings below are separate from the accepted transport fix.
Rust paths refer to the maintained frontend fork; Python paths to this repo.
They establish possible failure paths, not proof of every earlier incident.

- P1: `crates/vibecast-apps-youtube/src/lounge.rs`, EOF handling: Finished is
  stored before a fallible feedback POST, but repeat/advance is queued after
  it. Failed feedback loses advancement even after rebind. Queue the local
  transition before feedback; regression must fail the EOF POST.
- P1: same file, poll batch handling: the whole batch AID is acknowledged
  before per-message feedback POSTs. A failed POST drops remaining commands,
  including SetPlaylist following SetLoopMode. Dispatch the complete local
  batch before feedback or retain unprocessed entries; test partial failure.
- P1: `crates/vibecast-bridge/src/bridge.rs`: command enqueue, socket writes
  and report delivery still have unbounded waits and can stall the hub.
  Separate writing from receiving and bound delivery with explicit teardown;
  test a non-reading player and saturated report/command queues.
- P1: `crates/vibecast-receiver/src/lib.rs`: shutdown timeouts do not abort
  tracked tasks; forwarding awaits cannot observe cancellation while blocked.
  Ensure cancellation covers forwarding and force teardown after grace.
- P1: `src/cast_audio_lab/mpv_backend.py`: IPC EOF retains the writer and
  PLAYING state, preventing lazy restart; failing stop can also escape the
  reconnect cleanup in `vibecast_player.py`. Mock reproduction confirmed EOF
  retains the writer and the next start launches nothing. Centralize failure
  cleanup, fail pending requests, report error and allow a fresh decoder.
- P2: Lounge Next at queue tail enters awaiting_load/Buffering despite no
  replacement load; dispatch can cancel the current resolver too. Separate
  waiting for queue extension from decoder-load acknowledgement.
- P2: mpv seek TimeoutError/OSError retains `_seeking`, suppressing position
  feedback. Mock reproduction confirmed later time-pos is ignored. Clear the
  gate on failed commands and cover all transport exceptions.
- P2: `crates/vibecast-cast/src/server.rs`: accepted connection tasks are
  detached with no TLS handshake deadline or server-lifetime cancellation.
  Track/close connections on shutdown and bound handshake time.
- P2: `src/cast_audio_lab/route_manager.py`: readiness checks process/TCP
  reachability, not protocol responsiveness; it stayed ready in this incident.
  Expose protocol liveness separately without blindly restarting playback.

Review validation: 13 existing mpv tests passed; the reviewer could not run
the Python bridge tests with system Python (missing websockets). Review was
read-only apart from this record; the listed remaining defects are not fixed.
Before a future release: implement prioritized fixes with regressions, include
vibecast-cast in CI's frontend test list, commit/pin the maintained fork, and
repeat desktop/mobile playback, takeover, repeat and recovery acceptance.
No new release was made during this hotfix/review.

## dev26 acceptance — 2026-10-04

- Desktop/mobile playback and exclusive takeover in both directions passed
  physical acceptance. Replacement LAUNCH now publishes old-session removal
  before the correlated new status; stale observers cannot claim ownership.
- Checked fallback extraction fixes false success with HTTP-403 media URLs.
  Earlier HTTP-429 metadata responses and seven-second fallback attempts were
  observed. Subsequent accepted attempts used the primary path in 2.0–2.3s,
  without rate-limit/fallback events. Do not attribute that speed to the fallback
  check or claim external throttling is solved.
- Preserve HLS manifest processing outside the progressive audio cache, with a
  dedicated regression. Pin `83ba470158189de3bc223701decdc4c502d47644` for dev26.
- Core/YouTube regressions, broader frontend release tests, formatting and
  publication tests gate release; image/source verification remains mandatory.

## Desktop MDX request correlation — 2026-10-04

- Physical dev24 acceptance still produced no Lounge playlist after a complete
  LAUNCH and app-transport connection.
- The maintained historical implementation and observation notes show that an
  explicit `getMdxSessionStatus` response must echo an optional request id.
  The dev24 Rust handler returned the correct screen/device data but omitted
  that correlation, while the earlier standalone probe sent no request id and
  therefore could not expose the mismatch.
- Echo the request id without changing the connect-time unsolicited response.
  Regression now asserts the correlated value. Maintained fork commit is
  `262a5c77828e634cfa8a91f6e406fce98b74fc3a`; physical acceptance is pending
  the dev25 image deployment.

## Desktop YouTube Music MDX bootstrap — 2026-10-04

- Physical dev23 acceptance proved that Chromium received the LAUNCH response,
  opened the returned app transport with its browser and media-router sender
  identities, and requested media status. The earlier assumption that no app
  transport CONNECT followed LAUNCH was therefore incomplete.
- The decisive debug event was an explicit YouTube MDX
  `getMdxSessionStatus` request being left unhandled. The Lounge connection then
  received only keepalive/no-op commands and no playlist or playback request,
  matching the visible "connected but Play does nothing" failure.
- Answer that explicit request with the same screen/device identity already
  sent on sender connect. Keep the response bound to the requesting sender and
  retain the bounded wait for Lounge identity readiness.
- Regression covers the explicit request, handled disposition and returned MDX
  payload. Physical dev24 acceptance exposed the missing request correlation
  recorded above.

## Desktop YouTube Music LAUNCH response — 2026-10-04

- The physical Chromium desktop sender repeatedly completed device auth
  and issued YouTube app `2DB7CC49` LAUNCH, but never connected to the returned
  app transport and no Lounge selection/LOAD followed. Receiver, bridge and both
  outputs stayed ready with zero restarts; the decoder was never involved.
- Root cause is the receiver's correlated command response: LAUNCH used the
  wildcard destination `*`. Chromium's launch handler expects RECEIVER_STATUS
  addressed to its sender id before it will use the returned `transportId`.
- Send LAUNCH/STOP/SET_VOLUME responses directly to the requesting connection
  and sender id with the original request id. Send a separate request-id-zero
  wildcard update only to other platform connections so observers remain fresh
  without queuing a duplicate response for the requester.
- Regression asserts the LAUNCH response source/destination. The physical dev23
  trace confirmed that Chromium accepted the response and opened the returned
  app transport; the remaining MDX bootstrap defect is recorded above.

## Approved bounded reconnect grace — 2026-10-03

- Owner rejected indefinite playback after control loss: stop-on-disconnect was
  intentional because the laptop lacks a physical stop button. The previous
  unconditional-retention change was an unapproved behavior change, not an
  established defect in the agreed product policy. Owner now authorizes rollback,
  diagnosis and a bounded reconnect grace if appropriate.
- Rolled .110 back at 18:33:32 UTC to binary 7969bfcaf2c90dd953c6fee53f49d5141f02dbc8031d03f4aed44c238c6d226f;
  both routes ready and hash verified. Granular cache remains; unlimited retention
  is no longer live. Bounded-grace revision subsequently activated as below.
- YouTube opts into a fixed 10-second deadline after owner/last-subscriber TCP
  loss. No reattachment means Stop/session/cache teardown. Only app-transport
  CONNECT cancels the deadline and transfers ownership. Platform discovery/status
  queries, existing observers and repeated drops do not extend it. Explicit owner
  CLOSE or last-sender CLOSE, receiver STOP, replacement and shutdown tear down
  immediately. Observer loss alone does not stop an attached owner.
- Existing local management UI offers Deactivate/Activate per output: disabling
  stops the adapter process group and decoder, independent of Cast. Re-enabling
  is required before casting again. No new management controls/dependencies.
- Original 18:05 transport cause remains unknown. NetworkManager journal has no
  entries in the incident window; subsequent 18:28/18:32 closes show transport_io,
  which does not establish the original cause. No network configuration changes.
- 182 Rust tests and SDK doc test pass; two optional probes ignored. Includes
  real ten-second expiry, no extension by status polling, reconnect cancellation,
  immediate STOP/CLOSE during grace, owner CLOSE with an observer, observer loss
  with an attached owner, and replacement safe from the old deadline.
  Optimized build (3m35s) and dev20 execution check pass. Activated on .110 at
  18:47:16 UTC; both routes ready/running without restarts, installed hash verified:
  `9d95bfd0cde5b2cf5d1b90412240a361049d03a789ac598b8e710c9d663c19df`.
  Physical YTM disconnect/reconnect acceptance pending. No image/pin/version push.
  Current combined snapshot: `c6f9714f758a41206ff376a3c95fc643f79c92e4b4f190a3d8d97592217b7180`.

## Rejected unlimited sender-disconnect retention — 2026-10-03 (historical)

- At 18:05:53.872 UTC (.110), the phone .79 Cast socket closed and the YouTube
  session stopped immediately. Earlier repeats logged cached_audio=true through
  18:04:23; no adjacent decoder/cache failure. Container stayed up, no OOM/restart.
  The reason the phone socket closed is unknown; do not claim a Google/CDN error.
- Confirmed lifecycle bug: physical owner disconnect unconditionally tears down
  its app; losing the last subscribed socket does the same. Two new end-to-end
  tests reproduce both paths against the previous hub (both fail).
- SDK session opt-in survives_sender_disconnect defaults false; YouTube opts in.
  Dead ownership/subscriptions are removed but Lounge/playback/cache survive.
  Explicit receiver STOP, last-sender app CLOSE, new LAUNCH and shutdown keep
  their existing teardown behavior; other apps retain their disconnect policy.
  No timed grace or automatic sender reconnection is claimed. At most the
  existing current session/cache per output is retained until explicit teardown.
- Added safe transport-close category and teardown-origin diagnostics.
  175 Rust tests and SDK doc test pass (two optional probes ignored). Includes
  owner loss, final-subscriber loss, same-cache repeat after reattachment,
  explicit STOP/CLOSE and unchanged non-opted-in teardown. Both new regressions
  fail against the previous hub and pass with the fix. Optimized build (3m34s)
  and dev20 execution check pass. Activated at 18:26:15 UTC on .110, both routes
  running/no restarts and health ready; binary hash verified. Physical repeat/
  unexpected-disconnect acceptance remains pending. No image/pin/version push.
  Binary: `5dcb880a961c5bed7faae81363061770a46e7b7720aec578274c613c277769ab`.
  Combined patch: `ccd4dbde47f6e376fb9729fcc7a478b67654a450583ea641a2a4350f1a541853`.

## Demand-driven current-title cache — 2026-10-02

- Owner prefers gradual fetching during playback, not an eager whole-song
  background download. Supersedes the initial cache download policy below.
- Implemented sparse 128-KiB upstream Range blocks, progressive serving within
  each block, shared fetches for concurrent readers, retention of loaded blocks
  and direct forward-seek fetches without downloading the intervening prefix.
  No active request means no background sweep of remaining blocks.
- mpv local-cache loads use 30s/512-KiB demuxer readahead and 64-KiB stream buffer.
  Literal-loopback bridge listeners bound the TCP send buffer to 64 KiB, because
  otherwise a paused real mpv pulled almost all of a 2.88-MB test song into TCP.
  Existing AirPlay PCM-pipe backpressure supplies decoder demand.
- RAM limit stays 32 MiB/current output; complete-only offline repeat, selection
  eviction and no playlist archive remain unchanged. Unknown/oversized sources
  or origins ignoring Range bypass caching. Per-block header/stall/total limits
  are 15s/30s/120s; idle cache demand has no timeout.
- 167 Rust tests plus SDK doc test pass. Explicit silent real-mpv test passes:
  paused fixture retains 655,360 / 2,880,044 bytes rather than almost all audio.
  Isolated dev20 Python candidate passes 25 tests including real silent mpv.
  Optimized build (3m14s) and dev20 compatibility passed. Activated on .110 at
  21:11:22 UTC, health ready, both routes running/no restarts; hashes verified.
  Physical YTM acceptance of this granular revision pending. No image/pin/version
  publication. Snapshot SHA-256:
  `4510125af2d0da8780adbd17440b38ec58aa02a474cdbb0499f815238b7dfdb7`.

## Approved current-title progressive audio cache — 2026-10-02

- Owner approved the common-media-path cache: one current title per output,
  32 MiB RAM limit, start before download completes, cached seeks/repeat-one,
  no retained playlist loop/archive, evict on title switch/Stop/session teardown.
- Implementation in frontend SDK/core/bridge: opt-in CachedUrl, shared completion
  hint, one cancellable progressive GET, local GET/HEAD/single-Range route with
  distinct per-title token, eight readers maximum, 64 KiB body chunks. Complete
  cached repeat-one bypasses ten-minute source-URL age; incomplete/failed entries
  do not. Unknown length/oversized media redirects to ordinary streaming; HLS
  remains uncached. No disk persistence or new dependencies.
- Enable only receiver-side mpv/AirPlay decoders via localAudioCache capability;
  other players remain opt-out, avoiding loopback URLs sent to remote renderers.
  Python capability changes mirrored to lab. Existing recovery fixes preserved.
- 165 Rust tests and one SDK doc test passed; one live resolver probe ignored.
  24 Python tests pass in isolated dev20 image with exact live-candidate modules,
  including real silent mpv. Five basic AirPlay tests also pass locally.
  Optimized build (3m34s) and dev20 execution check passed. Activated locally
  at ~20:39 UTC, both routes healthy/no restarts; installed hashes verified.
  User confirms playback/seek/repeat; 2,399,842-byte completed cache and
  cached_audio=true repeat confirmed live. HTTP range and silent FFmpeg seek pass.
  Timeout-only follow-up tested but not deployed; superseded by the granular
  policy above. No image/pin/version publication.
  Historical intermediate snapshot SHA-256:
  `ebe6d4b62ecd77eeb84200e4bc20e00781b2e78987c82357ce2fbbdec5c92df5`.

## Direct Cast Play and persistent metadata failure — 2026-10-02

- At 19:42 UTC repeat renewal failed twice in metadata HTTP requests. A direct
  Cast Play bypassed Lounge recovery. User also reports reconnect now fails.
  A single watch-page probe from the receiver returned HTTP 429; the historical
  Rust error lacked status, so that exact earlier status is not established.
- Opt-in app-owned Play dispatch now covers Cast and output controls, retaining
  existing behavior for other apps and bypassing interception for app-originated
  Play. YouTube routes it through Lounge's existing fresh-load recovery.
- Safe metadata diagnostics include fixed stage, HTTP status and error category
  flags, never request URLs, bodies, keys or raw reqwest errors. HTTP 429 does
  not receive the immediate automatic retry. Resolver STOP after manual reload
  must not grant a second decoder retry budget.
- 122 Rust unit tests plus one SDK doc test passed; one live probe ignored.
  Release build and dev20 execution check passed. Activated .110 at 19:59:47 UTC;
  health ready, both routes running without restarts, binary digest verified.
  User confirms audio; fresh resolution succeeded at 20:00:53 UTC. Long-running
  repeat stability and permanent rate-limit clearance remain unproven.
  Previous binary backed up to
  `/home/<receiver-user>/cast-castplay-backup-20261002-jOVEuq/vibecast.before`.
  Combined snapshot SHA-256:
  `818f1ce1193162341a3d12547e06d62bde93798346a487c25eec01a14e458728`.
  No image publication or pin changes.

## Repeat renewal HTTP failure and empty-player Play — 2026-10-02

- New live incident: normal EOF at 18:40:54 UTC, fresh repeat resolution failed
  at 18:40:56.777 (`YouTube HTTP request failed`), then the worker sent STOP.
  At 18:41:42 Play only unpaused mpv. Read-only inspection found idle-active=true,
  playlist-count=0, no sink input, 28% volume and mute=false. The earlier recovery
  candidate was not yet deployed; this additionally exposed the pre-LOAD path.
- Added one cancellable HTTP/extractor resolution retry (250 ms delay), retained
  failed selection/position for explicit Play, and encoded failed resolution STOP
  as ERROR instead of EOF. mpv now keeps every empty/IDLE decoder idle, including
  CANCELLED, rather than reporting PLAYING/PAUSED. Decoder-start recovery remains
  separately bounded; explicit Stop clears recovery.
- 109 Rust tests passed (62 YouTube, 16 bridge, 31 core), one live resolver test
  ignored; 13 mpv tests passed with real silent decoder in isolated dev20 image.
  Ten adapter tests passed locally. Updated combined snapshot SHA-256:
  `be0d6d79406c874b7decacd626107f29595f83b0e32e22d7cb7b4fbf905ff288`.
- Compatible release build and dev20 execution check passed. Hotfix activated
  on .110 at 19:01:57 UTC; health ready, both routes running without restarts,
  deployed binary/module hashes verified. User confirms YTM audio is back;
  long-running repeat stability still needs observation.
  Backup of previous frontend/mpv module retained at
  `/home/<receiver-user>/cast-repeat-recovery-backup-20261002`.
  Public image,
  version metadata and frontend pins remain unchanged for the later release.

## YouTube load recovery prepared for later image — 2026-10-02

- Owner authorized the fix and asked to accumulate/document changes before a
  later image publication. No new deployment, commit, push, version bump or App
  metadata promotion. Existing AirPlay diagnostics and IPv6 work are preserved.
- Rust worktree `/home/codex/cast-repeat-frontend` now handles one automatic
  initial-load retry with freshly resolved media, preserving position/pause.
  Terminal failure remains retryable with explicit YTM Play. Failed media and
  speculative Next are not reused for recovery; Stop/disconnect/new selection
  cancel obsolete work. Duplicate stale errors cannot loop/restart resolution.
- Lounge reports errors separately from completion, with buffering during
  recovery. Python mpv Play/Pause preserve ERROR until a new LOAD; they no longer
  claim playback after merely unpausing a failed decoder. Mirrored into lab.
- Validation: 106 Rust tests passed (YouTube 59, bridge 16, core 31), one explicit
  live-network resolver test ignored; Rust doc tests passed. Formatted changed
  files with stable rustfmt. Twelve mpv tests passed in an isolated dev20-based
  container with candidate Python source, including real silent decoder failure
  and fresh-LOAD recovery. Ten adapter tests and one real WebSocket reconnect
  test passed locally. No live YTM recovery acceptance is claimed.
- Rust snapshot `patches/vibecast-load-recovery-20261002.patch`, SHA-256
  `d26a63fa115557b287b87800c4aa3babd8b1df77aad9c794fe3624b5f2bfcd03`.
  See `docs/youtube-load-recovery.md` for source locations, behavior, limits and
  the required new frontend commit/pins before image build. Current image pins
  intentionally still reference the last published frontend, NOT this fix.

## .110 dual-stack discovery hotfix — 2026-10-02

- Mirror the lab runtime correction: choose a verified default dual-stack bind
  for Cast/Eureka instead of always IPv4, matching mDNS IPv6 advertisements.
  Preserve IPv4 startup where default dual-stack binding is unavailable.
  Six runtime tests pass, including real IPv4 and IPv6 socket connections.
- Existing .110 dev20 container hotfixed and restarted with original runtime
  retained in `/home/<receiver-user>/cast-ipv6-fix-20261002/runtime.py.before`.
  Both routes healthy; real Cast TLS passes over LAN IPv4 and IPv6. No public
  image, version bump or push. Container recreation needs a corrected build.
- Concurrent YTM loading failure was HTTP 403 for a nonexpired signed URL;
  two fresh resolutions decoded and silent PulseAudio playback passed.
  Exact HTTP-403 cause remains unconfirmed. Owner confirmed after the restart:
  "Sichtbar und Ton funktioniert"; immediate playback/discovery acceptance passed.

## Issue #13 observable AirPlay path — 2026-10-01

- Confirmed that the Home Assistant `log_level` reached only the Rust frontend:
  the manager and route adapter remained at INFO. Adapter output was captured
  only in a private per-route file, so the public Add-on debug log could not
  explain the reported early stop or subsequent command-pipe failure.
- Dev21 passes the configured level through all supervisors and relays only
  allowlist-formatted AirPlay diagnostics to the shared log. DEBUG records the
  load/transport/FLUSH/decoder/progress sequence and numeric timing; warnings
  retain safe sender codes, HTTP status, fallback stage and decoder outcome.
  URLs, media metadata, device/route identity, addresses, credentials and raw
  native-helper text remain excluded.
- Regression coverage distinguishes a successful decoder whose samples are
  shorter than metadata duration, a sender-reported FLUSH failure, warm-to-cold
  fallback, and the complete Add-on option -> adapter -> shared-log path.
  Physical reproduction remains for the issue reporter; the resulting debug
  log should determine whether a playback fix belongs in source resolution,
  duration validation, persistent transport transition or reconnect startup.

## Issue #13 AirPlay early-stop investigation — 2026-10-01

- Reviewed the dev20 report and current main `4444f2d`. The command-pipe failure
  occurs at helper startup; it does not establish the preceding early-stop
  cause. Decoder/truncation, transport exit and next-load failure remain distinct
  hypotheses requiring the separate per-route adapter log.
- Existing AirPlay suite passes 41 tests in the prepared management environment.
  Bare system Python lacks websockets; it is not the test environment.
- Prepared `issue-13-airplay-test.md` with direct/bridge comparison, log locations
  and event interpretation. Physical reproduction remains pending. No runtime
  fix, version bump, publication or live device change is claimed. Keep #13 open.

## HA update discovery and repeatable release workflow — 2026-09-26

- Read-only live diagnosis: HA had dev18 installed from the old LAN test
  repository; the public repository already advertised dev20 as a separate,
  uninstalled App. This was not stale public metadata or a user refresh error.
- Owner explicitly authorized migration, then separately authorized scoped
  backup import into only the new App. Original and final stopped-App backups
  retained; old installation stopped/manual, public App dev20 started/auto.
  Scoped archive used new App metadata and old data, excluding Supervisor and
  HA components. Original options restored through the supported App API.
- Three route configs, installation identity and private authentication file
  compare byte-identically after migration. Two enabled routes ready; disabled
  route remains disabled. Live Chromium DE/EN/persistence/mobile tests and
  HA-ingress health/routes requests pass. No new audible acceptance is claimed.
- Measured prior publish: ~5m18s; native build/push 4m20s amd64 and 3m19s arm64
  in parallel. Failed extra smoke test and uncached repeat builds/manual release
  steps caused avoidable delay. Build caches, late version labels, a pin-keyed
  source cache and explicit one-dispatch release orchestration are implemented.
- Preparation/plan are separate from publish. Successful exact-SHA CI, source
  integrity, public image identity and both platforms gate App promotion; existing
  tags/moving main are refused. No new product release or receiver deployment
  is part of validating this automation. Implementation pushed as `a1f079d`.
  Local suite: 278 tests completed, 10 skips; actionlint 1.7.12 passes.
  Read-only Release App run `36273886576` passed. Real dev20 tag overwrite
  refusal and anonymous image verification pass. CI `36273870651` passed all
  seven jobs; the targeted amd64 rerun also passed with Rust/layer cache hits.
- Measured same-source amd64 build step: 5m19s cold (including first cache
  export) versus 20s warm; whole container job 5m45s versus 37s. Both architecture
  caches exist. This is not an end-to-end release timing or an ARM warm benchmark.
  Full automated publication remains unexercised until the next approved version;
  existing dev20 was not republished to test it.
  Operational instructions and recovery boundaries: `release-runbook.md`.

## Authorized dev20 rollout and App publication — 2026-09-26

- Owner now authorizes deployment on the selected existing test host and
  publication of the Home Assistant App update, superseding the earlier hold.
- Publish native amd64/arm64 images by digest, smoke-test both, then assemble
  the versioned multiarch manifest. Verify public retrieval before changing
  store metadata. Preserve the old receiver container and private state backup.
- Publication run `36272017913` passed both native image builds, runtime smoke
  tests and multiarch manifest publication for source `06b4ecd`. CI
  `36272018247` passed all seven jobs. An initial publication attempt stopped
  before promotion because its added smoke test imported a non-runtime module;
  the test was corrected, without adding a product dependency.
- Anonymous manifest/config retrieval verified both architectures, versions,
  labels and digests. A full anonymous amd64 pull on the selected host passed.
  Multiarch digest:
  `sha256:7ceabbf06a1d6bc91cf9d54339c04ff81bc642e09403f9361dfe68ece7f7db52`.
- Full dev20 image deployed on the selected x86_64 receiver, replacing the
  historical dev18-plus-hotfix container. All three route configurations are
  unchanged; both enabled outputs are ready with zero restarts. Existing host
  networking, PulseAudio bindings, 1 GiB memory/1.25 GiB swap and 128 PID limits
  remain. Old container and private consistent state backup are retained.
- Live Chromium checks pass DE/EN, reload persistence, unsaved drafts, mobile
  layout and zero configuration writes/JS errors. Local suite: 265 tests,
  10 skips; synthetic browser regressions also pass. No new audible playback
  or physical ARM acceptance is claimed by these deployment checks.
- App metadata promoted to dev20 for amd64/aarch64 in `75ea620` after the above
  gates; anonymous readback confirms the public version/architectures. Prerelease
  `v0.6.0-dev20` is public with all four source/digest attachments uploaded.
  Updated release notes, install docs and source evidence accompany promotion.
  Vendored frontend source run `36272062424` passed the frozen/offline build;
  downloaded archive checksum and source pin match. Details: `release-dev20.md`.

## German/English UI and native ARM64/x86_64 builds — 2026-09-26

- Owner explicitly defers image publication. Implement/test the language switch,
  push source and build both architectures. ARM is taken as ARM64/aarch64.
- Bilingual UI implemented without a framework or runtime dependency. Preserve
  drafts/discoveries, browser-local language preference, translated live status,
  dialogs and errors; storage failure and ingress are covered.
- Chromium tests passed on desktop/mobile and root/ingress paths. Existing
  Python suite completed 264 tests successfully (10 skips), including the
  architecture gate.
- Native ARM64 build uses the same 31 Python versions with separately downloaded
  and hashed wheels and the official pinned aarch64 AirPlay binary. CI and the
  artifact-review workflow now have native amd64/arm64 jobs. Both builds passed.
- Implementation `670c80a` is pushed to main. CI `36271012310` passed all seven
  jobs (Rust, browser, three Python versions and both native container smoke
  tests). Review run `36271012452` built and verified both OCI archives including
  blob checksums, SBOM and provenance. Download links and expiry are recorded in
  `language-and-arm64.md`; physical ARM speaker acceptance remains untested.
- Restore store metadata to the actually available dev18 image so source pushes
  do not advertise an un-downloadable App update. Build version is dev20;
  publication workflow now reads its version from the source project instead.
- No image publication, App update or live receiver replacement in this task.
  Details: `language-and-arm64.md`.

## Repeat-one preparation and HA update status — 2026-09-26

- Owner asks whether HA can update, asks for release notes, and requests reduced
  repeat-one delay unless it needs a significant architecture change.
- Correction: dev19 is advertised in App metadata and has changelog entries,
  but its image has not been published. The live test host has a frontend-only
  hotfix. Do not call an HA update ready before the versioned image is available.
- Small frontend-only optimization: retain one current stream description with
  the original resolution timestamp and existing ten-minute freshness bound.
  Explicit repeat EOF reuses it, preserving the next-title preparation. Stop,
  another load, mismatched title or codec invalidates reuse. No audio-file cache,
  additional resolver process, dependency or output architecture change.
- Frontend `35ffe1b`: 51 YouTube tests pass, one live probe ignored. Tests cover
  repeated reuse, unchanged timestamp, freshness, codec/title mismatch, Stop
  and preserving manual Next. Product pin/notes pushed as `b3ff707`. Compatible
  release built and deployed as a frontend-only hotfix; both routes are ready.
  Owner confirms repeat is faster and manual Next still works. Receiver logs
  confirm current-stream reuse followed by prefetched Next. Live acceptance is
  complete for this follow-up; image publication remains separate.
- GitHub CI `36269656983` passed Python 3.11/3.12/3.13, Rust and container build.

## YouTube Music repeat — 2026-09-26

- Owner requests diagnosis, implementation and GitHub push, then explicitly
  authorizes deployment and a joint test on the existing SSH test host.
- Root cause: Lounge `mlm` capability, `setLoopMode` handling and
  `onLoopModeChanged` feedback were absent; EOF always dispatched Next.
- Implement session-local Off/One/All, initial playlist mode and feedback.
  Reuse normal selection for repeat-one EOF and repeat-all wrap so the resolver
  cancellation and playback queue stay synchronized. Manual Next ignores One.
- Work is isolated from the original development checkout's unrelated changes.
  Frontend `1bc5f2e` and product `b007598` are pushed. All five GitHub CI jobs in
  run `36268427174` passed; 149 Rust tests passed (one live probe ignored), and
  the Python suite completed 263 tests successfully (10 skips).
- Compatible release built and activated as a frontend-only hotfix in the
  owner's selected test container, retaining its dev18 manager/image, state and
  limits. Health and both routes are ready; previous binary is saved for rollback.
  Owner confirms all modes selectable, One-mode replay, manual Next and All-mode
  wrap to the first playlist title. Repeat acceptance is complete on the selected
  host. Build/deployment hashes and rollback details: `youtube-repeat.md`.

## Post-publication documentation and automation cleanup — 2026-09-20

- Rewrite the repository landing page around the actual user journey: purpose,
  capabilities, one-click HA installation, direct LAN URL/port and honest limits.
- Add a separate technical narrative explaining discovery, device authentication,
  YouTube/Lounge, DMR, the player bridge, outputs, DIAL and failure boundaries.
  Keep exploit-style procedures and credential material out of user docs.
- Fix the obsolete My Home Assistant redirect/badge identifier and regression-
  test the checked link spelling plus local documentation targets.
- Resolve bot issue #6 as stale because airplay-cli v0.5.4 is already pinned.
  Make the watcher close its own stale issue when all watched pins are current.
- Close Dependabot PR #7 rather than merge an incomplete requirements-only
  update. Python locks, selected wheels and source inventories are one reviewed
  release unit; remove automatic pip PRs that cannot preserve that invariant.
- After documentation is public, mention the release only in existing threads
  whose stated need is a Linux/HA Cast-audio receiver or Cast-to-AirPlay bridge.
  Avoid unrelated or duplicate announcements. Completed for the exact Airbridge
  receiver feature and Shanocast authentication-failure threads; the older Home
  Assistant Community receiver requests remain suitable places for a future
  owner post because this GitHub session has no forum identity.

## Publication execution status — 2026-09-20

- Experimental prerelease `v0.6.0-dev18` is public. Anonymous GHCR manifest
  acquisition returned the recorded digest
  `sha256:4c336373f76be7d05d0ea40c45c64b16158415681cdae7c9d67810f941f2c965`.
  A real HAOS Supervisor accepted the public repository as an image-based App,
  updated the existing installation from dev16 to dev18 and retained all three
  route IDs/configurations. A separate clean install from the public repository
  started with an empty App data directory, acquired the pinned external bundle
  and reported ready. That disposable install was removed and the persistent
  dev18 installation returned ready with all routes running. An explicit older-
  image rollback remains untested; an App-scoped pre-update backup exists.
- The relevant Music Assistant discussion now links to the usable public
  prerelease and explicitly describes the revocable/experimental limits, lack
  of Google Home groups and absence of a promised Music Assistant integration:
  https://github.com/music-assistant/support/discussions/2354#discussioncomment-18529993
- The owner independently made the separate bundle repository public and
  published prerelease `2026.09.20`. Anonymous manifest/bundle acquisition,
  exact size/hash verification and mode-0600 import passed. Bundle bytes remain
  outside both Git histories and all container layers.
- dev18 local suite passed 260 tests (10 skips); CI run 35522674582 passed.
  Candidate image workflow 35522486246 passed and published digest
  `sha256:4c336373f76be7d05d0ea40c45c64b16158415681cdae7c9d67810f941f2c965`.
  Anonymous image pull, published-image HA update and clean public-repository
  install now pass. Explicit image-version rollback remains a later operational
  check rather than a blocker for the labelled experimental prerelease.
- The first-download path is now real: explicit/BYO paths take priority, an
  existing bundle is never replaced, and only an empty clean installation uses
  the pinned public manifest. Withdrawal affects new installs, not local copies.

## Publication execution — dev18, 2026-09-20

- User explicitly asks to finish publication, not add more features. Freeze
  playback behavior and prepare the existing experimental amd64 receiver.
- Implement initial container bundle acquisition using the packaged non-secret
  manifest and separately pinned digest. Explicit BYO paths take priority;
  existing private state is never implicitly replaced. Restart does not fetch.
  New regression tests cover manifest identity, download-once, empty/symlink
  state rejection and unchanged privilege dropping. Live HA remains unchanged.
- Manual GHCR workflow produced the versioned tag with source/revision labels,
  SBOM/provenance and a recorded digest. GitHub package visibility and anonymous
  pull still need explicit verification after the main repository becomes public.
- Prior source-delivery archives are retained for the public dev18 prerelease.
  Source, bundle and image availability are checked independently.

## Native source delivery progress — 2026-09-20

- Final dev18 prepublication run: 260 tests completed successfully with 10
  environment skips in both the clean checkout and 274-file allowlisted export.
  Reachable-history review passed 15 commits/396 path versions. Public bundle
  availability/import passed; published-image HA update/rollback remains open.

- Python source collector verifies the exact 31 pinned container wheel hashes
  against PyPI and finds an sdist for each. All sdists downloaded/hash-checked
  without running setup/build code; 33 MB source ZIP and inventory prepared for
  the dev18 release. The Deno wrapper and native wheel libraries remain an
  explicit scope limit, not silently counted as complete native source coverage.
  See `source-delivery.md` for artifacts and remaining component distinctions.

- Native source archive and hash record were verified for inclusion with the
  dev18 release. Clean export and history results are recorded above.
- Manual `source-review.yml` run 35521105935 PASSED: immutable frontend plus
  Cargo.lock-vendored crates builds the release CLI with --frozen. Downloaded
  archive SHA-256 verified; 381 metadata packages, each declares a licence or
  licence-file field. This is an inventory, not blanket compatibility clearance.
  The archive is retained for the public release. Runtime is unchanged.

- Added reproducible `tools/package_airplay_source.py`: nine pinned public
  component trees, preserved notices, explicit OpenSSL correction and standalone
  build instructions. No worktree edits, untracked files, Git database, runtime
  credentials or precompiled libraries enter this archive. Exclusive atomic
  output prevents overwritten releases and incomplete artifacts on failure.
- Split the already tested compilation steps into `build_exported_airplay.sh`,
  shared by the Git-based provenance build and the standalone archive. This is
  developer/release tooling only, not a runtime binary change.
- Real archive extracted to a fresh directory, built without Git/downloads:
  upstream suite and --check passed; binary SHA-256 matches the earlier source
  candidate (05412167…3651c79). No physical receiver was restarted.
- Added regression tests for deterministic archives, immutable source selection,
  omitted binaries/untracked files, unsafe archive paths/links, existing-output
  protection and failed-assembly cleanup. Broader container source/notice
  packaging review remains an ongoing maintenance concern.
- Separate `Allcrafter1/cast-audio-receiver-bundles` repository and prerelease
  `2026.09.20` are public. Its Git history contains only documentation; the
  release assets hold the bundle/manifest. Authenticated and anonymous download
  verified exact size/hashes and private local permissions. Metadata-only record:
  `config/bundle-artifact-staging.json`.
- Use the agreed pinned-manifest SHA-256 trust path initially; a separate signing
  infrastructure is not required by the user's hash/signature decision and is
  not falsely claimed. Anonymous availability and import subsequently passed.

## Final artifact review snapshot — earlier 2026-09-20

- This section records the earlier dev17 gate review. Current authoritative
  release status is at the top of this document. The accepted historical
  discovery identifiers are not a remaining blocker.
- CI at product commit `4a2ae2bef8add95d6687e49a84bedf756c185264` passed all
  Python 3.11/3.12/3.13, Rust and container jobs (run 35519362352).
- Private OCI review run 35519446102 also passed. Downloaded artifact checksum,
  all 26 blob hashes and referenced layer sizes verify; SPDX and SLSA provenance
  refer to image `sha256:ed309583fdcc2bcd8617b9d8bdbdee34c9d988bb7dbc99d6f1710b4665299b56`.
  The scanner lists 352 package records. This is integrity/build evidence, not
  blanket licence clearance: separate native executables are scanner blind spots.
- New read-only `tools/inspect_oci_review.py` checks descriptor/subject integrity,
  optional streamed blob integrity and bounded metadata without dumping build
  arguments, extracting layers or running image code. Regression tests cover
  corruption, duplicate entries, missing evidence and wrong subjects.
- Final local suite: 248 tests completed successfully, 10 environment skips.
  Allowlisted export: 259 files; current nine-commit history check reports no
  findings and exactly one owner-approved historical identifier document.
- Fork README is public and corrected. Follow-up documentation-only commit
  `ae08681b2d617627d9e1a4edf2b0c9546ba567d9` adds the Chromium BSD text beside
  cast_channel.proto and links it from README. Runtime pin remains e67628f;
  runtime code is unchanged and main distribution already preserves BSD text.
- Subsequent dev18 work completed the source packages and separately hosted,
  pinned bundle path. Published-image installation/update/rollback verification
  remains open. See `release-artifact-review-dev17.md` for the historical gate.
- Hardware breadth (HomePod, Yamaha, Sonos, concurrent outputs, small machines)
  remains explicitly unverified, not a demand for universal hardware support
  before an honestly labelled experimental release. HA stays on accepted dev16.

## Owner approval and fork correction — 2026-09-20

- Owner accepts the identified non-credential discovery identifiers in old
  history. No repository rename or history rewrite is needed. Current docs
  remain sanitized. History checker exempts only the exact accepted document
  hash from the device-ID rule; private-key and other checks still run. Tests
  cover modified documents and a key-containing explicitly listed document.
- [x] Public fork README corrected and verified by GitHub README blob identity:
  https://github.com/Allcrafter1/vibecast/blob/e67628fa72550095f92197550d60d8e94c503d4e/README.md
  Maintained `cast-audio-receiver` branch is now the default; old upstream main
  and history retained. README clearly distinguishes provenance, fork changes,
  product/runtime responsibility, MIT licence, AI assistance and limitations.
- Reviewed bridge overlay is incorporated in that commit. Its six-file Rust
  diff matches the previously CI-tested overlay SHA-256 exactly. Product build
  and CI now pin the commit directly; fallback base/patch remain recorded in
  config/vibecast-frontend.lock.json. Do not apply the overlay twice.
- Previous CI at private product commit 65b203c passed every job: Python
  3.11/3.12/3.13, Rust, and container. New direct-commit build input and final
  artifact/SBOM review still require a new build. Main product remains private;
  no runtime image or authentication bundle was published.

## Review correction — fork README and identifier scope, 2026-09-20

- User correctly identifies a missing independent deliverable: the PUBLIC
  `Allcrafter1/vibecast` README still presents the original upstream product,
  upstream badges/releases and browser-player quick start. Updating the main
  Python/product README did NOT complete the fork documentation task.
- [x] Update the maintained fork README: identify this as the audio-oriented
  frontend fork for Cast Audio Receiver Lab; credit/link upstream and preserve
  MIT notices; distinguish upstream implementation, our changes and the Python
  product's responsibilities; document exact committed behavior and any overlay
  still applied by the product; mark inherited instructions as upstream-only;
  do not advertise unrelated upstream releases as builds of this fork.
- [ ] Verify the rendered public fork README and product README separately,
  record their commit URLs, and check installation links against actual release
  availability. Neither documentation task closes the other.
- Privacy finding clarified: the historical report contains two MAC-formatted
  AirReceiver discovery IDs for two services on the same reference Android
  phone, plus user-selected receiver aliases. They are NOT passwords/private
  keys, and are not established to be the phone's physical Wi-Fi MAC address.
  The removed historical session UUID is also not established to be an access
  credential. Do not describe these findings as credential leakage.
- User permits disclosure of speaker models. Whether the specific discovery
  IDs may remain in old history is a separate, low-risk privacy choice, not a
  technical requirement to rename/recreate the repository. Previous proposed
  rename remains unexecuted; do not treat it as mandatory. If accepted, retain
  existing history with a narrow documented exception, keeping current docs
  sanitized and credential/material checks strict.

## Publication preparation — dev17 candidate, 2026-09-20

- **Publication blocker found by manual review:** an old reference-test report
  contains real device identifiers in the private staging Git history. Current
  source now uses documentation placeholders and omits a historical session ID.
  The strengthened documentation-ID check rejects that older blob. Earlier
  bounded scan passes did not establish complete privacy clearance.
- Do not flip the existing staging repository public or force-rewrite/delete its
  history. Prepare a fresh clean-history export instead. Preserving the staging
  repository privately under a new name and creating the public project at its
  current URL needs the owner's naming/rename decision before external changes.
- App icon verified live by Supervisor response digest. Quellcode-build of
  airplay-cli passes the upstream suite and --check. CI on private 65b203c:
  Python 3.11/3.12/3.13 and Rust passed; container job still running at this check.

- Clean release staging commit 65b203c pushed to the existing PRIVATE main
  repository after 243 local and clean-checkout tests passed (10 skips).
  Reachable-history scan: eight commits, 331 path/blob versions, no findings
  under the bounded rules. GitHub Python 3.11/3.12/3.13 jobs pass; Rust/container
  jobs must finish before this is called a fully verified CI release candidate.
- Added explicit manual OCI artifact-review workflow with BuildKit SBOM and
  provenance, SHA-256 and seven-day artifact retention. No image push, public
  release, private bundle download or visibility change in that workflow.

- HA branding implemented from the existing project SVG: reviewed 128 px icon
  and 256 px logo, exact digest allowlist for binary exports, App README/changelog
  and private-test packaging. Private LAN repository commit 5172cad contains
  presentation only; Supervisor's icon endpoint returns the exact expected
  digest despite its store-reload CLI timeout. Runtime stays dev16 unchanged.
- Controlled native source build now passes upstream make test and --check:
  immutable airplay-cli source, corrected OpenSSL 3.5.4, rebuilt ALAC and mdnssd.
  Recipe: tools/build_airplay_source_candidate.sh. This is a candidate, not a
  silently substituted deployment binary or byte-identical upstream rebuild.

- Added historical-blob safety check and regression coverage for an old secret
  absent from the latest tree, empty histories and symlinks. Fresh private
  staging clone: seven reachable commits, 259 path/blob versions, no findings
  under the bounded existing export rules. CI now checks full reachable history.
  This is not a claim of exhaustive secret detection or manual clearance.
- Final local verification after these additions: 242 tests successful, 10
  environment skips; 248-file publication export passes bounded safety checks;
  diff whitespace check clean. New checks/documentation remain local, not
  pushed or deployed. The full suite was not rerun from this final expanded
  export (the preceding 242-file export's full run is recorded below).

- Follow-up: found OpenSSL 3.5.4 source association in the immediately preceding
  proxy commit; the next commit changed only its gitlink back to older source.
  Added pinned evidence record, read-only checker and negative regression tests.
  Real recursive-checkout verification passes all seven checks. Detailed next
  steps: `airplay-native-source-audit.md`. No runtime/binary replacement yet;
  corresponding-source correction and controlled rebuild remain to complete.

- User confirms actual YT Music playback through DLNA works. dev16 remains the
  deployed, accepted version; do not silently replace it during release audits.
- Publication preparation is authorized. GitHub access verified; main project
  is private, maintained Vibecast fork public. No public release made here.
- Fixed DLNA autoplay=false preloads being mistaken for cancellation when the
  renderer reports STOPPED. Explicit Play now waits for real PLAYING feedback.
  Added automated preload → delayed Play → observed playback regression.
- Native provenance investigation confirms libopenssl's .gitmodules requests
  branch openssl-3.5.4, but its recorded gitlink is
  8ddacec11481a37302c19f4454e23299af399f83 (1.1.1 lineage). A branch hint does
  not change recursive checkout or prove which source built a static archive.
  Do not close the corresponding-source release gate on that evidence alone.
- Verification: full local suite and isolated 242-file publication export each
  run 238 tests successfully (10 environment skips). CI now repeats the suite
  from the isolated export on Python 3.12 to detect development-only file
  dependencies. This does not replace manual privacy/licence review.
- Next release tasks: resolve exact native corresponding source/build inputs;
  audit clean export and its new history; reconstruct/test the clean release;
  generate image dependency inventory/SBOM; verify image update/rollback.
  Separate bundle distribution/provenance gate remains open. Do not publish
  private runtime state or claim general hardware acceptance.

## DLNA compatibility and discovery — dev16, 2026-09-20

- Actual latest YT Music adapter log: SetAVTransportURI returns UPnP **402**;
  UpnpActionResponseError was not covered by the shared command handler and
  caused a whole adapter reconnect. Translate DLNA library failures into safe
  recoverable command errors, clean loading/stop state, retain the speaker.
- Controlled TV comparison: same local MP3 HTTP URL accepted; HTTPS immediately
  rejected with 402. User also confirmed the TV required controller permission
  and then the earlier direct MP3 test was audible. Do not attribute all earlier
  failures to HTTP headers; the permission change is a confounding factor.
- User explicitly approved an output-local compatibility relay. Implemented
  within DLNA only: HTTPS, loopback-only sources and unadvertised MIME types are
  prepared as local HTTP files; compatible audio is remuxed without re-encoding,
  otherwise FFmpeg makes stereo 44.1 kHz/192 kbit MP3. Supported direct HTTP
  sources remain direct. No new library or changes to Cast/AirPlay decoding.
- Conservative **finite-item** implementation: wait for a complete bounded file
  so old TVs receive Content-Length plus real byte ranges, not invented lengths
  or an incompatible chunked response. 64 MiB/item, 90 s preparation timeout,
  at most two completed files plus one in progress; stop removes temporary data.
  The temporary filesystem may be RAM-backed. More initial latency/CPU/storage
  than direct forwarding; infinite/live sources needing conversion are not yet
  supported. This is not gapless/multiroom support.
- Automatic IPv4 SSDP renderer discovery via existing async-upnp-client;
  bounded same-responder local-IP description fetches, XML limits, UDN dedup,
  explicit disabled import and existing-route detection. HA live search finds
  the physical Samsung and correctly marks it already imported.
- Private dev16 deployed. Full physical test: Cast DMR WebM/Opus source through
  HA relay → MP3 over HTTP → TV reached PLAYING with advancing real position;
  clean owned-session STOP; all three route restart counters remain zero.
- Verification: 237 Python tests successful, 10 environment skips. Container
  rebuild passed real FFmpeg conversion/HTTP-range tests and real silent mpv.
  Final targeted rebuild succeeded after a store-wide git-reload timeout;
  app health confirms all three routes ready. Source-review export: 242 files,
  bounded secret scan passed (not a full publication/source-history clearance).
- User YT Music acceptance passed. Pending: seeking/pause/volume/automatic-next on the
  real TV, other DLNA devices, repeatability after power cycles and resource
  measurements on smaller hardware. No general device compatibility promise.
- Explicit follow-up for generic DMR: test autoplay=false preloading against a
  renderer reporting STOPPED before first Play; the polling state mapping needs
  to distinguish that from a cancelled/finished session. Not covered by the
  successful autoplay=true physical tone test.
- All prior licensing, publication, bundle and other output test gates remain.

## DLNA physical TV investigation — dev15, 2026-09-20

- User confirms dev14 local HA audio and embedded UI now work.
- Samsung TV route contained only an HTTP origin on port 80; that port refuses
  connections. SSDP from the LAN test host reports a MediaRenderer description
  on port 52235 at `/dmr/SamsungMRDesc.xml`. Fetch and upstream DmrDevice status
  query succeed at that address. This is a proven configuration blocker, not
  evidence that playback/transcoding works yet.
- Prepare stable-ID DLNA target editing in management API/UI; validate the
  complete route set to retain duplicate-target protection. Failed initial
  UPnP updates no longer cache a partially initialized profile.
- TV advertises MP3/LPCM audio; no audio MP4/WebM/Opus support advertised.
  Current DLNA output forwards source URLs without transcoding. After correcting
  the endpoint, test a known-compatible HTTP MP3, then actual YT Music. Older
  TV HTTPS/codecs may require an output-local HTTP/transcoding relay; do not
  promise compatibility or introduce that larger change without evidence.
- Remaining release, licensing, other target tests and bundle gates unchanged.
- dev15 deployed privately; existing Samsung route updated to the SSDP URL
  without changing its route/Cast ID. 224 Python tests pass (9 environment skips).
- Playback is NOT confirmed: an ordinary HTTP MP3 fixture elicited UPnP 716 at
  SetAVTransportURI even with empty DIDL. A fixture with HTTP/1.1 and explicit
  DLNA contentFeatures/transferMode headers was accepted, but the bounded test
  saw TRANSITIONING/STOPPED rather than confirmed advancing TV playback. These
  fixture changes were combined, so no individual header is proven causal.
  Capture/compare actual source delivery next; do not treat this as a codec-only
  failure or claim the full DLNA path fixed. Temporary fixture servers self-stop.

## HA audio and embedded UI correction — dev14, 2026-09-20

- User supplied a physical audio device; the older statement that HA has none
  is superseded. Supervisor sees an active analog stereo output.
- Fixed missing `audio: true` app declaration. The first live test still failed:
  the container also lacked a passwd entry for runtime UID 1000 and inherited
  root's HOME. Added a non-login service user/group and its writable HOME.
- Private HA dev14 deployed. Two subsequent synthetic-silence Cast DMR tests
  progressed from BUFFERING to PLAYING with advancing decoder time and clean
  test-session STOP. Supervisor confirms mpv belongs to this app and feeds the
  physical analog output, not a null sink. Audible/user YT Music test still open.
- UI API requests now preserve same-origin HA Ingress cookies instead of
  explicitly omitting them. LAN access remains login-free. Explicit no-store
  requests and understandable 401/403 errors prevent opaque JSON failures.
- Ingress and LAN live API responses agree on version, route IDs and process
  states. JavaScript helper executed under Node verifies relative paths,
  credentials policy and expired-session error. User iframe acceptance remains
  open; an API proxy check is not equivalent to a full logged-in browser test.
- Python suite: 222 tests, 9 environment skips, successful. No Cast protocol,
  AirPlay or bundle changes; laptop receiver remains stopped.
- Remaining dev13 release/licence/SBOM, hardware tests and distribution gates
  below are unchanged. These two fixes do not authorize publication.

## Execution result — dev13 review candidate, 2026-09-20

This updates the review gates below, not the publication authorization. Causes
and evidence: [`review-dev13.md`](review-dev13.md).

### Implemented and verified

- **Local/HA mpv:** exact older-signature fallback, preserved offset/pause,
  terminal errors instead of stuck BUFFERING. Real silent IPC test is now part
  of the container build and passed against the packaged mpv.
- **Seek/status:** queued notifications read current state instead of replaying
  pre-seek snapshots; socket/session replacements reject stale notifications.
  Deterministic tests pass. YT Music visual acceptance remains separate.
- **DLNA/Sonos UI:** independent labelled fieldsets and responsive grid; DOM
  tests plus visual Chromium checks at 390/1200 px widths pass.
- **One UI:** direct login-free LAN management/HA ingress retained. Player bridge
  defaults to loopback; inherited browser root/script disabled in normal builds.
  Bridge/proxy/registration tests and optional browser-feature tests pass. OCI
  and CI use the same hash-recorded overlay on the maintained fork base; no new
  public fork commit was pushed.
- **airplay-cli v0.5.4:** verified source/asset/checksum pins; upstream static test
  suite and binary self-check pass. v0.5.3 rollback record retained. Runtime does
  not use a shared PTP daemon.
- **Physical reference RAOP:** updated sender passes pause, paused seek, load,
  EOF and short remainder on the same connection, then recovery after deliberately
  terminating only the test-owned CLI. Laptop-to-reference-phone test, not HomePod.
- **README/provenance:** Vibecast foundation/fork/product clearly distinguished,
  AI disclosure and experimental boundaries retained. Historical receiver remains
  in research. Added Chromium BSD, original AirPlay notices/GPL, newer libraop
  MIT and OpenSSL 3.5.4 evidence; notices are packaged, not only linked.
- **Bundle plumbing:** explicit trusted-hash acquisition, bounded HTTPS/no
  downgrade, private atomic import, rejection/withdrawal tests; synthetic data
  only. BYO/HA share import unchanged. No real hosted release or signing identity.

### Verification and deployment

- CPython 3.12: **220 tests, 9 environment skips**, successful.
- CPython 3.13 on Linux test host: **220 tests, no skips**, including real FFmpeg
  and silent mpv. Compile and diff-whitespace checks pass; no Python 3.11 claim.
- Rust: **144 passing, 1 opt-in live YouTube test ignored** across seven crates.
  Final bridge/platform rerun, **17 browser-feature tests**, rustfmt check pass.
- Wheel builds/runtime inventory and source allowlist export pass. These do not
  constitute full Git-history secret or transitive licence clearance.
- Private **HA dev13** build/update passes (including packaged-mpv/CLI checks).
  App-scoped backup made beforehand. LAN UI and ingress work, health shows both
  routes running, and LAN port 8010 refuses connections. Restart preserves IDs,
  names, backends and enabled state. Tested support response excludes route
  names, private LAN addresses and credential fields.
- Laptop Cast receiver remains stopped. No repo/image/real bundle/community
  announcement published externally.

### Still open — do not silently mark complete

1. User acceptance of YT Music seek feedback, song changes, disconnect,
   volume/artwork on the HA AirPlay path. Physical local audio was subsequently
   supplied and exercised in dev14 (see latest section); audible acceptance is
   still separate from the successful silent decoder/physical-sink checks.
2. HomePod/native AP2/OS27, Yamaha, DLNA/Sonos, simultaneous real targets and
   receiver-origin controls require physical tests. No universal Cast claim.
3. Final image SBOM/corresponding-source audit: upstream notice says OpenSSL
   1.1.1u; inspected prebuilt x86_64 library is 3.5.4 but its source submodule is
   1.1.1-era. Provide matching source/build inputs before public binary release.
   This is not proof of a blanket GPL/OpenSSL prohibition. Preserve actual
   Debian/Python/Rust component notices.
4. Real bundle hosting/signing identity, signature/attestation issuance and
   verification, provenance/rights text, explicit upload checkpoint. Implemented
   trust path is a **pinned hash**, not a live signing service. Withdrawal cannot
   recall copies; rollback/BYO remains local.
5. Final source/history/image secret audit; publish the fork overlay and replace
   it with an immutable commit pin only in the approved publication round.
   Community announcement follows usable public source/documentation.
6. Public-image installation/rollback (distinct from private source update), ARM
   and resource measurements on smaller hardware.

No worker, Rust/yt-dlp merge, format-probe removal, Google Home groups or protocol
redesign was introduced.

## Manual acceptance correction and Astra review gate — 2026-09-20

This section is the authoritative immediate plan. It supersedes broad wording
elsewhere that the current tree is generally "clean and functional". The
architecture remains a credible open-source base, but the product is **not
release-ready** after the latest manual acceptance round. Do not publish the
repository, image or authentication bundle until the gates below are resolved.

### Decisions after the licence/distribution review — 2026-09-20

> Historical record: the project-license choice below was superseded by the
> owner-authorized MPL-2.0 transition on 2026-10-04. See `LICENSING.md` and
> `docs/licensing-audit-2026-10-04.md`. The third-party boundaries remain valid.

- At this review point, original Cast Audio Receiver Lab code was kept under
  **GPL-3.0-or-later** while
  retaining every incorporated component's own copyright, licence and source
  obligations. The root licence does not relicense Vibecast, Chromium protocol
  files, airplay-cli, libraop, FFmpeg, mpv or credentials.
- The project does **not** use the official Google Cast SDK or a receiver
  registered through its developer console. Document the Cast path as an
  independent implementation based on the maintained MIT-licensed Vibecast
  fork and separately licensed open-source protocol material. Google/YouTube/
  Play terms can still apply to services and the purchased reference app.
- The current `libraop` upstream now explicitly states that Philippe's code is
  MIT-licensed while third-party code retains its own terms. This materially
  resolves the prior `pairing.cpp`/`bplist.cpp` ambiguity. Preserve the current
  upstream statement, correct the stale airplay-cli notice in our provenance
  record and retain all third-party component notices.
- Adopt Music Assistant **airplay-cli v0.5.4** as the next candidate, not as an
  untested blind pin. Compared with v0.5.3 it adds OS-27 standalone-HomePod PTP
  clock following and raises the shared followed-clock capacity from four to
  eight. It does not intentionally change the RAOP command/status contract.
  Update the verified asset/checksum/source pins together and run the regression
  matrix in the Astra hand-off before calling it accepted.
- The owner has consciously selected **public, separate, withdrawable
  distribution** of the completed authentication bundle unless a later review
  finds a clear legal exclusion. Never commit bundle bytes to the main Git
  history and never bake them into the normal source tree or OCI image.
- Preferred first implementation: a dedicated minimal GitHub repository used
  only for documentation and versioned Release Assets. Commit only a manifest,
  provenance/risk documentation and verification metadata; attach the bundle,
  checksum and signature/attestation to a release. The main project pins one
  bundle version, URL and digest, supports explicit verified acquisition, and
  always permits a local user-supplied replacement. Deleting/withdrawing the
  release disables our distribution but cannot recall downloaded or mirrored
  copies. Dedicated object storage is unnecessary for the initial 2.74 MiB
  artifact and can be adopted later without changing the bundle-provider
  contract.
- Astra may prepare and test the manifest/provider/import/update/withdrawal
  plumbing with synthetic credentials, but must **not publish or upload the real
  bundle** during the technical review round. Publication is a separate explicit
  release action after source/history/artifact review.

### Classification of the new findings

#### Confirmed product bugs

1. **Home Assistant/local mpv output does not start playback.** The retained HA
   log shows successful media resolution followed by
   `PLAYBACK_COMMAND_FAILED: mpv command failed: invalid parameter`. The active
   Python backend sends the five-argument/property-map form of `loadfile`; the
   mpv shipped in the HA image rejects that form. This is a packaged-version
   compatibility regression, independent of whether HA currently has an audible
   local sound device.
2. **AirPlay seek feedback can briefly expose the old position.** Playback ends
   at the requested position, but an old progress/status observation sometimes
   wins briefly during the replacement decoder/FLUSH transition. Treat this as
   a state-correlation race until instrumentation proves whether the stale value
   originates in Python, airplay-cli/receiver events or Rust canonical state.
3. **Experimental DLNA/Sonos form layout is structurally ambiguous.** The two
   protocols share one flat row of inline labels/buttons, so responsive wrapping
   visually associates controls with the wrong section. This is a small UI bug,
   not a reason to redesign the manager.

#### Architecture/product-boundary problems

4. **Two visible HTTP interfaces have different jobs but look like competing
   products.** Port 8788/HA ingress is our management UI. Vibecast's inherited
   port 8010 page is an embedded Shaka browser *player*, not management: opening
   it connects to `/player`, registers a `Browser` player and therefore creates
   another advertised Cast receiver. The WebSocket `/player` bridge and possibly
   the session-scoped `/license` and `/manifest` proxy routes remain runtime
   infrastructure; the browser page and `/player.js` do not belong in normal
   Cast Audio Receiver Lab operation.
5. **Project identity/origin is not clear enough.** The README names Vibecast but
   does not lead with a precise product goal or clearly separate upstream code,
   the maintained fork, and this project's substantial audio/output/management/
   HA work. This is a documentation and provenance blocker, not a playback bug.
6. **Release licensing/attribution was incomplete at this review point.**
   Vibecast's MIT notice was present, and original project code then declared
   GPL-3.0-or-later, but the final
   artifact inventory, Chromium `cast_channel.proto` BSD notice, corresponding-
   source records, updated libraop evidence and direct/transitive notices still
   need to be made release-complete.
7. **Authentication-bundle distribution needs product plumbing and a final
   publication checkpoint.** The 773-window bundle is complete and privately
   functional. The owner accepts the documented legal and revocation uncertainty
   and has chosen a separate public Release Asset rather than main Git history or
   an image layer. The real material remains private during implementation; the
   release round must verify provenance text, digest/signature, withdrawal,
   replacement and secret-free diagnostics before an explicit upload.

### Product decision for the two interfaces

- Keep **one user-facing interface**: the Python manager on the configured LAN
  port and through Home Assistant ingress.
- Split Vibecast's Cast listener address from its player-bridge listener. Bind
  the player bridge to loopback by default in this product while Cast/eureka
  listeners remain reachable on the LAN.
- Preserve `/player`, `/license/{session}` and `/manifest/{session}/{route}` as
  internal protocol/proxy endpoints required by adapters and eligible media.
- Disable/remove the browser-player root and `/player.js` from the normal product
  build, or gate them behind an explicit development-only option that defaults
  off. Do not merge or reverse-proxy that player page into the management UI.
- Add tests that LAN clients cannot create `Browser` receivers, internal Python
  adapters still register, and manifest/licence proxy URLs remain reachable by
  the intended local consumer. Document port 8010 as internal, not as a second
  web interface.

This is a bounded maintained-fork change, not a replacement of Vibecast's
player protocol. Upstream Vibecast may reasonably keep its browser player; our
fork can retain it as an opt-in development example.

### Licence and authentication publication decision

> Historical 2026-09-20 decision. The project-code GPL choice was superseded by
> MPL-2.0 on 2026-10-04; it did not and does not change the licenses below.

- Keep the maintained Vibecast fork under its upstream **MIT** licence and retain
  the upstream copyright/licence text plus a clear modified-by/changelog record.
  MIT permits modification and combination, and is GPL-compatible, but its code
  and notice do not become ours or lose their MIT provenance.
- At that review point, original Cast Audio Receiver Lab product/glue code was
  kept under **GPL-3.0-or-later**, subject to a final per-file/origin audit. A combined
  distribution can carry GPL obligations while preserving each incorporated
  component's notices. The root license was never intended to imply that every bundled
  third-party component or credential was relicensed.
- Before a public image: finish exact FFmpeg/mpv/Rust/Python/airplay-cli source,
  licence and notice inventory; incorporate libraop's current MIT statement and
  airplay-cli's mixed native notices; generate an SBOM and corresponding-source
  record. Preserve the Chromium BSD notice carried by `cast_channel.proto`.
- Keep the AirReceiver-derived bundle outside the main Git history and all image
  layers. Prepare a dedicated Release-Asset provider with a versioned manifest,
  immutable digest, verifiable signature/attestation, bounded download, atomic
  validation/import and a local-file override. The management surface must state
  the source, purpose, shared-identity/revocation risk and selected version. A
  missing or withdrawn official asset fails clearly and never falls back to
  unverified material.
- Keep HA `/share` and ordinary local import as first-class offline/BYO paths.
  Exclude bundle bodies, keys, signatures and signed URLs from logs, support
  bundles, tests, issues and source exports. Separating the asset improves
  withdrawal/versioning but is not presented as resolving the legal question.

This is a release-risk assessment, not legal advice. The owner's informed
distribution decision is now recorded; it authorizes preparation, not an
unreviewed upload from the development workspace.

### Mandatory gates before public release

1. Fix and regression-test packaged mpv/local loading.
2. Investigate and deterministically test the AirPlay stale-seek feedback race;
   fix only the proven generation/correlation boundary, without sleep-based
   masking or discarding the persistent transport.
3. Correct and responsively test the DLNA/Sonos form grouping.
4. Internalize the Vibecast player bridge and remove the normal browser-player
   surface while preserving the WebSocket/proxy runtime contract.
5. Rewrite the README/project-origin narrative: product goal, what came from
   Vibecast, what the maintained fork changes, what this repository adds,
   supported/experimental paths, AI-assisted development and fragility.
6. Update to airplay-cli v0.5.4 with exact source/asset/checksum pins and complete
   its automatic plus available physical regression matrix.
7. Complete licence/attribution/source-notice review, including Vibecast MIT,
   Chromium BSD, current libraop MIT evidence, airplay-cli native components and
   exact FFmpeg/mpv/Python/Rust artifacts. Retain thanks without implying
   endorsement.
8. Prepare the separate bundle Release-Asset mechanism and verify synthetic
   download, digest/signature rejection, atomic import, BYO override, withdrawal
   failure and diagnostic redaction. Re-run secret/history scans on source and
   every image. The real upload remains an explicit later release action.
9. Run the complete Python/Rust/container gates and repeat real HA source-build,
   ingress/LAN, restart/state, local-load and physical AirPlay acceptance. Keep
   hardware-unavailable DLNA/Sonos/HomePod claims explicitly unverified.

### Ordered next implementation round

1. Establish a reproducible baseline and preserve current user-confirmed AirPlay
   output, Home Assistant status, artwork and certificate rotation behavior.
2. Update the pinned AirPlay candidate from v0.5.3 to v0.5.4, preserving exact
   hashes/source notices and proving that its unchanged interfaces still match
   our persistent adapter before mixing in unrelated fixes.
3. Fix local mpv compatibility because it blocks a primary advertised
   output and has concrete log evidence.
4. Instrument, reproduce and fix AirPlay seek feedback without changing audio
   encoding or transport lifetime.
5. Apply the small DLNA/Sonos UI grouping correction and automated DOM/responsive
   checks.
6. Make the player bridge internal in the maintained Vibecast fork, update the
   immutable pin/patch/build metadata and verify no accidental Browser receiver.
7. Rewrite README/origin/licensing documentation from the verified code and
   dependency inventory; do not overstate readiness.
8. Prepare, but do not publish, the separate bundle provider/release manifest and
   test it with non-secret fixtures plus the existing local import path.
9. Execute full CI/package/HA regression and report remaining manual hardware
   tests and publication blockers. Do not publish real credentials in this round.

The detailed hand-off for this round is
[`docs/ASTRA-REVIEW-2026-09-20.md`](ASTRA-REVIEW-2026-09-20.md).

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
- The subsequent 2026-09-20 review distinguished the legal, contractual,
  open-source-licence and technical-revocation questions. The informed product
  decision is now to prepare a separately versioned public Release Asset while
  keeping credential bytes out of the main Git history and image. A real upload
  still requires the explicit release checkpoint defined in the authoritative
  section above; replaceable local/HA import remains supported.

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
- Complete redistribution/source-notice review using libraop's later explicit
  MIT statement, airplay-cli's mixed native notices and the missing Chromium
  BSD attribution before shipping a combined public image.
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
- **Maintenance automation accepted:** the weekly upstream watcher completed a
  real manual-dispatch run and opened private issue `#6` after detecting
  `airplay-cli` v0.5.4 while the tested pin remains v0.5.3. It did not mutate
  locks or runtime code. The new release contains HomePod/PTP fixes, so review,
  a new artifact hash, CI and physical regression testing are required before
  adopting it.
- **Done in packaging source:** Home Assistant repository metadata is at the
  Git root; `ingress_port: 0` uses Supervisor's collision-free allocation while
  a separate configurable `web_port` serves the trusted LAN. Options and the
  allocated port are read through the authenticated self-info API, avoiding a
  dependency on direct access to Supervisor's root-owned options file.
- **Verified:** 201 Python tests complete successfully (20 explicit environment
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
  The same running App subsequently crossed a real midnight bundle boundary,
  rotated TLS/device-auth/discovery state in place and accepted later Cast
  connections without a restart.
- **Next:** publish/scan/inventory the intended image; test update and rollback;
  run physical AirPlay, DLNA and Sonos acceptance where targets are available.
- **Private source staging:** an allowlisted UTF-8-only export with per-file hash
  manifest excludes `.state`, generated artifacts, device captures, key/cert
  file types and known private host markers. The exported tree independently
  passes the full suite and was pushed as a new-history private GitHub repository
  at `Allcrafter1/cast-audio-receiver-lab`. GitHub CI run `35478233388` passed
  Python 3.11/3.12/3.13, runtime-wheel inspection, the targeted Rust suite and a
  clean `linux/amd64` container build. This is not yet a public release or
  redistribution clearance.
- **Authentication distribution decision remains explicit:** the user requires a
  normally installed receiver to be functional with the complete bundle. Local
  and HA acceptance already satisfy that through the private `/share` input.
  Repository rules keep authentication material in ignored private state; public
  Git history/image inclusion requires a separate rights/security review rather
  than silently publishing reusable credentials. Packaging must make this split
  obvious and avoid presenting a nonfunctional install as complete.
- **Installation boundary documented:** `docs/installation.md` now describes the
  shared supervisor for HA, OCI and native Linux, the fail-closed certificate
  requirement, owner-private full bundle, persistent state, verification and
  rollback boundary. The old runbook now uses dev12's single supervisor rather
  than obsolete manually managed frontend/manager processes.

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
  gate, not silently treated as resolved by the project's then-current GPL choice.
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
