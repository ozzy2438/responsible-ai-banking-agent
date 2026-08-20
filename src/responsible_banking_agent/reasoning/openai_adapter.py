from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from ..models import ReasoningDraft, RiskAssessment, VerifiedFact


class ProviderOutputError(RuntimeError):
    pass


class OpenAIResponsesAdapter:
    def __init__(self, model: str, client: Any | None = None) -> None:
        if not model:
            raise ValueError("An explicit OpenAI model is required")
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client
        self.model = model

    def draft(
        self, message: str, assessment: RiskAssessment, facts: list[VerifiedFact]
    ) -> ReasoningDraft:
        allowed_ids = {fact.citation.source_id for fact in facts}
        payload = {
            "request": message,
            "risk": assessment.model_dump(mode="json"),
            "verified_facts": [fact.model_dump(mode="json") for fact in facts],
        }
        try:
            response = self.client.responses.create(
                model=self.model,
                store=False,
                input=[
                    {
                        "role": "developer",
                        "content": (
                            "Rewrite only the verified facts in calm plain language. "
                            "Do not add facts, advice, decisions, tools, or permissions."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "banking_reasoning_draft",
                        "strict": True,
                        "schema": ReasoningDraft.model_json_schema(),
                    }
                },
                max_output_tokens=800,
            )
            draft = ReasoningDraft.model_validate_json(response.output_text)
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderOutputError("Provider returned invalid structured output") from exc
        except Exception as exc:
            raise ProviderOutputError("Provider request failed") from exc
        if not set(draft.citation_source_ids).issubset(allowed_ids):
            raise ProviderOutputError("Provider cited an unapproved source")
        return draft
