# App changelog

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
