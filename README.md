# Cast Audio Receiver Lab

This is an experimental, audio-only Google Cast V2 receiver and protocol bridge.
The current product path uses Vibecast as its upstream Cast frontend and a small
external-player adapter for Linux or AirPlay output.

## Current development path (0.6.0.dev12)

Use the [current runbook](docs/current-runbook.md), not the historical standalone
Python receiver commands further down this page. The active architecture is:

```text
YouTube Music / a compatible default-media sender
    → Vibecast (Cast discovery, app sessions, YouTube resolution / direct URL)
    → one Python adapter per configured speaker
    → mpv locally OR FFmpeg PCM → Music Assistant airplay-cli → AirPlay target
```

The direct LAN management UI has no login and manages persistent speaker IDs,
editable names, explicit AirPlay imports, enable/disable and deletion. The web
port is configurable (default 8788). It is intended for a trusted LAN, not the
public Internet. Existing Google Home group/adoption support is **not** provided.

YouTube Music, local output and persistent legacy RAOP have been practically
tested. The generic Default Media Receiver supports single direct HTTP(S) media
loads; an actual HA media-library test used it. This does not imply compatibility
with every Cast app, Spotify, DRM, HomePod or all AirPlay hardware. Those require
separate implementations or acceptance tests. A Home Assistant App/add-on and
one-click public installer/updater are not yet available. The repository now
contains an experimental Home Assistant App package; a real HAOS/Supervisor
source build, install, ingress/LAN access, restart and persistent speaker-state
test has passed. Hardware AirPlay, update and rollback acceptance remain open.

Current automated coverage and pending user checks:
[DMR metadata correction](docs/dmr-metadata-dev5.md),
[dev4 verification](docs/autonomous-dev4.md),
[working plan](docs/WORKING-PLAN.md),
[installation and deployment](docs/installation.md),
[maintenance](docs/maintenance.md),
[speaker management](docs/speaker-management.md), and the
[first real Home Assistant acceptance run](docs/ha-acceptance-20260920.md).
Authentication bundles are private runtime inputs, not included public assets.
Cast trust/revocation, YouTube control/extraction and target firmware can break
compatibility independently of our version. Long certificate validity is not a
guarantee of future service acceptance.

A functional Cast deployment requires that input: startup fails explicitly if
the configured bundle is missing or unreadable rather than presenting a dead
speaker as healthy. The owner's private Home Assistant installation uses the
validated 773-window bundle through 2030-12-06. Whether the same reusable
third-party authentication material may be redistributed in a public repository
or image is a separate unresolved release gate; it is never silently uploaded.

Artwork conversion is centralized in `cast_audio_lab.artwork`: all current
AirPlay covers are decoded through a lossless intermediate, center-cropped to a
bounded 1:1 image, conservatively stripped of embedded letterbox bands, and
encoded once as high-quality JPEG. The source image's own resolution remains a
hard quality limit. With `--artwork-public-url` configured, the manager prepares
and serves square images for Cast/Home Assistant too; original URLs remain the
fallback while processing or on failure. This happens independently of playback.
See [shared artwork](docs/artwork-dev11.md) for setup, cache limits and tests.

Much of this experimental code was developed collaboratively with AI (GPT/Astra)
from requirements and practical tests led by an initiator without programming
experience. Independent review and contributions are welcome. See
[contribution guidance](CONTRIBUTING.md) and
[origin and attribution requirements](docs/PROJECT-ORIGIN.md); this project is
not endorsed by Google, Apple or Music Assistant.
The verified foundation/credits inventory is in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md);
remaining license ambiguities are explicitly recorded as publication gates.

## Historical prototypes and development notes

The remaining commands document earlier experiments; they are retained for
research and are **not** the installation procedure for the current application.

Version0.5.0 adds an active-path Default Media Receiver (`CC1AD845`) for
single HTTP(S) media LOADs. Direct audio, controls, seeking, EOF, error recovery
and reconnect have passed isolated tests through real mpv and Redmi RAOP output.
This is not arbitrary service-app support: Spotify-specific receivers, DRM and
Cast queue loading are not implemented by this provider. Standard sender/app
acceptance remains separate from the development-sender tests.

