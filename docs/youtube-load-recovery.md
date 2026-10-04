# YouTube load recovery — pending image changes, 2026-10-02

## Approved ten-second reconnect grace — 2026-10-03

The owner clarified that stop-on-disconnect was intentional and rejected the
unlimited-retention change. That earlier change altered product policy without
agreement; describing the intended teardown as a confirmed bug was incorrect.
Owner approved restoring stop behavior and adding a bounded reconnect window.
At 18:33:32 UTC .110 was rolled back to 7969bfcaf2c90dd953c6fee53f49d5141f02dbc8031d03f4aed44c238c6d226f,
with both routes ready and hash verified. The progressive cache is retained.

New policy: YouTube opts into a fixed ten-second deadline when its owner or last
subscribed Cast socket is lost. Reattachment to the same app transport cancels
the deadline and transfers ownership. At expiry the player stops, session/cache
are released and receiver status is updated. Existing observers, platform CONNECT,
GET_STATUS and further disappearing sockets do not extend the deadline. Losing an
observer while the owner stays attached does not start a deadline. Owner CLOSE,
last-sender CLOSE, receiver STOP, replacement LAUNCH and shutdown are immediate.
Other apps keep their existing policy. A user-initiated disconnect that merely
closes TCP is indistinguishable from link loss and can therefore take up to ten
seconds to stop. There is no automatic reconnection initiated by the receiver.

The hub owns absolute deadlines in its event loop; cancellation leaves no detached
timer that could later stop a reattached/replacement session. Expired deadlines
take priority over queued status traffic. No dependencies or Python changes.

Local emergency stop already exists at http://RECEIVER_HOST:8788: select
Audio Lab Laptop / Deaktivieren. It terminates that output's adapter process group
and decoder without depending on Cast. Use Aktivieren before casting again.
This is output deactivation, not a new playback-only Stop button.

Diagnosis remains inconclusive: privileged NetworkManager journal has no entries
at 18:05:00–18:06:10 UTC; later closes at 18:28/18:32 were transport_io. Those
later events do not establish the original cause. No network settings changed.
182 Rust tests and SDK doc test pass: YouTube 64, bridge 17, Cast 6, core 50,
platform 16, player API 18, SDK 11. Two optional probes ignored. Expiry tests
exercise the actual ten-second window, a late platform probe, existing observers,
reattachment cancellation and replacement safety. Explicit STOP/CLOSE tests assert
immediate teardown within a two-second test bound. Optimized build completed in
3m35s, dev20 execution check passed. Candidate SHA-256:
`9d95bfd0cde5b2cf5d1b90412240a361049d03a789ac598b8e710c9d663c19df`.
Activated on .110 at 18:47:16 UTC; manager/bridge ready, both outputs running
with zero restarts, binary hash verified and no startup warning/error. Physical
YTM disconnect/reconnect acceptance remains pending. Only the binary changed;
no Python/config changes or image/pin/version publication. Local management UI
returned HTTP 200 via the laptop LAN address.
Current combined patch SHA-256:
`c6f9714f758a41206ff376a3c95fc643f79c92e4b4f190a3d8d97592217b7180`.
Product/lab snapshots match; reverse-apply check passes. The SDK capability is
now allows_sender_reconnect_grace, not the rejected survives_sender_disconnect.

Rollback to immediate stop-on-disconnect remains available using
`/home/<receiver-user>/cast-disconnect-backup-20261003-hDZxqN/vibecast.before`
(SHA-256 7969bfcaf2c90dd953c6fee53f49d5141f02dbc8031d03f4aed44c238c6d226f).
Stop the container, copy that file to /usr/local/bin/vibecast in the container,
then start it. Python, output configuration and the granular-cache flags stay.
Do not restore the rejected unlimited-retention binary 5dcb880a... as a default.

## Rejected unlimited retention (historical) — 2026-10-03

At 18:05:53.872 UTC the .79 phone Cast connection closed and YouTube session
9dccb4dc-4b20-4f4d-b11c-bd4be0ba6a71 stopped immediately. The 2,399,842-byte
song had completed its cache; repeated cached_audio=true loads continued through
18:04:23. No adjacent decoder/CDN failure, container restart or OOM was observed.
The underlying transport-close cause is not recorded by the old binary; do not
claim that Wi-Fi, Android power saving, Google or an explicit user action is proven.

