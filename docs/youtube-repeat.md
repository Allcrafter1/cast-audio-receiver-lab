# YouTube Music repeat — dev19

## Repeat-one stream preparation

Follow-up frontend `35ffe1b5ceca4962903a4f217cb18ef7d3dfb071` retains the current
resolved stream description in memory. A distinct repeat-one EOF command reuses
that description at position zero with autoplay, without another metadata/yt-dlp
resolution. The already prepared next title stays available for manual Next.

This adds no decoder, resolver process, audio-file cache or dependency. The
existing ten-minute freshness rule applies from the original resolution time,
including media obtained through prefetch; repeating never renews that age.
Expired entries and changed codec preferences use the normal cancellable
resolver. Stop or another load clears the old current entry. The decoder still
opens the stream and output buffering still applies; this is not gapless playback.

The YouTube suite passes 51 tests (one explicit live probe ignored), including
repeated reuse without a new resolver request, preserving a pending Next,
freshness, codec/title mismatch and Stop. Follow-up live acceptance is pending.

HA distribution status: dev19 release notes exist in both changelogs, but the
versioned container image has not yet been published. The version field alone
does not establish that an App update can download and install the new version.

## Original repeat functionality and joint test

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

Initial frontend source: `1bc5f2edb8c4566ebeeef8d48574e174c849175d` on the maintained
`Allcrafter1/vibecast` branch; the product now pins the preparation follow-up above.

Automated checks cover capability advertisement, valid/invalid commands, initial
mode, feedback, empty queues, end-of-queue behavior, and an asynchronous EOF
followed by a duplicate EOF and manual Next. Rust: 149 passed across seven crates,
one explicit live resolver test ignored. Python: 263 tests completed successfully,
10 environment skips. Live acceptance results are recorded below.

Deployment for the joint test on 2026-09-26:

- GitHub CI run `36268427174` passed Python 3.11/3.12/3.13, Rust and container.
- Compatible optimized CLI built with `rust:1.98-bookworm`, locked dependencies,
  two build jobs and a 4 GiB memory ceiling. The built Lounge source hash matches
  the committed file exactly.
- Replaced only the frontend binary in the existing test receiver container;
  its base image and Python manager still identify as dev18. This is a live
  frontend hotfix, not a published dev19 image or a complete dev19 installation.
- Candidate `--help` succeeded inside the container before activation. After
  restart, health reports ready and both enabled routes are running. Existing
  memory/PID limits and persistent state remain in place.
- Active frontend SHA-256:
  `d9a15d33622775cbb1854b85a88efbff524047416b9e2b307b81c012a02a1888`.
  Previous frontend retained outside the container as `vibecast-dev18.rollback`,
  SHA-256 `b89dc9f7fd2cf9db5295d11c172767ca1bcfa2ef7e3d65c466688dbd1ccd1321`.
  Rollback: stop this container, copy that binary back to
  `/usr/local/bin/vibecast`, then start the same container. Recreating from its
  original dev18 image also removes the hotfix, so use the new source pin for
  future builds.
- Owner confirmed all three modes are selectable after reconnecting, and
  confirmed audible One-mode replay plus manual Next. The matching receiver
  trace shows the same queue index reloaded at time zero, then the next index
  loaded through the normal prefetch path. Owner also confirmed that All mode
  restarts the first playlist title after the final title finishes. All requested
  repeat scenarios passed the joint test; broader hardware coverage is unchanged.

Manual acceptance on the owner's selected test host:

1. Disconnect and reconnect YouTube Music so it receives the new capabilities.
2. Cycle Repeat through Off, All and One; verify the icon stays in the selected mode.
3. In One, seek near the end and verify the same title restarts once.
4. Press Next in One and verify it advances.
5. With a short known queue, verify All wraps from its last title to the first.
6. Turn Repeat off and check normal queue progression, pause, seek and disconnect.

Build/test, deployment and owner confirmation are separate milestones. The joint
test confirmed mode selection, One-mode EOF, manual Next and All-mode queue wrap.
No additional hardware or unrelated feature acceptance is implied.
