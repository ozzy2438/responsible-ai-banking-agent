# System Card

## Intended use

Support verified general banking explanations, authorised read-only synthetic
account questions, and complete human handoffs. The intended users are developers,
reviewers, and assurance practitioners evaluating control behaviour.

## Prohibited use

Real customer service, production banking, credit or fraud decisions, personalised
financial advice, identity verification, transaction execution, customer-record
changes, or regulatory reporting.

## Autonomy

Read-only assistance plus escalation. The only workflow writes are requests,
escalations, reviewer routing notes, and audit events. Financial data is immutable.

## Data

All fixtures are synthetic. Raw secrets and full payment-card credentials are
never intentionally stored. Redacted request content and structured outcomes are
retained only for the reference workflow.

## Reasoning

Deterministic stub by default. Optional OpenAI Responses API output is constrained
to a schema, receives no callable tools, and cannot override control decisions.
No live model call occurs in CI or the acceptance suite.

## Known limitations

- No real identity provider, consent system, core banking API, or records schedule.
- No production rate limiting, high availability, disaster recovery, or SIEM.
- Golden cases prove expected behaviour only for the committed corpus.
- Passing gates is not evidence of legal compliance or production fitness.
