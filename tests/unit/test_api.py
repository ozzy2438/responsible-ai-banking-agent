from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from responsible_banking_agent.api import create_app
from responsible_banking_agent.config import Settings
from responsible_banking_agent.identity import IdentityStore
from responsible_banking_agent.models import AssistResponse, EscalationRoute
from responsible_banking_agent.rate_limit import InMemoryRateLimiter, RateLimiter
from responsible_banking_agent.repository import AccountRecord, TransactionRecord

ALICE_ID = UUID("11111111-1111-4111-8111-111111111111")
BOB_ID = UUID("22222222-2222-4222-8222-222222222222")
ACCOUNT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


class FakeRepository:
    def __init__(self) -> None:
        self.responses: dict[tuple[UUID, str], AssistResponse] = {}
        self.actions: list[dict[str, Any]] = []

    def ready(self) -> bool:
        return True

    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None:
        if actor_id != ALICE_ID or account_id != ACCOUNT_ID:
            return None
        return AccountRecord(account_id, "Synthetic Everyday", "AUD", "1250.50", datetime.now(UTC))

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]:
        del actor_id, account_id, limit
        return []

    def persist_response(self, **kwargs: Any) -> AssistResponse:
        key = (kwargs["actor_id"], kwargs["idempotency_key"])
        return self.responses.setdefault(key, kwargs["response"])

    def get_request(self, actor_id: UUID, request_id: UUID) -> AssistResponse | None:
        return next(
            (
                response
                for (owner, _), response in self.responses.items()
                if owner == actor_id and response.request_id == request_id
            ),
            None,
        )

    def list_escalations(self) -> list[dict[str, Any]]:
        return [
            {
                "id": UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
                "request_id": uuid4(),
                "route": "customer_service",
                "status": "open",
                "summary": "Synthetic review case",
                "redacted_message": "Help with my account",
                "risk_level": "HIGH",
            }
        ]

    def record_review_action(
        self,
        *,
        escalation_id: UUID,
        actor_id: UUID,
        action: str,
        route: EscalationRoute | None,
        reason: str,
    ) -> None:
        self.actions.append(
            {
                "escalation_id": escalation_id,
                "actor_id": actor_id,
                "action": action,
                "route": route,
                "reason": reason,
            }
        )


def _identities() -> IdentityStore:
    return IdentityStore(
        {
            "alice": {
                "token": "alice-test-token",
                "actor_id": str(ALICE_ID),
                "role": "customer",
                "display_name": "Alice",
            },
            "bob": {
                "token": "bob-test-token",
                "actor_id": str(BOB_ID),
                "role": "customer",
                "display_name": "Bob",
            },
            "reviewer": {
                "token": "reviewer-test-token",
                "actor_id": "33333333-3333-4333-8333-333333333333",
                "role": "reviewer",
                "display_name": "Riley",
            },
            "compliance": {
                "token": "compliance-test-token",
                "actor_id": "44444444-4444-4444-8444-444444444444",
                "role": "compliance",
                "display_name": "Casey",
            },
        }
    )


def _client(
    repository: FakeRepository | None = None,
    *,
    rate_limiter: RateLimiter | None = None,
    max_request_body_bytes: int = 16_384,
) -> tuple[TestClient, FakeRepository]:
    repository = repository or FakeRepository()
    settings = Settings(
        app_env="test",
        identity_provider="simulated",
        reasoning_provider="stub",
        database_url="postgresql://unused",
        migration_database_url="",
        app_db_password="",
        identities_file=Path("unused"),
        policy_bundle_path=Path("policies"),
        openai_api_key=None,
        openai_model=None,
        session_cookie_secure=False,
        max_request_body_bytes=max_request_body_bytes,
    )
    return (
        TestClient(
            create_app(
                settings,
                repository,
                _identities(),
                rate_limiter=rate_limiter,
            )
        ),
        repository,
    )


def test_authentication_idempotency_isolation_and_security_headers() -> None:
    client, _ = _client()
    unauthenticated = client.post(
        "/v1/assist",
        headers={"Idempotency-Key": "test-key-123"},
        json={"message": "What are branch opening hours?"},
    )
    assert unauthenticated.status_code == 401

    headers = {"Authorization": "Bearer alice-test-token", "Idempotency-Key": "same-key-123"}
    first = client.post(
        "/v1/assist", headers=headers, json={"message": "What are branch opening hours?"}
    )
    second = client.post(
        "/v1/assist", headers=headers, json={"message": "What are branch opening hours?"}
    )
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.headers["x-frame-options"] == "DENY"
    assert first.headers["cache-control"] == "no-store"

    request_id = first.json()["request_id"]
    alice_get = client.get(
        f"/v1/requests/{request_id}", headers={"Authorization": "Bearer alice-test-token"}
    )
    bob_get = client.get(
        f"/v1/requests/{request_id}", headers={"Authorization": "Bearer bob-test-token"}
    )
    assert alice_get.status_code == 200
    assert bob_get.status_code == 404