The hub unconditionally stopped apps when their launching socket closed, or when
the final subscribed socket disappeared. New end-to-end tests reproduce both
undesired teardowns against the previous hub. SDK AppSession now defaults
survives_sender_disconnect=false; YouTube opts in because its Lounge control and
playback are receiver-owned. Remove the dead socket's owner/subscriptions, retain
the same session/cache/player, and allow sender reattachment. Explicit receiver
STOP, last-sender app CLOSE, replacement LAUNCH and shutdown remain terminal.
Non-opted-in apps retain their previous cleanup behavior. This does not repair
the phone connection itself or silently restart an explicitly stopped session.

Safe logs now distinguish peer EOF, transport I/O, framing/dispatch closure,
explicit STOP/CLOSE, and preserved/terminated apps after transport loss. No raw
HTTP URLs, credentials or payloads added. 175 Rust tests pass (YouTube 64,
bridge 17, Cast 6, core 43, platform 16, player API 18, SDK 11), plus SDK doc
test. Two optional probes ignored. New disconnect tests fail against old hub
and pass with fix; same cache URL survives reattachment/repeat, explicit
STOP/CLOSE still works and existing non-opted-in policy tests pass. Python is
unchanged by this fix. Optimized build passed in 3m34s; dev20 execution check
passed. Activated on .110 at 18:26:15 UTC, both routes running without restarts,
manager/bridge ready, no startup warning/error, installed hash verified:
`5dcb880a961c5bed7faae81363061770a46e7b7720aec578274c613c277769ab`.
Physical long-running repeat/disconnect acceptance is pending; no forced network
fault injected into the user's live session. No image/pin/version publication.
Combined snapshot (including this fix and all prior recovery/cache changes):
`ccd4dbde47f6e376fb9729fcc7a478b67654a450583ea641a2a4350f1a541853`.
Both product/lab snapshots match and reverse-apply check passes. Include the
new SDK opt-in and Cast diagnostics in the future frontend commit/pin as well.

Pre-deployment rollback binary on .110:
`/home/<receiver-user>/cast-disconnect-backup-20261003-hDZxqN/vibecast.before`.
To restore: stop cast-audio-receiver, copy it to /usr/local/bin/vibecast in the
same container, then start it. Python modules/config/data are unchanged.

## Current-title audio cache (owner-approved architecture)

The earlier cache retained only stream URLs. This implementation keeps one
progressive YouTube audio object in RAM per output, up to **32 MiB of audio**,
with no disk persistence or playlist archive. At the owner's follow-up request,
the initial eager background GET is replaced by demand-driven 128-KiB Range
blocks. A single worker coalesces concurrent readers; unfetched holes allocate
no audio storage. GET/HEAD/single-byte-range responses serve available chunks
before even the current block completes. Backward seeks reuse bytes; forward
seeks request the target block without downloading the intervening prefix.
Eight concurrent readers and 64-KiB response chunks bound transfer buffers.
Per-block timeouts: 15s headers, 30s without body progress, 120s hard ceiling.
Waiting for decoder demand is not a network stall and has no timeout.

For local cache URLs only, mpv readahead is 30s / at most 512 KiB, with a 64-KiB
stream buffer. Literal-loopback bridge listeners use a 64-KiB TCP send buffer;
without this, a paused real decoder still pulled 2,752,512 of 2,880,044 fixture
bytes into kernel buffers despite the mpv limit. The corrected real-decoder
regression requires less than half after 3 seconds. These are approximate
readahead bounds, not exact timestamp-based limits; transport/container overhead
and metadata probes also request bytes. AirPlay already has PCM pipe backpressure.

Only complete objects bypass the ten-minute URL age for repeat-one. EOF retains
the current object for replay. New selection, Stop, error or session teardown
cancels its download, clears bytes and invalidates the completion hint. Each
selection has a new opaque route token, so stale URLs cannot fetch the next song.
Normal playlist traversal (including repeat-all) replaces the single slot rather
than collecting songs. Prefetched-next resolution does not download audio.

Clear progressive responses with a valid byte Content-Range and known total
<=32 MiB are eligible. Unknown-length/oversized responses or origins ignoring
Range use normal streaming via redirect;
HLS/manifests remain uncached. Truncated/rejected downloads are never marked
complete. Initial YouTube resolution still needs network access and can fail,
including with 429; the cache does not bypass access controls or rate limits.

The `localAudioCache` player capability defaults false. Python mpv and AirPlay
opt in because their decoders run on the receiver; remote-pull renderers and old
players retain existing URLs. No dependency or protocol-version bump is needed.
Rust changes span SDK, player API, core (new `audio_cache.rs`), bridge, platform
capability conversion and YouTube. Python changes: backend capability flags and
registration in `mpv_backend.py`, `airplay.py`, `vibecast_player.py`.

