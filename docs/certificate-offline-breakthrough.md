# Offline certificate generation — 2026-09-13

## Latest: live collection and generation boundary

User confirmed actual YouTube Music connection/audio. Six-window contiguous bundle
through2026-09-24 deployed at12:52UTC; receiverPID250763/playerPID250768, Cast40679.
New local fresh challenge verified. Original manifests kept for rollback.

Independent collectorPID250663 continues in private job directory
`.state/airreceiver-a50/collection-20260913` on USBIP server. It resumes validated
receipts, restores phone after each capture and checkpoints every16 windows.
collection-run-01.log reports progress; STOP file requests safe exit after current
restore. Do not overlap phone experiments with it. No automatic final deployment.

Horizon narrowed: Dec4–6,2030 succeeds, Dec6 and later sampled dates fail before
TLS-context installation. Jan/Jul/Oct/Nov2030 all succeed. The1800-day span from
Jan1,2026 is consistent with900 prepared two-day windows, but does not prove the
internal storage format or online refresh strategy. APK signature scans (raw,
base64, hex) returned no matches; bounded heap scan found current signatures only.
No Google device private key extracted. Sequential capture is the working path.

14 synthetic tests passed; live initial batch and resumption both succeeded.
Full coverage to2030 is still IN PROGRESS, not complete or guaranteed. Phone USB
power verified,100% battery and35.8C before long run. Collector stops before a new
pilot without external power, below20% battery or at/above42C, as well as on any
capture/validation failure. Time/network watchdog remains independent of host.

## Outcome and passed acceptance gate

Offline generation works, but uses a DIFFERENT device identity from the working
online AirReceiver response. Successful cryptographic checks do not establish
Google sender acceptance/revocation status. The user has now confirmed successful
YouTube Music connection and playback with the deployed offline identity. This
passes today's acceptance gate, not a guarantee about future validity/revocation.

Wi-Fi disabled and mobile-data disable requested; capture performed through an
ephemeral USB ADB port forward. Later pilots also check all policy-routing tables
for remaining unicast default routes, not merely Android's usually empty main
table. Phone clock/settings/network are restored after each run.

## Evidence

- Offline Sep15: new TLS window Sep14–16,734-byte DER; native X509_sign observed.
- Offline current date: cached AIRSCREEN material still wins.
- Isolating app_cast/config.json does not remove that material.
- SoftMediaPairedData.xml contains cks2. Temporarily omit ONLY this entry while
  offline: a new current Sep12–14 certificate appears with the offline identity.
  Original XML, other entries, ownership and settings are restored afterwards.
- Jan15,2027 offline: Jan14–16 certificate successfully captured and signatures
  verified. This is an isolated future sample, NOT continuous coverage to2027.
- Dec13,2032: UI ready but TLS handshake failed twice. The first helper stderr
  was not retained; retry preserved it privately. No2032 window acquired and no
  exact upper generation limit established. Do not infer chain expiry caused it.
- Online device leaf expires2033; offline leaf expires2034. Both use the same
  intermediate expiring2032-12-14 00:47:12 UTC.

cks2 behavior strongly identifies a cache selection issue. These tests do not
establish the online refresh endpoint or prove an online time service exists.
No Google device private key was exported. The existing helper extracts active
TLS keys and obtains the application's responses, verifying both signature hashes.

## Linux test deployment

Private offline-current-next.json contains two contiguous windows Sep12–16.
tools/merge_certificate_windows.py verifies matching device/chain identity,
device->intermediate signatures, TLS key matches and SHA1/SHA256 response signatures.
It rejects mixed identities, gaps for deployable output, and missing current window.
Five synthetic tests passed (adjacency/deduplication, gap, mixed identity, bad
signature, wrong TLS key). It is not a Google trust/revocation validator.

Controls-17 Linux receiver now uses this test manifest, receiverPID248477,
playerPID248482, Cast port41965. Local fresh challenge verifies the live signature.
Original current-both.json remains untouched. Rollback: restart receiver/player
with original environment and same arguments, changing --certs back to
.state/airreceiver-a50/current-both.json. No source/binary change for deployment.

User was asked for YouTube Music connection + audible playback with normal phone
clock. User confirmed connection and playback work as before; collection can proceed.

## Artifacts and scope

All captured material, preference-test files and failure diagnostics remain under
ignored remote .state with mode0600; phone temporary preference artifacts remain
private to root/app storage. They must not enter published source/snapshots.
Original phone preference backups are restored; generated diagnostic copies kept
for recovery. No app reset, account changes or licensing-preference modification.
App left Ready To Cast with automatic time/timezone, Wi-Fi/mobile data restored.

Pilot utility now supports offline USB collection and optional cks2 omission with
phone-local watchdog restoration. It remains a single-window pilot, not a proven
unattended multi-year collector. Process/USB-loss fault injection not yet tested.
