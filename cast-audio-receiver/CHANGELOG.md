# App changelog

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
