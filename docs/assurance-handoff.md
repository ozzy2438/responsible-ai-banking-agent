# Production Assurance Handoff

No item below is satisfied by repository tests alone. Each row requires a named
owner, dated decision, and evidence link in the bank's controlled system.

| Gate | Required owner | Minimum evidence | Current status |
|---|---|---|---|
| Identity and SCA | Bank identity/security | Issuer/claims/scopes/ACR mapping, revocation and independent auth review | Unassigned |
| Core-banking read API | API owner and data owner | Approved sandbox contract, mTLS identity, field classification, source-version rules | Unassigned |
| Privacy | Privacy officer | PIA/DPIA, notice/authority, retention, access/correction, cross-border decision | Unassigned |
| Legal and regulatory | Legal/compliance/AML/credit | Formal review of mappings and escalation obligations | Unassigned |
| Model risk | MRM committee | Intended-use approval, independent evaluation, thresholds, drift and change policy | Unassigned |
| Hosting and secrets | Platform/security | Architecture approval, secrets platform, key rotation and network controls | Unassigned |
| SOC/SIEM and incidents | SOC/operations | Log onboarding, alerts, on-call, severity matrix, notification workflow | Unassigned |
| Resilience | Service owner/BCM | HA design, tested backups, RTO/RPO, restore and failover evidence | Unassigned |
| Independent security | External assessor | Scoped penetration test and closed critical/high findings | Unassigned |
| UAT and pilot | Product/risk executive | Staff UAT, accessibility, pilot cohort, rollback and accountable go/no-go | Unassigned |

The repository owner may attach redacted engineering evidence to a submission,
but must not mark an external gate approved on behalf of these owners.
