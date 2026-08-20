# Architecture

## Scope

V1 is a single-bank, synthetic reference app with a JSON API and a small
server-rendered reviewer console. There is no customer chat UI, external bank
connection, production identity provider, money movement, or cloud deployment.

## Components

```text
synthetic customer or reviewer
             |
             v
FastAPI authentication and request boundary
             |
             v
deterministic control service
  | redaction | risk | authorisation | evidence | validation | audit
  |               |                         |
  |               v                         v
  |       versioned policy bundle       PostgreSQL 16
  |
  +--> deterministic stub (default)
  +--> optional schema-constrained OpenAI adapter (no tools, store=false)
```

## Trust boundaries

- Identity and role come from a verified bearer token or local-only secure cookie.
- Account identifiers supplied by a client are re-authorised on every request.
- The model receives only redacted facts already selected by deterministic code.
- Model output is untrusted until schema, citation, and authority validation pass.
- Base financial tables are owned by the migration role. The app role receives
  only allow-listed function execution and bounded workflow permissions.
- Audit events are append-only and correlated by `request_id`.

## Failure behaviour

Missing identity, conflicting evidence, stale facts, provider failure, invalid
model output, unknown intent, and policy gaps fail closed. The customer receives
a concise limitation and next step; high-impact cases create a reviewer handoff.