Granular-cache validation: 167 Rust tests passed (YouTube 64, bridge 17, core 41,
platform 16, player API 18, SDK 11), one SDK doc test passed. Live resolver probe
remains ignored. Optional real-mpv test was run explicitly and passed: a paused
180-second WAV retained 655,360 / 2,880,044 bytes after 3s (previously 2,752,512).
Sparse-range test verifies no idle prefetch, seek-to-tail without prefix fetch,
coalesced concurrent readers, no complete hint with holes, complete local replay
without further upstream requests. Isolated dev20 exact Python candidate passes
25 tests (14 mpv including real silent integration, 11 adapter). Local mpv unit
suite: 13 passed. Optimized build completed in 3m14s; dev20 execution check passed.
Activated on .110 at 21:11:22 UTC: manager/bridge ready, both enabled routes
running with zero restarts; installed binary/Python hashes verified. Physical
YTM playback/seek acceptance for this granular revision is pending.

Installed granular revision:

- `vibecast`: `7969bfcaf2c90dd953c6fee53f49d5141f02dbc8031d03f4aed44c238c6d226f`
- `mpv_backend.py`: `5e48dcca1bb99d63d7890b1629d428b94f6606ae4dc8f002bec9b50553d3d60f`
- Only these two files changed on the live container; AirPlay, adapter,
  dual-stack runtime, config/data and the dev20 image identity remain unchanged.
- Rollback to the user-confirmed eager cache:
  `/home/<receiver-user>/cast-granular-cache-backup-20261002-z1Ouhq` contains
  `vibecast.before` and `mpv_backend.py`. Stop the container, restore them to
  `/usr/local/bin/vibecast` and
  `/usr/local/lib/python3.12/site-packages/cast_audio_lab/mpv_backend.py`, start it.
- No frontend commit/pin, version change or image publication performed.

Initial eager-cache validation: 165 Rust tests passed, plus SDK doc test.
Includes early playback, offline replay/seek with one upstream GET, partial and
suffix ranges/HEAD/416, cancellation/byte release, oversized/unknown fallback,
truncation/rejection, stalled-download eviction, EOF retention, title replacement/Stop eviction, stale
token rejection, and complete-only replay beyond URL age. Python adapter 11,
mpv unit 12 and basic AirPlay 5 tests passed locally. Exact live-candidate Python
modules passed 24 tests in isolated dev20 (13 mpv including real silent decoder,
11 adapter tests). Release build passed in 3m34s, dev20 execution check passed,
activated on .110 at ~20:39 UTC; both routes ready/no restarts and hashes verified.
User confirmed playback, seeking and repeat-one. Live evidence: first URL failed
403 at 20:39:56 UTC, automatic fresh resolution loaded at 20:39:59; this added
about three seconds to startup. Cache completed at 20:40:52 with 2,399,842 bytes.
Read-only IPC confirms mpv uses the local cache. Local suffix-range request
returned 206/1,024 bytes; silent FFmpeg seek to 100s exited 0 with no diagnostic
output. At 20:43:01 repeat logged `cached_audio=true`. AirPlay hardware acceptance
is not claimed. Timeout-only follow-up was tested but never deployed separately;
the demand-driven block policy above supersedes it.

Historical initial eager-cache SHA-256 values:

- `vibecast`: `28a7266507e325c3d5683b2a1b6a81d81fcba58fe0e53ac60c48f96c8ca89388`
- `mpv_backend.py`: `92a20359431c4e632de7289973218bf0c4c55891a9d7a6af8e0cc992885cf2a5`
- `airplay.py` (live baseline + cache flag): `3210dcded55f1381eb616d01dcbd81bac0202519501d3afd011c1d67b425a80f`
- `vibecast_player.py`: `8167c9d4b006d090af576f1d703a496ea5a641a8667d9f7ca1ebf9debbb2a429`

Combined patch snapshot (including prior recovery fixes and new untracked source)
SHA-256: `c6f9714f758a41206ff376a3c95fc643f79c92e4b4f190a3d8d97592217b7180`.
Snapshots in product/lab match and reverse-apply check passes. Earlier hashes
below are historical. The later image must include the new Rust source and
Python opt-in; rebuilding from the old frontend pin does not include this cache.

Pre-cache rollback on .110: `/home/<receiver-user>/cast-audio-cache-backup-20261002-vKAHVD`
contains `vibecast.before`, `mpv_backend.py`, `airplay.py`, `vibecast_player.py`.
Live Python candidate is the existing installed modules plus cache flags only,
not the unrelated pending dev21 AirPlay diagnostics. Stop the container before
restoring these four files to their original executable/site-packages paths,
then start it. Config/data and the dual-stack fix are unchanged.

