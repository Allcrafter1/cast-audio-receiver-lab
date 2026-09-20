import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('support_inventory',
    Path(__file__).parents[1] / 'tools/support_inventory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InventoryTests(unittest.TestCase):
    def test_missing_binary_does_not_discard_remaining_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'private-missing-binary'
            with patch.object(module.shutil, 'which', return_value=None):
                result = module.inventory(frontend=missing)
            self.assertEqual(result['binaries']['vibecast'], {'error': 'not_found'})
            self.assertIn('packages', result)
            self.assertNotIn(directory, str(result))
            self.assertNotIn('private-missing-binary', str(result))

    def test_unreadable_binary_uses_fixed_error_without_exception_details(self):
        with patch.object(module.shutil, 'which', return_value=None), \
                patch.object(module, 'digest', side_effect=PermissionError('private-path')):
            result = module.inventory(frontend=Path('private-path'))
        self.assertEqual(result['binaries']['vibecast'], {'error': 'permission_denied'})
        self.assertNotIn('private-path', str(result))

    def test_hashes_binary_without_executing_or_printing_path(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'private-name'
            binary.write_bytes(b'abc')
            with patch.object(module.shutil, 'which', return_value=None):
                result = module.inventory(frontend=binary)
            self.assertEqual(result['binaries']['vibecast']['sha256'],
                'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
            self.assertNotIn(directory, str(result))
            self.assertNotIn('private-name', str(result))
