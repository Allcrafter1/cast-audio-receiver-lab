# Home Assistant acceptance — 2026-09-20

This records the first real HAOS/Supervisor acceptance run without publishing a
product repository or embedding private authentication material.

## Passed

- Generated a secret-free, source-only Home Assistant test repository.
- Supervisor built and installed the amd64 image from that context.
- The root bootstrap created only the App-owned state directories, imported the
  separately mounted certificate input and dropped permanently to UID/GID 1000.
- Dynamic ingress and the separately configurable trusted-LAN port both served
  the same management process.
- `/health` reported the manager and Cast frontend ready.
- A local-output test route registered as an audio Cast receiver.
- App restart preserved the route UUID, name, enabled state and running state.
- `/api/support` returned only schema/application/runtime data and a numbered,
  name-free route summary; it exposed no target, local address, certificate or
  media data.
- The final private certificate inventory (773 windows through 2030-12-06) was
  imported after preserving the previous `/share` input as a rollback copy. The
  frontend returned ready and advertised the persistent route again.

No media was played through the local output because the HA host has no audio
device. The laptop development receiver remained stopped to avoid duplicate Cast
advertisements.

At idle with one enabled local route, Supervisor reported about 67.5 MiB memory
(0.57% of the test host limit) and 0.04% CPU. This is a useful packaging
baseline, not a playback peak or evidence for smaller/ARM hardware.

## Still open

- End-to-end AirPlay playback from the HA App to a physical receiver.
- Physical DLNA and Sonos interoperability.
- Installation from the eventual published image, image inventory/SBOM/scan,
  update and rollback while retaining persistent state.
- ARM builds and resource measurements on smaller target hardware.

This acceptance proves the packaging and lifecycle exercised above. It does not
prove future Google sender acceptance, certificate non-revocation, arbitrary
Cast-app compatibility or redistribution permission for private credentials.

The user requires final installations to include the working authentication
coverage rather than silently producing an unusable receiver. For now this is
fulfilled by the private `/share` input and atomic bootstrap import. Public
repository/image inclusion remains gated on a separate redistribution and
security review; the private source-staging repository intentionally contains no
bundle.
