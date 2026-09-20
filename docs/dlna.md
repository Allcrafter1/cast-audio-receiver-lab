# DLNA output (experimental)

Use **DLNA-Netzwerk durchsuchen** in management. Select a discovered renderer;
imports are disabled until explicitly enabled. A scan does not start playback.
Manual configuration requires the full UPnP device-description XML URL including
port/path, not merely a TV's IP. Existing addresses can be edited without
recreating the Cast speaker. Some TVs ask for controller permission on-screen.

## Media path

DLNA renderers fetch a URL; they do not receive our decoder's PCM stream. Older
devices may reject HTTPS entirely and support MP3/LPCM but not YouTube's audio
formats. This was reproduced on the development Samsung: HTTP accepted, HTTPS
rejected at SetAVTransportURI with UPnP 402. HA likewise recommends local HTTP:
https://www.home-assistant.io/integrations/dlna_dmr/

The adapter preserves compatible direct HTTP playback. For HTTPS, loopback-only
sources and formats not advertised by the renderer, it prepares a local media
file using existing FFmpeg, then serves an opaque HTTP URL with Content-Length,
HEAD and byte-range support. Supported known audio containers are remuxed with
stream copy; otherwise the fallback is 192 kbit/s stereo MP3 at 44.1 kHz. A device
without MP3 support is not guaranteed to work. Source URLs are not an open HTTP
proxy endpoint and are not included in relay access logs.

**Important trade-off:** this initial compatibility implementation completes
the file before playback. It costs preparation time and, when encoding, CPU and
another lossy encode. It is not equivalent to AirPlay's persistent PCM pipeline.
Each prepared file is limited to 64 MiB; preparation times out after 90 seconds.
At most two completed files plus an in-progress file are retained. Data lives
in the system temporary directory (which may be RAM-backed), not the persistent
speaker store, and is removed at stop/shutdown. No indefinite media cache.

Live/infinite sources that require this fallback are **not supported**: they
eventually reach a preparation limit. Compatible HTTP radio can still be sent
directly. Gapless playback, groups and broad renderer compatibility are not
promised. The relay listens on the LAN address routed toward the renderer using
an ephemeral TCP port; container deployments need the documented host network.

## Testing and diagnosing

1. Run discovery; verify existing devices are not imported twice.
2. Approve the controller on the TV if requested.
3. Test a finite, known-compatible MP3 over HTTP.
4. Test WebM/Opus through Cast → HA → relay → TV.
5. Test a real YouTube Music item, then pause, volume, seek, next and disconnect.
6. Repeat after TV power-off/on. Check adapter restarts and observed TV state.

Steps 1, 3 and 4 passed on one Samsung; user heard the direct MP3 test. The
end-to-end relay test confirmed TV PLAYING with advancing position and clean
STOP. YT Music and full physical control regression remain user acceptance.
SOAP acceptance alone is not successful playback; the adapter reports loading
until device polling confirms playback. Startup failures and library exceptions
must return errors rather than crash/recreate the Cast speaker.

Useful private logs contain `DLNA command=... failed category=UPnP ...` and
`DLNA local media prepared mime=... elapsed_ms=...`. Do not publish signed media
URLs, raw target files, full archives or authentication bundles. Only a sanitized
error category plus version, format, timing and renderer model is needed first.
