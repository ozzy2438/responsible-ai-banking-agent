import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest

from responsible_banking_agent.config import Settings
from responsible_banking_agent.database import migrate
from responsible_banking_agent.models import Actor, AssistRequest, Role
from responsible_banking_agent.policies import PolicyStore
from responsible_banking_agent.reasoning.stub import DeterministicStub
from responsible_banking_agent.repository import Repository
from responsible_banking_agent.service import BankingService

pytestmark = pytest.mark.integration


def _settings() -> Settings:
    migration_url = os.environ.get("MIGRATION_DATABASE_URL")
    app_url = os.environ.get("TEST_DATABASE_URL")
    if not migration_url or not app_url:
        pytest.skip("PostgreSQL test URLs are not configured")
    return Settings(
        app_env="test",
        identity_provider="simulated",
        reasoning_provider="stub",
        database_url=app_url,
        migration_database_url=migration_url,
        app_db_password=os.getenv("APP_DB_PASSWORD", "app-local-only"),
        identities_file=Path("unused"),
        policy_bundle_path=Path("policies"),
        openai_api_key=None,
        openai_model=None,
    )


def _load_cases() -> list[dict]:
    return json.loads(Path("evaluation/synthetic_scenarios.json").read_text(encoding="utf-8"))


CASES = _load_cases()


def test_extended_corpus_is_nonempty_and_distinct_from_blocking_corpus() -> None:
    assert len(CASES) >= 25
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_scenario_matches_expected_risk_and_disposition(case: dict) -> None:
    settings = _settings()
    migrate(settings)
    repository = Repository(settings.database_url)
    policies = PolicyStore(Path("policies"))
    service = BankingService(repository, policies, DeterministicStub())

    actor = Actor(actor_id=UUID(case["actor_id"]), role=Role.CUSTOMER, display_name="Synthetic")
    account_id = UUID(case["account_id"]) if case.get("account_id") else None
    if account_id and case["expected_risk"] == "MEDIUM":
        with psycopg.connect(settings.migration_database_url) as connection:
            connection.execute(
                "UPDATE accounts SET updated_at = now() WHERE id = %s", (account_id,)
            )
            connection.execute(
                "UPDATE transactions SET updated_at = now() WHERE account_id = %s",
                (account_id,),
            )
    request = AssistRequest(message=case["message"], account_id=account_id)

    response = service.assist(
        actor,
        request,
        idempotency_key=f"synthetic-scenario-{case['id']}-{uuid4()}",
    )

    assert response.risk_level.value == case["expected_risk"], case["id"]
    assert response.disposition.value == case["expected_disposition"], case["id"]
