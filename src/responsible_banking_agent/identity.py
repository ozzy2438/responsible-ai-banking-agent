from __future__ import annotations

import hmac
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

import jwt

from .models import Actor, Role

if TYPE_CHECKING:
    from .config import Settings


class AuthenticationError(RuntimeError):
    pass


class IdentityProvider(Protocol):
    def authenticate(self, token: str) -> Actor: ...


class IdentityStore:
    def __init__(self, entries: dict[str, dict[str, Any]]) -> None:
        self.entries = entries

    @classmethod
    def from_file(cls, path: Path) -> IdentityStore:
        return cls(json.loads(path.read_text(encoding="utf-8"))["identities"])

    def authenticate(self, token: str) -> Actor:
        for entry in self.entries.values():
            if hmac.compare_digest(str(entry["token"]), token):
                return Actor(
                    actor_id=UUID(entry["actor_id"]),
                    role=Role(entry["role"]),
                    display_name=entry["display_name"],
                    authentication_method="simulated",
                )
        raise AuthenticationError("Invalid bearer token")

    def token_for_alias(self, alias: str) -> str:
        try:
            return str(self.entries[alias]["token"])
        except KeyError as exc:
            raise AuthenticationError("Unknown local identity") from exc


class SigningKeyProvider(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class OIDCIdentityProvider:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: tuple[str, ...],
        actor_id_claim: str,
        role_claim: str,
        name_claim: str,
        reviewer_acr: str | None,
        scope_claim: str,
        assist_scope: str,
        review_scope: str,
        signing_keys: SigningKeyProvider | None = None,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.actor_id_claim = actor_id_claim
        self.role_claim = role_claim
        self.name_claim = name_claim
        self.reviewer_acr = reviewer_acr
        self.scope_claim = scope_claim
        self.assist_scope = assist_scope
        self.review_scope = review_scope
        self.signing_keys = signing_keys or jwt.PyJWKClient(
            jwks_url,
            cache_keys=True,
            lifespan=300,
            timeout=5,
        )

    def authenticate(self, token: str) -> Actor:
        if not token or len(token) > 16_384:
            raise AuthenticationError("Invalid bearer token")
        try:
            signing_key = self.signing_keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
                leeway=30,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "iss",
                        "aud",
                        "sub",
                        self.actor_id_claim,
                        self.role_claim,
                    ]
                },
            )
            actor_id = UUID(str(claims[self.actor_id_claim]))
            role = Role(str(claims[self.role_claim]))
            display_name = str(claims.get(self.name_claim) or claims["sub"])
            assurance_level = str(claims["acr"]) if claims.get("acr") else None
            raw_methods = claims.get("amr", [])
            if not isinstance(raw_methods, list) or not all(
                isinstance(item, str) for item in raw_methods
            ):
                raise AuthenticationError("Invalid authentication-method claim")
            authentication_methods = list(raw_methods)
            raw_scopes = claims.get(self.scope_claim, "")
            if isinstance(raw_scopes, str):
                authorization_scopes = raw_scopes.split()
            elif isinstance(raw_scopes, list) and all(isinstance(item, str) for item in raw_scopes):
                authorization_scopes = list(raw_scopes)
            else:
                raise AuthenticationError("Invalid authorization-scope claim")
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, AttributeError) as exc:
            raise AuthenticationError("OIDC token validation failed") from exc

        if (
            role in {Role.REVIEWER, Role.COMPLIANCE}
            and self.reviewer_acr
            and assurance_level != self.reviewer_acr
        ):
            raise AuthenticationError("Step-up authentication is required")
        required_scope = (
            self.review_scope if role in {Role.REVIEWER, Role.COMPLIANCE} else self.assist_scope
        )
        if required_scope not in authorization_scopes:
            raise AuthenticationError("Required authorization scope is missing")
        return Actor(
            actor_id=actor_id,
            role=role,
            display_name=display_name,
            authentication_method="oidc",
            assurance_level=assurance_level,
            authentication_methods=authentication_methods,
            authorization_scopes=authorization_scopes,
        )


def build_identity_provider(
    settings: Settings, simulated_store: IdentityStore | None = None
) -> IdentityProvider:
    if settings.identity_provider == "simulated":
        return simulated_store or IdentityStore.from_file(settings.identities_file)
    return OIDCIdentityProvider(
        issuer=settings.oidc_issuer or "",
        audience=settings.oidc_audience or "",
        jwks_url=settings.oidc_jwks_url or "",
        algorithms=settings.oidc_algorithms,
        actor_id_claim=settings.oidc_actor_id_claim,
        role_claim=settings.oidc_role_claim,
        name_claim=settings.oidc_name_claim,
        reviewer_acr=settings.oidc_reviewer_acr,
        scope_claim=settings.oidc_scope_claim,
        assist_scope=settings.oidc_assist_scope,
        review_scope=settings.oidc_review_scope,
    )


def create_local_identities(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = {
        "alice": {
            "actor_id": "11111111-1111-4111-8111-111111111111",
            "role": "customer",
            "display_name": "Alice Example",
        },
        "bob": {
            "actor_id": "22222222-2222-4222-8222-222222222222",
            "role": "customer",
            "display_name": "Bob Example",
        },
        "reviewer": {
            "actor_id": "33333333-3333-4333-8333-333333333333",
            "role": "reviewer",
            "display_name": "Riley Reviewer",
        },
        "compliance": {
            "actor_id": "44444444-4444-4444-8444-444444444444",
            "role": "compliance",
            "display_name": "Casey Compliance",
        },
    }
    for entry in entries.values():
        entry["token"] = secrets.token_urlsafe(32)
    path.write_text(json.dumps({"identities": entries}, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> None:
    create_local_identities(Path(".local/identities.json"))
    print("Created ignored local simulated identities in .local/identities.json")
