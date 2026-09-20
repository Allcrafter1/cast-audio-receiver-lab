# Contributing

Independent reviews, bug reports, tests and focused improvements are welcome.
This is experimental software developed extensively with AI assistance and
practical user testing, not a certified Cast implementation. Read the
[project origin](docs/PROJECT-ORIGIN.md) and [working plan](docs/WORKING-PLAN.md)
before proposing large changes.

## Scope and development

Priorities are reliable YouTube Music reception, generic direct-URL Default
Media Receiver support, and local/AirPlay outputs. Google Home adoption/groups
and arbitrary DRM/service Web Receivers are not supported. Prefer existing
native solutions before adding another service-specific adapter.

Follow the [current runbook](docs/current-runbook.md) and
[source reconstruction](docs/source-reconstruction.md). Use a separate virtual
environment and the matching complete frontend patch, not all historical patches.
Preserve private state. With management extras installed, run:

```sh
python -m unittest discover -s tests -q
python -m compileall -q src tools
```

Tests use loopback servers and owned subprocesses; a restrictive sandbox may
block them. FFmpeg tests explicitly skip if it is absent. A skip does not prove
working conversion. Rust commands/toolchain are in the reconstruction guide;
real decoding, artwork and device checks are in [TESTING.md](docs/TESTING.md).

- Add a regression before fixing a reproducible bug. Distinguish sender-side
  behavior from receiver errors before changing message order or queue logic.
- Keep playback independent of optional image processing. Bound queues, retries,
  caches and subprocesses, and cancel/reap obsolete work.
- Preserve speaker identities and saved settings across upgrades.
- Keep version, changelog, complete patches and source locks consistent.
- Distinguish implemented, automated-tested, deployed and user-confirmed.
- Discuss substantial refactors and new dependencies first. Do not incidentally
  remove format checks, retune audio buffers or add permanent extractor workers;
  those trade-offs were explicitly deferred.

## Reporting and publishing

Report versions/hashes, platform, sender/output types, steps, timestamp, expected
and actual behavior. Compare local output against AirPlay and the same source
on another receiver where possible. See [maintenance](docs/maintenance.md).

Never attach authentication bundles, private keys, tokens/cookies, signed media
URLs, pairing secrets, full environments or unreviewed logs. Titles, filenames,
device names and LAN addresses may also be private. Review all attachments.

Our GPL-3.0-or-later declaration does not relicense dependencies. Preserve
upstream notices and credit actual contributions. Unresolved distribution
questions are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Passing tests
is not independent security review. Do not imply Google/Apple/Music Assistant
endorsement or guarantee future service compatibility. Music Assistant outreach
must wait for a usable, public, documented repository.
