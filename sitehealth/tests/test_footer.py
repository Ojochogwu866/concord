from django.test import Client
from django.utils import timezone
from pytest_django.fixtures import Settings

from audits.models import AuditRun, Finding
from briefs.site_setup import SiteStructure


def footer_html(client: Client) -> str:
    html = client.get("/en/").content.decode()
    return html[html.index("<footer") :]


def test_credits_designer_without_link_until_profile_is_set(
    client: Client, site_structure: SiteStructure, settings: Settings
) -> None:
    settings.DESIGNER_PROFILE_URL = ""

    assert "Designed and built by DD" in footer_html(client)


def test_credit_links_to_designer_profile(
    client: Client, site_structure: SiteStructure, settings: Settings
) -> None:
    settings.DESIGNER_PROFILE_URL = "https://github.com/example"

    html = footer_html(client)

    assert (
        'href="https://github.com/example" rel="me" aria-label="DD on GitHub">DD</a>'
        in html
    )


def test_shows_inspection_status_before_and_after_a_run(
    client: Client, site_structure: SiteStructure
) -> None:
    assert "Not inspected yet" in footer_html(client)

    run = AuditRun.objects.create(
        status=AuditRun.Status.SUCCEEDED, finished_at=timezone.now()
    )
    Finding.objects.create(
        run=run, code="a11y.img_alt", severity=Finding.Severity.ERROR, message="x"
    )

    html = footer_html(client)
    assert "1 open finding" in html
    assert 'href="/en/#inspection-log"' in html
