# dev20 publication and deployment evidence

The owner explicitly authorized publication and the selected x86_64 test-host
update on 2026-09-26, superseding the earlier candidate-only hold.

## Public image

- Tag: `ghcr.io/allcrafter1/cast-audio-receiver:0.6.0-dev20`.
- Image source: `06b4ecd5e1199180030e94cbd3ce3cb8a7d39e68`.
- [Publication run](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36272017913):
  native amd64 and arm64 builds, runtime checks and merged manifest all passed.
- [CI](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36272018247):
  all seven jobs passed. Local Python suite: 265 tests completed, 10 skips.
- Multiarch digest:
  `sha256:7ceabbf06a1d6bc91cf9d54339c04ff81bc642e09403f9361dfe68ece7f7db52`.
- amd64 manifest:
  `sha256:f382489c89758ca916a94ff3ad1bb8d281548662bea9954f55104c47d0add134`.
- arm64 manifest:
  `sha256:8a86e2304e6c7dd9e27f143a76367249f2789ff3a5b838cc6329a1309e7e7181`.

Anonymous registry readback verified the index, both platform manifests/configs,
source revision, version and HA architecture labels (`amd64`, `aarch64`), with
attestation manifests retained. The selected host pulled the complete amd64
image using an empty Docker credential configuration before deployment.

## Deployment and rollback preparation

The selected existing receiver now runs the full dev20 image by immutable
multiarch digest, not the earlier frontend-only hotfix. Its three route
configurations were compared before/after and are identical. Both enabled
outputs report ready and running with zero restarts. Network, PulseAudio,
restart policy, memory/swap and PID limits are retained.

The previous stopped container is retained as `cast-audio-receiver-pre-dev20`.
A consistent private data archive and inspect/config snapshots were created
while the receiver was stopped (directory mode 0700, files 0600). No old
container, image or state was deleted. A rollback must stop the new receiver
before restarting the retained container; never run both against the same
state/host ports. Explicit post-update rollback was not exercised.

Live Chromium checks against the actual receiver passed language switching,
persisted choice, unsaved inputs, mobile layout and all three displayed routes,
with no configuration writes or JavaScript errors. This is not a new audible
playback acceptance test. Prior joint Repeat acceptance remains recorded in
`youtube-repeat.md`. ARM64 has native runtime checks but no physical speaker
or real ARM HAOS acceptance claim. The initial rollout did not install dev20 on
a separate HAOS host; the later migration below supersedes that limitation for
the selected x86_64 HAOS host.

## App and source release

App metadata was promoted to dev20 for amd64/aarch64 in `75ea620` after public
retrieval and deployment checks; anonymous readback confirms both architectures
and the version. The [dev20 prerelease](https://github.com/Allcrafter1/cast-audio-receiver-lab/releases/tag/v0.6.0-dev20)
is public with source archive/checksum and image digest/manifest assets uploaded.
Existing App options and persistent data layout are
unchanged. Release/update notes include the Repeat fixes inherited from dev19,
the DE/EN interface and the ARM64 limitations.

[Source review](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36272062424)
passed the frozen/offline frontend build. The retained source archive matches
pin `35ffe1b5ceca4962903a4f217cb18ef7d3dfb071` and SHA-256
`a3b71ea3aa05818bb19ba720a696860044c5f79bbb8dba0c3db3fc20d0a87f83`.
See `source-delivery.md` for unchanged dependency source assets and limitations.

## Later HA repository migration

The owner's HA installation still belonged to the old local test repository;
the public store already showed dev20 as a separate, uninstalled App. Matching
display names do not imply matching repository/App identities, so refreshing
the store could not update the old installation.

After explicit migration and scoped-restore approval, original and final
stopped-App backups were retained. A fresh public App installation supplied
its own Supervisor metadata/identity, while the previous App supplied its data.
The migration archive excluded HA, shared folders and Supervisor configuration;
only the new App was selected for restore. User options were reapplied through
the supported App configuration API. The old App remains stopped with manual
boot as a recovery option, rather than running a duplicate receiver.

The new public App reports dev20 installed/latest and ready through HA ingress.
All three route configurations, frontend installation identity and private
authentication material compare byte-identically to the stopped old App backup.
Both enabled routes are running; the disabled route stays disabled. Live
DE/EN, persistence, unsaved-input and mobile browser checks pass, as do ingress
health/route requests. No new audible playback or physical ARM test is implied.
