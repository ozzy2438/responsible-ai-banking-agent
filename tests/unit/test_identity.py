from types import SimpleNamespace
from typing import Any
from uuid import UUID

import jwt
import pytest

from responsible_banking_agent.identity import (
    AuthenticationError,
    IdentityStore,
    OIDCIdentityProvider,
)


def test_identity_is_server_derived_from_token() -> None:
    store = IdentityStore(
        {
            "alice": {
                "token": "token-alice",
                "actor_id": "11111111-1111-4111-8111-111111111111",
                "role": "customer",
                "display_name": "Alice",
            }
        }
    )
    actor = store.authenticate("token-alice")
    assert actor.actor_id == UUID("11111111-1111-4111-8111-111111111111")
    with pytest.raises(AuthenticationError):
        store.authenticate("wrong")


class FakeSigningKeys:
    def get_signing_key_from_jwt(self, token: str) -> Any:
        assert token == "signed-token"
        return SimpleNamespace(key="public-key")


def _oidc_provider() -> OIDCIdentityProvider:
    return OIDCIdentityProvider(
        issuer="https://identity.example.test",
        audience="banking-agent",
        jwks_url="https://identity.example.test/jwks.json",
        algorithms=("RS256",),
        actor_id_claim="actor_id",
        role_claim="role",
        name_claim="name",
        reviewer_acr="urn:example:high",
        scope_claim="scope",
        assist_scope="banking:assist",
        review_scope="banking:review",
        signing_keys=FakeSigningKeys(),
    )


def test_oidc_identity_is_derived_from_verified_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = {
        "sub": "reviewer-123",
        "actor_id": "33333333-3333-4333-8333-333333333333",
        "role": "reviewer",
        "name": "Riley Reviewer",
        "acr": "urn:example:high",
        "amr": ["pwd", "mfa"],
        "scope": "banking:assist banking:review",
    }

    def decode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert args == ("signed-token", "public-key")
        assert kwargs["algorithms"] == ["RS256"]
        assert kwargs["audience"] == "banking-agent"
        assert kwargs["issuer"] == "https://identity.example.test"
        return claims

    monkeypatch.setattr(jwt, "decode", decode)
    actor = _oidc_provider().authenticate("signed-token")
    assert actor.actor_id == UUID("33333333-3333-4333-8333-333333333333")
    assert actor.authentication_method == "oidc"
    assert actor.authentication_methods == ["pwd", "mfa"]
    assert actor.authorization_scopes == ["banking:assist", "banking:review"]


def test_oidc_reviewer_requires_configured_step_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "reviewer-123",
            "actor_id": "33333333-3333-4333-8333-333333333333",
            "role": "reviewer",
            "acr": "urn:example:low",
            "scope": "banking:review",
        },
    )
    with pytest.raises(AuthenticationError, match="Step-up"):
        _oidc_provider().authenticate("signed-token")


def test_oidc_identity_requires_role_appropriate_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "reviewer-123",
            "actor_id": "33333333-3333-4333-8333-333333333333",
            "role": "reviewer",
            "acr": "urn:example:high",
            "scope": "banking:assist",
        },
    )
    with pytest.raises(AuthenticationError, match="scope"):
        _oidc_provider().authenticate("signed-token")


def test_oidc_validation_failure_is_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise jwt.InvalidTokenError("detailed provider message")

    monkeypatch.setattr(jwt, "decode", reject)
    with pytest.raises(AuthenticationError, match="OIDC token validation failed"):
        _oidc_provider().authenticate("signed-token")
