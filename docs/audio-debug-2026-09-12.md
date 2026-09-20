# Audio transport investigation, 2026-09-12

Experimental revision: HLS-1 (not a release).

The Cast application launches, but this alone does not establish audio playback.
Android progressive URLs can serve an initial range while refusing later ranges
or open-ended requests with HTTP 403. Earlier successful first-range probes were
insufficient; neither missing Premium credentials nor a particular token is
established as the cause of the CDN rejection.

The curl-to-mpv shell pipeline previously hid transport failure. Without pipefail
its status follows the last command. The backend interpreted success as FINISHED
and explicitly moved the position to the duration. The deployed command was
corrected to preserve curl failure.

A fresh default yt-dlp best-audio URL selected HLS. FFmpeg opened the URL directly
and decoded the entire test track (213.043084 seconds), exit 0, no error output.
Piping playlist text into a raw-audio stdin path is inappropriate: the decoder
must fetch the playlist and its segments. The HLS-1 experiment therefore uses
direct mpv URL playback with yt-dlp disabled in mpv (resolution already happened).

Resolver changes: default yt-dlp client selection, a 35-second subprocess limit,
blocking work moved off the async executor, HLS MIME type, and explicit resolution
failure instead of silently reverting to an already failing Android URL.
The Rust resolver still uses InnerTube for metadata and requires it to succeed.
The external-player template now supports {start_time} for mpv --start.

Remaining verification: sender-driven playback on the actual selected song,
audible output, queue advancement, disconnect cleanup. CommandAudioBackend still
uses estimated time and has no real seek/volume IPC. A decoder-feedback backend
is needed before calling those controls production-ready. Authentication bundles
were not changed by this investigation.

Deployment check: release build succeeded. A direct mpv smoke test opened the
HLS URL at 60 seconds and played a four-second excerpt: AAC stereo 44100 Hz,
PulseAudio output initialized, exit 0. HLS-1 was deployed with direct mpv input,
--start={start_time}, and a private mpv diagnostic log. Sender testing remains
necessary; the smoke test does not prove audibility or queue behavior for the
user's song.

## HLS-2: actual sender tracks and executable selection

The first sender trial after HLS-1 never reached mpv: both selected video IDs
failed external resolution. /usr/bin/yt-dlp was version 2025.04.30, whereas the
project environment has 2026.08.19. Explicit iOS, VR and Safari probes with the
old executable failed too. A successful unrelated test video was insufficient.

Installed default yt-dlp dependencies, EJS 0.8.0 and Deno 2.9.6 in the project
venv. With that venv first in PATH, both sender-selected videos resolve and
decode fully with FFmpeg (139.714771 and 217.376167 seconds, exit 0, no errors).
Restarted receiver and player with the venv first in PATH. No certificate change
was necessary. Reproducible dependencies are in
config/youtube-extractor-requirements.txt. Future launchers must prepend their
project venv bin directory to PATH for the Rust resolver's yt-dlp subprocess.
Sender playback/start-position confirmation is still pending.
