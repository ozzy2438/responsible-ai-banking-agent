import json

import pytest

from responsible_banking_agent.models import Citation, RiskAssessment, RiskLevel, VerifiedFact
from responsible_banking_agent.reasoning.openai_adapter import (
    OpenAIResponsesAdapter,
    ProviderOutputError,
)
from responsible_banking_agent.reasoning.stub import DeterministicStub
from responsible_banking_agent.validation import ResponseValidationError, validate_draft


def _fact() -> VerifiedFact:
    return VerifiedFact(
        label="Service",
        value="Synthetic verified service information.",
        citation=Citation(
            source_type="policy", source_id="POL-GENERAL-001", version="1", section="s"
        ),
    )


class FakeResponses:
    def __init__(self, output: str) -> None:
        self.output = output
        self.kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return type("Response", (), {"output_text": self.output})()


class FakeClient:
    def __init__(self, output: str) -> None:
        self.responses = FakeResponses(output)


def test_openai_adapter_uses_strict_schema_and_store_false() -> None:
    output = json.dumps(
        {
            "answer": "Verified answer.",
            "uncertainty": [],
            "next_steps": [],
            "citation_source_ids": ["POL-GENERAL-001"],
        }
    )
    client = FakeClient(output)
    draft = OpenAIResponsesAdapter("explicit-model", client).draft(
        "question", RiskAssessment(level=RiskLevel.LOW, reason_codes=["general"]), [_fact()]
    )
    assert draft.answer == "Verified answer."
    assert client.responses.kwargs["store"] is False
    assert client.responses.kwargs["text"]["format"]["strict"] is True  # type: ignore[index]


def test_openai_adapter_rejects_unapproved_citation() -> None:
    output = json.dumps(
        {
            "answer": "Unsupported.",
            "uncertainty": [],
            "next_steps": [],
            "citation_source_ids": ["INVENTED"],
        }
    )
    with pytest.raises(ProviderOutputError):
        OpenAIResponsesAdapter("explicit-model", FakeClient(output)).draft(
            "question", RiskAssessment(level=RiskLevel.LOW, reason_codes=["general"]), [_fact()]
        )


def test_stub_and_validator_require_citation() -> None:
    assessment = RiskAssessment(level=RiskLevel.LOW, reason_codes=["general"])
    draft = DeterministicStub().draft("question", assessment, [_fact()])
    validate_draft(draft, assessment, [_fact()])
    bad = draft.model_copy(update={"citation_source_ids": []})
    with pytest.raises(ResponseValidationError):
        validate_draft(bad, assessment, [_fact()])
