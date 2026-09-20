# Separate bundle artifact — privately staged, not publicly published

Code and authentication material have separate release lifecycles. On
2026-09-20 the owner-authorized bundle was staged as a **draft release in the
private** `Allcrafter1/cast-audio-receiver-bundles` repository. Its Git history
contains only provenance documentation and ignore rules, never bundle bytes.
No public download service or signing identity has been enabled. Automated
unit tests use only obviously synthetic JSON. The importer does not
generate, extract or circumvent authentication; it verifies a supplied artifact.

## Private round-trip verification

Draft version `2026.09.20` holds the 2,742,207-byte bundle and its 283-byte
manifest. Both were downloaded again through authenticated GitHub access into
a mode-0700 temporary directory (bundle mode 0600) and their SHA-256 values
matched the original files. The metadata-only record is
`config/bundle-artifact-staging.json`. No keys appear in that record.

This verifies hosting integrity, **not anonymous installation**. While the
repository is private and the release is a draft, the manifest's final release
URL is not an available public download. Do not silently turn that staging
record into a default runtime acquisition setting. The existing HA test app
continues using its local, working bundle, with no network dependency added.

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
signature verification; no self-signed downloaded key is trusted. Final public
availability and an anonymous importer test remain publication tasks.

Separate hosting changes organization and withdrawal, not permission to
redistribute material. Provenance, proprietary reference-app conditions and
shared-identity/revocation risks must be reviewed independently of code licences.
