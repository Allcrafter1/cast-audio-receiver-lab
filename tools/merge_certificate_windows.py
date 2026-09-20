#!/usr/bin/env python3
"""Validate and merge private, same-identity Cast TLS windows. Never print keys.

This verifies cryptographic consistency, NOT Google acceptance or revocation.
The installed manifest is not replaced by this utility.
"""
import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _validity(cert):
    """Return timezone-aware validity on cryptography 41 and newer releases."""
    before = getattr(cert, "not_valid_before_utc", None)
    after = getattr(cert, "not_valid_after_utc", None)
    if before is None:
        before = cert.not_valid_before.replace(tzinfo=dt.UTC)
    if after is None:
        after = cert.not_valid_after.replace(tzinfo=dt.UTC)
    return before, after


def merge(paths):
    merged = None
    entries = {}
    source_entries = 0
    for path in paths:
        m = json.loads(path.read_text())
        if merged is None:
            merged = {'cpu': m['cpu'], 'ica': m['ica'], 'certs': []}
        if (m['cpu'],m['ica']) != (merged['cpu'],merged['ica']):
            raise ValueError('different device identities/chains cannot share this manifest')
        device = x509.load_pem_x509_certificate(m['cpu'].encode())
        chain = x509.load_pem_x509_certificates(m['ica'].encode())
        if not chain: raise ValueError('missing intermediate chain')
        for child, parent in zip([device]+chain,chain):
            if child.issuer != parent.subject: raise ValueError('issuer mismatch')
            parent.public_key().verify(child.signature,child.tbs_certificate_bytes,
                padding.PKCS1v15(),child.signature_hash_algorithm)
        for entry in m['certs']:
            source_entries += 1
            cert=x509.load_pem_x509_certificate(entry['pu'].encode())
            key=serialization.load_pem_private_key(entry['pr'].encode(),password=None)
            enc=serialization.Encoding.DER; fmt=serialization.PublicFormat.SubjectPublicKeyInfo
            if cert.public_key().public_bytes(enc,fmt)!=key.public_key().public_bytes(enc,fmt):
                raise ValueError('TLS key mismatch')
            der=cert.public_bytes(enc)
            for name,algorithm in [('sig_sha1',hashes.SHA1()),('sig_sha256',hashes.SHA256())]:
                device.public_key().verify(base64.b64decode(entry[name],validate=True),der,
                    padding.PKCS1v15(),algorithm)
            entries[der]=(*_validity(cert),entry)
    if merged is None or not entries: raise ValueError('no windows')
    ordered=sorted(entries.values(),key=lambda v:(v[0],v[1]))
    start,end=ordered[0][:2]
    gaps=[]
    for lo,hi,_ in ordered:
        if hi<=lo: raise ValueError('invalid validity interval')
        if lo>end:gaps.append((end.isoformat(),lo.isoformat()))
        end=max(end,hi)
    merged['certs']=[e for _,_,e in ordered]
    public_keys = {
        x509.load_pem_x509_certificate(e['pu'].encode()).public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        for _, _, e in ordered
    }
    limit=min(_validity(c)[1] for c in [device]+chain)
    return merged,{'windows':len(ordered),'start':start.isoformat(),'end':end.isoformat(),
        'source_entries':source_entries,'duplicate_entries':source_entries-len(entries),
        'distinct_public_keys':len(public_keys),
        'gaps':gaps,'chain_expires':limit.isoformat(),
        'usable_through_at_most':min(end,limit).isoformat()}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    out=args.output.resolve()
    if '.state' not in out.parts:p.error('output must be private .state')
    m,report=merge(args.inputs)
    if report['gaps']:raise ValueError('coverage gaps; refusing deployable output')
    now=dt.datetime.now(dt.UTC)
    if not any(
        _validity(x509.load_pem_x509_certificate(e['pu'].encode()))[0] <= now <
        _validity(x509.load_pem_x509_certificate(e['pu'].encode()))[1]
        for e in m['certs']
    ):
        raise ValueError('no currently valid window')
    out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(m,f)
    print(json.dumps(report))


if __name__=='__main__':main()
