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
| Forged or confused-deputy identity | OIDC issuer/audience/JWKS/asymmetric algorithm validation plus UUID role claims | OIDC unit tests |
| Authenticated but unauthorised role use | Role-appropriate OAuth scopes and reviewer ACR step-up | Identity contract tests |
| Compromised/misdirected bank response | HTTPS+mTLS, strict schemas, no redirects, identity/account equality checks | Adapter contract tests |
| Request flooding | HMAC-pseudonymised IP and actor limits; shared function-only PostgreSQL buckets | API and database tests |
| Log leakage | Normalised route groups and allow-listed structured metadata only | Formatter and API tests |
| Oversized request | ASGI body limit before model parsing | API boundary tests |
| Host-header abuse | Explicit trusted-host allow-list | API boundary tests |

## Explicit residual risk

Keyword and pattern classification is not a production-grade intent classifier.
The OIDC and bank adapters have no approved bank configuration or external
contract test environment. Local cookies and the review UI are for demonstration
only. The fixed-window limiter still depends on correct ingress client-address
handling and the selected PostgreSQL topology. Regulatory mappings require
independent legal, compliance, privacy, security, accessibility, and operational
review.
