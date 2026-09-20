# Architecture review and packaging decision — 2026-09-19

Status: review/proposal. This records the current implementation and the minimum
refactors recommended before packaging. It does not authorize the Home Assistant
package or a new plugin framework by itself.

## Current system in one picture

```text
Android sender / Home Assistant
             |
             | Cast discovery, TLS and application messages
             v
  one Rust/Vibecast frontend process
    - one virtual Cast receiver per registered output
    - Cast sessions, media state and device authentication
    - YouTube/Lounge application and URL resolution
    - Default Media Receiver for direct HTTP(S) media
             |
             | versioned JSON messages over local WebSocket
             | Load / Play / Pause / Seek / Stop / Volume
             v
  one Python adapter process per enabled route
    - maps normalized media and controls onto AudioBackend
    - reports actual state/position/volume/error to Rust
    - asks the manager to prepare shared square artwork
             |
       +-----+------------------------------+
       |                                    |
       v                                    v
  persistent mpv IPC                 AirPlayAudioBackend
  local decode/output                FFmpeg -> 44.1 kHz stereo PCM
                                             |
                                             v
                                  Music Assistant airplay-cli
                                             |
                                             v
                                       AirPlay target

  Python management process
    - direct LAN UI/API
    - persistent route IDs/names/target configuration
    - AirPlay discovery and artwork HTTP cache
    - owns/restarts adapter processes, but not the Rust frontend
```

The manager UI configures routes; it is not in the audio stream. The Rust
frontend owns Cast application/session semantics. An output adapter owns actual
playback and is the source of truth for audible state and position.

## Responsibilities and why each technology exists

### Rust / patched Vibecast

Rust provides the network-facing Cast runtime: `_googlecast._tcp` discovery,
TLS/Cast framing, device-auth response selection, sender connections, receiver
and media namespaces, session ownership and media state. Vibecast already has a
useful input boundary:

- `AppProvider` identifies and launches a Cast application.
- `AppSession` resolves a Cast load into canonical `PlaybackMedia` and handles
  service-specific namespaces.
- YouTube and Default Media Receiver are separate providers.
- `PlaybackController` lets app-specific control channels drive the common
  player state machine.

This is the correct place for future Cast-side inputs. A new service receiver is
not a Python output and should normally be another provider/crate registered at
build time. Compile-time registration is acceptable; a runtime plugin ABI would
add risk without a current user need.

### Python orchestration and adapters

Python provides the management API/UI, discovery, configuration, lifecycle
supervision for output adapters, cover processing coordination, and the bridge
from Vibecast's player protocol to concrete audio backends. `AudioBackend` is
already a protocol-neutral interface with metadata, load, play, pause, stop,
seek, volume, status and shutdown operations.

Python is a good fit here: the orchestration is I/O-heavy, integrations are
easier to add, and neither PCM nor image pixels are processed in Python itself.
There is no performance reason to rewrite this layer in Rust now.

### mpv

mpv is the local-output decoder/player. It stays alive and is controlled over
JSON IPC. It handles source formats, buffering, seeking, audio-device output and
reports real position, pause, volume, EOF and errors. Reimplementing those
functions would create a large and fragile media player.

### FFmpeg

For AirPlay, FFmpeg opens the selected source and normalizes it to the PCM format
expected by the sender: signed 16-bit, 44.1 kHz, stereo. It also performs bounded
image decoding/cropping/encoding. It is not the Cast receiver or AirPlay protocol
implementation.

### yt-dlp plus its JavaScript support stack

The YouTube application receives YouTube identities/queue controls rather than
a stable generic audio URL. The resolver uses yt-dlp's extraction stack to
obtain a checked playable source. This boundary is intentionally replaceable and
fragile: YouTube changes can break it independently of Cast or AirPlay.

### Music Assistant airplay-cli

`airplay-cli` implements the AirPlay/RAOP transport, pairing/capability behavior,
metadata/artwork/progress delivery and remote-control event stream. Our adapter
keeps that transport persistent and feeds it FFmpeg PCM. We should track and
credit the upstream rather than fork its protocol implementation casually.

## Current data flows

### Audio and initial metadata

1. A sender launches a Cast app on one advertised receiver.
2. The app provider normalizes the request to `PlaybackMedia`: stream URL(s),
   type, title/artist/album, duration, images, start position and autoplay.
3. Rust sends a session-scoped `load` command to that receiver's Python adapter.
4. The adapter first reports `BUFFERING`, sets protocol-neutral metadata, then
   asks the selected backend to load.
5. mpv opens the URL directly, or FFmpeg opens it and streams PCM to airplay-cli.
6. The backend reports actual state, position and volume to Python; Python sends
   those reports to Rust; Rust updates Cast media/receiver state and invokes the
   active app's playback/volume callbacks.

