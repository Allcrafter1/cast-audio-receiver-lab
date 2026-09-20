# Architecture review / Controls-11 — 2026-09-13

## Scope

Implement volume state synchronization and persistence only. Keep the working
Audio-10 queue preparation. Other performance changes require agreement.

Version artifact: patches/vibecast-controls-11-snapshot.patch is cumulative
against the vendored Git baseline, not additive to older snapshots. Python
changes live in the main repository. On the test laptop, the running Audio-10
binary was copied to .state/controls-11-rollback/vibecast-audio10 before restart.
The old player's measured 26% level was migrated into the new persisted state.

Validation so far: core 21 tests and player API 17 tests pass; local Python
player 4 tests and backend 9 tests pass. The new pre-load volume restoration
test prevents startup Volume commands from being dropped before a Load.
All 10 Lounge tests also pass. Release build succeeded and Controls-11 was
deployed to the laptop. A live Cast GET_STATUS after restart returned level
0.26, muted false, matching the migrated backend value. Sender UI reopening,
active-session reverse feedback and the zero-to-ten-percent transition still
require the user integration test. The full YouTube suite has the separately
documented live-extractor/DASH-fixture failure; it is not wholly green.

The receiver owns persisted level/mute per stable device ID. Player reports carry
optional actual volume/mute, maintaining compatibility with older clients. Core
updates Cast receiver/media state and notifies the app; YouTube uses a watch
channel to report the latest value instead of hardcoded 100%. Feedback does not
send a fresh volume command to the backend, avoiding a command-feedback loop.
On a new app launch only, zero is promoted to 0.1 and unmuted. Nonzero levels
are preserved. A temporary file plus rename avoids partially written JSON;
this is not a guarantee against every power-loss scenario.

## Current data flow

Cast/Lounge command -> normalize selection/update queue -> local dispatch ->
resolve metadata and checked audio URL concurrently -> mpv load -> actual
playback reports -> Cast/Lounge state. Prepared next-item results bypass fresh
resolution when selection identity and age match. New queue selections do not.

Rust metadata retrieval and yt-dlp URL extraction already run concurrently.
Metadata is not the input to yt-dlp; the selected video ID is. Session identity
and selection must be known before dispatch, but outbound HTTP status ACKs no
longer gate local commands. A full four-second trace is not established by
adding unrelated single measurements; distinguish request latency, CPU time
and actual audible onset.

## Format checking

Observed audio candidates for the difficult title include Opus 249/250/251 and
AAC 140; availability and delivery protocol vary by client/title. yt-dlp -f ba
--check-formats ranks candidates and checks availability. Listing candidates
does not mean downloading each one. The direct HTTP test path uses a small
test download (10,241 bytes in the inspected version); segmented paths differ.

The slow observed check succeeded on the first candidate. Racing remaining
candidates only after a failure would not reduce that particular 4.1-second
check. Such racing can help repeated failures but costs extra requests and
potentially selects a lower-quality stream. Defer until repeated-failure traces
justify bounded concurrency and an explicit quality policy.

mpv opens the selected URL again. Sharing the probe bytes would require ownership
of a stream/proxy with ranges, seek, segmented delivery, buffering and retries.
This is substantially more maintenance than retaining upstream validation.
Keep the current 0.1–0.3-second player startup/buffer behavior.

## Resource measurements already taken (single samples, not guarantees)

- Host: i5-6300U, 2 cores/4 threads.
- Idle receiver/Python/mpv RSS about 24/27/106 MiB; sum 157 MiB.
  PSS sum about 114 MiB; CPU approximately zero over the sampled five seconds.
- Ordinary standalone extraction: 2.02 s wall, 0.83 s CPU, process-tree peak
  RSS about 64 MiB.
- Difficult extraction: 7.82 s wall, 3.14 s CPU, tree peak RSS about 362 MiB.
  This is before playback decoding/encoding and is not unavoidable audio cost.
  Helper/JavaScript runtime contribution needs per-process attribution.
- Separate 8-second mpv null-output probe: 0.51 s CPU, RSS 85 MiB. Not a complete
  live PulseAudio or future AirPlay benchmark.
- Python yt-dlp import/initialization: 0.377 s, RSS 51 MiB/PSS 41 MiB.
  This is not an implemented worker's measured incremental memory.

RSS totals double-count shared pages. CPU seconds are not seconds of blocking
or a percentage of the complete four-thread machine. Speculative extraction can
overlap playback/foreground work; these standalone peaks are not a whole-system
memory cap.

## Recommendations, not yet implemented

One persistent extractor interpreter may save startup/import time and repeated
allocation, but raises the idle memory floor and does not remove JavaScript or
network work. Use a fresh YoutubeDL object per job, bounded jobs/timeouts and
worker replacement after failure if prototyped. A two-worker prewarmed pool or
discarding every used worker shifts work to the background; it does not eliminate
CPU cost and may increase peak memory. Foreground loads must not wait behind
speculative work. Measure before selecting this design.

For small devices: bound extractor concurrency, allow disabling prefetch, review
mpv cache limits, and propagate cancellation into subprocess groups. Aborting an
async prefetch task currently need not kill its blocking extractor immediately.

Structured yt-dlp metadata can potentially replace duplicate Rust requests, but
must be tested across a representative corpus. Do not use filenames for metadata,
do not substitute uploader for artist, and allow absent album/artist fields.
ID, title, duration and artwork also need explicit fallback semantics. Actual EOF
must remain player-driven. The separate Rust response is not automatically more
stable merely because it is implemented in Rust. Defer consolidation until field
coverage, failure behavior and latency are compared.

## Broader Cast support and access conditions

Real Cast senders select app IDs. A shared device runtime can load service-specific
Web Receivers; a Default Media Receiver covers generic supported media URLs.
Our native YouTube/Lounge adapter is not that general browser runtime. Supporting
arbitrary Cast apps needs more than speaker discovery flags. A generic URL receiver
is a more bounded next compatibility target than full Web Receiver/DRM emulation.

YouTube control and audio retrieval are separate here. The extractor invocation
does not receive the user's Premium login. Therefore do not claim that retrieval
uses authenticated Premium entitlements, or that Google sees no Cast-like activity.
YouTube terms restrict automated access and uses outside authorized mechanisms;
Premium does not generally authorize every client implementation. Contract terms
and statutory copyright/technical protection rules are distinct. No categorical
legal conclusion follows merely from using yt-dlp or encountering a 403.

References:
- https://developers.google.com/cast/docs/web_receiver/basic
- https://github.com/yt-dlp/yt-dlp#output-template
- https://www.youtube.com/static?gl=DE&hl=de&template=terms
- https://www.gesetze-im-internet.de/urhg/__95a.html
