from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Disposition(StrEnum):
    ANSWERED = "answered"
    ESCALATED = "escalated"
    NEEDS_INFORMATION = "needs_information"


class Role(StrEnum):
    CUSTOMER = "customer"
    SUPPORT = "support"
    REVIEWER = "reviewer"
    COMPLIANCE = "compliance"


class EscalationRoute(StrEnum):
    CUSTOMER_SERVICE = "customer_service"
    COMPLAINTS = "complaints"
    FRAUD_OPERATIONS = "fraud_operations"
    HARDSHIP = "hardship"
    LENDING_SPECIALIST = "lending_specialist"
    LEGAL_COMPLIANCE = "legal_compliance"


class Actor(StrictModel):
    actor_id: UUID
    role: Role
    display_name: str = Field(min_length=1, max_length=100)


class AssistRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    account_id: UUID | None = None


class Citation(StrictModel):
    source_type: Literal["policy", "account", "transaction"]
    source_id: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    section: str = Field(min_length=1, max_length=120)


class VerifiedFact(StrictModel):
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)
    citation: Citation


class RiskAssessment(StrictModel):
    level: RiskLevel
    reason_codes: list[str] = Field(min_length=1)
    route: EscalationRoute | None = None


class ReasoningDraft(StrictModel):
    answer: str = Field(min_length=1, max_length=2000)
    uncertainty: list[str] = Field(default_factory=list, max_length=10)
    next_steps: list[str] = Field(default_factory=list, max_length=10)
    citation_source_ids: list[str] = Field(default_factory=list, max_length=20)


class AssistResponse(StrictModel):
    request_id: UUID
    risk_level: RiskLevel
    disposition: Disposition
    answer: str
    verified_facts: list[VerifiedFact]
    citations: list[Citation]
    uncertainty: list[str]
    next_steps: list[str]
    escalation_id: UUID | None = None
