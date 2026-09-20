# AirPlay bridge 0.4.4 — first wiring, not hardware acceptance

The active Vibecast external-player adapter now accepts `--backend airplay`.
It reuses the existing AirPlayAudioBackend: checked media URL -> FFmpeg PCM ->
cliairplay. No new protocol implementation, dependency or Cast frontend change.
The known-working laptop mpv output stays the live default during collection.

Verification: 84 Python tests passed locally; nine new bridge/lifecycle tests
also passed on USBIP server in `.state/airplay-0.4.4-staging`. Live source/output
was not replaced. The staged package can be selected with
`PYTHONPATH=.state/airplay-0.4.4-staging/src .venv/bin/python -m cast_audio_lab.vibecast_player`.

The agreed unified upstream is [music-assistant/airplay-cli](https://github.com/music-assistant/airplay-cli),
not the archived older repository named cliairplay. Versionv0.5.3 Linux x86_64
downloaded to `.state/airplay-tools/v0.5.3/cliairplay-linux-x86_64` on USBIP server.
Binary and SHA256SUMS verified against published release digests, license/notices
retained; `--check` returned `cliairplay v0.5.3 check`. No global installation or
capability/privilege changes. Reproducible pin: config/cliairplay-linux-x86_64.lock.json.
The [upstream command contract](https://github.com/music-assistant/airplay-cli/blob/v0.5.3/README.md)
was reviewed; actual device interactions remain untested.

## Explicit target configuration

Save the selected receiver's discovered properties in a private JSON file:

```json
{
  "host": "192.0.2.20",
  "port": 5000,
  "protocol": "raop",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "name": "AV Receiver",
  "txt": {}
}
```

This is an example, not a discovered/live device. Use the actual advertised port,
device ID and TXT properties; HomePod setup must not blindly reuse legacy RAOP
settings. Optional fields: credentials, legacy_secret, password and interface.
Keep secrets out of Git, use file permissions0600. The downstream cliairplay CLI
still receives credentials in process arguments; this is not protection against
other processes with permission to inspect them.

With the existing Vibecast frontend running, start a separate explicit route:

```bash
cast-vibecast-player --bridge ws://127.0.0.1:8010/player \
  --backend airplay --airplay-config /private/path/target.json \
  --name "Living Room Audio" --cliairplay /path/to/cliairplay
```

No target is automatically imported or played. Cast identity derives from target
device_id, independently of display name, or from explicit `--player-id`.
This allows renaming without creating a different receiver identity. The existing
mpv/command defaults and IDs are unchanged. Latency option remains600ms by default;
this setting is NOT a measured audible latency or a target-device guarantee.

## Implemented and tested

- Route/config validation, explicit target selection and rename-stable identity.
- Reuse existing metadata/play/pause/seek/volume backend interface.
- Failed/cancelled partial start reaps the started child and removes FIFO/tempdir.
- Startup RuntimeError becomes a bridge error, rather than escaping the command
  handler; a subsequent load can be accepted.
- Muted state respected when starting cliairplay; backend shutdown on adapter exit.
- Pairing fields omitted from target repr; raw decoder/CLI diagnostics not logged
  because they can contain signed media URLs or pairing material.
- Unit tests include real harmless local subprocess cleanup, not real AirPlay.

## Still required before claiming AirPlay support works end-to-end

1. Binary provisioning/self-test is complete for Linux x86_64 only. Validate
   actual setup/status/event behavior against a selected receiver; a binary
   self-test is not a successful streaming test. FFmpeg exists on USBIP server.
2. Select a real Yamaha/other RAOP receiver and test audible playback, controls,
   receiver-side feedback, connection failure/retry and teardown.
3. Verify decoder EOF versus drained/audible EOF, status/position feedback,
   automatic next title, signed/DASH/HLS input compatibility and metadata/artwork.
   The old backend still uses optimistic state/timing and reconnects on seek/load;
   this wiring step does not establish gaplessness or accurate AirPlay timing.
4. HomePod/AirPlay2 pairing/reconnect and latency measurements separately.

No claim that a successful adapter unit test validates the cliairplay protocol or
YouTube Music -> physical AirPlay playback. Certificate collection is independent
and must not be interrupted to perform these tests.
