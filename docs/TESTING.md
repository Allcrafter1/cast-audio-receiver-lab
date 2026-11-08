# Reproducible test matrix

## Current release candidate: 0.8.0-dev1 — 2026-11-08

`0.8.0.dev1` integrates the complete dev3 candidate below. It restarts
natural-EOF Replay through the existing repeat worker and names video aliases
`<output name> (YT)`. Audio names, UUIDs, shared playback and ownership remain
unchanged. [Replay details and disconnect evidence](youtube-repeat.md).

- Both added regressions fail against the previous implementation and pass with
  the fix: EOF Play versus pause/stop/loading, and replay before queue enrichment.
- **306 Rust library tests pass** (YouTube 159, core 124, platform 21, receiver 2),
  with three existing opt-in tests ignored. Cross-endpoint takeover also checks
  that each app receives the selected endpoint name and shared storage.
- **431 Python tests pass**, three skipped, from 434 discovered, with real FFmpeg
  relay/artwork coverage. Full Rust formatting and the optimized Linux build pass.
- The cumulative source patch reconstructs all 139 inventoried source inputs;
  the source lock, Containerfile and CI point to the same dev3 snapshot.
- This candidate has **not** been retested through the Android Replay button:
  ADB reports no attached device. Previous dev2 app acceptance below remains
  historical evidence, not a claim of dev3 phone validation.

Installation and read-only LAN checks on Audio Lab Laptop pass: both enabled
outputs are ready, route definitions and IDs are preserved, and all 28 installed
Python files plus the actually loaded executable match the candidate hashes.
Cast DEVICE_INFO reports `Audio Lab Laptop` / `Audio Lab Laptop (YT)` and
`Audio Lab AirPlay` / `Audio Lab AirPlay (YT)`. Base/YouTube/Music PTR separation
and complementary app availability remain correct for all four endpoints.
Both Laptop endpoints report the same idle session and volume state. The prior
dev2 container is retained as `cast-audio-receiver-before-youtube-replay-20261108-1`.
This is a local candidate deployment, not a public or Home Assistant update.

Executable SHA-256:
`cc0362f164a6839b2d4643ddd06e3f541422a44ca75236bbe2c548ea69eef5ae`.

## Previous candidate: shared dual identities — 2026-11-08

`0.7.0.dev2` was the preceding product candidate on Audio Lab Laptop. Each enabled output
has the existing speaker plus a stable YouTube-only video alias, sharing one
runtime. See [architecture and costs](dual-cast-identities.md). The accepted
Music/web controls, volume policy, Sonos/relay/metadata work and TuneIn are
included; this is not the isolated silent research receiver.

The final Linux executable SHA-256 is
`50461bdbe12537c92d9bd486e18618f28a6a111f6bf57a90f9dd7797f0510ebe`.
Deployment verifies the binary and all **28 Python runtime files**, retains all
three output definitions (two enabled) and keeps a rollback container. Runtime
readiness is **2/2 outputs**, including mpv and AirPlay. No Home Assistant
installation, public release, registry image or PR merge is changed.

Automated evidence:

- **358 Rust library tests pass**, three pre-existing opt-in probes ignored:
  core 124, SDK 12, YouTube 157, TuneIn 15, Cast transport 13, discovery with
  mDNS 14, platform 21 and receiver 2. The SDK doctest also passes.
- The separately tested vendored mDNS library passes **37 tests**. Coverage
  includes subtype-only announcements/goodbyes and normal base/subtype behavior.
- The final Python run discovers **434 tests**, passes **431**, and skips three:
  two local mpv tests (no host mpv installed) and the opt-in native DACP probe.
  FFmpeg/ffprobe were supplied from the temporary test-tool directory, so actual
  Opus/WebM-to-MP3 relay and artwork conversions ran rather than being skipped.
- Full Rust formatting, FFI/primitives compilation, source-export and packaging
  checks pass. The wheel completeness check finds 46 files and no historical
  receiver modules. Existing YouTube resolver warnings remain; this is not a
  warning-free build claim.
