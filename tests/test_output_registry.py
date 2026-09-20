import argparse
from pathlib import Path
import tempfile
import unittest
import uuid

from cast_audio_lab.output_registry import (
    adapter_arguments,
    is_singleton,
    output_names,
    validate_output_target,
)
from cast_audio_lab.routes import Route


class OutputRegistryTests(unittest.TestCase):
    def test_builtin_outputs_and_cardinality(self):
        self.assertEqual(output_names(), ("mpv", "airplay", "dlna", "sonos"))
        self.assertTrue(is_singleton("mpv"))
        self.assertFalse(is_singleton("airplay"))

    def test_local_output_rejects_target(self):
        self.assertIsNone(validate_output_target("mpv", None))
        with self.assertRaises(ValueError):
            validate_output_target("mpv", {"host": "127.0.0.1"})

    def test_airplay_arguments_write_private_target(self):
        target = {
            "host": "192.0.2.10",
            "port": 7000,
            "protocol": "raop",
            "device_id": "AA:BB:CC:DD:EE:FF",
            "txt": {"cn": "0,1"},
        }
        route = Route.parse(
            {
                "id": str(uuid.uuid4()),
                "name": "Target",
                "backend": "airplay",
                "target": target,
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            args = adapter_arguments(
                "airplay", route, Path(directory), "/opt/cliairplay"
            )
            self.assertEqual(args[-2:], ["--cliairplay", "/opt/cliairplay"])
            private_file = Path(args[1])
            self.assertTrue(private_file.exists())
            self.assertEqual(private_file.stat().st_mode & 0o777, 0o600)

    def test_dlna_and_sonos_targets_are_normalized(self):
        dlna = validate_output_target(
            "dlna", {"description_url": "http://192.168.1.20:49152/device.xml"}
        )
        self.assertEqual(dlna["host"], "192.168.1.20")
        self.assertEqual(dlna["port"], 49152)
        self.assertEqual(dlna["protocol"], "dlna")
        sonos = validate_output_target("sonos", {"host": "192.168.1.21"})
        self.assertEqual(sonos["port"], 1400)
        self.assertEqual(sonos["protocol"], "sonos")
        # Route configuration passes through validation on create, save and
        # reload. Canonical values therefore have to remain valid unchanged.
        self.assertEqual(validate_output_target("dlna", dlna), dlna)
        self.assertEqual(validate_output_target("sonos", sonos), sonos)

    def test_network_target_rejects_tampered_canonical_fields(self):
        with self.assertRaises(ValueError):
            validate_output_target(
                "dlna",
                {
                    "description_url": "http://192.168.1.20/device.xml",
                    "host": "192.168.1.21",
                },
            )
        with self.assertRaises(ValueError):
            validate_output_target(
                "sonos", {"host": "192.168.1.21", "protocol": "dlna"}
            )

    def test_unknown_output_fails_closed(self):
        with self.assertRaises(ValueError):
            validate_output_target("unknown", None)


if __name__ == "__main__":
    unittest.main()
