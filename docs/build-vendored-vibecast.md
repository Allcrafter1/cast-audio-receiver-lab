# Building the vendored frontend source archive

The source-review workflow assembles the exact frontend commit recorded in
`config/vibecast-frontend.lock.json`, plus all Cargo.lock dependency sources
using Cargo's standard `vendor` command. Upstream licence files stay beside
their crates. `SOURCE-METADATA.json` records package licences/source identities;
it is an inventory, not a legal compatibility verdict. Dependencies used only
by other workspace members or platforms may be included too.

The top-level frontend remains MIT. The Chromium BSD notice is additionally
placed beside its protocol schema (documentation-only addition to the pinned
source). `SOURCE-PIN.json` identifies the original immutable revision. Private
Cast runtime material, Git history and compiled binaries are not included by
this workflow. Public upstream crate test fixtures may contain test keys; they
are not credentials extracted from a user's runtime.

On Linux x86_64 with Rust **1.98.1**, a C/C++ compiler, CMake and the platform
development headers already installed, extract the archive and run:

```sh
cd vibecast-sources
cargo +1.98.1 build --frozen --release -p vibecast-cli
```

The vendored `.cargo/config.toml` supplies dependencies without registry/git
downloads. `--frozen` also prevents a silent Cargo.lock update. Installing the
compiler/toolchain itself is a separate prerequisite; do not mistake this for a
container image or a universal, cross-platform reproducibility guarantee.

The resulting executable is `target/release/vibecast` unless CARGO_TARGET_DIR is
set. Actual receiver operation still needs its separately supplied runtime
bundle and output adapters. This archive covers the Rust frontend, not the
Python application, AirPlay component, or Debian packages in the full image.

The workflow validates a release build before uploading a private review
artifact. Retain the final verified archive alongside a release; the temporary
seven-day CI artifact is not a permanent corresponding-source distribution.
