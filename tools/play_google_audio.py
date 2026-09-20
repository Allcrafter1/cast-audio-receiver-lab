#!/usr/bin/env python3
"""Play a YouTube/Googlevideo audio URL through curl and mpv.

Experimental transport, not a verified solution to CDN HTTP 403 responses.
Both transport and decoder must succeed before reporting a finished track.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: play_google_audio.py URL", file=sys.stderr)
        return 2

    url = sys.argv[1]
    curl = subprocess.Popen(
        [
            "curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--retry",
            "2",
            "--retry-delay",
            "1",
            "--user-agent",
            "com.google.android.youtube/20.10.38",
            "--referer",
            "https://www.youtube.com/",
            "--header",
            "Origin: https://www.youtube.com",
            "--header",
            "Accept-Language: en-US,en;q=0.9",
            "--header",
            "Range: bytes=0-",
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=None,
        start_new_session=True,
    )
    assert curl.stdout is not None

    try:
        player = subprocess.Popen(
            [
                "mpv",
                "--no-video",
                "--audio-display=no",
                "--ytdl=no",
                "--really-quiet",
                "-",
            ],
            stdin=curl.stdout,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )
        curl.stdout.close()
        try:
            player_code = player.wait()
            if player_code != 0:
                return player_code
            # Empty input can make a decoder exit successfully even though
            # curl failed. Never convert a failed download into track EOF.
            return curl.wait()
        finally:
            if curl.poll() is None:
                os.killpg(curl.pid, signal.SIGTERM)
                curl.wait()
    except BaseException:
        if curl.poll() is None:
            os.killpg(curl.pid, signal.SIGTERM)
            curl.wait()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
