from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_NON_PRODUCTION_ENVIRONMENTS = {"local", "test"}
_ALLOWED_OIDC_ALGORITHMS = {"RS256", "ES256"}


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _read_secret_file(directory: Path, name: str) -> str | None:
    path = directory / name.lower()
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Secret file must be a regular non-symlink file: {path}")
    if path.stat().st_size > 16_384:
        raise ValueError(f"Secret file is unexpectedly large: {path}")
    value = path.read_text(encoding="utf-8").strip()
    if not value or "\n" in value or "\r" in value:
        raise ValueError(f"Secret file must contain one non-empty value: {path}")
    return value


def _is_https(value: str | None) -> bool:
    return bool(value and urlparse(value).scheme == "https")


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
    credential_source: str = "env"
    secrets_dir: Path = Path("/run/secrets/responsible-banking-agent")
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: tuple[str, ...] = ("RS256",)
    oidc_actor_id_claim: str = "actor_id"
    oidc_role_claim: str = "role"
    oidc_name_claim: str = "name"
    oidc_reviewer_acr: str | None = None
    oidc_scope_claim: str = "scope"
    oidc_assist_scope: str = "banking:assist"
    oidc_review_scope: str = "banking:review"
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "testserver")
    log_format: str = "text"
    bank_data_provider: str = "synthetic"
    bank_api_base_url: str | None = None
    bank_api_token: str | None = None
    bank_api_ca_file: Path | None = None
    bank_api_client_cert_file: Path | None = None
    bank_api_client_key_file: Path | None = None
    bank_api_timeout_seconds: float = 3.0
    rate_limit_backend: str = "memory"
    rate_limit_hmac_key: str | None = None
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    max_request_body_bytes: int = 16_384

    @classmethod
    def from_env(cls) -> Settings:
        credential_source = os.getenv("SECRET_SOURCE", "env")
        secrets_dir = Path(os.getenv("SECRETS_DIR", "/run/secrets/responsible-banking-agent"))

        def secret(name: str, *, required: bool = False) -> str | None:
            value = (
                _read_secret_file(secrets_dir, name)
                if credential_source == "files"
                else os.getenv(name)
            )
            if required and not value:
                raise ValueError(f"{name} is required from {credential_source} credential source")
            return value

        settings = cls(
            app_env=os.getenv("APP_ENV", "local"),
            identity_provider=os.getenv("IDENTITY_PROVIDER", "simulated"),
            reasoning_provider=os.getenv("REASONING_PROVIDER", "stub"),
            database_url=secret("DATABASE_URL", required=True) or "",
            migration_database_url=secret("MIGRATION_DATABASE_URL") or "",
            app_db_password=secret("APP_DB_PASSWORD") or "",
            identities_file=Path(os.getenv("SIMULATED_IDENTITIES_FILE", ".local/identities.json")),
            policy_bundle_path=Path(os.getenv("POLICY_BUNDLE_PATH", "policies")),
            openai_api_key=secret("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL"),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
            credential_source=credential_source,
            secrets_dir=secrets_dir,
            oidc_issuer=os.getenv("OIDC_ISSUER"),
            oidc_audience=os.getenv("OIDC_AUDIENCE"),
            oidc_jwks_url=os.getenv("OIDC_JWKS_URL"),
            oidc_algorithms=_csv(os.getenv("OIDC_ALGORITHMS", "RS256")),
            oidc_actor_id_claim=os.getenv("OIDC_ACTOR_ID_CLAIM", "actor_id"),
            oidc_role_claim=os.getenv("OIDC_ROLE_CLAIM", "role"),
            oidc_name_claim=os.getenv("OIDC_NAME_CLAIM", "name"),
            oidc_reviewer_acr=os.getenv("OIDC_REVIEWER_ACR"),
            oidc_scope_claim=os.getenv("OIDC_SCOPE_CLAIM", "scope"),
            oidc_assist_scope=os.getenv("OIDC_ASSIST_SCOPE", "banking:assist"),
            oidc_review_scope=os.getenv("OIDC_REVIEW_SCOPE", "banking:review"),
            allowed_hosts=_csv(os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")),
            log_format=os.getenv("LOG_FORMAT", "text"),
            bank_data_provider=os.getenv("BANK_DATA_PROVIDER", "synthetic"),
            bank_api_base_url=os.getenv("BANK_API_BASE_URL"),
            bank_api_token=secret("BANK_API_TOKEN"),
            bank_api_ca_file=(Path(value) if (value := os.getenv("BANK_API_CA_FILE")) else None),
            bank_api_client_cert_file=(
                Path(value) if (value := os.getenv("BANK_API_CLIENT_CERT_FILE")) else None
            ),
            bank_api_client_key_file=(
                Path(value) if (value := os.getenv("BANK_API_CLIENT_KEY_FILE")) else None
            ),
            bank_api_timeout_seconds=float(os.getenv("BANK_API_TIMEOUT_SECONDS", "3")),
            rate_limit_backend=os.getenv("RATE_LIMIT_BACKEND", "memory"),
            rate_limit_hmac_key=secret("RATE_LIMIT_HMAC_KEY"),
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "120")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            max_request_body_bytes=int(os.getenv("MAX_REQUEST_BODY_BYTES", "16384")),
        )
        settings.validate()
        return settings

    @property
    def is_production_like(self) -> bool:
        return self.app_env not in _NON_PRODUCTION_ENVIRONMENTS

    def validate(self) -> None:
        if self.app_env not in {"local", "test", "staging", "production"}:
            raise ValueError("APP_ENV must be local, test, staging, or production")
        if self.credential_source not in {"env", "files"}:
            raise ValueError("SECRET_SOURCE must be env or files")
        if self.identity_provider not in {"simulated", "oidc"}:
            raise ValueError("IDENTITY_PROVIDER must be simulated or oidc")
        if self.is_production_like and self.identity_provider != "oidc":
            raise ValueError("OIDC identity is required outside local/test")
        if self.is_production_like and self.credential_source != "files":
            raise ValueError("Mounted secret files are required outside local/test")
        if self.is_production_like and not self.session_cookie_secure:
            raise ValueError("Secure cookies are required outside local/test")
        if self.is_production_like and self.log_format != "json":
            raise ValueError("JSON logging is required outside local/test")
        if not self.allowed_hosts or (self.is_production_like and "*" in self.allowed_hosts):
            raise ValueError("Explicit ALLOWED_HOSTS are required")

        if self.identity_provider == "oidc":
            if not all((self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url)):
                raise ValueError("OIDC mode requires issuer, audience, and JWKS URL")
            if not _is_https(self.oidc_issuer) or not _is_https(self.oidc_jwks_url):
                raise ValueError("OIDC issuer and JWKS URL must use HTTPS")
            if not self.oidc_algorithms or not set(self.oidc_algorithms).issubset(
                _ALLOWED_OIDC_ALGORITHMS
            ):
                raise ValueError("OIDC algorithms are restricted to RS256 and ES256")
            if self.is_production_like and not self.oidc_reviewer_acr:
                raise ValueError("OIDC_REVIEWER_ACR is required outside local/test")
            if not self.oidc_assist_scope or not self.oidc_review_scope:
                raise ValueError("OIDC assist and review scopes are required")

        if self.reasoning_provider not in {"stub", "openai"}:
            raise ValueError("Unsupported reasoning provider")
        if self.reasoning_provider == "openai" and not (self.openai_api_key and self.openai_model):
            raise ValueError("OpenAI mode requires OPENAI_API_KEY and explicit OPENAI_MODEL")

        if self.bank_data_provider not in {"synthetic", "http"}:
            raise ValueError("BANK_DATA_PROVIDER must be synthetic or http")
        if self.is_production_like and self.bank_data_provider != "http":
            raise ValueError("A real bank data provider is required outside local/test")
        if self.bank_data_provider == "http":
            if not _is_https(self.bank_api_base_url):
                raise ValueError("BANK_API_BASE_URL must use HTTPS")
            if not self.bank_api_token:
                raise ValueError("BANK_API_TOKEN is required for the HTTP bank provider")
            if not all(
                (
                    self.bank_api_ca_file,
                    self.bank_api_client_cert_file,
                    self.bank_api_client_key_file,
                )
            ):
                raise ValueError("The HTTP bank provider requires CA and mTLS certificate files")
        if not 0.1 <= self.bank_api_timeout_seconds <= 10:
            raise ValueError("BANK_API_TIMEOUT_SECONDS must be between 0.1 and 10")

        if self.rate_limit_backend not in {"memory", "postgres"}:
            raise ValueError("RATE_LIMIT_BACKEND must be memory or postgres")
        if self.is_production_like and self.rate_limit_backend != "postgres":
            raise ValueError("PostgreSQL rate limiting is required outside local/test")
        if self.rate_limit_backend == "postgres" and (
            not self.rate_limit_hmac_key or len(self.rate_limit_hmac_key) < 32
        ):
            raise ValueError("PostgreSQL rate limiting requires a 32+ character HMAC key")
        if not 1 <= self.rate_limit_requests <= 10_000:
            raise ValueError("RATE_LIMIT_REQUESTS must be between 1 and 10000")
        if not 1 <= self.rate_limit_window_seconds <= 3600:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be between 1 and 3600")
        if not 4096 <= self.max_request_body_bytes <= 1_048_576:
            raise ValueError("MAX_REQUEST_BODY_BYTES must be between 4096 and 1048576")
