# AirReceiver interoperability observation

Observed on 2026-07-29 UTC against a user-owned, current Google Play
installation of `com.softmedia.receiver`. Personal network identifiers and the
short-lived TLS fingerprint are intentionally omitted.

## Network identity

- HTTP server: `AirReceiver/1.0.3.0`
- Emulated model: `Eureka Dongle - Chromecast`
- Emulated Cast build: `1.36.151708`
- Model name: `AirReceiver`
- mDNS capability bitmask: `ca=4101` (audio and video output, not
  audio-only)
- `display_supported`: `true`
- Receiver status described volume as `attenuation`

This explains why sender applications display it as a television rather than
an audio-only speaker.

## Device authentication

Two independent TLS connections produced the same result:

- The TLS leaf certificate is self-issued with an `AIRSCREEN` identity and has
  a 48-hour validity window.
- Its subject-public-key SHA-256 fingerprint before certificate rollover was
  `288788c4e1ee42b80008adf71a2d6b7e5186cee803734a5e5cc21e1a721d4ca6`.
- The response uses RSA PKCS#1 v1.5 and SHA-256.
- It contains one intermediate certificate and no CRL.
- The returned Google TV client certificate is a legacy `Eureka Gen1` device
  certificate with SHA-256 fingerprint
  `942f06e6c8ee6bbc60c51d49b91f9473629a7cde2648532bb6bb18a029c174d5`.
- The response omits the sender nonce even when a fresh 16-byte nonce is
  explicitly requested.
- Its signature verifies over the TLS certificate alone.

This is the legacy, nonce-less authentication behavior associated with the
Shanocast research. It is accepted by the tested Android sender path even
though current Open Screen requires the returned nonce and checks revocation.

The public Shanocast analysis of AirReceiver found that the TLS key pair stays
fixed and that the app ships or obtains a pool of precomputed certificate
signatures. The current live version still exhibits all externally testable
properties of that replay design. Comparing the TLS subject-public-key
fingerprint after the current certificate expires will verify whether its key
also remains fixed today.

The `AIRSCREEN` marker is notable because it belongs to a different commercial
receiver product. It may simply be a reused certificate template; by itself it
does not establish a relationship between the vendors.

## Experiments needed

1. Capture the real Android sender challenge with this lab receiver. Its safe
   log records only nonce presence/length and algorithms.
2. Start YouTube Music playback and read `RECEIVER_STATUS` while its receiver
   app is active. This reveals app ID, transport ID and namespaces.
3. Export the installed APK splits via ADB and statically inspect only
   interoperability-relevant code, resources, native libraries and hostnames.
4. Test a clean AirReceiver start while its WAN access is blocked to determine
   whether current builds still rely entirely on bundled material.

Private keys, reusable signatures and license bypasses are outside this
project. They are unnecessary for understanding the state machine, app
handling, media protocol and audio-only advertisement.

## YouTube and YouTube Music path

Launching Cast app ID `233637DE` produced:

- display name `YouTube`;
- `urn:x-cast:com.google.youtube.mdx`;
- `urn:x-cast:com.google.cast.media`;
- the generic debug, CAC and injection namespaces.

After connecting to the app transport, `getMdxSessionStatus` returned an
`mdxSessionStatus` containing a device ID and a 64-character screen ID. The
screen ID value was not recorded. The ordinary media namespace simultaneously
reported one idle media session.

Google's public app catalog currently maps `233637DE` to
`https://www.youtube.com/tv?castv=2.0`. This strongly indicates a web/TV
receiver runtime with a Cast IPC bridge rather than a YouTube audio-stream
special case. YouTube Music uses this YouTube receiver and its MDX/Lounge
pairing.

AirReceiver also exposes a separate optional `YouTube DIAL` feature and a
`YouTube TV` launcher. These are not the same path. While the Cast YouTube
session above was active, `GET /apps/YouTube` still returned HTTP 404, proving
that the DIAL service was not implicitly activated by the Cast launch in the
observed configuration.

The practical choices are therefore:

- Cast V2 + `233637DE`: can advertise audio-only capabilities, but requires
  Cast device authentication.
- YouTube DIAL + YouTube TV: avoids Cast device authentication, but is a
  television-oriented discovery and pairing path.
