# DMR metadata preservation — dev5

## Reproduced boundary

The silent real-mpv test sends a normal single-item DMR LOAD with metadataType3,
title, artist and albumName. On the actual dev4 binary the subsequent MEDIA_STATUS
reports metadataType0 and loses the artist/album. This reproduces a receiver-side
loss without relying on SWR3 or a specific HA sender. The test fails before the
fix at `music metadata type was lost`.

Google's [MusicTrackMediaMetadata reference](https://developers.google.com/cast/docs/reference/web_receiver/cast.framework.messages.MusicTrackMediaMetadata)
documents artist, albumName and albumArtist as separate fields. A generic subtitle
is not a substitute for preserving those supplied music fields.

The old common metadata model did not represent those fields. The DMR resolver
then reduced parsed metadata to title/subtitle/images, and the coordinator rebuilt
a generic metadata object. Finally, the Python adapter treated subtitle as artist
and never passed an album. This explains the synthetic failure; it does **not**
prove what the earlier SWR3 or local-file sender actually supplied.

## Narrow additive change

- Add optional typed artist/albumName/albumArtist to the existing common model.
- Retain the original typed metadata object for DMR through PlaybackMedia and
  the optional player-payload metadata field, and use it in MEDIA_STATUS.
- Keep top-level legacy title/subtitle/images so existing player clients still
  work. Omit the new object when absent. No new endpoint, cache or dependency.
- Python prefers supplied track artist, then album artist/subtitle fallback, and
  forwards album to the already existing protocol-neutral backend/AirPlay fields.
- Other providers, including YouTube, explicitly retain the existing path with
  metadata=None. Their extraction, timing, queue and control logic is unchanged.

This is not a generic pass-through of every unknown JSON field and not a schema
for all possible video/music metadata. Unsupported fields remain unsupported.
Absent artist/artwork are not synthesized by scraping another service.

## Separate open questions

- SWR3 and local-file actual LOAD field presence and supported-command feedback.
- ICY/current-radio-title updates discovered by the decoder are not implemented
  by retaining initial sender metadata. That would be another feedback path.
- Live radio pause may be supported by the output but sender UI policy can
  differ; do not claim its UI fixed without the sender test.
- Cast/HA still receives original image URLs. The square crop applies to AirPlay
  image conversion only; a shared image-serving path is a separate decision.
- Media category normalization is still historical/video-biased; do not confuse
  that field with the already working audio-speaker discovery capability.

Unit tests cover typed round-trip, DMR retention/absence, coordinator status and
player payload, plus Python output mapping and unchanged legacy YouTube fields.
The silent DMR test checks both returned Cast metadata and output metadata.
See the Working Plan for actual build/deployment and acceptance status.

## Verification and deployment

138 deterministic Rust tests pass (one explicit live YouTube probe ignored).
All134 Python tests pass on Linux. The installed dev5 wheel in a fresh CPython3.12
hash-locked environment also passes the suite, with three FFmpeg skips where
that executable is unavailable. The 14 real-mpv silent DMR checks pass, including
the regression that failed on dev4. No live SWR3/HA user confirmation is implied.

Deployed under `.state/manager-dev5`: frontend326405, manager326406,
adapters326412/326413. All three existing route configurations retained, both
enabled routes run, and live Chromium UI checks pass. Same private479-window
bundle; old dev4 source/binary/launch inputs retained for rollback.
Source snapshot matches all109 inventoried files on local/reconstructed/remote
trees. The frontend hash is in `config/vibecast-0.6.0.dev5-source.lock.json`.
Python wheel SHA256:
`187dbc7b670800749db4e1e9fc9b69d496b0240f6eb16a4bd2741a995104bda5`.
