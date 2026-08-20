from __future__ import annotations

from typing import Protocol

from ..models import ReasoningDraft, RiskAssessment, VerifiedFact


class ReasoningProvider(Protocol):
    def draft(
        self, message: str, assessment: RiskAssessment, facts: list[VerifiedFact]
    ) -> ReasoningDraft: ...
