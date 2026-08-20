from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .models import AssistResponse, EscalationRoute


@dataclass(frozen=True)
class AccountRecord:
    account_id: UUID
    account_name: str
    currency: str
    available_balance: str
    updated_at: datetime


@dataclass(frozen=True)
class TransactionRecord:
    transaction_id: UUID
    description: str
    amount: str
    currency: str
    booked_at: datetime
    updated_at: datetime


class BankingRepository(Protocol):
    def ready(self) -> bool: ...

    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None: ...

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]: ...

    def persist_response(
        self,
        *,
        response: AssistResponse,
        actor_id: UUID,
        idempotency_key: str,
        redacted_message: str,
        route: EscalationRoute | None,
        escalation_summary: str,
    ) -> AssistResponse: ...

    def get_request(self, actor_id: UUID, request_id: UUID) -> AssistResponse | None: ...

    def list_escalations(self) -> list[dict[str, Any]]: ...

    def record_review_action(
        self,
        *,
        escalation_id: UUID,
        actor_id: UUID,
        action: str,
        route: EscalationRoute | None,
        reason: str,
    ) -> None: ...


class Repository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ready(self) -> bool:
        try:
            with psycopg.connect(self.database_url) as connection:
                connection.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                "SELECT * FROM get_authorized_account(%s, %s)", (actor_id, account_id)
            ).fetchone()
        return AccountRecord(**row) if row else None

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            rows = connection.execute(
                "SELECT * FROM get_authorized_transactions(%s, %s, %s)",
                (actor_id, account_id, limit),
            ).fetchall()
        return [TransactionRecord(**row) for row in rows]

    def persist_response(
        self,
        *,
        response: AssistResponse,
        actor_id: UUID,
        idempotency_key: str,
        redacted_message: str,
        route: EscalationRoute | None,
        escalation_summary: str,
    ) -> AssistResponse:
        payload = response.model_dump(mode="json")
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                "SELECT persist_assist_response(%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)",
                (
                    response.request_id,
                    actor_id,
                    idempotency_key,
                    redacted_message,
                    response.risk_level.value,
                    response.disposition.value,
                    json.dumps(payload),
                    response.escalation_id,
                    route.value if route else None,
                    escalation_summary,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Database did not return the persisted response")
        return AssistResponse.model_validate(row[0])

    def get_request(self, actor_id: UUID, request_id: UUID) -> AssistResponse | None:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            row = connection.execute(
                "SELECT get_request_response(%s, %s) AS response_json",
                (actor_id, request_id),
            ).fetchone()
        return (
            AssistResponse.model_validate(row["response_json"])
            if row and row["response_json"]
            else None
        )

    def list_escalations(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            rows = connection.execute("SELECT item FROM list_escalations() AS item").fetchall()
        return [dict(row["item"]) for row in rows]

    def record_review_action(
        self,
        *,
        escalation_id: UUID,
        actor_id: UUID,
        action: str,
        route: EscalationRoute | None,
        reason: str,
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                "SELECT record_review_action(%s, %s, %s, %s, %s)",
                (escalation_id, actor_id, action, route.value if route else None, reason),
            ).fetchone()
        if row is None or not row[0]:
            raise KeyError("Escalation not found")
