# Native Google Cast speaker track

## What controls the device class

A native Cast receiver is discovered through `_googlecast._tcp.local` and
normally accepts Cast V2 TLS connections on port 8009. The `ca` TXT field is a
capability bit mask:

- bit 0 (`1`): video output
- bit 2 (`4`): audio output

An audio-only receiver must advertise audio output without video output. The
base value is therefore `ca=4`; modern Google devices add further capability
bits.

Observed on the local network on 2026-07-30:

| Receiver | `ca` | Base output bits |
| --- | ---: | --- |
| AirReceiver | `4101` | video + audio |
| Nest Audio | `199428` | audio, no video |
| Lenovo CD-4N341Y | `207364` (idle) | audio, no video |

This explains the TV classification of AirReceiver independently of its DIAL
service.

## Authentication observation

A read-only fresh-nonce challenge against the purchased AirReceiver instance
showed:

- a Google TV device certificate chaining through `Eureka Gen1 ICA`;
- no sender nonce in the response;
- a valid signature over the current TLS peer certificate;
- a peer certificate lifetime of two days.

This matches the replay design documented by the Shanocast author. The
Google-signed device private key is not required to be present in the APK when
precomputed peer-certificate signatures are used.

Copying only the public certificates is insufficient. Copying the shared TLS
key and replay table would impersonate the same certified device and remains
dependent on sender nonce checks staying relaxed, the certificate not being
revoked, and precomputed time windows being available. It is suitable only as
a fragile interoperability experiment, not a distributable receiver design.

## Current reversible experiment

The Linux laptop publishes `Audio Lab Laptop Speaker` with `ca=4100` and
forwards Cast TLS byte-for-byte to the purchased AirReceiver installation on
the old phone. A setup proxy on port 8008 rewrites only the public device
description to an audio-only, multizone-capable shape. It does not copy or
terminate receiver credentials.

Run it on the laptop with:

```sh
python3 tools/cast_speaker_shim.py 192.168.1.60 \
  --advertise-address 192.168.1.50 \
  --advertise-host audiolab-speaker.local \
  --name 'Audio Lab Laptop' \
  --instance-name 'Audio Lab Laptop Speaker'
```

Stop it with `Ctrl-C`. The publisher and both listeners are removed together.

## Remaining standalone implementation

1. Preserve the working audio-only discovery and YouTube Music Cast path.
2. Do not rely on AirReceiver's setup multizone routes: binary analysis proved
   that they are unconditional `200 OK` stubs.
3. Add an audio-only Cast V2 discovery and receiver service to the Linux
   runtime.
4. Implement Cast device authentication. The legitimate production path
   requires Google-provisioned credentials; the replay path is lab-only.
5. Implement the YouTube Music application launch/session behavior and bridge
   it to the already working DIAL/Lounge player backend.
6. Validate play, pause, seek, volume, queue handling, reconnects, and sender
   behavior before integrating the receiver with Home Assistant.
