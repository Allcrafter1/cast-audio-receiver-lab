# YouTube Music receiver plan

## Confirmed flow

```text
YouTube Music sender
        |
        | Cast LAUNCH 233637DE (YouTube)
        |          or 2DB7CC49 (YouTube Music)
        v
Cast receiver platform
        |
        | launch https://www.youtube.com/tv?castv=2.0
        v
YouTube receiver runtime
        |
        +-- Cast namespace: com.google.youtube.mdx
        |      getMdxSessionStatus -> screenId
        |
        +-- YouTube Lounge/MDX cloud session
        |
        +-- Cast media status and local audio/video playback
```

AirReceiver appears to provide a generic Web Receiver/IPC container: both
YouTube and the Default Media Receiver expose its `com.google.cast.inject`
namespace, while their app-specific namespaces differ.

## Implementation strategy

The empirical AirReceiver A/B test established that both of these work
independently:

1. Google Cast Receiver with YouTube DIAL disabled.
2. YouTube DIAL with Google Cast Receiver disabled.

Both required one additional Play press after connecting. DIAL therefore gives
us a useful open first milestone, while Cast remains the path to native speaker
presentation.

The implementation now uses a transport-neutral Lounge command engine:

```text
                 +-- DIAL discovery (implemented; appears as TV)
phone / YT Music|
                 +-- Cast MDX adapter (next; can advertise ca=4)
                              |
                              v
                 Lounge command engine
                              |
                  YouTube audio resolver
                              |
                         AudioBackend
```

The DIAL receiver intentionally starts playback when `setPlaylist` selects a
video. This differs from the observed AirReceiver behavior and avoids the
second Play press.

The first resolver uses optional `yt-dlp`. It is replaceable because YouTube
stream extraction changes independently of discovery and Lounge control.

## Native Cast speaker target

The existing Cast service already advertises audio-only capability (`ca=4`).
The remaining blocker for stock senders is legitimate receiver device
attestation. The receiver now exposes YouTube app ID `233637DE` and the
empirically observed YouTube Music ID `2DB7CC49`, advertises their MDX
namespace, answers `getMdxSessionStatus` with the active Lounge `screenId` and
`deviceId`, and feeds that Lounge into the same player core. No DIAL or TV
identity is required on this path.

Hosting Google's receiver page in a constrained Chromium/Cobalt runtime remains
a fallback if a native MDX adapter proves incomplete. Such a runtime would:

1. resolve an app ID through Google's public Cast app catalog;
2. allow only the app's declared HTTPS origins;
3. expose connection, sender and media APIs to the page;
4. translate page messages to Cast V2 namespaces;
5. send audio to a selectable ALSA/PipeWire or network output;
6. suppress video rendering when the platform is configured audio-only;
7. report `display_supported:false` and advertise audio-only mDNS capability.

The current Python receiver already supplies discovery, TLS framing, receiver
control, the media namespace and a player abstraction. Missing components are
the browser/IPC application runtime and a legitimate stock-sender
authentication provider.

## DIAL milestone

The current DIAL service implements SSDP discovery, the device description,
the `/apps/YouTube` status/launch resources, ephemeral Lounge screen
credentials, command polling, queue control and audio playback. Sender
applications will still classify it as a TV; that is a presentation limitation
of the discovery path, not of the shared playback core.