Implemented in the historical Python receiver prototype (not the current
Vibecast application's compatibility list):

- `_googlecast._tcp` mDNS advertisement with audio-only capability (`ca=4`)
- TLS Cast channel and protobuf envelope
- heartbeat, receiver and media namespaces
- Default Media Receiver (`CC1AD845`)
- load/play/pause/stop/seek/volume state
- null and external command audio backends
- a fail-closed, pluggable authentication provider
- an experimental YouTube Music path using DIAL and YouTube Lounge
- audio-only YouTube URL resolution through optional `yt-dlp`

For current behavior and release preparation, see the
[working plan](docs/WORKING-PLAN.md), [maintenance guide](docs/maintenance.md),
[Default Media Receiver plan](docs/default-media-receiver-plan.md), and
[project origin / experimental status](docs/PROJECT-ORIGIN.md).

## Native Cast frontend

`tools/import_shanocast_bundle.py` converts Shanocast's public replay material
into Vibecast's replaceable `certs.json` format and verifies every signature.
Generated authentication material remains outside Git. The published table
covers two-day certificate windows through 2027-12-21; operation after that
date requires a replacement bundle. A separately held private inventory has
been cryptographically validated as 773 distinct, gap-free windows from
2026-09-12 through 2030-12-06 and passed the Home Assistant import/start path;
it is not part of the repository or container image.

See [docs/vibecast-audio-frontend.md](docs/vibecast-audio-frontend.md) for the
pinned upstream revision, build, speaker advertisement and Linux player path.

## Run locally

The supported entrypoint owns the native frontend and the speaker manager as
one process tree. It expects a built `vibecast` binary and a private replacement
authentication bundle in its state directory (or supplied with `--certs`).

```bash
cast-audio-receiver --frontend /path/to/vibecast \
  --data-dir /var/lib/cast-audio-receiver --web-port 8788
```

The manager then opens directly on the LAN at port 8788. Add local or discovered
AirPlay outputs there. See [installation and deployment](docs/installation.md)
for the Home Assistant, OCI and native boundaries and the
[current runbook](docs/current-runbook.md) for source development. OCI and Home
Assistant source packaging now exist; a public image, one-click repository URL
and update/rollback acceptance are still release milestones.

## AirPlay output (first implementation)

For the current **Vibecast external-player path**, version0.4.4 adds
`cast-vibecast-player --backend airplay --airplay-config /private/target.json`.
See [the integration/test instructions](docs/airplay-044-integration.md).
Version 0.4.8 playback/controls/artwork were user-confirmed on Redmi AirReceiver
RAOP. Version 0.4.9 keeps the transport open across loads/seeks; physical
synthetic transition/EOF/recovery tests pass, and the user confirmed YT Music
operation on the tested Redmi receiver. Other devices are not implied tested.
Use `--airplay-reconnect-on-load` on the external player for the previous mode.
HomePod/native AirPlay 2 and other hardware still require separate acceptance.
The older standalone receiver example below is not the active YouTube Music path.

The receiver can normalize Cast media to 16-bit/44.1 kHz stereo PCM with
FFmpeg and feed Music Assistant's `cliairplay`. The latter auto-selects RAOP,
AirPlay 2 compatibility mode or native AirPlay 2 based on the selected target.
This keeps Yamaha/AV receivers, HomePods and Apple TVs behind one output API.

Discovery, target validation and persistent AirPlay configuration are handled
by the manager; the old command examples were moved with the prototype to
[`research/legacy_python_receiver`](research/legacy_python_receiver/README.md).

Run tests:

```bash
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

## Experimental YouTube Music receiver

The first working compatibility path uses DIAL discovery plus YouTube's
undocumented Lounge protocol. It does not need Cast device attestation, but
YouTube currently presents DIAL receivers as TVs rather than speakers.

The preserved prototype is source-only and must be opted into explicitly:

```bash
PYTHONPATH=src:. python3 -m \
  research.legacy_python_receiver.legacy_cast_receiver.youtube_receiver \
  --name "Kitchen Audio Lab" --player-command "mpv --no-video {url}"
```

The receiver deliberately autoplays a `setPlaylist` command. Pass
`--no-autoplay` to reproduce receivers that wait for a second explicit Play
press.

This protocol is unofficial and can change. `yt-dlp` may also require current
YouTube extractor support or a user-supplied token/cookie configuration in the
future.

## Output adapters

The normal runtime exposes each configured output as a stable Cast speaker.
Local mpv and AirPlay are the tested output paths. Direct DLNA/UPnP and Sonos
outputs are available as experimental adapters: their lifecycle, validation and
control mapping have automated tests, but no physical renderer has been accepted
yet. They hand the source URL to the target device and therefore do not claim
that every signed URL, DASH manifest, codec or metadata field will work there.
See [network output limitations](docs/network-outputs.md).

The adapters share a small static registry and a versioned player contract. This
keeps targets, playback state and output-origin controls separate without
creating a dynamic plugin ABI. Adding another output should normally require a
backend module plus one registry entry, not changes to the Cast frontend.

## Probe your own AirReceiver instance

Before inspecting an APK, run a fresh, read-only authentication challenge
against the app on your Android device:

```bash
PYTHONPATH=src python3 tools/probe_auth.py 192.168.x.y
```

The JSON report contains certificate fingerprints, algorithms, lengths and
whether the response binds the fresh nonce to the TLS certificate. It never
prints the response signature or certificate bodies, and it does not attempt
to extract a private key. The report is suitable for comparing behavior, though
certificate fingerprints should still be treated as device metadata.

Receiver status and availability of a few well-known audio app IDs can be read
without launching or stopping an app:

```bash
PYTHONPATH=src python3 tools/inspect_receiver.py 192.168.x.y
```

## Authentication provider API

Pass `--auth-provider package.module:provider`. The object must expose:

```python
async def respond(challenge: bytes, receiver_tls_certificate_der: bytes) -> bytes | None:
    ...
```

The input and output are complete serialized `DeviceAuthMessage` payloads.
Returning `None` closes the unauthenticated connection.

See [the current architecture](docs/architecture-current.md) for the active
product design and [docs/architecture.md](docs/architecture.md) for the earlier
research boundary and
next experiments. The sanitized results from a live AirReceiver installation
are recorded in
[docs/airreceiver-observation.md](docs/airreceiver-observation.md).
The YouTube/YouTube Music implementation path is in
[docs/youtube-receiver-plan.md](docs/youtube-receiver-plan.md).
The product architecture, direct-versus-group routing, Home Assistant packaging
and staged implementation are defined in
[docs/project-a-roadmap.md](docs/project-a-roadmap.md).
