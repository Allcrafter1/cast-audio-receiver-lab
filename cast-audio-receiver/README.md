# Cast Audio Receiver Lab

An experimental audio-only Cast receiver for YouTube Music and supported direct
media. Create named speakers that play locally or forward to AirPlay, DLNA or
Sonos. Manage them through **Open Web UI** in Home Assistant or the local network.

- Linux amd64 only at present.
- Valid, separately supplied Cast authentication material is required.
- Direct LAN management has no login: trusted networks only, never expose it
  to the Internet.
- AirPlay2/HomePod, Sonos and wider DLNA compatibility still need hardware tests.
- Google/service changes can break the experimental receiver independently of
  updates. Google Home groups and Spotify Cast are not supported.

Read the Documentation tab before starting. Based on Vibecast and existing
open-source media tools; see the main repository for architecture, full credits,
source/licence records and known limitations.
