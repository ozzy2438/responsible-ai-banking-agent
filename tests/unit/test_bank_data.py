from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from responsible_banking_agent.bank_data import (
    BankDataConflict,
    BankDataUnavailable,
    ReadOnlyBankingAPIProvider,
)

ACTOR_ID = UUID("11111111-1111-4111-8111-111111111111")
ACCOUNT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TRANSACTION_ID = UUID("a1000000-0000-4000-8000-000000000001")


def _provider(handler: httpx.MockTransport) -> ReadOnlyBankingAPIProvider:
    client = httpx.Client(base_url="https://bank.example.test/", transport=handler)
    return ReadOnlyBankingAPIProvider(
        base_url="https://bank.example.test",
        token="bank-token",
        ca_file=Path("ca.pem"),
        client_cert_file=Path("client.pem"),
        client_key_file=Path("client-key.pem"),
        timeout_seconds=1,
        client=client,
    )


def test_read_only_bank_provider_validates_scope_and_provenance() -> None:
    now = datetime.now(UTC).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer bank-token"
        if request.url.path.endswith("/transactions"):
            assert request.url.params["limit"] == "5"
            return httpx.Response(
                200,
                json={
                    "transactions": [
                        {
                            "customer_id": str(ACTOR_ID),
                            "account_id": str(ACCOUNT_ID),
                            "transaction_id": str(TRANSACTION_ID),
                            "description": "Approved bank transaction",
                            "amount": "-12.50",
                            "currency": "AUD",
                            "booked_at": now,
                            "updated_at": now,
                            "source_system": "core-banking-read-api",
                            "source_version": "txn-v7",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "customer_id": str(ACTOR_ID),
                "account_id": str(ACCOUNT_ID),
                "account_name": "Everyday account",
                "currency": "AUD",
                "available_balance": "1200.50",
                "updated_at": now,
                "source_system": "core-banking-read-api",
                "source_version": "acct-v4",
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    account = provider.get_authorized_account(ACTOR_ID, ACCOUNT_ID)
    transactions = provider.get_authorized_transactions(ACTOR_ID, ACCOUNT_ID)
    assert account and account.source_version == "acct-v4"
    assert transactions[0].source_version == "txn-v7"


def test_read_only_bank_provider_rejects_cross_customer_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            json={
                "customer_id": "22222222-2222-4222-8222-222222222222",
                "account_id": str(ACCOUNT_ID),
                "account_name": "Wrong customer",
                "currency": "AUD",
                "available_balance": "1.00",
                "updated_at": datetime.now(UTC).isoformat(),
                "source_system": "core-banking-read-api",
                "source_version": "bad-v1",
            },
        )

    with pytest.raises(BankDataConflict, match="crossed"):
        _provider(httpx.MockTransport(handler)).get_authorized_account(ACTOR_ID, ACCOUNT_ID)


def test_read_only_bank_provider_fails_closed_on_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, json={"internal": "details must not escape"})

    with pytest.raises(BankDataUnavailable, match="unavailable"):
        _provider(httpx.MockTransport(handler)).get_authorized_account(ACTOR_ID, ACCOUNT_ID)


def test_read_only_bank_provider_rejects_non_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, text="unexpected upstream page")

    with pytest.raises(BankDataConflict, match="not JSON"):
        _provider(httpx.MockTransport(handler)).get_authorized_account(ACTOR_ID, ACCOUNT_ID)
