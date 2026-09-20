# Autonomous verification — 0.6.0.dev4

No manual interaction or audible test is required for these changes. Existing
queue/prefetch, format validation, extractor, startup buffer and persistent
AirPlay transport decisions are retained.

## Artwork

The user selected centered **1:1**, not 4:3. AirPlay's existing bounded FFmpeg
conversion now crops a centered square before reducing to at most 512×512.
Landscape images retain their full height; portrait images retain full width.
Smaller images are not upscaled. No padding is added. This is geometric cropping,
not detection/removal of every border baked into a source image; meaningful
content outside the square is intentionally discarded.

Three synthetic-image FFmpeg tests verify landscape, portrait, square and large
images with contrasting edge strips. All pass on the actual Linux FFmpeg.
Cancellation/timeout and old-track artwork cleanup tests remain in the suite.
No new dependency or playback pipeline is introduced.

**Remaining limitation:** Cast/HA still see the original artwork URL. The Python
adapter cannot change metadata already published by the Rust frontend merely by
cropping its local AirPlay JPEG. Serving transformed covers to HA would require
an explicit shared image endpoint/cache or another supported source image URL.
That is not silently included in this small output-only correction. Actual
rendering on Yamaha/HomePod and HA remains a later acceptance check.

## Resource measurement

`tools/resource_profile.py` samples only explicitly selected Linux process trees:

```sh
python tools/resource_profile.py --pid FRONTEND_PID --pid MANAGER_PID \
  --samples 30 --interval 1
```

The tool does not initiate playback, change processes, inspect environment or
export command lines. It includes descendants and avoids counting overlapping
trees twice. Root exit/PID reuse stops measurement. PSS unavailable because of
permissions is reported as null, not zero. RSS sums double-count shared pages;
PSS is preferable for combined footprint. 100% CPU means one fully used core.
Intervals include sampling overhead. Very short-lived processes can escape the
sampler; exits/new processes are counted as a warning that CPU is incomplete.
These are sampled values, not guaranteed peaks or a cgroup accounting substitute.

Five quiet samples of the deployed dev3 frontend + manager trees (five processes,
including the resident mpv) measured 231824 KiB RSS (~226.4 MiB), about 175902 KiB
PSS (~171.8 MiB), and 0–0.98% of one core. No playback was initiated. This is a
short quiescent observation, **not a loading/playback benchmark**, not a memory
minimum, and not proof of small-device suitability. No yt-dlp worker was added.
Future load/playback comparisons must use the same selected roots, title/output,
sample duration and versions. Keep live compatibility tests opt-in.

## Deployment / acceptance

Dev4 Python: 129 tests pass on Linux (including FFmpeg); locally 126
pass and three FFmpeg tests skip because that executable is absent.
The package version and changelog are updated. Deployment and frontend tests
are tracked separately in the Working Plan. Dev4 is deployed from
`.state/manager-dev4`; frontend320893, manager320894, adapters320900/320901.
Three configured routes retained; both enabled adapters registered; live
Chromium direct-entry/list/delete-controls/favicon/reload checks pass.

The additional app-CLOSE regression fails before and passes after a small
platform status refresh: closing only the app channel no longer waits for a
socket disconnect to announce an empty app list. 135 deterministic Rust tests
pass, one live YouTube test ignored. Thirteen real-mpv DMR cases pass with the
new zero-PCM fixture option. Source/hash records are in the dev4 source lock;
previous dev3 binaries/source and private launch inputs remain for rollback.

After the initial activation, the independently validated 479-window private
bundle was tested with the same 13 silent DMR cases and activated. Frontend is
now PID320979; manager/adapters unchanged and reconnected. The bundle retains
every original full entry unchanged, covers through 2029-04-27 UTC without gaps,
and remains subject to future sender trust/revocation changes. Previous bundle
is retained. No Android time/network changes occurred during this continuation.

Dependency tooling added three further tests: current local suite132, three
FFmpeg skips. The CPython3.12 hash-locked fresh environment passes pip check.
The built dev4 wheel installs offline with all UI assets and reports the correct
version; wheel SHA256 is
`27ad0cd62d9ef07a58433271cd77d2f03c4469f174706628473096a289d6dac3`.
See dependency-locks.md and THIRD_PARTY_NOTICES.md for audit boundaries.

Later user checks, without blocking autonomous work:

- End a YT Music cast while HA observes; expect idle/unavailable media controls,
  then a clean reconnect.
- SWR3 and the local file: capture which metadata/controls are actually supplied;
  do not infer radio pause support from an image-only change.
- Inspect square artwork on the AirPlay destination; HA artwork is still pending.
- Receiver-origin controls and independent simultaneous real output targets.
