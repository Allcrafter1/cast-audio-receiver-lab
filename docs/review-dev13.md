# Implementation review — dev13, 2026-09-20

## Findings and changes

**Local mpv regression.** The five-argument `loadfile` array includes the
insertion-index argument added in mpv 0.38. Bookworm's older mpv rejects it.
The adapter now retries the legacy signature only on that exact argument error,
preserving start offset and autoplay/pause. Other errors are not retried. Both
failed modern and failed legacy loads release feedback gates and report IDLE /
ERROR instead of staying BUFFERING. A real silent decoder test exercises start
offset, pause, seek, EOF, reload and stop. The container build runs it against
its actual packaged mpv, not just a mock or the laptop version.

**Seek feedback race.** Python queued status callbacks captured a playback
snapshot before execution. A later seek/load/reconnect could make that snapshot
obsolete. Queued notifications now verify session and WebSocket identity, then
read current backend state at execution. Tests reproduce delayed pre-seek
feedback and replacement sockets. This is a proven stale-report path, not proof
that every observed physical AirPlay flicker had this single cause. No sleep,
extra buffering or transport reconnection was added to hide the symptom.

**UI.** DLNA and Sonos now have separate labelled fieldsets and responsive grid
layouts. Tests ensure each add button belongs to its own protocol section.
Headless Chromium renders were also visually inspected at 390 px mobile and
1200 px desktop widths: both protocol groups retain their labels and buttons.
The file-only render's API error is expected; live ingress/UI was checked separately.

**One interface.** Cast/eureka bind stays LAN-visible. The player/proxy bridge
has a separate `network.player_bind_host`, default 127.0.0.1. Browser root,
index and player.js return 404 in normal builds. Upstream browser assets remain
available with the explicit `vibecast-bridge/browser-player` Cargo feature.
WebSocket registration, session manifest and licence proxies remain unchanged.
Rust tests cover those routes. The manager stays login-free and LAN-accessible.

DLNA/Sonos already handed media URLs directly to external renderers; URLs for
loopback manifest proxies were already unsuitable. The boundary is now explicit,
not claimed fixed by exposing the internal bridge. Direct public media URLs
remain the experimental path; proxy/transcode forwarding is future work.

**Packaging/source.** No new fork commit is published. The existing immutable
dev12 commit plus `vibecast-dev13-internal-bridge.patch` reconstruct the candidate;
the overlay has a digest record and is applied by both OCI and CI. The normal
wheel and image carry the project and third-party notices. Container builds
record installed Debian versions plus FFmpeg/mpv build information.

**Documentation/licences.** The README now identifies what Vibecast supplies,
what our fork changes, and what this Python product adds. Historical prototype
commands no longer confuse the installation section; their code is retained.
Chromium BSD, unmodified airplay-cli notices/GPL and the newer libraop MIT
statement are included. AI involvement and experimental/hardware limits remain
prominent. The airplay-cli OpenSSL notice is stale: inspected prebuilt x86_64
libcrypto identifies itself as 3.5.4, while the source submodule is 1.1.1-era.
Matching corresponding source remains a concrete release-inventory task.

**Bundle distribution.** Explicit hash-pinned HTTPS acquisition is implemented
without embedded URLs or credentials and tested using synthetic JSON only.
Size/time bounds, redirect downgrade rejection, atomic private import, corrupt
download preservation and withdrawal handling are separate from Cast identity
validation. See [distribution design](bundle-distribution.md). Real signatures,
hosting identity and upload are still a separate publication step.

## airplay-cli update and regression scope

The v0.5.4 source is exactly `431c5c582eef9307c4e39c50a0ea65e970bc1128`.
The release asset and SHA256SUMS match the reviewed pins. Its two upstream
changes are HomePod OS27 standalone receiver-clock following and shared PTP
capacity 4 → 8 (layout v3). Our adapter does not start or attach a shared PTP
daemon; its stdin PCM/FIFO/status interface is unchanged. Therefore no shared
daemon migration was added. The upstream suite was built with its release
`STATIC=1` configuration and passes with local sockets allowed.

Repeat physical acceptance: persistent connection across manual/automatic
song transitions; forward/back seek without status bounce; pause/resume;
volume/mute feedback; title/duration/artwork; disconnect/reconnect and receiver
loss/recovery. HomePod/native AP2, OS27 and five-plus shared HomePods are **not
physically tested**. The prior asset/source hashes remain in the rollback record.

## Evidence so far

- Baseline after initial local fix: 203 Python tests; socket-restricted sandbox
  failures were environmental, not counted as product regressions.
- Extended suite: 214 tests on the CPython 3.13 test host, all passing, including
  real mpv 0.40 null-output IPC and FFmpeg artwork cases.
- Rust review gate: 144 tests pass; one intentionally opt-in live YouTube test
  ignored. Includes bridge, platform, default-media, YouTube, core, player API,
  SDK. Separate browser-feature and final formatting rerun tracked in plan.
- Exact downloaded cliairplay v0.5.4 passes `--check`; upstream `make test
  STATIC=1` passes. First sandbox socket failure and incorrect dynamic-build
  invocation are not reported as upstream defects.
- Wheel builds successfully and runtime inventory excludes historical receiver
  modules. Source export passes its bounded allowlist/content checks, which do
  not constitute a complete legal or secret audit of Git history.

Final total: 220 Python tests pass on the Linux CPython 3.13 host without skips;
the CPython 3.12 environment skips nine binary/environment-dependent tests.
Final Rust formatting and bridge/platform checks pass; browser-feature build
passes 17 tests. Physical v0.5.4 reference-RAOP persistence/recovery test passes.
HA dev13 builds, starts, serves ingress/LAN UI and preserves both configured
speaker identities across restart; LAN bridge access is closed. Packaged mpv's
silent integration test is part of that successful image build.

Remaining publication/hardware boundaries are in the newest WORKING-PLAN
section; do not infer stock-sender UI acceptance from a successful unit test.
