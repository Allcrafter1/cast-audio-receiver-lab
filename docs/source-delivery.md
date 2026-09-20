# Release source delivery

Source archives are assembled separately from runtime credentials and retained
as assets with the public experimental release. This document records the
reviewed source-delivery scope; it is not a claim of universal compatibility.

## Native AirPlay

`cast-airplay-native-source-v054-release.tar.gz` contains nine immutable source
trees, component/version manifest, notices and an offline build script.
Size/hash and verified candidate binary digest are in
`config/airplay-source-artifact.json`. The extracted source and build recipe
match the successful standalone rebuild (6,121 files compared). Upstream tests
pass. This does not assert byte identity with the original upstream executable
or silently replace the existing runtime. See `airplay-native-source-audit.md`.

## Rust frontend

The manually dispatched `source-review.yml` uses Cargo vendor with Cargo.lock,
preserves crate notices, and requires a frozen release build before uploading
the archive. Build and dependency sources are distinct from the compiler and
system-tool prerequisites. See `build-vendored-vibecast.md`.

Run **35521105935** passed its frozen/offline CLI release build. Downloaded
`vibecast-vendored-source.tar.gz` matches its SHA-256 sidecar:
`411dfcea28df2d73216b180c3cd8c8c1066c49e270b8d9a12dac4634ef47b824`.
The dependency sources and notices are retained; this does not imply that
every dependency applies to every platform or that the complete container's
other source obligations are covered by this Rust archive.

## Python packages

All **31** pinned container wheels match their filenames and SHA-256 values in
the corresponding public PyPI release metadata. All have source distributions.
`config/container-python-source-references.json` records the exact source URLs,
sizes and hashes. It can be refreshed without running package build hooks:

```sh
python tools/python_source_inventory.py \
  config/container-linux-x86_64-cp312.wheels.json \
  new-source-inventory.json --source-archive new-python-sources.zip
```

The checked source ZIP is 33,188,344 bytes, SHA-256
`ec83949c9ef27f743bd08127357467325104e205f75ef15e5bccb52cff75e61d`.
It contains the 31 hash-verified, unopened source distributions and a metadata
record; it is retained with the public release. No package setup/build code
was executed to collect it. Runtime versions have not changed.

**Do not equate a Python sdist with complete native source coverage.** In
particular, Deno's small Python package is a wrapper for a separate executable;
lxml wheels can incorporate native libraries. Their upstream notices and
native build/source identities need separate accounting. The inventory sets
`embedded_native_source_coverage_verified: false` deliberately.

## Debian/base image and remaining review

The reviewed image contains its Debian package list, FFmpeg/mpv build records
and distribution copyright files. The image SBOM records exact package
versions, but scanner `NOASSERTION` fields are neither permission nor a ban.
Final release work must connect the shipped native/base-image components to
their source versions and notices and retain the actual artifact evidence.
Do not close this task simply by relabelling every component GPL, or assume
that one native archive covers the entire image.

Authentication-bundle provenance/availability is a different task, documented
in `bundle-distribution.md`. Source licence notices do not licence that material.
