# Artwork and HA radio follow-up

User confirms HA terminal status and management/favicon work. Do not reopen
the successful teardown implementation based on missing radio metadata.

## Observed sender information

The two HA Default Media LOADs at 2026-09-14 16:23:51 and 16:27:57 UTC have
streamType LIVE, no duration, no title/subtitle, and zero images. This is evidence
of absent sender fields, not proof that the station itself has no metadata.
Station/track information embedded in ICY or obtained from a station API is a
separate enrichment mechanism not currently implemented. A live stream has no
finite track duration unless a source supplies one; don't invent a progress bar.
The separate local-file duration case remains unverified.

## Actual AirPlay image defect

Inspected a generated JPEG from the active pipeline, not just the unit fixture:
480x480, SAR1:1, but black top/bottom bands and colored left/right padding around
the album. The outer square filter worked; embedded padding survived.

The shared converter first decodes/crops through a lossless PNG intermediate,
then makes one final JPEG. Lanczos is used when the source exceeds the 512px
bound. A 64x64 grayscale preview detects only full-width
symmetric black bands of 2..16 rows before the equal center crop. Dark/asymmetric
images are left unchanged. Area resampling avoids artificial edge ringing.
Optional failure preserves the prior square image; fetch/conversion is bounded
and child processes are killed/reaped on cancellation. The work runs off the
playback start path with the existing artwork task. The saved example becomes
360x360 and visually fills the frame. Dev9 removes the former double-JPEG
softness; the source's own pixel detail still limits final quality. Actual
receiver rendering remains a user acceptance check.

The saved 480x480 reference was replayed through dev9 on the remote FFmpeg:
the final 360x360 JPEG grew from 25,051 bytes in the old double-encoded sample
to 57,516 bytes and retained visibly more fine detail. This is a controlled
conversion comparison, not a claim that a low-resolution source can be made
higher resolution.

A remote CPU-only benchmark of the full converter on a synthetic 1024x600
source took 0.36–0.38 seconds per run (three runs, no network). Because the
AirPlay artwork task is already asynchronous, this cost does not delay audio;
it would only delay an image update if the future Cast/HA endpoint were made
synchronous.

If the target still looks soft, inspect the generated dimensions and URL
variant before changing the policy: the previously inspected source had only
360x360 real content inside a 480x480 letterboxed frame. Upscaling that image
to 512px can match a receiver canvas but cannot recreate source detail, so it
is intentionally a separate, evidence-based choice.

## Shared Cast/HA covers: proposed next architecture boundary

Cast/HA currently see the original metadata URL; sending a cropped AirPlay JPEG
cannot change that. Recommended: expose bounded processed images through the
existing management HTTP service, on its existing configurable LAN port. Use
opaque image IDs, a bounded expiring cache, and one shared conversion policy.
No arbitrary URL query proxy, new dependency, separate port, or playback wait.
Frontend status must use the processed image URL and announce metadata updates
when ready; stale track completions must not overwrite newer artwork. Keep the
original URL as a failure fallback. This cross-process metadata/cache boundary
needs agreement before implementing, per the project's architecture rule.
