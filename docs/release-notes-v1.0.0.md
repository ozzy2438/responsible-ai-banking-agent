## v1.0.0 — portfolio reference release

Responsible AI Banking Agent is a synthetic, human-supervised banking
assistant reference implementation. Deterministic code—not a language model—
controls risk classification, authorisation, privacy redaction, evidence
validation, and mandatory escalation.

### Highlights

- One-command, loopback-only Docker Compose demo with PostgreSQL 16 and four
  synthetic identities.
- Customer assistant flows for cited LOW-risk FAQs, authorised MEDIUM-risk
  account questions, mandatory HIGH-risk escalation, and prompt-injection
  resistance.
- Human-review console with controlled acknowledge, allow-listed route, and
  close transitions backed by immutable audit records.
- 96 automated tests, including a fixed 48-case adversarial banking-safety
  corpus and real PostgreSQL permission/isolation checks.
- 11 blocking CI gates covering formatting, strict typing, tests, Compose
  smoke/restart, dependency and secret audits, static analysis, and
  filesystem/container vulnerability scanning.
- Digest-pinned public GHCR image with no `latest` tag, SPDX JSON SBOM, and
  GitHub build-provenance and SBOM attestations.

### Important boundaries

This is a public portfolio reference release, not a production banking
deployment or compliance certification. It uses synthetic data only, has no
real-bank integration, does not move money, and cannot autonomously approve
credit, decide fraud, or resolve hardship. See the README and production
readiness roadmap for the controls a real deployment would still require.

The release workflow appends the exact OCI digest, immutable tags, and SBOM
asset details below after all blocking gates and published-digest smoke tests
pass.