### Artwork

The initial media carries the original image URL. In parallel with playback,
the adapter asks the loopback-only manager endpoint to create/cache a bounded
square JPEG. The manager publishes only the opaque finished image on its LAN
HTTP endpoint. The adapter sends an artwork update correlated by session and
original URL; Rust replaces artwork only if that media is still active. Cover
work therefore cannot delay or replace the audio load.

### Controls from the Cast sender

Cast or YouTube/Lounge control -> Rust canonical session state -> player command
over WebSocket -> concrete backend -> actual backend state report -> Rust/app ->
sender feedback. This is why play/pause, seek and volume can stay synchronized.

### Controls originating at an output receiver

AirPlay remote play/pause/stop currently changes the Python backend state. The
resulting state report reaches Rust and the YouTube application's
`on_playback_update`, so the architecture can reflect state and volume. It does
not yet carry an explicit user-intent command from output to active input.
`PlayerReport` has only State, Artwork and Error, while the AirPlay remote parser
handles only play/pause/toggle/stop. Next/Previous (and a robust distinction
between an output-origin pause request and passive status) therefore lack a
general structural path. This must be resolved before freezing the bridge API,
although hardware acceptance can wait.

## What is already modular, and what is coupled

### Keep as-is or evolve gently

- Input providers behind Vibecast `AppProvider` / `AppSession`.
- Canonical Rust `PlaybackMedia` and session state.
- Python `AudioBackend` for load/control/status.
- One adapter process per advertised output. Failure isolation and independent
  identities are useful, despite their process overhead.
- Persistent mpv and AirPlay transports.
- Shared asynchronous artwork conversion/cache.
- Static, compile-time input and output registration for the first release.

### Coupling/technical debt to address before packaging

1. **No single process owner.** The manager supervises adapter processes, but
   the Rust frontend is started separately. A release needs one top-level
   supervisor/entrypoint that starts Rust, waits for bridge readiness, starts
   management/adapters, handles signals and reports readiness.
2. **Output kinds are hard-coded in several places.** `mpv`/`airplay` validation,
   CLI construction, target schema and UI behavior are separate conditionals.
   A small static backend registry should own descriptor, config validation,
   discovery capability and factory/argv creation. This is not a dynamic plugin
   platform.
3. **Player protocol has no version/capability negotiation.** Add an explicit
   protocol version and supported command/report capabilities before external
   adapters depend on it.
4. **Output-origin control intent is incomplete.** Add a session-scoped
   `controlRequest` report (play, pause, stop, seek, volume, next, previous) and
   route it through the active app/canonical coordinator. State reports remain
   observations, not commands, preventing feedback loops.
5. **Metadata and artwork updates are asymmetric.** Artwork has a narrow update
   message while other metadata is load-only. Keep this for the first release
   unless DLNA/Sonos requires general incremental metadata; do not refactor only
   for aesthetic purity.
6. **The patched Vibecast checkout is a dirty upstream worktree.** It works and
   can be reconstructed from a base plus complete patch, but that is awkward for
   contributors and automated updates. Publish a reviewable maintained fork or
   a clean pinned source tree; do not expose dozens of historical cumulative
   experiment patches as the build recipe.
7. **Historical Python receiver code is installed beside the active product.**
   Keep it under an explicitly historical/research area or remove it from the
   release package so users do not start the wrong receiver.
8. **Current docs mix historical and active paths.** Historical documents need
   labels; installation docs must present one supported route.
9. **Dependency and redistribution audit is incomplete.** In particular review
   the exact FFmpeg/mpv builds, Rust transitive inventory, yt-dlp support stack,
   and airplay-cli's own third-party caveats before publishing a combined image.
10. **Operational APIs are missing.** Route listing is not a health/readiness
    contract and there is no complete redacted support bundle.

## Recommended minimum core/adapter design

Do not introduce a generic event bus or arbitrary runtime plugins. Formalize the
boundaries that already exist:

```text
Input adapter (Rust AppProvider/AppSession)
        -> canonical media + input-specific controls
Session coordinator (Rust; single authority)
        <-> versioned player bridge
Output adapter (Python AudioBackend + static descriptor)
```

The canonical contract should cover:

- stable route/player identity and declared capabilities;
- media URL(s), content type, metadata, duration, start/autoplay and artwork;
- commands load/play/pause/stop/seek/volume;
- observed state, position, duration, volume, idle/error reason;
- explicit output-origin control requests;
- schema/protocol version and correlation/session generation.

