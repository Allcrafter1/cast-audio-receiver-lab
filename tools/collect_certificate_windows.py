#!/usr/bin/env python3
"""Sequential, resumable private collection using the bounded phone pilot.

Each window restores the phone independently. No runtime manifest is changed.
Stop at the first failure; never turn a failed or unverified capture into coverage.
Create a STOP file in the job directory to stop after the current safe restoration.
"""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from contextlib import contextmanager

from merge_certificate_windows import merge


def next_target(report):
    end = dt.datetime.fromisoformat(report['end'])
    if end.time() != dt.time(0):
        raise ValueError('pilot requires midnight-aligned windows')
    return end.date().isoformat()


def extends(report, previous):
    lo, hi = (dt.datetime.fromisoformat(report[k]) for k in ('start','end'))
    end = dt.datetime.fromisoformat(previous['end'])
    if report['gaps'] or not lo <= end < hi:
        raise ValueError('new window does not extend contiguous coverage')


def write_new(path, value):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(value,f)
        f.flush()
        os.fsync(f.fileno())


def restored(log):
    for line in log.read_text().splitlines():
        try:
            if json.loads(line).get('clock_restored') is True:
                return True
        except (ValueError,AttributeError):
            pass
    return False


def health_guard(serial):
    result=subprocess.run(['adb','-s',serial,'shell','-n','dumpsys battery'],
        check=True,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=12)
    values={k.strip():v.strip() for line in result.stdout.splitlines()
            if ':' in line for k,v in [line.split(':',1)]}
    if not any(values.get(k)=='true' for k in ['USB powered','AC powered','Wireless powered']):
        raise RuntimeError('unattended collection requires external phone power')
    if int(values.get('level','-1'))<20:
        raise RuntimeError('phone battery too low for unattended collection')
    if not 0<=int(values.get('temperature','-1'))<420:
        raise RuntimeError('phone temperature outside conservative collection guard')


@contextmanager
def keep_awake_on_usb(serial):
    """Keep an already-unlocked test phone awake; never dismiss a secure lock."""
    adb = ['adb', '-s', serial, 'shell', '-n']
    def call(*args):
        return subprocess.run(adb + list(args), check=True, capture_output=True,
                              text=True, timeout=12).stdout.strip()
    previous = call('settings', 'get', 'global', 'stay_on_while_plugged_in')
    if previous not in {str(n) for n in range(8)}:
        raise RuntimeError('unexpected stay-awake setting; refusing change')
    try:
        call('svc', 'power', 'stayon', 'usb')
        yield
    finally:
        # Do not overwrite a setting the user deliberately changed meanwhile.
        if call('settings', 'get', 'global', 'stay_on_while_plugged_in') == '2':
            call('settings', 'put', 'global', 'stay_on_while_plugged_in', previous)


