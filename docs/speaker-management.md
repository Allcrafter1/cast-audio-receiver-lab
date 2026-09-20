# Speaker management — 0.6.0.dev3

Deployed on the live test laptop, including both existing speaker identities.
The manager owns one Python adapter process per enabled speaker. The existing
Rust frontend remains separately managed. Playback protocols are unchanged.

## Install and start

Use a separate environment initially; do not upgrade a working playback environment
in place. From the repository root:

```sh
python3 -m venv .venv-management
.venv-management/bin/pip install -c config/management-tested-constraints.txt '.[management]'
.venv-management/bin/cast-speaker-manager --state-dir .state/speaker-manager --port 8788
```

The constraints record the tested CPython 3.12 Linux development environment;
they are not a cross-platform wheel-hash lock. Other architectures and the remote
Python 3.13 installation require separate verification.

Open `http://192.168.1.50:8788` (substitute the receiver's address) from the
home LAN. The UI loads immediately and
fetches the configured speakers automatically. There is no login, token, API key,
authentication flag or credential file. The default bind is `0.0.0.0` (all IPv4
interfaces); `--host` and `--port` remain configurable. This management service is
intended for the local network.

## Speaker lifecycle

- Add a local output, or explicitly scan and import one AirPlay service endpoint.
  Nothing is automatically enabled; discovery is not a continuous import loop.
- Each speaker has an immutable UUID and an independently editable Cast name.
- Delete stops only the selected speaker and removes its configuration and
  generated target file; private historical logs/backups remain. The UI asks
  for confirmation. New duplicate local outputs are rejected, including CLI
  imports; older duplicates remain manageable rather than being silently removed.
- Enabling starts its adapter. Disabling stops that adapter and its owned process
  group. Renaming an enabled speaker restarts only that speaker and interrupts
  its session; the UI warns first.
- Duplicate target identities/endpoints are rejected. Known AirConnect bridges
  are filtered, but arbitrary third-party bridge loops cannot be detected with
  certainty. Choose real destinations deliberately.
- `running` means the adapter process is alive, not authenticated, connected to
  AirPlay, or audibly playing. Per-route private rotating logs aid diagnostics.
- Crashes retry with bounded exponential backoff up to 60 seconds. Graceful
  shutdown escalates SIGINT → TERM → KILL. Uncertain cleanup prevents replacement.

Configuration and target credentials are private files (directory 0700, files
0600); writes use atomic replacement. The API never returns pairing/TXT secrets,
raw logs, executable selection, or private file contents. Same-origin checks,
bounded JSON request bodies and a restrictive CSP remain; none requires a login.

## Adopting an existing route without changing its identity

While the manager is stopped, import the old target config and existing player UUID:

```sh
cast-speaker-manager --state-dir .state/speaker-manager \
  --import-target /absolute/private/target.json \
  --player-id EXISTING-UUID --name 'My speaker'
```

For local output use `--import-local` instead of `--import-target`. Imports are
disabled. Stop the old manually managed adapter before enabling its replacement;
the manager cannot detect every external process advertising the same UUID.
Keep the frontend's existing data directory to preserve its stored device state.
Pass the existing absolute `--cliairplay` path when starting the manager.

## Verification and remaining gates

Automated tests cover config round-trip, failed atomic save, exclusive ownership,
input validation, stable identity, independent two-process operation, crash
restart, direct unauthenticated API, cross-origin rejection, body limits, private-path
protection, disabled import, duplicate targets and secret-free discovery results.
These are real subprocess/local HTTP tests, not real two-speaker audio acceptance.

Live Chromium check passed for direct page entry, both existing speakers,
rename/reload, disable/enable and restoring the original name, without JavaScript
errors. A real manager restart also restored both enabled routes from disk.

The previous live adapters were separate manual processes and the manager had no
routes.json. Both were migrated into persistent manager configuration with their
original UUIDs, target and audio environment. Rollback state is saved privately
in `.state/manager-dev2-migration-backup`; the old token file was removed from the
active state (a rollback copy remains). Rust frontend state was preserved.
Real multi-output audio, resource measurements, HA packaging,
and artifact-hash dependency locking remain open. SIGKILL of the manager itself
cannot guarantee child cleanup; production packaging needs service/cgroup ownership.
The UI includes delete and an SVG favicon. A target editor is not implemented.
