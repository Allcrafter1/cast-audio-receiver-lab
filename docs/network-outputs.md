# Experimental network outputs

DLNA/UPnP MediaRenderer and Sonos are implemented as optional outputs behind the
same static registry as local mpv and AirPlay. They are not yet physical-device
acceptance claims.

## Current data path

For both adapters, the target device pulls the selected HTTP(S) media URL
directly. The receiver forwards basic metadata, playback commands and volume,
then polls the target for transport state and position. It does **not** currently
proxy, decrypt or transcode the stream.

This is intentionally the smallest useful implementation, but it has important
consequences:

- the target must be able to reach the source URL itself;
- its firmware must understand the source container, codec and any manifest;
- short-lived signed URLs may expire or reject a different client;
- DLNA metadata and seeking vary substantially between renderers;
- Sonos URI behavior differs between ordinary tracks, radio streams and music
  services.

Local mpv and AirPlay decode on the receiver host and therefore do not share all
of these limitations. A future local relay/transcode layer may improve network
renderer compatibility, but it would add CPU use, latency, lifecycle ownership
and another HTTP security boundary. It should be driven by hardware evidence,
not added speculatively.

## Upstreams and status

- DLNA uses pinned `async-upnp-client` 0.48.1 and its `DmrDevice` profile.
- Sonos uses pinned SoCo 0.31.2 and its direct `play_uri`/transport APIs.
- Target configuration is validated and persisted atomically. New routes are
  disabled until explicitly enabled.
- Simulated-device unit tests cover load, metadata, seek, play/pause, volume,
  stop and error containment.
- Physical DLNA and Sonos playback, artwork behavior, natural end detection and
  receiver-side button feedback remain pending.

These adapters are extensions, not a claim that Sonos is generic DLNA or that
all Cast sources can be forwarded unchanged.
