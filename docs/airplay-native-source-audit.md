# AirPlay native-source evidence (dev17)

The runtime continues to use the already tested airplay-cli v0.5.4 asset.
This audit does not change the deployed executable or declare release clearance.

## What the history establishes

The pinned `libopenssl` proxy is
`ac74d79efc7a702386fcf00d4b7e0a785721a3ed`. Its preceding commit,
[`d8653048bbfaf65b44bcef67c8c66e368b822cde`](https://github.com/philippe44/libopenssl/commit/d8653048bbfaf65b44bcef67c8c66e368b822cde),
introduced the 3.5.4 binaries and selected OpenSSL source
`c1eeb9406b6142148f267594197d853403d10208` (the `openssl-3.5.4` tag).
The next commit changed **only** the OpenSSL gitlink back to
`8ddacec11481a37302c19f4454e23299af399f83`. The Linux x86_64 target files and
build recipe did not change between these two proxy commits.

This supplies a concrete historical association between the shipped archive
and a matching-version source, stronger than inferring source from a version
string alone. It does not prove byte-for-byte reproducibility, absence of local
upstream patches, or complete provenance of all the other linked libraries.

## Recheck without changing a checkout

Use a complete recursive checkout of the pinned airplay-cli revision, including
the proxy's Git history and the OpenSSL tag object:

```sh
python tools/check_airplay_source_evidence.py /path/to/airplay-cli
```

The checker verifies revisions, both historical gitlinks, unchanged target
tree/build recipe, the local libcrypto archive hash and source VERSION.dat.
It reads no private project runtime state. Missing objects or mismatches fail
closed. Pins and evidence status live in
`config/airplay-native-source-evidence.json`.

## Controlled source-build result

The isolated Linux x86_64 reconstruction now builds successfully and passes
upstream `make test` (including RAOP lifecycle, session, AP2 clock/timeline,
artwork and announcement tests) plus `--check`. Run it with:

```sh
bash tools/build_airplay_source_candidate.sh /path/to/airplay-cli /new/build/directory
```

It exports immutable source objects, selects OpenSSL 3.5.4 explicitly and
rebuilds the linked ALAC, mdnssd and libcrypto archives rather than taking their
prebuilt contents. It labels its result `0.5.4-source-candidate`; this is not
the original upstream artifact or a deployed replacement. The tested local
candidate SHA-256 is
`054121676576a7c5a89a02609b96db224a65d9f98cb3fd7c2633b87be3651c79`.
Compiler/platform differences can change that digest; this is not a
byte-for-byte reproducibility claim. No new runtime library is introduced.

The recipe is a development/release-verification path, not a replacement for
the Containerfile's currently pinned upstream executable. Shipping the new
executable requires building against the deployment distribution and repeating
physical acceptance; do not copy a host-built binary into a different libc
environment and assume compatibility.

## Remaining publication work

### Source archive assembled and rebuilt

`tools/package_airplay_source.py CHECKOUT NEW_ARCHIVE.tar.gz` now assembles the
nine immutable component trees used by the controlled build. It excludes
precompiled libraries/build outputs and untracked/modified checkout content,
preserves component notices, and includes a component manifest plus the offline
`build_exported_airplay.sh` recipe. Failed assembly never publishes a partial
archive or overwrites an existing one. No Cast identity material is read.

An actual archive was extracted into a fresh directory and rebuilt without Git
or downloads. Upstream tests and `--check` pass; the binary digest again equals
`054121676576a7c5a89a02609b96db224a65d9f98cb3fd7c2633b87be3651c79`.
This closes the source-collection/rebuild task for this **candidate**. It does
not retroactively prove the original release executable's exact build inputs.
The complete container additionally needs its Rust/Python/Debian source and
notice inventory; this archive does not claim to replace those deliverables.

- Retain the assembled native source archive and its SHA-256 with the release,
  preserving the original pin and reason for the OpenSSL override in the manifest.
- Verify the remaining native dependencies and included notices, not only
  OpenSSL. Do not mistake a complete source tree for proof of which objects were
  actually linked into the release executable.
- Prefer a controlled rebuild to verify the corrected recipe. If the project
  switches from the upstream executable to its own build, retain rollback and
  repeat persistent RAOP, controls, seek, reconnect and AirPlay2 acceptance.
  Do not silently replace the user-confirmed runtime during this audit.

The upstream [build-system explanation](https://github.com/philippe44/cross-compiling#organizing-submodules--packages)
explains the proxy/prebuilt layout. The source correction above is established
by the inspected Git objects, not a promise by that documentation.