## Follow-up: direct Cast Play and HTTP 429

At 19:42 UTC both metadata resolution attempts failed; later direct Cast Play
reached the empty decoder without Lounge recovery. Reconnect also failed. One
read-only watch-page probe from the receiver returned HTTP 429. This establishes
rate limiting at probe time, not the exact status of older generic HTTP errors.

Direct Cast/output Play now opts into YouTube's existing Lounge recovery through
an SDK capability and the ordered app callback queue. Other apps retain their
normal Play path. App-originated Play bypasses interception to avoid recursion.
The Cast acknowledgement retains actual state rather than claiming PLAYING before
fresh media exists. Recovery still uses current item/position and bounded retries.
Resolver STOP after a manual reload cannot accidentally grant another decoder retry.

Metadata diagnostics log fixed stage (`watch_metadata`/`player_metadata`), status,
and timeout/connect/decode/body flags, never URLs, keys, body or raw errors.
HTTP 429 skips the immediate automatic retry; manual retry remains available.
This does not lift a YouTube rate limit or establish its cause/duration. Do not
recommend rapid repeated Reload/reconnect attempts while 429 persists.

Tests: 122 Rust unit tests passed (YouTube 63, core 32, bridge 16, SDK 11),
one SDK doc test passed, one live resolver probe ignored. Includes direct Cast
and output Play routing, unchanged generic Play, app Play without recursion,
Lounge recovery while polling, preserved HTTP status and 429 retry exclusion.
Optimized build passed (Rust 1.98.1/bookworm, offline, 3m43s), execution in dev20
passed, activated locally at 19:59:47 UTC. Health ready and both routes running
without restarts. Installed binary SHA-256:
`1b66e83c57a70a34517af401c037e2b2a36b1928d69589917c52785633fd6eee`.
User confirms audible playback. At 20:00:53 UTC a fresh resolution of the
previously failing song succeeded (start=67s, autoplay=true). This establishes
recovery for that attempt, not permanent clearance or long-run repeat stability.
Rollback to the preceding recovery binary: stop the container, copy
`/home/<receiver-user>/cast-castplay-backup-20261002-jOVEuq/vibecast.before`
back to `/usr/local/bin/vibecast`, start the same container. Python/config/data
are unchanged by this follow-up. No image/pin/version changes.

The combined snapshot now includes SDK, core and resolver files in addition to
YouTube lib/lounge. SHA-256:
`818f1ce1193162341a3d12547e06d62bde93798346a487c25eec01a14e458728`.
The earlier deployment hashes below are historical, not this new candidate.

## Follow-up: repeat renewal failed before decoder LOAD

At 18:40:54 UTC on .110 the repeated 230-second song reached normal EOF. The
expired ten-minute reuse window required fresh resolution. At 18:40:56.777 the
resolver reported `YouTube HTTP request failed` and stopped playback; no new
decoder LOAD followed. At 18:41:42 Play only unpaused an empty decoder. Inspection
confirmed `idle-active=true`, zero playlist entries, no PulseAudio sink input,
volume 28% and mute=false. This was not a muted/playing audio stream.

The follow-up retries HTTP/extractor resolution failure once after 250 ms,
inside the existing cancellable command loop. A final failure retains the item
and requested position so even a plain Play can resolve it again. Resolution
STOP while awaiting a load becomes an error rather than EOF, without scheduling
another Lounge retry for the already exhausted resolver stage. Decoder-load
recovery remains separately bounded as described below. mpv refuses to claim
PLAYING/PAUSED for any IDLE decoder, including CANCELLED after resolver STOP.

Follow-up verification: 109 Rust tests pass (YouTube 62, bridge 16, core 31), one
explicit live resolver test ignored. Thirteen mpv tests pass in an isolated
dev20-based container, including a real silent decoder. The local hotfix is
active on .110; publication and frontend pin updates remain deferred.

## Problem and behavior

On .110 a newly resolved, nonexpired YouTube audio URL failed with HTTP 403.
Fresh resolution of the same video decoded successfully. This does not establish
why Google rejected the original URL. Previously the decoder reported ERROR,
but Play only unpaused an idle mpv and falsely reported PLAYING. Lounge also
encoded ERROR like a completed song and reported playability OK.

The pending fix adds one automatic fresh resolution after an initial decoder
load failure, retaining the current queue slot, position and requested pause.
It bypasses current/repeat media and discards speculative Next preparation;
normal successful playback and repeat keep their existing reuse behavior.
Periodic reports from the failed load cannot start additional retries. A second
failure is reported as an error, not a completed song. Play after failure starts
a fresh explicit attempt (with its own one automatic retry budget). Explicit
title reselection continues to use the normal fresh-load path.

