# Reproducible test matrix

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
