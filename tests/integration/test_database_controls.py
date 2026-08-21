import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
import pytest

from responsible_banking_agent.config import Settings
from responsible_banking_agent.database import migrate
from responsible_banking_agent.models import AssistResponse, Disposition, EscalationRoute, RiskLevel
from responsible_banking_agent.repository import Repository

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


def test_migrations_repeat_and_app_role_is_restricted() -> None:
    settings = _settings()
    migrate(settings)
    migrate(settings)
    alice = UUID("11111111-1111-4111-8111-111111111111")
    alice_account = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    bob = UUID("22222222-2222-4222-8222-222222222222")
    repository = Repository(settings.database_url)
    assert repository.get_authorized_account(alice, alice_account) is not None
    assert repository.get_authorized_account(bob, alice_account) is None
    with psycopg.connect(settings.database_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("SELECT * FROM accounts").fetchall()
        connection.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("UPDATE accounts SET available_balance = 0")
        connection.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(
                "INSERT INTO transactions("
                "id, account_id, description, amount, booked_at, updated_at"
                ") "
                "VALUES (%s, %s, 'forbidden', 1, now(), now())",
                (uuid4(), alice_account),
            )


def _response() -> AssistResponse:
    return AssistResponse(
        request_id=uuid4(),
        risk_level=RiskLevel.LOW,
        disposition=Disposition.ANSWERED,
        answer="Synthetic response",
        verified_facts=[],
        citations=[],
        uncertainty=[],
        next_steps=[],
    )


def test_concurrent_idempotency_and_append_only_audit() -> None:
    settings = _settings()
    migrate(settings)
    repository = Repository(settings.database_url)
    alice = UUID("11111111-1111-4111-8111-111111111111")
    idempotency_key = f"concurrent-{uuid4()}"

    def persist(_: int) -> AssistResponse:
        return repository.persist_response(
            response=_response(),
            actor_id=alice,
            idempotency_key=idempotency_key,
            redacted_message="What are branch opening hours?",
            route=None,
            escalation_summary="No escalation",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(persist, range(8)))
    request_ids = {result.request_id for result in results}
    assert len(request_ids) == 1

    request_id = request_ids.pop()
    with psycopg.connect(settings.migration_database_url) as connection:
        request_count = connection.execute(
            "SELECT count(*) FROM assist_requests WHERE actor_id = %s AND idempotency_key = %s",
            (alice, idempotency_key),
        ).fetchone()
        audit_count = connection.execute(
            "SELECT count(*) FROM audit_events WHERE request_id = %s", (request_id,)
        ).fetchone()
        assert request_count and request_count[0] == 1
        assert audit_count and audit_count[0] == 1
        with pytest.raises(psycopg.errors.RaiseException, match="immutable record"):
            connection.execute(
                "UPDATE audit_events SET event_type = 'tampered' WHERE request_id = %s",
                (request_id,),
            )
        connection.rollback()
        with pytest.raises(psycopg.errors.RaiseException, match="immutable record"):
            connection.execute("DELETE FROM audit_events WHERE request_id = %s", (request_id,))


def test_review_actions_are_controlled_and_immutable() -> None:
    settings = _settings()
    migrate(settings)
    repository = Repository(settings.database_url)
    alice = UUID("11111111-1111-4111-8111-111111111111")
    reviewer = UUID("33333333-3333-4333-8333-333333333333")
    response = _response().model_copy(
        update={
            "risk_level": RiskLevel.HIGH,
            "disposition": Disposition.ESCALATED,
            "escalation_id": uuid4(),
        }
    )
    stored = repository.persist_response(
        response=response,
        actor_id=alice,
        idempotency_key=f"review-{uuid4()}",
        redacted_message="Approve my loan",
        route=EscalationRoute.LENDING_SPECIALIST,
        escalation_summary="Human lending review required",
    )
    assert stored.escalation_id
    repository.record_review_action(
        escalation_id=stored.escalation_id,
        actor_id=reviewer,
        action="route",
        route=EscalationRoute.LENDING_SPECIALIST,
        reason="Specialist review required",
    )
    queue = repository.list_escalations()
    assert any(item["id"] == str(stored.escalation_id) for item in queue)

    with (
        psycopg.connect(settings.migration_database_url) as connection,
        pytest.raises(psycopg.errors.RaiseException, match="immutable record"),
    ):
        connection.execute(
            "UPDATE review_actions SET reason = 'tampered' WHERE escalation_id = %s",
            (stored.escalation_id,),
        )


def test_rate_limit_state_is_function_only_and_concurrency_safe() -> None:
    settings = _settings()
    migrate(settings)
    subject_hash = "a" * 64
    route_group = f"test-{uuid4()}"

    def consume(_: int) -> bool:
        with psycopg.connect(settings.database_url) as connection:
            row = connection.execute(
                "SELECT consume_rate_limit(%s, %s, %s, %s)",
                (subject_hash, route_group, 4, 60),
            ).fetchone()
        assert row is not None
        return bool(row[0])

    with ThreadPoolExecutor(max_workers=8) as pool:
        decisions = list(pool.map(consume, range(8)))
    assert sum(decisions) == 4

    with psycopg.connect(settings.database_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("SELECT * FROM rate_limit_buckets").fetchall()
        connection.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(
                "INSERT INTO rate_limit_buckets VALUES (%s, %s, now(), 1)",
                ("b" * 64, route_group),
            )
