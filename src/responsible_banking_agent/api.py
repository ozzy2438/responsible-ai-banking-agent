import secrets
import time
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import Cookie, Depends, FastAPI, Form, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .bank_data import build_bank_data_provider
from .config import Settings
from .identity import AuthenticationError, IdentityProvider, IdentityStore, build_identity_provider
from .middleware import BodyLimitMiddleware
from .models import Actor, AssistRequest, AssistResponse, EscalationRoute, Role
from .observability import configure_http_logger, route_group
from .policies import PolicyStore
from .rate_limit import (
    RateLimiter,
    RateLimitUnavailable,
    build_rate_limiter,
    hash_rate_limit_subject,
)
from .reasoning.openai_adapter import OpenAIResponsesAdapter
from .reasoning.stub import DeterministicStub
from .repository import BankingRepository, Repository
from .service import BankingService
from .version import __version__


class DevLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alias: Literal["alice", "bob", "reviewer", "compliance"]


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["acknowledge", "route", "close"]
    route: EscalationRoute | None = None
    reason: str = Field(min_length=3, max_length=500)


# Presentation-only lookup for the demo UI: which synthetic fixture account a
# demo customer persona owns, so the "attach my account" scenario button can
# pass a real, authorised account_id. Every service-layer authorization check
# in service.py re-verifies ownership regardless of what this map contains.
_DEMO_CUSTOMER_ACCOUNTS = {
    UUID("11111111-1111-4111-8111-111111111111"): UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    UUID("22222222-2222-4222-8222-222222222222"): UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
}


def create_app(
    settings: Settings | None = None,
    repository: BankingRepository | None = None,
    identities: IdentityStore | None = None,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    repository = repository or Repository(settings.database_url)
    identity_provider: IdentityProvider = build_identity_provider(settings, identities)
    policies = PolicyStore(settings.policy_bundle_path)
    provider = (
        OpenAIResponsesAdapter(settings.openai_model or "")
        if settings.reasoning_provider == "openai"
        else DeterministicStub()
    )
    data_provider = build_bank_data_provider(settings=settings, synthetic_provider=repository)
    rate_limiter = rate_limiter or build_rate_limiter(settings)
    rate_limit_key = settings.rate_limit_hmac_key or "local-only-rate-limit-key-not-for-production"
    http_logger = configure_http_logger(settings.log_format)
    service = BankingService(repository, policies, provider, data_provider)
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app = FastAPI(title="Responsible AI Banking Agent", version=__version__)
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )
    app.state.settings = settings
    app.state.repository = repository
    app.state.identity_provider = identity_provider
    app.state.rate_limiter = rate_limiter
    app.state.service = service
    demo_enabled = settings.app_env in {"local", "test"} and isinstance(
        identity_provider, IdentityStore
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(settings.allowed_hosts),
        www_redirect=False,
    )
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_request_body_bytes)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request, exc
        return JSONResponse(
            {"detail": "Request validation failed"},
            status_code=422,
        )

    def add_security_headers(response: Response, request_id: str) -> Response:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = request_id
        if settings.is_production_like:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            request_id = str(UUID(request.headers.get("X-Request-ID", "")))
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        group = route_group(request.url.path)
        started = time.perf_counter()

        if group not in {"/healthz", "/readyz"}:
            client_host = request.client.host if request.client else "unknown"
            subject_hash = hash_rate_limit_subject(rate_limit_key, f"ip:{client_host}")
            try:
                allowed = await run_in_threadpool(rate_limiter.allow, subject_hash, f"ip:{group}")
            except RateLimitUnavailable:
                response: Response = JSONResponse(
                    {"detail": "Request control unavailable"}, status_code=503
                )
            else:
                response = (
                    await call_next(request)
                    if allowed
                    else JSONResponse(
                        {"detail": "Too many requests"},
                        status_code=429,
                        headers={"Retry-After": str(settings.rate_limit_window_seconds)},
                    )
                )
        else:
            response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        http_logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "route_group": group,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return add_security_headers(response, request_id)

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
            return identity_provider.authenticate(token)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Authentication failed") from exc

    def reviewer(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.role not in {Role.REVIEWER, Role.COMPLIANCE}:
            raise HTTPException(status_code=403, detail="Reviewer role required")
        return actor

    def optional_actor(
        authorization: Annotated[str | None, Header()] = None,
        session_token: Annotated[str | None, Cookie()] = None,
    ) -> Actor | None:
        token = session_token
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
        if not token:
            return None
        try:
            return identity_provider.authenticate(token)
        except AuthenticationError:
            return None

    @app.get("/", response_class=HTMLResponse)
    def landing(
        request: Request, actor: Annotated[Actor | None, Depends(optional_actor)]
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="landing.html",
            context={"actor": actor, "demo_enabled": demo_enabled},
        )

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
        subject_hash = hash_rate_limit_subject(rate_limit_key, f"actor:{actor.actor_id}")
        try:
            allowed = rate_limiter.allow(subject_hash, "actor:/v1/assist")
        except RateLimitUnavailable as exc:
            raise HTTPException(status_code=503, detail="Request control unavailable") from exc
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
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
        if body.action != "route" and body.route is not None:
            raise HTTPException(status_code=422, detail="Route is only valid for route actions")
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
        if settings.app_env not in {"local", "test"} or not isinstance(
            identity_provider, IdentityStore
        ):
            raise HTTPException(status_code=404)
        response.status_code = 204
        response.set_cookie(
            "session_token",
            identity_provider.token_for_alias(body.alias),
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="strict",
            max_age=3600,
        )
        return response

    @app.get("/demo", response_class=HTMLResponse, response_model=None)
    def demo(
        request: Request, actor: Annotated[Actor | None, Depends(optional_actor)]
    ) -> HTMLResponse | RedirectResponse:
        if not demo_enabled:
            raise HTTPException(status_code=404)
        if actor is None:
            return RedirectResponse("/", status_code=303)
        account_id = _DEMO_CUSTOMER_ACCOUNTS.get(actor.actor_id)
        return templates.TemplateResponse(
            request=request,
            name="demo.html",
            context={"actor": actor, "account_id": account_id},
        )

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
        route: Annotated[str | None, Form()] = None,
    ) -> RedirectResponse:
        if not csrf_token or not secrets.compare_digest(csrf, csrf_token):
            raise HTTPException(status_code=403, detail="CSRF check failed")
        try:
            parsed_route = EscalationRoute(route) if route else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid route") from exc
        if action == "route" and parsed_route is None:
            raise HTTPException(status_code=422, detail="Route is required")
        if action != "route" and parsed_route is not None:
            raise HTTPException(status_code=422, detail="Route is only valid for route actions")
        try:
            repository.record_review_action(
                escalation_id=escalation_id,
                actor_id=actor.actor_id,
                action=action,
                route=parsed_route,
                reason=reason,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=409,
                detail="Review action is no longer valid for this escalation",
            ) from exc
        return RedirectResponse("/review/escalations", status_code=303)

    return app
