# Audio-9: prepare next queue item

## Measurements

Timestamped yt-dlp diagnostics on the laptop:

- b7l31agg58g: page at 0.72 s, visionOS API at 1.70 s, HLS info
  at 1.82 s, format test 2.07–2.17 s, finish 2.31 s.
- qXCwga3LUO0: additional TV/embedded API requests and JS challenge;
  challenge starts 2.29 s, format test 4.09–8.20 s, finish 8.32 s.
- Forcing AAC did not help: 8.63 s vs 8.39 s for best-audio in the
  comparison. Keep upstream best-audio selection and availability testing.

These are samples, not a controlled benchmark. In particular the four-second
format test is measured duration, not an explanation of the server's delay.

## Implementation

After successful playback dispatch or a queue update, resolve the next known
queue item in a background task. One speculative slot per YouTube session;
no disk cache. It cannot itself start playback. Explicit/automatic Next can
consume the result, waiting for an already-running resolution if necessary.
Only results completed less than ten minutes ago are reused. Failed, expired,
or mismatched results fall back to ordinary checked resolution.

New setPlaylist selections deliberately retain the existing resolution path,
including pending-selection coalescing. This avoids changing the ordering that
fixed duplicate starts. Arbitrary quick-selection songs are not accelerated.

Changed next item, Stop and session task teardown discard/cancel the speculative
task. The underlying existing spawn_blocking extractor cannot be interrupted
by async task cancellation and may finish within its existing 35-second process
timeout; its result cannot be used after cancellation. Thus one live slot does
not guarantee only one subprocess during rapid queue changes.

Limitations: URL availability can change after preflight; TTL is not a promise
of validity. Queues with unknown next item cannot prefetch. Current code does
not refresh a ten-minute-old slot in the background, but resolves anew on use.
This improves transition latency, not gapless audio or AirPlay synchronization.

## Tests

Rust tests cover TTL expiry and speculative-task cancellation. Live validation
must compare a prepared Next/automatic transition with new-queue selection,
and recheck Stop/disconnect. Look for `prefetching next YouTube media` followed
by `using prefetched YouTube media` and a single player load.

Final-source checks: both prefetch unit tests and all nine Lounge tests passed.
Release build succeeded; Audio-9 deployed to the laptop and player reconnect
verified. User verification of prepared transitions remains pending.
Queue snapshot: patches/vibecast-audio-9-queue-snapshot.patch is cumulative
against vendored upstream, not additive to older lib.rs patches.
