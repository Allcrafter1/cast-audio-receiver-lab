# Cast Audio Receiver Lab

This is the thin Home Assistant packaging layer for the same OCI image and
`cast-audio-receiver` supervisor used by normal Linux/container installs. It is
not a separate implementation.

The app is currently a **packaging preview**, not an installable public release:
the referenced GHCR image has not been published. Place a compatible private
Cast authentication bundle at `/share/cast-audio-receiver/certs.json` before
starting the App. The file is mounted read-only; an advanced configuration may
select another absolute path. Private authentication material is intentionally
not stored in this repository, entered into the web UI or exposed through
diagnostics.

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

Only `amd64` is declared because that is the architecture for which the pinned
AirPlay sender binary and current physical tests exist. Adding an architecture
requires a corresponding verified `cliairplay` artifact/build and a full
receiver test; editing the architecture list alone is not support.
