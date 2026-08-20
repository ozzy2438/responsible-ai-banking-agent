# Privacy and Data Lifecycle

1. Accept only the minimum message and optional account identifier.
2. Authenticate before account lookup.
3. Detect and redact credentials and full card-like values before persistence.
4. Retrieve only facts authorised for the server-derived actor.
5. Send only redacted and necessary context to an optional reasoning provider.
6. Persist redacted content, outcome, provenance, escalation, and audit metadata.
7. Never include raw request text or financial facts in application logs.

The reference app does not define a production retention period. Before real use,
the bank must approve purpose, notices, consent or authority, retention, deletion,
de-identification, access/correction, cross-border processing, breach response,
and third-party terms.
