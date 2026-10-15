from typing import Any

from django.core.management.base import BaseCommand

from briefs.site_setup import ensure_site_structure


class Command(BaseCommand):
    help = "Create the home page and briefs index if they are missing. Safe to re-run."

    def handle(self, *args: Any, **options: Any) -> None:
        structure = ensure_site_structure()
        self.stdout.write(
            self.style.SUCCESS(
                f"Site ready: home page {structure.home.pk}, "
                f"briefs index {structure.brief_index.pk}."
            )
        )
