# Architecture

## Scope

V1 is a single-bank, synthetic reference app with a JSON API and a small
server-rendered reviewer console. Vendor-neutral production adapters exist but
no real identity provider, bank endpoint, credential, customer data, hosting
platform, or approval is configured. There is no customer chat UI, money
movement, or cloud deployment.

## Components

```text
synthetic identity (local/test) OR approved OIDC issuer (production-like)
             |
             v
FastAPI authentication, host/body/rate-limit, and request-id boundary
             |
             v
deterministic control service
  | redaction | risk | authorisation | evidence | validation | audit
  |               |                         |
  |               v                         v
  |       versioned policy bundle       PostgreSQL 16 workflow/audit
  |                                        |
  |                                        +--> shared rate-limit function
  |
  +--> synthetic facts (local/test)
  +--> HTTPS+mTLS read-only bank adapter (production-like, unconfigured)
  |
  +--> deterministic stub (default)
  +--> optional schema-constrained OpenAI adapter (no tools, store=false)
```

## Trust boundaries

- Local/test identity comes from a simulated token/cookie. Production-like
  identity requires signed OIDC tokens validated against pinned issuer,
  audience, asymmetric algorithms, JWKS, role scopes, and reviewer assurance.
- Production-like secrets come only from fixed mounted-secret filenames; the
  loader rejects symlinks and oversized or multiline values.
- Account identifiers supplied by a client are re-authorised on every request.
- The external bank adapter uses only HTTPS+mTLS, bounded timeouts, no redirects,
  strict response schemas, and customer/account identity agreement checks.
- The model receives only redacted facts already selected by deterministic code.
- Model output is untrusted until schema, citation, and authority validation pass.
- Base financial tables are owned by the migration role. The app role receives
  only allow-listed function execution and bounded workflow permissions.
- Audit events are append-only and correlated by `request_id`.
- Logs contain only an allow-list of request metadata and normalised route names;
  request bodies, authorization headers, account IDs, and raw IPs are excluded.

## Failure behaviour

Missing identity/scope/assurance, conflicting or unavailable bank evidence,
stale facts, rate-limit-store failure, provider failure, invalid model output,
unknown intent, and policy gaps fail closed. The customer receives a concise
limitation and next step; high-impact cases create a reviewer handoff.
