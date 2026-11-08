# Network outputs and volume synchronization

DLNA/UPnP MediaRenderer and direct Sonos are optional outputs behind the same
registry as local mpv and AirPlay. Sonos through AirPlay and the direct `sonos`
backend have different implementation and test histories.

## Startup volume

At a new Cast app session the player reads the output's current level and mute
state where supported. A valid, unmuted level above zero is adopted unchanged,
including levels above 25%. If the output is at zero, muted, unavailable to read,
or returns an invalid value, the player sets **25%, unmuted**, before playback.
This is a fallback, not a permanent volume cap. Failure to apply the fallback
fails the load instead of starting audio with an unknown level.

The shared backend policy replaces the conflicting proposals in
[zero00zero's PR #16](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/16)
and [PR #17](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/17).
Persisted Cast volume is no longer authoritative for the physical output at
launch. The bridge marks launch initialization explicitly, so deliberate sender
commands before the first track still work. Older frontends use a conservative
first-preload-command fallback. A load without a preceding launch command also
initializes volume. Track changes and seeks in the same session do not reset it;
after Stop or a new app session the policy applies again. A zero/mute change
*during* playback remains zero/muted.

| Output | Startup reading | Receiver → Cast feedback |
| --- | --- | --- |
| Direct Sonos | SoCo device volume and mute | RenderingControl events, renewed automatically; polling fallback below |
| DLNA | DmrDevice update / GetVolume and GetMute when supported | Existing one-second profile polling, including pause and idle until Stop |
| mpv | Existing process's live `volume` and `mute` properties; 25% for a new process | mpv property-change events; this is player gain, not the OS mixer or an external amplifier |
| AirPlay | Current airplay-cli adapter exposes no pre-playback receiver-volume query; 25% fallback | Existing DACP absolute-volume callbacks and remote control events, when the device sends them |

The arbitrary `--backend command` development output has no physical volume
API. It now rejects initialization/volume commands instead of pretending to
apply a safe level; use the managed `mpv` backend for local playback. The null
backend remains a simulated output. No backend can infer changes that its
receiver does not report or expose through a query.

Hardware feedback updates the shared state without echoing a new volume write.
Existing output-wide volume revisions remain intact, including startup replies,
so delayed acknowledgements cannot overwrite newer sender commands.

## Sonos events and polling

SoCo 0.31.2 supports UPnP `RenderingControl` subscriptions. The adapter uses its
thread-safe event queue interface to deliver volume/mute on the asyncio loop,
not SoCo's non-thread-safe threaded subscription callback. See the
[SoCo subscription API](https://soco.readthedocs.io/en/stable/api/soco.events.html).

A subscription must receive an actual volume/mute event before it suppresses
five-second volume polling. Subscription failure, renewal failure or expiry
keeps/enables that fallback. After 60 seconds without a volume event, a watchdog
reads the device and replaces the subscription; this also recovers a silently
broken callback path. Events remain the immediate path when available. Volume
read errors alone do not stop audio. Stop/shutdown unsubscribes, waits for any
in-flight subscription operation, and rejects late events from the old owner.
Transport/position still use the existing one-second poll; this is separate from
volume events. The receiver host's SoCo callback listener must be reachable from
the speaker; a working SOAP connection alone does not prove that path works.

This event path is automatically tested, **not yet verified on physical Sonos**.
It controls the configured device, not a newly introduced group-volume policy.

## Media and metadata

Both network renderers pull media over HTTP. DLNA already uses the bounded
local `DlnaMediaRelay` for loopback URLs, HTTPS compatibility and unsupported
advertised formats. Direct Sonos now reuses that same relay for loopback sources,
Opus/WebM, ambiguous Ogg and unknown types. Supported remote MP3, AAC/MP4, FLAC
and WAV remain direct, including compatible live radio. MIME selection is a
compatibility policy, not proof that every codec/profile in a container is
supported by every device.

The relay copies supported containers or converts to MP3 at 192 kbit/s,
44.1 kHz stereo. It prepares a complete bounded file first (64 MiB, 90-second
preparation deadline), then serves Content-Length and byte ranges. This adds
startup latency; unsupported infinite/live sources are not a streaming
transcoding feature. Cancellation removes partial output, and Stop/shutdown
closes relay resources. Source URLs must still be reachable and authorized.

Sonos receives DIDL-Lite music-track metadata with title, artist, album and
artwork, plus the actual relayed MIME and URL. Title-only fallback applies if
metadata construction is unavailable. DLNA already forwards these music fields;
shared Cast metadata extraction remains common to all backends. Actual artwork
rendering, seeking and format support still depend on device firmware.

## Evidence and remaining acceptance

- In PR #16, zero00zero physically observed YouTube Music Android → AirPlay →
  Sonos Era 100 starting at 100% with the published 0.7.0-dev1 HA App. The proposed
  fix was explicitly automated-tested only, not deployed to that speaker.
- In PR #17, the author reports daily AirPlay use with Sonos Era 100 and “Play”.
  They explicitly did **not** test the direct `sonos` backend on hardware. The
  report does not establish every Play model, artwork, seeking or bidirectional
  volume behavior. The later general positive PR comment is not a feature-by-
  feature acceptance of either fix.
- The author checked Opus/WebM → MP3 through the relay with real FFmpeg/ffprobe.
  This integration adds a repeatable automated version with an HTTP source and
  format/duration assertions, alongside fake-device metadata, control, startup,
  event/fallback and cleanup tests.
- Direct Sonos playback, artwork, event delivery and renewal on real networks,
  natural end handling, seeking and grouped-speaker behavior remain unverified.
  AirPlay receiver-to-sender feedback remains device-dependent. Existing DLNA
  device reports are separate; no new physical test was performed for this work.

Acceptance should cover a positive device level above 25%, zero, mute, read
failure, changes from both sender and device, pause/idle, track replacement,
Stop/reconnect, event callback interruption, Opus conversion and supported live
radio. Automated success is not a hardware or deployment claim.

## Complete PR disposition

| Original change | Integration |
| --- | --- |
| #16 startup cap and sender feedback | Replaced by the common device-read/25% fallback policy; corrected status still goes back to Cast. |
| #16 `CAST_AUDIO_MAX_LAUNCH_VOLUME` override | Intentionally not added: the requested policy has a fixed 25% fallback and preserves valid physical levels above it. |
| #16 uncapped volume during playback | Preserved; explicit pre-load user commands are also distinguished from launch initialization. |
| #17 Opus/WebM, Ogg, unknown MIME and loopback relay routing | Integrated using the existing shared finite-file relay. |
| #17 supported remote formats / live radio stay direct | Integrated and tested without constructing a relay. |
| #17 relay URL and actual MIME in DIDL | Integrated; source identity remains separate in backend status. |
| #17 title, artist, album and artwork | Integrated; artist is emitted as both creator and UPnP artist, with XML escaping. |
| #17 title-only metadata fallback | Integrated, including SoCo's own DIDLMetadataError; does not retry failed playback commands. |
| #17 early SoCo data-structure import | Retained in backend construction. |
| #17 launch-time device-volume adoption | Generalized to the shared policy instead of keeping a Sonos-only special case. |
| #17 five-second reverse-volume polling | Replaced by preferred events with five-second fallback and a silence watchdog. |
| #17 Stop/shutdown relay cleanup | Integrated and hardened for both Sonos and DLNA: cleanup errors still terminate local playback state; temporary media is removed and failed HTTP cleanup can be retried. |
| Tests from both PRs | Retained or adapted to the unified semantics, supplemented by lifecycle, metadata, direct-radio and conversion checks. |

Neither PR contains another unrelated feature beyond these changes. Versions,
publication and hardware acceptance are separate from this local integration.
