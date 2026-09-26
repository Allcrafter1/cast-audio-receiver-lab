# Bilingual UI and native builds — dev20

The top-right Deutsch/English buttons update the interface in place. A saved
browser-local choice wins over the browser's language; German browser locales
use German, all other locales use English. Unavailable localStorage is handled
without breaking the page. Names, URLs, discoveries and unsaved form inputs
are never translated or reset when switching. Status updates and active notices
follow the selected language. No playback process restarts or configuration API
writes occur from a language change.

`tests/browser_ui.cjs` uses Chromium and synthetic API responses, covering both
languages, discovery in flight, drafts, dialogs, errors, reload persistence,
blocked storage, desktop/mobile layout and HA ingress-relative URLs. Run with
Node 22+ and Playwright 1.63.0 available through NODE_PATH:

```sh
node tests/browser_ui.cjs
```

The normal Python suite retains the request/session-cookie regression. The
browser tests also run in CI using isolated tooling, not runtime dependencies.

## Architecture builds

ARM means **64-bit ARM (aarch64 / Docker arm64)** in this candidate. 32-bit ARM
is not supported. Native GitHub runners build amd64 and arm64 independently;
no emulation or cross-architecture library substitution is used.

- Same Rust commit, Python package versions and AirPlay version on both targets.
- ARM Python wheels are downloaded separately and inventoried with the existing
  `tools/wheel_inventory.py`. All 31 versions match x86_64. Hash-locked binary
  installation prevents accidental source builds or x86 wheel substitutions.
- AirPlay v0.5.4 uses its upstream architecture-specific executable and checksum;
  `cliairplay --check` and the decoder/relay tests execute during each build.
- CI loads each image on its matching runner, then checks frontend startup,
  AirPlay, Deno and native Python imports without network/private credentials.
- Manual `release-review.yml` saves separate OCI archives, SHA-256, SBOM and
  provenance as seven-day GitHub Actions artifacts. It does not push to GHCR,
  create a release, fetch runtime Cast credentials or change a live receiver.

Build success is not physical ARM speaker acceptance. The dev20 publication
workflow builds amd64/arm64 on native runners, pushes by digest, smoke-tests both
images and only then creates the versioned multiarch manifest. It reads the
version from pyproject.toml, independently of App store promotion. The store is
updated only after public retrieval and the selected x86_64 receiver deployment
are verified. See the working plan for final publication evidence.

## Verified candidate and downloads

Source commit: `670c80a044f5a9d401084362ded690e1add62114` (dev20).
Local Python checks completed 264 tests successfully with 10 skips; Chromium
passed the desktop/mobile, DE/EN, persistence, ingress and interaction checks.
[CI run](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36271012310)
passed all seven jobs, including native runtime smoke tests on both platforms.
[Artifact review](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36271012452)
successfully built both candidates and verified their OCI blobs and attestations.

- [x86_64 / amd64 archive](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36271012452/artifacts/10915277766)
- [ARM64 / aarch64 archive](https://github.com/Allcrafter1/cast-audio-receiver-lab/actions/runs/36271012452/artifacts/10915552304)

Each download contains an OCI image archive and its SHA-256 file. Artifacts
expire on 2026-10-03 (seven-day retention); these are build candidates, not a
published registry release. Publication and live deployment were initially
deferred; the owner subsequently authorized them as a separate rollout step.
The persistent installation reference is now the dev20 GHCR tag, not these
expiring review archives.
