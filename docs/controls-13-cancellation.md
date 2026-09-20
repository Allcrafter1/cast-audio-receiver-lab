# Controls-13: interruptible foreground resolution

Scope approved by user: stop obsolete requests without changing format validation,
metadata sources, buffers or introducing a worker architecture.

## Implementation

The existing command loop keeps one foreground resolver future alive while
selecting commands and cancellation. A newer distinct selection drops this future
and is processed next. Stop and disconnect drop it too. Pending pause/autoplay and
seek position apply to the eventual media; seek is not sent to the previous title.
Duplicate same pending selection updates the queue without restarting resolution.
Matching prefetched next media is adopted with its existing age check.

yt-dlp retains --check-formats -f ba --get-url and the 35-second deadline. Tokio
process support replaces spawn_blocking and the external timeout wrapper. On Linux
the child starts in its own process group. Resolver drop synchronously requests
SIGKILL via the system kill utility for that owned group; a supervisor drains and
reaps the direct child. Pipes are drained by wait_with_output, avoiding pipe-fill
deadlocks. Successful requests disarm cancellation. No permanent worker RAM floor.

The kill utility introduces a short synchronous operation on cancellation, not
on ordinary playback or every command. This trade-off should be measured on small
hardware. Background task abort is scheduled by Tokio; physical subprocess cleanup
may briefly overlap a replacement. Do not claim a strict global extractor memory
cap, especially across multiple receiver instances. Helpers that create their own
session/process group escape group signalling; the current test covers ordinary
inherited groups. Linux init/subreaper handles adopted grandchild zombies.

## Tests / acceptance

Automated result: 38 YouTube tests, 22 core tests and 17 player API tests pass;
the explicit live network probe is separate. Four local Python player tests pass.
Release build succeeded and Controls-13 was deployed. Previous binary saved in
.state/controls-13-rollback/vibecast-controls12 on the test laptop. Cumulative
source snapshot: patches/vibecast-controls-13-snapshot.patch (do not stack it on
older snapshots). Cast GET_STATUS after restart preserved the saved 26% level.

Explicit live resolver probe also passed: b7l31agg58g 2,221 ms and qXCwga3LUO0
8,206 ms. These are single extraction samples, not audible-onset measurements
or proof of a latency improvement. No live audio was started by this probe.

Initial resource sample after restart, before any playback: receiver RSS 14,560
KiB/PSS 12,556 KiB; Python adapter RSS 27,256 KiB/PSS 19,619 KiB. Both showed
0 measured CPU ticks over two seconds. No adapter-owned mpv was running yet.
This excludes playback/extraction, is not a whole-system requirement and is NOT
a like-for-like improvement over the pre-restart sample: that older mpv process
had active CPU usage. Burst-selection peaks remain to be measured with user tests.

- Controlled slow A -> B -> C invalidates old responses, only C loads.
- Duplicate C does not re-resolve; pending Pause and Seek 42 apply to C.
- Same-queue advance reuses prepared D without a new resolver request.
- Stop and session cancellation reject stale success/failure.
- Real shell + sleep process tree: cancellation and timeout stop helper, reap
  leader. Normal process stdout/status preserved.
- Existing queue TTL, controls, Lounge and volume tests remain required.
- Old metadata fixture now tests resolve_metadata with an explicit duration and
  audio URL, reflecting existing production code; no live external extraction.

Live test: choose A then B/C while still loading, verify only last selection plays;
repeat pending pause/seek; verify Next and automatic transition, then This Device
and reconnect. Compare actual process-tree RSS/PSS and CPU without build processes.
Synthetic tests do not establish real YT Music UI behavior or audible gaplessness.

TLS future-window collection remains the next pre-AirPlay milestone after this
regression. No phone-clock or authentication-material changes in Controls-13.
