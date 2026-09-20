# Installation and deployment

The project is still an experimental pre-release. The tested deployment is
Linux `amd64`; the public GHCR image and one-click Home Assistant repository are
not published yet. All delivery forms run the same `cast-audio-receiver`
supervisor and therefore do not maintain separate playback implementations.

## Required private Cast input

A usable Google Cast speaker requires a compatible `certs.json` authentication
bundle. The process fails closed when the configured input is missing or
unreadable; a management page alone is not proof that Cast is ready.

The owner's Home Assistant installation already contains the complete validated
773-window bundle through 2030-12-06 at
`/share/cast-audio-receiver/certs.json`. It is imported atomically into the
App's private `/data` state with mode `0600` during startup. The source
repository and public container context deliberately do not contain that
reusable private material. Back up the `/share` copy privately before changing
or reinstalling the host.

Certificate date coverage is not a guarantee of Google acceptance: server-side
revocation or a protocol change can invalidate it earlier.

## Home Assistant App preview

The source package under `cast-audio-receiver/` has passed a real HAOS/
Supervisor build, install, ingress, LAN, restart and state-persistence test.
The referenced public image is not published, so this is not a one-click public
installation yet.

Before starting the App, ensure the private bundle exists at the default path:

```text
/share/cast-audio-receiver/certs.json
```

Normal configuration intentionally stays small:

- `web_port` (default `8788`) controls direct access from the trusted LAN.
- `log_level` defaults to `INFO`; use `DEBUG` only for bounded diagnosis.
- `artwork_public_url` may point to the App's LAN origin when Cast clients need
  the locally processed square artwork. Empty preserves the sender URL.
- `certificate_path` is an advanced replacement path for bundle rotation.

Open Web UI launches the same manager through Home Assistant ingress without a
second login. Direct LAN access is `http://HOME_ASSISTANT_IP:8788`. Do not expose
that unauthenticated port to the Internet or an untrusted network.

Persistent routes and frontend identity live under the App's `/data`; an App
restart retains them. Updating or rolling back must preserve `/data` and the
private `/share` bundle. Published-image update/rollback acceptance remains a
release gate.

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
  -v /absolute/private/certs.json:/run/secrets/cast-certs.json:ro \
  -e CAST_AUDIO_CERTS=/run/secrets/cast-certs.json \
  -e CAST_AUDIO_WEB_PORT=8788 \
  cast-audio-receiver:local
```

The UI is then available at `http://LINUX_LAN_IP:8788`. Container deployment on
non-Home-Assistant hosts is implemented, but the first public image inventory,
SBOM, vulnerability scan, update and rollback test are still open.

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
