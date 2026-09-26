# Cast Audio Receiver Lab

This is the thin Home Assistant packaging layer for the same OCI image and
`cast-audio-receiver` supervisor used by normal Linux/container installs. It is
not a separate implementation.

The app is an **experimental public pre-release**. A real HAOS/Supervisor build,
install, ingress/LAN, local-audio restart and persistent-route test has passed.
On a clean first start it verifies and privately stores the separately released,
pinned authentication bundle. An advanced `certificate_path` may select a local
replacement instead. Authentication material is not stored in this repository,
entered in the web UI or exposed through diagnostics. Invalid configured input
fails explicitly; the App must never appear healthy as a nonfunctional receiver.

Home Assistant ingress opens the management UI without a second application
login. Host networking is required for Cast and AirPlay discovery. Current
Supervisor versions allocate a free ingress port when `ingress_port` is zero;
the app reads that port from its authenticated self-info endpoint. The separate
`web_port` option controls direct LAN access and defaults to 8788. If direct LAN
access is unwanted, leave the port reachable only on a trusted network/firewall;
the application deliberately has no second login layer.

`artwork_public_url` is optional. Set it to a LAN-reachable origin such as
`http://192.168.1.20:8788` if Cast clients should receive locally processed
square cover URLs. Leave it empty if that address is not stable.

`amd64` and `aarch64` (64-bit ARM) have native image builds, architecture-specific
pinned AirPlay assets/wheels and runtime checks. Physical ARM speaker acceptance
remains open. 32-bit ARM is not supported.

## If an update does not appear

Check the repository of the **installed** App, not only the App store. An old
local/test repository and the public GitHub repository create separate App
identities even when their displayed names match. A public release does not
update an installation belonging to another repository. Do not uninstall the
old App or start a duplicate against the same ports to resolve this. Back up and
migrate its data/identities first; the public repository is
`https://github.com/Allcrafter1/cast-audio-receiver-lab`.
# Local audio and embedded interface

The app uses Home Assistant's shared PulseAudio service (`audio: true`), not
direct access to `/dev/snd`. Pass the sound card through to HA OS first, then
select the desired output using Home Assistant's app audio settings. A physical
device visible to HA alone is insufficient without the app's audio mapping.
The container runs the player as a named, non-root service user with a writable
home. AirPlay does not require a local sound card.

The embedded management page uses HA's existing Ingress session cookie for
same-origin API calls. It adds no application login or token. Direct LAN access
remains unauthenticated. Reopen the app panel after an update or expired HA
session. If states disagree, report the version displayed by each page and any
visible error; never include your ingress URL/session cookie in a public issue.
