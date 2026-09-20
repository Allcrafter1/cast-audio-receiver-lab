# Acknowledgements and third-party inventory

This project would not have been possible without the upstream implementations,
protocol research and maintenance work below. Thank you to their authors and
contributors. Our glue code and practical testing do not replace that work, and
no upstream author is implied to endorse or support this experiment.

This is a source-based inventory, **not a completed redistribution clearance or
full transitive license audit**. Do not interpret the project's GPL declaration
as relicensing third-party material or credentials.

## Main implementation and research foundations

| Project / author | Actual role here | Recorded source / license status |
| --- | --- | --- |
| [Vibecast](https://github.com/emilsvennesson/vibecast), Nils Emil Svensson and contributors | Active Cast frontend, application/player architecture and YouTube implementation, maintained in our [reviewable fork](https://github.com/Allcrafter1/vibecast/commit/f28befe02fe930db300294d6bf49cdf5fec5a747) | Fork commit `f28befe02fe930db300294d6bf49cdf5fec5a747`, based on upstream `b4616f8f399be706a1409ed21922aa2df892e303`; MIT. Preserve upstream copyright/license; copy in `licenses/Vibecast-MIT.txt`. |
| [Shanocast](https://github.com/rgerganov/shanocast), rgerganov and contributors | Earlier compatibility research, public precomputed-signature format and importer reference | Local research checkout `1b57813f2a92c5dbb68c916263127b75e9c8164f`; README links [the author's explanation](https://xakcop.com/post/shanocast/). No standalone license file found in that checkout; do not assume the entire repository or embedded material is MIT/GPL. |
| [Music Assistant airplay-cli](https://github.com/music-assistant/airplay-cli) and contributors | Actual persistent AirPlay output executable | v0.5.3, commit `bdee878e18fe6e859830ed20499fc87497ae53a1`; combined binary declared GPLv3 by upstream. Exact x86_64 artifact hash in `config/cliairplay-linux-x86_64.lock.json`. |
| [philippe44/libraop](https://github.com/philippe44/libraop), Shiro Ninomiya and other authors listed upstream | RAOP/transport work incorporated by airplay-cli, not independently reimplemented here | Retain airplay-cli's full third-party notices and component texts; see caveat below. |
| [FFmpeg](https://ffmpeg.org/) contributors | Audio decode/PCM normalization and bounded artwork conversion | External host executable; exact enabled-component/build license must be inventoried for the shipped artifact. No single blanket license claim for every FFmpeg build. |
| [mpv](https://github.com/mpv-player/mpv) contributors | Local audio output and decoder-owned position/EOF/status via IPC | External host executable; retain the actual distribution's license/build information. |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp), EJS and Deno contributors | Checked YouTube audio-source extraction and its JavaScript support stack | Direct version pins in `config/youtube-extractor-requirements.txt`; complete artifact/transitive license audit still open. |
| [async-upnp-client](https://github.com/StevenLooman/async_upnp_client), Steven Looman and contributors | Experimental direct DLNA/UPnP MediaRenderer output | Pinned to v0.48.1; Apache-2.0. Hardware interoperability remains unverified. |
| [SoCo](https://github.com/SoCo/SoCo), SoCo contributors | Experimental direct Sonos output and control | Pinned to v0.31.2; MIT. Hardware interoperability remains unverified. |
| AirReceiver | Purchased reference receiver used in interoperability comparisons on user-owned Android devices | Reference testing, not an open-source dependency. Proprietary app/package and private credentials are not shipped by this repository. |

The Shanocast README credits Google's Open Screen as its foundation. Our active
frontend is Vibecast, not a claim that this repository contains or maintains a
complete Open Screen runtime. Additional individual research articles mentioned
during discussion must have their exact contribution/link verified before being
added as implementation credits; do not invent attribution or endorsements.

## AirPlay upstream caveat to resolve before release

The inspected airplay-cli v0.5.3 `THIRD_PARTY_NOTICES.md` explicitly documents
mixed component licenses and missing explicit upstream grants for libraop
`pairing.cpp` / `bplist.cpp`. It also identifies bundled OpenSSL in static
release binaries. Preserve that notice and investigate the actual shipped build
and applicable obligations before distributing a combined image. Merely choosing
GPLv3 for our code does not complete this audit. Do not silently remove ambiguous
notices or describe all incorporated code as uniformly Apache/MIT.

## Python runtime dependencies

The exact selected wheel filenames, hashes and declared license metadata for
the tested CPython 3.12 and 3.13 environments are recorded separately in
`config/management-linux-x86_64-cp312.wheels.json` and the corresponding cp313
inventory. Principal dependencies:

| Distribution | Declared license in inspected package metadata |
| --- | --- |
| cryptography 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| pyOpenSSL 26.4.0 | Apache License, Version 2.0 |
| websockets 17.1 | BSD-3-Clause |
| zeroconf 0.151.3 | LGPL-2.1-or-later |
| aiohttp 3.14.3 | Apache-2.0 AND MIT |

The wheel inventory also lists their selected transitive runtime packages.
These summaries are not substitutes for the actual bundled license texts.
Rust's Cargo.lock and airplay-cli's incorporated native libraries require their
own complete inventory. Host FFmpeg/mpv and build tools are separate again.

## Release checklist

- Retain original copyright/license texts for every shipped component.
- Identify exact corresponding source, modifications and build recipe for each
  binary; meet applicable source/notice requirements for the chosen artifact.
- Audit repository history and built archives for private data and secrets.
- Resolve incomplete/ambiguous source license records before publishing artifacts.
- Include [project origin / AI disclosure](docs/PROJECT-ORIGIN.md), experimental
  limits and contribution guidance without claiming independent review.
