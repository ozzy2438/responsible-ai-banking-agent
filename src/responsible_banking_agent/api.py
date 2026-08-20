import secrets
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import Cookie, Depends, FastAPI, Form, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import RequestResponseEndpoint

from .config import Settings
from .identity import AuthenticationError, IdentityStore
from .models import Actor, AssistRequest, AssistResponse, EscalationRoute, Role
from .policies import PolicyStore
from .reasoning.openai_adapter import OpenAIResponsesAdapter
from .reasoning.stub import DeterministicStub
from .repository import BankingRepository, Repository
from .service import BankingService


class DevLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alias: Literal["alice", "bob", "reviewer", "compliance"]


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["acknowledge", "route", "close"]
    route: EscalationRoute | None = None
    reason: str = Field(min_length=3, max_length=500)


def create_app(
    settings: Settings | None = None,
    repository: BankingRepository | None = None,
    identities: IdentityStore | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = repository or Repository(settings.database_url)
    identities = identities or IdentityStore.from_file(settings.identities_file)
    policies = PolicyStore(settings.policy_bundle_path)
    provider = (
        OpenAIResponsesAdapter(settings.openai_model or "")
        if settings.reasoning_provider == "openai"
        else DeterministicStub()
    )
    service = BankingService(repository, policies, provider)
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app = FastAPI(title="Responsible AI Banking Agent", version="0.1.0-rc.1")
    app.state.settings = settings
    app.state.repository = repository
    app.state.identities = identities
    app.state.service = service

    @app.middleware("http")
    async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    def current_actor(
        authorization: Annotated[str | None, Header()] = None,
        session_token: Annotated[str | None, Cookie()] = None,
    ) -> Actor:
        token = session_token
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            return identities.authenticate(token)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Authentication failed") from exc

    def reviewer(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.role not in {Role.REVIEWER, Role.COMPLIANCE}:
            raise HTTPException(status_code=403, detail="Reviewer role required")
        return actor

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def ready() -> dict[str, str]:
        if not repository.ready():
            raise HTTPException(status_code=503, detail="Database unavailable")
        return {"status": "ready"}

    @app.post("/v1/assist", response_model=AssistResponse)
    def assist(
        body: AssistRequest,
        actor: Annotated[Actor, Depends(current_actor)],
        idempotency_key: Annotated[
            str, Header(alias="Idempotency-Key", min_length=8, max_length=100)
        ],
    ) -> AssistResponse:
        return service.assist(actor, body, idempotency_key)

    @app.get("/v1/requests/{request_id}", response_model=AssistResponse)
    def get_request(
        request_id: UUID, actor: Annotated[Actor, Depends(current_actor)]
    ) -> AssistResponse:
        result = service.get_request(actor, request_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Request not found")
        return result

    @app.get("/v1/reviewer/escalations")
    def escalations(actor: Annotated[Actor, Depends(reviewer)]) -> list[dict[str, Any]]:
        del actor
        return repository.list_escalations()

    @app.post("/v1/reviewer/escalations/{escalation_id}/actions", status_code=204)
    def review_action(
        escalation_id: UUID,
        body: ReviewAction,
        actor: Annotated[Actor, Depends(reviewer)],
    ) -> Response:
        if body.action == "route" and body.route is None:
            raise HTTPException(status_code=422, detail="Route is required")
        try:
            repository.record_review_action(
                escalation_id=escalation_id,
                actor_id=actor.actor_id,
                action=body.action,
                route=body.route,
                reason=body.reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Escalation not found") from exc
        return Response(status_code=204)

    @app.post("/dev/login", status_code=204)
    def dev_login(body: DevLogin, response: Response) -> Response:
        if settings.app_env not in {"local", "test"}:
            raise HTTPException(status_code=404)
        response.status_code = 204
        response.set_cookie(
            "session_token",
            identities.token_for_alias(body.alias),
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="strict",
            max_age=3600,
        )
        return response

    @app.get("/review/escalations", response_class=HTMLResponse)
    def review_page(request: Request, actor: Annotated[Actor, Depends(reviewer)]) -> HTMLResponse:
        csrf = secrets.token_urlsafe(24)
        response = templates.TemplateResponse(
            request=request,
            name="review.html",
            context={"actor": actor, "items": repository.list_escalations(), "csrf": csrf},
        )
        response.set_cookie(
            "csrf_token",
            csrf,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="strict",
        )
        return response

    @app.post("/review/escalations/{escalation_id}/actions")
    def review_form_action(
        escalation_id: UUID,
        actor: Annotated[Actor, Depends(reviewer)],
        action: Annotated[Literal["acknowledge", "route", "close"], Form()],
        reason: Annotated[str, Form(min_length=3, max_length=500)],
        csrf: Annotated[str, Form()],
        csrf_token: Annotated[str | None, Cookie()] = None,
        route: Annotated[EscalationRoute | None, Form()] = None,
    ) -> RedirectResponse:
        if not csrf_token or not secrets.compare_digest(csrf, csrf_token):
            raise HTTPException(status_code=403, detail="CSRF check failed")
        if action == "route" and route is None:
            raise HTTPException(status_code=422, detail="Route is required")
        repository.record_review_action(
            escalation_id=escalation_id,
            actor_id=actor.actor_id,
            action=action,
            route=route,
            reason=reason,
        )
        return RedirectResponse("/review/escalations", status_code=303)

    return app
