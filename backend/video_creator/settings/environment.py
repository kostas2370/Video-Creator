import os

from django.core.exceptions import ImproperlyConfigured


def env_bool(name, *, default):
    value = os.getenv(name, "").strip().casefold()
    if not value:
        return default
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be true or false.")
