# YouTube discovery and PR #18 investigation

The findings below are the investigation history. The subsequently authorized
`0.7.0-dev2` candidate implements [two identities sharing one receiver](dual-cast-identities.md):
the original speaker for Music/other apps and a YouTube-only video alias.
Current implementation/deployment evidence is in [TESTING.md](TESTING.md).
Earlier statements that no product option was implemented refer to their
respective test stage, not to this later candidate. No public PR merge or release
has been performed by the candidate installation.

Research/validation: 2026-11-07–08, using source review, deterministic tests,
release-binary smoke checks and deployment readback. The first continuity
candidate did not resolve the complete incident. The owner accepts the current
web/Music playback behavior. After the subtype follow-up, both Android apps list
both speakers and Music still connects and plays audio. Ordinary YouTube still
fails to connect and temporarily loses the speaker entries. App discovery and
successful playback remain separate checks; full YouTube compatibility has not
been established.
No public release or PR #18 merge has been made.

The owner subsequently authorized an isolated capability-combination lab and
autonomous ADB UI testing. The [capability lab record](youtube-capability-lab.md)
adds historical profile reconstruction and the installed GMS route-icon mapping.
For matching capability snapshots, its individual-speaker predicate is identical
to the inspected YouTube picker's audio-only rejection predicate. Group types
and divergent snapshots have separate limits; this is not a universal
impossibility claim. With the owner's input-debugging authorization, native UI
trials now measure the four PR #18 layers independently. The lab record keeps
fresh-UUID observations separate from same-device comparisons, and silent
protocol acceptance separate from real audio. No product TV mode is added;
the working mdnsapps deployment remains the baseline.

Completed follow-up: 25 profiles, 50 app/profile observations, plus four paired
runs with 16 same-device observations. The full PR #18 profile accepted native
YouTube/Music media as a TV in both apps. Mismatched announcements could initially
show different icons, but did not preserve the requested presentation through
the paired sequence. This is bounded to the tested phone/app versions, not a
universal impossibility claim. The final audit verified the original installation
and phone setting restored; no product TV option was implemented.

## Preserve the speaker identity

The project deliberately identifies its receivers as audio speakers.
The historical [native speaker investigation](native-cast-speaker.md) records
Nest Audio advertising `ca=199428`, with audio output and no video-output bit.
AirReceiver advertised `4101`, including video output, and appeared as a TV.
The [September frontend record](vibecast-audio-frontend.md) explicitly records
the user's speaker-icon confirmation on 2026-09-12 after v0.4.2 aligned
`GET_DEVICE_INFO.deviceCapabilities` with mDNS at `199428`. That early test
established classification; it did not establish successful authentication or
YouTube playback. Its old build/config-copy instructions are historical.

Current product speaker mDNS and `DEVICE_INFO` agree at `199428`. Keep that
profile and the existing Cast IDs. Capability overrides are confined to the
explicitly authorized, separate research lab; no product TV mode is enabled.

## What the PR author actually verified

