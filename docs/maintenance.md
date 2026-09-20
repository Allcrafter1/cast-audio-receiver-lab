# Maintenance and incident recovery

This is an operational workflow for the experimental receiver, not an existing
automatic updater. The current product path is Vibecast → Python external-player
adapter → mpv or FFmpeg PCM / Music Assistant airplay-cli. Older Python/Node
receiver experiments are not the production Cast frontend. The latest decisions
in [WORKING-PLAN.md](WORKING-PLAN.md) override historical experiment instructions.

## Reproducibility inventory (release audit: 2026-09-20)

Update after dev6 verification: a complete current Rust patch now exists;
fresh-checkout source reconstruction matches the build host. See
[source reconstruction](source-reconstruction.md) for exact scope and remaining
environment/bit-reproducibility gaps. Historical partial patches below must not
be applied as a series.

| Component | Existing version record | Remaining gap |
| --- | --- | --- |
| Our adapter | `pyproject.toml`, package version, `CHANGELOG.md`, dev18 release | Keep release tag, image digest and HA version aligned. |
| Vibecast | Maintained commit `e67628fa72550095f92197550d60d8e94c503d4e`, Cargo.lock, vendored-source release archive | Frozen archive rebuild passes; full OS/toolchain bit reproducibility is not claimed. |
| yt-dlp extraction stack | `config/youtube-extractor-requirements.txt`: yt-dlp 2026.8.19, yt-dlp-ejs 0.8.0, deno 2.9.6; complete container resolution in `config/container-linux-x86_64-cp312.lock.txt` | amd64 CPython 3.12 is hash-locked and offline-verified; ARM remains separate. |
| AirPlay sender | `config/cliairplay-linux-x86_64.lock.json`: unified Music Assistant airplay-cli v0.5.4, source/asset/checksum pins | Linux x86_64/reference-RAOP verified; HomePod/Yamaha and other architectures remain separate. |
| Python libraries | Tested constraints and separate 17-wheel CPython3.12/3.13 Linux x86_64 hash locks | Fresh offline install/pip-check/tests verified for both; ARM and extractor/build dependencies remain separate. See dependency-locks.md. |
| FFmpeg / mpv | Host-installed executables | Host versions/build options must be recorded; no application-controlled pin yet. |
| Device authentication | Separately released, hash-pinned, replaceable bundle and validation tools | Coverage, installed file and sender acceptance are separate facts; revocation can happen before expiry. |

Do not run all files in `patches/` as a patch series. For example, Controls-17 is
a cumulative two-file snapshot, not a complete replacement for earlier changes
in other files. Use the single complete patch for the intended version from the
reconstruction guide; dev6 needs no additional supplements. A documented base commit alone does not reproduce
the running binary. Every release needs a fresh build/source/licence review and
must preserve applicable copyright and attribution files.

## When something stops working

`tools/support_inventory.py` supplies a read-only JSON version/hash inventory:

```bash
PYTHONPATH=src .venv/bin/python tools/support_inventory.py \
  --frontend /path/to/deployed/vibecast --airplay /path/to/deployed/cliairplay
```

Use the runtime's actual virtual environment and source path. It does not gather
logs, URLs, account data, environment variables or authentication material.
Binary hashes identify builds; a missing installed-package version is distinct
from the imported adapter version in source-based development deployments.
An explicitly supplied binary that is absent or unreadable now produces a
fixed-label per-component error, while the rest of the report remains available.
This matters when diagnosing a partially installed update. An error is not a
successful hash verification; private filesystem paths are not printed.

First preserve evidence; do not update everything or repeatedly restart all
components. Record:

- App version, actual frontend binary hash, adapter source/release identity,
  OS/architecture and dependency versions from the **running environment**.
- Sender app/OS and receiver model/firmware, selected output mode, reproduction
  time including timezone, expected result and observed result.
- Whether a known-good title works, whether the failure occurs on mpv as well as
  AirPlay, and whether another sender/reference receiver reproduces it.
- Stage reached: discovery → authentication → application launch → selected
  media → source resolved → decoder started → AirPlay connected/started → audio.

