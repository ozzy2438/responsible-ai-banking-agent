# ADR 0003: Production adapter boundaries

## Decision

Keep local/test simulated identity and synthetic data, but make every
production-like startup select vendor-neutral fail-closed adapters:

- OIDC access-token validation with asymmetric JWKS verification, explicit
  issuer/audience, controlled UUID/role claims, OAuth scopes, and reviewer ACR;
- an HTTPS+mTLS read-only bank API with strict schema and scope agreement;
- fixed mounted-secret files, PostgreSQL-backed rate limits, explicit hosts,
  bounded bodies, and allow-listed structured request metadata.

No adapter may fall back to a local provider after startup or runtime failure.

## Consequences

The repository can prepare and test integration boundaries without inventing a
bank's IdP, API, consent policy, hosting platform, or operational approval. A
real deployment remains blocked until the assurance-handoff owners supply and
accept those external contracts.
