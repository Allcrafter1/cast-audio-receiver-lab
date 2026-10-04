# MPL 2.0 transition and provenance audit — 2026-10-04

## Result and scope

The current product source was reviewed before changing original project files
from `GPL-3.0-or-later` to `MPL-2.0`. The reachable product history contains
commits by the repository owner, AI-assisted `Codex` commits made for the owner,
and dependency/release bots; no additional human code contributor was found.
GitHub's contributor and pull-request lists likewise show only the owner and
automation; the merged pull requests are dependency-action updates. The owner
authorized this relicensing. Third-party material was reviewed separately and
is not covered by that authorization.

This is a source/provenance audit, not legal advice or a guarantee about every
possible copyright doctrine. It records the repository and upstream revisions
actually checked so the conclusion can be reproduced.

## License boundaries verified

- Original product source, tests, tools, project documentation and packaging are
  covered by the root MPL 2.0 license unless specifically excepted.
- Vibecast remains MIT at the maintained fork. Product patch files contain
  changes to that MIT code and remain MIT so they can be reviewed or returned
  upstream. The original MIT text remains in `licenses/Vibecast-MIT.txt`.
- Chromium's Cast channel schema remains BSD-3-Clause and retains its copyright
  and notice in the fork and `licenses/Chromium-BSD.txt`.
- Music Assistant's `airplay-cli` v0.5.4 remains a separate GPLv3 executable,
  launched as a process rather than copied into the Python source. Its exact
  locks, full GPL text, third-party inventory and corresponding-source process
  remain in place. The root MPL license does not alter any of them.
- Deno/V8, OpenSSL, libraop, FFmpeg, mpv, Python and Rust dependencies retain
  their recorded upstream terms. The transition does not turn the existing
  source/SBOM review records into a blanket clearance claim.
- Authentication material is fetched as a separately versioned runtime input;
  it is not committed to this repository or embedded in the normal image and is
  not licensed by the MPL.

## Shanocast review

The comparison used the local research checkout of
[`rgerganov/shanocast`](https://github.com/rgerganov/shanocast) at
`1b57813f2a92c5dbb68c916263127b75e9c8164f`. Its tracked tree contains no
standalone license file. It was therefore treated as unlicensed/all-rights-
reserved material, not as MIT, GPL or otherwise reusable code.

The current product tree and maintained Rust frontend were checked for the
Shanocast patch, source files, embedded certificate/key arrays and signature
tables. None are present. The active frontend is the separately MIT-licensed
Vibecast fork.

`tools/import_shanocast_bundle.py` was also compared with Shanocast's C++ patch.
It is an independently structured Python compatibility tool that:

- reads array data from a path supplied by the user instead of embedding it;
- parses the externally supplied representation;
- reconstructs and verifies certificates with Python cryptography APIs; and
- writes the product's JSON manifest format.

It necessarily shares factual interoperability parameters and field names with
the format it reads (time window, signature size, certificate values and array
identifiers), but no copied C++ implementation block was identified. Its first
known project version is commit
`4364498089034099af86d1192bb6350f144d69e2`; the product import is byte-identical
to that version before this documentation update (SHA-256
`8a38a7df3a810e1caac5d7b81a9657d7c6d3d20323ec0e0bdf50c28ae60ff17e`).
Generated authentication data and any user-supplied upstream checkout remain
outside the product tree and outside the MPL grant.

The supported conclusion is narrow: this dated review found research and format
interoperability, not copied Shanocast implementation code, in the current
release source. It is not represented as a formal clean-room process or an
absolute legal guarantee.

## Compatibility and historical releases

Mozilla documents MPL 2.0 as file-level copyleft and permits MPL-covered files
to be combined with Apache-2.0 files in a larger work. MPL-covered files and
their modifications remain MPL; this change does not promise that Home
Assistant, Music Assistant or another project will accept a contribution.

Tags and release artifacts through `0.6.0-dev21` remain under their published
`GPL-3.0-or-later` grant. The MPL transition starts with `0.6.0-dev22` and does
not revoke or replace rights already granted for old versions.

Primary references:

- [Mozilla Public License 2.0](https://www.mozilla.org/MPL/2.0/)
- [Mozilla MPL 2.0 FAQ](https://www.mozilla.org/MPL/2.0/FAQ/)
- [Music Assistant discussion #2354](https://github.com/orgs/music-assistant/discussions/2354)