- A separate archive plus the single cumulative patch reconstructs all **139
  inventoried source inputs**. Source lock, Containerfile and CI use the same
  snapshot. Registry vendoring preserves the local patched mDNS dependency.

On-wire checks for **both mpv and AirPlay** confirm the speaker appears in base
and Music PTR replies, while the video alias appears only in YouTube PTR replies.
Both Cast DEVICE_INFO replies use the compact UUID spelling of their mDNS TXT
record, with capability masks `199428` and `199429` respectively. Availability
maps are complementary, including a Default Media Receiver control check.

An actual shared-cache test exposes a limitation: a fresh general Zeroconf
browser initially sees only the speakers; after a YouTube subtype browser fills
the shared cache, it also reports the video aliases. Additional Home Assistant
entities are therefore possible, even without base PTRs for those aliases. This
test does not modify or audit the user's HA entity registry. Both aliases still
report and control the same player state.

Authorized Android product testing uses ordinary YouTube and YouTube Music
separately on the connected phone. On the final build, YouTube shows one
selectable TV entry for Audio Lab Laptop and starts app `233637DE`; mpv decodes
AAC at 44.1 kHz with advancing time. Music shows one speaker entry and replaces
it with app `2DB7CC49`; the same single output decodes Opus at 48 kHz. Both
endpoints report exactly the same active session and volume (25%, unmuted in
the recorded final run). Music → YouTube then replaces the session again and
returns to advancing AAC playback. After the UUID correction the three selections
each show one target row (TV → speaker → TV); the native route IDs and receiver
app IDs agree. These are real decoder/output-state observations;
human confirmation of the physical sound remains a separate acceptance step.

The first product iteration exposed dashed/compact copies of the same UUID in
Android's route list. DEVICE_INFO now matches the compact mDNS spelling for all
UUID-based endpoints. Persistent UUIDs and app storage were not renamed and no
app data was cleared. A YouTube accessibility dump timed out during animation;
direct screenshots, route records and decoder samples were used separately,
rather than treating that capture failure as a playback failure.

Private manifests, logs and observations are retained under
`.state/dual-identity-20261108-2/`; the preceding iteration is `...-1/`.
The last stable single-identity container remains available as
`cast-audio-receiver-before-dual-identity-20261108-1`; the immediately preceding
dual iteration is `cast-audio-receiver-before-dual-identity-20261108-2`.

Remaining release gates: wider client/reconnect testing, direct Sonos hardware
acceptance, the latest stock TuneIn autostart retest, and public amd64/arm64 OCI
build/promotion. The owner-requested existing browser behavior is preserved;
no additional web-cache redesign or automatic browser userscript is deployed.

## Historical single-identity baseline

The following entries record earlier candidates and their limitations. They do
not describe the current deployment or supersede the dual-identity results above.

