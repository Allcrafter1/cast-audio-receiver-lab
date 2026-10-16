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
`2975e7b7d997bb896951656a004c5e94a7b8633f`. It is represented in the product
tree by `patches/vibecast-0.6.0.dev27-current.patch`, applied once over public
dev26 base `83ba470158189de3bc223701decdc4c502d47644`. Patch SHA-256:
`02ed71eec0bf69304436f7d7b21da12640b0d4b9efba93d9b92bafe9cb9a8397`.
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

## First live attempt and follow-up

At 19:05:58 UTC on 2026-10-16, selection of `lENt7-t8I-I` carried a CTT
and entered the credential-bound resolver. All three attempts were rejected
with "This video may be inappropriate for some users." No audio LOAD succeeded.
This confirms token receipt, not successful account authorization.

Comparison with the issue reporter's VideoLoader showed missing content
acknowledgement and MDX playback fields. The follow-up adds `racyCheckOk`,
`contentCheckOk` and `isMdxPlayback` only for matching sender credentials.
Anonymous requests remain unchanged. A mismatched video credential is also
rejected at request construction. The authenticated stream now uses the
existing optional audio cache, preserving URL-refresh behavior.

Follow-up source commit: `2975e7b7d997bb896951656a004c5e94a7b8633f`.
Compatible binary SHA-256:
`c6be61d4a0985cd4e4ec6eb834af5442e872d6c7f0acc3fb88103beb17991d7c`.
Activated on `.110` at approximately 21:10 CEST; the in-container hash matched
and both routes were responsive after restart.
YouTube tests: 99 passed, one live test ignored. A new rejection fixture ensures
that server denial is preserved. Live acceptance of this follow-up is pending;
the ANDROID client still differs from the reporter's Music/TV clients.
