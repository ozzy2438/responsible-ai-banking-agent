# Independent Security Test Scope

This is a proposed rules-of-engagement input. A contracted assessor and the
bank security owner must approve the final scope, dates, contacts, environment,
and stop conditions before testing.

## In scope

- OIDC validation: issuer/audience/algorithm confusion, JWKS rotation/failure,
  malformed claims, role/scope escalation, reviewer ACR bypass, and token size;
- API authorization: cross-customer IDs, reviewer endpoints, 401/403/404
  behaviour, CSRF, idempotency, body/host/rate-limit boundaries;
- evidence adapter: mTLS/CA enforcement, redirect and timeout handling, schema
  confusion, mismatched customer/account IDs, stale/conflicting evidence;
- database controls: app-role function allow-list, audit/review immutability,
  rate-limit table denial, search-path and concurrency attacks;
- privacy and injection: secret/card redaction, log/persistence leakage, prompt
  injection, citation/authority bypass, model/provider failures;
- container/supply chain: non-root/read-only execution, image vulnerabilities,
  SBOM/provenance verification, pinned workflow controls.

## Environment and data

Use a dedicated non-production environment and synthetic data only. Do not use
real customer records, production credentials, live payment rails, or a live
OpenAI call. Test identities and certificates must be purpose-created and
revoked afterward.

## Stop conditions

Stop immediately for evidence of cross-customer disclosure, secret leakage,
financial-record mutation, an autonomous high-impact decision, access outside
the agreed environment, or instability affecting another service. Notify the
named security contact through the approved private channel; do not open a
public issue with sensitive evidence.

## Required output

The final report must identify the exact commit/image digest, methods, limits,
findings and severity, reproduction with synthetic data, remediation owner,
retest result, residual risk, and explicit unresolved blockers. Critical/high
findings block any pilot.
