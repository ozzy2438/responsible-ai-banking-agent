# Delivery Controls

## Pull request gates

The `CI` workflow runs with read-only repository permissions unless a job needs
less. Its independently visible blocking jobs are:

- Repository hygiene
- Ruff and strict typing
- Unit tests
- PostgreSQL integration
- Policy evaluations
- Container smoke
- Dependency audit
- Secret scan
- Static security scan
- Filesystem vulnerability scan
- Image vulnerability scan

All third-party and GitHub-authored Actions are pinned to full commit SHAs. The
container uses a digest-pinned Python base, runs as UID/GID `10001:10001`, and is
smoked with a read-only root filesystem.

## Release candidate

Only the exact `v0.1.0-rc.2` tag activates the release workflow. It first calls
the full CI workflow again. After all gates pass, it publishes the public GHCR
image with only these tags:

- `0.1.0-rc.2`
- `sha-<full release commit>`

It deliberately does not publish `latest`. The workflow generates an SPDX JSON
SBOM, creates GitHub-signed build-provenance and SBOM attestations for the exact
image digest, verifies the attestation, pulls and smokes that digest, uploads the
SBOM, and finally creates a GitHub prerelease.

Verification after publication:

```sh
docker pull ghcr.io/ozzy2438/responsible-ai-banking-agent@sha256:<digest>
gh attestation verify \
  oci://ghcr.io/ozzy2438/responsible-ai-banking-agent@sha256:<digest> \
  --repo ozzy2438/responsible-ai-banking-agent
```

The public package contains only synthetic application code and must never be
treated as a private customer artifact. A green workflow is evidence about the
tested commit; it is not a production deployment, stable release, legal
approval, or compliance finding.
