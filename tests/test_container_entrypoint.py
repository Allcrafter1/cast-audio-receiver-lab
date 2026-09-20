import json
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from cast_audio_lab.container_entrypoint import _supervisor_self_info, runtime_argv


class ContainerEntrypointTests(unittest.TestCase):
    def test_supervisor_self_info_uses_bearer_token_without_exposing_it(self):
        captured = {}

        def opener(request, timeout):
            captured["authorization"] = request.get_header("Authorization")
            captured["timeout"] = timeout
            return BytesIO(
                b'{"result":"ok","data":{"ingress_port":43124,"options":{}}}'
            )

        info = _supervisor_self_info(
            {"SUPERVISOR_TOKEN": "private-token"}, opener=opener
        )
        self.assertEqual(info["ingress_port"], 43124)
        self.assertEqual(captured["authorization"], "Bearer private-token")
        self.assertEqual(captured["timeout"], 5)

    def test_defaults_need_no_visible_configuration(self):
        argv = runtime_argv(environ={}, options_path=Path("/missing/options.json"))
        self.assertEqual(argv[argv.index("--web-port") + 1], "8788")
        self.assertEqual(argv[argv.index("--data-dir") + 1], "/data")
        self.assertEqual(
            argv[argv.index("--certs") + 1], "/data/private/certs.json"
        )
        self.assertNotIn("--artwork-public-url", argv)

    def test_ha_options_and_environment_override_are_allowlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            options = Path(directory) / "options.json"
            options.write_text(
                json.dumps(
                    {
                        "web_port": 9000,
                        "log_level": "DEBUG",
                        "artwork_public_url": "http://192.0.2.1:9000",
                    }
                )
            )
            argv = runtime_argv(
                environ={
                    "CAST_AUDIO_WEB_PORT": "8789",
                    "CAST_AUDIO_INGRESS_PORT": "43123",
                },
                options_path=options,
            )
        self.assertEqual(argv[argv.index("--web-port") + 1], "8789")
        self.assertEqual(argv[argv.index("--log-level") + 1], "DEBUG")
        self.assertEqual(
            argv[argv.index("--artwork-public-url") + 1],
            "http://192.0.2.1:9000",
        )
        self.assertIn("--ha-ingress", argv)
        self.assertEqual(argv[argv.index("--ingress-port") + 1], "43123")

    def test_ha_dynamic_ingress_port_is_resolved_separately_from_lan_port(self):
        with tempfile.TemporaryDirectory() as directory:
            options = Path(directory) / "options.json"
            options.write_text('{"web_port": 9000, "log_level": "INFO", "artwork_public_url": ""}')
            argv = runtime_argv(
                environ={"SUPERVISOR_TOKEN": "private"},
                options_path=options,
                supervisor_info_resolver=lambda env: {
                    "ingress_port": 43124,
                    "options": {
                        "web_port": 9000,
                        "log_level": "INFO",
                        "artwork_public_url": "",
                    },
                },
            )
        self.assertEqual(argv[argv.index("--web-port") + 1], "9000")
        self.assertEqual(argv[argv.index("--ingress-port") + 1], "43124")

    def test_ha_certificate_path_is_replaceable_without_embedding_bundle(self):
        argv = runtime_argv(
            environ={"SUPERVISOR_TOKEN": "private"},
            supervisor_info_resolver=lambda environ: {
                "options": {
                    "certificate_path": "/share/cast-audio-receiver/custom.json"
                },
                "ingress_port": 18081,
            },
        )
        self.assertEqual(
            argv[argv.index("--certs") + 1],
            "/share/cast-audio-receiver/custom.json",
        )

    def test_unknown_ha_option_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            options = Path(directory) / "options.json"
            options.write_text('{"password": "not-supported"}')
            with self.assertRaisesRegex(ValueError, "unknown Home Assistant option"):
                runtime_argv(environ={}, options_path=options)


if __name__ == "__main__":
    unittest.main()
