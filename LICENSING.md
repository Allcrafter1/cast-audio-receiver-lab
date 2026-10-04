# Licensing scope

Cast Audio Receiver Lab is a mixed-license repository and distribution. The
root [`LICENSE`](LICENSE) applies the **Mozilla Public License 2.0
(`MPL-2.0`)** to original project material unless a file or the table below
says otherwise. The project does not use the MPL's “Incompatible With
Secondary Licenses” notice.

Project-owned source files use `SPDX-License-Identifier: MPL-2.0` headers where
their format permits it; the root license and this scope document cover the
remaining project-owned files.

This change applies to the source at `0.6.0-dev22` and later. Immutable tags,
release assets and source copies published before that release remain available
under the `GPL-3.0-or-later` terms with which they were published. Replacing the
root license does not withdraw those earlier grants.

## File and component boundaries

| Paths or component | License/status |
| --- | --- |
| Original Python product code, historical Python research code, tests, project tools, packaging, workflows, project documentation and project artwork | `MPL-2.0`, unless a more specific notice is present |
| `patches/vibecast-*.patch` and the maintained [Vibecast fork](https://github.com/Allcrafter1/vibecast) | Upstream **MIT** license, including our fork modifications; preserve `licenses/Vibecast-MIT.txt` |
| Chromium `cast_channel.proto` carried by the Vibecast fork | **BSD-3-Clause** with Chromium's copyright and notice; preserve `licenses/Chromium-BSD.txt` |
| Files under `licenses/` | The license/notice they reproduce; they are evidence for the named third-party work, not MPL relicensing declarations |
| Music Assistant `airplay-cli` executable and corresponding source archive | **GPL version 3** combined binary with separately recorded incorporated-component terms; preserve `licenses/airplay-cli-GPL.txt` and `licenses/airplay-cli-THIRD_PARTY_NOTICES.md` |
| Other dependencies and host executables | Their own upstream terms, versions and notices as recorded in `THIRD_PARTY_NOTICES.md`, package metadata, locks, SBOMs and source artifacts |
| Authentication bundles, credentials and user state | Not project source and not granted rights by the MPL; none are stored in this repository or normal image |

The container is an aggregate containing MPL project files and separately
licensed programs and libraries. Its OCI license annotation therefore uses
`NOASSERTION` rather than incorrectly describing the entire image as MPL or
GPL; the additional `io.cast-audio-receiver.project-license=MPL-2.0` annotation
identifies the original project layer. The complete notices are installed under
`/usr/share/doc/cast-audio-receiver/` and summarized in
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Reuse and contributions

MPL-licensed files may be combined with Apache-2.0, MIT, BSD or proprietary
files in a larger work while modifications to the MPL-covered files remain
subject to MPL 2.0. This does not relicense an MPL file as Apache-2.0 and does
not override another project's contribution policy.

Contributions to original project files are accepted under MPL 2.0. Changes to
the Vibecast fork or its patch series are accepted under that codebase's MIT
license so fixes can continue to flow upstream. Do not submit code copied from
unlicensed sources or remove third-party copyright and license notices.

The provenance and Shanocast-specific review for this transition is recorded in
[`docs/licensing-audit-2026-10-04.md`](docs/licensing-audit-2026-10-04.md).
