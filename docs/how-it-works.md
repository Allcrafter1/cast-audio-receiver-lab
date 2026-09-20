# How a Linux process becomes a Cast audio speaker

This project started with a very ordinary annoyance: YouTube Music on Android
could see Google speakers, but not the AirPlay receivers and amplifiers already
in the house. A simple URL forwarder sounded plausible. It was not enough.

For the phone to treat a Linux process like a real speaker, that process has to
look coherent at every layer: discovery, encrypted transport, device
authentication, application launch, media control, playback feedback and
cleanup. This document tells the technical story of how those pieces fit
together in the current receiver.

It is a description of an experimental implementation, not a compatibility or
security promise. The active Cast frontend is our maintained
[Vibecast fork](https://github.com/Allcrafter1/vibecast); the Python code in this
repository turns that frontend into a manageable multi-output product.

## 1. First, appear as the right kind of device

Cast discovery happens locally through DNS-SD/mDNS. A sender looks for
`_googlecast._tcp.local` services and reads TXT fields describing the receiver:
its stable ID, friendly name, model and capabilities.

That last part matters. Advertising a Cast endpoint is not enough to make it a
speaker. Our early receiver could communicate, but Android presented it as a TV.
The fix was to make all of the advertised device information agree that this is
an audio output: the mDNS capability field, the receiver device-information
response and the runtime model have to tell the same story.

Each configured route is registered with a stable player identity and is then
advertised as a separate audio receiver. Renaming or restarting it therefore
does not create an endless sequence of new speakers.

Discovery gets the name into the Cast picker. It does not establish trust and
it does not play anything yet.

## 2. Cast V2 is an authenticated message channel

After discovery, a sender connects to the advertised TCP endpoint and opens a
TLS session. Inside that session, Cast messages use the envelope published in
Chromium's
[`cast_channel.proto`](https://chromium.googlesource.com/openscreen/+/refs/heads/main/cast/common/channel/proto/cast_channel.proto).
Namespaces separate device authentication, heartbeats, connection management,
receiver/application control, generic media commands and application-specific
traffic.

The project incorporates that published protocol schema through Vibecast. It
does **not** embed Google's official Cast SDK, run a receiver registered in the
Cast Developer Console or load Google's full browser receiver runtime.

TLS by itself is not sufficient. Cast has a second device-authentication step:
the receiver supplies a Google-issued device certificate chain and a signature
that proves an acceptable device identity is associated with the TLS peer
certificate. A random self-signed certificate can encrypt the connection but
cannot satisfy that device check.

This is the wall that stops most otherwise convincing software receivers.

## 3. The authentication result that changed the project

Earlier work by [Shanocast](https://github.com/rgerganov/shanocast) showed that
some sender implementations accepted a legacy response made from precomputed
signatures for short-lived TLS certificates. Its public identity later appeared
in the Cast revocation data and stopped working with our Android sender, but the
shape of the solution was valuable.

We then compared a purchased AirReceiver installation on two user-owned Android
devices with the failing Linux endpoint. The useful observations were:

1. Both installations presented the same long-lived Cast device identity. It
   was not a newly issued identity for every phone.
2. The TLS peer certificate was self-signed and valid for a short, two-day
   window.
3. In the observed legacy response, the device-auth signature verified over the
   exact TLS peer-certificate bytes. The response omitted the sender nonce.
4. The old Shanocast identity was present in the revocation data we inspected;
   the working reference identity was not.

That explains both the opportunity and the constraint. If a sender accepts this
legacy form, a response can be replayed only with the **exact** peer certificate
for which it was signed. Editing or re-signing the certificate changes its DER
bytes and invalidates the device-auth signature. Because each peer certificate
is short-lived, one credential does not cover years of normal clock time.

The next breakthrough came from controlled offline tests on the owned rooted
Android reference device. Moving the device clock and isolating a stale cached
record caused the reference receiver to produce a different valid peer
certificate/key/response set for the selected time window. The result worked on
the Linux receiver in a real YouTube Music test. This also showed that the
observed window generation did not require a live Google issuance request for
every date.

We collected the resulting windows through 6 December 2030. Every entry was
checked for:

- matching TLS private key and peer certificate;
- a consistent device/intermediate certificate identity;
- valid response signatures for the recorded peer certificate;
- unique, adjacent time windows with no gaps or accidental duplicates.

At runtime Vibecast selects the window matching the current time and uses its
peer key/certificate and recorded authentication response. The bundle is a
replaceable input, not hard-coded application logic.

This mechanism remains deliberately described as fragile. Google can revoke the
shared device identity, senders can require challenge-nonce binding, certificate
validation can change, or the stored date coverage can run out. Cryptographic
self-consistency proves that we reproduced the observed response; it does not
force a sender to keep accepting it.

### What a real device would change

A genuine Cast device has a factory-provisioned device certificate and access to
the matching private key, commonly behind a device signing interface rather than
as an ordinary exportable file. Tristan Penman's
[Chromecast device-authentication research](https://tristanpenman.com/blog/posts/2025/03/22/chromecast-device-authentication/)
shows the important distinction: on a compatible rooted first-generation unit,
software can ask the device to sign a newly generated peer certificate without
extracting the long-term private key itself.

Researching that path on our own hardware is a future experiment. It is not a
normal installation method, it is not known to work on arbitrary Cast devices,
and it does not make the resulting identity immune to expiry or revocation. The
current release uses the separately distributed, time-windowed bundle described
above.

## 4. Launching an application without running a browser

Once the Cast channel is authenticated, the sender asks the receiver to launch
an application ID. Official Cast devices may load a Web Receiver application.
Our audio receiver implements only the application behavior it needs, as native
Rust providers.

There are two supported input paths today:

### YouTube and YouTube Music

YouTube uses its Cast namespaces to obtain a screen/session identity and then
coordinates the queue through YouTube's Lounge/MDX protocol. The sender remains
the familiar YouTube Music UI, but it is not continuously pushing decoded audio
from the phone.

The Vibecast YouTube provider follows that session, turns the selected item and
queue into the receiver's canonical media state, and obtains a checked playable
audio source through the pinned yt-dlp extraction boundary. Queue prefetch and
cancellation ensure that an obsolete slow resolution cannot overwrite a newer
selection. During development this produced genuinely gapless transitions on an
album whose tracks flow into one another.

Play, pause, seek, volume, next/previous, metadata, artwork, natural track end
and disconnect all have to update that same canonical session. Merely starting
an external player would leave the phone stuck in “connecting”, display stale
positions or allow an abandoned session to block the next sender.

### Default Media Receiver

The public Default Media Receiver application ID accepts ordinary Cast media
loads containing an HTTP(S) media URL, content type, timing and metadata. Home
Assistant uses this path for direct media, local files exposed over HTTP, TTS and
radio streams.

Our provider implements the relevant media messages directly instead of
embedding Google's receiver page. It preserves signed URLs, differentiates live
streams from finite media and returns observed playback state. It intentionally
does not promise arbitrary custom Cast apps, DRM or complete Cast queue
semantics. Google's own receiver overview likewise distinguishes the basic
[Default Media Receiver](https://developers.google.com/cast/docs/web_receiver)
from service-specific custom receivers.

## 5. Why we did not stop at DIAL

[DIAL](https://www.dial-multiscreen.org/overview) means “Discovery And Launch”.
It is good at exactly that: finding a first-screen device and starting an
application. Post-launch application communication is outside DIAL itself.

Our first experimental receiver proved that YouTube Music could be coordinated
through DIAL plus YouTube Lounge without passing Cast device authentication.
That remains useful historical research and a possible fallback. It did not
meet the product goal:

- Android presented it as a TV-style YouTube target rather than an audio Cast
  speaker;
- it did not provide the normal Cast media/status channel used by Home
  Assistant;
- it could not cover the generic Default Media Receiver path;
- its discovery and lifecycle semantics differed from the speakers users were
  trying to replace.

The harder Cast path is what makes the result feel and behave like a speaker,
not merely a remote application launcher.

## 6. One Cast session, several very different outputs

The Rust frontend owns the Cast-facing application and media state. It sends a
normalized command over a versioned, loopback-only WebSocket player protocol to
one Python adapter process per enabled route. That boundary carries media URLs,
metadata, duration, start position and controls in one direction, and actual
state, position, volume, end/error events and receiver-origin controls in the
other.

Keeping this boundary small is what lets outputs differ without teaching the
Cast frontend every transport:

- **Local audio:** mpv owns decoding and the real playback clock. Its IPC events
  supply position, pause, volume, EOF and failures.
- **AirPlay:** FFmpeg normalizes the selected stream to PCM and feeds a persistent
  Music Assistant `airplay-cli` session. Keeping the transport open avoids a new
  AirPlay handshake on every song. Metadata, square artwork and supported target
  controls travel alongside the audio.
- **DLNA:** compatible renderers fetch the media directly. For devices that
  cannot consume the original HTTPS/codec combination, a bounded local HTTP
  relay can terminate HTTPS and remux or transcode to a compatible form.
- **Sonos:** the experimental backend asks the target to pull the media URL
  directly. Its software contract is tested, but real hardware is not yet an
  acceptance claim.

Artwork is processed asynchronously so downloading and center-cropping a square
cover does not hold up audio start. Status is based on what the output reports,
not what the receiver hoped a command would do.

## 7. Process ownership and recovery

A small supervisor starts the Rust frontend, waits for its player bridge, starts
the Python manager and shuts them down in the reverse order. The manager owns
the persistent speaker definitions, adapter processes, target discovery,
artwork cache, web interface and redacted diagnostics.

This matters after failures. A decoder error must not look like a successful
track end, an old load must not win a race against a new one, a broken output
must not poison the next session, and disconnect must release the Cast session
for another phone. Much of the project's test suite is about these unglamorous
state transitions because they are what separate a demo from a usable receiver.

## 8. What can break

The design isolates fragile dependencies, but cannot remove them:

- **Cast authentication:** revocation, expiry or stricter sender validation can
  invalidate the current bundle immediately.
- **YouTube:** Lounge behavior and media extraction are undocumented service
  boundaries. yt-dlp and its JavaScript runtime need regular updates.
- **Signed media URLs:** they expire and must not be cached or logged as ordinary
  harmless URLs.
- **AirPlay, DLNA and Sonos:** real receivers differ in timing, codec support and
  control behavior; mocked tests cannot cover every model.
- **Discovery:** mDNS and renderer discovery require a LAN that permits multicast
  and containers need the correct network mode.
- **Platform support:** the released image is validated on `amd64`; other
  architectures need matching native transport artifacts and real testing.

The response to that fragility is not to pretend it is stable. Versions are
pinned, output boundaries are narrow, support reports are redacted, and the
project records which behaviors were automated-tested versus physically
confirmed. When something changes upstream, maintainers should be able to
replace one boundary and repeat a focused acceptance matrix rather than reverse
engineer the entire stack again.

## Sources and deeper records

The concise maintainer view is [Current architecture](architecture-current.md).
Detailed experiment logs remain in this repository so conclusions can be traced
back to evidence, especially:

- [Cast authentication comparison](auth-comparison-2026-09-12.md)
- [Offline certificate-generation result](certificate-offline-breakthrough.md)
- [Default Media Receiver design and tests](default-media-receiver-plan.md)
- [Current bundle distribution](bundle-distribution.md)
- [Credits, licences and exact upstream roles](../THIRD_PARTY_NOTICES.md)

The protocol and research foundations include Chromium's published Cast sources,
[Vibecast](https://github.com/emilsvennesson/vibecast),
[Shanocast and its author's write-up](https://xakcop.com/post/shanocast/), the
[official Cast receiver overview](https://developers.google.com/cast/docs/web_receiver),
the [DIAL specification site](https://www.dial-multiscreen.org/overview), and
the device-authentication research linked above. These projects and researchers
made our practical integration possible; none is implied to endorse it.
