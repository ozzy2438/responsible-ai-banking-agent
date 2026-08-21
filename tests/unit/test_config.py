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


def test_production_oidc_requires_file_secrets_json_logs_and_strong_reviewer_acr() -> None:
    production = _settings(
        app_env="production",
        identity_provider="oidc",
        credential_source="files",
        log_format="json",
        oidc_issuer="https://identity.example.test",
        oidc_audience="banking-agent",
        oidc_jwks_url="https://identity.example.test/jwks.json",
        oidc_reviewer_acr="urn:example:high",
        bank_data_provider="http",
        bank_api_base_url="https://api.example.test",
        bank_api_token="test-token",
        bank_api_ca_file=Path("ca.pem"),
        bank_api_client_cert_file=Path("client.pem"),
        bank_api_client_key_file=Path("client-key.pem"),
        rate_limit_backend="postgres",
        rate_limit_hmac_key="x" * 32,
    )
    production.validate()
    with pytest.raises(ValueError, match="Mounted secret files"):
        production.__class__(**{**production.__dict__, "credential_source": "env"}).validate()


def test_oidc_rejects_symmetric_algorithms() -> None:
    with pytest.raises(ValueError, match="restricted"):
        _settings(
            identity_provider="oidc",
            oidc_issuer="https://identity.example.test",
            oidc_audience="banking-agent",
            oidc_jwks_url="https://identity.example.test/jwks.json",
            oidc_algorithms=("HS256",),
        ).validate()


def test_http_bank_provider_requires_https_token_and_mtls() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        _settings(
            bank_data_provider="http",
            bank_api_base_url="http://bank.example.test",
            bank_api_token="test-token",
            bank_api_ca_file=Path("ca.pem"),
            bank_api_client_cert_file=Path("client.pem"),
            bank_api_client_key_file=Path("client-key.pem"),
        ).validate()


def test_file_secret_source_reads_fixed_non_symlink_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "database_url").write_text("postgresql://from-file\n", encoding="utf-8")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_SOURCE", "files")
    monkeypatch.setenv("SECRETS_DIR", str(tmp_path))
    settings = Settings.from_env()
    assert settings.database_url == "postgresql://from-file"

    (tmp_path / "database_url").unlink()
    (tmp_path / "actual").write_text("postgresql://hidden", encoding="utf-8")
    (tmp_path / "database_url").symlink_to(tmp_path / "actual")
    with pytest.raises(ValueError, match="non-symlink"):
        Settings.from_env()
