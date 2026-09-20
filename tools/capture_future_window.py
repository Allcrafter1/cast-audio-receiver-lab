#!/usr/bin/env python3
"""Bounded single-window test; restores phone time even on capture failure.

Requires the user's explicit clock-change authorization. Only the selected
test phone is changed. A separate phone-local watchdog restores time if the
host disappears. Existing capture helper keeps credential output private.
"""
import argparse
import fcntl
import datetime as dt
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time
import re
import xml.etree.ElementTree as ET

NATIVE_TRACE = r"""
const counts = {}, adjustments = [], certificates = [];
Process.attachModuleObserver({onAdded(m) {
  if (m.name !== 'libAirReceiver.so') return;
  for (const name of ['X509_sign','X509_gmtime_adj','ASN1_TIME_set',
      'ASN1_TIME_adj','PEM_read_bio_X509','d2i_X509','SSL_CTX_use_certificate']) {
    const address = m.findExportByName(name);
    if (!address) continue;
    counts[name] = 0;
    Interceptor.attach(address, {onEnter(args) {
      counts[name]++;
      if ((name === 'X509_gmtime_adj' || name === 'ASN1_TIME_set') && adjustments.length < 16)
        adjustments.push({function:name, seconds:args[1].toInt32()});
    }, onLeave(result) {
      if (name !== 'PEM_read_bio_X509' || result.isNull() || certificates.length >= 16) return;
      const der = new NativeFunction(m.getExportByName('i2d_X509'), 'int', ['pointer','pointer']);
      const length = der(result, ptr(0));
      if (length <= 0 || length > 16384) return;
      const buffer = Memory.alloc(length), cursor = Memory.alloc(Process.pointerSize);
      cursor.writePointer(buffer);
      if (der(result, cursor) === length) {
        certificates.push(length);
        send({kind:'public_certificate'},buffer.readByteArray(length));
      }
    }});
  }
}});
rpc.exports = {stats() {
  const now = new NativeFunction(Process.getModuleByName('libc.so').getExportByName('time'),
      'int64', ['pointer'])(ptr(0)).toString();
  return {counts, adjustments, process_epoch:now};
}};
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', required=True)
    p.add_argument('--host', required=True)
    p.add_argument('--date', required=True, help='UTC YYYY-MM-DD')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--isolate-cast-cache', action='store_true',
                   help='temporarily move only app_cast/config.json; restore original afterwards')
    p.add_argument('--observe-native', action='store_true',
                   help='attach after activity launch; count certificate calls around Start, no secrets')
    p.add_argument('--offline', action='store_true', help='disable Wi-Fi/mobile data temporarily, capture over USB')
    p.add_argument('--isolate-paired-cache', action='store_true', help='temporarily omit only cks2 preference, restore original XML')
    a = p.parse_args()
    target = int(dt.datetime.fromisoformat(a.date).replace(tzinfo=dt.UTC).timestamp())
    output = a.output.resolve()
    if '.state' not in output.parts or output.exists():
        p.error('output must be a new path below ignored .state')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+',a.serial):
        p.error('unexpected serial characters')
    Path('.state').mkdir(exist_ok=True,mode=0o700)
    # Retained until process exit, including all restoration and UI operations.
    phone_lock = os.fdopen(os.open(Path('.state') / f'certificate-phone-{a.serial}.lock',
                                   os.O_RDWR|os.O_CREAT,0o600),'w')
    fcntl.flock(phone_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    adb = ['adb', '-s', a.serial]
    def run(args, timeout=12):
        return subprocess.run(args, check=True, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout).stdout.strip()
    def shell(command):
        return run(adb + ['shell', '-n', command])
    def root(command):
        return shell('su -c ' + shlex.quote(command))
    assert 'uid=0' in root('id')
    automatic = shell('settings get global auto_time')
    if automatic not in ('0','1'):
        raise RuntimeError('unexpected time setting; refusing mutation')
    epoch = int(shell('date -u +%s'))
    uptime = int(float(shell('cat /proc/uptime').split()[0]))
    snapshot = {'epoch':epoch, 'uptime':uptime, 'auto_time':automatic,
                'auto_time_zone':shell('settings get global auto_time_zone'),
                'timezone':shell('getprop persist.sys.timezone'), 'target':target}
    wifi = shell('settings get global wifi_on') if a.offline else ''
    mobile = shell('settings get global mobile_data') if a.offline else ''
    if a.offline and (wifi not in ('0','1') or mobile not in ('0','1')):
        raise RuntimeError('unexpected network settings; refusing mutation')
    snapshot.update(wifi=wifi,mobile_data=mobile)
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    journal = output.with_suffix('.clock.json')
    with os.fdopen(os.open(journal, os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(snapshot,f)
    script = '/data/local/tmp/castlab-clock-restore.sh'
    run(adb + ['push',str(Path(__file__).with_name('android_clock_restore.sh')),script])
    cache = '/data/user/0/com.softmedia.receiver/app_cast/config.json'
    backup = cache + f'.clockpilot-{epoch}' if a.isolate_cast_cache else ''
    if backup:
        root(f'test -f {cache} && test ! -e {backup} && test ! -e {backup}.generated')
    paired='/data/user/0/com.softmedia.receiver/shared_prefs/SoftMediaPairedData.xml'
    paired_backup=paired+f'.clockpilot-{epoch}' if a.isolate_paired_cache else ''
    paired_test=None
    if paired_backup:
        root(f'test -f {paired} && test ! -e {paired_backup} && test ! -e {paired_backup}.generated')
        original=root(f'cat {paired}')
        tree=ET.fromstring(original)
        entry=next((n for n in tree if n.get('name')=='cks2'),None)
        if entry is None:raise RuntimeError('expected cks2 entry absent')
        tree.remove(entry)
        paired_test=output.with_suffix('.paired-test.xml')
        with os.fdopen(os.open(paired_test,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:
            f.write(ET.tostring(tree,encoding='utf-8',xml_declaration=True))
        run(adb+['push',str(paired_test),'/data/local/tmp/castlab-paired-test.xml'])
    watchdog = root(f'nohup sh {script} {epoch} {uptime} {automatic} 90 '
                    f'{shlex.quote(backup)} {shlex.quote(wifi)} {shlex.quote(mobile)} {shlex.quote(paired_backup)} '
                    '> /data/local/tmp/castlab-clock-restore.log 2>&1 < /dev/null & echo $!')
    if not watchdog.isdigit():
        raise RuntimeError('watchdog PID unavailable; refusing mutation')
    observations = []
    observed_certificates = []
    capture_host, capture_port = a.host, 8009
    forwarded = None
    def launch(observe=False):
        shell('am force-stop com.softmedia.receiver')
        shell('am start -n com.softmedia.receiver/.app.SplashActivity')
        if observe:
            import frida
            device = frida.get_device(a.serial,timeout=5)
            deadline = time.monotonic()+5
            pid_text = shell('pidof com.softmedia.receiver || true')
            while not pid_text.isdigit() and time.monotonic()<deadline:
                time.sleep(.1)
                pid_text = shell('pidof com.softmedia.receiver || true')
            if not pid_text.isdigit(): raise RuntimeError('app PID unavailable for observation')
            pid = int(pid_text)
            session = device.attach(pid)
            script = session.create_script(NATIVE_TRACE)
            def public_certificate(message, data):
                if message.get('type') != 'send' or message.get('payload',{}).get('kind') != 'public_certificate':
                    return
                from cryptography import x509
                from cryptography.hazmat.primitives import hashes
                try:
                    c = x509.load_der_x509_certificate(data)
                    observed_certificates.append({'sha256':c.fingerprint(hashes.SHA256()).hex(),
                        'not_before':c.not_valid_before_utc.isoformat(),
                        'not_after':c.not_valid_after_utc.isoformat()})
                except ValueError:
                    pass
            script.on('message',public_certificate)
            script.load()
            observations.append((session,script))
        def ui_nodes():
            try:
                shell('uiautomator dump /data/local/tmp/castlab-ui.xml')
            except subprocess.CalledProcessError as error:
                # Samsung occasionally kills the short-lived dump process under
                # repeated launches (shell reports 137). Retry inside the same
                # bounded readiness window; never waive the Ready To Cast gate.
                if error.returncode in {-9, 137}:
                    return None
                raise
            raw = shell('cat /data/local/tmp/castlab-ui.xml')
            return [n for n in ET.fromstring(raw).iter('node')
                    if n.get('package')=='com.softmedia.receiver']
        ui_deadline = time.monotonic() + 10
        tapped = False
        while True:
            nodes = ui_nodes()
            if nodes is None:
                if time.monotonic() >= ui_deadline:
                    raise RuntimeError('receiver UI inspection repeatedly killed during bounded wait')
                time.sleep(.3)
                continue
            if any(n.get('text')=='Ready To Cast' for n in nodes):
                break
            if time.monotonic() >= ui_deadline:
                raise RuntimeError('receiver UI not Ready To Cast after bounded wait; check lock screen and app state')
            start = next((n for n in nodes if n.get('text','').upper()=='START'),None)
            if start is not None and not tapped:
                bounds = list(map(int,re.findall(r'\d+',start.get('bounds',''))))
                if len(bounds)!=4: raise RuntimeError('Start button bounds unavailable')
                shell(f'input tap {(bounds[0]+bounds[2])//2} {(bounds[1]+bounds[3])//2}')
                tapped = True
            time.sleep(.3)
        print(json.dumps({'receiver_ui':'Ready To Cast'}),flush=True)
        deadline = time.monotonic()+20
        while time.monotonic()<deadline:
            pid = shell('pidof com.softmedia.receiver || true')
            try:
                with socket.create_connection((capture_host,capture_port),timeout=1):
                    if pid.isdigit(): return pid
            except OSError:
                pass
            time.sleep(.3)
        raise RuntimeError('Cast endpoint did not restart')
    try:
        if paired_backup:
            shell('am force-stop com.softmedia.receiver')
            root(f'cp -p {paired} {paired_backup}')
            root(f'cat /data/local/tmp/castlab-paired-test.xml > {paired}')
        if a.offline:
            forwarded = int(run(adb+['forward','tcp:0','tcp:8009']))
            capture_host, capture_port = '127.0.0.1', forwarded
            root('svc wifi disable')
            root('svc data disable')
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                routes=shell('ip -4 route show table all default; ip -6 route show table all default')
                if not any(l.startswith('default ') for l in routes.splitlines()) and shell('settings get global wifi_on')=='0': break
                time.sleep(.3)
            else:
                raise RuntimeError('offline routing state not confirmed')
            print(json.dumps({'wifi':False,'default_routes':False,'capture_transport':'USB'}),flush=True)
        if backup:
            shell('am force-stop com.softmedia.receiver')
            root(f'mv {cache} {backup}')
        root('settings put global auto_time 0')
        root(f'date -u @{target}')
        pid = launch(a.observe_native)
        observed = int(shell('date -u +%s'))
        if abs(observed-target)>60:
            raise RuntimeError('phone did not retain requested time; refusing capture')
        if observations:
            stats=observations[-1][1].exports_sync.stats()
            print(json.dumps({'native_start_observation':stats,
                              'loaded_public_certificates':observed_certificates}),flush=True)
        env = dict(os.environ, PYTHONPATH='src')
        try:
            result = run([sys.executable, str(Path(__file__).with_name('capture_airreceiver_window.py')),
                '--serial',a.serial,'--pid',pid,'--host',capture_host,'--port',str(capture_port),
                '--output',str(output)],timeout=40)
        except subprocess.CalledProcessError as error:
            error_path=output.with_suffix('.capture-error.txt')
            with os.fdopen(os.open(error_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
                f.write(error.stderr)
            raise RuntimeError(f'capture helper failed; private diagnostic saved at {error_path}') from None
        print(result,flush=True)
        from cryptography import x509
        manifest = json.loads(output.read_text())
        peer = x509.load_pem_x509_certificate(manifest['certs'][0]['pu'].encode())
        if not (peer.not_valid_before_utc.timestamp() <= target < peer.not_valid_after_utc.timestamp()):
            raise RuntimeError('captured certificate does not cover target with remaining validity; retained as diagnostic only')
    finally:
        for session, _ in observations:
            try: session.detach()
            except Exception: pass
        # Keep watchdog alive until the host has verified its own restoration.
        elapsed = int(float(shell('cat /proc/uptime').split()[0]))-uptime
        root(f'date -u @{epoch+elapsed}')
        root(f'settings put global auto_time {automatic}')
        if a.offline:
            root('svc wifi '+('enable' if wifi=='1' else 'disable'))
            root('svc data '+('enable' if mobile=='1' else 'disable'))
        if backup:
            shell('am force-stop com.softmedia.receiver')
            root(f'if [ -f {backup} ]; then '
                 f'if [ -f {cache} ]; then mv {cache} {backup}.generated; fi; '
                 f'mv {backup} {cache}; fi')
        if paired_backup:
            shell('am force-stop com.softmedia.receiver')
            root(f'if [ -f {paired_backup} ]; then mv {paired} {paired_backup}.generated; '
                 f'mv {paired_backup} {paired}; fi')
        restored = int(shell('date -u +%s'))
        if abs(restored-(epoch+elapsed))>5 or shell('settings get global auto_time')!=automatic:
            raise RuntimeError('clock restore verification failed; watchdog still armed')
        root(f'kill {watchdog}')
        print(json.dumps({'clock_restored':True,'auto_time':automatic,
                          'utc':dt.datetime.fromtimestamp(restored,dt.UTC).isoformat()}),flush=True)
        try:
            launch()  # Recreate current-date context; never leave future TLS active.
        finally:
            if forwarded is not None:
                run(adb+['forward','--remove',f'tcp:{forwarded}'])
        print(json.dumps({'current_receiver_ready':True}),flush=True)


if __name__=='__main__':
    main()
