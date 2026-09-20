# Separate bundle artifact — prepared, not published

Code and authentication material have separate release lifecycles. No real
material, public hosting repository, signing identity or download URL is created
by this review. Tests use only obviously synthetic JSON. The importer does not
generate, extract or circumvent authentication; it verifies a supplied artifact.

## Proposed release shape

Use a small dedicated GitHub repository for public provenance/risk documentation
and versioned Release Assets, not bundle bytes in Git. A release would attach
the bundle, JSON manifest, checksum and a signed attestation. A reviewed main
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

Actual signing/attestation issuance and verification of the real release remain
a publication gate: choose the distribution repository/identity, verify with
GitHub artifact attestation tooling, then record its immutable trusted manifest
digest. No self-signed downloaded key is treated as trusted. The present importer
implements the pinned-hash trust path, not an invented signing infrastructure.

Separate hosting changes organization and withdrawal, not permission to
redistribute material. Provenance, proprietary reference-app conditions and
shared-identity/revocation risks must be reviewed independently of code licences.
