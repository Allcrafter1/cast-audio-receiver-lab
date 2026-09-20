#!/usr/bin/env python3
"""Read-only search for already-observed auth signatures in the test app.

Print addresses/labels only, not signatures or unrelated memory. No clock change,
key extraction, memory patch or persistent phone change. Bounded native heap scan.
"""
import argparse
import base64
import json
from pathlib import Path

import frida


AGENT=r"""
rpc.exports={scan(patterns){
  const results=[];
  let bytes=0,skipped=0;
  for (const r of Process.enumerateRanges({protection:'rw-',coalesce:true})) {
    if (r.size>64*1024*1024 || bytes+r.size>256*1024*1024 ||
        (r.file && !r.file.path.includes('libAirReceiver'))) {skipped++;continue;}
    bytes+=r.size;
    for (const p of patterns) {
      try {
        for (const hit of Memory.scanSync(r.base,r.size,p.pattern)) {
          results.push({label:p.label,address:hit.address.toString(),
              range_base:r.base.toString(),range_size:r.size});
          if (results.length>=64) return {bytes,skipped,results,capped:true};
        }
      } catch (_) { /* mapping may disappear during a read-only scan */ }
    }
  }
  return {bytes,skipped,results,capped:false};
}};
"""


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True)
    p.add_argument('--pid',required=True,type=int)
    p.add_argument('samples',nargs='+',type=Path)
    a=p.parse_args()
    patterns=[]
    for path in a.samples:
        m=json.loads(path.read_text())
        for kind in ['sig_sha1','sig_sha256']:
            encoded=m['certs'][0][kind]
            for encoding,data in [('raw',base64.b64decode(encoded,validate=True)),('base64',encoded.encode())]:
                patterns.append({'label':f'{path.stem}:{kind}:{encoding}',
                                 'pattern':data.hex(' ')})
    device=frida.get_device(a.serial,timeout=5)
    session=device.attach(a.pid)
    try:
        script=session.create_script(AGENT)
        script.load()
        print(json.dumps(script.exports_sync.scan(patterns)))
    finally:
        session.detach()


if __name__=='__main__':main()
