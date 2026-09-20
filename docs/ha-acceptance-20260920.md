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
- The running HA process crossed a real certificate-window boundary at midnight,
  logged rotation of TLS, device-auth and discovery state, and accepted later
  Cast connections without an App restart. This validates bundle selection and
  live rotation for one boundary; it does not prove future Google acceptance.

No media was played through the local output because the HA host has no audio
device. The laptop development receiver remained stopped to avoid duplicate Cast
advertisements.

At idle with one enabled local route, Supervisor reported about 67.5 MiB memory
(0.57% of the test host limit) and 0.04% CPU. This is a useful packaging
baseline, not a playback peak or evidence for smaller/ARM hardware.

## Still open

- End-to-end AirPlay playback from the HA App to a physical receiver.
- Physical DLNA and Sonos interoperability.
- Explicit rollback to an older published image while retaining persistent
  state. Public-image update and a disposable clean public-repository install
  now pass as recorded below.
- ARM builds and resource measurements on smaller target hardware.

This acceptance proves the packaging and lifecycle exercised above. It does not
prove future Google sender acceptance, certificate non-revocation, arbitrary
Cast-app compatibility or redistribution permission for private credentials.

The user requires final installations to obtain working authentication coverage
rather than silently producing an unusable receiver. The initial acceptance used
the private `/share` input and atomic bootstrap import. The later public dev18
test below exercises the separately hosted, digest-pinned first-install path;
bundle bytes remain outside the product Git history and container image.

## Public dev18 follow-up

After publication, anonymous GHCR acquisition returned the recorded dev18 image
digest. A real Supervisor updated the existing dev16 App to the public dev18
image. `/health` was ready, all three configured routes were running and their
stable IDs were unchanged. The public GitHub App repository was then added to
the same HAOS host and a disposable clean installation was started while the
persistent installation was stopped. It downloaded the separately hosted,
pinned authentication bundle into its empty private state and reached ready
without a user-supplied certificate path. The disposable installation was
removed and the persistent dev18 installation returned ready with the same
three route IDs. An App-scoped backup was created before the update.

This verifies public repository discovery, anonymous image use, first-install
bundle acquisition, update persistence and restoration of the normal instance.
It is not an explicit downgrade/older-image rollback test and does not replace
the remaining physical-hardware checks.
