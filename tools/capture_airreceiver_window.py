#!/usr/bin/env python3
"""Capture one TLS window from the user's running AirReceiver test installation.

Requires an explicitly selected rooted Android device and Frida server. Only
the active TLS key is exported; no Google device private key is requested.
Output is private local state, never printed. The phone clock is not changed.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import ssl
import threading

import frida
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from research.legacy_python_receiver.legacy_cast_receiver.auth import DEVICE_AUTH_NAMESPACE
from research.legacy_python_receiver.legacy_cast_receiver.wire import (CastMessage, PayloadType, iter_protobuf_fields,
                                 read_cast_message, write_cast_message,
                                 encode_length_delimited_field, encode_varint_field)
from probe_auth import analyze_response

AGENT = r"""
const m = Process.getModuleByName('libAirReceiver.so');
function native(name, result, args) {
  return new NativeFunction(m.getExportByName(name), result, args);
}
const key = native('SSL_get_privatekey', 'pointer', ['pointer']);
const cert = native('SSL_get_certificate', 'pointer', ['pointer']);
const keyDER = native('i2d_PrivateKey', 'int', ['pointer', 'pointer']);
const certDER = native('i2d_X509', 'int', ['pointer', 'pointer']);
function encode(fn, value) {
  const length = fn(value, ptr(0));
  if (length <= 0 || length > 65536) throw new Error('invalid DER length');
  const buffer = Memory.alloc(length);
  const cursor = Memory.alloc(Process.pointerSize);
  cursor.writePointer(buffer);
  if (fn(value, cursor) !== length) throw new Error('DER encode failed');
  return buffer.readByteArray(length);
}
const seen = new Set();
Interceptor.attach(m.getExportByName('SSL_new'), {
  onLeave(ssl) {
    if (ssl.isNull()) return;
    const k = key(ssl), c = cert(ssl);
    if (k.isNull() || c.isNull()) return;
    const id = k.toString() + ':' + c.toString();
    if (seen.has(id)) return;
    seen.add(id);
    send({kind:'cert', id:id}, encode(certDER, c));
    send({kind:'key', id:id}, encode(keyDER, k));
  }
});
"""


async def capture(host: str, port: int, hash_algorithm: int = 1):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=ctx), 10)
    try:
        der = writer.get_extra_info('ssl_object').getpeercert(binary_form=True)
        nonce = os.urandom(16)
        await write_cast_message(writer, CastMessage(
            source_id='sender-0', destination_id='receiver-0',
            namespace=DEVICE_AUTH_NAMESPACE, payload_type=PayloadType.BINARY,
            payload_binary=encode_length_delimited_field(1,
                encode_varint_field(1, 1) + encode_length_delimited_field(2, nonce)
                + encode_varint_field(3, hash_algorithm))))
        reply = await asyncio.wait_for(read_cast_message(reader), 10)
        report = analyze_response(reply, nonce, der)
        if not report.get('signature_valid_for_tls_certificate_only'):
            raise ValueError('response is not a valid TLS-only capture')
        if report.get('hash_algorithm') != ('SHA256' if hash_algorithm else 'SHA1'):
            raise ValueError('receiver returned an unexpected signature hash')
        outer = {n: v for n, _, v in iter_protobuf_fields(reply.payload_binary)}
        fields = {}
        for n, _, value in iter_protobuf_fields(outer[2]):
            fields.setdefault(n, []).append(value)
        return der, fields, report
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), 3)
        except (TimeoutError, OSError):
            pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', required=True)
    p.add_argument('--pid', type=int, required=True)
    p.add_argument('--host', required=True)
    p.add_argument('--port', type=int, default=8009)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    if '.state' not in output.parts:
        p.error('output must be in an ignored .state directory')
    records = {}
    lock = threading.Lock()
    errors = []

    def receive(message, data):
        with lock:
            if message['type'] == 'error':
                errors.append('native instrumentation failed')
            elif message['type'] == 'send' and data:
                payload = message['payload']
                records.setdefault(payload['id'], {})[payload['kind']] = data

    device = frida.get_device(args.serial, timeout=5)
    session = device.attach(args.pid)
    try:
        script = session.create_script(AGENT)
        script.on('message', receive)
        script.load()
        peer, fields, report = asyncio.run(capture(args.host, args.port))
        peer_sha1, fields_sha1, _ = asyncio.run(capture(args.host, args.port, 0))
        if peer_sha1 != peer or fields_sha1.get(2) != fields.get(2):
            raise ValueError('identity rotated during capture; retry')
        with lock:
            matches = [r['key'] for r in records.values()
                       if r.get('cert') == peer and 'key' in r]
        if errors or not matches:
            raise RuntimeError('no matching TLS key observed; no bundle written')
        key = serialization.load_der_private_key(matches[0], password=None)
        cert = x509.load_der_x509_certificate(peer)
        fmt = serialization.PublicFormat.SubjectPublicKeyInfo
        enc = serialization.Encoding.DER
        if key.public_key().public_bytes(enc, fmt) != cert.public_key().public_bytes(enc, fmt):
            raise ValueError('TLS certificate and key do not match')
        def pem(der):
            return x509.load_der_x509_certificate(der).public_bytes(
                serialization.Encoding.PEM).decode('ascii')
        manifest = {'cpu': pem(fields[2][0]),
                    'ica': ''.join(pem(v) for v in fields.get(3, [])),
                    'certs': [{'pu': pem(peer), 'pr': key.private_bytes(
                        serialization.Encoding.PEM,
                        serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption()).decode('ascii'),
                        'sig_sha1': base64.b64encode(fields_sha1[1][0]).decode('ascii'),
                        'sig_sha256': base64.b64encode(fields[1][0]).decode('ascii')}]}
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
            json.dump(manifest, f)
        print(json.dumps({'output': str(output), 'tls_key_matches': True,
                          'auth_signature_verified': True,
                          'tls_certificate': report['tls_certificate']}))
    finally:
        session.detach()


if __name__ == '__main__':
    main()
