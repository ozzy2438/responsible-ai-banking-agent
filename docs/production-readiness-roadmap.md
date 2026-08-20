# Production Readiness Roadmap

> **Planning artifact, not a compliance or security sign-off.** It records
> what is already built, what remains, and — for each remaining item —
> whether it is something a future engineering change in this repository can
> close, or something only the bank's own legal, risk, privacy, security, and
> executive functions can close. No item in the second category can be
> satisfied by a commit.

## Where this sits

`v0.1.0-rc.2` is a technically verified, synthetic-data-only reference
candidate: CI, security scanning, SBOM, and provenance attestation pass on a
pinned commit. That is evidence about the tested commit. It is not a
production deployment, legal approval, or compliance finding — see
[the evidence language in the README](../README.md#evidence-language) and
[known limitations in the system card](system-card.md#known-limitations).

## Status summary

| # | Stage | Type | Status |
|---|---|---|---|
| 1 | Reconcile RC2 release fixes onto the trunk branch | Engineering | Done — see below |
| 2 | Real identity provider and strong customer authentication | Engineering + external | Not started |
| 3 | Approved real bank system and data integrations | Engineering + external | Not started |
| 4 | Bank legal, risk, privacy, and compliance approval | Organizational | Not started |
| 5 | Production infrastructure: secrets, monitoring, DR, incident response | Engineering + organizational | Not started |
| 6 | Independent security testing, UAT, model-risk validation, controlled pilot | External + organizational | Not started |

"Engineering" items can be advanced by writing code and docs in this
repository. "External" and "organizational" items require people, contracts,
or approvals outside this repository; a coding session cannot complete them,
only prepare the inputs they need.

## 1. Reconcile RC2 onto the trunk branch — done

Root cause: PR #1 merged the initial implementation into `main`, but the
three release-workflow fixes that actually shipped as `v0.1.0-rc.2`
(`a09c8b4`, `2d152d6`, `cadded0`) were committed directly onto
`feat/initial-responsible-banking-agent` afterward and never came back
through review. `main` and the published RC2 image therefore diverged: the
tag was correct, the trunk branch was stale.

This branch merges those three commits so its `.github/workflows/release.yml`,
`README.md`, and `docs/delivery.md` are now byte-identical to the
`v0.1.0-rc.2` tag. Once this lands on `main` through normal review, the drift
is closed.

**Prevention:** treat a pushed release tag as a signal to check that the tag
commit is reachable from `main`, not just that the tag exists. A branch
protection rule requiring release-workflow changes to land via reviewed PR
(no direct pushes to feature branches post-merge) would have caught this
automatically.

## 2. Real identity provider and strong customer authentication

Today, identity is a local-only secure cookie or a bearer token minted by
`POST /dev/login`, which the app refuses to expose outside `local`/`test`
environments (see [`docs/architecture.md`](architecture.md) and the README's
run instructions). That boundary is correct for a reference app and wrong for
production.

**Engineering work this repo can do:**
- Introduce a pluggable authentication-provider interface, mirroring the
  optional-provider pattern already used for reasoning
  ([ADR 0002](decisions/0002-optional-openai-provider.md)): a
  production build selects an OIDC/OAuth2 adapter; `local`/`test` keep the
  simulated identity path, unreachable by construction outside those
  environments.
- JWKS-based token validation, session binding to `request_id`, and
  step-up/MFA hooks that the risk layer can require before high-risk actions.
- Fail closed (escalate, do not authenticate) if the real IdP is unreachable
  or returns an ambiguous result, consistent with the existing
  fail-closed posture in [`docs/architecture.md`](architecture.md#failure-behaviour).

**Not closable by engineering alone:** which IdP/SCA method the bank actually
runs, the customer consent and re-authentication policy, and acceptance of
the adapter by the bank's identity and security teams.

**Exit criteria:** no simulated-identity code path is reachable in a
production build; an independent auth review has signed off the adapter.

## 3. Approved real bank system and data integrations

All account, transaction, and policy data today are synthetic fixtures with a
committed manifest hash ([`docs/policy-source-register.md`](policy-source-register.md)).
A larger, deterministic synthetic dataset now exists
([`docs/synthetic-data.md`](synthetic-data.md)) for engineering confidence and
demos at scale — it strengthens this stage's testing but does not close it: a
bigger synthetic dataset is still synthetic, not an approved real data source.

**Engineering work this repo can do:**
- Keep the same evidence-retrieval contract (deterministic selection,
  citation validation, read-only authority per
  [ADR 0001](decisions/0001-read-only-authority.md)) but point it at a real
  core-banking read API instead of PostgreSQL fixtures.
- Contract tests against the bank's sandbox/staging API so the deterministic
  control layer is verified against real response shapes before any
  production credential exists.
- Replace synthetic policy fixtures with the bank's actual, versioned policy
  content, keeping the same provenance/citation requirement so an answer
  without a traceable source still fails closed.

**Not closable by engineering alone:** approved API access to core banking
systems, a data-sharing agreement, and a data-classification sign-off on
which fields the assistant may read.

**Exit criteria:** zero synthetic fixtures remain on the production code
path; every evidence source is traceable to an approved system of record.

## 4. Bank legal, risk, privacy, and compliance approval

This stage is approval of what is already built and documented, not new
engineering.

**What already exists as submission input:**
[`docs/system-card.md`](system-card.md),
[`docs/threat-model.md`](threat-model.md),
[`docs/compliance-mapping.md`](compliance-mapping.md) (explicitly marked
*engineering interpretation only*),
[`docs/privacy-data-lifecycle.md`](privacy-data-lifecycle.md),
[`docs/escalation-matrix.md`](escalation-matrix.md), and
[`SECURITY.md`](../SECURITY.md).

**What remains:** formal legal sign-off mapping the compliance-mapping table
to the bank's actual obligations and internal policy; a DPIA/PIA under APP
11; AML/CTF and responsible-lending sign-off consistent with the AUSTRAC and
ASIC RG 209 rows already flagged in
[`docs/compliance-mapping.md`](compliance-mapping.md); and a model-risk
management (MRM) submission.

**Not closable by engineering at all.** This requires the bank's own legal,
risk, privacy, and compliance functions to review and formally accept the
documents above — no repository change substitutes for that decision.

## 5. Production infrastructure: secrets, monitoring, DR, incident response

The [system card](system-card.md#known-limitations) already states this
plainly: no production rate limiting, high availability, disaster recovery,
or SIEM today; [the incident runbook](runbooks/incident-response.md) is
explicitly "not an APRA, OAIC, AUSTRAC, ASIC, or bank incident procedure."

**Engineering work this repo can do:**
- Replace `.env`-based local secrets with a secrets-manager-backed config
  loader (Vault/KMS-class), so no credential is ever committed or shipped in
  an image layer.
- Rate limiting and structured, redaction-first observability
  (building on the redaction rules already enforced in
  [`docs/privacy-data-lifecycle.md`](privacy-data-lifecycle.md)) with export
  to the bank's SIEM.
- An HA topology for PostgreSQL and a DR runbook that extends
  [`docs/runbooks/incident-response.md`](runbooks/incident-response.md)
  with real recovery-time/point objectives, once a hosting decision exists.

**Not closable by engineering alone:** the bank's actual hosting/cloud
decision, its secrets platform, SOC/SIEM ownership, on-call rotation, and a
signed business-continuity plan.

**Exit criteria:** the "known limitations" bullet on rate limiting, HA, DR,
and SIEM in [`docs/system-card.md`](system-card.md#known-limitations) is
retired, with evidence linked from this roadmap.

## 6. Independent security testing, UAT, model-risk validation, controlled pilot

The current evaluation gate is a fixed, deterministic, repo-internal corpus:
48 cases, thresholds defined in
[`docs/evaluation-rubric.md`](evaluation-rubric.md). That corpus proves the
committed code meets its own declared gates — it is not independent
verification.

**Engineering work this repo can do:** grow the adversarial corpus with
findings from UAT and pentest, publish a scoped test-environment/rules doc
for an external penetration test, and instrument model-risk metrics
(escalation precision/recall, refusal rate, drift against the golden corpus)
so an MRM committee has real evidence to review.

**Not closable by engineering alone:** a third-party independent penetration
test, UAT with actual bank staff, model-risk-management committee sign-off,
and an accountable executive's go/no-go decision on a controlled pilot
cohort with a rollback plan. None of these can be self-certified from inside
a coding session.

## What this document is not

It is not a project plan with dates, not a compliance certification, and not
an implementation of stages 2–6 — those stages are mostly gated on decisions
and approvals that belong to the bank, not to this repository. It exists so
that the engineering-closable portion of each stage is tracked in the same
place as the controls it depends on, and so the organizational-only items are
never mistaken for something a future commit could resolve.
