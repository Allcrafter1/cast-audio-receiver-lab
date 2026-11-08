# YouTube capability lab

These research tools prepare an isolated receiver for testing the ordinary
Android **YouTube** app while preserving the product's speaker identity. They
do not add a product setting or TV option, modify an installed receiver, invoke
ADB/SSH, or deploy anything. YouTube Music remains a separate working comparison.

The [investigation](../../docs/youtube-capability-lab.md) records the exact sender
versions, historical profiles and evidence. In the inspected installed APKs, the
normal GMS route's individual-speaker type and YouTube's audio-only rejection
test are both `AUDIO_OUT && !VIDEO_OUT`, when they read the same capability
snapshot. Other bits, a model string or icon URL cannot change that equality.
This is a bounded static finding, not a claim that every sender path behaves
identically or that a live hybrid profile is impossible. Mismatched capability
snapshots, group routes and account paths need separate evidence.

The initial secure-lock and `INJECT_EVENTS` obstacles on 2026-11-08 were
resolved by the owner. Authorized native picker screenshots and selection
observations are recorded in the investigation. The synthetic commands below
are separate checks; alone they cannot establish an app icon, sender acceptance
or real audio playback.

## Prepare a separate lab binary

Run these commands from the product repository root. Python 3.11 or newer is
required. The runner uses `websockets`; the combined probe also uses `zeroconf`.
Use an existing environment containing those dependencies, such as the product
image used by the investigation.

Supply an explicit clean frontend source tree or preserved source snapshot,
without build artifacts or Git metadata. The
preparer copies it to a new directory under `/tmp`, verifies the expected source
patterns, and patches only that copy. It refuses an existing destination. It
does not modify the supplied source or the product receiver.

```bash
python3 tools/youtube_capability_lab/prepare.py \
  --source /path/to/explicit/frontend-source \
  --destination /tmp/youtube-capability-lab/frontend-source
```

The resulting `frontend-source/PATCH-MANIFEST.json` records both changed files
and their baseline and lab hashes. Build the copied source using the supported
frontend toolchain:

```bash
cargo build --locked --release \
  --manifest-path /tmp/youtube-capability-lab/frontend-source/Cargo.toml \
  -p vibecast-cli
```

For a host requiring the investigation's glibc 2.36 target, use the established
`cargo zigbuild` workflow instead of assuming the build host's libc is compatible.
Keep the resulting binary at a separate lab path; do not replace the installed
product binary or share its data directory.

The lab binary has four independent environment overrides:

| Override | Wire field | Unset default |
| --- | --- | --- |
| `CAST_LAB_MDNS_CA` | mDNS TXT `ca` | `199428` |
| `CAST_LAB_DEVICE_CAPABILITIES` | Cast `DEVICE_INFO.deviceCapabilities` | `199428` |
| `CAST_LAB_MDNS_ICON` | mDNS TXT `ic` | `/setup/icon.png` |
| `CAST_LAB_DEVICE_ICON_URL` | Cast `deviceIconUrl` | Empty |

The preparer adds these seams to the copied source only. Never use them for a
production deployment. Existing TOML configuration supplies Eureka display and
group flags, the device model and the streaming-API display header. Profiles
support `eureka_display`, `api_display`, `multizone`, `cloud_groups`, `model`,
`mdns_icon` and `device_icon_url` independently. The `display` profile key is
only Eureka's fallback; the streaming-API display flag defaults to false.

## Run one profile

Use the authorized LAN host and an existing authorized real certificate manifest
by absolute path. The helper reads that manifest without copying its contents
into evidence. A synthetic certificate cannot establish stock-sender trust.

```bash
python3 tools/youtube_capability_lab/run_profile.py \
  --binary /tmp/youtube-capability-lab/frontend-source/target/release/vibecast \
  --certs /path/to/private/existing/certs.json \
  --run-root /tmp/youtube-capability-lab/runs \
  --profile speaker
```

Without an identity epoch, the receiver registers as `Audio Lab Probe <profile>`
with deterministic installation/player IDs for that profile. For fresh live
attempts, set the runner-only environment variable `CAST_LAB_IDENTITY_EPOCH` to
a new unique value for **each app/profile attempt**. The runner derives a new
installation UUID and appends an eight-character hash suffix to the friendly
name. It records the actual `friendly_name` and epoch in the private
`<run-root>/<profile>/lab-identity.json` (mode `0600`). Match that exact suffixed
name in the picker; an old unsuffixed or differently suffixed entry is a cached
route, even if its profile text matches.

Changing the epoch changes identity/name but does not choose a new data
directory. Pair every new epoch with a separate, previously unused `--run-root`
so receiver/app/Lounge state and the receiver queue start fresh for each app and
profile. Preserve prior attempt directories as evidence. This fresh-data matrix
does not test reconnection to a previously paired receiver or recovery of an
existing queue. A separate continuity test is needed for those behaviors.

Working receiver identities and Lounge state are never reused. Keep only
one lab profile running at a time. For a container, mount the lab files and cert
material read-only, use a separate writable run directory, and expose no physical
audio devices. Match the network and image to the host's existing test setup.

Stop the helper with Ctrl-C or SIGTERM. It disconnects the player, sends SIGINT
to the receiver, waits up to eight seconds, and force-stops only a receiver that
did not exit. After an abrupt kill, inspect `receiver.pid` before removing a
stale PID file. Never kill an unrelated process based on an old PID file.

JSON stdout contains labels, counts, session hashes and verification flags.
Raw receiver logs are private (`0600` inside a `0700` directory) and need review
before publication. Media URLs, tokens and raw peer messages are not printed by
the helper. Startup parsing accepts both plain and ANSI-colored receiver logs.

