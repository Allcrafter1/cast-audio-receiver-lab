# Incident log

This log records observations worth correlating if they recur. A single report
is not automatically a confirmed software defect or justification for a broad
behavior change. Times are local unless explicitly marked otherwise.

## 2026-09-19 approximately 22:10 Europe/Berlin — AirPlay did not start once

- Expected: selected media begins on the configured AirPlay output.
- Observed: playback did not start on one attempt.
- Recovery: reconnecting succeeded and playback worked afterward.
- Frequency: one observed occurrence at time of report.
- Retained-log correlation: at 22:08:37 the AirPlay transport reached
  `connected` and `started`, but FFmpeg then classified the source fetch as
  `http_403`, exited with zero decoded seconds and marked the stream truncated.
  A reconnect/load at 22:09:44 reached `audio` at 22:09:44.667.
- Plausible cause: the first signed media URL was expired or transiently denied;
  the evidence does **not** point to AirPlay connection establishment itself.
  This remains a one-event diagnosis rather than a general root-cause proof.
- Policy: preserve evidence; do not retune codecs, buffering or persistent
  transport based on this incident alone. If it repeats, record exact title,
  sender, target, UI state and timestamp, then compare adapter, decoder and
  airplay-cli lifecycle events around both the failed and successful attempts.
  A future retry policy should re-resolve rather than blindly retry the same
  signed URL, but it requires repeated evidence and an explicit session-level
  re-resolution contract before implementation.