def test_review_endpoints_enforce_role_and_csrf() -> None:
    client, repository = _client()
    customer = client.get(
        "/v1/reviewer/escalations", headers={"Authorization": "Bearer alice-test-token"}
    )
    reviewer = client.get(
        "/v1/reviewer/escalations", headers={"Authorization": "Bearer reviewer-test-token"}
    )
    assert customer.status_code == 403
    assert reviewer.status_code == 200

    login = client.post("/dev/login", json={"alias": "reviewer"})
    assert login.status_code == 204
    assert login.cookies.get("session_token") == "reviewer-test-token"
    page = client.get("/review/escalations")
    assert page.status_code == 200
    csrf = client.cookies.get("csrf_token")
    assert csrf

    escalation_id = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    rejected = client.post(
        f"/review/escalations/{escalation_id}/actions",
        data={"action": "acknowledge", "reason": "Reviewed", "csrf": "wrong"},
    )
    accepted = client.post(
        f"/review/escalations/{escalation_id}/actions",
        data={"action": "acknowledge", "reason": "Reviewed", "csrf": csrf},
        follow_redirects=False,
    )
    assert rejected.status_code == 403
    assert accepted.status_code == 303
    assert repository.actions[-1]["action"] == "acknowledge"


def test_health_readiness_and_validation_failures() -> None:
    client, _ = _client()
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
    missing_key = client.post(
        "/v1/assist",
        headers={"Authorization": "Bearer alice-test-token"},
        json={"message": "What are branch opening hours?"},
    )
    assert missing_key.status_code == 422
    route_without_target = client.post(
        "/v1/reviewer/escalations/eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee/actions",
        headers={"Authorization": "Bearer reviewer-test-token"},
        json={"action": "route", "reason": "Route this case"},
    )
    assert route_without_target.status_code == 422

    validation_secret = "must-not-be-echoed-123"
    invalid = client.post(
        "/v1/assist",
        headers={"Authorization": "Bearer alice-test-token", "Idempotency-Key": "invalid-1"},
        json={"message": 123, "unexpected": validation_secret},
    )
    assert invalid.status_code == 422
    assert validation_secret not in invalid.text


def test_request_boundary_enforces_ids_hosts_body_limits_and_rate_limits() -> None:
    limiter = InMemoryRateLimiter(requests=2, window_seconds=60, clock=lambda: 100.0)
    client, _ = _client(rate_limiter=limiter, max_request_body_bytes=4096)
    headers = {"Authorization": "Bearer alice-test-token", "Idempotency-Key": "rate-key-1"}

    first = client.post(
        "/v1/assist",
        headers={**headers, "X-Request-ID": "not-a-uuid"},
        json={"message": "What are branch opening hours?"},
    )
    second = client.post(
        "/v1/assist",
        headers={**headers, "Idempotency-Key": "rate-key-2"},
        json={"message": "What are branch opening hours?"},
    )
    limited = client.post(
        "/v1/assist",
        headers={**headers, "Idempotency-Key": "rate-key-3"},
        json={"message": "What are branch opening hours?"},
    )
    assert first.status_code == 200
    UUID(first.headers["X-Request-ID"])
    assert second.status_code == 200
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"

    oversized_client, _ = _client(max_request_body_bytes=4096)
    oversized = oversized_client.post(
        "/v1/assist",
        headers=headers,
        json={"message": "x" * 5000},
    )
    assert oversized.status_code == 413

    invalid_host = oversized_client.get("/healthz", headers={"Host": "evil.example"})
    assert invalid_host.status_code == 400


def test_landing_and_static_assets_are_public() -> None:
    client, _ = _client()
    landing = client.get("/")
    assert landing.status_code == 200
    assert "Alice Example" in landing.text
    assert landing.headers["content-security-policy"] == (
        "default-src 'self'; style-src 'self' 'unsafe-inline'"
    )

    script = client.get("/static/landing.js")
    assert script.status_code == 200
    assert "/dev/login" in script.text


def test_demo_page_requires_sign_in_and_reflects_known_account() -> None:
    client, _ = _client()
    signed_out = client.get("/demo", follow_redirects=False)
    assert signed_out.status_code == 303
    assert signed_out.headers["location"] == "/"

    client.post("/dev/login", json={"alias": "alice"})
    alice_demo = client.get("/demo")
    assert alice_demo.status_code == 200
    assert str(ACCOUNT_ID) in alice_demo.text

    client.cookies.clear()
    client.post("/dev/login", json={"alias": "reviewer"})
    reviewer_demo = client.get("/demo")
    assert reviewer_demo.status_code == 200
    assert str(ACCOUNT_ID) not in reviewer_demo.text
