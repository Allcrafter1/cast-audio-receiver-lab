# Route manager / Web UI — approved proposal

Approved by the user and implemented as development version0.6.0.dev1.
Current usage, tests and remaining deployment gates: docs/speaker-management.md.
The original proposal below records the agreed scope, not current test status.

This introduces process ownership and an HTTP dependency, so user agreement is
required before implementing it. Current explicit per-route adapters remain valid.

## Small first milestone

- One Python management service owns configured adapter child processes; one
  child per route retains failure isolation and existing backend interfaces.
  The Rust frontend remains a separately started service initially. HA packaging
  later supervises both; avoid changing the playback protocol for a UI.
- Versioned JSON config with a random immutable route UUID, editable Cast name,
  selected backend/target and enabled flag. Renaming never changes identity.
  Adopt existing player IDs when importing current routes; do not invalidate
  saved volume/device identities just because management is added.
- Explicit scan/import action, no automatic recursive bridge creation. Show
  target protocol/identity, mark already imported targets, select one protocol
  endpoint deliberately, exclude our own known advertisements. Unknown reverse
  bridges cannot reliably be identified by name; never import every new device
  continually. No group/synchronization implementation in this milestone.
- List, rename, enable/disable and status UI. Target/pairing secrets remain in
  private state and are not returned through the UI/status API. No arbitrary
  executable/command-line fields accepted from HTTP requests.
- Bounded restart backoff; clean SIGINT shutdown and child reaping. Changing one
  route affects only that route. Explain disruptive rename/target changes before
  applying them; no silent replacement of currently active sessions.
- Config validation and atomic persistence; duplicate identities and invalid
  ports rejected. Retain last good configuration on error. Web port configurable.

## Proposed dependency and exposure

Use aiohttp for the small async HTTP API/static page, with plain HTML/JavaScript
and no frontend build toolchain. This is one NEW direct Python dependency and
must be reviewed/locked (including transitives); it is not installed yet.
Official API reference: https://docs.aiohttp.org/en/stable/web_quickstart.html

Default to loopback, with explicit authenticated LAN exposure or HA ingress
planned later. Validate origins/CSRF boundaries and bound request bodies; never
serve private directories or raw diagnostic logs. A UI without a settled access
policy should not be exposed to the household network by default.

## Verification before deployment

Config round-trip/migration, stable ID after rename, repeated start/stop without
orphans, isolated route crash/restart, two concurrently active routes, failed
config save preserving previous state, protected HTTP mutations, secret-free
responses, playback/disconnect regressions. Test against fake children first,
then explicitly selected real outputs. Measure actual incremental RAM/CPU before
making small-device suitability claims.
