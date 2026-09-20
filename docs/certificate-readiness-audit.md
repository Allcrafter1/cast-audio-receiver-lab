# Reference receiver readiness and inventory audit — 2026-09-13

The previous run captured the March21–23,2028 certificate successfully, but failed
when restarting the reference app at current time. Its final clock-restored marker
was printed only after that restart, obscuring the distinction. The current phone
clock matched Linux; the phone was subsequently observed at its secure lock screen.
No secure lock was bypassed: the user unlocked the Samsung A50, after which the app
again displayed Ready To Cast. Locking plausibly explains readiness failures;
the old log cannot prove that every earlier startup failure had that cause.

## Certificate uniqueness

- Original checkpoint:278 entries,278 distinct certificate SHA-256 fingerprints,
  278 distinct two-day windows and one shared public TLS key.
- Repeated March21 capture: byte-identical certificate to the earlier capture for
  the same date, with valid key/signature checks. This is repeatable per-date
  selection, not proof that the app generates new key material on each launch.
- Resumed pilot:281 distinct certificates, no duplicates or gaps, coverage from
  September12,2026 through March27,2028 exclusive. New dates extend coverage;
  repeated extraction of a single certificate cannot satisfy this test.
- Offline capture verified no Wi-Fi/default route and used USB; original online
  settings and time were restored. The reference phone being online between
  pilots does not mean these captures required an online time service.
- Cryptographic consistency and date coverage do not establish future sender
  acceptance, revocation status or distribution rights.

## Reliability changes

Bounded UI readiness retry; tap START at most once per launch. Clock restoration
and current-date receiver readiness are separate log events. Collector keeps an
already-unlocked externally powered phone awake on USB, restores its prior setting
on normal/error exit, and preserves a concurrent user setting change. This does
not unlock the phone. If the process is forcibly killed, check/restore that setting
manually; stop normally via its STOP file. Existing per-pilot90s phone-local
clock/network watchdog, temperature/power guards and fail-closed behavior remain.

Original failed artifacts retained. New job directory:
`.state/airreceiver-a50/collection-resume-20260913` on the Linux test machine.
Seed includes only verified inventory plus the successfully repeated capture.
Two-window pilot exited cleanly and restored stay-awake from2 to0. Background
continuation targets December6,2030; this is a target, not completed coverage.

New merge reports explicitly show input count, duplicate count and distinct public
key count. Checkpoint comparisons ignore input-level diagnostic counts because
deduplicated checkpoints differ from potentially overlapping source collections.
Private bundles remain outside Git. Runtime deployment is a separate milestone;
this investigation did not replace the active six-window bundle.
