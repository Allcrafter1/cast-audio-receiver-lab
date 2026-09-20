# Controls-5: new-queue start diagnostics (2026-09-12)

User confirms cleanup, reconnect, seeking and Next within the existing queue
work. Selecting a new queue can still start a track twice. This is not yet fixed.

Evidence from the last test, same player session:

- Loads at 20:08:38.869 and 20:08:41.797 local time.
- Loads at 20:09:17.844 and 20:09:22.845 local time.
- Previous logs did not include a usable content ID, Lounge command sequence,
  or mpv end-file error. These pairs alone cannot prove duplicate commands for
  the same track.
- The last mpv playlist item remained present while mpv was idle. Reopening its
  URL with ffmpeg successfully decoded eight seconds (exit 0). This rules out
  permanent unavailability at probe time, not a transient playback failure.

Instrumentation now records Lounge command name and sequence, queue-requested
video ID/start position, player title/start position, and mpv end-file
reason/error/entry/position. No signed media URLs or authentication data are
logged by these additions. Titles and video IDs are local listening history.

Also clear loading/seeking feedback gates on player errors; regression tested.
Do not blindly debounce loads by title or time: this could suppress intentional
replay, seek, or a legitimate new queue. The next real sender test is needed to
distinguish repeated BrowserChannel sequences, distinct setPlaylist commands,
and a second load through the Cast media path.

Local checks: seven mpv backend tests and two player tests pass.

User identified failed song as `qXCwga3LUO0` (Puh, ist das heiß, 179 s).
Explicit probe with the deployed yt-dlp version resolved format 251 (HTTPS)
in 6.02 s; ffmpeg decoded the entire source successfully (exit 0), without
account credentials. This does not reproduce the original session failure.

Release build succeeded and the diagnostic receiver/player were restarted
(PIDs 210488/210499). Player WebSocket reconnect confirmed at 20:17:50.
The separate full mpv probe hit its 60-second wall-clock limit; that is not
evidence of a decode failure for a 179-second audio track. A subsequent URL
probe returned no URL, so resolver transience still needs investigation.
