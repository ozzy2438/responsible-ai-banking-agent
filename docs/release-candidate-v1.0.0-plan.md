# v1.0.0 Stable Release Runbook

This runbook defines the controlled publication path for the synthetic
portfolio release. It does not make the application a production banking
system, a compliance certification, or evidence of real-bank approval.

## Release invariants

The release workflow fails closed unless all of these conditions hold:

1. The pushed tag is exactly `v1.0.0`.
2. The tagged commit is contained in protected `main` history.
3. The tag, `pyproject.toml` package version, and runtime API version all
   resolve to `1.0.0`.
4. The reusable CI workflow reruns all 11 blocking gates successfully.
5. The image publishes only immutable `1.0.0` and `sha-<commit>` tags; it
   never publishes `latest`.
6. The exact published digest receives GitHub build-provenance and SBOM
   attestations, is pulled by digest, and passes the release smoke test before
   GitHub creates the stable release.

## Controlled sequence

1. Merge the release-preparation pull request through protected `main` after
   its required review and checks pass.
2. Confirm the exact merge SHA and its post-merge CI result.
3. Create annotated tag `v1.0.0` on that exact protected-main commit and push
   only that tag.
4. Wait for the tag-triggered `Stable release` workflow to complete.
5. Record and independently verify:

   - workflow run and released commit;
   - GHCR digest and immutable tags;
   - absence of a `latest` tag;
   - SPDX JSON SBOM release asset;
   - build-provenance and SBOM attestations;
   - exact-digest pull and smoke result;
   - stable GitHub release state.

If any gate fails, do not create or recreate the GitHub release manually.
Correct the cause through a reviewed commit and use a new authorised version;
never move or overwrite the immutable `v1.0.0` tag.

## Verification commands

Replace `<digest>` with the digest reported by the successful release
workflow:

```sh
docker pull ghcr.io/ozzy2438/responsible-ai-banking-agent@sha256:<digest>
gh attestation verify \
  oci://ghcr.io/ozzy2438/responsible-ai-banking-agent@sha256:<digest> \
  --repo ozzy2438/responsible-ai-banking-agent
```

The public package contains synthetic application code only. A green release
is evidence about the tested artifact and delivery controls; it is not a
production deployment, legal approval, or compliance finding.
