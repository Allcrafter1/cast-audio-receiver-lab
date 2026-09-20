# Packaging design

## One runtime, three delivery forms

`cast-audio-receiver` is the product entrypoint. It supervises the native Rust
frontend and the Python manager/output adapters. Native Linux services, the OCI
image and Home Assistant must invoke this same entrypoint; none may grow a
separate playback implementation.

The Home Assistant App maps `/share` read-only and defaults the replaceable
authentication input to `/share/cast-audio-receiver/certs.json`. This keeps
private material out of the image, Git history, web UI and diagnostics while
still allowing rotation without rebuilding the receiver.

The `Containerfile` is the first pinned `linux/amd64` build recipe. It builds
the maintained Vibecast source, verifies the downloaded Music Assistant
`cliairplay` v0.5.4 candidate against the recorded SHA-256, installs the tested
extractor versions and includes FFmpeg/mpv. It never bakes `/data` or a private
authentication bundle into an image layer.

The image also installs the optional DLNA and Sonos adapter dependencies; those
adapters remain opt-in and hardware-unverified.

The container starts through a minimal state bootstrap because Home Assistant
and ordinary container engines may mount `/data` as root-owned. The bootstrap
creates or repairs ownership only below `/data/frontend`, `/data/speakers` and
`/data/private`, refuses symlinked state roots, clears supplementary groups and
then permanently drops to UID/GID 1000 before starting receiver code. It does
not alter Home Assistant's `options.json` or run playback/network code as root.
When a root-readable bundle path is configured, the same bounded bootstrap
rejects symlinks/oversize inputs and atomically imports it as mode 0600 into the
private App state before dropping privileges. The global `/share` copy therefore
does not need to be made readable by the unprivileged runtime.

The root `cast-audio-receiver/` directory is the thin Home Assistant
metadata/configuration layer pointing at that OCI image. `repository.yaml` is at
the repository root as required by Home Assistant's repository scanner. The app
enables ingress and host networking because local Cast, mDNS and AirPlay traffic
cannot be treated like an ordinary isolated web app.

## Reproducibility boundary

The Rust lockfile, maintained source commit and AirPlay artifact are pinned. The
container's CPython 3.12/x86_64 runtime, including extractor, DLNA and Sonos
transitive wheels, is hash-locked in
`config/container-linux-x86_64-cp312.lock.txt`. Its isolated project-wheel build
also uses hash-pinned setuptools/wheel. Debian base-image digests and apt package
versions are not yet content-addressed, so the Containerfile is more repeatable
but still not a bit-for-bit reproducible release claim.

Before publishing an image:

1. pin base images by digest and record OS package inventory;
2. run the Python, Rust, wheel-content and container smoke gates;
3. scan the final image and source export for private state/secrets;
4. produce an SBOM and attach source/licence notices;
5. test rollback plus real Cast, Default Media Receiver and at least one output.

For pre-publication acceptance, `tools/create_ha_test_repository.py` produces a
minimal source-only App repository whose adjacent Dockerfile is built by the
test Supervisor. It deliberately excludes `.state`, research artifacts and all
authentication material. This local-build fixture is not the final release
layout and must not be mistaken for permission to publish the development Git
history.

## Home Assistant listeners

The add-on uses host networking for Cast/mDNS. On current Supervisor versions,
`ingress_port: 0` allocates a collision-free port that the container reads from
the authenticated `/addons/self/info` API. The manager listens on that ingress
port and, separately, on the user-selected direct LAN `web_port` (8788 by
default). Both listeners serve the same process and state; Home Assistant is not
a separate receiver build. A real Supervisor source build, install, start,
ingress/LAN access, restart and persistent-route test passed on 2026-09-20.
Published-image installation plus update and rollback acceptance remain open.
