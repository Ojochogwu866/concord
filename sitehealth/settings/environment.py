import os

from django.core.exceptions import ImproperlyConfigured


def get_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    return value


def get_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_required_list(name: str) -> list[str]:
    values = get_list(name)
    if not values:
        raise ImproperlyConfigured(
            f"Set the {name} environment variable to a comma-separated list."
        )
    return values
