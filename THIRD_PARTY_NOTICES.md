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
| [Music Assistant airplay-cli](https://github.com/music-assistant/airplay-cli) and contributors | Actual persistent AirPlay output executable | v0.5.4, commit `431c5c582eef9307c4e39c50a0ea65e970bc1128`; combined binary declared GPLv3 by upstream. Exact x86_64 artifact hash in `config/cliairplay-linux-x86_64.lock.json`; preserved notices in `licenses/airplay-cli-THIRD_PARTY_NOTICES.md`. |
| [Chromium](https://chromium.googlesource.com/chromium/src/), The Chromium Authors | `cast_channel.proto` envelope schema incorporated through Vibecast | File copyright 2014; BSD-3-Clause notice in `licenses/Chromium-BSD.txt`. This protocol file is not the Google Cast SDK. |
| [philippe44/libraop](https://github.com/philippe44/libraop), Shiro Ninomiya and other authors listed upstream | RAOP/transport work incorporated by airplay-cli, not independently reimplemented here | Retain airplay-cli's full third-party notices and component texts; see caveat below. |
| [FFmpeg](https://ffmpeg.org/) contributors | Audio decode/PCM normalization and bounded artwork conversion | External host executable; exact enabled-component/build license must be inventoried for the shipped artifact. No single blanket license claim for every FFmpeg build. |
| [mpv](https://github.com/mpv-player/mpv) contributors | Local audio output and decoder-owned position/EOF/status via IPC | External host executable; retain the actual distribution's license/build information. |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp), EJS and Deno contributors | Checked YouTube audio-source extraction and its JavaScript support stack | Direct version pins in `config/youtube-extractor-requirements.txt`; complete artifact/transitive license audit still open. |
| [async-upnp-client](https://github.com/StevenLooman/async_upnp_client), Steven Looman and contributors | DLNA/UPnP MediaRenderer discovery, metadata and control | Pinned to v0.48.1; Apache-2.0. One older Samsung tested; wider interoperability remains unverified. The output-local HTTP/FFmpeg relay is project code using the already credited aiohttp/FFmpeg components. |
| [SoCo](https://github.com/SoCo/SoCo), SoCo contributors | Experimental direct Sonos output and control | Pinned to v0.31.2; MIT. Hardware interoperability remains unverified. |
| AirReceiver | Purchased reference receiver used in interoperability comparisons on user-owned Android devices | Reference testing, not an open-source dependency. Proprietary app/package and private credentials are not shipped by this repository. |

The Shanocast README credits Google's Open Screen as its foundation. Our active
frontend is Vibecast, not a claim that this repository contains or maintains a
complete Open Screen runtime. Additional individual research articles mentioned
during discussion must have their exact contribution/link verified before being
added as implementation credits; do not invent attribution or endorsements.

## AirPlay native licence evidence and remaining release check

Current maintained Vibecast build input is commit
`e67628fa72550095f92197550d60d8e94c503d4e`, recorded in
`config/vibecast-frontend.lock.json`. It incorporates the previously separate
bridge overlay and corrects the fork README. The older commit in the provenance
table remains the integration base; MIT notices remain unchanged.

The airplay-cli v0.5.4 notice records mixed component licences. Its statement that
libraop has no licence is now stale: upstream commit
`4fe461a809eadd5230e3b587a3b3c948f90d9617` adds Philippe's MIT statement while
explicitly preserving third-party conditions. We retain both the unmodified
airplay-cli notice and that newer evidence in `licenses/`. Its pinned libraop
revision is still `81c2182649da8645ac2a58b78e9f370c79a4165b`; no silent submodule
upgrade or blanket relicensing is implied.

The notice's OpenSSL version is also stale for the inspected x86_64 artifact:
the pinned prebuilt `libcrypto.a` reports **OpenSSL 3.5.4** when queried by a
minimal linked `OpenSSL_version()` program; its headers match. The downloaded
release binary contains `3.5.4` and OpenSSL 3 provider symbols. OpenSSL 3 uses
Apache-2.0, rather than the notice's 1.1.1u OpenSSL/SSLeay terms. Preserve the
upstream notice as evidence, with this correction alongside it.

The vendored OpenSSL *source submodule*, however, still points to a 1.1.1-era
revision. Close this source/prebuilt mismatch before declaring corresponding
source complete. This is a concrete provenance task, not proof of a blanket
GPL/OpenSSL conflict. RAOP/AES GPL-2.0-or-later lineage, GPL-3.0 mdnssd and other
MIT/BSD/Apache components retain their individual notices. Publish exact
recursive corresponding source and build instructions with any binary release;
GitHub's automatic airplay-cli source archive omits submodules.

The dev17 audit additionally checked `libopenssl/.gitmodules`: its branch hint
is `openssl-3.5.4`, while its actual gitlink remains
`8ddacec11481a37302c19f4454e23299af399f83`. A normal recursive checkout uses
the gitlink, not the hint. Its build script also skips existing static archives.
Consequently, merely including that recursive checkout and invoking its build
script does not yet establish matching source for the shipped library. Resolve
this using documented upstream build provenance or a verified source-built
artifact before distributing a project binary/image.

Follow-up history inspection found the matching 3.5.4 source gitlink in the
immediately preceding proxy commit, with unchanged Linux archive/build files.
See [the evidence and repeatable check](docs/airplay-native-source-audit.md).
This narrows the source correction required; it is not yet a verified rebuild
or complete native dependency clearance.

## Python runtime dependencies

The runtime wheel/source reference inventory is now checked against exact PyPI
file hashes: `config/container-python-source-references.json`. All 31 container
runtime wheels have source distributions, collected in the private release
source archive. This is not proof of embedded native library coverage.

In particular, **Deno is not just its Python launcher**. The exact executable
from the reviewed OCI image reports Deno 2.9.6, V8 15.0.245.2-rusty and
TypeScript 6.0.3. The upstream Deno v2.9.6 MIT text is preserved in
`licenses/Deno-2.9.6-MIT.txt`, from
https://github.com/denoland/deno/blob/v2.9.6/LICENSE.md . Retain its embedded
third-party notices as a separate native-runtime review task; the Python
wrapper's licence alone is not a complete Deno/V8/TypeScript inventory.

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
