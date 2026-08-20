# Threat Model

## Protected assets

- customer identity and synthetic account/transaction facts;
- authentication tokens and provider credentials;
- policy integrity and provenance;
- escalation and audit integrity;
- release image provenance.

## Primary threats and controls

| Threat | Control | Verification |
|---|---|---|
| Cross-customer access | Server-derived actor plus ownership check and 404 response | API and direct-role tests |
| Prompt injection | No model tools; deterministic evidence and disposition | Adversarial golden cases |
| Secret submission | Pre-persistence redaction and log filtering | Redaction and persistence tests |
| Invented banking facts | Versioned evidence plus citation validator | Unsupported-claim tests |
| Autonomous high-impact decision | Deterministic high-risk escalation | 100% high-risk gate |
| Replay or duplicate request | Required idempotency key and database uniqueness | Concurrent integration test |
| Audit alteration | Privileges plus database trigger | Direct-role update/delete probes |
| Supply-chain compromise | Pinned actions, audits, SBOM, provenance attestation | CI and attestation verification |

## Explicit residual risk

Keyword and pattern classification is not a production-grade intent classifier.
Synthetic identities are not production authentication. Local cookies and the
review UI are for demonstration only. Regulatory mappings require independent
legal, compliance, privacy, security, accessibility, and operational review.
