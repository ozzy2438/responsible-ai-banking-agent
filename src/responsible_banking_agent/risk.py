from __future__ import annotations

import re
from uuid import UUID

from .models import EscalationRoute, RiskAssessment, RiskLevel

_HIGH_RULES: tuple[tuple[str, EscalationRoute, tuple[str, ...]], ...] = (
    ("fraud", EscalationRoute.FRAUD_OPERATIONS, ("fraud", "scam", "stolen", "suspicious")),
    (
        "hardship",
        EscalationRoute.HARDSHIP,
        ("hardship", "cannot pay", "can't pay", "financial difficulty"),
    ),
    (
        "lending",
        EscalationRoute.LENDING_SPECIALIST,
        ("loan", "mortgage", "credit limit", "creditworthy", "approve credit"),
    ),
    (
        "advice",
        EscalationRoute.LEGAL_COMPLIANCE,
        ("invest", "financial advice", "which shares", "personal advice"),
    ),
    (
        "legal",
        EscalationRoute.LEGAL_COMPLIANCE,
        ("legal", "regulator", "lawsuit", "court", "policy exception"),
    ),
    (
        "transaction_action",
        EscalationRoute.CUSTOMER_SERVICE,
        ("transfer money", "send money", "move funds", "change my address", "close my account"),
    ),
    (
        "unusual_transaction",
        EscalationRoute.FRAUD_OPERATIONS,
        ("large transaction", "unusual transaction", "source of funds"),
    ),
    (
        "bypass",
        EscalationRoute.LEGAL_COMPLIANCE,
        ("bypass", "override control", "ignore previous", "system prompt", "reveal secret"),
    ),
)
_MEDIUM = (
    "balance",
    "account",
    "transaction",
    "statement",
    "complaint",
    "charge",
    "fee",
    "direct debit",
)
_LOW = ("branch", "opening hours", "how do", "what is", "explain", "process", "contact")


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def classify_request(
    message: str,
    account_id: UUID | None = None,
    redaction_categories: tuple[str, ...] = (),
) -> RiskAssessment:
    lowered = " ".join(message.lower().split())
    if redaction_categories:
        return RiskAssessment(
            level=RiskLevel.HIGH,
            reason_codes=["sensitive_credential_submitted"],
            route=EscalationRoute.CUSTOMER_SERVICE,
        )
    for reason, route, phrases in _HIGH_RULES:
        if any(_contains(lowered, phrase) for phrase in phrases):
            return RiskAssessment(level=RiskLevel.HIGH, reason_codes=[reason], route=route)
    if account_id is not None or any(_contains(lowered, phrase) for phrase in _MEDIUM):
        medium_route = EscalationRoute.COMPLAINTS if _contains(lowered, "complaint") else None
        return RiskAssessment(
            level=RiskLevel.MEDIUM, reason_codes=["account_specific"], route=medium_route
        )
    if any(_contains(lowered, phrase) for phrase in _LOW):
        return RiskAssessment(level=RiskLevel.LOW, reason_codes=["approved_general_information"])
    return RiskAssessment(
        level=RiskLevel.HIGH,
        reason_codes=["unclassified_or_uncertain"],
        route=EscalationRoute.CUSTOMER_SERVICE,
    )