For ordinary YouTube discovery/reconnect, historical speaker classification and
the separate installed laptop/HA versions, see
[the PR #18 investigation](youtube-discovery-pr18.md). The local defaults,
availability, MDX-startup and bounded owner-continuity regressions pass. The
follow-up also verifies per-receiver app storage, the discovery request/ack
exchange and bounded cloud-channel termination. The ordinary-YouTube
controls/audio follow-up passes 338 library tests, the SDK doctest and 14 silent
release-binary checks. Its accepted playback behavior is retained in the active
`0.7.0.dev1+local.20261108.mdnsapps` candidate described below. The loaded
executable, all 28 Python files and audio-only profiles are verified. New
regressions cover title selection, original/manual audio, preserved pause and
position, URL refresh, failed/superseded changes and retained Music behavior.
The owner accepts the current ordinary-YouTube web behavior and requests no
further web reconnect changes for now. Ordinary Android casting through the
installed single speaker identity remains unresolved. A separate silent lab has
since verified app-specific routing with two identities; this is not installed,
audibly verified or a replacement for the default speaker. Home Assistant is
unchanged on its separately audited dev20 install.

The owner confirms Music playback still works, including the latest Android
retest. During an earlier USB comparison neither mobile app listed the speakers;
the new subtype candidate restores listing in both. Keep Music playback as the
regression baseline; the historical Music Web findings below are distinct from
the current ordinary-YouTube discovery/handoff problem.

## Application-subtype mDNS candidate — 2026-11-08

Private candidate `0.7.0.dev1+local.20261108.mdnsapps` adds subtype PTRs derived
from the shared application registry to the same receiver identity. A LAN
capture during the Android retest includes `_233637DE` and `_2DB7CC49` subtype
queries that the preceding base-only advertisement cannot answer. This is a
concrete discovery gap; it does not by itself establish the cause of every
reported listing or launch failure. No display capability or playback,
Music, reconnect or ownership behavior is changed.

The regression run passes **341 library tests**: Core 122, SDK 12, YouTube 157,
TuneIn 15, platform 21, discovery with mDNS 13 and receiver 1. Three existing
opt-in probes remain ignored; the SDK doctest also passes. The patched
`mdns-sd` dependency separately passes **36 library tests**. New coverage checks
registered-app ID normalization/deduplication, one stable base instance, direct subtype
answers, per-PTR known-answer suppression, all announcement/goodbye PTRs and
their coexistence in the DNS cache. Existing Music/playback tests remain in the
same regression gate.

Repeat the frontend gate from the reconstructed checkout with the existing
dependency cache:

```sh
cargo test --offline --locked -p vibecast-core -p vibecast-sdk \
  -p vibecast-apps-youtube -p vibecast-apps-tunein -p vibecast-platform \
  -p vibecast-discovery -p vibecast-receiver --features vibecast-discovery/mdns
```

The dependency's complete library suite needs local UDP sockets and usable
network interfaces; restricted-sandbox socket failures do not establish a
protocol regression. Retained suite logs and source manifests are under
`.state/mdns-app-discovery-20261108-1/`. Independent eight-patch reconstruction
matches all **136 inputs**, including the **22 vendored files** and licence
texts; see [source reconstruction](source-reconstruction.md).

The release build and **14 silent checks of this candidate binary** pass, and
the candidate is installed and active on the test laptop. Readback verifies
`/proc/PID/exe` SHA-256
`02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b`,
all **28 Python files**, **2/2 ready routes**, `ca=199428` and
`display_supported=false`. The highest referenced glibc symbol version is
`GLIBC_2.34`. The shipping CLI build enables the receiver's mDNS feature as
well as the discovery feature used by the regression command above.

LAN PTR lookups returned **2 base / 0 YouTube / 0 Music** receiver instances
before activation and **2 / 2 / 2** afterwards, all referring to the same two
speaker identities. These are DNS discovery results, not an app-playback test
or a claim that Music had stopped working. The previous container remains
available as `cast-audio-receiver-before-mdns-app-discovery-20261108-1`.
The phone retest confirms both apps list the speakers and **Music connects and
plays audio**. Ordinary YouTube selection still produces no visible connection
or audio; its entries temporarily disappear and later return. The receiver
captures Music's `2DB7CC49` launch and no ordinary `233637DE` launch. Phone-peer
correlation identifies only Music Cast connections in that interval. Reliable
ordinary-YouTube listing, launch, audio and reconnect acceptance is **not met**;
the app selection path remains under investigation. Native Android receiver
registration via `NsdManager` is a separate discovery implementation and is not
covered by the desktop mDNS claim.

## Known YouTube Music Web limitations — do not patch the receiver

Investigated on 2026-11-07 against YTM Web build
`yt_music_web.en_US.I6PQRHpqgd8.es5.O` and player `a5c2aafe`.
These are upstream web-client defects, not established receiver regressions.
There is no receiver-side fix for the browser's internal connection object or
its local UI state. Do not reopen receiver workaround work for the same symptoms
without new evidence that commands or valid status are lost in our code.

| Symptom | Established evidence / explanation | Workaround |
| --- | --- | --- |
| Play/Pause stops working after returning to the tab, while status and HA still work | YTM calls a disconnected Chrome `PresentationConnection`. `send()` throws synchronously; YTM's error-callback-based Lounge fallback is bypassed. Receiver TCP remained open and Lounge updates continued. | Reload the page; reconnect if necessary. User confirmed restored control. |
| After reload, Chrome's Cast UI knows the playing song but the YTM page does not show it | Remote context contains the correct video, PLAYING state, position and duration; the local player has no video. YTM's remote-title handler requires an existing local/preloaded watch endpoint before updating the UI. Repeating `getNowPlaying` did not repair it. | Selecting a title initializes the UI, but also changes/restarts playback; it is not a transparent resynchronization action. |

The original cause of the Chrome page connection becoming disconnected is
**unknown**; do not describe it as a proven receiver-triggered disconnect or a
proven browser background-tab timeout. The confirmed web defect is continuing
to use that disconnected object without handling its synchronous exception.

`index: null` alone is also not proof of faulty receiver feedback: isolated
Google Lounge tests removed a correctly sent `currentIndex` before delivery.
The UI guard above does not use that index. Do not add field-name guesses,
status-push timers, forced disconnects, ownership changes or browser injection
to work around these findings. Preserve functional mobile and HA behavior.
Detailed incident evidence is in the desktop-web section of `WORKING-PLAN.md`.

## dev13 review regression commands

Run `PYTHONPATH=src:. python -m unittest discover -s tests -v`. The real mpv
test uses a generated silent WAV and `--ao=null`: no physical sound device is
required. It checks paused offset load, seek, EOF, replacement and stop, and is
also run inside the OCI build against the packaged mpv. Unit tests separately
exercise the legacy/modern argument signatures and failed-load gate cleanup.

Reconstruct the dev12 frontend plus the digest-pinned dev13 overlay, then run
the seven-crate CI gate and `cargo fmt --all -- --check`. Also run
`cargo test --locked -p vibecast-bridge --features browser-player --lib` to
keep the explicit upstream development example functional. The default build
must return 404 for `/`, `/index.html`, `/player.js` on its internal bridge.

For an explicitly selected physical test receiver, the existing
`tools/test_persistent_airplay.py --config PRIVATE_TARGET --cliairplay VERIFIED_BINARY`
emits quiet synthetic tones. It checks one connection across load/seek/EOF and
recovery after killing only its own CLI. Never select another household device
automatically just because the intended target is unavailable.

Manual follow-up on the HA output: several forward/back YT Music seeks (watch
for old-position flashes), paused seek, queue/direct song selection, next track,
volume feedback, artwork, disconnect and reconnect. Keep HomePod/Yamaha and
multiple-target acceptance distinct from the reference-phone result.

Bundle tests use synthetic JSON only. Do not attach real credentials to tests,
screenshots, logs or public issues. Tests prove artifact integrity/import behavior,
not future acceptance of a device identity by Google.

Dev11 adds `tools/test_default_media.py --artwork-check` to the existing silent
fixture. It verifies actual square conversion, HTTP image retrieval and Cast
metadata feedback without changing playback position/state. See
[artwork verification](artwork-dev11.md) for dependencies and acceptance steps.

Use a versioned candidate and private test state. Record the adapter version,
frontend digest, dependency inventory, backend and test date. Never conflate
implemented, deterministic-tested, deployed and user-confirmed.

## Automatic checks without a listener

| Layer | Repeatable check | What it establishes / does not establish |
| --- | --- | --- |
| Python unit/integration | `python -m unittest discover -s tests` in the intended environment | Control/state mapping, cancellation, process ownership, routes/API, artifact tools. FFmpeg crop tests skip explicitly when unavailable. |
| Installed package | Install the built wheel `--no-deps` into a fresh hash-locked environment; `pip check`; run tests without `PYTHONPATH=src` | Tests the installed code and packaged UI assets rather than accidentally importing the development tree. |
| Rust source | Fresh upstream checkout + single version's complete patch; `source_inventory.py` comparison | Exact inventoried source equality; not a hermetic build or binary reproducibility proof. |
| Rust protocol/core | Seven-crate deterministic gate in source-reconstruction.md | Parsing, app sessions, media/volume/status, teardown, resolver cancellation and fixture behavior. Explicit live YouTube probe remains separate. |
| Real local decoder | `test_default_media.py --silent-fixture` with candidate binary and existing private bundle | Actual Cast framing, direct URL LOAD, mpv playback clock, controls, metadata, EOF/errors/recovery and cleanup without audible PCM. Skips Google sender device-auth validation. |
| Management browser | Headless direct-LAN entry, list/reload, favicon, no JS errors | Real UI rendering with existing routes. Do not delete/rename live user routes as a convenience; mutating cases use private isolated API fixtures. |
| Artwork conversion | Synthetic landscape/portrait/square/large images through real FFmpeg | Shared lossless-intermediate conversion, centered square crop, size cap, no artificial padding. Not remote-device rendering or automatic detection of every embedded border. |
| Resources | `resource_profile.py --pid FRONTEND --pid MANAGER` | Sampled tree RSS/PSS/interval CPU. Short-lived helpers and unsampled peaks can be missed. No playback is initiated by the tool. |

Fresh package test procedure and limitations are in dependency-locks.md and
current-runbook.md. Keep external media URLs, user accounts and devices out of
deterministic unit fixtures. Use loopback servers and synthetic media.
The post-dev5 core regression uses two separate Cast connections: owner loss
must notify the observer with terminal media/application status and allow a new
launch. It passes without further runtime changes; include the documented
test-only supplement when reproducing that test.
The post-dev5 audio-category supplement adds an AUDIO assertion to the DMR tool.
An unmodified dev5 binary deliberately fails this new regression. The candidate
passes 17 checks, including a finite WAV labelled LIVE: playback/pause and the
no-seek capability policy work. This is not a continuous-radio, HTTP reconnect,
ICY metadata or real SWR3 acceptance test.
Use `--fixture-format mp3` or `--fixture-format flac` with `--silent-fixture`
to encode the same bounded synthetic PCM using existing FFmpeg and exercise
the complete decoder/control test with those formats. WAV remains the default.
The helper never fetches media and is test-only, not a new runtime transcoder.
It also withholds HTTP response headers for a controlled stalled source, then
tests replacement by a valid LOAD and receiver STOP/relaunch. This is separate
from mid-stream connection loss and long-running radio acceptance.

## Opt-in device / sender acceptance

The research-only [YouTube capability lab](youtube-capability-lab.md) supplies
25 profiles and [portable commands](../tools/youtube_capability_lab/README.md),
including all 16 combinations of mDNS/DEVICE_INFO video output and the two
display flags. The first three layers are queried on the isolated receiver;
the outgoing API header has configuration/source evidence, not a TLS capture.
All 50 Android app/profile observations and four paired runs (16 observations)
completed without automation errors. They record listing, icon, selection, app
LAUNCH and silent LOAD separately. Fresh-UUID observations in the two apps cannot
establish the presentation of one shared device; paired comparisons are a
separate gate. Neither silent LOAD nor a rendered icon verifies decoding,
audible playback or disconnect/reconnect. Two silent-player helper tests pass.
Preserve the working Music/web receiver and keep unsupported group/no-output
identities experimental.

See the [full matrix](youtube-capability-results-20261108.md) and
[same-device sequences](youtube-capability-paired-20261108.md). Visual/XML review
corrects a connected Music controller missed by the old row parser; raw results
remain retained. No stable requested **single-identity** presentation was
established. A later dual-identity lab used separate UUIDs/ports, app subtypes
and inverse Availability responses: both app orders showed only the intended
route and produced the matching LAUNCH plus silent LOAD. Rapid UUID replacement
temporarily retained an old route and dimmed the new one; keeping the identity
stable until discovery converged restored selection. Audible playback, shared
backend/volume ownership and a product option remain unverified/unimplemented.
The final installation audit verified the original loaded binary, all 28 runtime
files, two ready outputs, removed lab and restored phone USB stay-awake setting.

Do not require the owner to test each tiny intermediate change. Accumulate a
bounded checklist against one known candidate; record failures and keep the
previous release. Unattended work continues with independent automatic tasks.

| Scenario | Observe on sender and actual output | Current evidence |
| --- | --- | --- |
| YT Music normal queue | Play/pause, seek, manual/automatic Next, initial load, queue replacement | Earlier user-confirmed working baseline; retest after candidate release. |
| YT Music disconnect while HA observes | Audio stops, final idle/application status, reconnect and second sender | Prior user-confirmed disconnect; latest terminal/HA observer changes automatically tested, HA acceptance pending. |
| Receiver-origin controls | Change output/HA volume and play/pause; inspect YT UI and sound | Automated backend-to-Cast volume coverage; actual YT UI and all remote command paths remain a separate gate. |
| SWR3 / local HA file | Sender-supplied title/images/metadata type, pause support, unknown/live duration | User reports missing fields/controls; do not infer what was supplied without LOAD evidence. Synthetic music-metadata loss is independently reproduced. |
| Default media from another Android sender | Correct app ID, HTTP(S) media, controls/errors | Candidates are not blanket app compatibility promises. Custom service receivers and DRM remain out of scope. |
| AirPlay Redmi RAOP | Metadata, duration/seek feedback, persistent connection, queue/EOF, reconnect | Earlier user-confirmed baseline plus isolated device tests. New square artwork/music fields need rendering acceptance. |
| Yamaha / other RAOP / HomePod | Discovery, pairing, protocol/capabilities, real sound and controls | Not established by Redmi tests. No automatic testing against arbitrary discovered household devices. |
| Two concurrent real outputs | Independent controls, errors, teardown and bounded resources | Automatic child-process isolation passes; simultaneous acoustic output acceptance remains open. |

Extremely rapid title selection also showed incorrect final ordering on Nest
Audio. Preserve that comparison as a sender limitation; do not add guessing
heuristics merely to force a particular final title in synthetic tests.

## Failure recording

Record scenario, precise time/timezone, expected versus actual behavior and
versions. Identify the boundary first: discovery/authentication, app launch,
source resolution, decoder, output connection or feedback. Retain private logs
locally; redact signed URLs, tokens, credentials and personal playback history
before sharing. A UI screenshot alone is not a playback-state trace.

For noisy/slow network media, compare a known-good item and the previous release.
Do not remove format validation or reduce buffering simply to make a timing test
look better. Public release, licensing review and future Google acceptance are
not established by a green test suite.

## PR #16 / #17 integration regression

Run `PYTHONPATH=src:. python -m pytest tests/test_volume_policy.py tests/test_sonos.py
tests/test_dlna.py tests/test_dlna_media.py tests/test_vibecast_player.py
tests/test_mpv_backend.py` as one command, plus the existing AirPlay/DACP suite.
Install the project’s Sonos/DLNA test extras; real conversion requires FFmpeg and
ffprobe. The suite uses local HTTP/IPC sockets and must be allowed to bind them.
`test_real_opus_webm_becomes_sonos_mp3_with_correct_format` checks an actual
Opus source, relay response, MP3 codec, stereo, 44.1 kHz and duration.

The matching frontend needs `cargo test -p vibecast-player-api -p vibecast-core
--lib --offline` (one command). Startup commands must carry `initialize: true`,
ordinary volume commands `false`, and corrected output reports must preserve
volume revisions. See [network outputs](network-outputs.md) for the separate
hardware acceptance checklist and the contributor’s exact evidence.

The final PR remainder audit ran the Sonos, DLNA, media-relay, volume-policy and
Vibecast-player suites with temporary FFmpeg/ffprobe 7.0.2 on PATH: **71 passed,
zero skipped, 14 subtests**. This supersedes the earlier unverified claim about
local real conversion: without those binaries, the conversion cases had skipped.
Additional cases cover SoCo DIDL errors, direct radio without a relay, and
shared cleanup failure/retry, including the next HTTP-listener start.
