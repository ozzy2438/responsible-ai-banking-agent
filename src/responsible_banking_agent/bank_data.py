from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .repository import AccountRecord, TransactionRecord

if TYPE_CHECKING:
    from .config import Settings


class BankDataError(RuntimeError):
    pass


class BankDataUnavailable(BankDataError):
    pass


class BankDataConflict(BankDataError):
    pass


class BankDataProvider(Protocol):
    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None: ...

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]: ...


class _AccountPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    account_id: UUID
    account_name: str = Field(min_length=1, max_length=120)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    available_balance: Decimal
    updated_at: datetime
    source_system: str = Field(min_length=1, max_length=80)
    source_version: str = Field(min_length=1, max_length=80)


class _TransactionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    account_id: UUID
    transaction_id: UUID
    description: str = Field(min_length=1, max_length=200)
    amount: Decimal
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    booked_at: datetime
    updated_at: datetime
    source_system: str = Field(min_length=1, max_length=80)
    source_version: str = Field(min_length=1, max_length=80)


class _TransactionsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transactions: list[_TransactionPayload] = Field(max_length=20)


class ReadOnlyBankingAPIProvider:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        ca_file: Path,
        client_cert_file: Path,
        client_key_file: Path,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        self.token = token
        self.client = client or httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            verify=str(ca_file),
            cert=(str(client_cert_file), str(client_key_file)),
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": "responsible-banking-agent/0.1"},
        )

    def _get(self, path: str, params: dict[str, int] | None = None) -> httpx.Response:
        try:
            response = self.client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if response.status_code == 404:
                return response
            response.raise_for_status()
            if len(response.content) > 1_048_576:
                raise BankDataConflict("Bank evidence response exceeded the size limit")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            if content_type != "application/json":
                raise BankDataConflict("Bank evidence response was not JSON")
            return response
        except httpx.HTTPError as exc:
            raise BankDataUnavailable("Approved bank evidence source is unavailable") from exc

    def get_authorized_account(self, actor_id: UUID, account_id: UUID) -> AccountRecord | None:
        response = self._get(f"v1/customers/{actor_id}/accounts/{account_id}")
        if response.status_code == 404:
            return None
        try:
            payload = _AccountPayload.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise BankDataConflict("Bank account evidence failed contract validation") from exc
        if payload.customer_id != actor_id or payload.account_id != account_id:
            raise BankDataConflict("Bank account evidence crossed the requested scope")
        return AccountRecord(
            account_id=payload.account_id,
            account_name=payload.account_name,
            currency=payload.currency,
            available_balance=format(payload.available_balance, "f"),
            updated_at=payload.updated_at,
            source_system=payload.source_system,
            source_version=payload.source_version,
        )

    def get_authorized_transactions(
        self, actor_id: UUID, account_id: UUID, limit: int = 5
    ) -> list[TransactionRecord]:
        bounded_limit = min(max(limit, 1), 20)
        response = self._get(
            f"v1/customers/{actor_id}/accounts/{account_id}/transactions",
            params={"limit": bounded_limit},
        )
        if response.status_code == 404:
            return []
        try:
            payload = _TransactionsPayload.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise BankDataConflict("Bank transaction evidence failed contract validation") from exc
        if any(
            item.customer_id != actor_id or item.account_id != account_id
            for item in payload.transactions
        ):
            raise BankDataConflict("Bank transaction evidence crossed the requested scope")
        return [
            TransactionRecord(
                transaction_id=item.transaction_id,
                description=item.description,
                amount=format(item.amount, "f"),
                currency=item.currency,
                booked_at=item.booked_at,
                updated_at=item.updated_at,
                source_system=item.source_system,
                source_version=item.source_version,
            )
            for item in payload.transactions[:bounded_limit]
        ]


def build_bank_data_provider(
    *, settings: Settings, synthetic_provider: BankDataProvider
) -> BankDataProvider:
    if settings.bank_data_provider == "synthetic":
        return synthetic_provider
    return ReadOnlyBankingAPIProvider(
        base_url=settings.bank_api_base_url or "",
        token=settings.bank_api_token or "",
        ca_file=settings.bank_api_ca_file or Path(""),
        client_cert_file=settings.bank_api_client_cert_file or Path(""),
        client_key_file=settings.bank_api_client_key_file or Path(""),
        timeout_seconds=settings.bank_api_timeout_seconds,
    )
