# Installation and deployment

The project is an experimental pre-release. The tested deployment is Linux
`amd64`; a versioned GHCR image and Home Assistant repository metadata are
published from this repository. All delivery forms run the same `cast-audio-receiver`
supervisor and therefore do not maintain separate playback implementations.

## Cast authentication input

A usable Google Cast speaker requires a compatible `certs.json` authentication
bundle. The process fails closed when the configured input is missing or
unreadable; a management page alone is not proof that Cast is ready.

The source repository and container image contain only a pinned manifest, not
the bundle. On a clean first start with no explicit path, the runtime downloads
the separately published `2026.09.20` bundle once, checks its exact size and
SHA-256 digest, then atomically stores it under private `/data` state with mode
`0600`. Restarts do not redownload it and existing material is never silently
replaced. Set `certificate_path` to use a local/BYO bundle instead.

Certificate date coverage is not a guarantee of Google acceptance: server-side
revocation or a protocol change can invalidate it earlier.

## Home Assistant App

In Home Assistant, open **Settings → Apps → App store → Repositories**, add
`https://github.com/Allcrafter1/cast-audio-receiver-lab`, refresh the store and
install **Cast Audio Receiver Lab**. Only `amd64` is supported by this release.

The source package under `cast-audio-receiver/` has passed a real HAOS/
Supervisor build, install, ingress, LAN, local-audio restart and
state-persistence test. It references the version-matched public GHCR image.

No bundle option is required for a clean install. To avoid the network download
or use your own material, put a bundle at a persistent absolute path and set
`certificate_path` to it.

Normal configuration intentionally stays small:

- `web_port` (default `8788`) controls direct access from the trusted LAN.
- `log_level` defaults to `INFO`; use `DEBUG` only for bounded diagnosis.
- `artwork_public_url` may point to the App's LAN origin when Cast clients need
  the locally processed square artwork. Empty preserves the sender URL.
- `certificate_path` is an advanced replacement path for bundle rotation.

Open Web UI launches the same manager through Home Assistant ingress without a
second login. Direct LAN access is `http://HOME_ASSISTANT_IP:8788`. Do not expose
that unauthenticated port to the Internet or an untrusted network.

Persistent routes, frontend identity and the acquired bundle live under the
App's `/data`; an App restart retains them. Updating or rolling back must
preserve `/data`.

## Local OCI build

The checked-in `Containerfile` builds the maintained Vibecast fork, the Python
manager and pinned `cliairplay` in one `linux/amd64` image:

```sh
docker build -f Containerfile -t cast-audio-receiver:local .
```

Use host networking for mDNS, Cast and target discovery. Mount state read/write
and the private bundle read-only; the root bootstrap copies the latter into
private state before permanently dropping to UID/GID 1000:

```sh
docker run --rm --network host \
  -v /absolute/cast-audio-state:/data \
  -e CAST_AUDIO_WEB_PORT=8788 \
  ghcr.io/allcrafter1/cast-audio-receiver:0.6.0-dev18
```

For BYO material, additionally mount the file read-only and set
`CAST_AUDIO_CERTS` to its container path.

The UI is then available at `http://LINUX_LAN_IP:8788`. The published image has
an attached GitHub Actions provenance/SBOM record; broader hardware and
published-image rollback testing remain open.

## Native Linux development install

For source development, build the pinned Vibecast fork, install this Python
package and provide the pinned `cliairplay` binary as described in the
[development runbook](current-runbook.md). Start the single supervisor rather
than separately managing frontend and manager:

```sh
cast-audio-receiver \
  --frontend /absolute/path/to/vibecast \
  --cliairplay /absolute/path/to/cliairplay \
  --data-dir /absolute/private/state \
  --certs /absolute/private/certs.json \
  --web-port 8788
```

The supervisor starts the frontend first, waits for its player bridge, starts
the manager second and shuts the manager/adapters down before the frontend.

## Verification and diagnosis

After startup:

1. `GET /health` must report `ready: true` and both manager and frontend ready.
2. `GET /status` shows safe operational state and route counts.
3. Add or enable a target in the UI and verify that its Cast speaker appears.
4. Use `GET /api/support` as the first shareable diagnostic record.

`/api/support` intentionally omits route names, IDs, target addresses, media
URLs, account data, certificates and keys. See the [maintenance guide](maintenance.md)
before sharing any additional log excerpt.
