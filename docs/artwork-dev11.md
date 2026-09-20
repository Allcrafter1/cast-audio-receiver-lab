# Shared square artwork for Cast and Home Assistant

Dev11 is deployed on the development laptop. 157 Python tests pass on Linux
(local environment skips eight FFmpeg-dependent tests); 158 Rust tests pass
and all20 silent DMR integration checks pass. These include the full image
conversion/HTTP/Cast feedback path. HA visual acceptance is still pending.

The shared `artwork.py` converter now also feeds Cast metadata. AirPlay keeps
using the same converter with its existing local-file delivery. There is no
change to decoding, audio buffers, source extraction, or queue policy.

## Flow

1. A LOAD provides an original image URL. Playback starts normally.
2. The Python adapter asks the existing local manager to prepare that image in
   the background. The manager coalesces requests for the same source URL.
3. The converter creates a bounded square JPEG using the established lossless
   intermediate and conservative embedded-border treatment.
4. The adapter reports the resulting LAN image URL through a new `artwork`
   bridge message. The Rust frontend updates only the active matching cover
   and broadcasts MEDIA_STATUS. It does not change the playback clock/state or
   inject a new YouTube selection.
5. Home Assistant and other Cast controllers can fetch the processed JPEG.

STOP, reconnect and replacement LOAD cancel the adapter's pending image report.
The frontend independently rejects mismatched source images and idle sessions.
Identical source URLs across tracks may share a cover, which is intentional.
No image is fabricated when the sender supplies none (for example a bare radio
URL). This does not implement ICY stream-title extraction.

## Configuration and limits

Use the updated frontend and Python adapter together, and start the manager with
`--artwork-public-url http://YOUR-LAN-HOST:8788`. Use the actual configured port.
The address must be reachable from Home Assistant and sender devices, not just
from the receiver. The processing request uses loopback; bind the manager to
`0.0.0.0`, `::`, or loopback. Without the option, original Cast image URLs remain
unchanged, which also supports rolling back to an older frontend.

The management UI stays directly accessible without credentials. Only finished
opaque image URLs allow cross-origin reads. Image preparation is loopback-only;
the management API retains its existing same-origin request checks.

- Up to 32 JPEGs, each bounded to 1 MiB, in a private temporary directory.
- One conversion at a time, at most four distinct queued/in-flight sources.
- One-hour URL-cache lifetime; oldest entries evicted when full.
- Cancellation of one consumer does not cancel a conversion another needs.
- No permanent worker or new runtime dependency; FFmpeg and aiohttp already exist.
- On error/overload, keep the original image URL. Audio never waits for conversion.

AirPlay and the HTTP cache currently share the conversion algorithm, not a
single cross-process file. An AirPlay route can therefore prepare the same
source separately for its output and for Cast feedback. Avoid a bigger transport
refactor without profiling evidence. The new cache bounds work between Cast
routes, but does not claim zero extra CPU or network cost.

The cache is disposable: manager restart, expiry or eviction removes old URLs.
Long-lived controllers may temporarily retain an expired URL until another LOAD.
Remote access through Home Assistant and HTTPS/mixed-content browsers may need
different routing; this LAN development setup does not establish remote support.

## Reproducible verification

`tools/test_default_media.py --artwork-check --silent-fixture --binary PATH
--certs PRIVATE_BUNDLE` uses real mpv, FFmpeg, the manager HTTP service and Cast
messages. A 640x360 fixture must appear as a 360x360 JPEG in MEDIA_STATUS, without
changing pause/position. The remaining seek/volume/EOF/error/cleanup cases run
afterward. No Internet image or audible tone is needed.

Unit tests cover cache reuse, expiry/eviction, cancellation, invalid sources,
cross-origin image reads versus API writes, old-track rejection and preservation
of the playback clock. Actual Home Assistant rendering is still a separate
acceptance test: start a known YT Music album, inspect the HA cover, seek, change
tracks rapidly and leave the session. AirPlay should remain unchanged.

The user's reported sound distortion was confirmed to be an intentional effect
in the song, not a receiver defect. Do not use it as evidence for codec changes.
