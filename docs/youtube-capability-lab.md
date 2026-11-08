# YouTube capability and speaker-icon lab

Historical research record. The subsequently authorized `0.7.0-dev2` product
implementation is documented in [dual Cast identities](dual-cast-identities.md).
Statements below about no product implementation describe the isolated lab
stage; its measurements remain separate from the later real-output tests.

Investigation date: 2026-11-08. This continues the
[PR #18 investigation](youtube-discovery-pr18.md). The target is casting from
the ordinary Android YouTube app while keeping the receiver's individual
speaker presentation. YouTube Music and the accepted browser behavior remain
the working baseline.

The owner authorized autonomous capability experiments and ADB UI observation.
This authorizes a temporary lab, not a TV option in the product. If the only
working profile presents a television, record that result and stop without
implementing the option. No public release or successful hybrid profile is
claimed here.

Follow-up scope: the owner would also accept a TV icon in ordinary YouTube if
the same receiver still appears as a speaker in YouTube Music. This is a
separate per-app rendering hypothesis to verify, not permission for a universal
TV identity or a product TV toggle. The initial secure-lock and Xiaomi
`INJECT_EVENTS` restrictions were resolved with the owner's help. Authorized
native UI trials now use screenshots and exact, freshly suffixed test names;
they do not clear app data or change the signed-in account.

**Result:** no stable **single-identity** combination meeting that presentation
requirement was established in the tested versions. The full PR #18 profile
accepts ordinary YouTube media but presents a TV in both apps. A deliberately
conflicting mDNS/DEVICE_INFO profile can initially show Music as a speaker and
YouTube as a TV, but its presentation changes with the sequence and session
state. It is not a verified speaker-preserving solution.

A later isolated test did establish a different, two-identity arrangement:
one stable UUID/port presents an audio-only speaker exclusively to YouTube
Music, while a second stable UUID/port presents a video-capable TV exclusively
to ordinary YouTube. Both app orders produced the intended native route,
app-specific LAUNCH and silent LOAD after discovery converged. This proves the
per-app split is technically possible; it does **not** make one Cast identity
render differently between apps, verify audible playback, or implement a
product option. The default speaker identity remains unchanged.

## What the old experiments established

The historical records contain several profiles, but no verified combination
of ordinary YouTube-app playback and an individual speaker icon.

| Stand | mDNS `ca` | Cast `DEVICE_INFO.deviceCapabilities` | Eureka display | Evidence and limit |
| --- | ---: | ---: | --- | --- |
| Purchased AirReceiver | 4101 | Not separately recorded | true | Observed as a TV; its Cast path accepted the tested sender. |
| Transparent speaker shim | 4100 | Forwarded unchanged from AirReceiver | false | Rewrote mDNS/setup only. It did not terminate encrypted Cast or establish a successful hybrid profile. |
| v0.4.0, `4364498` | 4100 | 4101 | No audio TOML supplied by this commit | Preserved bundle and source patch; output signals disagreed. |
| v0.4.1, `bdfdf40` | 199428 | 4101 | false in the new audio TOML | Preserved bundle; the Cast-channel response still included video. |
| v0.4.2, `51a52e9` | 199428 | 199428 | false with audio TOML | Owner confirmed the speaker icon. Authentication still failed at that early stage, before app launch. |
| Initially audited current laptop | 199428 | 199428 | true through defaults | Actual installed readback; this mismatch was not established as the reason for intermittent listing. |
| Current app-subtype candidate | 199428 | 199428 | false | Both Android apps listed the speakers; Music played. Ordinary YouTube selection failed and entries temporarily disappeared. |
| PR #18 first hardware test | 199429 | 199428 | true with the option enabled | Author reported that ordinary Android YouTube still did not list the receiver. |
| PR #18 after `b0ed527` | 199429 | 199429 | true with the option enabled | Author confirmed Android YouTube playback through AirPlay to a Sonos Era 100. A retained speaker icon was not confirmed. |

The local v0.4.0 and v0.4.1 Git bundles point to `4364498` and `bdfdf40`
respectively. The retained complete source snapshots for v0.5.0 and
dev4/5/6/11/12 explicitly set both bitfields to `199428`; they do not reveal a
different successful hybrid profile.

Sources: [original speaker profiles](native-cast-speaker.md),
[transparent shim boundaries](airreceiver-apk-5.1.7.md#speaker-shim-experiment),
[v0.4.2 speaker-icon confirmation](vibecast-audio-frontend.md#live-verification-and-remaining-auth-failure),
[installed default mismatch](youtube-discovery-pr18.md), and the author's
[PR #18 hardware follow-up](https://github.com/Allcrafter1/cast-audio-receiver-lab/pull/18).
The PR result verifies that author's sender/output combination with video
enabled; it does not verify our requested speaker presentation.

## Installed sender code: icon and selection are separate decisions

The public installed APKs were copied through normal package paths and
inspected locally. This analysis does not inspect private app data and does not
establish which branch executed on a particular tap.

| Package | Installed version | Public base-APK SHA-256 |
| --- | --- | --- |
| YouTube | 21.40.162 | `6f8251e0d40bbcb78f2fa88a290a21f8ee6d8790b33af5826b3f76bb044f68f8` |
| YouTube Music | 9.44.52 | `22522e605323ff364e40ce1fcc5dfccc222de236f2a057d5a61edfb0f94bc2ed` |
| Google Play services | 26.43.30 (260400-1006944126), code 264330035 | `8395c70a5e4ffbe2712aea7e1045d700b282f0a67d19b80686c595c991f12112` |

Private analysis files are under
`/tmp/cast-youtube-public-apk-20261108/`. They are evidence for these exact
versions, not a claim about every YouTube version or client.

Let `A` mean capability bit 4 (`AUDIO_OUT`) is set, and `V` mean bit 1
(`VIDEO_OUT`) is set. The inspected methods implement:

```text
GMS base RouteInfo.deviceType = A ? (V ? 1 : 2) : 0
YouTube audioOnly             = A && !V
```

GMS `bkni.b(CastDevice)` supplies the first expression. `bjdn.o(biqn)` passes
it to `ryu.j(int)`, which writes the route descriptor's `deviceType`. A scan of
all DEX files in this GMS APK found only two callers of `bkni.b`: this route
publisher and `bjqn.d`, which chooses a notification icon.

YouTube's `fca.b()` reads `deviceType`; `fdb` copies it into its route field
`o`, and `anky.a()` exposes that field. The inspected picker renderer,
`anil.b(anky)`, selects TV artwork for type 1 and individual speaker artwork
for type 2. Group and generic Cast artwork are fallback cases. The separate
`CastDevice.b()` classification enum is not this route-icon mapping.

YouTube `anhl.e(CastDevice)` implements the second expression. The active
picker family reaches `anhk.onClick` through `anil` → `anhx.f` → `anhw`.
Its allow-audio provider is `iim.nA` → `iil` case 783, a constant false in
this build. On the normal selection path an audio-only route emits a local
event instead of invoking the selection handler. The account-dialog callback
is a separate path; receiver metadata cannot choose that account state.

Both APKs use the raw capability mask for these output-bit tests. GMS
`CastDevice.g` delegates to `bjat.a`; YouTube `CastDevice.e` delegates to
`ahtq.d`. Each tests `(mask & bit) == bit`. The parcel writers/creators carry
the capability field separately from Eureka information. Neither output
predicate consults `display_supported`, the model name or an icon URL.

For a normal standalone route using the **same capability snapshot** for its
icon and Cast extras, type 2 and the rejection predicate are therefore the
same condition: `A && !V`. Other bits cannot change that equality. This is a
bounded static result, not a successful or failed live playback test and not
a universal impossibility claim.

## Boundaries that the lab must keep visible

**Group overrides.** GMS `bjdn.o` can overwrite the base type with 1000 for a
dynamic group (bit 64), gated by `jzab.c()`. Its publishing method also creates
a type-1000 copy for group devices. The inspected group predicate is
`(bit32 && !bit64 && !bit128) || bit64`. Such a route can reach YouTube's group
artwork fallback even with video enabled. It is a claimed Cast group, with
member/session/controller behavior, rather than an individual speaker. A
speaker-group icon alone would not meet the individual-speaker success
criterion or establish working group semantics. Member descriptors have
their own construction path and do not all carry the ordinary Cast extras.

**No audio-output bit.** Clearing AUDIO_OUT while leaving VIDEO_OUT clear,
for example `199424`, makes the YouTube audio-only predicate false. GMS's base
type becomes 0, whose ordinary picker fallback is generic Cast artwork. This
does not preserve a real type-2 speaker and advertises no audio output. It is
a diagnostic candidate, not a proposed product profile. Setting VIDEO_OUT
while AUDIO_OUT remains clear likewise gives base type 0.

**Capability snapshots can differ.** In `bjdn.o`, icon classification reads
`biqn.d()`, while the normal route's `EXTRA_CAST_DEVICE` comes from `biqn.b`.
The former uses mutable `biqj.d` when present; the latter is a stored
`CastDevice`. `bink.a` constructs a new `biqn(biqj, ...)` for publication,
whose constructor initially copies that same current `biqj.d` into `b` and
retains the `biqj` reference. `biqj.i` can subsequently replace `d` with an
updated device. Thus construction starts with matching snapshots, but the
inspected code alone does not rule out later divergence. No stable,
receiver-controlled way to obtain a speaker icon plus non-audio-only extras
has been established. Deliberately conflicting mDNS and DEVICE_INFO responses
must be measured, including after refresh and reconnect; transient cache
appearance is insufficient evidence of a solution.

**Different icons in YouTube and Music.** The owner would accept ordinary
YouTube presenting a TV if Music retained its speaker presentation. The installed
Music 9.44.52 code does not currently establish that path: `xwj.a()` returns the
same route `deviceType` field. Its picker renderers `xto.d` and `xtq.e` select TV
for type 1 and speaker for type 2, as does the `xtm` device control. The newer
Elements path `xlw.invoke` maps type 1 to enum value 2 and type 2, type 12 and
group cases to enum value 3; those enum assets were not independently decoded.
Thus the normal shared native route with VIDEO_OUT is expected to appear as a
TV in both apps. Resource decoding independently confirms that Music's ordinary
picker type-1 resource `2131233674` is `yt_outline_tv_vd_theme_24` (screen and
stand), while type-2 resource `2131233644` is
`yt_outline_speaker_vd_theme_24` (speaker cabinet and drivers). This is not an
inference solely from numeric route types. Music's acceptance of audio-only
devices is a separate decision;
it does not imply a music-specific icon override. Live screenshots confirm TV
artwork in both apps for the complete PR #18 profile. Fresh-device tests can
also produce different artwork between apps for deliberately mismatched
profiles; these use different UUIDs and cannot establish that one receiver
keeps different icons in the two apps. Same-UUID comparisons are required.

**Other providers and account paths.** The inspected YouTube MDX/DIAL/cloud
provider `angm` sets its routes to type 1. Routes without native Cast extras,
account-specific callback paths, and other app versions have different
boundaries. They do not establish a working native speaker combination here.

## Isolated capability test setup and validation

All **25 profiles / 50 app-profile observations** completed without automation
errors on the authorized Android 15 phone. The
[complete result table](youtube-capability-results-20261108.md) and
[sanitized data](youtube-capability-results-20261108.json) preserve the four
inputs, actual icon, selection, known app LAUNCH ID and silent LOAD count.
The two app columns use separate fresh identities; same-device comparisons
are recorded separately. These observations are bounded to the listed app
versions, signed-in account, LAN and finite search window.

Four additional runs produced **16 same-device app observations**, with two
rounds per run and both app orders for the most promising mismatch. The
[paired sequence table](youtube-capability-paired-20261108.md) and
[sanitized paired data](youtube-capability-paired-20261108.json) retain these
separately from the fresh-UUID matrix.

| Profile | Four inputs: mDNS / DEVICE_INFO / Eureka / API display | Observed result |
| --- | --- | --- |
| Speaker baseline | 199428 / 199428 / false / false | Music speaker, LAUNCH and silent LOAD. Ordinary YouTube was not seen in the bounded paired search; an earlier listed-speaker calibration tap produced no LAUNCH/LOAD. |
| Consistent VIDEO_OUT, display off | 199429 / 199429 / false / false | TV in both apps; each launched its own app and supplied a silent LOAD. Neither display flag was needed for this positive protocol control. |
| Complete PR #18 profile | 199429 / 199429 / true / true | TV in both apps; paired first-round LAUNCH/LOAD in each app, plus repeated YouTube LOAD. |
| Reverse mismatch, Music first | 199428 / 199429 / false / false | Music initially speaker with LOAD; YouTube then TV with LOAD; the subsequent Music controller was TV. The requested presentation did not persist. |
| Same mismatch, YouTube first | 199428 / 199429 / false / false | YouTube speaker with no LAUNCH/LOAD; Music picker TV with LOAD, later Music controller speaker. Different icons alone did not establish working YouTube casting. |
| Group/no-output diagnostics | See the full matrix | Generic Cast or TV artwork; no supported individual-speaker solution. Group/pair semantics are not implemented. |

This contradicts neither the author's confirmed Sonos/AirPlay audio test nor
the earlier historical speaker icon. It separates identity from acceptance.
Some conflicting profiles were accepted here despite the author's initial
failure, so his field-consistency observation is not generalized into a
universal filtering rule. Deliberately disagreeing fields did not yield a
stable presentation in our paired checks.

## Dual-identity app-subtype result

`GET_DEVICE_INFO` cannot reliably choose an identity per calling app. In the
captured Android exchanges its request carries only `type` and `requestId`.
The Cast envelope has an opaque sender ID, and CONNECT identifies the generic
Google Cast prober rather than YouTube or YouTube Music. Vibecast would ignore
unknown JSON fields, but the relevant app ID is not present to parse.

The app IDs appear in separate messages: `GET_APP_AVAILABILITY` can contain
`233637DE` (YouTube), `2DB7CC49` (YouTube Music), or both, and LAUNCH identifies
the selected app only after route selection. Play services aggregates the
criteria of active clients, so even an Availability request containing both
IDs does not identify its originating app. Delaying `GET_DEVICE_INFO` until an
Availability request arrives would therefore be a timing heuristic, not a
protocol-level solution.

The successful isolated arrangement avoids that ambiguity by keeping two
internally consistent endpoints:

| Identity | UUID/port | mDNS and Cast capability mask | Discovery | Availability response |
| --- | --- | ---: | --- | --- |
| Speaker | Separate, stable | 199428 | Base `_googlecast._tcp` plus only `_2DB7CC49` Music subtype | Music available; YouTube unavailable |
| YouTube TV | Separate, stable | 199429 | Only `_233637DE` YouTube subtype; base PTR suppressed in the lab | YouTube available; Music unavailable |

Both Eureka and configured API display flags remained false; the TV route is
caused by the consistent VIDEO_OUT capability, not by enabling those display
flags. The subtype-only base-PTR suppression and Availability allow-list are
lab-only changes. They are gated by `CAST_LAB_APP_SUBTYPE_ONLY`,
`CAST_LAB_MDNS_SUBTYPE_ONLY` and `CAST_LAB_APP_AVAILABILITY_ONLY`; defaults are
unchanged when those variables are absent. The tested dual-identity lab binary
has SHA-256
`2eb81cee839fda3ada9aa1df139cee571c74c3248602bc959ba2234ee615030e`;
it was never installed as the product executable.
The exact lab-only source delta is retained as
[`vibecast-youtube-dual-identity-lab-20261108.patch`](../patches/vibecast-youtube-dual-identity-lab-20261108.patch).

Direct on-wire probes confirmed all six intended PTR properties: the Speaker
was present in base and Music discovery but absent from YouTube discovery; the
TV was present in YouTube discovery but absent from base and Music discovery.
A Cast-protocol probe then confirmed the inverse Availability maps for both
app IDs. This matters because DNS-SD subtypes alone are additive and do not
normally hide a service from base browsing.

The authorized Android UI test used the installed versions listed above,
fresh exact names, no app-data clearing and a silent player:

| Stable sequence | Ordinary YouTube | YouTube Music |
| --- | --- | --- |
| YouTube, then Music | Only the TV identity was visible; `233637DE` LAUNCH and silent LOAD reached only the TV endpoint. | Only the Speaker identity was visible; `2DB7CC49` LAUNCH and silent LOAD reached only the Speaker endpoint. |
| Music, then YouTube | Only the TV identity was visible and launched/loaded on the TV endpoint. | Only the Speaker identity was visible and launched/loaded on the Speaker endpoint. |

The screenshots and MediaRouter diagnostics also distinguish this from an
MDX-only duplicate: the selected routes carried native Google Cast device
UUIDs, and the matching Cast V2 receiver logs recorded the expected LAUNCH.
The other endpoint remained quiet in every successful selection.

A cache stress case exposed an important operational constraint. Rapidly
stopping the lab and creating another UUID left the previous Music route in
Play services while the new exact route appeared dimmed and could not be
selected. No route-controller creation or receiver connection occurred for
the ignored taps. Keeping the new UUID stable until discovery converged made
the same route selectable; Music then launched and loaded normally, followed
by a successful YouTube selection. This is evidence for stable product UUIDs
and careful session cleanup, not evidence that the capability split failed.

The result is intentionally bounded. The silent player did not fetch, decode
or render media, so audible output, track language, seeking, reconnect and
shared backend/volume ownership remain unverified. Exposing two product
identities would also require explicit arbitration so they control one output.
No dual-identity product option was implemented, and this experiment is not a
recommendation to replace the default speaker identity with a TV identity.

The initial row parser missed one already-connected Music controller because
its title lives outside the short selectable-row structure. Original
`raw_listed=false` is retained; the paired record adds the UUID-matched visual
and XML correction. The controller's speaker icon was real, not evidence that
the receiver disappeared. A later YouTube row had a playback-status subtitle
that shifted its icon below the title; its clipped hash remains unclassified,
and its TV artwork is established by visual review instead. Controller presence
does not count as a new selection, LAUNCH or LOAD. These corrections affect
the observation helpers only, not the receiver or reconnect behavior.

The matrix harness is built and staged in
`.state/youtube-capability-matrix-20261108-1/`, with remote lab files under
`~/cast-hybrid-20261108-1` on the test host. The validated runtime is a separate,
silent Docker lab without audio devices. The frozen working receiver baseline
and its identities are kept intact. No product TV toggle is implemented.

The matrix varies four layers independently: mDNS `ca`, Cast
`DEVICE_INFO.deviceCapabilities`, Eureka `display_supported`, and the
configured outgoing `CAST-DEVICE-CAPABILITIES` display flag. It includes all
16 binary combinations of these layers plus nine model, output-bit and
group/pair diagnostics. These are temporary experimental profiles, not
selectable product behavior. `video-eureka-on-api-on` matches all four PR #18
settings; `video-eureka-on` leaves the outgoing API display flag false.

The initial **17-profile** version passed isolated information-query smoke checks: actual mDNS
`ca`, Cast `DEVICE_INFO.deviceCapabilities` and Eureka display/group flags matched
their inputs. The final run bound DNS-SD queries to the laptop's LAN interface;
the same-host resolver can still aggregate addresses from other local interfaces,
so this is not a packet-capture claim about addresses learned by the phone.
That first smoke run covered all eight combinations of mDNS video bit,
Cast-info video bit and Eureka display, plus diagnostics. The extended 25-profile
matrix adds the eight API-display counterparts. Every native test starts with
the same information queries. The API flag has configuration and shared-client
`default_headers` source evidence, not an intercepted TLS header. Information
queries alone establish the setup, not native sender acceptance or playback.

The [portable harness and commands](../tools/youtube_capability_lab/README.md)
are retained in the repository. Two silent-player behavior tests pass; an
independent preparation from the frozen baseline reproduces both patched source
files exactly. Private `WIRE-SMOKE.json`, `BUILD-MANIFEST.json`,
`PUBLIC-APK-MAPPING.json` and `FINAL-AUDIT.json` retain the evidence. The lab
binary SHA-256 is
`651091476e70316669a373e510701330977577cf1f8822d1c56cc8098cacb0d1`;
it is a research binary, never the installed product executable.

The final post-test audit confirms the lab container is removed and the
loaded product executable remains
`02d1494745094f9df3e61df3b25a5e557ebcb7c2c3a1251e073e1e353feb847b`,
all 28 runtime files match, both enabled routes remain ready, mDNS remains
`199428` and both Eureka display flags remain false. Home Assistant was not
changed. The original phone USB stay-awake setting was restored, test apps were
closed and the temporary phone XML removed. No TV mode or product capability
override was added. All 50 matrix cases and four paired runs completed with
their container teardowns verified.

The owner resolved the initial secure-lock and input-permission obstacles.
Native UI trials now cover listing/icon capture, selection, receiver app LAUNCH
and silent media LOAD. Each app/profile gets a fresh UUID, suffixed name and
separate data directory; apps restart without clearing their data. This avoids
clicking a previous test identity, but the two app columns initially concern
different devices. A paired pass must keep the same UUID between apps before
claiming app-dependent presentation.

The phone's picker can retain old or dimmed entries and can expose more than
one row for a name. Exact-label selection uses the highest-contrast visible
matching icon. Dimmed entries are recorded without being tapped, not as failed
Cast attempts. The bounded search does not prove Discovery/APP_AVAILABILITY
convergence or identify the provider behind each row. A missing row means not
observed in that window, not universal absence. Only actual screenshot artwork
is classified; unknown crops require visual review.

The silent player acknowledges media commands without fetching, decoding or
rendering audio. A LAUNCH or LOAD therefore does not verify audible playback,
title changes, audio-language selection or disconnect/reconnect. Fresh queues
and a paused YouTube/Music MAIN start can also leave a session without a LOAD.
Any promising same-device presentation still needs separate real-output and
reconnect acceptance. No playback/session logic is changed by this lab.

## Next session on the prepared laptop

No rebuild or reinstall is required. The private laptop controller can start
one isolated profile alongside the working receiver:

```bash
python3 ~/cast-hybrid-20261108-1/control.py run --profile video-info-only
```

It verifies the unchanged baseline binary and health before starting. Begin
with `speaker`, then compare `video-info-only`, `video-mdns-only` and
`video-eureka-off`; use `video-eureka-on-api-on` for the complete PR #18 control.
With `CAST_LAB_IDENTITY_EPOCH`, each attempt has a fresh UUID and a suffixed
`Audio Lab Probe <profile>` name recorded in `lab-identity.json`. Compare actual native
YouTube screenshots and selection/LAUNCH evidence before considering any
real-output test. Group/no-output cases remain unsupported diagnostic identities.

An unlocked phone and working authorized ADB input injection are prerequisites
for autonomous UI operation. Do not change accounts,
clear app data, or infer a successful reconnect from a cached icon.

Stop the temporary receiver after every session:

```bash
python3 ~/cast-hybrid-20261108-1/control.py stop
```

The controller removes only its separately labelled lab container; the working
receiver and its data are retained. A promising speaker-looking route must keep
that identity after refresh/reconnect and eventually pass actual audio and Music
regression checks. If success requires television presentation, stop without
implementing a TV option.
