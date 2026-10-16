# YouTube credential transfer — 0.6.0.dev27

## Scope and intent

The YouTube Lounge sender may include a `ctt` with `setPlaylist`. The receiver
now preserves that opaque value only as account context for the selected video
and forwards it to the matching InnerTube player request as:

```json
{
  "context": {
    "user": {
      "credentialTransferTokens": [
        {"scope": "VIDEO", "token": "<sender value>"}
      ]
    }
  }
}
```

This does not manufacture an account, age assertion or entitlement. YouTube
still decides whether the sender-provided context is valid and whether playback
is permitted. The implementation is intended to preserve the user's signed-in
context, not to bypass an access decision.

## Lifetime and isolation

- The token is bound to the selected video ID and active Lounge session.
- Empty values and ambiguous video mappings are ignored.
- A changed token for the same in-flight selection supersedes the old request.
- Retry, repeat and signed-URL refresh for that same selection retain it.
- Next, Previous, queue advancement, Stop and controller takeover discard it.
- Anonymous prefetch never inherits the current title's token, and a
  token-bearing selection never consumes an anonymous prefetched result.
- The value is not persisted, copied into playback metadata, passed on a
  process command line or written to logs. Diagnostics expose presence only.

## Resolver behavior

Anonymous playback keeps the existing parallel InnerTube plus checked `yt-dlp`
strategy. A token-bearing request instead uses the matching authenticated
InnerTube response directly. Waiting for anonymous `yt-dlp` in that case would
both add latency and replace the credential-bound media URL with an unrelated
anonymous result.

## Version and evidence

The maintained frontend was versioned locally as commit
`c730201523c2a1c1541de4fa7f2662e082e0eb21`. It is represented in the product
tree by `patches/vibecast-0.6.0.dev27-current.patch`, applied once over public
dev26 base `83ba470158189de3bc223701decdc4c502d47644`. Patch SHA-256:
`56cbee6d784aa262fd5bd156bd1711fd3fe5feaab696f922551e606ba4c7ede0`.
The local commit is not claimed to exist on the public remote.

Automated verification ran 390 Rust unit/integration tests: 388 passed and two
explicit hardware/live probes were ignored; the SDK doctest also passed. The YouTube crate contributes
98 passing tests and one explicit live-network probe ignored. The Rust 1.98/Zig
GLIBC-compatible optimized x86-64 binary SHA-256 is
`cc51e5aee11e40b177bffa039845e924e90207ff8c9a6190f41ef6688a43e59c`;
its highest referenced GLIBC symbol version is 2.34.

The source/Python/container candidate is `0.6.0.dev27`; Home Assistant store
metadata remains at published `0.6.0-dev26` until an image is built, verified and
promoted through the release workflow.

The compatible binary was activated in the existing `.110` test container at
2026-10-16 21:03 CEST. The mounted and in-container SHA-256 both matched
`cc51e5aee11e40b177bffa039845e924e90207ff8c9a6190f41ef6688a43e59c`.
After startup, management, frontend bridge and both enabled routes reported
ready/responsive with zero restarts. The displaced binary (SHA-256
`40c8796f288715988b56373ff9272445c64fe43d5183557215e91ea7b1ca5619`)
is retained in the host-private, timestamped dev27 rollback directory.

Physical acceptance must separately show that the sender supplies a CTT and
that `Fuck My Computer` (`lENt7-t8I-I`) becomes playable. No token value is
required in evidence or logs.
