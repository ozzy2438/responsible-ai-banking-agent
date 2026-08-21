# Synthetic Reference Incident Runbook

1. Stop publishing new images and preserve the exact commit and workflow evidence.
2. Disable the optional provider and run in deterministic stub mode.
3. Classify whether confidentiality, integrity, availability, audit, or authority
   controls failed; do not place sensitive details in a public issue.
4. Preserve redacted logs, request IDs, image digest, policy manifest, and test output.
5. Route the event to the repository owner and appropriate security/privacy reviewer.
6. Add a failing regression test before remediation.
7. Re-run all gates and obtain independent review before any later promotion.

## Production-foundation signals

- Repeated OIDC failures: preserve request IDs and issuer availability evidence;
  never capture tokens. Disable the affected external route and contact the
  bank identity owner.
- Bank API contract/scope failure: keep the assistant fail-closed, preserve the
  normalised error category and source version, and contact the bank API owner.
- Rate-limit store failure: return 503 rather than bypassing the limiter. Restore
  the approved PostgreSQL service before accepting protected traffic.
- Suspected secret exposure: revoke/rotate at the external secrets platform,
  preserve only redacted evidence, and rebuild any affected image/runtime.
- Log pipeline/SIEM outage: do not claim monitoring coverage. Follow the bank's
  approved service-degradation policy once one exists.

This runbook is not an APRA, OAIC, AUSTRAC, ASIC, or bank incident procedure.
