from __future__ import annotations

from ..models import ReasoningDraft, RiskAssessment, RiskLevel, VerifiedFact


class DeterministicStub:
    def draft(
        self, message: str, assessment: RiskAssessment, facts: list[VerifiedFact]
    ) -> ReasoningDraft:
        del message
        if assessment.level is RiskLevel.HIGH or assessment.route is not None:
            return ReasoningDraft(
                answer="This request needs review by an authorised banking specialist.",
                uncertainty=["No autonomous decision has been made."],
                next_steps=["A reviewer will assess the verified information and contact you."],
            )
        if not facts:
            return ReasoningDraft(
                answer="I don't have enough verified information to determine that.",
                uncertainty=["No approved source matched the request."],
                next_steps=["Ask customer service to verify the required information."],
            )
        summary = " ".join(f"{fact.label}: {fact.value}" for fact in facts)
        return ReasoningDraft(
            answer=summary,
            next_steps=["Contact customer service if you need account-specific help."],
            citation_source_ids=[fact.citation.source_id for fact in facts],
        )
