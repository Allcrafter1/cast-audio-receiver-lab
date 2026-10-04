# SPDX-License-Identifier: MPL-2.0
"""Offline release safety gates; no publishing, credentials or live receivers."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.error

from tools import release


class ReleaseAutomationTests(unittest.TestCase):
    def test_version_conversion_rejects_shell_and_stable_inputs(self):
        self.assertEqual(release.image_tag('0.6.0.dev21'), '0.6.0-dev21')
        for bad in ['0.6.0', '0.6.0-dev21', '0.6.0.dev21;echo', '../dev21']:
            with self.assertRaises(ValueError):
                release.image_tag(bad)

    def fixture(self, root):
        files = {
            'pyproject.toml':'[project]\nversion = "0.6.0.dev20"\n',
            'src/cast_audio_lab/__init__.py':'__version__ = "0.6.0.dev20"\n',
            'Containerfile':'ARG BUILD_VERSION=0.6.0-dev20\n',
            'cast-audio-receiver/config.yaml':'version: "0.6.0-dev20"\narch:\n  - amd64\n  - aarch64\n',
            'cast-audio-receiver/CHANGELOG.md':'# Notes\n\n## 0.6.0-dev20 — tested\n\n- Real change.\n\n## 0.6.0-dev18\nOld.\n',
        }
        for name, value in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)

    def test_prepare_keeps_store_on_available_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            store = (root / 'cast-audio-receiver/config.yaml').read_bytes()
            release.prepare('0.6.0.dev21', root)
            self.assertEqual(release.candidate(root), '0.6.0-dev21')
            self.assertEqual((root / 'cast-audio-receiver/config.yaml').read_bytes(), store)

    def test_notes_only_selected_version_and_no_placeholders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertEqual(release.notes('0.6.0-dev20', root), '- Real change.')
            with self.assertRaises(ValueError):
                release.notes('0.6.0-dev21', root)
            (root / 'cast-audio-receiver/CHANGELOG.md').write_text('## 0.6.0-dev20\n- TODO\n')
            with self.assertRaises(ValueError):
                release.notes('0.6.0-dev20', root)

    def test_source_version_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            (root / 'Containerfile').write_text('ARG BUILD_VERSION=0.6.0-dev19\n')
            with self.assertRaises(ValueError):
                release.candidate(root)

    def registry(self):
        tag, sha = '0.6.0-dev21', 'a' * 40
        records = {'manifests/' + tag: ({'manifests':[
            {'platform':{'architecture':arch}, 'digest':arch} for arch in ['amd64','arm64']]}, 'index')}
        for arch, ha_arch in [('amd64','amd64'), ('arm64','aarch64')]:
            records['manifests/' + arch] = ({'config':{'digest':'config-' + arch}}, arch)
            records['blobs/config-' + arch] = ({'architecture':arch, 'os':'linux', 'config':{'Labels':{
                'io.hass.version':tag, 'io.hass.arch':ha_arch, 'org.opencontainers.image.revision':sha}}}, arch)
        registry = Mock()
        registry.get.side_effect = lambda path, expected=None: records[path]
        return registry, records, tag, sha

    def test_public_image_requires_both_correct_architectures(self):
        registry, records, tag, sha = self.registry()
        self.assertEqual(release.verify_image(tag, sha, registry), 'index')
        records['manifests/' + tag][0]['manifests'].pop()
        with self.assertRaises(ValueError):
            release.verify_image(tag, sha, registry)

    def test_public_image_rejects_wrong_version_revision_or_architecture(self):
        for field in ['io.hass.version', 'io.hass.arch', 'org.opencontainers.image.revision']:
            registry, records, tag, sha = self.registry()
            records['blobs/config-arm64'][0]['config']['Labels'][field] = 'wrong'
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.verify_image(tag, sha, registry)

    def test_guard_refuses_existing_release_or_moving_main(self):
        sha = 'a' * 40
        for outputs in [[sha, 'b' * 40 + '\trefs/heads/main'],
                        [sha, sha + '\trefs/heads/main', sha + '\trefs/tags/v0.6.0-dev21']]:
            with patch.object(release, 'run', side_effect=outputs), self.assertRaises(ValueError):
                release.guard('0.6.0-dev21', sha)

    def test_guard_only_treats_404_as_missing_image(self):
        sha = 'a' * 40
        for code in [404, 401, 500]:
            registry = Mock()
            registry.get.side_effect = urllib.error.HTTPError('registry', code, 'failure', {}, None)
            with patch.object(release, 'run', side_effect=[sha, sha + '\trefs/heads/main', '']), patch.object(release, 'Registry', return_value=registry):
                if code == 404:
                    release.guard('0.6.0-dev21', sha)
                else:
                    with self.assertRaises(urllib.error.HTTPError):
                        release.guard('0.6.0-dev21', sha)

    def test_failed_ci_cannot_promote(self):
        with patch.object(release, 'run', return_value=json.dumps([{'status':'completed','conclusion':'failure','url':'test'}])):
            with self.assertRaises(ValueError):
                release.wait_ci('a' * 40)

    def test_successful_ci_and_promoted_config(self):
        with patch.object(release, 'run', return_value=json.dumps([{'status':'completed','conclusion':'success'}])):
            release.wait_ci('a' * 40)
        config = 'version: "0.6.0-dev20"\narch:\n  - amd64\n  - aarch64\n'
        self.assertIn('version: "0.6.0-dev21"', release.promoted_config(config, '0.6.0-dev21'))
        with self.assertRaises(ValueError):
            release.promoted_config(config.replace('  - aarch64\n',''), '0.6.0-dev21')

    def test_source_archive_must_match_hash_and_full_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'config').mkdir()
            pin = {'commit':'a' * 40, 'repository':'https://example.invalid/frontend'}
            (root / 'config/vibecast-frontend.lock.json').write_text(json.dumps(pin))
            archive = root / 'vibecast-vendored-source.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                body = json.dumps(pin).encode()
                info = tarfile.TarInfo('vibecast-sources/SOURCE-PIN.json')
                info.size = len(body)
                tar.addfile(info, io.BytesIO(body))
            (root / 'vibecast-vendored-source.tar.gz.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '  source.tar.gz\n')
            release.verify_source(root, root)
            (root / 'config/vibecast-frontend.lock.json').write_text('{}')
            with self.assertRaises(ValueError):
                release.verify_source(root, root)
            (root / 'vibecast-vendored-source.tar.gz.sha256').write_text('0' * 64)
            with self.assertRaises(ValueError):
                release.verify_source(root, root)

    def test_release_is_explicit_and_waits_for_both_artifacts(self):
        workflow = (release.ROOT / '.github/workflows/release.yml').read_text()
        self.assertIn('default: false', workflow)
        self.assertIn('needs: [image, source]', workflow)
        self.assertIn('if: inputs.publish', workflow)
        self.assertIn('tools/release.py guard', workflow)
        self.assertIn('tools/release.py wait-ci', workflow)
        self.assertNotIn('ssh ', workflow)
        container = (release.ROOT / 'Containerfile').read_text()
        self.assertGreater(container.index('ARG BUILD_VERSION='), container.index('RUN groupadd'))
        for name in ['ci.yml','publish-image.yml']:
            content = (release.ROOT / '.github/workflows' / name).read_text()
            self.assertIn('mode=max,timeout=2m,ignore-error=true', content)

    def test_promotion_does_not_write_metadata_before_all_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            before = (root / 'cast-audio-receiver/config.yaml').read_bytes()
            sha = 'a' * 40
            with patch.object(release, 'ROOT', root), patch.object(release, 'run', side_effect=['', sha + '\trefs/heads/main', sha, '']), patch.object(release.subprocess, 'run', return_value=Mock(returncode=1)), patch.object(release, 'wait_ci'), patch.object(release, 'verify_source'), patch.object(release, 'verify_image', side_effect=ValueError('Wrong image')):
                with self.assertRaises(ValueError):
                    release.promote('0.6.0-dev21', sha, root)
            self.assertEqual((root / 'cast-audio-receiver/config.yaml').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
