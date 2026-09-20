"""Translate a tiny container/Home Assistant configuration into runtime args."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen

from . import runtime


def _options(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("invalid Home Assistant options file") from error
    if not isinstance(value, dict):
        raise ValueError("Home Assistant options must be an object")
    return value


def _supervisor_self_info(
    environ: dict[str, str], *, opener=urlopen
) -> dict:
    """Read this app's non-secret configuration and allocated ingress port."""

    token = environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise ValueError("Home Assistant ingress requires SUPERVISOR_TOKEN")
    request = Request(
        "http://supervisor/addons/self/info",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with opener(request, timeout=5) as response:
            payload = json.load(response)
        data = payload.get("data", payload)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError("could not read Home Assistant app information") from error
    if not isinstance(data, dict):
        raise ValueError("Home Assistant returned invalid app information")
    return data


def runtime_argv(
    *,
    environ: dict[str, str] | None = None,
    options_path: Path = Path("/data/options.json"),
    supervisor_info_resolver=_supervisor_self_info,
) -> list[str]:
    """Build only the deliberately small public container configuration."""

    env = os.environ if environ is None else environ
    supervisor_info = None
    if env.get("SUPERVISOR_TOKEN"):
        supervisor_info = supervisor_info_resolver(env)
        ha_ingress = True
        options = supervisor_info.get("options", {})
        if not isinstance(options, dict):
            raise ValueError("Home Assistant options must be an object")
    else:
        ha_ingress = options_path.exists()
        options = _options(options_path)
    allowed = {"web_port", "log_level", "artwork_public_url", "certificate_path"}
    unknown = set(options) - allowed
    if unknown:
        raise ValueError(f"unknown Home Assistant option: {sorted(unknown)[0]}")

    data_dir = env.get("CAST_AUDIO_DATA_DIR", "/data")
    certs = env.get(
        "CAST_AUDIO_CERTS",
        str(options.get("certificate_path") or Path(data_dir) / "private" / "certs.json"),
    )
    web_port = env.get("CAST_AUDIO_WEB_PORT", str(options.get("web_port", 8788)))
    log_level = env.get("CAST_AUDIO_LOG_LEVEL", str(options.get("log_level", "INFO")))
    artwork = env.get(
        "CAST_AUDIO_ARTWORK_PUBLIC_URL", str(options.get("artwork_public_url", ""))
    ).strip()
    argv = [
        "--frontend",
        env.get("CAST_AUDIO_FRONTEND", "/usr/local/bin/vibecast"),
        "--cliairplay",
        env.get("CAST_AUDIO_CLIAIRPLAY", "/usr/local/bin/cliairplay"),
        "--data-dir",
        data_dir,
        "--certs",
        certs,
        "--web-port",
        web_port,
        "--log-level",
        log_level,
    ]
    if artwork:
        argv += ["--artwork-public-url", artwork]
    if ha_ingress:
        raw_ingress_port = env.get("CAST_AUDIO_INGRESS_PORT")
        try:
            ingress_port = (
                int(raw_ingress_port)
                if raw_ingress_port is not None
                else supervisor_info.get("ingress_port")
                if supervisor_info is not None
                else None
            )
        except (TypeError, ValueError) as error:
            raise ValueError("invalid Home Assistant ingress port") from error
        if type(ingress_port) is not int or not 1 <= ingress_port <= 65535:
            raise ValueError("invalid Home Assistant ingress port")
        argv += ["--ha-ingress", "--ingress-port", str(ingress_port)]
    return argv


def main() -> None:
    try:
        sys.argv = ["cast-audio-receiver", *runtime_argv(), *sys.argv[1:]]
    except ValueError as error:
        raise SystemExit(str(error)) from error
    runtime.main()


if __name__ == "__main__":
    main()
