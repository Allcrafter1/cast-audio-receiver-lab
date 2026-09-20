# Controls-12 and plan audit

## Volume finding

Validation: the new active-session platform test failed on Controls-11 with a
missing-message timeout. Controls-12 passes all 22 core tests, including the
media-to-platform update. Release build succeeded and was deployed. Android
hardware-button/UI verification is still pending. Existing receiver binary was
saved at .state/controls-12-rollback/vibecast-controls11 on the test laptop.
patches/vibecast-controls-12-snapshot.patch is cumulative against vendored Git,
not additive to the previous snapshots. No authentication bundle changes.

Old subscriptions map was keyed by (TCP connection, sender ID) and stored one
transport. App CONNECT replaced receiver-0. Platform SET_VOLUME still changed
the backend, but receiver-status broadcasts had no subscribed recipient.

Separate platform subscriptions coexist with app subscriptions, are removed on
platform CLOSE/TCP disconnect, and survive app-channel close. App ownership and
last-sender cleanup remain separate. Media SET_VOLUME now also broadcasts the
new device status, not only media status. Tests cover both volume namespaces.

## Rapid selection is not prefetch

Foreground resolution still blocks the command consumer. A -> B -> C needs
latest-selection cancellation and subprocess cleanup; background next-item
prefetch does not supply that. No speculative retries of an unchanged title
are planned. See the authoritative WORKING-PLAN.md for acceptance criteria.

## Why checks may be slow

The observed slow first candidate succeeded. This rules out a claim that all
of that sample was spent failing through other codecs. A probe's elapsed time
can include DNS/connect/TLS, server first-byte delay, redirects, playlist and
segment requests and retry/backoff. Which dominates this title is not yet
attributed. Total extraction can additionally include service client metadata
requests and JavaScript processing. Do not call all extraction time a CDN delay,
or infer a cause solely from codec/bitrate. Keep validation unchanged.

## Generic Cast layer

Public Web Receiver application code is not a standalone Linux Cast receiver.
It expects the Cast Application Framework/runtime. Google's reference app can
be studied/reused under its license, but a compatible browser/platform API,
media pipeline and potentially service authentication/DRM are separate needs.
Publicly served JavaScript is not automatically openly licensed.

Our native AppProvider/PlaybackController/backend boundary is already a generic
separation. Reuse the native transport/session/player core, keep Lounge/yt-dlp
inside the YouTube adapter, audit Default Media Receiver behavior and actual
Android sender app IDs. The earlier Python receiver implemented a default-media
slice; that does not establish that the active Vibecast binary supports it.
Source audit: platform build_app_providers currently registers SvtPlay, Tv4Play,
Viaplay, PrimeVideo and YouTube, not a Default Media Receiver provider. Their
presence is not a claim that these video services work in our audio deployment.
Do not simply whitelist every app ID or advertise unsupported capabilities.

Candidate Android sender matrix (documented Cast support, not compatibility
with this receiver, and not a popularity ranking):
- Pocket Casts: podcasts, useful first audio compatibility target.
  https://support.pocketcasts.com/knowledge-base/chromecast/
- BubbleUPnP: local/network audio, useful codec and URL behavior tests.
  https://bubblesoftapps.com/bubbleupnp/
- TIDAL and Qobuz: music services, service-specific behavior must be measured.
  https://support.tidal.com/hc/en-us/articles/360001256118-Chromecast
  https://help.qobuz.com/en/articles/10206-how-do-i-experience-hi-res-on-android
- Plex: documented Android casting; verify audio-speaker applicability separately.
  https://support.plex.tv/articles/201812808-cast-from-android/

Receiver references:
- https://developers.google.com/cast/docs/web_receiver
- https://github.com/googlecast/CastReceiver

Decision: volume fix first, cancellation next, keep successful playback plumbing.
No browser runtime, new service adapter or deferred performance redesign now.
