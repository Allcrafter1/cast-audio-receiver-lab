#!/usr/bin/env python3
"""Read-only version inventory. Does not collect logs, URLs, accounts or keys.

Run using the SAME Python environment as the adapter. Binary hashes identify
actual builds; they do not imply that a corresponding reproducible source exists.
"""
import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import shutil


def installed(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def inventory(frontend=None, airplay=None):
    report = {
        'python': platform.python_version(),
        'system': platform.system(),
        'architecture': platform.machine(),
        'packages': {name: installed(name) for name in (
            'cast-audio-receiver-lab', 'websockets', 'cryptography', 'pyOpenSSL',
            'zeroconf', 'aiohttp', 'yt-dlp', 'yt-dlp-ejs', 'deno',
            'async-upnp-client', 'soco')},
        'binaries': {},
    }
    # Hash supplied/installed binaries instead of executing arbitrary paths or
    # printing their command lines/environment. No private paths in the report.
    for name, path in [('vibecast', frontend), ('cliairplay', airplay),
                       ('ffmpeg', shutil.which('ffmpeg')), ('mpv', shutil.which('mpv'))]:
        try:
            report['binaries'][name] = {'sha256': digest(path)} if path else None
        except FileNotFoundError:
            report['binaries'][name] = {'error': 'not_found'}
        except PermissionError:
            report['binaries'][name] = {'error': 'permission_denied'}
        except OSError:
            # Never include exception text: it can expose a private install path.
            report['binaries'][name] = {'error': 'unreadable'}
    try:
        import cast_audio_lab
        report['imported_adapter_version'] = cast_audio_lab.__version__
    except ImportError:
        report['imported_adapter_version'] = None
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frontend', type=Path, help='actual deployed Vibecast binary')
    parser.add_argument('--airplay', type=Path, help='actual deployed cliairplay binary')
    args = parser.parse_args()
    print(json.dumps(inventory(args.frontend, args.airplay), indent=2))


if __name__ == '__main__':
    main()
