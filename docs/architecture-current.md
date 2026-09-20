# Current architecture (dev13)

This document describes the active product path. Historical experiments live
under `research/` and are not installed with the runtime wheel.

The player bridge is a separate loopback listener; only the Python management
interface is user-facing. The inherited browser player is an explicitly enabled
development feature, absent from the normal build. See the dev13 review for
the bounded changes rather than assuming every upstream Vibecast feature is
part of this audio product.

## Processes and ownership

```text
Cast sender / Home Assistant
            |
            v
maintained Vibecast fork (Rust)
  Cast discovery, TLS/session handling, YouTube + Default Media inputs
            |
            | player protocol v2 on loopback WebSocket
            v
one Python adapter process per enabled speaker
  normalized load/control/status contract
            |
     +------+------+----------------+
     |             |                |
 local mpv      AirPlay       experimental direct-pull
 decoder        FFmpeg PCM    DLNA / Sonos
                -> airplay-cli

Python manager + UI
  routes, stable IDs, target discovery/config, artwork cache,
  adapter supervision, health/status/redacted support report

top-level supervisor
  starts Rust first, waits for its bridge, starts manager,
  then shuts manager/adapters down before Rust
```

The top-level supervisor owns only process lifecycle. The Rust coordinator is
the authority for the active Cast application/session. Each output backend is
the authority for what its target is actually doing.

## Normalized data and control flow

An input provider resolves a sender request into media URL(s), MIME type,
metadata, artwork, duration, start position and autoplay. Rust sends a
session-correlated `load` through the versioned player bridge. Python maps that
command to the selected `AudioBackend` and returns observed state, position,
volume and terminal reason.

Sender controls travel Rust → Python → output. Output-origin controls use a
separate v2 `controlRequest` message, rather than pretending that a passive
state observation is a command. Rust applies play/pause/stop/seek/volume to its
canonical session; next/previous are forwarded to the active YouTube Lounge
session. Hardware acceptance of every receiver-origin command remains pending,
but the structural return path now exists and has deterministic tests.

Artwork is kept off the audio-start critical path. The adapter starts playback
with the original metadata, while the manager asynchronously downloads and
center-crops a bounded square JPEG. A session/source-correlated artwork update
replaces the URL only if the same item is still active.

## Extension boundaries

Inputs are Rust `AppProvider`/`AppSession` implementations. YouTube and the
Default Media Receiver are separate providers today. A future service-specific
Cast receiver belongs there.

Outputs implement the small Python `AudioBackend` contract and add one entry to
the static output registry. The registry centralizes target validation,
singleton policy, process arguments and backend construction. It is deliberately
not an arbitrary runtime plugin loader; normal source changes are an acceptable
cost for a new adapter.

DLNA and Sonos currently let the physical target fetch the source URL. They do
not yet add a relay/transcoder, because that would introduce another HTTP
server, seek/range semantics, CPU cost and failure boundary. See
`network-outputs.md`.

## Component roles

- **Rust / maintained Vibecast fork:** Cast-facing protocol, applications,
  sessions, YouTube queue/source resolution and canonical media state.
- **Python:** management, orchestration, adapter protocol and output mappings;
  it does not process PCM samples itself.
- **mpv:** durable local decoder/player and real local playback state.
- **FFmpeg:** AirPlay PCM normalization and bounded artwork conversion.
- **yt-dlp stack:** replaceable, fragile YouTube source extraction boundary.
- **airplay-cli:** upstream AirPlay/RAOP transport, metadata and receiver events.
- **async-upnp-client / SoCo:** optional DLNA and Sonos control transports.

## Remaining release debt

The architecture is now a reasonable open-source base: responsibilities are
separated, lifecycle has one owner, protocols are versioned, extensions have
narrow boundaries, and deterministic tests cover failure/cancellation paths.
It is not release-finished. Remaining work is mostly product/release engineering:

- build and smoke-test the OCI image on a Docker-capable host;
- install/update/rollback-test the Home Assistant wrapper on real Supervisor;
- finish complete dependency/SBOM/licence inventories;
- perform physical DLNA/Sonos and additional AirPlay target acceptance;
- create a sanitized clean-history product repository and publish artifacts;
- complete and privately provision the replaceable authentication bundle;
- decide whether hardware evidence justifies a network-output relay/transcoder.

The known fragile boundaries are Cast authentication policy, undocumented
YouTube/Lounge behavior, yt-dlp extraction, signed source URLs, AirPlay upstream
behavior and renderer-specific DLNA/Sonos compatibility. Diagnostics and pins
make failures isolatable; they cannot guarantee that external services never
change or revoke behavior.