Adding a future input will normally add a Rust provider and registry entry.
Adding an output will normally add one Python backend plus one static registry
descriptor, tests and optional discovery/UI schema. Neither should require
editing the YouTube resolver or another backend.

## DLNA and Sonos assessment

`async_upnp_client` is a sensible maintained foundation for DLNA DMR discovery,
control and eventing and was originally written for Home Assistant's DLNA DMR
use case. It does not make DLNA a trivial drop-in PCM backend. A DMR commonly
pulls a URL after `SetAVTransportURI`, so our adapter must also provide:

- capability/content-type selection;
- DIDL-Lite metadata and artwork URL;
- AVTransport play/pause/seek/stop and RenderingControl volume;
- subscription/poll fallback for state/position;
- a LAN HTTP proxy/transcode endpoint when a target cannot fetch the original
  signed URL or codec, with Range, cancellation, expiry and seek behavior.

The direct URL path may be small for compatible devices; a reliable general
adapter is a separate milestone. Implement it after the output registry and
media-serving boundary, not before the first packaging work.

Sonos should be a separate adapter. SoCo already supports discovery, `play_uri`,
transport/volume and Sonos-specific services under MIT, but grouping and service
behavior are not equivalent to generic DLNA. Reuse SoCo (or another maintained
Sonos client after review); do not disguise Sonos as a guaranteed DLNA subset.

## Repository recommendation

Start with **one public product monorepo**. Directory separation is enough:

```text
receiver/
  python/cast_audio_receiver/   management, bridge and output adapters
  rust/                         clean pinned Vibecast fork/source integration
  web/                          management UI (or packaged with Python)
  packaging/oci/
  packaging/linux/
  packaging/home-assistant/
  tests/{unit,integration,fixtures}/
  docs/
  licenses/
  tools/
```

Use at most a second repository for a clean Vibecast fork if preserving upstream
history and offering patches upstream is materially easier there. Pin that fork
by immutable commit in the product build. Do not split every adapter into its
own repository. Keep HA packaging in the product repository initially; split a
thin HA app repository only if distribution conventions or multiple apps later
make that cleaner.

## Minimal configuration policy

| Setting | What/why | Recommended exposure |
| --- | --- | --- |
| Web UI port | Direct LAN management and artwork HTTP endpoint. Conflicts are plausible. | Normal option; default `8788`. |
| Authentication bundle | Private replaceable Cast runtime input. | Required setup/import path, stored outside image/source; never print contents. |
| Bind address | Interfaces on which management listens. | Internal default `0.0.0.0`; advanced override only. Trusted-LAN warning remains. |
| Data directory | IDs, routes, volume/settings and caches that survive upgrades. | Platform default: `/data` in container/HA, XDG state on Linux; advanced CLI override, not normal UI. |
| Cast/player ports | Cast receiver/eureka endpoints plus local Rust-Python bridge. | Automatically allocate Cast ports; bridge stays loopback/internal. Debug override only. |
| Binary paths | Exact mpv, FFmpeg and airplay-cli executables. | Bundled known paths in image; PATH lookup in developer/native mode; advanced override only. |
| Log level | Diagnostic verbosity. | `INFO` default; one advanced troubleshooting option. Never make unsafe raw upstream logs the default. |
| Local audio device | Which ALSA/Pulse/PipeWire destination mpv uses. | System default normally; show selector/advanced option only when local output is enabled and multiple devices exist. |
| Artwork/LAN address | URL that physical receivers can fetch for processed covers. | Autodetect route/interface and published web port; override only for VLAN, multi-NIC, proxy or unusual DNS. |

Internal timeouts, codec probes, bridge addresses and subprocess paths should not
become a large end-user form. Advanced CLI/environment overrides can remain for
development without becoming HA options.

## Packaging recommendation

1. **Supervised reproducible runtime first.** Define one entrypoint/config model
   and a clean build from pinned sources.
2. **OCI image second.** It is the portable build artifact containing Rust,
   Python, mpv/FFmpeg and airplay-cli. Publish immutable multi-architecture
   images only for architectures where every native component builds/tests.
3. **Linux deployment.** Initially provide a documented systemd service around
   the same OCI image (host network plus explicit audio/persistent mounts). A
   native package/installer can follow if container audio/networking proves too
   awkward; do not maintain a second implementation.
4. **Home Assistant App/add-on.** Make it a thin HA configuration/presentation
   layer around the same image/build stages: `config.yaml`, options translation,
   persistent `/data`, host networking for mDNS/Cast, configurable web port and
   HA audio mapping only when local output is used. Direct LAN artwork still
   needs a reachable port even if the UI later also uses HA ingress.

