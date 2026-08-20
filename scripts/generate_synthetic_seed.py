"""Deterministically generate the bulk synthetic seed migration.

Produces ``migrations/0003_synthetic_seed_data.sql``: a large population of
synthetic customers, accounts, and transactions for local development and
demo/stress use, plus a small set of hand-named edge-case fixtures (stale
account data, a multi-account customer, a foreign-currency account, an
overdrawn account, a high-balance account).

This is a dev-only generator, not part of the installed package. Re-running
it produces byte-identical output: every random choice is drawn from a
``random.Random`` seeded with ``SEED``, and every UUID is derived with
``uuid.uuid5`` from a namespace computed from this repository's URL, so nothing
here depends on wall-clock time or process entropy. Row timestamps are emitted
as SQL ``now() - interval '...'`` expressions rather than literal computed
dates, so seeded data is always fresh relative to whenever the migration is
actually applied — matching the pattern already used for the two seed rows in
``migrations/0001_schema.sql``.

Usage: python scripts/generate_synthetic_seed.py > migrations/0003_synthetic_seed_data.sql
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

SEED = 424242
CUSTOMER_COUNT = 300
NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL,
    "https://github.com/ozzy2438/responsible-ai-banking-agent/synthetic-seed",
)
BATCH_SIZE = 200
SIX_MONTHS_HOURS = 180 * 24

ACCOUNT_TEMPLATES = [
    ("Synthetic Everyday", "AUD", Decimal("50.00"), Decimal("12000.00"), 0.65),
    ("Synthetic Saver", "AUD", Decimal("200.00"), Decimal("40000.00"), 0.20),
    ("Synthetic Bills", "AUD", Decimal("20.00"), Decimal("3000.00"), 0.10),
    ("Synthetic Travel", "AUD", Decimal("0.00"), Decimal("5000.00"), 0.05),
]

# (description, low_amount, high_amount) — negative ranges are debits.
TRANSACTION_TYPES = [
    ("Synthetic grocery", Decimal("-80.00"), Decimal("-15.00"), 16),
    ("Synthetic dining", Decimal("-60.00"), Decimal("-8.00"), 14),
    ("Synthetic fuel", Decimal("-90.00"), Decimal("-30.00"), 8),
    ("Synthetic subscription", Decimal("-25.00"), Decimal("-5.00"), 10),
    ("Synthetic utility payment", Decimal("-220.00"), Decimal("-40.00"), 6),
    ("Synthetic pharmacy", Decimal("-70.00"), Decimal("-5.00"), 6),
    ("Synthetic rent", Decimal("-650.00"), Decimal("-350.00"), 4),
    ("Synthetic ATM withdrawal", Decimal("-400.00"), Decimal("-20.00"), 8),
    ("Synthetic transfer out", Decimal("-500.00"), Decimal("-10.00"), 8),
    ("Synthetic salary", Decimal("1800.00"), Decimal("4200.00"), 5),
    ("Synthetic refund", Decimal("5.00"), Decimal("120.00"), 4),
    ("Synthetic deposit", Decimal("20.00"), Decimal("800.00"), 6),
]


@dataclass
class Customer:
    id: uuid.UUID
    display_name: str


@dataclass
class Account:
    id: uuid.UUID
    customer_id: uuid.UUID
    account_name: str
    currency: str
    available_balance: Decimal
    updated_at_expr: str


@dataclass
class Transaction:
    id: uuid.UUID
    account_id: uuid.UUID
    description: str
    amount: Decimal
    booked_at_expr: str
    updated_at_expr: str


@dataclass
class SeedData:
    customers: list[Customer] = field(default_factory=list)
    accounts: list[Account] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)


def _uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, key)


def _sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _weighted_choice(rng: random.Random, options: list[tuple], weight_index: int):
    weights = [option[weight_index] for option in options]
    return rng.choices(options, weights=weights, k=1)[0]


def _random_amount(rng: random.Random, low: Decimal, high: Decimal) -> Decimal:
    span = int((high - low) * 100)
    cents = rng.randint(0, span) if span > 0 else 0
    return (low + Decimal(cents) / 100).quantize(Decimal("0.01"))


def _generate_account_transactions(rng: random.Random, account: Account) -> list[Transaction]:
    count = rng.randint(8, 30)
    transactions = []
    for index in range(count):
        description, low, high, _ = _weighted_choice(rng, TRANSACTION_TYPES, 3)
        amount = _random_amount(rng, low, high)
        offset_hours = rng.randint(1, SIX_MONTHS_HOURS)
        transactions.append(
            Transaction(
                id=_uuid(f"transaction/{account.id}/{index}"),
                account_id=account.id,
                description=description,
                amount=amount,
                booked_at_expr=f"now() - interval '{offset_hours} hours'",
                updated_at_expr="now()",
            )
        )
    return transactions


def build_bulk_population(rng: random.Random) -> SeedData:
    data = SeedData()
    for index in range(1, CUSTOMER_COUNT + 1):
        customer = Customer(
            id=_uuid(f"customer/{index:04d}"),
            display_name=f"Synthetic Customer {index:04d}",
        )
        data.customers.append(customer)

        account_count = 2 if rng.random() < 0.15 else 1
        for account_index in range(account_count):
            if account_index == 0:
                name, currency, low, high, _ = ACCOUNT_TEMPLATES[0]
            else:
                name, currency, low, high, _ = _weighted_choice(rng, ACCOUNT_TEMPLATES[1:], 4)
            balance = _random_amount(rng, low, high)
            freshness_hours = rng.randint(0, 20)
            account = Account(
                id=_uuid(f"account/{customer.id}/{account_index}"),
                customer_id=customer.id,
                account_name=name,
                currency=currency,
                available_balance=balance,
                updated_at_expr=f"now() - interval '{freshness_hours} hours'",
            )
            data.accounts.append(account)
            data.transactions.extend(_generate_account_transactions(rng, account))
    return data


def build_named_fixtures(rng: random.Random) -> SeedData:
    """Hand-named edge-case fixtures the extended scenario corpus references by UUID."""
    data = SeedData()

    stale_customer = Customer(
        id=uuid.UUID("55555555-5555-4555-8555-555555555555"),
        display_name="Priya StaleData Example",
    )
    stale_account = Account(
        id=uuid.UUID("55555555-aaaa-4555-8aaa-555555555555"),
        customer_id=stale_customer.id,
        account_name="Synthetic Everyday",
        currency="AUD",
        available_balance=Decimal("640.15"),
        updated_at_expr="now() - interval '3 days'",
    )
    data.customers.append(stale_customer)
    data.accounts.append(stale_account)
    data.transactions.extend(_generate_account_transactions(rng, stale_account))

    multi_customer = Customer(
        id=uuid.UUID("66666666-6666-4666-8666-666666666666"),
        display_name="Jordan MultiAccount Example",
    )
    multi_everyday = Account(
        id=uuid.UUID("66666666-aaaa-4666-8aaa-666666666666"),
        customer_id=multi_customer.id,
        account_name="Synthetic Everyday",
        currency="AUD",
        available_balance=Decimal("2310.40"),
        updated_at_expr="now() - interval '2 hours'",
    )
    multi_saver = Account(
        id=uuid.UUID("66666666-bbbb-4666-8bbb-666666666666"),
        customer_id=multi_customer.id,
        account_name="Synthetic Saver",
        currency="AUD",
        available_balance=Decimal("15420.00"),
        updated_at_expr="now() - interval '2 hours'",
    )
    data.customers.append(multi_customer)
    data.accounts.extend([multi_everyday, multi_saver])
    data.transactions.extend(_generate_account_transactions(rng, multi_everyday))
    data.transactions.extend(_generate_account_transactions(rng, multi_saver))

    fx_customer = Customer(
        id=uuid.UUID("77777777-7777-4777-8777-777777777777"),
        display_name="Sam ForeignCurrency Example",
    )
    fx_account = Account(
        id=uuid.UUID("77777777-aaaa-4777-8aaa-777777777777"),
        customer_id=fx_customer.id,
        account_name="Synthetic Everyday USD",
        currency="USD",
        available_balance=Decimal("3125.60"),
        updated_at_expr="now() - interval '1 hour'",
    )
    data.customers.append(fx_customer)
    data.accounts.append(fx_account)
    data.transactions.extend(_generate_account_transactions(rng, fx_account))

    overdrawn_customer = Customer(
        id=uuid.UUID("88888888-8888-4888-8888-888888888888"),
        display_name="Morgan Overdrawn Example",
    )
    overdrawn_account = Account(
        id=uuid.UUID("88888888-aaaa-4888-8aaa-888888888888"),
        customer_id=overdrawn_customer.id,
        account_name="Synthetic Everyday",
        currency="AUD",
        available_balance=Decimal("-125.40"),
        updated_at_expr="now() - interval '1 hour'",
    )
    data.customers.append(overdrawn_customer)
    data.accounts.append(overdrawn_account)
    data.transactions.extend(_generate_account_transactions(rng, overdrawn_account))

    high_balance_customer = Customer(
        id=uuid.UUID("99999999-9999-4999-8999-999999999999"),
        display_name="Taylor HighBalance Example",
    )
    high_balance_account = Account(
        id=uuid.UUID("99999999-aaaa-4999-8aaa-999999999999"),
        customer_id=high_balance_customer.id,
        account_name="Synthetic Saver",
        currency="AUD",
        available_balance=Decimal("248500.00"),
        updated_at_expr="now() - interval '1 hour'",
    )
    data.customers.append(high_balance_customer)
    data.accounts.append(high_balance_account)
    data.transactions.append(
        Transaction(
            id=uuid.UUID("99999999-1000-4000-8000-999999999999"),
            account_id=high_balance_account.id,
            description="Synthetic large transfer out",
            amount=Decimal("-52000.00"),
            booked_at_expr="now() - interval '18 hours'",
            updated_at_expr="now()",
        )
    )
    data.transactions.extend(_generate_account_transactions(rng, high_balance_account))

    return data


def _check_no_duplicate_ids(data: SeedData) -> None:
    customer_ids = [c.id for c in data.customers]
    account_ids = [a.id for a in data.accounts]
    transaction_ids = [t.id for t in data.transactions]
    for label, ids in (
        ("customer", customer_ids),
        ("account", account_ids),
        ("transaction", transaction_ids),
    ):
        if len(ids) != len(set(ids)):
            raise AssertionError(f"duplicate {label} id generated")


def _emit_inserts(lines: list[str], table: str, columns: list[str], rows: list[str]) -> None:
    if not rows:
        return
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        lines.append(f"INSERT INTO {table}({', '.join(columns)}) VALUES")
        lines.append(",\n".join(batch) + ";")
        lines.append("")


def render(data: SeedData) -> str:
    lines = [
        "-- Bulk synthetic seed data.",
        "-- Generated by scripts/generate_synthetic_seed.py — do not hand-edit.",
        f"-- SEED={SEED} CUSTOMER_COUNT={CUSTOMER_COUNT} NAMESPACE={NAMESPACE}",
        f"-- Rows: {len(data.customers)} customers, {len(data.accounts)} accounts, "
        f"{len(data.transactions)} transactions.",
        "-- Regenerate with: .venv/bin/python scripts/generate_synthetic_seed.py "
        "> migrations/0003_synthetic_seed_data.sql",
        "",
    ]

    customer_rows = [
        f"({_sql_str(str(c.id))}, {_sql_str(c.display_name)}, true)" for c in data.customers
    ]
    _emit_inserts(lines, "customers", ["id", "display_name", "synthetic"], customer_rows)

    account_rows = [
        f"({_sql_str(str(a.id))}, {_sql_str(str(a.customer_id))}, "
        f"{_sql_str(a.account_name)}, {_sql_str(a.currency)}, {a.available_balance}, "
        f"{a.updated_at_expr})"
        for a in data.accounts
    ]
    _emit_inserts(
        lines,
        "accounts",
        ["id", "customer_id", "account_name", "currency", "available_balance", "updated_at"],
        account_rows,
    )

    transaction_rows = [
        f"({_sql_str(str(t.id))}, {_sql_str(str(t.account_id))}, "
        f"{_sql_str(t.description)}, {t.amount}, {t.booked_at_expr}, {t.updated_at_expr})"
        for t in data.transactions
    ]
    _emit_inserts(
        lines,
        "transactions",
        ["id", "account_id", "description", "amount", "booked_at", "updated_at"],
        transaction_rows,
    )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    rng = random.Random(SEED)
    data = build_named_fixtures(rng)
    bulk = build_bulk_population(rng)
    data.customers.extend(bulk.customers)
    data.accounts.extend(bulk.accounts)
    data.transactions.extend(bulk.transactions)
    _check_no_duplicate_ids(data)
    print(render(data), end="")


if __name__ == "__main__":
    main()
