# Responsible AI Banking Agent

Responsible AI Banking Agent is a **synthetic, human-supervised reference
application** for testing safe banking-assistant controls. It answers verified
general questions and authorised read-only account questions, then routes
regulated, high-impact, uncertain, or unsupported requests to a human workflow.

> Status: initial reference implementation candidate. This repository is not a
> bank system, legal opinion, compliance certification, production deployment,
> or evidence that an AI system is safe for real customers.

## Authority boundary

The application may:

- explain versioned synthetic product and process information;
- read the authenticated synthetic customer's permitted account facts;
- explain clearly identified synthetic transactions;
- create an escalation record and reviewer handoff.

It never moves money, changes customer or account data, approves credit,
determines fraud, gives personalised financial advice, bypasses verification,
or makes a final hardship, legal, regulatory, or policy-exception decision.

## Deterministic control flow

```text
authenticate -> redact -> classify -> authorise -> retrieve verified evidence
-> draft bounded response -> validate authority and citations -> answer/escalate
-> append audit event
```

Risk, authorisation, evidence selection, escalation, and audit are deterministic.
The default reasoning provider is a deterministic stub. An optional OpenAI
Responses API adapter may improve wording from redacted and authorised evidence,
but it cannot lower risk, widen access, choose tools, or change disposition.

## Planned local stack

- Python 3.12, FastAPI, Pydantic, Jinja2
- PostgreSQL 16 with separate migration and restricted application roles
- synthetic fixtures and versioned policy documents
- Docker and GitHub Actions
- private GHCR pre-release images with provenance and SBOM attestations

See [the system card](docs/system-card.md),
[architecture](docs/architecture.md), and
[threat model](docs/threat-model.md) for the controlled scope.

## Evidence language

Repository tests can establish only that this synthetic implementation met its
declared test gates at a specific commit. They cannot establish legal compliance,
production readiness, model fitness, or approval for banking use.

No open-source licence has been selected. All rights are reserved unless the
owner makes a separate licensing decision.
