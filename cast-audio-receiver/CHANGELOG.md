# App changelog

## 0.6.0-dev23 — desktop YouTube Music Cast launch

- Fix YouTube Music casting from Chromium-based desktop browsers. The receiver
  now sends the LAUNCH result directly to the requesting sender, allowing the
  browser to obtain the app transport and continue into playback.
- Preserve receiver-status updates for Home Assistant and other observers, and
  use the same correctly addressed replies for Stop and volume commands.

## 0.6.0-dev22 — playback recovery, current-title cache and MPL 2.0

- Recover a failed YouTube Music load with one fresh bounded retry; **Retry/Play**
  now performs a real reload instead of trying to unpause an empty decoder.
- Stream the current progressive audio into a bounded 32 MiB memory cache while
  it plays. Seeking can fetch sparse ranges, and single-title repeat can reuse a
  complete cached title without caching the whole playlist or delaying startup
  for a full download.
- Keep playback alive for at most ten seconds after an unexpected YouTube Cast
  control disconnect so the sender can reattach. Explicit disconnect/Close and
  Stop still stop immediately.
- Match IPv6 discovery with dual-stack listeners where the host supports them.
- Original project files are now MPL-2.0, allowing file-level reuse in larger
  Apache-2.0 projects while keeping modifications to those files open. Existing
  Vibecast MIT, Chromium BSD, `airplay-cli` GPLv3 and other third-party licenses
  remain unchanged; releases through dev21 remain GPL-3.0-or-later.

## 0.6.0-dev21 — AirPlay diagnostics

- The Add-on `log_level: debug` setting now reaches AirPlay output adapters.
- AirPlay failures in the normal Add-on log now identify decoder truncation,
  expected versus decoded duration, sender error codes, FLUSH timeout/failure,
  warm-to-cold reconnect fallback and unexpected transport closure.
- Shared diagnostics omit stream URLs, titles, device addresses, credentials
  and unrestricted helper output. This version is intended to make one debug
  reproduction sufficient for diagnosing the reported end-of-track failure.

## 0.6.0-dev20 — experimental pre-release

- Switch between Deutsch and English at the top right. The browser remembers
  your choice; unsaved input and discovered devices survive language changes.
- Translate controls, status, discovery, errors and confirmation dialogs.
- Publish native x86_64 and ARM64 images. ARM64 passes native build/runtime
  checks; physical ARM speaker testing remains open. 32-bit ARM is unsupported.
- Includes the dev19 YouTube Music Repeat modes and faster single-title repeat
  described below. Existing speaker configurations and identities are retained.

## 0.6.0-dev19 — YouTube Music repeat

- Reduce the pause when repeating a title by reusing its recently resolved
  stream. The next title stays prepared for manual skipping. Stream opening
  and output buffering still apply; this is not gapless audio playback.
- Joint receiver test confirmed faster repeat and working manual Next.

- Enable the sender's repeat control and synchronize Off, One and All modes.
- Repeat the current title at natural EOF or wrap the playlist; manual Next
  still advances when repeating one title.

## 0.6.0-dev18 — experimental pre-release

- Add verified one-time acquisition of the separately published authentication
  bundle on a clean install; keep local overrides and existing state authoritative.
- Publish the versioned OCI image with source/revision labels, SBOM and provenance.

## 0.6.0-dev17 — candidate

- Add the project speaker icon and logo to the Home Assistant App.
- Fix DLNA preload handling: a title loaded without autoplay remains ready
  instead of being mistaken for a cancelled session.
- Strengthen publication/export and upstream source evidence checks.

## 0.6.0-dev16

- Add DLNA network discovery and a bounded local HTTP compatibility relay for
  finite tracks that older renderers cannot retrieve or decode directly.
- Recover cleanly from rejected UPnP commands. User confirmed YouTube Music
  playback on an older Samsung TV; this is not general hardware certification.

## 0.6.0-dev14–15

- Fix physical local audio in Home Assistant and embedded management access.
- Allow correcting a DLNA target without recreating its Cast speaker identity.

Full development history, limitations and attribution are in the main repository.
