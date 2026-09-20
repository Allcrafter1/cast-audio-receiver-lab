# AirPlay 0.4.5 — Redmi reference test

2026-09-13: user stopped AirCast to avoid confusing bridge discovery and enabled
only AirPort Express Speaker + iOS Media Receiver in AirReceiver on a Redmi Note
11 Pro+5G. User already verified both with an iPad. The private test address is
intentionally omitted.

Discovery distinguishes two identities on the same phone:

- Teufel(Audio),91:AC:6D:79:34:61,RAOP6000,et=0,1,cn=0,1.
- Teufel,91:AC:6D:79:34:60,RAOP+AirPlay7000,AppleTV3,1-style advertisement.

First target is explicitly the6000 audio service. Do not merge these two logical
receivers merely because their IP matches. Do not disturb Samsung certificate
collection or infer native HomePod support from this legacy RAOP test.

## Two integration fixes

1. `--txt` consumes one argv entry. Previously each TXT pair was a separate
   positional argument; upstream rejected streaming audio supplied on argv.
   Join the pairs inside a single argument; never invoke a shell.
2. RAOP reads dedicated --et/--md/--am/--pk/--pw/--cn options. Merely populating
   the AirPlay2 --txt map did not supply these values. Omitted et selected the
   upstream0,4 default, which attempts MFi auth-setup. On this target the pinned
   upstream binary aborted with free(): invalid pointer, also in a minimal direct
   CLI invocation without Python. Explicit advertised et=0,1 establishes the
   connection. Forward advertised capabilities; do not patch/suppress allocator
   errors or claim the upstream invalid-free bug itself is fixed.

The inspected primary source for this branch is
[libraop raopcl_connect](https://github.com/philippe44/libraop/blob/81c2182649da8645ac2a58b78e9f370c79a4165b/src/raop_client.c).
No upstream binary/source rebuild, global install or phone change performed.

## Confirmed and pending

- All85 Python tests pass, including argv grouping and dedicated RAOP options.
- Direct backend -> FFmpeg -> cliairplay v0.5.3 -> Redmi6000: connected, audio
  buffered, started; decoder exited0. User CONFIRMED audible short660Hz test tone.
- Separate Vibecast adapter started as **Audio Lab AirPlay**, PID269116.
  Target config/log/PID/tone/private diagnostic files under remote
  `.state/airplay-redmi-20260913`; code uses `.state/airplay-0.4.4-staging` with
  the0.4.5 airplay.py fixes. Existing Audio Lab Laptop output unchanged.
- Full YouTube Music -> Cast -> AirPlay playback and controls remain the next
  user test. Direct tone does not establish EOF/queue, seek, metadata or feedback.
- iOS Media Receiver7000 has been discovered, not tested by our sender yet.
- Existing reconnect-on-load/seek and optimistic status/EOF limitations remain;
  do not describe the current adapter as gapless or completely synchronized.
