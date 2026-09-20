# Galaxy A50 runtime test, 2026-09-12

## Confirmed environment

The user's SM-A505FN runs Android 11, Magisk root, and AirReceiver 5.1.8
(2020164766), with native ARM64 code. Its private test address is intentionally
omitted.
ADB and root access work. The live Cast identity and current TLS certificate
match the previously observed 5.1.7 installations.

Frida 17.18.0 was installed for the investigation. Its Android server listens
on loopback and is accessed through USB. The first server launch accidentally
ran as shell due to ADB command quoting; it was stopped and relaunched under
root. Native process attachment then worked. No bootloader operation, clock
change, or system-wide SELinux disabling was performed.

## Capture and implementation

`tools/capture_airreceiver_window.py` attaches to an explicitly selected
AirReceiver PID. It observes `SSL_new` in `libAirReceiver.so`, serializes the
active TLS certificate/key, and matches these against a fresh Cast connection.
It captures and verifies SHA-256 and SHA-1 responses separately; it never
substitutes a SHA-256 signature into the SHA-1 slot.

Both response signatures verify over the TLS certificate alone. The returned
nonce is absent. The TLS private key matches that certificate. No Google
device private key was extracted, and possession of that key by AirReceiver
has not been established.

The generated manifest is exclusive-created with mode 0600 under `.state`.
Private values are not printed. The remote deployment uses
`.state/airreceiver-a50/current-both.json`. A previous SHA-256-only exploratory
capture remains in `current.json` and is not the deployed manifest.

The existing patched Vibecast frontend was restarted with the new manifest,
retaining its installation identity and audio capabilities. The mpv-backed
player was also restarted as `Audio Lab Laptop`. It registered successfully;
the current Cast endpoint uses the Linux test host and a dynamic port.

A fresh Linux endpoint probe returned the same TLS/device certificates and a
valid TLS-only SHA-256 signature. This verifies transfer of the authentication
bundle and the Linux response; it does not alone prove stock YouTube Music
acceptance or successful audio playback. A user playback test was requested.

## Limits and next step

This captures only 2026-09-12 through 2026-09-14 UTC. No multi-year collection
has been run. Test actual sender playback before automating phone time changes.
The leaf expires in September 2033, but its observed intermediate expires
2032-12-14; leaf expiry alone cannot define a usable collection horizon.

The approach is now demonstrated for one current window. It removes the need
to locate an embedded Google signing key or acquire another Cast device.
The next steps are playback verification, then controlled future-window
collection with clock restoration and rotation tests.
