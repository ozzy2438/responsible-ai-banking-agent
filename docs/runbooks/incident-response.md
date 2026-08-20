# Synthetic Reference Incident Runbook

1. Stop publishing new images and preserve the exact commit and workflow evidence.
2. Disable the optional provider and run in deterministic stub mode.
3. Classify whether confidentiality, integrity, availability, audit, or authority
   controls failed; do not place sensitive details in a public issue.
4. Preserve redacted logs, request IDs, image digest, policy manifest, and test output.
5. Route the event to the repository owner and appropriate security/privacy reviewer.
6. Add a failing regression test before remediation.
7. Re-run all gates and obtain independent review before any later promotion.

This runbook is not an APRA, OAIC, AUSTRAC, ASIC, or bank incident procedure.
