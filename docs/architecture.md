# Historical prototype architecture and decision record

> This document describes the original standalone Python Cast experiment. It is
> retained as research history, not as the architecture of the current product.
> The active Vibecast/Rust + Python adapter architecture is documented in
> [architecture-review-2026-09-19.md](architecture-review-2026-09-19.md) and the
> [current runbook](current-runbook.md).

## Decision

Start with a small audio-only Cast V2 receiver and keep device attestation behind
an interface. This makes discovery, TLS framing, receiver/media namespaces and
actual playback independently testable.

Shanocast is useful protocol research, but not a sustainable base: its published
method replays signatures observed from AirReceiver, and current Chromium
versions reject the associated certificate. Copying a production key or replay
table would also create a security and distribution problem instead of solving
device identity.

Open Screen is the best long-term native foundation for Cast Streaming and
mirroring. Its standalone receiver is significantly larger and does not by
itself provide the general URL-based audio behavior of the Default Media
Receiver. The lab implementation therefore targets that missing, testable slice
first.

## Components

```text
phone / Chrome
      |
      | mDNS: _googlecast._tcp, ca=4
      v
TLS Cast channel :8009
      |
      +-- deviceauth ---> external AuthProvider
      |
      +-- heartbeat / receiver / media
                          |
                          v
                  AudioBackend
                    |        |
                   null   command argv
                             |
                         mpv/gstreamer
```

## Scope of milestone 1

- Audio-only mDNS capability (`ca=4`)
- Cast V2 length framing and protobuf envelope
- Heartbeat, connection, receiver and media namespaces
- Default Media Receiver app ID `CC1AD845`
- URL media load, play, pause, stop, seek and volume state
- Null backend and shell-free command backend
- Pluggable device authentication with fail-closed default

It does not claim compatibility with app-specific receivers such as Spotify or
YouTube Music. Those senders launch their own app IDs and often use additional
namespaces. Supporting them requires either app-specific protocol work or a
compatible receiver-app runtime after device authentication is resolved.

## Authentication boundary

A stock sender signs a fresh challenge into the TLS receiver certificate and
validates a receiver certificate chain rooted in Google's trust store. A
self-signed TLS certificate is enough for transport encryption but not for that
attestation.

Acceptable providers include a licensed/certified receiver implementation or a
user-owned hardware identity exposed through a signing service where its terms
and hardware permit that use. This repository deliberately has no facility for
extracting private keys or loading published production credentials.

## Next experiments

1. Run a read-only challenge probe against the user's own AirReceiver instance
   and record only behavior: algorithms, nonce binding, chain shape and result.
2. Exercise this receiver with a development sender that does not use Google's
   production trust decision.
3. Put a real player behind the command backend and validate HTTP/HLS audio,
   codec errors and clock/status behavior.
4. If certified identity becomes available, implement it as an external
   `AuthProvider`.
5. Add app IDs one at a time from observed, user-initiated audio sessions.
