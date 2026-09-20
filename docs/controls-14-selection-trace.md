# Controls-14: distinguish sender sequence from selection interpretation

## Follow-up reproduction with raw selection diagnostics

User started TOD, then Du wirst mir fehlen -> zehnvonzehn -> Alles was ich hab
-> Katz&Maus -> Zerrissen. All following times are local on 2026-09-13.

| Time | Sequence | Explicit/raw and parsed selection | Index / length | eventDetails video |
| --- | --- | --- | --- | --- |
| 13:13:50.505 | 9 | EwlCTxy8P-M (initial TOD per user) | 0 / 25 | absent |
| 13:14:07.053 | 15 | LguRBZ5d2_I | 0 / 100 | absent |
| 13:14:08.381 | 18 | OjzHimoVml4 | 0 / 100 | absent |
| 13:14:09.561 | 20 | iYvPgb8v5Ys | 0 / 100 | absent |
| 13:14:10.729 | 22 | GJOP_7X3E1k | 0 / 100 | absent |
| 13:14:11.613 | 24 | LguRBZ5d2_I | 1 / 101 | matches |
| 13:14:12.733 | 26 | 93g0HeM5NcM (Zerrissen) | 0 / 100 | absent |
| 13:14:13.627 | 28 | OjzHimoVml4 | 1 / 101 | matches |
| 13:14:14.506 | 30 | iYvPgb8v5Ys | 2 / 102 | matches |
| 13:14:15.303 | 32 | GJOP_7X3E1k | 3 / 103 | matches |
| 13:14:16.182 | 34 | LguRBZ5d2_I | 4 / 104 | matches |
| 13:14:18.597 | commit | LguRBZ5d2_I | — | — |

Every replacement cancels the previous foreground request. The last received
selection wins as implemented. No raw-vs-parsed ID mismatch in this trace.
The user's last intended selection WAS received, then superseded by later
messages naming older selections. Increasing index/length plus eventDetails is
consistent with asynchronous queue enrichment, but not enough to infer causality
or safely discard those messages. Receiver feedback may provoke/reinforce it.
Next investigation: correlate queue update origin/generation and outbound state;
do not blanket-ignore eventDetails or classify every new sequence as a new tap.

## Observed example

User subsequently identified intended order, with some uncertainty about the
final title: Du wirst mir fehlen -> zehnvonzehn -> Alles was ich hab -> Katz&Maus
-> Zerrissen (Bruckner). Existing successful player-load logs establish
93g0HeM5NcM = Zerrissen, LguRBZ5d2_I = Du wirst mir fehlen, OjzHimoVml4 = zehnvonzehn.
Thus Zerrissen did reach parsed selection at 13:04:20.232, before later
setPlaylist interpretations displaced it. This does not yet determine the
contents/intent of those later raw messages. Another burst at 13:01 also shows
Zerrissen selected, superseded and the final parsed selection loading correctly.

Date 2026-09-13; times below Europe/Berlin (receiver log UTC + 2).
Session 7942df04-54d2-478c-af41-32ef4f961740.

| Time | Incoming Lounge sequence | Resulting selection/action |
| --- | --- | --- |
| 13:04:13.358 | 15 setPlaylist | LguRBZ5d2_I, index 0, length 100 |
| 13:04:14.575 | 18 setPlaylist | OjzHimoVml4, index 0, length 100; prior cancelled |
| 13:04:15.851 | 20 setPlaylist | iYvPgb8v5Ys, index 0, length 100; prior cancelled |
| 13:04:16.668 | 22 setPlaylist | LguRBZ5d2_I, index 1, length 101; prior cancelled |
| 13:04:17.821 | 24 setPlaylist | GJOP_7X3E1k, index 0, length 100; prior cancelled |
| 13:04:18.743 | 27 setPlaylist | OjzHimoVml4, index 1, length 101; prior cancelled |
| 13:04:20.232 | 29 setPlaylist | 93g0HeM5NcM, index 0, length 100; prior cancelled |
| 13:04:21.289 | 33 setPlaylist | LguRBZ5d2_I, index 1, length 101; prior cancelled |
| 13:04:22.260 | 36 setPlaylist | OjzHimoVml4, index 2, length 102; prior cancelled |
| 13:04:24.562 | player load | zehnvonzehn, corresponding to OjzHimoVml4 |

Intermediate duplicates (16,25,30) were coalesced as queue updates. The final
resolver completed in 2.301 seconds; mpv file-loaded followed at 13:04:24.654.
The backwards selections coincide with new setPlaylist processing, not an old
aborted result unexpectedly completing. Sequence numbers increase in this burst.

Important limitation: logs show command name/sequence and parsed queue index/ID,
not the original videoId and eventDetails.videoId. parse_set_playlist uses the
indexed queue entry when a nonempty videoIds list exists; primary videoId is
only a fallback for an empty list. We cannot infer whether those fields disagree
from the old logs, nor whether the final screen tap generated a request at all.
No speculative preference change, queue filtering or replay suppression applied.

## Diagnostic change

39 YouTube tests pass (one live network probe intentionally not run). Release
build succeeded; Controls-14 deployed with no selection behavior change. Prior
binary saved at .state/controls-14-rollback/vibecast-controls13 on the laptop.
Cumulative source snapshot: patches/vibecast-controls-14-snapshot.patch.

At input parsing, log sequence with only videoId, eventVideoId, numeric currentIndex,
parsedIndex, selectedVideoId, queueLength and currentTime. Never log full params,
eventDetails JSON, account/session values or media URLs. Log the video ID when
resolved media is committed to playback. Existing supersession logs remain.
A test deliberately supplies conflicting selection fields plus private unrelated
fields; verify the conflict remains visible and unrelated fields are excluded.

Next test must include the user's final intended title. If raw and parsed selection
disagree, investigate parser semantics; if final accepted selection differs from
commit, investigate coordination; if no request names the intended title, do not
manufacture one. Also consider whether receiver feedback induced a later sender
request rather than assuming any sender-origin request proves sender-only fault.
