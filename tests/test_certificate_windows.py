import base64
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

spec=importlib.util.spec_from_file_location('window_merge',Path(__file__).parents[1]/'tools/merge_certificate_windows.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WindowMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.device_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.peer_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.ca=cls.certificate('CA',cls.ca_key,'CA',cls.ca_key,1,3650)
        cls.device=cls.certificate('Device',cls.device_key,'CA',cls.ca_key,1,3650)

    @staticmethod
    def certificate(name,key,issuer,signer,start,end):
        origin=dt.datetime(2026,1,1,tzinfo=dt.UTC)
        return (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)]))
            .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,issuer)]))
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(origin+dt.timedelta(days=start))
            .not_valid_after(origin+dt.timedelta(days=end)).sign(signer,hashes.SHA256()))

    def manifest(self,start,end):
        c=self.certificate('Peer',self.peer_key,'Peer',self.peer_key,start,end)
        der=c.public_bytes(serialization.Encoding.DER)
        pem=lambda c:c.public_bytes(serialization.Encoding.PEM).decode()
        e={'pu':pem(c),'pr':self.peer_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()}
        for name,alg in [('sig_sha1',hashes.SHA1()),('sig_sha256',hashes.SHA256())]:
            e[name]=base64.b64encode(self.device_key.sign(der,padding.PKCS1v15(),alg)).decode()
        return {'cpu':pem(self.device),'ica':pem(self.ca),'certs':[e]}

    def merge(self,*manifests):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for i,m in enumerate(manifests):
                p=Path(tmp)/f'{i}.json'; p.write_text(json.dumps(m)); paths.append(p)
            return module.merge(paths)

    def test_adjacent_windows_deduplicate_and_validate(self):
        a=self.manifest(1,3); b=self.manifest(3,5)
        merged,report=self.merge(a,b,a)
        self.assertEqual(len(merged['certs']),2)
        self.assertEqual(report['gaps'],[])
        self.assertEqual(report['source_entries'],3)
        self.assertEqual(report['duplicate_entries'],1)
        self.assertEqual(report['distinct_public_keys'],1)

    def test_gap_is_reported(self):
        _,report=self.merge(self.manifest(1,3),self.manifest(4,6))
        self.assertEqual(len(report['gaps']),1)

    def test_different_identity_is_rejected(self):
        a=self.manifest(1,3); b=self.manifest(3,5)
        b['cpu']=b['ica']
        with self.assertRaisesRegex(ValueError,'different device'):self.merge(a,b)

    def test_bad_signature_is_rejected(self):
        m=self.manifest(1,3); m['certs'][0]['sig_sha256']=base64.b64encode(b'bad').decode()
        with self.assertRaises(InvalidSignature):self.merge(m)

    def test_key_mismatch_is_rejected(self):
        m=self.manifest(1,3)
        m['certs'][0]['pr']=self.ca_key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
        with self.assertRaisesRegex(ValueError,'TLS key'):self.merge(m)
