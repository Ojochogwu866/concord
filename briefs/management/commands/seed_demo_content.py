from typing import Any

from django.core.management.base import BaseCommand

from briefs.demo import ensure_demo_content
from briefs.site_setup import ensure_site_structure


class Command(BaseCommand):
    help = (
        "Create the demo briefs and topics, translating two briefs into French. "
        "Safe to re-run."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        structure = ensure_site_structure()
        briefs = ensure_demo_content(structure.brief_index)
        self.stdout.write(
            self.style.SUCCESS(f"Demo content ready: {len(briefs)} briefs.")
        )
