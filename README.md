# Cast Audio Receiver Lab

An experimental Linux **Cast-audio receiver and output bridge**: receive
YouTube Music or supported direct-media Cast loads and play them locally or
forward them to AirPlay. Each configured output appears as its own speaker.
One web interface manages their names, targets and lifecycle.

This is not an official Google receiver, a universal Cast implementation, or a
Music Assistant integration. Google Home adoption/groups and Spotify Cast are
not supported. Service changes or revocation can break the experimental Cast
device identity independently of software updates.

## What comes from where?

This project is **built on Vibecast**, not a renamed independent implementation
of its protocol work. [Nils Emil Svensson's MIT-licensed Vibecast](https://github.com/emilsvennesson/vibecast)
supplies the Rust Cast frontend, discovery/session architecture, external-player
protocol and original YouTube application. Our maintained fork adds audio-speaker
capabilities, YouTube playback/queue/feedback changes, a generic Default Media
Receiver, artwork/status corrections and an internal-only player bridge.
Source pins and reconstructible patches record these changes.

This repository adds the Python product layer: supervision, persistent speaker
management, local mpv output, persistent AirPlay integration, experimental
DLNA/Sonos outputs, square-artwork processing, diagnostics, tests and packaging.
Music Assistant's **airplay-cli**, not our code, implements the AirPlay sender.
FFmpeg decodes audio to PCM; yt-dlp resolves checked YouTube audio sources.

See [architecture](docs/architecture-current.md),
[project origin](docs/PROJECT-ORIGIN.md) and
[credits and component licences](THIRD_PARTY_NOTICES.md). Thank you to all the
upstream authors and researchers. Attribution does not imply endorsement.

## Audio and control flow

```text
YouTube Music / supported direct-media Cast sender
    → maintained Vibecast frontend (Rust)
    → internal player bridge (WebSocket, loopback :8010)
    → one Python adapter per configured speaker
        ├─ mpv → local sound device
        ├─ FFmpeg → PCM → airplay-cli → AirPlay receiver
        ├─ DLNA: direct compatible HTTP, or local HTTP/remux/MP3 compatibility
        └─ direct media URL → Sonos (experimental)
```

Commands travel toward outputs; actual playback/volume/position and end/error
events travel back. Artwork processing is separate from audio. The manager
serves square covers to Cast/Home Assistant when its advertised artwork address
is reachable. Accepting URLs does not make proprietary service apps/DRM work.

The management UI is the **only user-facing interface**. It opens directly on
the trusted LAN, without a login, on configurable port **8788**, or through HA
ingress. Do not expose it to the Internet. The inherited Shaka browser player is
disabled in normal builds; its WebSocket/manifest/licence routes remain internal.

## Current status

| Path | Evidence / limitations |
| --- | --- |
| YouTube Music → local / legacy AirPlay | Earlier releases tested extensively on laptop and Redmi reference receiver; review candidate requires physical regression acceptance. |
| Default Media Receiver | User-tested Home Assistant direct media. Not a promise of all Cast apps, DRM or Cast queue support. |
| Home Assistant App | Experimental amd64 source install, ingress and persistence tested. User confirmed physical local output and embedded UI after the dev14 fixes. |
| HomePod / native AirPlay 2 / Yamaha | Upstream sender paths exist; physical acceptance outstanding. |
| DLNA | Discovery and local HTTP compatibility implemented. User confirmed YouTube Music on one older Samsung, alongside direct MP3 and HA-transcoded WebM/Opus tests; wider hardware coverage remains open. See [DLNA notes](docs/dlna.md). |
| Sonos | Implemented with library and mocked tests; real hardware unverified. External renderers cannot pull internal-only manifest URLs. |
| ARM / simultaneous targets / small devices | Not release-validated. |

This is an **experimental pre-release**. The core paths are usable and tested,
but hardware coverage is deliberately limited and the Cast authentication path
can be revoked independently of this code. The
[working plan](docs/WORKING-PLAN.md) distinguishes implemented, automated-tested,
deployed and user-confirmed work. airplay-cli v0.5.4 is the update candidate,
not evidence of tested HomePod compatibility.

## Install and configure

See [installation](docs/installation.md), [packaging](docs/packaging.md) and the
[current runbook](docs/current-runbook.md). A native source install needs the
frontend binary, runtime tools and valid user-supplied authentication material:

```bash
cast-audio-receiver --frontend /path/to/vibecast \
  --data-dir /var/lib/cast-audio-receiver --web-port 8788 \
  --certs /private/path/certs.json
```

Open the LAN URL to add, rename, disable or delete outputs. HA uses the same
runtime with ingress and a configurable LAN port. The published amd64 image is
`ghcr.io/allcrafter1/cast-audio-receiver:0.6.0-dev18`; see the installation
guide before deploying this experimental release.

Authentication material is **not committed to source or embedded in images**.
On a clean first start the pinned release manifest downloads the separately
published experimental bundle once, verifies its size and SHA-256 digest and
stores it privately. Existing state is never silently replaced and a local/BYO
bundle remains supported. See [bundle distribution](docs/bundle-distribution.md).
Separate distribution improves management/withdrawal, not the underlying legal
or revocation position.

The code does not use Google's official Cast SDK or a receiver registered in its
developer console. This independently implemented protocol path does not mean
Google/YouTube/Play service terms or reference-app conditions are irrelevant.

## Development, maintenance and reporting

```bash
python -m pip install -e '.[youtube,dlna,sonos]'
PYTHONPATH=src:. python -m unittest discover -s tests -v
```

See [testing](docs/TESTING.md), [maintenance](docs/maintenance.md),
[source reconstruction](docs/source-reconstruction.md) and
[release checklist](docs/RELEASE-CHECKLIST.md). Dependabot/upstream-watch identify
updates; locks record selected artifacts. Protocol updates are reviewed, not
silently installed into working systems.

Use the redacted support summary plus expected/observed behavior. Never post
keys, bundles, pairing/account credentials or signed media URLs. Historical
[Python receiver research](research/legacy_python_receiver/README.md) is preserved
outside normal runtime; its commands are not current installation instructions.

## Licence and contributions

Original product code: **GPL-3.0-or-later**. Third-party code retains its own
copyright/licence, including Vibecast MIT and Chromium protocol BSD notices.
See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and
`licenses/`. A code licence does not grant rights to unrelated credentials.
Release assets retain the reviewed source and notice inventories; this remains
an experimental project rather than a claim of universal compatibility.

Much of the code was developed collaboratively with **GPT/Astra and other AI
coding assistance**. The initiator had almost no programming experience;
requirements and architecture were discussed together and tested on real
devices. This is not a substitute for experienced independent review.
Contributions and critical reviews are welcome: [CONTRIBUTING.md](CONTRIBUTING.md).
No endorsement from Google, Apple, Vibecast or Music Assistant is implied.
