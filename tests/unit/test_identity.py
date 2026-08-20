from uuid import UUID

import pytest

from responsible_banking_agent.identity import AuthenticationError, IdentityStore


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