[PR #18](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/18) initially
proposed optional video advertisement, off by default. The later hardware
report, rather than the initial untested PR description, is the relevant result:

- Changing only mDNS to `199429` did not make the receiver appear in that
  Android YouTube app. The author's logs showed `gms_cast_prober` requesting
  `GET_DEVICE_INFO`, which still returned audio-only `199428`.
- The follow-up commit `b0ed527` made both bitfields `199429`. The author then
  reports the receiver being listed and audio playing from Android YouTube to
  a Sonos Era 100 through AirPlay, confirmed by the user in that test.
- This establishes that particular sender/device combination with video
  capabilities enabled. It does not establish that all YouTube clients require
  video capabilities, or verify ordinary YouTube in our speaker-only mode.

The submitted `enable_video_output()` aligns four distinct layers: mDNS `ca`,
Cast `DEVICE_INFO.deviceCapabilities`, Eureka `display_supported`, and
`display_supported` inside the outgoing `CAST-DEVICE-CAPABILITIES` HTTP header.
Its final enabled configuration is `199429` / `199429` / true / true. Before
the DEVICE_INFO follow-up, the source configuration was `199429` / `199428` /
true / true. The author's hardware report confirms the overall result; it is
not an independent wire measurement of each header. The API header is inherited
by frontend API/media HTTP clients and is separate from local discovery and
the inspected Android picker predicates. An experiment with both masks at
`199429` and Eureka true but API display false is therefore a useful partial
control, not exact PR #18 capability parity. The isolated lab includes explicit
API-display counterparts to distinguish these layers.

We retain the consistency lesson without adopting the TV identity option. The
owner's intermittently visible Android speakers do not establish which discovery
path listed them, so they neither prove nor rule out a local audio-only filter.

## General discovery fixes

1. **Consistent defaults without a runtime config file.** Set
   `display_supported=false` in both the Eureka capability defaults and the
   streaming `CAST-DEVICE-CAPABILITIES` defaults. The checked-in audio TOML
   already says false, but normal runtime startup does not copy it into the
   frontend data directory. Regression coverage checks default and empty-config
   construction as well as the resulting Eureka/header fields.
2. **Truthful application availability.** Answer `GET_APP_AVAILABILITY` from
   the actual provider registry. Previously every queried app was advertised as
   available even though unknown-app `LAUNCH` was rejected. The regression
   mixes supported and unsupported IDs, preserves request correlation, checks
   unknown launch rejection and then verifies a supported launch.
3. **Do not block MDX bootstrap on a diagnostic.** A valid initial Lounge bind
   now makes the identity ready immediately. Remove the optional screen-online
   probe from that critical path. A delayed availability fixture proves that
   establishment completes before the optional endpoint's three-second wait.

These fixes apply across output backends, with no Sonos exception. YouTube IDs
`233637DE` and `2DB7CC49` remain registered; no new IDs are justified here.

The initial continuity candidate passed these scoped Rust library tests:

| Suite | Passed | Ignored |
| --- | ---: | ---: |
| discovery | 11 | 0 |
| platform | 21 | 0 |
| core | 121 | 2 |
| sdk | 12 | 0 |
| apps-youtube | 148 | 1 |

Availability and delayed-probe regressions failed before their fixes. Local
socket fixtures, formatting and diff checks pass. These tests do not establish
Android discovery or physical Sonos acceptance.

## Installed versions and the reported regression

The initial read-only inspection distinguished the test laptop, label `.110`,
from the separate Home Assistant installation. At that initial audit, hashing
the running process's loaded executable confirmed the expected TuneIn-autostart
binary. All 28 installed Python/runtime assets matched its frozen candidate.
The later continuity deployment is listed separately below.

| Laptop candidate | Frontend SHA-256 |
| --- | --- |
| TuneIn autostart, active at initial audit | `16dcdc7aba9a504c2fcce314cc508f30eaace80fb695539bddcea7b1d55c7cc1` |
| preceding combined candidate | `7a4d9c859784cbec61cfc236df156c0c144fed9d845a30994c4b7468ab84f4d6` |
| PR #18 continuity, superseded | `bb129cbe110ea1f9dddc135bbfaf0ed7b43f76fa42212849b3b8ea73007a043b` |
| YouTube lifecycle, superseded | `66def8aefbd873101fd26c47eaa6583f97633a94776f4f4059ba46d050e51399` |
| YouTube controls/audio, superseded after rollback comparison | `a8430bd33a4bf6c77fa416c244f46e069e58ca27a2e5c4432e9fa700c1cad6a9` |
| Android diagnosis, rolled back for visibility comparison | `6b11b41f4260fc5fcaa906ef22a0bb0525f6e2e80ef8f9ed5db69e23da0d45e7` |
| App-subtype discovery, current private candidate | `02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b` |

The initial TuneIn-versus-combined reconstruction compared 114 recorded
frontend files: 112 unchanged, with only the TuneIn provider/tests differing.
That patch normalizes station handoff
time/autoplay; discovery, configuration, YouTube bootstrap, lifecycle routing
and Python are unchanged. TuneIn's distinct provider does not replace YouTube.

Neither initially audited laptop candidate had a frontend `config.toml`; that
absence predates the autostart patch. At that time live Eureka reported
`display_supported=true` for both routes while mDNS said `ca=199428`. This
confirmed the inconsistent defaults described above, not a new TuneIn-only
change or a proven cause of lost listing. Post-deployment readback now confirms
`display_supported=false`, `multizone_supported=true` and unchanged speaker
mDNS `ca=199428` for both laptop routes.

The separate active Home Assistant App container `0c012509` reports dev20;
runtime and Supervisor agree. It is healthy with two routes and approximately
531866 seconds of uptime at inspection. Duplicate dev18 container `0b4634bd`
is stopped. Neither the TuneIn nor continuity deployment updated HA. We could
not hash its frontend executable, so version/health agreement is not binary equality.

An all-interface mDNS resolver on the laptop aggregated LAN, loopback and
hotspot addresses for its own receiver services. A fresh IPv4 resolver bound
only to the LAN interface resolved both owned receivers to their LAN address
alone. A separate raw multicast probe checked the receiving interface on all
90 packets across three query batches, with zero parse failures: the owned
hostnames' A records contained only that LAN address, including replies from
the laptop itself. No loopback or hotspot address appeared on this observed
LAN path. The library filters addresses per interface; the earlier list was
local aggregation, not evidence for a LAN address-filter patch. This capture
used multicast loopback on the sender host, not a separate physical client.

At this initial inspection, ADB was available on the laptop but reported no
connected Android device. The later USB capture below supersedes that evidence
gap; it identifies a concrete missing app-subtype advertisement.

## Normal YouTube web handoff: cache conflict confirmed

The owner confirms that `music.youtube.com` works in the normal Chrome profile,
while `youtube.com` fails there. The first ordinary YouTube cast to the same
speaker works in Incognito, but the second connection in that same Incognito
window fails. This initially narrowed the failure to recurring browser state;
later flag/cache inspection below confirmed the stale-screen handoff conflict.
The successful first connection also demonstrates that this client can play
ordinary YouTube with the speaker identity.

The regular YouTube `233637DE` attempts at 21:02 and 21:11 UTC reach `LAUNCH`,
`getMdxSessionStatus`, identity readiness and MDX reply in under 0.6 seconds.
Afterward the current Lounge connection sees only keepalive/no-op traffic:
no `remoteConnected` or `setPlaylist`. Earlier YouTube Music `2DB7CC49`
sessions did receive those commands. These attempts stop before playlist
handoff, media resolution and decoder load; changing transcoding cannot fix
that observed stage. The removed slow diagnostic does not explain these fast
attempts. Reply routing retains the requesting connection, sender and request ID.

A later regular YouTube attempt at 21:25 UTC replies to MDX in about 0.56 seconds
and receives `remoteConnected`, `setPlaylist` and `getVolume`. This is temporally
consistent with the reported successful Incognito test; receiver logs do not
identify the browser profile, so that association is not independently proven.

The public [YouTube remote module](https://www.youtube.com/s/player/a5c2aafe/player_es6.vflset/en_US/remote.js)
contains a relevant cache behavior. Executing its unchanged
`getAutomaticScreenByIds` function with a cached previous screen and a newly
reported screen selects/checks the old screen when automatic caching is on.
With caching disabled, it fetches/checks the new screen instead. Our receiver
rotates its Lounge screen identity across ownership generations while keeping
the Cast identity stable, so this is a concrete reconnect compatibility risk.
In that inspected build the offline-error path retries the same stale entry
without evicting it. A second synthetic reproduction confirms that clearing
only the affected entry repairs one connection, then the next screen rotation
repeats the failure. This is not established as a one-time cache migration.
The paired player storage helper places the automatic-screen cache in
`sessionStorage` and the device-ID map in `localStorage`; inspect both stores.
On its own, this deterministic vendor-code reproduction did not establish the
affected browser's cache contents, flags or failure cause. Short-lived MDX token
support is conditional: the sender's local `enableCastLoungeToken` flag must be enabled;
otherwise even a token-bearing status follows the old cache path. Its actual
status request contains only `type`, without support negotiation. The inspected
MDX dispatcher accepts `mdxSessionStatus` and `loungeToken`, with no supported
cache-reset message found. The owner's `ytcfg.EXPERIMENT_FLAGS` lookup returned
`undefined`, which did not determine the effective player configuration.
The later direct singleton/config lookup confirmed effective token mode false
(`enableCastLoungeToken=false`).
The owner's sanitized in-memory screen cache also differed from the current
receiver's screen suffix. Together with first-connect success and second-connect
failure in the same Incognito window, this confirms the stale-screen handoff
conflict for the tested browser. A token-only patch would not fix that client.

## Bounded owner-continuity fix

Core now supplies an opaque owner-generation key to app contexts. For a stopped
app, it retains only the latest actual owner's still-connected Cast sockets
and the exact Cast app ID. The same owner can explicitly relaunch that app after
STOP, virtual app CLOSE or direct replacement without changing this key. A
different owner or app replaces the key. Disconnected sockets lose their
continuation grant, and a new receiver process starts fresh. There is no
history of previous owners.

YouTube rebinds its saved screen only when both continuity keys are present
and equal. Missing keys, old identity files and real ownership changes retain
fresh-screen behavior. The shared provider still separates ordinary YouTube
and YouTube Music identity files and app IDs. A definitive invalid-screen
response permits one fresh replacement; transient errors preserve the screen
and do not overwrite its saved identity.

This follows the existing physical-controller ownership model: logical sender
IDs on one Cast TCP connection already share an owner. It does not add Chrome
tab/profile isolation, or replace active reconnect, grace, multisocket or
takeover decisions. A real takeover transfers the new key before the replacement
Lounge identity is published. Normal Stop cancels and joins the old Lounge
worker, with bounded abort/reap and drop guards for interrupted teardown.

Six new Core protocol regressions cover relaunch, virtual CLOSE, direct
replacement, observers, A/B/A ownership, actual takeover callbacks, physical
disconnect/new Hub, exact app changes and failed providers. YouTube fixtures
cover screen reuse/rotation, legacy files, invalid versus transient responses,
new-key propagation and worker cleanup. Same-owner reuse and interrupted
cleanup both failed on the earlier implementation. All 313 scoped Rust tests
pass, with three pre-existing explicitly ignored probes; independent review
found no open issue.

The initial built candidate `0.7.0.dev1+local.20261107.pr18` was activated on the
test laptop and is superseded by the lifecycle follow-up below. Readback of the loaded `/proc` executable matches the continuity hash
in the table above. All 28 installed Python files/assets match the candidate;
only the version label differs from the preceding package. Expected imports
and readiness for both routes pass. The actual release binary also passed 14
Cast/bridge checks covering TuneIn/DMR, controls and bidirectional volume with
emulated output and no audio. These checks do not verify physical YouTube
playback or repeated reconnects.

The ordered four-patch recipe and hashes, frozen sources, test/build manifests
and deployment record are retained in `.state/pr18-continuity-20261107-1/`.
Rollback remains available through
`cast-audio-receiver-before-speaker-continuity-20261107-1`. HA remains on dev20.

The fix prevents unnecessary screen rotation for this same-owner relaunch. It
does not silently edit a browser's already stale cache. A receiver/process
restart or a genuine owner change still needs fresh identity isolation; legacy
YouTube with token mode disabled may retain an obsolete screen after that
boundary. Retest from a fresh browser context and record first and repeated
connects separately. Do not claim universal ordinary-YouTube compatibility.

The owner subsequently reported partial improvement followed by renewed
ordinary-YouTube failures; the continuity candidate did not pass full acceptance. Next validation must distinguish Android
listing/authentication, browser MDX receipt, Lounge screen selection and
physical playback, preserving ownership
isolation and speaker identity. The confirmed YTM Web UI/control limitations in
[TESTING.md](TESTING.md) remain distinct from this handoff issue.


## Reopened incident: Android probes and YouTube lifecycle

The owner explicitly confirms that **all YouTube Music paths work**. Ordinary
YouTube Android currently omits the speakers; youtube.com reliably lists them
but can claim a connection while audio remains in the browser. Signed-in and
repeated Incognito attempts are affected.

After the continuity deployment, ordinary YouTube received playlists at 21:56:36
and 21:56:53 UTC, then reached only no-op traffic at 21:59:04. The saved screen
identity did not change between those launches. The same-owner fix addressed
one demonstrated rotation case, but rotation alone cannot explain every later
failure. Do not label this incident fixed from synthetic tests.

Allowlisted transport logs show Android `gms_cast_prober` reaching both laptop
receivers and requesting Eureka, app availability, status and device information.
The owner also used YouTube Music, so these probes cannot be attributed to the
ordinary YouTube app. They prove that a GMS client can reach the receivers, not
that ordinary YouTube discovers or accepts them. The phone's final selection/
filter decision and the originating app remain unverified.
Do not infer mDNS loss or change advertisements just from a missing app entry.
Google documents [special discovery mechanisms in YouTube](https://developers.google.com/cast/docs/discovery)
and directs mobile [YouTube speaker playback through YouTube Music](https://support.google.com/chromecast/answer/7181830?hl=en).
That supports investigating a sender-specific filter; it does not establish the
cause of this phone's earlier intermittent entries or make a TV profile acceptable.

Three additional receiver defects have reproducible fixes:

1. **Shared persistent app state.** All virtual receiver hubs received the same
   installation directory and used `apps/<app-key>`. One speaker could therefore
   inherit/overwrite another speaker's Lounge device identity and continuity
   record. Core now scopes app state by the stable receiver ID, encoded as a
   safe path component. This applies to all providers/backends. Relaunch and
   receiver restart retain that receiver's state. The ambiguous old shared
   directory is left intact and is not copied into every new receiver directory.
   Existing installations create independent app identities once; receiver Cast
   IDs, names, settings and output routes are retained. YouTube and Music still
   have separate Lounge identity files within their shared provider directory.
2. **Reversed discovery handshake.** The old provider answered
   `onSetDiscoveryDeviceId` (an acknowledgement), ignored `getDiscoveryDeviceId`
   (the request), and did not announce its Cast/Lounge association on bind.
   The corrected shared Lounge implementation announces on bind/rebind, answers
   requests, and does not echo acknowledgements. Failed feedback already causes
   rebind/reannouncement; no additional independent polling worker is introduced.
   Analysis of the public [YouTube receiver](https://www.youtube.com/tv?castv=2.0)
   and an isolated real-service exchange both confirm the message directions.
3. **Abandoned cloud channels.** Cancelling the local long poll does not send
   the BrowserChannel termination request. Normal Stop and true takeover now
   terminate the current SID before returning; the request has a 500 ms limit,
   within the existing bounded worker shutdown. Network reconnects do not invoke
   this final teardown. No ownership policy, Music volume mapping or active
   reconnect grace is removed.

An isolated real-service probe observed screen availability still online just
following explicit termination, and offline after approximately 17 seconds.
Therefore termination must not be described as immediate cache invalidation.
Another isolated probe verified that an old cloud controller can still issue a
command after terminating and rebinding the **same screen**. Channel termination
is not credential revocation; unrestricted persistent-screen reuse would weaken
the existing controller isolation and has not been adopted.

The new storage, request/acknowledgement, rebind announcement and termination
regressions failed before their fixes. The follow-up passes 332 Rust library
tests (Core 122, SDK 12, YouTube 151, TuneIn 15, discovery 11, platform 21), with
three pre-existing ignored probes, plus the SDK doctest. The locally built
release executable passes 14 silent Cast/bridge checks for TuneIn/DMR, playback
controls and both volume directions. These do not prove Android listing, real
YouTube handoff or physical output acceptance.

The candidate `0.7.0.dev1+local.20261107.ytlifecycle` was installed on the
test laptop and is superseded by the controls/audio follow-up below. The loaded executable matches the hash in the table, all 28 Python
files match, readiness is 2/2, and both Eureka/mDNS profiles remain audio-only.
The previous container is retained as
`cast-audio-receiver-before-youtube-lifecycle-20261107-1`; HA is unchanged.
Its source, protocol
probe summaries, tests and build records are in `.state/youtube-lifecycle-20261107-1/`.
The fifth reconstruction patch is
`patches/vibecast-youtube-lifecycle-review-20261107.patch`.
The existing legacy Chrome screen-cache conflict remains open across genuine
ownership changes/process restarts. Correcting the handshake and channel
lifecycle does not by itself repair a browser entry pointing at an older screen.
A permanent fix must account for both sender caching and controller ownership;
neither enabling display capabilities nor weakening takeover isolation is a
verified solution. Physical validation must separately record ordinary Android
listing, first/repeated youtube.com playback and unchanged Music behavior.


## Ordinary YouTube video selection and audio — 2026-11-08

The owner reports that reopening youtube.com now permits playback, but selecting
another video leaves the previous video playing until a page reload. The ordinary
Android YouTube app still does not list the speakers. YouTube Music remains a
working baseline. Browser startup improvement is not full reconnect acceptance.

Two receiver defects are now reproduced independently of discovery:

- **Explicit video selection was suppressed.** Sanitized receiver traces show
  `setPlaylist/VIDEO_ADDED` selecting a different video at 22:40:46 UTC; only the
  subsequent `VIDEO_SELECTED` after reload started it. A second pair at 22:43:02
  and 22:43:14 has the same pattern. An isolated ordinary-YouTube Lounge exchange
  confirms that sender `setPlaylist` becomes receiver `setPlaylist/VIDEO_ADDED`,
  whereas sender `addVideo` becomes `updatePlaylist`. The established Music
  workaround treats queue additions as enrichment to avoid late additions
  overriding a newer selection. That workaround is retained for Music. Ordinary
  YouTube now honors explicit `setPlaylist` selection; `updatePlaylist` still
  updates the queue without starting the newly added video.
- **Bitrate overrode audio content.** For the owner's public example
  [uMtsPAEEavE](https://www.youtube.com/watch?v=uMtsPAEEavE), native metadata has
  English Original/default at 131407 bps and an Indonesian dub at 163104 bps.
  Selecting the highest bitrate across every language can therefore displace the
  original. The ordinary-YouTube native audio profile now ranks original/default
  content before bitrate. Music keeps its previous resolver profile. The
  existing external extractor configuration is unchanged.

Ordinary YouTube `setAudioTrack` commands now select the exact requested track
for the current video. Position and pause state are retained; URL refresh uses
that same track. Pending changes can be superseded. An unavailable track leaves
already resolved audio playing, and only a successful resolution acknowledges
the new choice. A different video clears the prior video's track selection.
Music ignores these new commands as before. No ownership, reconnect, volume,
backend, capability advertisement or Cast identity changes are part of this
follow-up.

The selection, original-track and track-command regressions failed before their
fixes. The final suite passes 338 library tests (YouTube 157, Core 122, SDK 12,
TuneIn 15, discovery with mDNS 11, platform 21), plus the SDK doctest; three
pre-existing live probes remain ignored. Added coverage includes exact track
selection, paused playback, same-track URL refresh, failed/superseded requests,
repeat of the retained media, new-video defaults and unchanged Music behavior.
These tests do not establish Android listing or physical sender acceptance.

The additive sixth reconstruction patch is
`patches/vibecast-youtube-controls-review-20261108.patch`, applied after the five
patches listed in `.state/youtube-controls-20261108-1/FRONTEND-SOURCE-MANIFEST.json`.
Reconstruction from frontend commit `85918111ac68cbf837bf58835b5fd066615963ad`
matches all 114 recorded source inputs; the delta to the lifecycle candidate is
limited to `lib.rs`, `lounge.rs` and `resolver.rs` in `vibecast-apps-youtube`.
The private candidate `0.7.0.dev1+local.20261108.ytcontrols` is active on the test
laptop. All 14 silent release-binary checks pass. The loaded executable hash
matches the table; all 28 Python files match, both routes are ready, and both
Eureka/mDNS identities retain `display_supported=false` / `ca=199428`. Python
changes are limited to the private version label. The old container is retained
as `cast-audio-receiver-before-youtube-controls-20261108-1`; HA is unchanged.
Physical acceptance must check normal
Chrome video A → B without reload, the example video's original audio, manual
track switching and repeated disconnect/reconnect separately. Android discovery
and legacy browser-screen caching remain open; no TV advertisement is introduced.


## Owner feedback and Android-only observation — 2026-11-08

The owner confirms ordinary YouTube web playback now works sufficiently well
and YouTube Music still works. Occasional stale connected state remains, but
the owner explicitly requests no further web/Music reconnect changes for now.
The ordinary Android YouTube app now lists the receivers relatively reliably,
with speaker icons. Casting to them aborts immediately. This updates the earlier
missing-listing observation; no isolated test identifies which prior change
caused the listing improvement. Specific audio-track acceptance was not separately
reported.

The next investigation is restricted to the Android app's immediate abort. A
15-minute read-only observation of existing receiver logs records allowlisted
TLS/authentication, Cast launch/close and YouTube handoff events with hashed peer
identifiers. It does not restart the receiver, enable video capabilities or alter
working playback/reconnect behavior. A timed user reproduction is pending.

### First timed Android attempt

The owner confirms the earlier 00:33 local-time traffic was not a deliberate
YouTube attempt; the first reported attempt was around 00:35 on November 8
(23:35 UTC November 7). The recorded Cast connection queries receiver status
and joins the existing `2DB7CC49` Music transport. Its sender source belongs to
Google Play Services (`com.google.android.gms` family). Play Services is a Cast
transport and can mediate an active user selection; the source ID does not prove
a passive/background probe or identify the originating app. The subsequent
`QUEUE_GET_ITEM_IDS` request is rejected by the existing weak-ownership guard.
The trace does not establish whether that rejection caused the YouTube UI abort.
The guard prevents queue reads alone from displacing working playback; it has
not been changed in this discovery follow-up.

No ordinary-YouTube LAUNCH or MDX bootstrap was recorded on the test laptop in
this attempt. The precise target speaker and a comparison with an explicitly
ended prior Music/browser Cast session were requested. Without that association
the trace cannot establish whether the app aborts locally, uses another receiver
or attempts another startup path. At this point no Android device was connected
to the laptop via ADB. Filtered evidence is retained locally under
`.state/youtube-android-observation-20261108/`. Receiver behavior is unchanged.

### Second attempt and diagnostic-only follow-up

The user repeated the attempt and still reports immediate failure. At 23:42:01
UTC the preceding Music session was explicitly stopped. Subsequent traffic at
23:42:21 and 23:42:51 contains receiver/status/device/app-availability probes but
no YouTube LAUNCH or MDX bootstrap. Therefore the earlier Music session alone
does not explain the failure. The exact selected speaker remains unconfirmed.

Private candidate `0.7.0.dev1+local.20261108.ytandroiddiag` adds only debug
diagnostics to Core: receiver CONNECT SDK/platform classification, and each
app-availability result with a bounded hexadecimal app ID and request/connection
IDs. It does not change responses, ownership, playback, discovery or capabilities.
The seventh reconstruction patch is `patches/vibecast-android-diagnostics-20261108.patch`.
The Core suite passes 122 tests (two existing ignored probes), and the built
program passes 14 silent Cast/bridge checks. Independent seven-patch reconstruction
matches all 114 source inputs; only the diagnostic additions in Core hub differ
from the controls/audio baseline.

The diagnostic candidate was activated on the test laptop. Loaded-process hash and
all 28 Python files match; both routes are ready and both identities retain
`ca=199428` / `display_supported=false`. Python changes only the private version
label. The prior container is retained as
`cast-audio-receiver-before-youtube-android-diagnostics-20261108-1`; HA is unchanged.
Receiver-profile diagnostic events were confirmed in the running logs. The next
user attempt must establish which app availability was requested before abort;
this is instrumentation, not a claimed Android playback fix.

### Discovery recheck after diagnostic restart

The owner identifies the intended receiver as **Audio Lab Laptop** and reports
that only ordinary YouTube stopped listing the speakers; YouTube Music remains
working. Readback still verifies the diagnostic executable, two running Eureka
identities with display disabled and two local mDNS speaker advertisements at
`199428`. New ports are 39319/40003; the previous candidate used 32817/33839.
This establishes local advertisement and continuing Music use, not visibility
in ordinary YouTube. No new Android discovery queries were observed in the
initial post-restart interval. The timing alone does not prove a code regression.

A bounded 120-second observation of TCP SYN headers to those old/new ports was
started to check stale endpoint use. It records no application payloads. The
owner was asked to compare the Cast list before/after force-stopping only the
ordinary YouTube app, without deleting app data or modifying Music. No capability,
reconnect or playback change has been made.

### Visibility comparison: diagnostic build rolled back

Force-stopping/reopening ordinary YouTube did not restore listing. The bounded
120-second port observation completed without matching TCP SYNs to the old or
current laptop receiver ports. This is not proof of a particular client filter
or a general network failure; Music remains working. No new Android
app-availability requests were captured by the diagnostic build during this
interval.

The diagnostic-only build was conservatively rolled back to the exact
owner-accepted `0.7.0.dev1+local.20261108.ytcontrols` executable/package for a
comparison. Both routes are ready and all 28 Python files match the restored
manifest. Its known title/audio fixes are retained. The diagnostic container and
logs remain at `cast-audio-receiver-android-diagnostics-held-20261108-1`. This
rollback is not a claim that diagnostic logging caused the disappearance;
restarting also reallocates ports and changes discovery timing. Android listing
needs a new user check before drawing a conclusion. HA is unchanged.

### USB evidence and app-filtered discovery — 2026-11-08

At the first USB comparison after rollback, the owner reported that neither
YouTube nor YouTube Music listed the speakers. This updated the earlier Music/listing comparison;
it does not establish a regression in Music playback or explain why previously
cached devices were visible. No isolated comparison has shown that the diagnostic
patch caused the disappearance.

The connected phone inventory establishes these versions:

| Component | Observed version |
| --- | --- |
| Android | 15, SDK 35 |
| YouTube | 21.40.162, version code 1561301422 |
| YouTube Music | 9.44.52, version code 94452240 |
| Google Play Services | 26.43.30 (260400-1006944126), version code 264330035 |

The bounded LAN capture contains 164 DNS questions, of which 154 are attributed
to the connected phone. Those include 31 base `_googlecast._tcp.local.` questions, nine
`_233637DE._sub._googlecast._tcp.local.` questions and 25
`_2DB7CC49._sub._googlecast._tcp.local.` questions. Other app-subtype questions
account for the remaining phone questions. These are actual phone queries for
the ordinary YouTube and Music app IDs. DNS traffic shared through Play Services does not
by itself attribute every query to a foreground app action.

A separate LAN probe against the restored controls build received these PTR
answers for the two owned receivers:

| Requested browse type | Owned receiver PTR answers |
| --- | ---: |
| Base `_googlecast._tcp.local.` | 2 |
| YouTube `_233637DE._sub._googlecast._tcp.local.` | 0 |
| Music `_2DB7CC49._sub._googlecast._tcp.local.` | 0 |

The receiver registered only its base service, while this phone also uses
app-filtered browse types. That is a concrete discovery gap shared by supported
apps and output backends. It can explain a missed subtype browse; it does not
establish the complete cause of intermittent listings or the later cast abort.

The candidate `mdns-app-discovery-20261108-1` adds subtype PTRs from the actual
`AppRegistry`, including every valid registered Cast app ID. Each points to the
same base service instance, host, port and TXT record through one mDNS daemon.
The small local `mdns-sd` extension answers the requested subtype directly,
applies known-answer suppression to that PTR, and announces/withdraws every
subtype together. It retains `ca=199428`, matching audio-only `DEVICE_INFO` and
Eureka capabilities. It does not enable display capabilities or change the
speaker icon, playback, queue ownership, reconnect or Music control behavior.
Regression coverage checks service identity, subtype validation, query answers,
known-answer suppression and goodbyes.

The private candidate `0.7.0.dev1+local.20261108.mdnsapps` is now installed on
the test laptop. The loaded `/proc` executable matches SHA-256
`02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b`;
all 28 installed Python files match the candidate and both routes are ready.
Readback retains `ca=199428` and Eureka `display_supported=false`. Rollback is
available as `cast-audio-receiver-before-mdns-app-discovery-20261108-1`.

The repeated LAN probe now receives two owned PTR answers for each of the base,
YouTube and Music browse types: **2/0/0 before, 2/2/2 after**. This verifies the
network response correction. The subsequent phone test gives a partial result:

- YouTube and YouTube Music both show both configured speakers.
- Music connects and plays audio as before.
- Tapping a speaker in ordinary YouTube produces no recognizable connection or
  audio according to the owner. The speaker entries temporarily disappear and
  return after a wait.

Receiver logs for this test interval contain one Music `2DB7CC49` LAUNCH and no
ordinary-YouTube `233637DE` LAUNCH. The missing subtype responses are corrected
and phone listing has improved, but reliable continued discovery and ordinary
YouTube casting are **not achieved**. The remaining failure occurs before any
recorded ordinary-YouTube app launch; the precise sender-side reason is still
unproven. This result does not justify changing working Music behavior or the
speaker identity.

Static inspection of public YouTube and Music APKs also found audio-only device
filters. Ordinary YouTube uses a server-configurable opt-in whose static default
is false. Music has its own configuration/account-metadata condition; the
obfuscated account field does not establish a subscription requirement. The
effective values on this phone are unknown. These are additional app-dependent
gates, separate from the missing DNS subtype response. Some MDX-only route paths
avoid this specific Cast-device filter, but the origin of the owner's earlier
visible entries is unproven. Neither these findings nor Google's general speaker
guidance proves that this phone requires a TV identity. Keep the speaker profile
and inspect the next observed failure before proposing another change.

### Active Android picker and app-side selection guard

A public activity/fragment inspection identifies the current picker as `anhv`
with `mState=7`, added=true and hidden=false; YouTube is resumed. Its RecyclerView
row binding is traced through `anic`/`anil`, `anhx.f` and `anhw` to
`anhk.onClick`. This controller receives the injected permission `nA`, which is
constant false in YouTube 21.40.162. Thus the additional selection guard is also
present in the currently displayed picker. The earlier `anjo`/`anjn` chooser
analysis was a static reference, not the observed active fragment.

The configurable **list filter** and this **selection guard** are separate.
For an audio-only `CastDevice`, the latter emits a local `ange` event instead of
invoking the selection handler; the row handler can then dismiss the picker.
This branch does not emit the audio-disallowed log phrase. A preceding account
dialog callback is a separate route. The owner confirms normal signed-in use;
the identified Incognito/pseudonymous-account exceptions are app/account decisions
that receiver metadata cannot set. Further row/session guards also exist.

A later, separate `onRouteSelected` guard also has a genuine early return, but
requires `angn.c()` as well as the audio-only predicate. That value combines
component enablement with app configuration and is cached. Public PackageManager
state currently lists `MediaTransferReceiver` as disabled; this neither determines
the cached/configuration value nor affects the earlier chooser click guard.
The complete `c()` runtime value cannot be read from that public component state.

During the phone test, the observed connections to the test laptop were Music
connections; no ordinary YouTube TCP connection or `233637DE` LAUNCH was recorded.
Two null-provider-descriptor warnings came from the GMS persistent Cast provider.
Neither warning proves the reason for the app abort. The local selection guard
fits the observed lack of a YouTube connection closely, but the clicked row's
complete route object and executed branch were not instrumented. No private app
data was inspected.

Public MediaRouter metadata contains the owned receivers under that GMS provider
and one observed `deviceType=2`. The owner also confirms speaker icons.
In the inspected picker, `anky.a()` supplies the route's device type; the icon
code distinguishes TV type 1 from speaker type 2. The standard MDX provider
`angm` builds its DIAL/cloud-screen routes with type 1, including `anks`/`ankx`
screens. The [AndroidX type definitions](https://developer.android.com/reference/androidx/mediarouter/media/MediaRouter.RouteInfo#DEVICE_TYPE_SPEAKER)
confirm those numeric meanings. These observations support the native speaker
route explanation. They do not expose the clicked row's `CastDevice` extras or
capability bits; extras absent from a public dump must not be read as an absent
`CastDevice` in the app.

No concrete omitted receiver field has been found that establishes another
supported speaker path. The existing MDX discovery/device-ID fields are sent
after LAUNCH and cannot repair an earlier local rejection. The inspected app
deduplicates a matching DIAL UUID against its native Cast route, with a separate
capability/experiment exception that our speaker profile does not satisfy.
Cloud-paired routes without `CastDevice` exist, but obtaining and maintaining
them would require a separate, unverified pairing/ownership architecture;
their default TV device type also fails the requested speaker presentation.
This does not establish impossibility for all app versions or MDX providers.

Google's current [speaker playback guidance](https://support.google.com/googlehome/answer/7181830?hl=en)
directs users to YouTube Music for YouTube content on speakers. That supports an
app-specific product boundary; it does not prove that every app version or route
requires a TV profile. No additional receiver change or TV emulation follows
from this finding.
