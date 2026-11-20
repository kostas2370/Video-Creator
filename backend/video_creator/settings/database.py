"""Shared development and production database configuration."""

import os

from django.core.exceptions import ImproperlyConfigured


def database_config(base_dir, *, production=False, environ=None):
    values = os.environ if environ is None else environ
    engine = (values.get("DATABASE_ENGINE") or "postgresql").strip().lower()
    if engine == "sqlite":
        if production:
            raise ImproperlyConfigured("Production requires PostgreSQL.")
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }
    if engine != "postgresql":
        raise ImproperlyConfigured("DATABASE_ENGINE must be postgresql or sqlite.")
    password = values.get("POSTGRES_PASSWORD") or ""
    if not password:
        raise ImproperlyConfigured("Set POSTGRES_PASSWORD before starting PostgreSQL.")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": values.get("POSTGRES_DB") or "video_creator",
        "USER": values.get("POSTGRES_USER") or "video_creator",
        "PASSWORD": password,
        "HOST": values.get("POSTGRES_HOST") or "postgres",
        "PORT": values.get("POSTGRES_PORT") or "5432",
        # The API uses ASGI; let requests close their database connections.
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 10,
            "sslmode": values.get("POSTGRES_SSLMODE") or "prefer",
        },
    }
