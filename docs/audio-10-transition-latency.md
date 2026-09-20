# Audio-10: transition latency

User comparison targets: about 2–3 s for a new title and less than 1 s for
the next title, before evaluating additional AirPlay output buffering.
These are acceptance targets, not measured guarantees from this implementation.

## Observed missed preparation

Latest log example (UTC): bd2vrqJdyn4 was prepared at 21:23:31.594.
At 21:23:59.162 the sender delivered setPlaylist, not Next. The command
loop requested the same video at 21:23:59.401 but discarded the prepared
result because Audio-9 accepted only Next. It resolved again until 21:24:01.406;
mpv reported file-loaded about 0.108 s later. Other transitions repeated this.

## Changes

- Recognize a setPlaylist selecting the following index in the same non-null
  queue identity, with matching next video and start=0, as eligible for the
  prepared result. New queues, arbitrary positions and repeated current index
  keep the normal path. Add structural diagnostics (no raw queue identifiers).
- After updating local queue/buffering state, send incoming playback commands
  before awaiting the outbound status HTTP acknowledgement. Preserve ordered
  outbound status posts. This saves that round trip on the local command path.
- Preserve existing format availability checks and pending-selection coalescing.

Live verification must confirm actual same-queue/index matching; previous logs
did not contain those fields. A missed match is safe but still slow. Verify one
load per transition, no duplicate new-queue start, and correct status ordering.

## Further work

Fresh selections still require extraction and format probing. Investigate a
persistent extractor worker (startup/imports currently roughly 0.7 s in samples)
and reuse of metadata instead of independent metadata requests. Keep bounded
timeouts, request cancellation, worker recovery and format checking. Measure
before introducing another backend service.

Automatic EOF transitions still post status before sending Next; examine this
separately if automatic transitions remain slower than sender-requested ones.

Release build passed. The new selection eligibility test and nine Lounge tests
passed. Deployed Audio-10 and verified player reconnect; actual sender matching
and perceived transition latency still need the next live test.
patches/vibecast-audio-10-transitions-snapshot.patch is cumulative against
vendored upstream for lib.rs/lounge.rs, not additive to their older snapshots.
