# Current development runbook

Current packaged development release: **0.6.0.dev12**. It adds one supervisor,
the static output registry, output-control protocol v2, operational endpoints,
container/HA packaging and the maintained Vibecast fork on top of the accepted
dev11 artwork path. The old laptop deployment and build directories remain
historical evidence; do not treat them as the source of the packaged release.

This is a Linux development installation, not a finished distribution or HA
App/add-on. Keep the prior working release and private state available. Do not
mix old standalone Python receiver commands with the current Vibecast frontend.

## Components and boundaries

1. **Vibecast frontend:** per-player Cast discovery/listeners, authentication,
   device volume, application sessions and normalized player commands.
   YouTube uses its service-specific control/metadata path and checked yt-dlp
   source extraction. The Default Media Receiver takes a direct HTTP(S) URL
   without invoking yt-dlp. It is not a browser executing arbitrary Web Receivers.
2. **Runtime supervisor:** starts the Rust frontend, waits for its player bridge,
   then starts the speaker manager. It owns bounded manager-first shutdown.
3. **Speaker manager:** local HTTP UI, durable route IDs/names/configuration,
   one independently supervised Python adapter per enabled route.
4. **Adapter:** normalized playback/status boundary. mpv performs local playback;
   AirPlay uses FFmpeg's 44.1kHz stereo 16-bit PCM and pinned airplay-cli.
   AirPlay transport persists across track changes, with bounded FLUSH/drain and
   reconnect fallback. STOP still closes playback.

Artwork is a shared, optional adapter task (`cast_audio_lab.artwork`). It reads
the sender URL or a local file, produces one bounded 1:1 JPEG through a
lossless intermediate, and never blocks audio startup. The current AirPlay
adapter consumes that file. Cast/Home Assistant receive the processed image
URL asynchronously when `--artwork-public-url` is set (enabled on the development
laptop). The original image remains the fallback. See [artwork delivery](artwork-dev11.md)
for cache bounds, network requirements and limitations. The image task does not
change playback position or trigger another LOAD.

The sender controls metadata/queue through the frontend; the decoder/output
reports actual playback state back. The manager UI is configuration, not a full
media player. A live adapter process alone does not establish audible playback.

## Prepare without disturbing a working install

Prerequisites: Linux, Python 3.11+, FFmpeg, mpv for local output, a compatible
Rust toolchain/cache for building the frontend, and the pinned airplay-cli asset
for AirPlay. See source/dependency locks in `config/`. Only the Linux x86_64
AirPlay asset is currently provisioned and tested; ARM support is not established.

Create a separate versioned release/environment directory. From its source root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -c config/management-tested-constraints.txt '.[management]'
.venv/bin/python -m pip install -r config/youtube-extractor-requirements.txt
```

These are tested-version constraints, not complete cross-platform hash locks.
For the tested CPython3.12 Linux x86_64 runtime an exact wheel-hash lock and
verified offline installation procedure are now available in
[dependency-locks.md](dependency-locks.md).
Do not run an unbounded upgrade against a live environment. Ensure the extractor
environment's bin directory is on the **frontend's** PATH: it launches yt-dlp,
so configuring only the adapter's PATH is insufficient.

Build the frontend using the single current complete patch and recorded source
lock, following [source reconstruction](source-reconstruction.md). Never stack
the historical cumulative snapshots. Keep binary/source/dependency hashes with
the release; source reconstruction is not a bit-identical build guarantee.

## Start the supervised runtime

Choose persistent private directories outside the release tree. Keep an existing
frontend data directory and manager routes to preserve identities and volume.
The manager directory must have mode 0700. The certificate bundle is a separate
private runtime input; this runbook does not provision a trusted identity.
For a new frontend state directory use `config/vibecast-audio.toml` as its
`config.toml`; it aligns Eureka/streaming capability fields with audio-only
operation. Do not overwrite an existing customized configuration blindly.

```sh
/absolute/release/.venv/bin/cast-audio-receiver \
  --frontend /absolute/release/vibecast \
  --cliairplay /absolute/tools/cliairplay \
  --data-dir /absolute/private/state \
  --certs /absolute/private/certs.json \
  --web-port 8788
```

Open `http://LINUX-LAN-IP:8788` directly. Add the local output or explicitly scan
for an AirPlay target, then enable it. Imports begin disabled. Names are editable
independently of immutable route UUIDs. At most one new local route is allowed;
multiple explicit AirPlay targets are possible but real concurrent audio testing
remains pending. See [speaker management](speaker-management.md) for migration.

Discovery uses mDNS; frontend per-speaker Cast/eureka ports are dynamically
assigned. Port 8788 is only the management UI; 8010 is the shared player bridge.
Do not confuse them when diagnosing port collisions. VLANs, Wi-Fi isolation and
container networking can prevent discovery despite a reachable management page.
The LAN UI deliberately has no authentication. Do not expose it via port
forwarding or a public reverse proxy.

For local mpv audio, the manager must have access to the intended user's audio
session/device. Our development laptop preserves XDG_RUNTIME_DIR and its D-Bus
session address. Do not copy another machine's paths or assume a root service
automatically has working PulseAudio/PipeWire access.

## Tests without a person listening

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

FFmpeg crop tests skip explicitly if FFmpeg is absent. Optional management/
bridge tests need their installed extras. For the Rust deterministic gate use
the exact crate list and toolchain in the reconstruction guide. Live ignored
YouTube tests are not automatically run.

On a prepared host an isolated real-decoder DMR test can run silently:

```sh
PYTHONPATH=src .venv/bin/python tools/test_default_media.py \
  --binary /absolute/release/vibecast --certs /absolute/private/certs.json \
  --silent-fixture
```

It starts its own temporary frontend, fixture HTTP server, player and mpv;
exercises actual decoding, pause, seek, volume/status, EOF, error/recovery and
teardown; then cleans them up. Zero-valued PCM avoids a tone even while volume
changes are tested. It still opens an audio output. Do not select an AirPlay
target for unattended tests unless that target is explicitly reserved.
The development sender does not verify device authentication, and silence cannot
prove acoustic output quality. Stock YouTube Music/HA and hardware acceptance
remain separate. See [dev4 verification](autonomous-dev4.md) for pending tests.
The dev5 DMR check additionally verifies artist/album/type through returned Cast
status and the output backend; its regression is documented in
[dmr-metadata-dev5.md](dmr-metadata-dev5.md).

## Update and rollback

Build/test a new release alongside the old one. Back up private frontend state,
manager routes and actual launch configuration with restrictive permissions.
Stop the manager gracefully first so adapters/decoders are reaped, then stop the
frontend if it is being replaced. Start the chosen frontend and then the manager
against the same state directories. Verify version, route count/IDs, process
registration and a representative playback test before discarding rollback.

If startup fails, restore the previous binaries/environment and launch arguments.
Do not overwrite identities or restore an unrelated empty routes file. No state
schema migration is introduced by dev4. A rollback cannot undo server-side
revocation or a YouTube protocol change.

Native development still benefits from systemd/cgroup ownership. The OCI/HA
path adds `tini`, one supervisor and bounded process-group shutdown; it is the
preferred lifecycle for deployment tests.

For incidents use [maintenance](maintenance.md): record versions/hashes, isolate
the failed stage and redact private material before sharing logs. The resource
sampler measures selected process trees without starting playback. Certificate
coverage, chain expiry and real sender acceptance are separate checks.
