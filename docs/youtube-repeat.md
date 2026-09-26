# YouTube Music repeat — dev19

The previous frontend did not advertise `mlm` (multi-state loop mode), ignored
`setLoopMode`, and always advanced at natural EOF. This accounts for the disabled
repeat control and the missing playback behavior.

Protocol evidence checked on 2026-09-26 in Google's public sender code:

- [YouTube Music sender](https://music.youtube.com/s/1dea707a/music_polymer_inlined_html.js):
  `MULTISTATE_LOOP_MODE` maps to `mlm`; `setLoopMode` carries `loopMode`;
  `onLoopModeChanged` reports it. Values are `LOOP_MODE_OFF`, `LOOP_MODE_ONE`,
  and `LOOP_MODE_ALL`. Initial `setPlaylist` can include `loopMode`.
- [YouTube remote module](https://www.youtube.com/s/player/7460dd14/player_ias.vflset/de_DE/remote.js):
  receiver capability `mlm` enables the multi-state loop control.

The mode belongs to each Lounge session. Unknown values are ignored. Mode
changes do not change playback position or start a new load. Now-playing
responses include a second BrowserChannel message reporting the mode, including
on reconnect; message offsets account for both messages.

At natural EOF, One selects the same queue slot at time zero. All selects the
first slot after the last. Manual Next ignores One and wraps with All. Off keeps
the existing queue-extension behavior. The ordinary selection/resolution path
keeps playback and Lounge indices synchronized and retains cancellation. This
does not add generic Default Media Receiver queue/repeat support.

Frontend source: `1bc5f2edb8c4566ebeeef8d48574e174c849175d` on the maintained
`Allcrafter1/vibecast` branch. The product container and CI pin this exact commit.

Automated checks cover capability advertisement, valid/invalid commands, initial
mode, feedback, empty queues, end-of-queue behavior, and an asynchronous EOF
followed by a duplicate EOF and manual Next. Rust: 149 passed across seven crates,
one explicit live resolver test ignored. Python: 263 tests completed successfully,
10 environment skips. Live acceptance remains pending.

Manual acceptance on the owner's selected test host:

1. Disconnect and reconnect YouTube Music so it receives the new capabilities.
2. Cycle Repeat through Off, All and One; verify the icon stays in the selected mode.
3. In One, seek near the end and verify the same title restarts once.
4. Press Next in One and verify it advances.
5. With a short known queue, verify All wraps from its last title to the first.
6. Turn Repeat off and check normal queue progression, pause, seek and disconnect.

Build/test, deployment and owner confirmation are separate milestones; no
physical acceptance is claimed until these steps have been observed.
