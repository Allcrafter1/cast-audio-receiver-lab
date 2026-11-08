# Two Cast identities, one audio receiver

The `0.7.0-dev3` candidate gives each desktop-managed output two stable Cast
identities. This is the product implementation of the successful
[PR #18 capability investigation](youtube-capability-lab.md), not the silent
research receiver. It applies to every registered output, including local mpv,
AirPlay, DLNA and direct Sonos; it does not add another audio backend.

## Discovery policy

| Property | Original speaker | YouTube video alias |
| --- | --- | --- |
| Friendly name | Output name, e.g. `Wohnzimmer` | Output name plus ` (YT)`, e.g. `Wohnzimmer (YT)` |
| Device UUID | Existing installation/player UUID, unchanged | UUIDv5 derived from the original UUID and `cast-audio-receiver/youtube-video/v1` |
| mDNS `ca` and Cast `DEVICE_INFO` | `199428` | `199429` |
| General `_googlecast._tcp` PTR | Yes | No |
| App subtype PTRs | All registered apps except `233637DE` | Only `233637DE` |
| App availability | Music and other registered apps available; YouTube unavailable | Only YouTube available |
| Explicit LAUNCH | Existing registered-app compatibility retained | Only YouTube |
| Eureka/API display flags | Existing audio defaults | Same existing audio defaults |

The video bit lets the native YouTube client select its TV route. It does not
enable video decoding or change the output's actual media capabilities. Music
and other clients respecting discovery/availability continue to select the
original speaker. The original endpoint still accepts explicit legacy launches,
including YouTube, so a previously cached browser route is not rejected solely
because discovery has moved to the alias. Discovery policy is not an access
control boundary; the existing local-network trust model is unchanged.

There is no attempt to infer the calling app from `GET_DEVICE_INFO`: the tested
request contains no app ID, and Google Play services can aggregate availability
queries. The listening endpoint supplies its fixed profile, consistently across
mDNS and Cast. The two Eureka endpoints also retain their respective UUIDs.
Cast `DEVICE_INFO.deviceId` uses the same compact UUID spelling as mDNS TXT `id`.
Internal UUIDs, persisted storage keys and derived aliases remain unchanged.
The first product UI test exposed dashed/compact duplicate Android routes;
matching the wire representation fixes the sender-visible inconsistency without
rotating device identities or clearing app data.

## Shared ownership and lifecycle

Both TLS listeners feed one `DeviceHub`. The transport allocates connection IDs
from one shared counter, so concurrent connections on different identities
cannot collide. There is exactly one Player, app-session map, output report
stream, volume state, player settings scope and canonical app-storage directory.
The active app receives the selected endpoint name and public UUID for its Cast/cloud association;
this does not create separate playback storage or a second decoder.

Starting an app through either identity uses the existing replacement and owner
takeover logic. Device status and output-volume feedback are shared. Existing
reconnect grace, passive-observer handling, stale-command rejection and explicit
Stop behavior remain in the same hub. An unsupported launch on the alias is
rejected before it can stop the current session or initialize the volume.

Startup prepares every endpoint before starting the hub tasks; a bind or
discovery failure releases the prepared resources. Shutdown withdraws both
announcements and closes accepted sockets. Certificate rotation shares the same
TLS/auth material and refreshes the certificate digest on both advertisements
without changing their IDs or subtype policies.

## Costs, compatibility and limits

- Per output, the alias adds one Cast listener, two Eureka listeners and an mDNS
  responder. It adds discovery/control traffic and client-cache entries, not a
  second player, media download or transcoder. No large-installation resource
  benchmark has been performed.
- Generic network scanners and clients that enumerate cached instances or
  disregard subtype/availability filtering can display both UUIDs. The design
  cannot guarantee one icon in every third-party client. The targeted Android
  app separation was measured, rather than inferred from the names alone.
- Home Assistant's [Cast discovery](https://github.com/home-assistant/core/blob/dev/homeassistant/components/cast/discovery.py)
  uses pychromecast, whose [normal mDNS browser](https://github.com/home-assistant-libs/pychromecast/blob/master/pychromecast/discovery.py)
  subscribes to the base Cast service. The subtype-only alias is deliberately
  absent from that PTR set. A real LAN test with the installed Zeroconf library
  found only the speaker in a fresh base browser, but **both identities** after
  a YouTube subtype browser populated the shared cache. Thus duplicate HA
  entries are possible; base-PTR suppression alone does not guarantee hiding
  the alias from that integration. No live HA entity registry was changed or
  audited in this test. If both IDs are registered, both control the same output;
  the owner accepts manually disabling an unwanted duplicate.
- Keep UUIDs stable. Earlier experiments with rapidly replaced UUIDs showed
  stale/dim client rows until discovery converged. Installation retains the
  original speaker UUID and derives the alias deterministically; do not rotate
  IDs to clear a phone's cache.
- Native Vibecast frontends that own discovery outside Rust retain the previous
  single endpoint. Their registration API must support subtype-only advertising
  before enabling this policy. This does not limit the Linux/OCI/Home Assistant
  product's output adapters.
- AirPlay, DLNA and Sonos use the same composition. Discovery on an AirPlay
  output is checked locally; this is not a new audible Sonos hardware test.
  Contributor-confirmed hardware scope remains in [network outputs](network-outputs.md).

## Candidate validation and release boundary

Behavior tests cover per-endpoint UUID/capability/availability replies,
shared volume and status, Speaker → Video → Speaker takeover, rejection of a
wrong-app launch, stale media commands/disconnects, legacy explicit launches,
unique connection IDs, socket cleanup and mDNS refresh/goodbye policy.

The Linux candidate is installed on the test laptop with a retained rollback
container. On-wire checks verify all four endpoint profiles for local mpv and
AirPlay. Real Android playback/transition observations are recorded in
[TESTING.md](TESTING.md); silent lab LOAD acceptance is kept separate from
actual decoder playback and listener-confirmed sound.

The cumulative frontend source patch, source lock, Containerfile and CI recipe
describe the same candidate. The local wheel is checked for completeness and
absence of historical receiver modules. Public multiarchitecture image builds,
registry publication and Home Assistant store promotion are separate release
steps; the test deployment does not perform them.
