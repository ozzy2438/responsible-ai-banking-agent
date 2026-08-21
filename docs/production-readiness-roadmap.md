# Production Readiness Roadmap

> **Planning artifact, not a compliance or security sign-off.** It records
> what is already built, what remains, and — for each remaining item —
> whether it is something a future engineering change in this repository can
> close, or something only the bank's own legal, risk, privacy, security, and
> executive functions can close. No item in the second category can be
> satisfied by a commit.

## Where this sits

`v1.0.0` is the stable synthetic-data-only portfolio release line. Its
controlled publication workflow reruns CI and security scanning, then binds
an SBOM and provenance attestations to the exact image digest. That is evidence
about the tested artifact. It is not a production deployment, legal approval,
or compliance finding — see
[the evidence language in the README](../README.md#evidence-language) and
[known limitations in the system card](system-card.md#known-limitations).

## Status summary

| # | Stage | Type | Status |
|---|---|---|---|
| 1 | Reconcile RC2 release fixes onto the trunk branch | Engineering | Done — see below |
| 2 | Real identity provider and strong customer authentication | Engineering + external | Generic adapter complete; bank selection/review pending |
| 3 | Approved real bank system and data integrations | Engineering + external | Generic adapter complete; real contract/access pending |
| 4 | Bank legal, risk, privacy, and compliance approval | Organizational | Not started |
| 5 | Production infrastructure: secrets, monitoring, DR, incident response | Engineering + organizational | Security foundations complete; platform/HA/DR/SIEM pending |
| 6 | Independent security testing, UAT, model-risk validation, controlled pilot | External + organizational | Scope/checklists ready; external execution pending |

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

PR #10 merged those three commits through normal review. Its
`.github/workflows/release.yml`, `README.md`, and `docs/delivery.md` reconciled
the published `v0.1.0-rc.2` state onto `main`; the drift is closed.

**Prevention:** treat a pushed release tag as a signal to check that the tag
commit is reachable from `main`, not just that the tag exists. A branch
protection rule requiring release-workflow changes to land via reviewed PR
(no direct pushes to feature branches post-merge) would have caught this
automatically.

## 2. Real identity provider and strong customer authentication

Local/test identity remains a secure cookie or bearer token minted by
`POST /dev/login`. Production-like startup now rejects that path and requires
the vendor-neutral OIDC adapter described in
[`production-configuration.md`](production-configuration.md).

**Engineering foundation implemented:** pluggable identity selection;
issuer/audience/JWKS validation; asymmetric algorithm allow-list; controlled
actor/role claims; role-specific OAuth scopes; reviewer/compliance ACR step-up;
and generic authentication failure without token or provider detail leakage.
There is no fallback to simulated identity outside local/test.

**Not closable by engineering alone:** which IdP/SCA method the bank actually
runs, the customer consent and re-authentication policy, and acceptance of
the adapter by the bank's identity and security teams.

**Exit criteria:** no simulated-identity code path is reachable in a
production build; an independent auth review has signed off the adapter.

## 3. Approved real bank system and data integrations

All configured account, transaction, and policy data today are synthetic fixtures with a
committed manifest hash ([`docs/policy-source-register.md`](policy-source-register.md)).
A larger, deterministic synthetic dataset now exists
([`docs/synthetic-data.md`](synthetic-data.md)) for engineering confidence and
demos at scale — it strengthens this stage's testing but does not close it: a
bigger synthetic dataset is still synthetic, not an approved real data source.

**Engineering foundation implemented:** a separate read-only HTTPS+mTLS bank
adapter with bounded timeouts, no redirects, strict response schemas,
customer/account equality checks, source-system/version citations, and safe
escalation for unavailable or conflicting evidence. Mock contract tests exist;
no real bank endpoint or credential is configured.

**Engineering still requiring an external sandbox:** run the same contract
suite against the selected bank staging API and replace synthetic policy
fixtures with approved, versioned bank policy content.

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

The [system card](system-card.md#known-limitations) states the remaining gap:
the generic controls are not connected to an approved ingress, secrets
platform, HA database, disaster-recovery process, SIEM, SOC, or on-call team.
The [incident runbook](runbooks/incident-response.md) is explicitly not an
APRA, OAIC, AUSTRAC, ASIC, or bank incident procedure.

**Engineering foundation implemented:** fixed mounted-secret loading for
production-like environments; explicit hosts and request-body bounds;
HMAC-pseudonymised IP/actor rate limits through a function-only PostgreSQL
store; request IDs; security headers; and allow-listed JSON request logs.

**Engineering still requiring platform decisions:** export logs to the bank's
SIEM and implement an HA topology for PostgreSQL and a DR runbook that extends
[`docs/runbooks/incident-response.md`](runbooks/incident-response.md) with real
recovery-time/point objectives, once a hosting decision exists.

**Not closable by engineering alone:** the bank's actual hosting/cloud
decision, its secrets platform, SOC/SIEM ownership, on-call rotation, and a
signed business-continuity plan.

**Exit criteria:** selected-platform load/failover evidence, secrets rotation,
SIEM alert validation, tested restore/failover with approved RTO/RPO, and named
operational owners are linked from this roadmap.

## 6. Independent security testing, UAT, model-risk validation, controlled pilot

The current evaluation gate is a fixed, deterministic, repo-internal corpus:
48 cases, thresholds defined in
[`docs/evaluation-rubric.md`](evaluation-rubric.md). That corpus proves the
committed code meets its own declared gates — it is not independent
verification.

**Engineering preparation implemented:** the extended synthetic corpus,
[`security-test-scope.md`](security-test-scope.md),
[`model-risk-monitoring.md`](model-risk-monitoring.md),
[`pilot-readiness-checklist.md`](pilot-readiness-checklist.md), and
[`assurance-handoff.md`](assurance-handoff.md) define scope, stop conditions,
baseline blocking metrics, required evidence, owners, and pilot gates. Findings
from real UAT/pentest must later become regression cases without weakening the
fixed golden corpus.

**Not closable by engineering alone:** a third-party independent penetration
test, UAT with actual bank staff, model-risk-management committee sign-off,
and an accountable executive's go/no-go decision on a controlled pilot
cohort with a rollback plan. None of these can be self-certified from inside
a coding session.

## What this document is not

It is not a project plan with dates or a compliance certification. Generic
engineering foundations for stages 2, 3, and 5 do not complete those stages;
they remain gated on decisions and approvals that belong to the bank. It
exists so that the engineering-closable portion of each stage is tracked in
the same place as the controls it depends on, and so the organizational-only
items are never mistaken for something a future commit could resolve.