Safe local inventory commands (run at the repository root; substitute the actual
runtime virtual environment when it is not `.venv-re`):

```bash
git rev-parse HEAD
git status --short
.venv-re/bin/python --version
.venv-re/bin/python -m pip show cryptography pyOpenSSL websockets zeroconf yt-dlp yt-dlp-ejs deno
ffmpeg -version
mpv --version
git -C third_party/vibecast rev-parse HEAD
git -C third_party/vibecast status --short
```

An outer Git commit is insufficient if sources are dirty or deployed from a
staging directory. Record hashes of the exact executable and relevant deployed
source files privately. Avoid attaching an unrestricted environment dump,
process command line, `pip freeze` from private-index installations, or raw
source diff: those can disclose credentials or private URLs.

The running manager also exposes `/health`, `/status` and `/api/support`.
`/health` is a minimal readiness signal. `/status` includes version, uptime and
named route state for the trusted local administrator. `/api/support` is the
public-issue starting point: it reports version/runtime plus numbered, name-free
route summaries and deliberately omits targets, addresses, media, certificates
and configuration. Its allowlist/redaction behavior is regression tested and was
verified against the real Home Assistant App; it is useful context, not a full
automatic diagnosis.

Use short, time-bounded log excerpts. Preserve selection/session correlation and
fixed-label failure categories, but remove signed media URLs, headers, cookies,
tokens, pairing secrets and authentication bundles. Media titles/history and
local addresses may also be private. Existing logging is not a guarantee that
every upstream diagnostic is safe to publish. A downloadable archive combining
this safe inventory with reviewed/redacted log categories remains future work;
do not attach raw container logs by default.

## Find the failing boundary before changing dependencies

| Observation | First checks / isolated experiment |
| --- | --- |
| Speaker absent | Listener/process alive; correct interface and mDNS; Wi-Fi isolation/VLAN; stable route identity. |
| Immediate connection rejection | Correct host time; active bundle coverage and readable configuration; compare sender acceptance. Updating yt-dlp cannot repair Cast authentication. |
| Connected, title never resolves | Selection actually received; metadata vs extractor stage timings; extractor exit category; reproduce the same public title with the pinned stack privately. |
| Source resolved, no PCM | FFmpeg diagnostic category, decoder exit and decoded sample count; distinguish expired/denied source from codec failure. |
| Local output works, AirPlay fails | Exact advertised target/protocol/capabilities, CLI version, connection/FLUSH/START acknowledgements, owned child lifecycle. |
| Audio works, wrong state/queue | Ordered command and state trace, session/track generation, expected decoded duration versus actual playout; do not assume a downloader update will help. |
| Only extremely fast selections fail | Compare reference speaker before introducing ordering heuristics; the same sender behavior was observed on Nest Audio. |

Do not use a real sender account's signed URL as a permanent regression fixture.
Keep synthetic fixtures for protocol and lifecycle behavior; use opt-in live
tests for service compatibility. Passing local authentication validation alone
does not demonstrate that Google sender software accepts the receiver.

## Small, reversible update procedure

1. Preserve the last working **complete** release, actual launch configuration
   and private state with restrictive permissions. Record source and executable
   hashes, dependency versions and test results. Never publish private state.
2. Choose one boundary to change. For an extractor regression, test a candidate
   yt-dlp stack in a separate virtual environment. For an AirPlay regression,
   test a separate upstream binary and verify its published digest. Do not
   perform an in-place global `pip install -U`, blanket `cargo update`, or change
   authentication data alongside unrelated playback fixes.
3. Review upstream release notes/source changes against the failing interface:
   extractor flags/output, CLI commands/status semantics, or Vibecast/player
   protocol. Confirm license and transitive changes. Upstream latest is a
   candidate, not automatically a compatible release.
4. Reproduce the failure on the baseline, then verify the candidate on the same
   input where possible. Retain format validation and cancellation protections.
5. Run the regression gates below, then stage only the affected service. Record
   implemented / automated-tested / deployed / user-confirmed separately.
6. After acceptance, update pins, changelog, build provenance and Working Plan.
   Keep rollback until a representative queue and reconnect test has passed.

