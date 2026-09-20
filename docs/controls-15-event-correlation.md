# Controls-15: prepare a selection-correlation fix

## Evidence and boundary

Controls-14 proves the last intended title arrives and is subsequently displaced
by newer protocol messages naming older titles. It does not prove the sender UI
issued those as fresh taps. The user reports slower selection works.
No raw/index mismatch or stale resolver completion explains the recorded burst.

Code inspection: each accepted setPlaylist immediately changes CurrentMedia and
posts nowPlaying, then subsequent events can replace it. Discarding only a final
player load would be insufficient: the older selection would already be reported
to the sender. A correctly correlated stale-update guard belongs before both
handle_internal and command dispatch. Incoming sequence is arrival order, not a
documented user-action generation ID.

## Diagnostic preparation, not a behavior fix

Add eventDetails.eventType (known symbolic values only; unknown becomes OTHER),
event video-list count, and the outgoing nowPlaying video/index/queue size plus
POST acknowledgement latency. Do not log user/avatar, tokens, full event JSON,
session IDs or signed media URLs. Retain raw-vs-parsed selection diagnostics.
This lets the next reproduction distinguish event categories and associate our
feedback with later queue mutations. POST acknowledgement alone is not proof
that the sender consumed the feedback.

No blanket eventDetails exclusion, prior-title blacklist, debounce, or queue
rewriting. Each risks breaking legitimate reselection or queue edits. If the
protocol gives no distinguishing information, a fully reliable receiver-only
fix cannot infer which older-title command was intentional.

## Fix acceptance checklist

- Proven stale queue enrichment cannot change the active selection or its report.
- Real reselection of a previously played title remains supported.
- Same-selection enrichment is retained without restarting playback.
- Automatic Next, explicit queue edits, seek and cleanup regressions pass.
- Replay captured event classes in an automated test before changing live policy.

## Status

40 YouTube unit tests passed; one explicitly live network test ignored. Four
Python player unittest cases passed. Release build succeeded (2m14s).
Controls-15 diagnostic build deployed with receiver/player restart; no playback
behavior fix enabled. Controls-14 binary retained remotely at
.state/controls-15-rollback/vibecast-controls14.
Lounge-only cumulative source snapshot: patches/vibecast-controls-15-lounge-snapshot.patch
(not a standalone full receiver patch, not to stack onto older Lounge snapshots).
Next requirement: rapid manual reproduction to capture event categories and
outgoing feedback timing; no additional slow-selection test required.
