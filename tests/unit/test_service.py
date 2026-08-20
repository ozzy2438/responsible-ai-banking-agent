from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from responsible_banking_agent.models import (
    Actor,
    AssistRequest,
    AssistResponse,
    ReasoningDraft,
    RiskAssessment,
    Role,
    VerifiedFact,
)
from responsible_banking_agent.policies import PolicyStore
from responsible_banking_agent.reasoning.openai_adapter import ProviderOutputError
from responsible_banking_agent.reasoning.stub import DeterministicStub
from responsible_banking_agent.repository import AccountRecord, TransactionRecord
from responsible_banking_agent.service import BankingService


class MemoryRepository:
    def __init__(self) -> None:
        self.responses: dict[tuple[UUID, str], AssistResponse] = {}

    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None:
        if actor_id != UUID("11111111-1111-4111-8111-111111111111"):
            return None
        return AccountRecord(account_id, "Synthetic Everyday", "AUD", "1250.50", datetime.now(UTC))

    def persist_response(self, **kwargs: Any) -> AssistResponse:
        key = (kwargs["actor_id"], kwargs["idempotency_key"])
        return self.responses.setdefault(key, kwargs["response"])

    def get_request(self, actor_id: UUID, request_id: UUID) -> AssistResponse | None:
        return next(
            (
                value
                for (owner, _), value in self.responses.items()
                if owner == actor_id and value.request_id == request_id
            ),
            None,
        )

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]:
        del account_id, limit
        if actor_id != UUID("11111111-1111-4111-8111-111111111111"):
            return []
        now = datetime.now(UTC)
        return [
            TransactionRecord(
                UUID("a1000000-0000-4000-8000-000000000001"),
                "Synthetic grocery",
                "-42.10",
                "AUD",
                now,
                now,
            )
        ]


def _actor() -> Actor:
    return Actor(
        actor_id=UUID("11111111-1111-4111-8111-111111111111"),
        role=Role.CUSTOMER,
        display_name="Alice",
    )


def test_low_answer_is_cited_and_idempotent() -> None:
    repository = MemoryRepository()
    service = BankingService(repository, PolicyStore(Path("policies")), DeterministicStub())
    first = service.assist(
        _actor(), AssistRequest(message="What are branch opening hours?"), "same-key"
    )
    second = service.assist(
        _actor(), AssistRequest(message="What are branch opening hours?"), "same-key"
    )
    assert first == second
    assert first.citations


def test_high_request_escalates_without_decision() -> None:
    service = BankingService(MemoryRepository(), PolicyStore(Path("policies")), DeterministicStub())
    response = service.assist(_actor(), AssistRequest(message="Approve my loan"), str(uuid4()))
    assert response.disposition.value == "escalated"
    assert "approved" not in response.answer.lower()


def test_secret_is_not_echoed() -> None:
    service = BankingService(MemoryRepository(), PolicyStore(Path("policies")), DeterministicStub())
    response = service.assist(_actor(), AssistRequest(message="PIN: 1234"), str(uuid4()))
    assert "1234" not in response.model_dump_json()


def test_authorised_transaction_is_returned_with_its_own_citation() -> None:
    service = BankingService(MemoryRepository(), PolicyStore(Path("policies")), DeterministicStub())
    response = service.assist(
        _actor(),
        AssistRequest(
            message="Explain my recent transaction",
            account_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ),
        str(uuid4()),
    )
    assert response.risk_level.value == "MEDIUM"
    assert any(citation.source_type == "transaction" for citation in response.citations)


class FailingProvider:
    def draft(
        self, message: str, assessment: RiskAssessment, facts: list[VerifiedFact]
    ) -> ReasoningDraft:
        del message, assessment, facts
        raise ProviderOutputError("mock provider failure")


def test_provider_failure_uses_safe_deterministic_fallback() -> None:
    service = BankingService(MemoryRepository(), PolicyStore(Path("policies")), FailingProvider())
    response = service.assist(
        _actor(), AssistRequest(message="What are branch opening hours?"), str(uuid4())
    )
    assert response.disposition.value == "answered"
    assert response.citations