Home Assistant's current model is explicitly container based and recommends
pre-built multi-architecture images. Therefore the OCI image is not throwaway
work; it is the natural shared deployment unit. A Home Assistant custom
integration is not required merely to run the receiver.

## Dependency/update policy

- Commit `Cargo.lock` and pin the Rust toolchain.
- Generate exact, hashed Python locks per supported interpreter/architecture.
- Pin OCI base images by digest for releases.
- Record exact airplay-cli release asset and digest.
- Pin/test yt-dlp, yt-dlp-ejs and Deno together as one compatibility set.
- Record FFmpeg/mpv package/build versions and enabled license features in each
  image; image digest is the final deployed identity.
- Generate an SBOM and retained license/notice bundle for every release image.

Use reviewed update pull requests, never automatic production upgrades. Start
with GitHub Dependabot for Cargo, pip, Docker and GitHub Actions. A scheduled
read-only upstream-report Action should inspect nonstandard pins (airplay-cli
release asset, Vibecast base/fork, yt-dlp support stack) and open/report an issue
containing only version differences and the required test matrix. If custom pin
tracking becomes cumbersome, Renovate is the stronger next step because its
custom managers and dependency dashboard can track arbitrary version files.
No update PR should auto-merge until deterministic tests and selected live
compatibility tests pass.

## Health, status, logs and support bundle

### `/health`

Machine-oriented, small and unauthenticated on the trusted LAN:

- `200` live/ready when manager event loop is healthy, Rust bridge is ready and
  every enabled adapter is registered or explicitly in bounded startup;
- `503` with fixed reason codes when a required component is missing/unready;
- no media names, URLs, target credentials or certificate material.

OCI/HA needs this to distinguish “process exists” from “receiver can accept
work” and to restart only on genuine failed health, not a normal empty session.

### `/status`

Operator-facing safe JSON: application/build versions, shortened artifact
hashes, route IDs/names and states, active/idle phase, last successful playback
time, last fixed error category, certificate coverage dates/fingerprint only,
and restart counts. Sensitive fields are omitted by construction. This answers
“which boundary failed?” without reading raw logs.

### Structured logs

Use stable event IDs/fields (timestamp, component, route ID, session correlation
ID, stage, duration, result/error category) in text or JSON. Never log signed
media URLs, HTTP headers/cookies, pairing data, authentication payloads or raw
environment. Titles should be disabled/redacted in support mode. Structured
events make regressions comparable across versions and let agents search by
stage instead of parsing prose.

### Redacted support bundle

An explicit button/CLI creates an allowlisted archive containing `/health`,
`/status`, build/dependency inventory, sanitized configuration shape, recent
structured events and test results. It must be assembled from known safe fields,
not from “zip the state directory and remove obvious secrets”. Add regression
tests that plant sentinel secrets/URLs and prove they do not appear. Users can
inspect the archive before attaching it to an issue.

## Publication/licensing findings

- `THIRD_PARTY_NOTICES.md`, the Vibecast MIT text, AI/origin disclosure and
  contribution guidance exist and are a good start.
- Complete the Rust transitive and container artifact license inventory; package
  metadata summaries alone are insufficient.
- Preserve airplay-cli's own third-party notice and resolve its documented
  ambiguous incorporated-source grants before redistributing the combined
  binary/image.
- Clearly distinguish code used, research inspiration, and proprietary
  interoperability comparison. Thanking projects does not grant redistribution
  rights or imply endorsement.
- Public certificates are not the same as private device/TLS/signing keys. Keep
  authentication bundles out of Git and public images unless a specific legal,
  contractual and security review establishes permission. The runtime should
  support replaceable private bundle import regardless.
- Before the first public push, build a fresh export and scan Git history,
  patches, logs, fixtures and artifacts—not only the working tree—for private
  data. Generate source/binary provenance and an SBOM from that exact release.

## Recommended decision sequence

1. Approve the minimal contracts above, particularly explicit output-origin
   controls and the static output registry.
2. Clean the patched Rust source into a reviewable fork/tree and quarantine
   historical Python prototypes from the release package.
3. Add the top-level supervisor plus `/health`, `/status`, structured event
   categories and redacted support bundle.
4. Produce and test one pinned x86_64 OCI image with persistent state and
   rollback; add CI, update notifications, SBOM and license artifacts.
5. Wrap the same image/build in the HA App metadata and real-HA test loop.
6. Test Yamaha/other AirPlay, HomePod/AirPlay 2, multiple outputs and weaker
   hardware. Add ARM images only after native dependencies pass there.
7. Design DLNA on the common output contract and HTTP media-serving boundary;
   keep Sonos a distinct optional adapter.

This sequence improves maintainability without destabilizing the working Cast,
queue, artwork or persistent AirPlay paths.
