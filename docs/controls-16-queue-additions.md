# Controls-16: queue additions are not automatically fresh selections

## Controls-16.1 regression follow-up

User reports success with ~1s between selections. Actual UI timing and Lounge
arrival timing differ; do not infer a reliable cutoff from server timestamps.
Added a sanitized reconstruction test through parser, normalization, internal
queue state and outbound nowPlaying serialization. Unlike the earlier append-only
test, additions repeatedly insert at index1; the last arrives during Playing.
Assert preserved video/index/state/time, then acceptance of explicit VIDEO_SELECTED.
This tests current safe semantics and exposes the known limit, not a fix for the
remaining user-reported outcome. No full raw queues or correlation identifiers
were retained in previous traces, so this is not an exact wire replay.
43 unit tests pass, one live probe ignored; whitespace check passed.
No production-code change, rebuild, restart, or requested repeat test.
Next informative manual experiment would compare the same sender and fixed order
on the reference receiver at rapid versus ~1s pacing. Do not add a title blacklist,
arbitrary selection lockout or global debounce without evidence and agreement.

## Follow-up: user test partially successful

2026-09-13 11:38 UTC: VIDEO_ADDED sequences30,32,34 all preserve Zerrissen
(including seq34 after playback starts). Zerrissen commits 11:38:25.286.
At 11:38:27.659 sequence37 explicitly reports VIDEO_SELECTED for GJOP_7X3E1k
at index1, queue length103, time0. Katz & Maus commits 11:38:28.562. Between
the addition and selection only setSubtitlesTrack and noop are recorded; no Next.
The new guard works, but does not handle this explicit delayed follow-up.
Do not label the user's test solved. Current evidence cannot distinguish this
VIDEO_SELECTED from a real tap selecting the same queue item. Need correlation
or a reference comparison before rejecting this class of command. No rollback
or broader filtering has been performed.

## Captured evidence

User's repeatable order: Du wirst mir fehlen -> zehnvonzehn -> Alles was ich hab
-> Katz & Maus -> Zerrissen. Controls-15 played Katz & Maus instead.
2026-09-13, timestamps UTC:

| Time | Sequence | Event | Selected video |
| --- | --- | --- | --- |
| 11:30:52.746 | 18 | PLAYLIST_SET | LguRBZ5d2_I |
| 11:30:53.957 | 21 | PLAYLIST_SET | OjzHimoVml4 |
| 11:30:55.427 | 23 | PLAYLIST_SET | iYvPgb8v5Ys |
| 11:30:56.607 | 25 | PLAYLIST_SET | GJOP_7X3E1k |
| 11:30:57.747 | 27 | PLAYLIST_SET | 93g0HeM5NcM |
| 11:30:58.628 | 29 | VIDEO_ADDED | LguRBZ5d2_I |
| 11:30:59.507 | 31 | VIDEO_ADDED | OjzHimoVml4 |
| 11:31:00.333 | 33 | VIDEO_ADDED | iYvPgb8v5Ys |
| 11:31:01.162 | 35 | VIDEO_ADDED | GJOP_7X3E1k |
| 11:31:03.763 | commit | playback | GJOP_7X3E1k |

Queue size grows from 100 to 104, incoming selection index from 0 to 4.
nowPlaying POST acknowledgement ~286–320ms. This does not prove why the sender
generates delayed additions, but identifies our actionable interpretation error:
we lose the distinction between adding and explicitly selecting a video.

## Narrow correction

Preserve VIDEO_ADDED classification through parsing. Before internal state and
command dispatch, convert it into existing UpdatePlaylist if the active video is
still at its existing slot and the non-null list identity agrees. Keep queue data
and send nowPlaying for the preserved selection. No resolver cancellation/load
for such an addition. Applies during loading and playback.

If those conditions fail, use previous SetPlaylist behavior (not a guess about
which title to select). Explicit VIDEO_SELECTED/PLAYLIST_SET, other event types,
empty startup state, moved active slot and different queues are unchanged.
No new dependency or queue architecture. Remaining limitation: this deliberately
does not handle insertion before the active index or unidentified queue ancestry.

## Status

42 YouTube unit tests passed (one explicit live-network probe ignored), including
the two new regression cases. Four Python player tests passed; diff whitespace
check passed. Release build succeeded (2m15s). Controls-16 deployed with receiver
and player restart. Rollback binary: .state/controls-16-rollback/vibecast-controls15.
Lounge-only cumulative snapshot: patches/vibecast-controls-16-lounge-snapshot.patch;
not a full standalone receiver snapshot and not to stack on older Lounge patches.
Manual reproduction with the fixed order is now required. No claim yet that all
rapid-selection cases are solved or that the same-list/slot guard matches every
live message; existing logs did not include full queues/list identities.
