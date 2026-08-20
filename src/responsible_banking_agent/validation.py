from __future__ import annotations

from .models import ReasoningDraft, RiskAssessment, RiskLevel, VerifiedFact


class ResponseValidationError(RuntimeError):
    pass


def validate_draft(
    draft: ReasoningDraft, assessment: RiskAssessment, facts: list[VerifiedFact]
) -> None:
    allowed = {fact.citation.source_id for fact in facts}
    if not set(draft.citation_source_ids).issubset(allowed):
        raise ResponseValidationError("Draft contains an unsupported citation")
    if assessment.level is not RiskLevel.HIGH and facts and not draft.citation_source_ids:
        raise ResponseValidationError("Factual response is missing citations")
    if assessment.level is RiskLevel.HIGH and "approved" in draft.answer.lower():
        raise ResponseValidationError("High-risk response contains decision language")
