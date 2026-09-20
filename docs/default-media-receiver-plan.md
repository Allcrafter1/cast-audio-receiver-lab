# Default Media Receiver: active-path integration plan

## Version0.5.0 acceptance update

Active Linux frontend now deployed (PID293360), both adapters0.5.0.
`tools/test_default_media.py` starts a separate loopback frontend and existing
mpv backend, serves an in-memory quiet WAV with HTTP Range support, then drives
the real Cast media namespace. OS-assigned bridge/Cast ports avoid collisions.
All13 checks passed on mpv and on explicitly selected Redmi RAOP6000:
initial paused position, paused seek, play-position, pause, sender volume,
backend volume feedback, queue rejection preserving playback, EOF,404,
recovery, receiver STOP, relaunch, app disconnect.

The test sender skips device-auth verification; it does not replace real
Google/HA/Android sender acceptance. HTTPS/MP3/FLAC/live-radio and artwork are
not all covered by the WAV test; retain the broader matrix below. Receiver-origin
volume status reaching Cast is verified, not YT Music's actual UI rendering.

While deploying, abnormal WebSocket close killed adapters; a narrow catch now
keeps the existing reconnect loop alive. Real regression fails before and passes
after; actual frontend restart also preserves both adapter processes and IDs.
See test_bridge_reconnect.py (existing optional bridge dependency required).

Example opt-in test (quiet audio on the executing Linux machine):

```sh
PYTHONPATH=src python tools/test_default_media.py \
  --binary /path/to/vibecast --certs /private/current-bundle.json
```

Add `--airplay-config /private/target.json --cliairplay /path/to/cliairplay`
only for an explicitly selected AirPlay target. Test owns its frontend/decoder;
it does not control an existing advertised receiver. Source paths must reference
one complete package checkout, not mixed historical staging directories.

## Earlier build milestone (historical)

Status: provider, registry and core guards implemented, 2026-09-13. Rust tests
pass on physical Linux: 7 provider +25 core +15 platform; repeat after formatting
also passed. YouTube regressions:43 passed,1 explicit live probe ignored.
Python regressions:104 passed. Offline/locked release build succeeded in2m17s;
actual direct-URL playback acceptance remains open; no live frontend restart yet.
Binary SHA256:47b2c33040a79d3603aa4750ed8c02cccb6db43e205b3628ffabb054699cf7bf.
Previous binary retained privately in .state/dmr-1/vibecast-before-dmr.
Historical Python DMR support is not proof of active-path compatibility.

Source snapshot: `patches/vibecast-dmr-1-snapshot.patch`, cumulative against
Vibecast b4616f8f399be706a1409ed21922aa2df892e303 for the nine included files.
Contains existing core control fixes too; do NOT stack it blindly on earlier
core snapshots. It is not the complete lab patch set. Cargo.lock adds only the
local provider and registry dependency, with no external dependency update.
The core protocol tests use a fake provider; real provider resolution and
registration have separate tests. This does not prove real decoder playback.

## Scope and expected usefulness

Implement the public media-control behavior for app ID `CC1AD845`, rather than
embedding Google's browser runtime or claiming compatibility with arbitrary
service receivers. Google describes the distinction between default, styled and
custom receivers in its [receiver overview](https://developers.google.com/cast/docs/web_receiver).
The [Google receiver codelab](https://developers.google.com/cast/codelabs/cast-receiver)
provides a controllable sender test using the default app ID.

The clearest practical additional consumer is Home Assistant's ordinary
`media_player.play_media` path: HTTP(S) music files, podcast audio, radio streams
and local/TTS audio delivered as URLs. Its [Cast documentation](https://www.home-assistant.io/integrations/cast/#using-the-built-in-media-player-app-default-media-receiver)
explicitly documents Default Media Receiver use. This is not HA's dashboard
receiver, nor its special Plex/BBC/etc. controllers.

Android URL-casting applications are candidates only when they actually launch
this ID and use supported media commands. A Cast button does not establish that.
Do not promise Pocket Casts, BubbleUPnP, TIDAL, Qobuz or Plex compatibility from
generic Cast support alone. Record the launched app ID and command kinds during
an opt-in sender test before adding an application to the compatibility list.
Spotify remains outside scope; a custom service receiver is not replaced by DMR.

## Small implementation boundary

The existing Rust SDK already provides `AppProvider` / `AppSession` and canonical
`PlaybackMedia`. Add a focused bundled provider (following the existing app-crate
pattern) and register it in `vibecast-platform::build_app_providers`. No new
external library or browser dependency is needed.

`resolve_media` should choose `media.contentUrl` when supplied, otherwise the
HTTP(S) `contentId`, preserving content identity separately. Validate URL scheme,
finite nonnegative timing, MIME type and metadata. Preserve the existing source
URL unchanged (including escaping/signatures); do not invent filename parsing or
run yt-dlp for a directly supplied media URL. LAN HTTP(S) sources are intentional;
`file:`, arbitrary decoder protocols and paths must not be accepted as URLs.
Pass source, stream type, title/subtitle/images, duration, autoplay and start time
through the existing player bridge to mpv or persistent AirPlay.

Initial metadata limitation: the shared Cast `MediaMetadata` model does not contain
music `artist` or `albumName` fields, so they are not retained during parsing.
The first provider preserves existing title/subtitle/images; no shared-schema
expansion is included. LIVE loads with a nonzero start position are rejected
rather than attempting FFmpeg seeking on an unseekable radio stream.

Reuse core PLAY/PAUSE/SEEK/STOP/GET_STATUS/SET_VOLUME and session cleanup. Preserve
LIVE versus BUFFERED behavior: absent duration is normal for radio, and a live
stream must not falsely advertise seeking just because file playback supports it.
Audit the current coordinator's generic supported-command mask for that case.

Important limitation found in the active source: `QueueLoadRequest` currently
contains only request ID, and `hub.rs` answers `QUEUE_LOAD` with empty status
without loading its items. `QUEUE_GET_ITEM_IDS` is single-item only. Therefore
the small first milestone is **single-item LOAD**, not complete Cast queue
compatibility. Return a clear unsupported response for unimplemented queue
operations rather than reporting success. Full queue semantics are a separate
scoped decision; some otherwise-generic Android senders may require them.

The model already has `content_url`; no shared message-schema expansion is needed
for that field. SDK app code should depend only on the SDK and existing workspace
libraries, following the upstream layering. Context7 was not available in this
session; official web documentation was used for protocol guidance.

## Acceptance and regression matrix

1. Registry availability + LAUNCH for `CC1AD845`; unknown app remains unsupported.
2. HTTP MP3/FLAC and HTTPS audio LOAD, correct title/artwork/duration; preserve
   signed URLs and choose contentUrl over a non-URL contentId.
3. Autoplay false, nonzero start, pause/play, seek while paused, volume feedback,
   media STOP, receiver STOP, disconnect and second-sender reconnect.
4. Natural EOF reports FINISHED once; source 404, invalid URL and decoder failure
   report error, not successful completion. Later valid LOAD still works.
5. LIVE URL with no duration; no fabricated track end or misleading seek support.
6. Unsupported QUEUE_LOAD has an explicit failure and does not disturb playback.
7. Repeat on mpv and AirPlay; YT Music queue, fast selection, persistent transport,
   saved volume and session-cleanup regressions remain green.
8. Real Home Assistant URL/TTS call and one opted-in Android URL sender. Inspect
   only app ID/command/timing outcomes; redact URLs, query strings and tokens.

This is a useful small extension, but not a one-line registration: validation,
metadata/state fidelity, explicit queue limitations and real sender tests belong
to the minimum releasable feature.
