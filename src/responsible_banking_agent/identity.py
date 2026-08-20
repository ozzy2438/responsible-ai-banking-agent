from __future__ import annotations

import hmac
import json
import secrets
from pathlib import Path
from typing import Any
from uuid import UUID

from .models import Actor, Role


class AuthenticationError(RuntimeError):
    pass


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
                )
        raise AuthenticationError("Invalid bearer token")

    def token_for_alias(self, alias: str) -> str:
        try:
            return str(self.entries[alias]["token"])
        except KeyError as exc:
            raise AuthenticationError("Unknown local identity") from exc


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
