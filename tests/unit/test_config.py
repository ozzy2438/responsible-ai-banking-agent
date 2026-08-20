from pathlib import Path

import pytest

from responsible_banking_agent.config import Settings


def _settings(**changes: object) -> Settings:
    values = {
        "app_env": "test",
        "identity_provider": "simulated",
        "reasoning_provider": "stub",
        "database_url": "postgresql://example",
        "migration_database_url": "postgresql://example",
        "app_db_password": "test-only",
        "identities_file": Path("identities.json"),
        "policy_bundle_path": Path("policies"),
        "openai_api_key": None,
        "openai_model": None,
    }
    values.update(changes)
    return Settings(**values)  # type: ignore[arg-type]


def test_openai_mode_requires_key_and_model() -> None:
    with pytest.raises(ValueError):
        _settings(reasoning_provider="openai").validate()


def test_simulated_identity_fails_outside_local_or_test() -> None:
    with pytest.raises(ValueError):
        _settings(app_env="production").validate()
