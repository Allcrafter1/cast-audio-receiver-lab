# Certificate-window pilot — 2026-09-13

## Follow-up: explicit UI Start and native observation

User correctly noted opening the activity is not the same as pressing START.
UI dump showed START even with port8009 listening. After an actual tap it showed
Ready To Cast. Pilot now locates START from current app UI bounds, taps it and
requires Ready To Cast before accepting a live endpoint, including restoration.
No fixed blind coordinates are used by the pilot.

Sep15 pilot with explicit Start still returns the exact Sep12–14 certificate.
A native observation repeat verifies libc time in the app itself is1789430407
(2026-09-15 00:00:07 UTC), so the process sees the changed wall clock.
Observed exported-call counts: X509_sign0, X509_gmtime_adj0, ASN1_TIME_set0,
ASN1_TIME_adj13, PEM_read_bio_X5096, d2i_X5099, SSL_CTX_use_certificate1.
These support a loaded-certificate path during the observed interval; they do
NOT prove no alternative generation path exists. Attachment occurs AFTER the
activity is launched, so earliest initialization may be missed. Frida spawn
instrumentation timed out and was abandoned; one attach raced PID creation,
fixed by bounded PID polling. All these failure paths restored time normally.

The exact live TLS cert was not found as raw DER/PEM in libAirReceiver.so.
A subsequent scan of865 installed APK entries found no exact DER, PEM, escaped
PEM or uninterrupted base64-DER match either. That is not proof it is absent in
other encoded/encrypted forms, app data or network-provided material.
No additional TLS window obtained, no manifest replacement, no multi-year sweep.
New private artifacts: pilot-ui-start-20260915.json and
pilot-native-button-retry-20260915.json (duplicate diagnostic material only).
Phone restored to actual date, automatic time/timezone and Ready To Cast.

## Outcome: no additional window obtained

User explicitly authorized collection on the rooted Galaxy A50. ADB, root,
loopback Frida and AirReceiver were checked. App was initially stopped and was
started through its existing SplashActivity; Cast listened on port8009.

Fresh baseline plus three pilots returned the SAME TLS certificate, device
certificate and intermediate chain as the installed current-both.json.

| Experiment | TLS notBefore | TLS notAfter | Additional coverage |
| --- | --- | --- | --- |
| Current-date baseline | 2026-09-12 00:00 UTC | 2026-09-14 00:00 UTC | none |
| Phone date 2026-09-14; app restart | same | same | none |
| Phone date 2026-09-15; app restart | same | same | none |
| Date 2026-09-15; isolated app_cast/config.json | same | same | none |

The last two pilots verified the actual phone epoch after app startup before
capture. Both failed the future-validity acceptance criterion, deliberately.
SHA1/SHA256 authentication signatures and key/certificate match were verified by
the existing capture helper, but signature validity does not imply date coverage.
The temporary config isolation left the original file restored (same size,
ownership and modification date). No cookies, accounts, licensing preferences,
bootloader settings, app-data reset or network-blocking changes were made.

Device certificate expires 2033-09-25 06:49:58 UTC; intermediate expires
2032-12-14 00:47:12 UTC. No claim of coverage to either date is justified.
Linux runtime and current-both.json were NOT replaced. Private captures remain
under remote .state/airreceiver-a50 with mode0600 and are diagnostic duplicates,
not deployable future coverage. No secret values are in this document.

## Clock safety

tools/capture_future_window.py runs one bounded experiment, not an unattended
multi-year sweep. It snapshots original epoch/monotonic uptime, auto_time,
auto_time_zone and timezone. It disables only auto_time, then restarts the app.
Finally it restores elapsed-adjusted original time and automatic setting and
restarts the app again. A detached phone-side watchdog provides a 90-second
emergency restore (and optional original config restoration) if the host fails.
Watchdog is stopped only after host restoration verification. Emergency USB-loss
behavior has not been fault-injected; do not claim this has been tested.

Final observed settings: auto_time=1, auto_time_zone=1, Europe/Berlin, correct
2026-09-13 UTC date. Original Cast config224244bytes dated2026-09-12 restored.
App running. Normal and failed-capture restoration paths exercised successfully.
Syntax checks pass. This utility is not yet a production batch collector.

## Next decision

Do NOT sweep years using the current method: it would just repeat the same
certificate. Need to establish where this app obtains/selects its TLS window:
another cache, embedded material, network-issued data, or a different time source.
Isolating one config file does not disprove all caching. No conclusion yet that
future collection is impossible, or that the old Shanocast method still works
unchanged on AirReceiver5.1.8. Keep the expiry milestone open before AirPlay.
