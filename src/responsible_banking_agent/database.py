from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg
from psycopg import sql

from .config import Settings


def migrate(settings: Settings, migrations_dir: Path = Path("migrations")) -> None:
    if not settings.migration_database_url or not settings.app_db_password:
        raise ValueError("Migration URL and application DB password are required")
    with (
        psycopg.connect(settings.migration_database_url, autocommit=True) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'banking_app'")
        password = sql.Literal(settings.app_db_password)
        if cursor.fetchone() is None:
            cursor.execute(sql.SQL("CREATE ROLE banking_app LOGIN PASSWORD {}").format(password))
        else:
            cursor.execute(sql.SQL("ALTER ROLE banking_app PASSWORD {}").format(password))
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    name text PRIMARY KEY,
                    sha256 text NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
        )
        for migration in sorted(migrations_dir.glob("*.sql")):
            raw = migration.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            cursor.execute(
                "SELECT sha256 FROM schema_migrations WHERE name = %s", (migration.name,)
            )
            row = cursor.fetchone()
            if row:
                if row[0] != digest:
                    raise RuntimeError(f"Applied migration changed: {migration.name}")
                continue
            with connection.transaction():
                cursor.execute(raw.decode("utf-8"))
                cursor.execute(
                    "INSERT INTO schema_migrations(name, sha256) VALUES (%s, %s)",
                    (migration.name, digest),
                )


def main() -> None:
    migrate(Settings.from_env())
