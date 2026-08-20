from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from .models import (
    Actor,
    AssistRequest,
    AssistResponse,
    Citation,
    Disposition,
    EscalationRoute,
    RiskLevel,
    VerifiedFact,
)
from .policies import PolicyStore
from .privacy import redact_sensitive
from .reasoning.base import ReasoningProvider
from .reasoning.openai_adapter import ProviderOutputError
from .reasoning.stub import DeterministicStub
from .repository import BankingRepository
from .risk import classify_request
from .validation import ResponseValidationError, validate_draft


class BankingService:
    def __init__(
        self, repository: BankingRepository, policies: PolicyStore, provider: ReasoningProvider
    ) -> None:
        self.repository = repository
        self.policies = policies
        self.provider = provider
        self.fallback = DeterministicStub()

    def assist(self, actor: Actor, request: AssistRequest, idempotency_key: str) -> AssistResponse:
        redaction = redact_sensitive(request.message)
        assessment = classify_request(request.message, request.account_id, redaction.categories)
        facts: list[VerifiedFact] = []
        if assessment.level is RiskLevel.LOW:
            facts = self.policies.lookup(redaction.text)
        elif assessment.level is RiskLevel.MEDIUM and request.account_id:
            account = self.repository.get_authorized_account(actor.actor_id, request.account_id)
            if account is None:
                assessment = assessment.model_copy(
                    update={
                        "level": RiskLevel.HIGH,
                        "reason_codes": ["identity_or_account_scope_conflict"],
                        "route": EscalationRoute.CUSTOMER_SERVICE,
                    }
                )
            elif datetime.now(UTC) - account.updated_at > timedelta(hours=24):
                assessment = assessment.model_copy(
                    update={
                        "level": RiskLevel.HIGH,
                        "reason_codes": ["account_data_stale"],
                        "route": EscalationRoute.CUSTOMER_SERVICE,
                    }
                )
            else:
                citation = Citation(
                    source_type="account",
                    source_id=str(account.account_id),
                    version=account.updated_at.isoformat(),
                    section="authorised-summary",
                )
                facts = [
                    VerifiedFact(label="Account", value=account.account_name, citation=citation),
                    VerifiedFact(
                        label="Available balance",
                        value=f"{account.currency} {account.available_balance}",
                        citation=citation,
                    ),
                ]
                if "transaction" in redaction.text.lower():
                    for transaction in self.repository.get_authorized_transactions(
                        actor.actor_id, request.account_id
                    ):
                        transaction_citation = Citation(
                            source_type="transaction",
                            source_id=str(transaction.transaction_id),
                            version=transaction.updated_at.isoformat(),
                            section="authorised-transaction",
                        )
                        facts.append(
                            VerifiedFact(
                                label=f"Transaction on {transaction.booked_at.date().isoformat()}",
                                value=(
                                    f"{transaction.description}: "
                                    f"{transaction.currency} {transaction.amount}"
                                ),
                                citation=transaction_citation,
                            )
                        )
        elif assessment.level is RiskLevel.MEDIUM:
            assessment = assessment.model_copy(
                update={
                    "level": RiskLevel.HIGH,
                    "reason_codes": ["account_identifier_required"],
                    "route": assessment.route or EscalationRoute.CUSTOMER_SERVICE,
                }
            )

        escalated = assessment.level is RiskLevel.HIGH or assessment.route is not None
        if escalated:
            draft = self.fallback.draft(redaction.text, assessment, facts)
        else:
            try:
                draft = self.provider.draft(redaction.text, assessment, facts)
                validate_draft(draft, assessment, facts)
            except (ProviderOutputError, ResponseValidationError, RuntimeError):
                draft = self.fallback.draft(redaction.text, assessment, facts)
                validate_draft(draft, assessment, facts)

        if redaction.redacted:
            draft = draft.model_copy(
                update={
                    "answer": (
                        "Sensitive credentials were removed. Do not share them with an assistant."
                    ),
                    "uncertainty": ["The submitted secret was not used to access an account."],
                    "next_steps": ["Use the bank's verified security support channel."],
                    "citation_source_ids": [],
                }
            )
        request_id = uuid4()
        escalation_id = uuid4() if escalated else None
        response = AssistResponse(
            request_id=request_id,
            risk_level=assessment.level,
            disposition=Disposition.ESCALATED if escalated else Disposition.ANSWERED,
            answer=draft.answer,
            verified_facts=facts,
            citations=[fact.citation for fact in facts],
            uncertainty=draft.uncertainty,
            next_steps=draft.next_steps,
            escalation_id=escalation_id,
        )
        return self.repository.persist_response(
            response=response,
            actor_id=actor.actor_id,
            idempotency_key=idempotency_key,
            redacted_message=redaction.text,
            route=assessment.route,
            escalation_summary=(
                f"Risk {assessment.level.value}; reasons: {', '.join(assessment.reason_codes)}"
            ),
        )

    def get_request(self, actor: Actor, request_id: UUID) -> AssistResponse | None:
        return self.repository.get_request(actor.actor_id, request_id)
