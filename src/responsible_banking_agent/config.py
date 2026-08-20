from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    identity_provider: str
    reasoning_provider: str
    database_url: str
    migration_database_url: str
    app_db_password: str
    identities_file: Path
    policy_bundle_path: Path
    openai_api_key: str | None
    openai_model: str | None
    session_cookie_secure: bool = True

    @classmethod
    def from_env(cls) -> Settings:
        settings = cls(
            app_env=os.getenv("APP_ENV", "local"),
            identity_provider=os.getenv("IDENTITY_PROVIDER", "simulated"),
            reasoning_provider=os.getenv("REASONING_PROVIDER", "stub"),
            database_url=os.environ["DATABASE_URL"],
            migration_database_url=os.getenv("MIGRATION_DATABASE_URL", ""),
            app_db_password=os.getenv("APP_DB_PASSWORD", ""),
            identities_file=Path(os.getenv("SIMULATED_IDENTITIES_FILE", ".local/identities.json")),
            policy_bundle_path=Path(os.getenv("POLICY_BUNDLE_PATH", "policies")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL"),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.app_env not in {"local", "test"} and self.identity_provider == "simulated":
            raise ValueError("Simulated identity is forbidden outside local/test")
        if self.reasoning_provider not in {"stub", "openai"}:
            raise ValueError("Unsupported reasoning provider")
        if self.reasoning_provider == "openai" and not (self.openai_api_key and self.openai_model):
            raise ValueError("OpenAI mode requires OPENAI_API_KEY and explicit OPENAI_MODEL")
