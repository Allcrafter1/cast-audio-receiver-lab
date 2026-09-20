# Cast Audio Receiver Lab

Cast **YouTube Music** and ordinary Cast media to outputs that Google does not
normally expose as Cast speakers. Each configured local, AirPlay or DLNA output
appears as its own audio receiver in Android and Home Assistant.

We built this because YouTube Music on Android has no useful AirPlay path, while
many perfectly good amplifiers and speakers do. What began as a protocol
experiment is now a working Linux receiver, output bridge and Home Assistant
App with one small management interface.

> [!WARNING]
> This is experimental interoperability software, not an official Google,
> Apple, Home Assistant or Music Assistant product. Cast authentication can be
> revoked or changed independently of this code. Use it on a trusted LAN and
> keep a known-working release available.

## Install in Home Assistant

[![Add the Cast Audio Receiver repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FAllcrafter1%2Fcast-audio-receiver-lab)

If the button does not open your instance, add this repository manually under
**Settings → Apps → App store → Repositories**:

```text
https://github.com/Allcrafter1/cast-audio-receiver-lab
```

Install **Cast Audio Receiver Lab**, start it and select **Open Web UI**. The
same interface is also available on your trusted LAN at:

```text
http://HOME_ASSISTANT_IP:8788
```

Port `8788` is the default and can be changed in the App configuration. The
current release supports `amd64`; ARM is not release-validated yet.

## What it can do

- Create a stable, audio-only Cast speaker for every configured output.
- Receive YouTube Music with play/pause, seek, skip, volume, queue progression,
  metadata and artwork feedback.
- Receive direct HTTP(S) media, radio and local/TTS URLs through the Cast
  Default Media Receiver path used by Home Assistant.
- Play locally with mpv, forward to AirPlay with Music Assistant's
  `airplay-cli`, or send to compatible DLNA renderers.
- Discover AirPlay and DLNA targets, keep routes across restarts and manage them
  from one LAN/ingress interface.
- Report redacted health and support information without including credentials,
  target addresses or signed media URLs.

Sonos output is implemented but has only mocked coverage, not a real-hardware
acceptance test. Spotify Cast, Bluetooth and Google Home speaker groups are not
goals of this release. Spotify already has Spotify Connect; Google Home does not
adopt this experimental device identity into native groups.

## Why this is technically unusual

A Cast receiver is more than an HTTP media player. It must advertise the right
speaker capabilities over mDNS, establish the Cast V2 channel, pass device
authentication, launch the application requested by the sender, translate its
control model and continuously report real output state back to the phone.

The project combines a maintained fork of
[Vibecast](https://github.com/emilsvennesson/vibecast) with a Python product
layer and real output transports. The important part is not merely obtaining an
audio URL: the phone must continue to see a coherent Cast session while mpv,
AirPlay or DLNA is actually doing the playback.

```text
YouTube Music / Home Assistant / another DMR sender
                       │
                       ▼
       maintained Vibecast frontend (Rust)
        discovery · TLS/auth · Cast sessions
        YouTube/Lounge · Default Media Receiver
                       │
             player protocol v2 (loopback)
                       │
                       ▼
          one Python adapter per speaker
             ├─ mpv → local audio
             ├─ FFmpeg → PCM → airplay-cli
             ├─ HTTP relay/remux → DLNA
             └─ direct media URL → Sonos (experimental)
```

Read [How it works](docs/how-it-works.md) for the story behind discovery,
authentication, YouTube sessions, the output bridge, DIAL and the limits of the
current approach. [Current architecture](docs/architecture-current.md) is the
short maintainer map.

## Current compatibility

| Path | Current evidence |
| --- | --- |
| YouTube Music → local audio | Extensively tested during development and through the published HA App. |
| YouTube Music → AirPlay | Tested with the legacy AirReceiver reference target, including persistent sessions and controls. HomePod/native AirPlay 2 and Yamaha hardware still need acceptance tests. |
| Home Assistant direct media / radio | Tested through the Default Media Receiver path. This does not imply support for every Cast app or DRM service. |
| DLNA | Tested on an older Samsung TV, including its connection-approval flow; renderer compatibility still varies. |
| Sonos | Implemented with deterministic tests; real hardware remains unverified. |
| Parallel outputs / small devices / ARM | Useful community test and contribution areas, not release claims. |

See the [working plan](docs/WORKING-PLAN.md) for the distinction between
implemented, automated-tested, deployed and user-confirmed work.

## Authentication and first start

The repository and container image contain no embedded Cast credentials. On a
clean first start, the pinned release manifest downloads a separately versioned
experimental authentication bundle, verifies its exact size and SHA-256 digest,
and stores it privately in persistent App state. A local replacement bundle can
be configured instead, and existing state is never silently overwritten.

That separation makes the material replaceable and withdrawable; it does not
make the mechanism official or durable. A sender update, revocation or expiry
can stop it working. See [bundle distribution](docs/bundle-distribution.md) and
the authentication section in [How it works](docs/how-it-works.md).

## Container and native installs

The published `amd64` image is:

```text
ghcr.io/allcrafter1/cast-audio-receiver:0.6.0-dev18
```

It needs host networking for Cast/mDNS and target discovery, plus persistent
`/data` storage. Native source installs additionally need the maintained Rust
frontend and runtime tools. Follow [Installation and deployment](docs/installation.md)
rather than starting the individual processes by hand.

## Development and maintenance

```bash
python -m pip install -e '.[youtube,dlna,sonos]'
PYTHONPATH=src:. python -m unittest discover -s tests -v
```

Useful maintainer documents:

- [Documentation map](docs/README.md)
- [Testing and hardware acceptance](docs/TESTING.md)
- [Maintenance, updates and support bundles](docs/maintenance.md)
- [Reconstructing the maintained Vibecast source](docs/source-reconstruction.md)
- [Release checklist](docs/RELEASE-CHECKLIST.md)
- [Credits and third-party licences](THIRD_PARTY_NOTICES.md)

Python runtime locks include reviewed wheel and source inventories and are
updated as one unit; a requirements-only bot bump is intentionally not enough.
Protocol and transport updates also need targeted regression tests.

## Origin, licence and contributions

This project would not exist without Vibecast, Shanocast and its research,
Music Assistant's `airplay-cli`, FFmpeg, mpv, yt-dlp, Chromium's published Cast
protocol sources and the researchers who documented Cast device authentication.
The exact relationship and licences are recorded in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Attribution does not imply
endorsement.

Original project code is **GPL-3.0-or-later**; third-party components retain
their own copyrights and licences. The project does not use Google's official
Cast SDK or a receiver registered in the Cast developer console.

Much of the implementation was developed collaboratively with GPT/Astra and
other AI coding assistance. The initiator began with almost no programming
experience; requirements, architecture and behavior were worked out together
and then tested repeatedly on real devices. Experienced review and contributions
are very welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and never attach
authentication bundles, keys, account tokens or signed media URLs to an issue.
