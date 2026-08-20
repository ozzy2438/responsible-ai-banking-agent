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

## Local stack

- Python 3.12, FastAPI, Pydantic, Jinja2
- PostgreSQL 16 with separate migration and restricted application roles
- synthetic fixtures and versioned policy documents
- Docker and GitHub Actions
- public GHCR release-candidate images with provenance and SBOM attestations;
  no production image or `latest` tag

## Run locally

Python 3.12 and Docker are required. The local database and identities contain
synthetic data only.

```sh
python3.12 -m venv .venv
.venv/bin/pip install -e ".[test]"
make identities
docker compose up -d postgres
```

Copy `.env.example` values into your shell, then run:

```sh
.venv/bin/python -m responsible_banking_agent.database
.venv/bin/python -m uvicorn responsible_banking_agent.app:create_app \
  --factory --host 127.0.0.1 --port 8000
```

`POST /dev/login` is deliberately available only in `local` and `test`
environments. Bearer tokens generated in `.local/identities.json` are for local
testing and are ignored by Git. Non-local startup rejects simulated identity.

The optional OpenAI adapter is disabled by default. Enabling it requires
`REASONING_PROVIDER=openai`, an explicit `OPENAI_MODEL`, and
`OPENAI_API_KEY`. It receives only redacted, authorised facts, requests strict
structured output with storage disabled, and cannot alter classification,
authorisation, or escalation. Automated tests never make live model calls.

## Verify

```sh
make lint
make typecheck
make test
```

See [the system card](docs/system-card.md),
[architecture](docs/architecture.md), and
[threat model](docs/threat-model.md) for the controlled scope. See
[delivery controls](docs/delivery.md) for CI jobs, RC publication, SBOM, and
attestation verification. See the
[production readiness roadmap](docs/production-readiness-roadmap.md) for what
remains between this reference candidate and any real deployment.

## Evidence language

Repository tests can establish only that this synthetic implementation met its
declared test gates at a specific commit. They cannot establish legal compliance,
production readiness, model fitness, or approval for banking use.

No open-source licence has been selected. All rights are reserved unless the
owner makes a separate licensing decision.
