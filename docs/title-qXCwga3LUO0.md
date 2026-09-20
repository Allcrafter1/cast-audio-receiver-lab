# Audio-6: title-specific HTTP 403 (2026-09-12)

User requested investigation of `qXCwga3LUO0`, separately from duplicate
queue starts. The new logs establish:

- 20:19:31.661: Puh, ist das heiß loaded, start 0.
- 20:19:31.774: mpv end-file, error/loading failed, entry 4.
- 20:19:36.743: same title loaded again.
- 20:19:36.858: same player error, entry 5.
- Mein echtes Leben before and after reaches file-loaded successfully.

A direct mpv probe reproduced HTTP 403 for the failing title while
`b7l31agg58g` played. A later same-URL ffmpeg probe also returned 403.
Changing User-Agent, disabling seekable HTTP, forcing IPv4 at extraction,
and bounded/open/no Range requests did not remove the observed 403.
This locates the observed failure at media URL retrieval, not Cast pairing
or premium-account login. It does not establish Google's reason for refusal.

The original extractor only used `--get-url -f ba`, trusting advertised
formats. Tests with yt-dlp `--check-formats`:

- Explicit audio/m4a selected 140 and mpv played it successfully.
- One best-audio extraction failed with no available format and a warning
  about missing web_embedded URLs; this remains a possible failure mode.
- Two subsequent best-audio extractions selected 251; ffmpeg fully decoded
  both successfully.

Change: add upstream `--check-formats` to the existing bounded (35 s)
extractor invocation. Keep best-audio selection and all control/session code
unchanged. This screens unavailable formats rather than introducing a
custom downloader or forcing lower quality for every title. It can add
startup latency and cannot guarantee a URL remains valid after probing.
No signed URLs or credentials are recorded here.

The duplicate-start issue is intentionally not modified in this iteration.

Integration probe: the exact revised extractor arguments followed by our
actual MpvAudioBackend (muted, independent of the live session) reached
PLAYING at 2.03 seconds with no idle/error reason. Seven backend unit tests
also pass. Full YT Music sender verification remains necessary.

Release build completed successfully; revised receiver deployed and restarted
on the test laptop. No authentication files were changed.
