import tempfile
import unittest
from pathlib import Path

from cast_audio_lab.airplay import (
    AirPlayTarget,
    cliairplay_argv,
    ffmpeg_pcm_argv,
    parse_cliairplay_line,
)
from research.legacy_python_receiver.legacy_cast_receiver.protocol import (
    metadata_from_cast,
)


class AirPlayAdapterTests(unittest.TestCase):
    def test_raop_encryption_capabilities_reach_dedicated_options(self):
        target = AirPlayTarget(host="192.0.2.20", port=6000, protocol="raop",
                              txt={"et": "0,1", "cn": "0,1", "md": "0,1,2"})
        argv = cliairplay_argv("cliairplay", target, Path("/tmp/test-pipe"), volume=.5, latency_ms=600)
        self.assertEqual(argv[argv.index("--et") + 1], "0,1")
        self.assertEqual(argv[argv.index("--cn") + 1], "0,1")
        self.assertEqual(argv[argv.index("--txt") + 1], "cn=0,1 et=0,1 md=0,1,2")
        self.assertEqual(argv[-1], target.host)

    def test_builds_safe_auto_route_command(self):
        target = AirPlayTarget(
            host="192.0.2.20",
            port=5000,
            protocol="auto",
            device_id="AA:BB:CC:DD:EE:FF",
            name="Living Room",
            txt={"cn": "0,1", "am": "RX-V6A"},
        )
        with tempfile.TemporaryDirectory() as directory:
            argv = cliairplay_argv(
                "/usr/bin/cliairplay",
                target,
                Path(directory) / "commands",
                volume=0.42,
                latency_ms=350,
            )
        self.assertEqual(argv[0], "/usr/bin/cliairplay")
        self.assertEqual(argv[-1], "192.0.2.20")
        self.assertEqual(argv[argv.index("--volume") + 1], "42")
        self.assertEqual(argv[argv.index("--latency") + 1], "350")
        self.assertEqual(argv[argv.index("--dacp") + 1], "AABBCCDDEEFF")
        self.assertEqual(argv[argv.index("--txt") + 1], "am=RX-V6A cn=0,1")
        self.assertEqual(argv[argv.index("--txt") + 2:], [target.host])

    def test_ffmpeg_normalizes_to_pcm(self):
        argv = ffmpeg_pcm_argv(
            "ffmpeg", "https://example.test/audio", start_time=12.5
        )
        self.assertIn("12.500", argv)
        self.assertEqual(argv[-2:], ["s16le", "pipe:1"])
        self.assertNotIn("-re", argv)

    def test_parses_remote_and_status_lines(self):
        remote = parse_cliairplay_line("[EVENT] remote command=pause")
        self.assertIsNotNone(remote)
        self.assertEqual(remote.kind, "event")
        self.assertEqual(remote.name, "remote")
        self.assertEqual(remote.values["command"], "pause")

        started = parse_cliairplay_line(
            "[STATUS] started requested_unix_ms=0 at_unix_ms=123"
        )
        self.assertEqual(started.name, "started")
        self.assertEqual(started.values["at_unix_ms"], "123")

    def test_extracts_cast_metadata(self):
        metadata = metadata_from_cast(
            {
                "contentId": "track-1",
                "duration": 123.4,
                "metadata": {
                    "title": "Song",
                    "artist": "Artist",
                    "albumName": "Album",
                    "images": [{"url": "https://example.test/cover.jpg"}],
                },
            }
        )
        self.assertEqual(metadata.title, "Song")
        self.assertEqual(metadata.artist, "Artist")
        self.assertEqual(metadata.artwork_url, "https://example.test/cover.jpg")
        self.assertEqual(metadata.item_id, "track-1")


if __name__ == "__main__":
    unittest.main()
