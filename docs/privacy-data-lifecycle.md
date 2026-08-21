# Privacy and Data Lifecycle

1. Accept only the minimum message and optional account identifier.
2. Authenticate before account lookup.
3. Detect and redact credentials and full card-like values before persistence.
4. Retrieve only facts authorised for the server-derived actor.
5. Send only redacted and necessary context to an optional reasoning provider.
6. Persist redacted content, outcome, provenance, escalation, and audit metadata.
7. Never include raw request text or financial facts in application logs.
8. Log only request ID, method, normalised route group, status, and duration.
9. Store only HMAC-pseudonymised rate-limit subjects; never store raw IP
   addresses in rate-limit records.
10. Read production-like credentials from fixed mounted-secret files; never
    return their contents or paths in API errors.

The reference app does not define a production retention period. Before real use,
the bank must approve purpose, notices, consent or authority, retention, deletion,
de-identification, access/correction, cross-border processing, breach response,
and third-party terms.

The OIDC and bank API adapters do not establish consent, collection authority,
retention, or cross-border approval. Those decisions remain external gates in
the production-readiness roadmap and assurance handoff.
