# Production Configuration Contract

This document describes startup gates implemented by the repository. It is not
a deployment guide or approval to connect a bank system.

## Fail-closed startup

`APP_ENV=staging` or `production` requires all of the following:

- `IDENTITY_PROVIDER=oidc` with HTTPS issuer and JWKS URLs, an audience, only
  `RS256`/`ES256`, UUID actor and controlled role claims, separate assist/review
  scopes, and a reviewer/compliance ACR value;
- `SECRET_SOURCE=files`; fixed lower-case files under `SECRETS_DIR` supply
  `database_url`, `bank_api_token`, `rate_limit_hmac_key`, and any optional
  `openai_api_key`;
- `BANK_DATA_PROVIDER=http` with an HTTPS base URL, CA bundle, client
  certificate/key, bearer credential, strict response contracts, no redirects,
  and a timeout no greater than ten seconds;
- `RATE_LIMIT_BACKEND=postgres` with a 32+ character HMAC key; raw IPs are not
  persisted;
- explicit `ALLOWED_HOSTS`, secure cookies, `LOG_FORMAT=json`, and a bounded
  request-body limit.

Missing or ambiguous values stop startup. Runtime identity, bank-evidence, and
rate-limit-store failures return a controlled authentication, escalation, or
503 response; they do not fall back to simulated identity, synthetic facts, or
an open limiter.

## External contract still required

Before a staging connection, the bank must provide and approve:

- issuer, audience, claim mapping, role/scope catalogue, assurance/step-up
  policy, token lifetime/revocation policy, and identity-owner contact;
- bank read-API schema matching the adapter contract, customer/account scope
  semantics, source-version rules, sandbox endpoint, CA and client identity;
- a secrets platform and mount mechanism, credential rotation process, ingress
  client-address contract, PostgreSQL topology, SIEM destination, and owners;
- data classification, consent/authority, retention, cross-border, incident,
  and operational approvals.

Do not place any of those real values in this public repository, an issue, a PR,
CI variables, or example files. Repository secrets are not automatically passed
to workflows, and CI makes no live bank or OpenAI call.

## Adapter evidence

Unit tests mock JWKS decoding and the HTTPS bank transport. PostgreSQL tests
exercise the rate-limit function through the restricted role and prove direct
table access is denied. These tests validate only the generic contract; the
selected bank systems still require sandbox contract testing and independent
review.
