# Security policy

This is experimental software intended for a trusted local network. It has not
received an independent security audit and currently has no support SLA.

The management UI deliberately has no application login. Do not expose its LAN
port to the Internet or an untrusted network. Use normal host/network isolation
when that trust assumption is unsuitable.

Please do not attach authentication bundles, private keys, pairing credentials,
account tokens, signed media URLs, raw environment dumps, private addresses or
unreviewed full logs to a public issue. Start with `/api/support`, the exact app
version, the failing stage and a short redacted log excerpt as described in
`docs/maintenance.md`.

For a suspected vulnerability, use GitHub's **Report a vulnerability** private
reporting channel. Do not publish exploit details or credentials in an issue.

Cast authentication compatibility, service revocation and protocol breakage are
known availability risks, not promises made by this project. A long local
certificate inventory does not establish future acceptance or permission to
redistribute third-party credentials.
