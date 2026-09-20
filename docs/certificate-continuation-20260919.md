# Certificate collection continuation — 2026-09-19

User explicitly requested resuming the documented collection on the rooted A50,
with a detached background process so unrelated development can continue.
No collector was running. USB/ADB/root/instrumentation access were checked;
phone was externally powered,100% charged and28.9°C. Automatic time was on and
USB stay-awake was initially0. The app was available without bypassing a lock.

The deployed seed was independently revalidated:479 distinct certificates,
no duplicates or gaps, covering2026-09-12 through2029-04-27 exclusive. One shared
public TLS key is expected; certificate/window uniqueness is checked separately.
The tools matched the previously reviewed local hashes; no capture mechanism
change or phone software update was necessary.

## Recovery and private job

The old April27 attempt failed on UI readiness. Its evidence remains untouched.
A new job uses the verified seed under
`.state/airreceiver-a50/collection-resume-20260919` on the Linux test host.
Two new windows (April27–29 and April29–May1) passed capture, signature/key/chain,
coverage and restoration checks. This extends validated coverage to May1,2029;
it does not establish completion to2030 or future Google acceptance.

The requested continuation stops at2030-12-06 exclusive, the previously observed
generation boundary, with a maximum320 further windows. Every pilot temporarily
goes offline over USB and restores the prior clock/network settings. Retain the
per-phone lock,90-second phone-local recovery watchdog,180-second pilot timeout,
power/temperature guards and first-failure stop. No automatic retry loop hides
failed windows. No active Linux receiver bundle is changed by collection.

## Background monitoring and stopping

Started at19:25UTC: supervisor371146, collector371147. Process inspection
confirmed a separate session and supervisor parent PID1. The initial handoff
is resume validation, not a claim of additional completed background windows.
The pilot completed with481 distinct certificates/no gaps and restored automatic
time/stay-awake to1/0 before this launch.

Private job records: `supervisor-pid.json`, `background-pid.json`,
`background-run.log`, and `background-result.json` on exit. A PID alone does not
prove progress: check its command identity and new `window-*.ok.json` receipts.
Receipts are written only after successful verification and restoration.
Immutable `bundle-NNNN.json` checkpoints are created every16 additions and on
normal completion; do not confuse log progress with the deployed bundle.

To stop safely, create an empty `STOP` file in this exact job directory. The
collector finishes restoration of the current pilot before stopping. Do not run
another phone/time experiment while it owns the device. A forced host-process
kill requires checking the phone watchdog and USB stay-awake setting afterward.

On exit, inspect the result/log, revalidate the final merged bundle, verify no
duplicates or gaps and retain the old runtime bundle before any separate
deployment. Do not publish private bundle material, raw capture diagnostics,
preferences or keys. Long validity does not guarantee sender acceptance.

## Follow-up result at 22:40 CEST

The detached process is no longer running. It promoted 30 additional windows
after the two-window pilot: the merged checkpoint contains 511 distinct
certificates, no duplicates and no gaps, with verified coverage ending at
2029-06-30T00:00:00Z. The next future certificate was captured, but its pilot
failed the mandatory restoration check because AirReceiver did not return to
`Ready To Cast` at the real date within the bounded wait. The collector stopped
on that first failure and did not create an `.ok` receipt for the attempt.

Before resuming, unlock the owned phone and place AirReceiver in its visible
ready state. Then re-run the documented resume path; do not manually promote the
unvalidated attempt or remove the current-date readiness check. No captured
bundle was activated in the receiver by this run.

## Second recovery at 23:44 CEST

The user unlocked the owned A50. AirReceiver was visibly `Ready To Cast`, the
phone was USB-powered at 100% and 29.4 C, and automatic time/timezone and USB
stay-awake were at their restored values `1/1/0`. The failed June30 artifacts
remain untouched in the first job.

A new private continuation directory
`.state/airreceiver-a50/collection-resume-20260919-2` uses the revalidated
511-window `bundle-0032.json` as its seed. A bounded one-window foreground pilot
passed capture, signature/key/chain, contiguous coverage and full restoration,
extending verified coverage to 2029-07-02. The detached continuation then
successfully promoted its first additional window, giving 513 distinct,
gap-free certificates through 2029-07-04 exclusive. No bundle was activated in
the running receiver.

The detached supervisor is PID375472 and collector PID375474, in session375472;
the supervisor was verified reparented to PID1. Status files are
`supervisor-pid-2.json`, `background-pid-2.json`, `background-run-2.log` and
`background-result-2.json` on exit. The target remains 2030-12-06 exclusive,
with first-failure stop and the unchanged phone-local recovery safeguards.

At the 16-addition checkpoint, `bundle-0016.json` contained 527 distinct
certificates with zero duplicates or gaps and coverage through 2029-08-01
exclusive. An identical private backup was copied to this workstation at
`.state/airreceiver-a50/laptop-backup-20260919/bundle-through-2029-08-01.json`.
Its SHA-256 is
`736ba1f62a677f996dd6705f24d8d914dedf5e4bedc7519adc0ef41caa1dc6e7`;
the hash matches the remote checkpoint and a local cryptographic merge check
confirmed all 527 windows, the shared key/chain, and gap-free coverage. From
this checkpoint 246 two-day windows remain to the requested 2030-12-06 end.

## Read-only progress check — 2026-09-20

A later detached continuation is active in private job
`collection-resume-20260920-3`; collector PID 379493 was still owned by its
detached supervisor at the read-only check. The newest immutable log checkpoint
reports 704 distinct windows, no duplicates or gaps, and verified coverage
through 2030-07-21 exclusive. Subsequent per-window success records were visible
through 2030-08-22, but they are not promoted here as the documented immutable
checkpoint until the next bundle/receipt is inspected. The target remains
2030-12-06. No runtime bundle was changed, and the collector was not restarted,
stopped or otherwise modified during this check.

## Final collection result at 01:51 CEST on 2026-09-20

The resumed run with temporary Samsung pocket-protection suppression and the
`uiautomator`-137 retry completed normally with return code 0. Its final
checkpoint contains 773 distinct certificates, no duplicates and no gaps, with
coverage from 2026-09-12 through 2030-12-06 exclusive. The phone restored
`screen_off_pocket=1` and `stay_on_while_plugged_in=0`; no process remains active
and no runtime bundle was activated.

The final checkpoint was copied to the workstation as
`.state/airreceiver-a50/laptop-backup-20260919/bundle-through-2030-12-06.json`
and locally revalidated. Its SHA-256 is
`97ac49c254dfdd9ef4a140481ffbff9d62d1bad9aa3909f5e06ea211691af7ef`.

## Home Assistant deployment verification — 2026-09-20

The final checkpoint was independently merged again: 773 source entries became
773 distinct windows with no duplicates or gaps, one expected public key,
coverage from 2026-09-12 through 2030-12-06 and intermediate-chain expiry on
2032-12-14. The reconstructed file matched the checkpoint byte-for-byte.

The prior Home Assistant `/share` input was preserved under a dated rollback
name. The final checkpoint was then installed with mode 0600 and the App was
restarted. Its root bootstrap imported the bundle into private unprivileged
state; `/health` returned ready, the persistent route remained running and the
Cast frontend advertised it again. The bundle remains outside the source tree
and image. This validates local integrity and runtime loading, not future Google
acceptance, non-revocation or redistribution rights.
