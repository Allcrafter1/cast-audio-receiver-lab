# Native Cast audio frontend

**Historical investigation.** The early patch/build commands and authentication
failure below describe the September 12 prototype, not the current working
receiver. Use [current-runbook.md](current-runbook.md) and the complete source
snapshot documented in [source-reconstruction.md](source-reconstruction.md).
Do not apply the old patch sequence to an existing working tree.

The product path uses Vibecast as the upstream CastV2, device-auth, app and
YouTube implementation. `cast-vibecast-player` is our small external-player
adapter. It registers one named output with Vibecast, receives normalized
load/play/pause/seek/stop/volume commands and sends player state back.

Pinned upstream revision: `b4616f8f399be706a1409ed21922aa2df892e303`.

## Authentication bundle

Shanocast publishes one fixed peer key and 795 SHA-256 device-auth signatures
for deterministic two-day TLS certificates from 2023-08-15 through 2027-12-21.
Generate a Vibecast manifest from a local Shanocast checkout:

```bash
python3 tools/import_shanocast_bundle.py \
  third_party/shanocast/shanocast.patch \
  .state/vibecast/certs.json
```

The importer recreates each TLS certificate byte-for-byte and verifies every
signature against the manufacturing certificate before writing output. The
result contains authentication/private material and is intentionally ignored by
Git. It is replaceable as one file when a newer capture set becomes available.

## Build and run

Build the pinned Vibecast source and apply the small product patch:

```bash
git -C third_party/vibecast checkout b4616f8f399be706a1409ed21922aa2df892e303
git -C third_party/vibecast apply ../../patches/vibecast-audio-receiver.patch
cargo build --manifest-path third_party/vibecast/Cargo.toml -p vibecast-cli --release
```

The patch changes the Cast mDNS capability to the value observed from a current
Nest Audio (`ca=199428`), uses the configured player name verbatim and preserves
the replay response by not attaching a newly fetched CRL. Copy
`config/vibecast-audio.toml` into the runtime data directory as `config.toml` so
Eureka and streaming API capability fields also report audio-only operation.

Start Vibecast, then the local mpv adapter:

```bash
third_party/vibecast/target/release/vibecast \
  --certs "$PWD/.state/vibecast/certs.json" \
  --data-dir "$PWD/.state/vibecast/runtime" \
  --model "Audio Speaker" \
  --bind-host 0.0.0.0

python3 -m pip install -e '.[bridge]'
cast-vibecast-player \
  --bridge ws://127.0.0.1:8010/player \
  --name "Audio Lab Laptop" \
  --player-command 'mpv --no-video --audio-display=no {url}'
```

The player name produces a stable player ID, so restarting does not create an
ever-growing sequence of Cast devices. An AirPlay backend will replace mpv at
the same player boundary; Cast authentication and YouTube handling remain
unchanged.

## Live verification and remaining auth failure

On 2026-09-12 the user confirmed the speaker icon after version 0.4.2 aligned
`GET_DEVICE_INFO.deviceCapabilities` with mDNS (`199428`). Stock sender
connections still close after the auth challenge, before any app launch.
Certificate-only signature verification does not establish nonce binding,
certificate-chain trust, or acceptance by Google Cast senders. Revocation has
not been established as the cause.

For diagnosis, apply `patches/vibecast-auth-diagnostics.patch` to the pinned
upstream checkout and rebuild. This logs the requested hash/signature algorithms
and nonce length only. Hash 0 is SHA-1 and 1 is SHA-256. The imported public
bundle contains SHA-256 signatures in both manifest slots, so a SHA-1 request
would currently receive incorrectly labelled signature material; determine the
actual sender request before drawing conclusions from an independent SHA-256
probe. The optional patch does not change authentication responses.

The diagnostic build observed SHA-256 / PKCS1v15 and a 16-byte challenge nonce.
On the USB-connected Redmi (private hotspot address omitted), YouTube Music sender
logs at 10:19 on 2026-09-12 repeatedly reported Cast socket status 2289 for
Audio Lab Laptop. The public CastStatusCodes reference did not identify that
code. Discovery's separate null-nonce/RAT warnings do not establish the cause
of the authenticated connection failure.

For the next sender capture, temporary Android `log.tag` overrides were set
to VERBOSE for DeviceAuthChannel, CastSocket, CastSocketConnection and
CastDeviceController. All four properties were initially empty. Restore each
to an empty string after capture; no persistent properties or app data are
changed. This may or may not enable additional logging in the installed GMS
build.

After the 10:24:35 and 10:24:40 retries, all four logging overrides were restored
to empty. No additional auth rejection detail appeared; both attempts again
reported 2289. Receiver logs confirm SHA-256/PKCS1v15 and a 16-byte nonce from
the same private sender address. A concurrent GMS connection to the AirReceiver device reported
connected, but this was not a controlled YouTube Music playback comparison.

The installed DynamiteModulesC APK was copied read-only to ignored diagnostic
storage. `tools/find_dex_status.py` inspected its three DEX files and found no
direct integer-constant instruction for 2289. This limited scan does not cover
computed codes, switch-table mappings or native libraries and does not identify
the error. No APK modifications were made.
