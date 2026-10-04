# Repeatable releases

## Normal path

The 2026-10-02 YouTube recovery/cache work is committed in the maintained fork
and pinned in `config/vibecast-frontend.lock.json`; see
[YouTube load recovery](youtube-load-recovery.md). Do not apply its snapshot on
top of the pinned commit.

1. Prepare a new source version locally (does not advertise an App update):

   ```sh
   python3 tools/release.py prepare --version 0.6.0.dev22 --execute
   ```

2. Implement/test the change, add reviewed entries to the project and App
   changelogs, then commit and push to `main`. Leave the App config version on
   the last available image. No credentials or live state belong in the commit.
3. Run the **Release App** workflow once with the exact candidate version:

   ```sh
   gh workflow run release.yml -f version=0.6.0-dev22 -F publish=true
   ```

The workflow checks the version and notes, refuses existing image/release tags,
waits for successful CI at the exact source SHA, runs cached native image builds
and source review in parallel, verifies anonymous registry retrieval and source
archive integrity, updates App metadata and install image references, then
creates the experimental GitHub release with source/digest assets. It never
changes private receiver hosts or installs/updates a user's HA App.

The default `publish=false` is a **read-only plan**, not a release. It checks
version/notes and validates workflow wiring without publishing or promoting:

```sh
gh workflow run release.yml -f version=0.6.0-dev22
python3 tools/release.py plan --expected-tag 0.6.0-dev22
```

The release uses the repository's short-lived Actions token, no personal token
or new external service. A fast-forward-only push prevents promotion over
unrelated work. Main must stay on the reviewed source SHA until promotion. If
branch protection disallows this push, promotion stops; review/merge the
metadata change through the repository's normal protected-branch process.

## Caching and measured baseline

The dev20 successful publish run took about **5m18s** end-to-end. Native image
build/push took **4m20s amd64** and **3m19s arm64**, concurrently, not in series.
An earlier attempt failed on an incorrect extra smoke-test import and had to be
repeated. Manual orchestration, source/archive downloads and documentation added
further delay; this was not all unavoidable first-deployment cost.

CI now exports BuildKit `mode=max` caches separately for each architecture;
publication imports those and its own caches. Version labels are after expensive
runtime installation layers. An unchanged Rust/frontend dependency stage can be
reused for a UI-only or version change. The source-review build has its own
pin-keyed Cargo cache. Cache export is bounded to two minutes and non-fatal; a
cache miss remains a valid clean build. No test gate is removed to gain speed.
The initial cache fill can be slower. Warm-build savings must be measured, not
promised as a fixed number for every release.

Measured in CI run **36273870651**, same source `a1f079d`: amd64 build step
**5m19s cold → 20s warm**, complete container job **5m45s → 37s**. The cold step
includes the initial 1m47s cache export; the warm run reports cache hits including
the Rust release build. Both native builds and subsequent runtime checks pass.
This is an unchanged-source, non-publishing container benchmark, not a promise
for a full release or every code change. ARM64 cache creation passed; its warm
speed was not separately benchmarked.

Validation also includes 278 local tests (10 environment skips), actionlint,
read-only **Release App** run `36273886576`, anonymous readback of the actual
dev20 index/configs, and rejection of its existing release tag before any write.
No dev21 was created and dev20 was not republished just to test orchestration.
The full automated publication path will first execute for a newly approved
version; individual gates and existing publication/source workflows are tested.

## Recovery boundaries

- Before manifest creation, a failed platform cannot promote the App. Fix the
  cause and rerun from a reviewed commit while that version is still unused.
- If images were published but promotion failed, **do not rebuild/overwrite the
  same version tag**. Inspect the run, retain its source SHA and download its
  `published-image-digest-*` and `vibecast-source-review-*` artifacts. The
  `promote` command is a separately invocable verified step; it requires the
  exact built checkout, unchanged main and successful CI. A moving main needs a
  reviewed recovery, not a force push or silently skipped gate.
- If the metadata commit succeeded but release creation failed, the App image
  is already available. Complete the GitHub release from that commit and the
  existing verified assets; no new receiver build is needed. Do not claim the
  entire release succeeded until the attachments are uploaded.
- A GitHub release does not prove that an existing HA installation follows that
  repository. Check the installed App's repository/slug, installed version and
  `version_latest`. A former local test repository creates a separate identity
  even if the App names match. Migrate with scoped backups and preserve Cast
  identity/data; never solve this by deleting the old data or running duplicate
  receivers on the same ports.

See `release-dev20.md` for the public-image baseline. The later HA migration was
separately authorized: old App retained stopped/manual, public App dev20 running,
three routes/installation identity/authentication material unchanged. This is
distinct from the earlier standalone x86_64 test-host deployment.
