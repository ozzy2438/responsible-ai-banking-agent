PYTHON := .venv/bin/python

.PHONY: setup identities db-up migrate serve lint typecheck test verify db-down regenerate-synthetic-seed demo demo-down

setup:
	python3.12 -m venv .venv
	.venv/bin/pip install -e ".[test]"

identities:
	$(PYTHON) -m responsible_banking_agent.identity

db-up:
	docker compose up -d postgres

migrate:
	$(PYTHON) -m responsible_banking_agent.database

serve:
	$(PYTHON) -m uvicorn responsible_banking_agent.app:create_app --factory --host 127.0.0.1 --port 8000

lint:
	.venv/bin/ruff format --check .
	.venv/bin/ruff check .

typecheck:
	.venv/bin/mypy src

test:
	$(PYTHON) -m pytest

verify: lint typecheck test

db-down:
	docker compose down

regenerate-synthetic-seed:
	$(PYTHON) scripts/generate_synthetic_seed.py > migrations/0003_synthetic_seed_data.sql

# One-command synthetic demo: builds the app image, starts PostgreSQL,
# migrates the schema, seeds local demo identities, and serves on :8000.
# The loopback-only PostgreSQL state is ephemeral and recreated after `down`.
# Synthetic data only — see README.md#demonstration-scenarios.
demo:
	docker compose up --build

demo-down:
	docker compose down