Process-stop waiters must treat missing `/proc/PID` and `ProcessLookupError` as
normal successful exit, not a failed deployment. An existence check followed by
a read can race process termination. Save rollback before stopping anything and
cover the entire stop/start sequence with recovery, not only candidate startup.
The private dev6 one-shot activation needed a bounded recovery for precisely
this race; it is not a reusable installer. Never rerun migration scripts blindly.

### Regression gates

The existing local Python suite does not require a live receiver:

```bash
PYTHONPATH=src .venv-re/bin/python -m unittest discover -s tests
```

On a prepared Rust build host, with the complete intended source tree and its
lockfile, use locked builds rather than silently selecting new dependencies:

```bash
cd third_party/vibecast
cargo test --locked -p vibecast-apps-default-media -p vibecast-apps-youtube -p vibecast-core -p vibecast-player-api -p vibecast-discovery -p vibecast-messages -p vibecast-platform --lib
cargo build --locked -p vibecast-cli --release
```

These commands are the proposed repeatable gate, not a claim that a clean
reconstruction or every platform has passed today. Explicit live/ignored tests
must be listed separately, never silently counted as service compatibility.
Run from the source directory so rustup selects its toolchain, and explicitly
pin the recorded compiler for a reproduction. An offline prepared cache was used
for the dev4 gate. `tools/test_default_media.py --silent-fixture` additionally
allows real-decoder testing without a tone; it does not prove audible quality.

With an explicitly selected test target, `tools/test_persistent_airplay.py`
checks pause, paused seek, warm title changes, natural completion and recovery
after terminating its own helper. It emits quiet audio and must not run against
an arbitrary discovered household device. It does not measure acoustic quality
or prove HomePod compatibility from a successful legacy RAOP receiver test.

Manual acceptance: new title, prepared/manual and automatic Next, seek including
paused seek, volume/buttons/feedback, artwork/duration, disconnect/reconnect,
second sender, failed load followed by valid load. Confirm no leaked children or
unbounded memory. Add multiple simultaneous routes before claiming multi-speaker
readiness. Keep latency observations distinct from precise audible measurements.

### Rollback

Stop only the affected service using its validated identity; restore its known
working binary/environment and launch configuration. Leave unrelated receivers
and collection jobs alone. Reconnect and play a known-good title. A package-only
rollback cannot reverse an upstream protocol change or revocation.

For persistent AirPlay-specific regressions, the existing
`--airplay-reconnect-on-load` switch provides a narrow fallback to per-track
connections. This is not a substitute for preserving the previous release.
Future state schema migrations need explicit backward compatibility or a backup
restoration procedure before shipping. Never change the Linux system clock to
test future validity; use synthetic boundary tests instead.

## Existing release automation and follow-up

- CI runs Python 3.11–3.13, clean source-export/history/wheel checks, Rust tests
  and an amd64 container build. Manual workflows retain OCI SBOM/provenance and
  frozen Rust/native source archives.
- Dependabot reports container and GitHub Actions changes, while
  `upstream-watch.yml` follows the pinned Vibecast and airplay-cli releases.
  Python runtime updates use the curated procedure above because requirements,
  selected wheels and source inventories must change together; a generic
  requirements-only PR is incomplete by construction. Production is never
  upgraded unattended. Service-side changes may occur without a release, so
  notifications are evidence to investigate, not availability monitoring.
- `/health`, `/status` and `/api/support` provide bounded diagnostics without
  credential payloads. More failure categories may be added when incidents show
  that the current allowlisted output is insufficient.
- The versioned OCI/Home Assistant App preserves `/data` and exposes a configurable
  LAN UI port. Published-image update/rollback, state migrations and additional
  architectures remain explicit acceptance work.

The desired “send version + redacted logs, isolate the changed boundary, test an
update” workflow is realistic. Most extractor or CLI compatibility changes can
be investigated independently. It is not an availability guarantee: a Cast
trust-policy change or unavailable service API may require substantial work or
have no sustainable fix. The project does not claim bit-for-bit reproducibility
or universal one-click recovery from external protocol changes.
