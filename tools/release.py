#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Explicit release orchestration. No credentials, receiver state or runtime deps."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import time
import tomllib
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REPO = 'Allcrafter1/cast-audio-receiver-lab'
IMAGE = 'ghcr.io/allcrafter1/cast-audio-receiver'


def run(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def image_tag(version):
    match = re.fullmatch(r'(\d+\.\d+\.\d+)\.dev(\d+)', version)
    if not match:
        raise ValueError('Expected a Python development version, e.g. 0.6.0.dev21')
    return match[1] + '-dev' + match[2]


def candidate(root=ROOT):
    version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
    tag = image_tag(version)
    if f'__version__ = "{version}"' not in (root / 'src/cast_audio_lab/__init__.py').read_text():
        raise ValueError('Python version mismatch')
    if f'ARG BUILD_VERSION={tag}\n' not in (root / 'Containerfile').read_text():
        raise ValueError('Container version mismatch')
    return tag


def notes(tag, root=ROOT):
    text = (root / 'cast-audio-receiver/CHANGELOG.md').read_text()
    match = re.search(r'^## ' + re.escape(tag) + r'(?: —[^\n]*)?\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not match or not match[1].strip() or re.search(r'\b(TODO|TBD)\b', match[1]):
        raise ValueError('Write reviewed App changelog notes before releasing')
    return match[1].strip()


def prepare(version, root=ROOT):
    """Only local source versions; deliberately leave the HA store unchanged."""
    tag = image_tag(version)
    changes = {
        'pyproject.toml': (r'(?m)^version = "[^"\n]+"$', f'version = "{version}"'),
        'src/cast_audio_lab/__init__.py': (r'(?m)^__version__ = "[^"\n]+"$', f'__version__ = "{version}"'),
        'Containerfile': (r'(?m)^ARG BUILD_VERSION=\S+$', f'ARG BUILD_VERSION={tag}'),
    }
    updated = {}
    for name, (pattern, replacement) in changes.items():
        content, count = re.subn(pattern, replacement, (root / name).read_text())
        if count != 1:
            raise ValueError(f'Expected exactly one version in {name}')
        updated[name] = content
    for name, content in updated.items():
        (root / name).write_text(content)
    print(f'Prepared {tag}; add changelog notes, test, commit and push. App store unchanged.')


class Registry:
    def __init__(self):
        url = 'https://ghcr.io/token?service=ghcr.io&scope=repository:allcrafter1/cast-audio-receiver:pull'
        with urllib.request.urlopen(url, timeout=30) as response:
            self.token = json.load(response)['token']

    def get(self, path, expected=None):
        request = urllib.request.Request('https://ghcr.io/v2/allcrafter1/cast-audio-receiver/' + path,
            headers={'Authorization': 'Bearer ' + self.token,
                     'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
            if expected and digest != expected:
                raise ValueError('Registry digest mismatch')
            recorded = response.headers.get('Docker-Content-Digest')
            if recorded and digest != recorded:
                raise ValueError('Registry content digest mismatch')
        return json.loads(raw), digest


def verify_image(tag, sha, registry=None):
    registry = registry or Registry()
    index, digest = registry.get('manifests/' + tag)
    platforms = set()
    for item in index['manifests']:
        arch = item['platform']['architecture']
        if arch not in ('amd64', 'arm64'):
            continue
        manifest, _ = registry.get('manifests/' + item['digest'], item['digest'])
        config, _ = registry.get('blobs/' + manifest['config']['digest'], manifest['config']['digest'])
        labels = config['config']['Labels']
        if (config['architecture'] != arch or config['os'] != 'linux'
                or labels['io.hass.version'] != tag
                or labels['io.hass.arch'] != {'amd64':'amd64', 'arm64':'aarch64'}[arch]
                or labels['org.opencontainers.image.revision'] != sha):
            raise ValueError('Published image identity/platform mismatch')
        platforms.add(arch)
    if platforms != {'amd64', 'arm64'}:
        raise ValueError('Both native platforms are required')
    return digest


def guard(tag, sha):
    if run('git', 'rev-parse', 'HEAD') != sha:
        raise ValueError('Checkout differs from approved source revision')
    if run('git', 'ls-remote', 'origin', 'refs/heads/main').split()[0] != sha:
        raise ValueError('Main advanced; release a reviewed current revision')
    if run('git', 'ls-remote', 'origin', 'refs/tags/v' + tag):
        raise ValueError('Release tag already exists; never overwrite a release')
    try:
        Registry().get('manifests/' + tag)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    else:
        raise ValueError('Image tag already exists; use promotion recovery, not rebuilding')


def wait_ci(sha, timeout=2700):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        runs = json.loads(run('gh', 'run', 'list', '--repo', REPO, '--workflow', 'ci.yml',
                              '--commit', sha, '--limit', '1', '--json', 'status,conclusion,url'))
        if runs and runs[0]['status'] == 'completed':
            if runs[0]['conclusion'] != 'success':
                raise ValueError('CI is not successful: ' + runs[0]['url'])
            return
        print('Waiting for successful CI at ' + sha, flush=True)
        time.sleep(15)
    raise TimeoutError('CI did not complete successfully within 45 minutes')


def verify_source(assets, root=ROOT):
    archive = assets / 'vibecast-vendored-source.tar.gz'
    expected = (assets / 'vibecast-vendored-source.tar.gz.sha256').read_text().split()[0]
    with archive.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != expected:
            raise ValueError('Source archive checksum mismatch')
    with tarfile.open(archive, 'r:gz') as tar:
        pin = json.load(tar.extractfile('vibecast-sources/SOURCE-PIN.json'))
    if pin != json.loads((root / 'config/vibecast-frontend.lock.json').read_text()):
        raise ValueError('Source archive does not match the frontend pin')


def promoted_config(config, tag):
    result, count = re.subn(r'(?m)^version: "[^"\n]+"$', f'version: "{tag}"', config)
    if count != 1 or '\n  - amd64\n' not in result or '\n  - aarch64\n' not in result:
        raise ValueError('Unexpected App metadata; review before promoting')
    return result


def promote(tag, sha, assets):
    if run('git', 'status', '--porcelain'):
        raise ValueError('Promotion requires a clean checkout')
    if run('git', 'ls-remote', 'origin', 'refs/heads/main').split()[0] != sha:
        raise ValueError('Main advanced; stop before store promotion')
    if run('git', 'rev-parse', 'HEAD') != sha:
        raise ValueError('Promotion checkout is not the built source')
    if run('git', 'ls-remote', 'origin', 'refs/tags/v' + tag):
        raise ValueError('Release tag already exists; inspect before promotion')
    existing = subprocess.run(['gh', 'release', 'view', 'v' + tag, '--repo', REPO],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if existing.returncode == 0:
        raise ValueError('Release already exists; inspect before promotion')
    wait_ci(sha)
    verify_source(assets)
    digest = verify_image(tag, sha)
    if (assets / 'image-digest.txt').read_text().strip() != digest:
        raise ValueError('Build record differs from anonymous registry readback')
    recorded_manifest = 'sha256:' + hashlib.sha256((assets / 'image-manifest.json').read_bytes()).hexdigest()
    if recorded_manifest != digest:
        raise ValueError('Manifest artifact checksum differs from published index')
    release_notes = notes(tag) + f'\n\nImage: `{IMAGE}:{tag}`\n\nDigest: `{digest}`\n\nSource: `{sha}`\n'
    (assets / 'release-notes.md').write_text(release_notes)
    path = ROOT / 'cast-audio-receiver/config.yaml'
    previous_tag = re.search(r'(?m)^version: "([^"\n]+)"$', path.read_text()).group(1)
    path.write_text(promoted_config(path.read_text(), tag))
    # Keep the two prominent install references in sync; no global history rewrite.
    for name in ('README.md', 'docs/installation.md'):
        doc = ROOT / name
        content = re.sub(re.escape(IMAGE) + r':\d+\.\d+\.\d+-dev\d+', IMAGE + ':' + tag, doc.read_text())
        doc.write_text(content.replace('**' + previous_tag + '**', '**' + tag + '**'))
    run('git', 'add', 'cast-audio-receiver/config.yaml', 'README.md', 'docs/installation.md')
    if run('git', 'diff', '--cached', '--name-only'):
        run('git', '-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit', '-m', f'release: promote verified {tag} App metadata [skip ci]')
        run('git', 'push', 'origin', 'HEAD:main')  # normal fast-forward push; never force
    target = run('git', 'rev-parse', 'HEAD')
    run('gh', 'release', 'create', 'v' + tag, '--repo', REPO, '--target', target,
        '--title', tag + ' — experimental pre-release', '--prerelease', '--latest=false',
        '--notes-file', str(assets / 'release-notes.md'),
        *[str(assets / name) for name in ('image-digest.txt', 'image-manifest.json',
            'vibecast-vendored-source.tar.gz', 'vibecast-vendored-source.tar.gz.sha256')])
    print(f'Published {tag}. Check the INSTALLED HA app repository, not only store availability.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'plan', 'guard', 'wait-ci', 'verify', 'promote'])
    parser.add_argument('--version', help='Python source version for prepare')
    parser.add_argument('--expected-tag')
    parser.add_argument('--sha', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--execute', action='store_true', help='Required for file writes or publication')
    args = parser.parse_args()
    if args.command == 'prepare':
        if not args.execute or not args.version:
            parser.error('prepare requires --version and --execute (local files only)')
        prepare(args.version)
        return
    tag = candidate()
    if args.expected_tag != tag:
        parser.error(f'Expected-tag must explicitly equal source version {tag}')
    notes(tag)
    if args.command == 'plan':
        print(f'{tag}: CI -> cached native builds + offline source -> public readback -> App metadata -> prerelease')
        print('No writes. Existing tags are refused. No live receiver or HA installation is changed.')
        return
    if not args.sha or not re.fullmatch('[0-9a-f]{40}', args.sha):
        parser.error('An exact 40-character source SHA is required')
    if args.command == 'guard':
        guard(tag, args.sha)
    elif args.command == 'wait-ci':
        wait_ci(args.sha)
    elif args.command == 'verify':
        print(verify_image(tag, args.sha))
    elif args.command == 'promote':
        if not args.execute or not args.assets:
            parser.error('promote requires --execute and --assets')
        promote(tag, args.sha, args.assets.resolve())


if __name__ == '__main__':
    main()