## Verify profile wiring

With the runner still active, run the probe on the same Linux host/container
and as a user permitted to inspect the lab receiver's process descriptors:

```bash
python3 tools/youtube_capability_lab/probe_profile.py \
  --run-root /tmp/youtube-capability-lab/runs \
  --profile speaker
```

When mounted at `/lab` inside the investigation container, with runtime state at
`/runs`, the equivalent command is:

```bash
python3 /lab/probe_profile.py --run-root /runs --profile speaker
```

The probe resolves only the exact profile service and verifies its friendly
name, mDNS mask and Cast `DEVICE_INFO` mask. It then checks Eureka's display,
multizone and cloud-group flags. mDNS advertises only the Cast port; Eureka uses
a separate random HTTP listener. To find it, the probe reads the lab PID's own
socket inodes and probes only that PID's loopback listeners, excluding the Cast
port. It never scans LAN ports or another process. `--eureka-port PORT` can
supply the known port explicitly.

Use `--interface LAN_IPV4_ADDRESS` to restrict DNS-SD queries to the host's
actual LAN interface. Without this option, the resolver uses its default
interfaces, which can include loopback or a phone hotspot. Record the queried
interface when comparing discovery results.

The probe does not authenticate a device, launch an app or play media. TLS peer
verification is intentionally skipped for this synthetic information query.
Its JSON always states `native_sender_verified=false`,
`device_auth_verified=false` and `audio_verified=false`. `wire.py` is copied
from the historical project's framing helper with its MPL-2.0 SPDX header;
no checkout-specific Python imports are needed.

## Record actual app behavior separately

The runner is a **silent protocol acknowledger**. It never fetches or decodes
media and never opens an audio device. It reports PLAYING to maintain a test
session; a LOAD proves that a command reached the bridge, not audible playback.
Every command event explicitly states `audio_verified=false`.

In the v3 live matrix, each app/profile uses a fresh identity and receiver data
directory, while the app is restarted without clearing its data or account.
The ordinary YouTube client opens the fixed public video and receives a pause
key before the picker; Music starts at its MAIN screen. A fresh receiver queue,
an unselected Music track or paused sender content can produce a valid session
without a LOAD. A missing LOAD alone therefore does not establish a capability
failure. Report listing, selectability, LAUNCH and LOAD separately.

The current calibrated screenshot comparison treats icon contrast below 150
as a greyed, unselectable row. Capture it as such and skip selection; do not
classify the absence of LAUNCH/LOAD as a failed cast attempt. Use the exact
fresh friendly name and the highest-contrast matching row to avoid a dim cached
duplicate. This threshold is a UI diagnostic for the tested capture layout,
not a Cast capability or a universal accessibility-state rule. Icon artwork is
classified separately from selectability.

For each profile record:

1. Actual outgoing mDNS mask, Cast `DEVICE_INFO` mask, Eureka display flag and
   configured streaming-API display header. Keep wire-verified fields separate
   from configuration-only evidence.
2. An actual ordinary-YouTube picker screenshot including the profile row.
3. The visible individual-speaker/TV/group icon, without inferring it from model text.
4. Whether selecting that row produces phone TCP/Cast LAUNCH and app traffic.
5. Whether a media LOAD reaches the silent player, with timestamps for correlation.
6. For a promising individual-speaker candidate, a separate real-output test of
   decoding, audio, title changes, disconnect/reconnect and a YouTube Music regression.

Start with `speaker`, then `video-info-only`, `video-mdns-only`,
`video-eureka-off` and `video-eureka-on` as controls. The latter changes Eureka
display while the outgoing API header still says false. Use
`video-eureka-on-api-on` for the exact four-layer PR #18 capability configuration;
`video-mdns-only-eureka-on-api-on` reproduces the first PR test's configuration
before its DEVICE_INFO correction. This is configuration parity, not a claim
that the author verified each individual HTTP header. Model-only and minimal-bit
profiles can help attribute classification. Group/pair flags, a Nest model or
missing AUDIO_OUT are explicitly unsupported identity diagnostics. The receiver
does not implement those identities/functions; an attractive icon alone does
not make them suitable product settings. A group icon also does not meet the
individual-speaker criterion. Mismatched fields need refresh/reconnect testing
to exclude a temporary stale icon.

The 25 supplied profiles include all 16 combinations of the mDNS VIDEO_OUT
bit, Cast DEVICE_INFO VIDEO_OUT bit, Eureka display and streaming-API display,
plus nine diagnostic model, output-bit and group/pair cases. Each of the eight
original three-field combinations keeps the API display flag false; its
`-api-on` counterpart explicitly sets `api_display=true`. The complete matrix is
[`profiles.json`](profiles.json); it describes test inputs, not verified app results.

`CAST-DEVICE-CAPABILITIES` is an outgoing frontend HTTP header, inherited by
the shared API/media clients. It is separate from local Cast `DEVICE_INFO` and
Eureka discovery. The inspected local icon/selection predicates do not read
that HTTP header; a header-dependent difference would need cloud/session or
post-launch evidence rather than an assumed change to the local picker guard.

If successful native YouTube casting requires TV presentation, record that
result and stop. Do not add a TV toggle or change the default speaker identity.

## Local helper tests

```bash
python3 tools/youtube_capability_lab/test_helper.py
```

The behavioral tests cover 25% initialization, seek/pause/stop/volume,
media-generation isolation and sanitized logs. They do not test Android,
discovery, authentication or real playback. Current investigation results,
including the limits of wire checks, belong in the linked investigation document.
