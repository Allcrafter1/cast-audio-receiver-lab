# Cast auth comparison, 2026-09-12

## Objective and current result

Investigate the immediate connection failure of the Linux receiver against
AirReceiver 5.1.7 on the user's Redmi. Speaker classification is confirmed fixed
in 0.4.2. Playback remains unconfirmed: Android reports socket status 2289 after
the device-auth exchange, before a YouTube app launch.

## Reproducible read-only comparison

`tools/probe_auth.py` now reports TLS negotiation, auth field presence,
intermediate certificate fingerprints and certificate signature OIDs. It
does not persist private keys, response signatures or certificate bodies.

| Property | AirReceiver 5.1.7 | Linux / public Shanocast bundle |
| --- | --- | --- |
| AuthResponse fields present | 1, 2, 3, 4, 6 | 1, 2, 3, 4, 6 |
| Cast response signature | RSA PKCS1v15 / SHA-256 | RSA PKCS1v15 / SHA-256 |
| Returned nonce / CRL | absent / absent | absent / absent |
| Certificate-only signature verifies | yes | yes |
| Fresh challenge-nonce signature verifies | no | no |
| Intermediate certificate SHA-256 | `529d9cd67fe5eb698e70dd26d7d8f12659f1e6e52348bf6a5cf716e13f410e73` | identical |
| Device certificate SHA-256 | `942f06e6c8ee6bbc60c51d49b91f9473629a7cde2648532bb6bb18a029c174d5` | `07df35a02b67245280b544b64a28a2d00fb8d543278718859673f51076a9b8fa` |
| TLS certificate self-signature | SHA-256 with RSA | SHA-1 with RSA |
| TLS certificate validity (UTC) | Sep 12–14, 2026 | Sep 12–14, 2026 |
| TLS protocol in diagnostic connection | TLS 1.3 | TLS 1.3 |
| Cipher in diagnostic connection | TLS_AES_256_GCM_SHA384 | identical |

This does not validate trust-chain acceptance, revocation policy, or the Android
sender's complete verification behavior. Matching field presence is not a claim
of byte-identical responses. The live sender itself requests SHA-256/PKCS1v15
with a 16-byte nonce; a SHA-1 request mismatch is not the observed cause.

The TLS certificate self-signature difference is a hypothesis, not an established
cause. Historical Chromium Cast code treats the TLS certificate principally as
signed data plus a validity window, rather than verifying it as an ordinary
trusted X.509 certificate; that code cannot establish current Android behavior:
https://chromium.googlesource.com/experimental/chromium/src/+/refs/tags/75.0.3770.70/components/cast_channel/cast_auth_util.cc

Re-signing the TLS certificate changes its DER bytes and therefore invalidates
the existing captured device-auth signature. Do not present a hash-algorithm
change alone as a compatible fix.

## APK inspection

Read-only symbol/string inspection of the installed ARM64 `libAirReceiver.so`
found Cast AuthChallenge/AuthResponse/DeviceAuthMessage protobuf names and
source-path markers for `jni/CastReceiver/in_process_receiver.cc`,
`standalone_cast_environment.cc`, and `cast_channel.pb.cpp`. The same native
library exports TLS/certificate routines including SSL_CTX_new and X509_sign.

This supports further inspection of the native receiver implementation. It does
not prove that Android services are unused or that the Windows build shares
identical code or credentials. No Windows binary/version was available for a
controlled comparison. No app modifications or root exploits were performed.

## Controlled second-installation comparison

The same AirReceiver 5.1.7 package was started on a second Android device and
probed independently. The Cast device-auth identity was byte-for-byte the same:

- device certificate SHA-256: `942f06e6c8ee6bbc60c51d49b91f9473629a7cde2648532bb6bb18a029c174d5`
- device SPKI SHA-256: `2fc69145f4b2d6f396a52f9acbe2221024b2fee1eb972b14989ca14acb1e1642`
- intermediate certificate SHA-256: `529d9cd67fe5eb698e70dd26d7d8f12659f1e6e52348bf6a5cf716e13f410e73`
- device-certificate subject: `CN=X752T FA8FCA659CB3`

The ARM64 native library hash was also identical on both installations. This is
strong evidence that AirReceiver distributes one shared, pre-issued Cast
identity (or a fixed identity pool), rather than requesting a new Google
certificate per installation. Google can still revoke such a shared identity,
which is why copying the same identity is inherently brittle.

The literal RSA private key found in `libAirReceiver.so` does **not** correspond
to the live Cast device certificate: its SPKI fingerprint is
`e14bc3d4793ca6f8be156fc07c4d41ef22faa082fb88308f3d8426daa5a39ede`. The
current AirReceiver Cast certificate and TLS certificate are also absent as
literal DER/PEM blobs in the inspected APK/native library. The embedded key is
therefore a separate Cast/TLS/setup credential, not the key needed to reproduce
the Google-issued AuthResponse.

The app does use encrypted SharedPreferences derived from a fixed 20-byte
application constant, package name, and Android ID for licensing/configuration.
That mechanism is not the source of the observed Cast identity: the identity is
identical across two devices and the exact certificate bytes are not present in
the package. Remaining possibilities are an obfuscated/split credential, a
runtime-provided credential, or a credential stored in native/app-private data.

The live protocol behavior matches the older AirReceiver reverse-engineering
report: the `AuthResponse` contains fields `[1, 2, 3, 4, 6]`, omits field 5
(`sender_nonce`), and its 256-byte signature verifies over the TLS peer
certificate alone, not over `sender_nonce || peer_certificate`. The TLS peer
certificate is a self-signed 48-hour certificate generated for the current
date. This is a replay-oriented compatibility path, not a normal per-challenge
signature implementation.

The strongest provenance hypothesis is therefore a reused Google Cast
credential bundle from the Eureka/Google-TV generation. The observed device
certificate is issued by `Eureka Gen1 ICA`, has the Google-TV subject and the
2013--2033 validity window. A public 2023 AirReceiver analysis observed the
same Eureka Gen1 chain and described a fixed peer key plus precomputed
signatures, likely sourced from a rooted Chromecast donor. That is strong
corroboration, but it does not prove whether the current bundle came directly
from a rooted first-generation Chromecast, an OEM/licensed partner, or a
credential pool acquired by the vendor. It also does not imply that the
certificate is specifically from an Android TV box.

## Sender diagnostics

The temporary Android log-tag overrides were restored to their original empty
values. The extra logging still exposed only status 2289. The separate null-nonce
warning from discovery is not sufficient to explain the authenticated connection
failure. A concurrent GMS connection to AirReceiver reported connected, but this
was not a controlled full YouTube Music playback test.

Direct integer-constant scanning found no 2289 match in the three DEX files of
DynamiteModulesC. A scan of the installed GMS base APK follows; a missing constant
would not exclude computed codes, switch tables or native code.

## Root cause

The current Cast CRL endpoint was downloaded locally on 2026-09-12. Its opaque
protobuf envelope contains the exact 32-byte SHA-256 SPKI hash of the Shanocast
device certificate (60479cb5...d4c46b9). The AirReceiver device certificate's
SPKI hash (2fc69145...b1e1642) was absent. This matches the observed behavior:
AirReceiver proceeds, while the Linux receiver is closed immediately after
auth. The public Shanocast credential is revoked.

tools/check_cast_crl.py now performs this check without printing certificate
bodies or private keys. There is no local cryptographic change that can repair
a revoked manufacturing identity. A working native Linux Cast receiver needs a
new, non-revoked Google-issued device credential set; the existing peer
signatures cannot be transformed into one.
