from importlib import import_module

from django.apps import AppConfig


class AuditsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audits"

    def ready(self) -> None:
        import_module("audits.checks")
