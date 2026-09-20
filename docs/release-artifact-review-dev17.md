# dev17 release artifact review

## Verified, 2026-09-20

The main project is still private. Candidate source commit:
`4a2ae2bef8add95d6687e49a84bedf756c185264`.

- Ordinary CI run **35519362352**: all jobs passed, including Rust, Python
  3.11/3.12/3.13 and the container build.
- Manual private artifact run **35519446102**: passed, no registry push.
- Downloaded OCI archive: checksum sidecar verified; all **26** blob hashes
  verified without extracting or executing layers. Referenced layer/config
  sizes checked where present.
- Image manifest:
  `sha256:ed309583fdcc2bcd8617b9d8bdbdee34c9d988bb7dbc99d6f1710b4665299b56`.
- Embedded SPDX inventory and SLSA provenance v1 both reference that image.
  The inventory has **352 package records**, not necessarily 352 distinct
  applications: scanners can report one component in multiple package systems.

Repeat the local read-only check after downloading the private review artifact:

```sh
sha256sum --check cast-audio-review.oci.tar.sha256
python tools/inspect_oci_review.py cast-audio-review.oci.tar --summary --verify-blobs
```

The GitHub artifact expires after seven days. A public release must retain its
own immutable evidence; do not treat this temporary workflow artifact as a
public installation mechanism or a permanent source archive.

## What the inventory does and does not establish

Detected versions include Debian FFmpeg `7:5.1.9-0+deb12u1`, mpv `0.35.1-4`,
Python `3.12.14`, yt-dlp `2026.8.19`, yt-dlp-ejs `0.8.0` and Deno `2.9.6`.
Some entries have `NOASSERTION` licence metadata. This means the scanner did
not establish a licence, not that the component has no licence or cannot ship.
Inspect the actual preserved copyright notices and source package records.

The separately copied Vibecast and cliairplay executables are **not reliably
covered by this automatic package inventory**. Their source pins, native
dependencies, notices and build recipes must be included explicitly. Likewise,
SBOM presence does not prove corresponding source completeness, absence of
secrets, signature authenticity, lack of vulnerabilities or hardware acceptance.

## Remaining release work, not new feature requests

1. Assemble native corresponding-source/notice deliverables with the explicit
   OpenSSL source correction described in `airplay-native-source-audit.md`.
   The controlled source build already passes; the runtime still uses the
   tested upstream binary. Do not silently swap it solely for this audit.
2. Finalize the separate authentication-bundle release. The importer and
   private inventory exist, but no real public asset, trusted manifest pin or
   default acquisition path exists yet. The current HA installation succeeds
   because its bundle was supplied separately. Source-code licence declarations
   do not establish rights to third-party authentication material.
3. Once delivery inputs are settled, test the intended published image's
   installation, update and rollback while preserving route IDs and user state.

These items are distinct from later real-hardware coverage and from the owner's
accepted historical, non-credential discovery identifiers. Do not re-open that
privacy decision or hide distribution gaps behind a generic green CI badge.
