# AirReceiver 5.1.7 static analysis

Analysis date: 2026-09-12

The APK set was pulled through normal ADB package paths from the user's
purchased installation. No private application data was read.

## Package shape

- Package: `com.softmedia.receiver`
- Version: `5.1.7` (`2020164765`)
- Target SDK: 35
- Relevant native library: `libAirReceiver.so` (AArch64, stripped)
- Cast runtime revision reported by the receiver: `1.36.151708`

AirReceiver has independent Java entry points and service switches for:

- Google Cast (`startCast`, ports 8008 and 8009)
- Open DIAL / YouTube (`startOpenDial`, port 3600)
- DLNA renderer
- AirPlay and AirTunes

This confirms that a successful YouTube DIAL session does not prove that the
Google Cast path was used. The Cast setting invokes a separate native receiver.

## Why it presents as a TV

Three independent observations agree:

1. The embedded Cast configuration declares
   `capabilities.display_supported=true`.
2. The Java discovery publisher hard-codes `ca=4101`, which includes
   `VIDEO_OUT` (`1`) and `AUDIO_OUT` (`4`).
3. A live `/setup/eureka_info` response reports `display_supported=true` and
   `multizone_supported=false`.

The setup endpoint accepts a POST containing a capability-shaped object with
HTTP 200 but ignores it. Device class is therefore not a user-configurable
setup property.

The embedded application catalog contains a distinct YouTube Music receiver:

- app ID `2DB7CC49`
- URL `https://www.youtube.com/tv?castv=2.0&theme=m`
- IPC and background mode enabled

The `YouTube` application entry is separate and advertises discovery through
both DIAL and Cast V2. This explains the two similar user-visible YouTube
receiver modes.

## Multizone code

The native library contains the Cast multizone namespace and route strings for:

- join group
- leave group
- disband group
- set audio-output delay
- dynamic groups and group status

The shipped configuration has dynamic groups and multichannel groups disabled.
It enables a video-device multizone experiment, but the live public capability
remains `multizone_supported=false` and the group list is empty.

ARM64 dispatch analysis confirms that all of these routes are stubs:

- `/setup/multizone/join_group`
- `/setup/multizone/leave_group`
- `/setup/multizone/disband_group`
- the equivalent underscore-form legacy routes
- `/setup/multizone_set_audio_output_delay`

Each branch loads the same HTTP version, status `200`, and reason `OK`, then
calls the response helper without parsing the request body. `ble_setup` uses
the same stub shape. This explains why join requests return success while the
subsequent eureka response continues to contain an empty group list.

## Authentication boundary

`res/raw/signature` is not a Cast credential. It is an eight-entry Java
properties file containing integrity values for the native libraries.

The native library contains one PEM RSA private-key marker and one PEM
certificate marker. The live TLS endpoint presents a dynamically dated,
two-day self-signed `AIRSCREEN` transport certificate. The most likely role of
that embedded pair is TLS transport certificate generation, not the separate
Google device-auth identity.

A device-auth probe returns the Google TV leaf certificate through `Eureka
Gen1 ICA` and omits the sender nonce. This is consistent with the replay class
described in public Shanocast research, but static analysis alone does not prove
whether this build stores a Google device private key or a replay table. The
lab does not extract or reuse either.

Google Home account linking is a separate boundary. The app requests
`/setup/get_app_device_id`; AirReceiver returns the expected three-field shape,
but its certificate is a Google TV/Eureka Gen1 identity. A real adopted Lenovo
speaker returns a unique Lenovo Cast leaf identity and additionally reports
cloud and UMA device identifiers. With setup state and SSID normalized, the
Home UI completes without an error but sends no room or group write to the
receiver and does not persist it in the Home device graph.

## Speaker shim experiment

`tools/cast_speaker_shim.py` tests classification without terminating Cast TLS:

- publishes `_googlecast._tcp` with `ca=4100` (AirReceiver minus video output)
- proxies and rewrites the public setup description to
  `display_supported=false` and `multizone_supported=true`
- forwards port 8009 byte-for-byte to the purchased AirReceiver instance
- keeps the backend's device ID so its encrypted Cast-channel identity remains
  consistent

This tests whether Google Home proceeds to the native multizone handlers. It
does not fabricate synchronization support and is not a standalone receiver.
