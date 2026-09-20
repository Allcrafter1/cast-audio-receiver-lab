# Separate authentication-bundle artifact

Code and authentication material have separate release lifecycles. The public
`Allcrafter1/cast-audio-receiver-bundles` repository contains provenance and
risk documentation, while release `2026.09.20` supplies the 2,742,207-byte
bundle and its small manifest as versioned Release Assets. Bundle bytes are not
part of either project's Git history or the runtime image.

The bundle contains 773 validated daily windows from 2026-09-12 through
2030-12-06 (end exclusive). This describes stored coverage, not guaranteed
future acceptance: the shared identity can be revoked and protocols can change.
The material came from the project owner's purchased AirReceiver installation;
it was not issued to this project. The reference APK is not redistributed.

## Verified public acquisition

The release assets were downloaded anonymously into a mode-0700 temporary
directory, the bundle was stored with mode 0600, and exact size and SHA-256
checks passed. The metadata-only record is
`config/bundle-artifact-staging.json`; no keys appear in it.

In dev18, a clean container/HA installation with no explicit bundle and no
existing state uses the packaged, hash-pinned release manifest exactly once.
Explicit local/BYO input always wins, existing state is never implicitly
replaced, and subsequent restarts do not require the bundle host.

## Proposed release shape

Use a small dedicated GitHub repository for public provenance/risk documentation
and versioned Release Assets, not bundle bytes in Git. A release attaches
the bundle and JSON manifest; a signed attestation is an optional additional
release mechanism, not implemented by the current importer. A reviewed main
project release pins the **manifest SHA-256**, which in turn pins version, HTTPS
URL, exact size and bundle SHA-256. The manifest must be trusted independently;
a checksum downloaded from the same untrusted location is not authenticity.

Schema 1 requires `schema_version`, `version`, `url`, `size` and `sha256`;
`withdrawn: true` rejects acquisition. Stable URLs may not contain credentials,
query strings or fragments. HTTPS redirects (including GitHub signed CDN URLs)
are allowed, but HTTP downgrades are not. Those URLs are never printed.

The manifest is bounded to 16 KiB; the artifact to 32 MiB and its pinned size.
Import is mode 0600, fsynced and atomically renamed only after size/hash and
basic JSON validation. This does **not** claim cryptographic validation of Cast
identity, date windows, certificate chains or future acceptance. The existing
frontend/import audit performs that separate task.

```bash
cast-audio-bundle /trusted/release/manifest.json \
  --manifest-sha256 <digest-from-reviewed-project-release> \
  --destination /private/state/certs.json
```

This is an explicit installation/update operation, not a network dependency on
every startup. Local `--certs` and HA `/share` imports still work unchanged.
Keep a private mode-0600 copy of a known-working bundle before updating. Rollback
is selecting that local file or explicitly re-importing a trusted older version.
Concurrent update invocations should not be used; runtime rotation is separate.

## Withdrawal and trust limits

Removing the release asset stops future downloads from our distribution. A
failed/withdrawn download leaves the existing local artifact unchanged. There
is no remote kill switch, no unverified fallback and no automatic replacement
of a user's own bundle. A downloaded or mirrored copy cannot be recalled.

An old, hash-pinned manifest does not magically learn a new withdrawal flag;
asset withdrawal is enforced by removing the hosted bytes, while a revised
manifest needs a new trusted pin. This is deliberate offline-friendly behavior.

The chosen initial trust mechanism is the **manifest hash pinned through the
reviewed main-project release**. This satisfies the requested hash/signature
integrity option without inventing another signing service. A future attestation
must be verified against a trusted repository/workflow identity before claiming
signature verification; no self-signed downloaded key is trusted. Public
availability and anonymous importer behavior were verified before the
dev18 release. Future bundle versions require a new reviewed manifest pin.

Separate hosting changes organization and withdrawal, not permission to
redistribute material. Provenance, proprietary reference-app conditions and
shared-identity/revocation risks must be reviewed independently of code licences.
