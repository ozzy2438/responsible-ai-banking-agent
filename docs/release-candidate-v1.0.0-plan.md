# v1.0.0 Stable Release &mdash; Readiness Plan (DRAFT, NOT APPLIED)

**Status: proposal only.** Nothing in this document has been executed. No
tag has been created, the release workflow has not been changed, and no GitHub
release or GHCR image has been published. It exists so the repository
owner has one place to review exactly what publishing `v1.0.0` would
involve and which approvals are required before anything publishes.

## What "release" means here

Same definition as the rest of this repository: a **synthetic portfolio
reference release**, not a production deployment, not a compliance
certification, and not evidence of real-bank approval. The existing
`docs/delivery.md` release controls (SBOM, attestations, digest pinning, no
`latest` tag) remain required, but its RC2-specific wording must be updated in
the future release-preparation commit described below.

## Blocking release-preparation work

The current repository cannot publish a correct stable `v1.0.0` tag yet:

1. `.github/workflows/release.yml` triggers and authorises only
   `v0.1.0-rc.2`.
2. `pyproject.toml` and the API identify the current development build as
   `0.2.0.dev0`, not `1.0.0`.
3. The workflow creates a GitHub prerelease. A stable `v1.0.0` must not use
   `--prerelease`.
4. The release notes emitted by the workflow are RC2-specific and do not yet
   use the reviewed stable notes below.

**A `v1.0.0` tag pushed today would not publish a release.** This is deliberate
fail-closed design from RC2. A separate release-preparation commit must make
all of the following changes together before any tag exists (not applied):

```diff
 on:
   push:
     tags:
-      - v0.1.0-rc.2
+      - v1.0.0
@@
       - name: Enforce the authorised release candidate tag
         shell: bash
-        run: test "$GITHUB_REF_NAME" = "v0.1.0-rc.2"
+        run: test "$GITHUB_REF_NAME" = "v1.0.0"
@@
         with:
           images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
           flavor: latest=false
           tags: |
-            type=raw,value=0.1.0-rc.2
+            type=raw,value=1.0.0
             type=raw,value=sha-${{ github.sha }}

 pyproject.toml:
-  version = "0.2.0.dev0"
+  version = "1.0.0"

 release command:
-  gh release create ... --prerelease ...
+  gh release create ... --notes-file docs/release-notes-v1.0.0.md ...
```

The release preparation must also add a blocking tag/package/API version
equality check and update `docs/delivery.md` from RC2-specific wording. All
other controls remain unchanged: SHA-pinned Actions, no `latest` tag, SBOM,
provenance and SBOM attestations on the exact digest, and a smoke test against
that published digest before creating the GitHub release.

## Readiness checklist against the exact release commit

The release SHA must be a merge commit on protected `main` that already
contains the approved release workflow, `1.0.0` package version, stable notes,
and all documentation updates. Do not tag this feature branch, its current
head, or an earlier pre-merge SHA: GitHub executes the workflow stored in the
tagged commit.

- [ ] All 11 blocking CI gates pass on the exact release-preparation commit
      (repository hygiene,
      Ruff + strict typing, unit tests, PostgreSQL integration, policy
      evaluations, container smoke, dependency audit, secret scan, static
      security scan, filesystem vulnerability scan, image vulnerability
      scan). Feature-branch CI is supporting evidence only; this item remains
      unchecked until those gates pass on the future release SHA.
- [ ] Package and API version set to `1.0.0`; workflow re-pointed to
      `v1.0.0`; prerelease mode removed; reviewed notes wired in; and
      tag/version equality gate added &mdash; **not yet applied, pending owner
      approval.**
- [ ] Exact protected-`main` commit SHA for the tag confirmed by the owner.
- [ ] Tag `v1.0.0` created and pushed &mdash; **not yet done, pending owner
      approval.**
- [ ] Release workflow republishes CI gates, then builds and pushes the
      image with immutable tags only: `1.0.0` and `sha-<commit>`. No
      `latest` tag, matching the RC2 policy.
- [ ] SPDX JSON SBOM generated and uploaded as a workflow artifact.
- [ ] GitHub build-provenance attestation and SBOM attestation created for
      the exact image digest and verified with `gh attestation verify`
      before the release is created.
- [ ] Published digest pulled and smoke-tested (`/healthz`) before the
      GitHub release is created &mdash; matches the existing RC2 smoke step.
- [ ] Stable GitHub release created from the verified tag, with
      release notes drafted below.
- [ ] Quick-start instructions re-verified against the published image
      (not just the local build) before announcing the release.

## Draft release notes (for `v1.0.0`, not yet published)

```markdown
## v1.0.0 &mdash; portfolio reference release

Synthetic, human-supervised banking assistant reference implementation.
Deterministic risk classification, authorization, redaction, cited
evidence, and mandatory human escalation run as code, not as prompts.

**This is a portfolio reference release only.** It is not deployed by,
or affiliated with, any real bank; not certified as legally or
regulatorily compliant; not connected to real customer data; and not
authorized to move money or make an autonomous credit, fraud, or hardship
decision under any configuration. See the README's Limitations section
and docs/production-readiness-roadmap.md for what a real deployment would
still require.

### What's new since v0.1.0-rc.2

- One-command demo: `make demo` / `docker compose up --build` builds the
  app, starts PostgreSQL, runs migrations, seeds four synthetic demo
  identities, and serves the app on loopback-only ports &mdash; no manual
  setup. Demo database state is ephemeral and recreated with the stack.
- A customer-facing landing page and assistant UI with four prepared
  scenarios (LOW, MEDIUM, HIGH, prompt-injection), plus a visually
  refreshed reviewer console.
- A blocking full-stack Compose HTTP smoke that starts the packaged app and
  PostgreSQL, verifies the customer answer/escalation path and reviewer
  route/close path, recreates the stack, and runs the journey again, in
  addition to the unit, integration, and 48-case policy evaluation suites.
- An architecture diagram, real screenshots, a 90&ndash;120s demo script,
  and a rewritten, CV-ready README.

### Evidence

- Public image: `ghcr.io/ozzy2438/responsible-ai-banking-agent@<digest>`
  (immutable digest; also tagged `1.0.0` and `sha-<commit>`, no `latest`).
- SPDX JSON SBOM published as a release asset, with GitHub build-provenance
  and SBOM attestations bound to the exact OCI image digest; verify with:
  ```sh
  gh attestation verify \
    oci://ghcr.io/ozzy2438/responsible-ai-banking-agent@<digest> \
    --repo ozzy2438/responsible-ai-banking-agent
  ```
- 11/11 blocking CI gates passing on the released commit; see the linked
  workflow run.

Synthetic public reference release only; not production approved.
```

## Owner approvals needed

Everything above is ready to execute except two owner decisions:

1. **Approve the release-preparation change** (workflow, `1.0.0` version,
   stable notes, delivery docs, and tag/version gate) after this feature PR is
   merged.
2. **Confirm the resulting protected-`main` SHA and separately approve
   pushing the `v1.0.0` tag.** Nothing publishes until both approvals and a
   green exact-SHA CI run exist.
