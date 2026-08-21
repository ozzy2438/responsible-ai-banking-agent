# v1.0.0 Release Candidate &mdash; Readiness Plan (DRAFT, NOT APPLIED)

**Status: proposal only.** Nothing in this document has been executed. No
tag has been created, no workflow file has been changed, and no GitHub
release or GHCR image has been published. It exists so the repository
owner has one place to review exactly what publishing `v1.0.0` would
involve, and to give the one approval required before any of it happens.

## What "release" means here

Same definition as the rest of this repository: a **synthetic, portfolio
reference candidate**, not a production deployment, not a compliance
certification, and not evidence of real-bank approval. The existing
`docs/delivery.md` release-evidence language (SBOM, attestations, digest
pinning, no `latest` tag) applies unchanged.

## Blocking technical issue found during review

`.github/workflows/release.yml` is currently hardcoded to the exact string
`v0.1.0-rc.2` in two places:

1. `on.push.tags` &mdash; only a `v0.1.0-rc.2` tag push triggers the workflow
   at all.
2. The `Enforce the authorised release candidate tag` step: `test
   "$GITHUB_REF_NAME" = "v0.1.0-rc.2"`, which fails the job closed for any
   other tag even if the workflow were somehow invoked.

**A `v1.0.0` tag pushed today would not trigger a release, and if the
trigger were changed but not this check, the job would fail closed at that
step.** This is deliberate fail-closed design from the RC2 work, not a bug
&mdash; it just needs to be re-pointed at the new candidate tag before
`v1.0.0` can be published. The minimal, in-place edit (not applied) would
be:

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
```

No other logic changes: still SHA-pinned Actions, still no `latest` tag,
still SBOM + provenance + SBOM attestation on the exact digest, still a
smoke test against the exact published digest before the GitHub release is
created.

## Readiness checklist against the exact candidate commit

Once the owner names the exact commit SHA to release (expected to be this
PR's merge commit on `main`, or `fa5b650fbf5d59c78401b8e0b1e44e026d983cd2`
if released pre-merge from this branch):

- [x] All 11 blocking CI gates pass on that commit (repository hygiene,
      Ruff + strict typing, unit tests, PostgreSQL integration, policy
      evaluations, container smoke, dependency audit, secret scan, static
      security scan, filesystem vulnerability scan, image vulnerability
      scan) &mdash; confirmed green on PR #12, both workflow attempts, 0
      failures.
- [ ] `release.yml` re-pointed at `v1.0.0` (diff above) &mdash; **not yet
      applied, pending owner approval.**
- [ ] Exact commit SHA for the tag confirmed by the owner.
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
- [ ] GitHub prerelease/release created from the verified tag, with
      release notes drafted below.
- [ ] Quick-start instructions re-verified against the published image
      (not just the local build) before announcing the release.

## Draft release notes (for `v1.0.0`, not yet published)

```markdown
## v1.0.0 &mdash; portfolio reference release

Synthetic, human-supervised banking assistant reference implementation.
Deterministic risk classification, authorization, redaction, cited
evidence, and mandatory human escalation run as code, not as prompts.

**This is a portfolio reference candidate only.** It is not deployed by,
or affiliated with, any real bank; not certified as legally or
regulatorily compliant; not connected to real customer data; and not
authorized to move money or make an autonomous credit, fraud, or hardship
decision under any configuration. See the README's Limitations section
and docs/production-readiness-roadmap.md for what a real deployment would
still require.

### What's new since v0.1.0-rc.2

- One-command demo: `make demo` / `docker compose up --build` builds the
  app, starts PostgreSQL, runs migrations, seeds four synthetic demo
  identities, and serves the app &mdash; no manual setup.
- A customer-facing landing page and assistant UI with four prepared
  scenarios (LOW, MEDIUM, HIGH, prompt-injection), plus a visually
  refreshed reviewer console.
- End-to-end automated coverage of the full demo journeys (customer
  assistant flow and reviewer acknowledge/route/close flow) in addition to
  the existing unit, integration, and 48-case policy evaluation suites.
- An architecture diagram, real screenshots, a 90&ndash;120s demo script,
  and a rewritten, CV-ready README.

### Evidence

- Public image: `ghcr.io/ozzy2438/responsible-ai-banking-agent@<digest>`
  (immutable digest; also tagged `1.0.0` and `sha-<commit>`, no `latest`).
- SPDX JSON SBOM and GitHub build-provenance + SBOM attestations attached
  to this release; verify with:
  ```sh
  gh attestation verify \
    oci://ghcr.io/ozzy2438/responsible-ai-banking-agent@<digest> \
    --repo ozzy2438/responsible-ai-banking-agent
  ```
- 11/11 blocking CI gates passing on the released commit; see the linked
  workflow run.

Synthetic public reference candidate only; not production approved.
```

## The one approval needed

Everything above is ready to execute except two owner decisions:

1. **Confirm the exact commit** to release (this PR's merge commit on
   `main` once merged, or a specific SHA if released pre-merge).
2. **Approve applying the `release.yml` diff above and pushing the
   `v1.0.0` tag.** Nothing publishes until both of those happen.
