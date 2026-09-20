# Public-release gates

This is a checklist, not a declaration that the project is ready for publication.
The development receiver and its private runtime inputs are separate from a
redistributable release. The latest deployment is recorded in WORKING-PLAN.md.

## dev13 review findings to retain

- Runtime/UI/private HA fixes and automated/reference-RAOP evidence are recorded
  in `review-dev13.md`; stock YT Music visual and other hardware checks remain.
- The bundle importer uses a trusted pinned manifest hash. Real release signing,
  hosting and actual upload still need an explicit publication action.
- Retain current licence evidence beside stale upstream notices. In particular,
  resolve the prebuilt OpenSSL 3.5.4 versus old source-submodule mismatch before
  claiming complete corresponding source for the airplay-cli binary.
- Generate a final image SBOM (for example with Syft) and review exact Debian,
  Python, Rust and native dependency/source inventories. The image's recorded
  package versions and FFmpeg/mpv build details are inputs, not the full audit.
- Promote the verified local frontend overlay to the maintained fork only when
  publishing is authorized; replace both build/CI inputs consistently.

## Already available

- Architecture/runbook, maintenance workflow and reproducible test matrix.
- AI-development disclosure and contribution guidance.
- Maintained Vibecast fork commit plus complete fallback patch, source hashes
  and reconstruction checks.
- Python versioning, complete container CPython 3.12 runtime/build locks and
  tested x86_64 CPython 3.12/3.13 management wheel locks.
- AirPlay upstream asset/version record and initial credits/license inventory.
- Speaker UI without login, stable IDs, deletion and configurable web port.

## Before making a repository public

- [ ] Review the exact export AND Git history for private data. Do not simply
  push the dirty development checkout. Exclude `.state`, private credentials,
  APKs, packet captures, account/pairing data and unreviewed logs.
  An allowlisted text-only export with a file/hash manifest now exists, passes
  the full suite and is staged in a new-history private GitHub repository. Manual
  review is still required before checking this public-release gate.
  dev17: a fresh private staging clone has seven reachable commits and 259
  unique historical path/blob versions; all pass the bounded export checks.
  Repeat `python tools/check_public_history.py /path/to/fresh-clone` after the
  final update. CI fetches full history and runs this check too. It does not
  inspect unreachable objects, release assets or external bundle hosting and
  does not replace manual review.
- [ ] Distinguish test fixtures from real credentials; inspect patches and built
  archives too. A grep-based secret scan alone is not sufficient clearance.
- [ ] Verify attribution for the actual code/research used, without inventing
  endorsements. Retain upstream license texts.
- [ ] Resolve source-distribution questions in THIRD_PARTY_NOTICES.md. Review
  combined binary/container distribution separately, especially airplay-cli's
  documented mixed-license/unclear-grant components.
- [ ] Reconstruct and test from the intended clean public source, rather than
  relying on untracked files or the old remote vendor directory.
- [x] Document supported installation and private runtime-input requirements.
  Do not imply credential redistribution permission or future Google acceptance.
- [ ] Add immutable release artifacts/tags only after the corresponding source,
  dependency records and license review match.

## Before calling the release generally usable

- [x] Confirm dev11 cover rendering in real Home Assistant; retain the known
  distinction between missing sender metadata and receiver propagation errors.
- [ ] Test real Yamaha/other RAOP hardware and HomePod/AirPlay2 separately.
- [ ] Test concurrent outputs and receiver-origin control/feedback to YT Music.
- [x] Validate a real HAOS/Supervisor source build, installation, initial start,
  ingress/LAN access, restart and persistent route ID/state.
- [ ] Validate published-image update and rollback while retaining state and IDs.
- [ ] Measure resource use on intended smaller platforms. x86_64 results do not
  establish ARM compatibility or its dependency/native-binary availability.
- [x] Verify the final private certificate inventory independently: 773 distinct,
  gap-free windows through 2030-12-06, one public key, valid signatures/chain.
  Import/start on the real HA test App passed; this does not prove future sender
  acceptance or grant redistribution rights.

## Following milestones

The Home Assistant packaging source now has persistent `/data`, host-network
guidance, dynamic ingress, a configurable LAN port, health APIs and one process
owner. Real source-build installation and restart/persistence acceptance passed;
it still needs a published image plus update/rollback and physical AirPlay
acceptance before it is called generally usable.

A generated secret-free local-build repository has been accepted by a real
Supervisor and is the pre-publication acceptance path. Its temporary LAN Git
service and separately supplied `/share` bundle are test infrastructure, not a
release distribution mechanism.

Only after a usable documented public repository exists, respond to the relevant
Music Assistant discussions. State the experimental/revocable nature, welcome
review/reuse, and do not promise to build a Music Assistant integration ourselves.
