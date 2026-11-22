# SoundCloud → Yamaha MusicCast (DLNA): what we learned

Field notes from making the Android SoundCloud app cast to a Yamaha MusicCast
stereo pair (WX-021 ×2 + NS-NSW100 sub) through this receiver's DLNA output.
Everything below was verified on real hardware with a microphone next to the
speakers, not only in tests.

## Result

- SoundCloud (free account) appears as a normal Cast target and starts within
  ~7 s, also for multi-hour DJ sets.
- Pause/play, seeking (e.g. jump to 1:05:25 → audio after ~0.3 s), volume keys,
  track changes, title/artist/cover and track duration on the Yamaha all work.

## SoundCloud Cast protocol (as observed)

- Cast app ID `B143C57E`, web receiver `https://cast-new.soundcloud.com`.
- `LOAD` carries `contentId = soundcloud:tracks:<id>` and the user's
  authorization in `customData.credentials.authorization`.
- Resolution: api-v2 `/tracks?ids=<id>` → `media.transcodings` → transcoding URL
  with `client_id` → JSON `{url}` → stream. The `audio/mpegurl` HLS variant often
  answers 404; unencrypted AAC HLS (`audio/mp4`, fMP4 with `EXT-X-MAP`) and
  progressive MP3 work. Encrypted transcodings are skipped (no DRM handling).
- The Android sender sends `autoplay: false` and never a later `PLAY`; the
  provider forces autoplay.
- On a track change the sender reuses the previous track's position
  (e.g. 4694 s for a 3-minute track). A start position at/after the end is
  treated as 0.
- The authorization header is only sent to api-v2, never to CDN URLs, and is
  not echoed back to senders.

## Yamaha MusicCast as DLNA renderer

- It plays only audio with a known `Content-Length`. Length-less (chunked or
  live) AAC or MP3 streams are accepted and report "playing" but stay silent.
- Working approach: transcode to CBR MP3 320 kbit/s (40 000 B/s, no Xing/ID3
  header), announce the computed length from the item duration, map HTTP Range
  requests to a time offset and pad the tail with zeros if the encoder ends a few
  frames early. No `Transfer-Encoding: chunked`.
- DIDL class must be `object.item.audioItem.musicTrack`: async-upnp-client
  derives `object.item.audioItem` from `audio/*`, which has no artist/album-art
  properties, so they are silently dropped. Add `res@duration` so the renderer
  knows the total time.
- The renderer drops the previous connection on every seek or track change;
  that is expected, not an error.
- For a stereo pair, cast to the master; the pair and sub follow.

## FFmpeg pitfalls

- `-ss` before an fMP4 HLS input produced 0 bytes. Instead, trim the playlist to
  the segment containing the start time and pass the remaining offset.
- `-allowed_extensions ALL` is needed for the trimmed local playlist but breaks
  non-HLS inputs, so it is only added there.
- Some CDNs reject `HEAD`; readiness checks use a small `GET`.

## Receiver core

- A reasonless `IDLE` echo (racing a volume reply) unregistered the freshly
  loaded manifest proxy, so the first load sometimes went nowhere. Proxies are now
  only released on `IDLE` with an idle reason (regression test included).

## Testing setup that made this debuggable

An Android tablet driven over `adb` (screenshots before every tap, because list
order changes), the receiver's route log, the renderer's UPnP
`GetPositionInfo`/`GetMediaInfo`, and a laptop microphone measuring dB levels
(silence ≈ −75 dB, music ≈ −50…−60 dB). "Renderer says playing" was not
sufficient evidence; only the microphone was.
