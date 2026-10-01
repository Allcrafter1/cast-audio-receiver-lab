# Issue #13: early AirPlay stop — test handoff

Status (2026-10-01): investigated against dev20 and main `4444f2d`; root cause
not established. No runtime change or new release. Report:
https://github.com/Allcrafter1/cast-audio-receiver-lab/issues/13

## Findings

The reported `cliairplay exited before opening command pipe` is raised while
starting an AirPlay helper, before the decoder starts for that load. It does
not identify why an already playing track stopped. It could belong to a later
load/seek/reconnect; the sequence needs the route log.

Adapter output is stored separately in `route-<id>.log` in the manager's
`speakers` directory, with one rotated `.log.1` file. It is not forwarded to the
normal frontend/App log. With the default container configuration this is
`/data/speakers/` **inside the receiver container**, not the SSH App's `/data`.
For a custom `--data-dir`, use `<data-dir>/speakers/`.

The decoder records its exit code, decoded and expected seconds, and truncation.
A nonzero exit, empty output, or output more than three seconds shorter than
known metadata duration produces ERROR, not FINISHED. Because decoding can run
ahead of audible playback, this is one possible early-stop mechanism, not a
confirmed diagnosis. The persistent transport otherwise waits for its elapsed
clock to reach the decoded sample count before signalling FINISHED.

## Manual test on the existing dev20 installation

1. Choose an affected track followed by another track in the queue. Turn repeat
   off. Record duration, local start time/timezone and device model. Let it play
   without seeking or manually selecting Next.
2. Test the receiver's direct AirPlay route first. Record audible stop time,
   displayed position in YT Music and HA, whether the second track starts, and
   whether Retry succeeds. Keep protocol/pairing unchanged.
3. Repeat the same queue through the Music Assistant AirPlay bridge. If an
   already configured local output is available, repeat there to separate the
   YouTube/decoder path from AirPlay.
4. After a failed run, try manual Next once and record whether it works. Keep
   its timestamp separate from the original failure.
5. Preserve the affected route log and rotated predecessor locally before they
   rotate again. Capture the normal App log for the same interval and the UI's
   support inventory (also at `/api/support`). The inventory has no playback logs.

With an existing authorized Docker shell, locate logs without printing route
configuration (replace `CONTAINER` with the actual receiver container):

```sh
docker exec CONTAINER sh -c 'ls -l /data/speakers/route-*.log*'
```

For HAOS use existing host/container access; the standard SSH App has a different
filesystem. Playback testing needs no new SSH exposure or permission changes;
local log retrieval can follow with the maintainer.

Keep the short log interval from track load through failure and the next load.
Useful fixed messages are:

```text
AirPlay load start=... duration=...
AirPlay decoder category=...
AirPlay decoder ended code=... decoded_s=... expected_s=... truncated=...
AirPlay track drained decoded_s=... elapsed_s=...
AirPlay warm transition failed; reconnecting
AirPlay transport created pid=...
AirPlay transport reused pid=...
AirPlay sender exited unexpectedly code=...
AirPlay PCM transport closed unexpectedly
cliairplay exited before opening command pipe
```

Review excerpts before sharing: omit credentials, signed URLs, route IDs,
addresses and personal metadata. Do not attach route JSON or certificates.

## Interpretation and automated evidence

| First relevant event | Next investigation |
| --- | --- |
| Decoder nonzero exit or truncated output | Source fetch/decoder category and metadata versus stream duration |
| Sender exit or PCM closure before decoder completion | AirPlay connection/process failure and receiver compatibility |
| FINISHED/drained, then warm reconnect and pipe-open failure | Next-track transport transition and reconnection |
| FINISHED/drained without the next load | Frontend queue/EOF handling |

These distinguish hypotheses; none alone proves a hardware-specific fix.
Existing AirPlay tests pass: **41 tests**, including sample-clock completion,
stale EOF protection, truncation detection, warm FLUSH/fallback and helper
cleanup. Run with installed project dependencies:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_airplay*.py'
```

Physical reproduction, direct-versus-bridge comparison and user acceptance are
pending. Keep issue #13 open. Publish through `release-runbook.md` once the
evidence supports a concrete fix.