@contextmanager
def suppress_accidental_touch(serial):
    """Temporarily disable Samsung's pocket overlay during unattended UI checks."""
    adb = ['adb', '-s', serial, 'shell', '-n']
    def call(*args):
        return subprocess.run(adb + list(args), check=True, capture_output=True,
                              text=True, timeout=12).stdout.strip()
    previous = call('settings', 'get', 'system', 'screen_off_pocket')
    if previous not in {'0', '1'}:
        raise RuntimeError('unexpected accidental-touch setting; refusing change')
    try:
        if previous == '1':
            call('settings', 'put', 'system', 'screen_off_pocket', '0')
        yield
    finally:
        # Preserve a concurrent user change. Restore only our temporary value.
        if previous == '1' and call('settings', 'get', 'system', 'screen_off_pocket') == '0':
            call('settings', 'put', 'system', 'screen_off_pocket', previous)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True)
    p.add_argument('--host',required=True)
    p.add_argument('--seed',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--until',required=True,help='exclusive coverage end, UTC YYYY-MM-DD')
    p.add_argument('--max-windows',type=int,default=16)
    a=p.parse_args()
    directory=a.directory.resolve()
    if '.state' not in directory.parts or a.max_windows<1:
        p.error('private .state directory and positive max-windows required')
    until=dt.datetime.fromisoformat(a.until).replace(tzinfo=dt.UTC)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=os.fdopen(os.open(directory/'collector.lock',os.O_RDWR|os.O_CREAT,0o600),'w')
    with lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        health_guard(a.serial)
        with keep_awake_on_usb(a.serial):
            with suppress_accidental_touch(a.serial):
                collect(a,directory,until)


def collect(a,directory,until):
    paths=[a.seed.resolve()]
    seed,report=merge(paths)
    if report['gaps']:
        raise ValueError('seed has coverage gaps')
    identity=(seed['cpu'],seed['ica'])
    limit=min(until,dt.datetime.fromisoformat(report['chain_expires']))
    receipts=sorted(directory.glob('window-*.ok.json'))
    for receipt in receipts:
        info=json.loads(receipt.read_text())
        path=directory/info['file']
        if path.parent!=directory or not path.name.startswith('window-'):
            raise ValueError('unexpected checkpoint path')
        one,r=merge([path])
        if (one['cpu'],one['ica'])!=identity:
            raise ValueError('identity changed during collection')
        extends(r,report)
        report['end']=r['end']
        paths.append(path)
    def checkpoint():
        manifest,summary=merge(paths)
        if summary['gaps']:
            raise ValueError('checkpoint would have gaps')
        output=directory/f"bundle-{len(paths)-1:04d}.json"
        if not output.exists():
            write_new(output,manifest)
        else:
            _,existing=merge([output])
            # Input-level duplicate counts differ between a set of source
            # windows and its already-deduplicated checkpoint; coverage must not.
            diagnostics = {'source_entries', 'duplicate_entries', 'distinct_public_keys'}
            if ({k:v for k,v in existing.items() if k not in diagnostics} !=
                    {k:v for k,v in summary.items() if k not in diagnostics}):
                raise ValueError('existing checkpoint disagrees with receipts')
        print(json.dumps({'checkpoint':str(output),**summary}),flush=True)
    checkpoint()
    for _ in range(a.max_windows):
        if (directory/'STOP').exists() or dt.datetime.fromisoformat(report['end'])>=limit:
            break
        target=next_target(report)
        path=directory/f'window-{target}.json'
        log=path.with_suffix('.log')
        # A prior incomplete attempt is evidence to investigate, not silently reuse.
        if path.exists() or log.exists():
            raise RuntimeError('incomplete attempt exists; inspect before retrying')
        try:
            health_guard(a.serial)
        except Exception:
            checkpoint()
            raise
        command=[sys.executable,str(Path(__file__).with_name('capture_future_window.py')),
            '--serial',a.serial,'--host',a.host,'--date',target,'--offline','--output',str(path)]
        with os.fdopen(os.open(log,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
            result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=f,stderr=f,
                env=dict(os.environ,PYTHONPATH='src'),timeout=180)
        if result.returncode or not restored(log):
            checkpoint()
            raise RuntimeError(f'pilot failed; collection stopped, private log: {log}')
        one,r=merge([path])
        if (one['cpu'],one['ica'])!=identity:
            raise ValueError('identity changed during collection')
        extends(r,report)
        report['end']=r['end']
        write_new(path.with_suffix('.ok.json'),{'file':path.name,'clock_restored':True,**r})
        paths.append(path)
        print(json.dumps({'collected':path.name,'coverage_end':r['end']}),flush=True)
        if (len(paths)-1)%16==0:
            checkpoint()
    checkpoint()
    print(json.dumps({'stopped_safely':True,'coverage_end':report['end'],
        'requested_end_reached':dt.datetime.fromisoformat(report['end'])>=limit}),flush=True)


if __name__=='__main__':
    main()
