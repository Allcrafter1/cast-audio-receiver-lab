import importlib.util
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
try:
    spec=importlib.util.spec_from_file_location('collector',TOOLS/'collect_certificate_windows.py')
    collector=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
finally:
    sys.path.remove(str(TOOLS))


class CollectionTests(unittest.TestCase):
    def test_keep_awake_restores_after_failure(self):
        responses = [SimpleNamespace(stdout='0'), SimpleNamespace(stdout=''),
                     SimpleNamespace(stdout='2'), SimpleNamespace(stdout='')]
        with patch.object(collector.subprocess, 'run', side_effect=responses) as run:
            with self.assertRaisesRegex(RuntimeError, 'pilot'):
                with collector.keep_awake_on_usb('test'):
                    raise RuntimeError('pilot failed')
        self.assertEqual(run.call_args.args[0][-5:],
                         ['settings','put','global','stay_on_while_plugged_in','0'])

    def test_keep_awake_preserves_user_change(self):
        with patch.object(collector.subprocess, 'run', side_effect=[
                SimpleNamespace(stdout='0'), SimpleNamespace(stdout=''),
                SimpleNamespace(stdout='7')]) as run:
            with collector.keep_awake_on_usb('test'):
                pass
        self.assertEqual(run.call_count, 3)

    def test_unknown_awake_setting_is_not_modified(self):
        with patch.object(collector.subprocess, 'run', return_value=SimpleNamespace(stdout='null')) as run:
            with self.assertRaisesRegex(RuntimeError, 'unexpected'):
                with collector.keep_awake_on_usb('test'):
                    self.fail('unexpected entry')
        self.assertEqual(run.call_count, 1)

    def test_accidental_touch_is_disabled_and_restored(self):
        responses = [SimpleNamespace(stdout='1'), SimpleNamespace(stdout=''),
                     SimpleNamespace(stdout='0'), SimpleNamespace(stdout='')]
        with patch.object(collector.subprocess, 'run', side_effect=responses) as run:
            with collector.suppress_accidental_touch('test'):
                pass
        self.assertEqual(run.call_args.args[0][-5:],
                         ['settings','put','system','screen_off_pocket','1'])

    def test_accidental_touch_preserves_user_change(self):
        responses = [SimpleNamespace(stdout='1'), SimpleNamespace(stdout=''),
                     SimpleNamespace(stdout='1')]
        with patch.object(collector.subprocess, 'run', side_effect=responses) as run:
            with collector.suppress_accidental_touch('test'):
                pass
        self.assertEqual(run.call_count, 3)

    def test_unknown_accidental_touch_setting_is_not_modified(self):
        with patch.object(collector.subprocess, 'run',
                          return_value=SimpleNamespace(stdout='null')) as run:
            with self.assertRaisesRegex(RuntimeError, 'accidental-touch'):
                with collector.suppress_accidental_touch('test'):
                    self.fail('unexpected entry')
        self.assertEqual(run.call_count, 1)

    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('window_fixtures',Path(__file__).with_name('test_certificate_windows.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.WindowMergeTests.setUpClass()
        cls.factory=module.WindowMergeTests()

    def test_collect_and_resume_without_recapturing(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            seed=directory/'seed.json'
            collector.write_new(seed,self.factory.manifest(1,3))
            a=SimpleNamespace(seed=seed,serial='test',host='localhost',max_windows=1)
            until=dt.datetime(2026,1,8,tzinfo=dt.UTC)
            requests=[]
            def run(command,**kwargs):
                target=command[command.index('--date')+1]
                requests.append(target)
                day=(dt.date.fromisoformat(target)-dt.date(2026,1,1)).days
                collector.write_new(Path(command[command.index('--output')+1]),self.factory.manifest(day,day+2))
                kwargs['stdout'].write(json.dumps({'clock_restored':True})+'\n')
                return SimpleNamespace(returncode=0)
            with patch.object(collector,'health_guard'),patch.object(collector.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()):
                collector.collect(a,directory,until)
                collector.collect(a,directory,until)
            self.assertEqual(requests,['2026-01-04','2026-01-06'])
            _,report=collector.merge([directory/'bundle-0002.json'])
            self.assertEqual(report['gaps'],[])
            self.assertEqual(report['end'],'2026-01-08T00:00:00+00:00')

    def test_failed_pilot_does_not_advance_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d); seed=directory/'seed.json'
            collector.write_new(seed,self.factory.manifest(1,3))
            a=SimpleNamespace(seed=seed,serial='test',host='localhost',max_windows=2)
            with patch.object(collector,'health_guard'),patch.object(collector.subprocess,'run',return_value=SimpleNamespace(returncode=1)) as run,contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'pilot failed'):
                    collector.collect(a,directory,dt.datetime(2026,1,8,tzinfo=dt.UTC))
            self.assertEqual(run.call_count,1)
            self.assertEqual(list(directory.glob('*.ok.json')),[])
            self.assertFalse((directory/'bundle-0001.json').exists())

    def test_health_guards_power_and_temperature(self):
        for powered,temp,okay in [('true',358,True),('false',358,False),('true',420,False)]:
            output=f'USB powered: {powered}\nlevel: 100\ntemperature: {temp}\n'
            with patch.object(collector.subprocess,'run',return_value=SimpleNamespace(stdout=output)):
                if okay:collector.health_guard('test')
                else:
                    with self.assertRaises(RuntimeError):collector.health_guard('test')

    def test_target_is_exact_end_not_end_plus_one(self):
        self.assertEqual(collector.next_target({'end':'2030-07-17T00:00:00+00:00'}),'2030-07-17')

    def test_reject_unaligned_window(self):
        with self.assertRaises(ValueError):
            collector.next_target({'end':'2030-07-17T00:00:01+00:00'})

    def test_adjacent_and_overlapping_windows_extend(self):
        old={'end':'2026-09-16T00:00:00+00:00'}
        for start in ['2026-09-16','2026-09-15']:
            collector.extends({'start':start+'T00:00:00+00:00',
                'end':'2026-09-18T00:00:00+00:00','gaps':[]},old)

    def test_gap_and_duplicate_are_rejected(self):
        old={'end':'2026-09-16T00:00:00+00:00'}
        for start,end in [('2026-09-17','2026-09-19'),('2026-09-14','2026-09-16')]:
            with self.assertRaises(ValueError):
                collector.extends({'start':start+'T00:00:00+00:00',
                    'end':end+'T00:00:00+00:00','gaps':[]},old)

    def test_restore_requires_explicit_success(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'log'
            collector.write_new(p,{'clock_restored':False})
            self.assertFalse(collector.restored(p))
            p2=Path(d)/'log2'
            collector.write_new(p2,{'clock_restored':True})
            self.assertTrue(collector.restored(p2))

    def test_existing_artifact_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'artifact'
            collector.write_new(p,{'first':True})
            with self.assertRaises(FileExistsError):
                collector.write_new(p,{'first':False})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)


if __name__=='__main__':unittest.main()