Pause/Play/Seek during resolution update the requested state. Stop, disconnect
and new selection cancel pending work. A delayed retry for the old video cannot
cancel a newer pending selection. Failures after playback has started are not
retried automatically, but Play can request fresh media at the reported position.
Generic decoder ERROR triggers this recovery; the bridge does not identify HTTP
403 separately. Deterministic errors therefore also get at most one automatic
retry. No repeated background reconnect, URL logging or new dependency is added.

The mpv guard also prevents Pause from erasing a terminal error. It does not try
to resolve YouTube itself or silently reload the same rejected URL. Recovery
belongs to the YouTube Lounge session. Other app protocols still need their
normal explicit LOAD after a decoder error.

## Source locations and later image gate

- Maintained Rust worktree: `/home/codex/cast-repeat-frontend`, files
  `crates/vibecast-apps-youtube/src/lib.rs` and `src/lounge.rs`.
- Maintained Python/image worktree: `/home/codex/cast-repeat-product`,
  `src/cast_audio_lab/mpv_backend.py` and the mpv regression tests.
- Python changes and handoff are mirrored into
  `/home/codex/cast-audio-receiver-lab`; preserve its unrelated development work.
- A generated Rust diff snapshot is stored as
  `patches/vibecast-load-recovery-20261002.patch` in both Python worktrees. It is
  review/recovery evidence against frontend base
  `35ffe1b5ceca4962903a4f217cb18ef7d3dfb071`, not an automatically applied overlay.

The reviewed frontend is now committed and pinned at
`6f01a42c8932c798a1ba321102dec8dcbdd8d1e9`. Container, lock and CI use that exact
revision. Do not apply the snapshot again. Build/test/publish the chosen version
through `release-runbook.md`, including the dual-stack runtime change and dev21
AirPlay diagnostics.

The dev23 follow-up also directly addresses correlated LAUNCH, STOP and volume
responses to the requesting Cast sender. Chromium desktop senders otherwise
ignore the wildcard LAUNCH result and never connect to the returned YouTube MDX
transport. Other platform observers receive a separate unsolicited status.

## Validation and deployment

109 Rust tests passed (YouTube 62, bridge 16, core 31); one explicit live-network
resolver test remains ignored. Thirteen mpv tests passed in an isolated dev20-based
container with candidate Python source, including the real silent decoder test.
Ten adapter tests and one real WebSocket reconnect test also passed. Regressions
cover bounded automatic retry, stale-error suppression, error versus EOF on the
Lounge wire, explicit Play recovery, resolver failure, preserved position/pause,
Stop/new-selection cancellation, and real mpv ERROR followed by a fresh LOAD.
Tests resolve controlled fixture media; they do not establish future YouTube
availability or prove the origin of the observed 403.

Snapshot SHA-256:
`be0d6d79406c874b7decacd626107f29595f83b0e32e22d7cb7b4fbf905ff288`.
Tested Rust source SHA-256:

- `lib.rs`: `768df363af545db8a985e64039833a85e40102ba3fef55f80f98fa62e0e5f316`
- `lounge.rs`: `5c2656d13035d229ff78c7c7726892a39db9a2cc2ea93214f8c8db89e2e6de23`

Rust test copy: `/home/<receiver-user>/cast-load-recovery-20261002` on .110. It is
separate from the live receiver and uses the existing offline Rust dependency
cache. The optimized binary built with Rust 1.98 in bookworm and passed execution
inside the dev20 image. Both recovery fixes were activated in the existing .110
container at 19:01:57 UTC, preserving the dual-stack fix and route configuration.
Health reports ready and both routes run without restarts. Installed hashes match:

- `vibecast`: `f2c3e3888282879259e05af102fccc57e9386be45a5e00e78c569a3e758331b1`
- `mpv_backend.py`: `b192a6df7556be88830d3bdd8ecea5ff0d8f6c7e4f03021aced935c7638448ba`

The user confirmed audible YTM playback after deployment. Long-running repeat
stability is not yet established by that confirmation. This is a
container-local hotfix, not a new image: recreating the container from the old
image loses it. Before-image rollback files on .110 are in
`/home/<receiver-user>/cast-repeat-recovery-backup-20261002`: `vibecast.before` and
`mpv_backend.py.before`. To roll back, stop the container, copy those files back
to `/usr/local/bin/vibecast` and
`/usr/local/lib/python3.12/site-packages/cast_audio_lab/mpv_backend.py`, then start
the same container. No data/config deletion is needed.
