# Project A: modular audio receiver

## Product decision

Build a standalone Linux service first. A Home Assistant add-on is packaging,
not the protocol engine. The same daemon must run on a speaker, Raspberry Pi,
NAS, or in a container.

There are two deliberately different playback paths:

1. **Direct target:** each physical speaker advertises its own audio-only Cast
   receiver and plays locally. This is the shortest path and the default for a
   single room.
2. **Virtual group target:** a receiver named, for example, `Everywhere`
   accepts one session and hands it to Music Assistant/Sendspin. Music
   Assistant performs timed distribution to the selected renderers. A group
   may add buffering, but relative synchronization matters more than minimum
   latency there.

The virtual target is our group alias. It is not and must not pretend to be a
Google Home speaker group.

## Architecture

```text
                  +--------------------------+
Google Cast  ---->|                          |----> local ALSA/PipeWire/mpv
DIAL/Lounge  ---->| receiver/session core    |----> Music Assistant/Sendspin
Spotify later --->| commands + metadata      |----> AirPlay bridge later
                  | URL or PCM               |----> UPnP/DLNA bridge later
                  +--------------------------+
```

Keep discovery, authentication, session state, media acquisition and playback
as separate interfaces. Prefer URL hand-off when an output can fetch the media
itself. Decode to PCM only when the destination requires it or when a
synchronized mixed-device group needs a common timed stream.

### Inputs

- **Cast V2 audio-only:** the desired user experience. Advertise
  `_googlecast._tcp` with audio capability (`ca=4`), so senders and Home
  Assistant see a speaker/media player instead of a television.
- **DIAL + YouTube Lounge:** useful credential-free fallback and compatibility
  test. It normally presents as a television and is not a replacement for a
  Cast endpoint in Home Assistant.
- **Spotify Connect:** possible later input, preferably through a maintained
  component such as librespot rather than a new protocol implementation.

### Outputs

- Local playback is milestone one.
- A Sendspin source/output adapter is milestone two. It makes Music Assistant
  the synchronization and routing layer for virtual groups.
- AirPlay and UPnP/DLNA are adapters after the core API is stable. Existing
  bridges should be reused where they meet the requirements.

## Home Assistant shape

- An add-on runs the daemon with host networking and persistent configuration.
- A small integration exposes health, sessions and controls as `media_player`
  entities. Cast discovery itself remains standard mDNS/Cast V2.
- One installation may configure several virtual receiver identities, each
  with a stable name, UUID and output route.
- Music Assistant owns group membership and timed playback. Virtual group
  aliases map to a Music Assistant/Sendspin player or hidden anchor rather than
  to Google Home cloud groups.

## Authentication and longevity

Google Cast device authentication is the only closed boundary. A stock sender
does not merely ask for an arbitrary certificate: it verifies a Google-trusted
certificate chain and a signature that proves possession of the matching
private key and binds the response to the current connection/challenge.

Consequences:

- Random keys or self-signed certificates cannot pass verification.
- A captured response is not a durable identity; replay approaches can depend
  on time windows and can be revoked sender-side.
- Copying one hardware identity requires its non-exportable/private secret,
  creates duplicate identity and revocation risk, and is unsuitable for a
  public project.
- No honest design can promise 10--20 years of stock-Google compatibility from
  an unofficial replay credential.

Therefore the repository ships no shared credential. The existing
`AuthProvider` boundary remains mandatory and fail-closed. It permits a lawful
device-specific or officially licensed provider to be added or rotated without
rewriting discovery, playback or routing. DIAL remains usable if Cast auth is
temporarily unavailable.

## Implementation choice

Do not throw away the current Python receiver: it already has the right module
boundaries, audio-only advertisement, Cast framing, YouTube/Lounge path,
backends and authentication seam. Evaluate Vibecast beside it as a maintained
Rust implementation and protocol reference. Port or embed only components that
materially improve conformance, media handling or deployment; avoid an early
rewrite.

AirReceiver is no longer a runtime dependency. It remains only historical
evidence that sender compatibility is possible.

## Milestones

1. Make the current daemon reproducibly installable and test local playback on
   Linux without AirReceiver; retain DIAL as the credential-free end-to-end
   baseline.
2. Add structured configuration, stable receiver IDs, health/status API and
   PipeWire/ALSA backends.
3. Add a Sendspin adapter and one virtual group alias routed through Music
   Assistant.
4. Package the same daemon as an OCI image and Home Assistant add-on; add the
   thin HA integration.
5. Run a Cast conformance comparison with Vibecast and finish the audio-only
   Cast path behind `AuthProvider`. Stock senders become a supported production
   input only when a sustainable legitimate provider exists.
6. Add output adapters in this order: existing Music Assistant bridges first,
   then only missing AirPlay/UPnP functionality.

## Explicit non-goals

- Google Home adoption or official Google speaker groups
- harvested AirReceiver or consumer-device private keys
- Bluetooth investigation
- coupling the core daemon to Home Assistant
