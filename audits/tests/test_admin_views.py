from typing import Any

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from wagtail.models import Locale

from audits.models import AuditRun, Finding
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory

FINDINGS_URL = reverse("finding:index")


@pytest.fixture
def admin_client(client: Client, django_user_model: Any) -> Client:
    user = django_user_model.objects.create_superuser(
        username="admin", email="admin@example.com", password=None
    )
    client.force_login(user)
    return client


@pytest.fixture
def run(db: None) -> AuditRun:
    return AuditRun.objects.create(
        status=AuditRun.Status.SUCCEEDED, finished_at=timezone.now(), pages_inspected=9
    )


def add_finding(
    run: AuditRun,
    page: BriefPage,
    code: str,
    *,
    language_code: str = "en",
    is_resolved: bool = False,
) -> Finding:
    return Finding.objects.create(
        run=run,
        page=page,
        locale=Locale.objects.get(language_code=language_code),
        code=code,
        severity=Finding.Severity.ERROR,
        message=f"Message for {code}.",
        resolved_at=timezone.now() if is_resolved else None,
    )


def listed_codes(client: Client, **params: str) -> set[str]:
    html = client.get(FINDINGS_URL, params).content.decode()
    known = ("i18n.missing_translation", "a11y.img_alt", "redirect.loop")
    return {code for code in known if code in html}


def test_lists_findings_with_page_and_status(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    add_finding(run, make_brief(title="Link rot"), "i18n.missing_translation")

    response = admin_client.get(FINDINGS_URL)

    html = response.content.decode()
    assert response.status_code == 200
    assert "i18n.missing_translation" in html
    assert "Link rot" in html
    assert "Open" in html


def test_findings_link_to_details_and_to_the_page_editor(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    brief = make_brief(title="Link rot")
    finding = add_finding(run, brief, "i18n.missing_translation")

    html = admin_client.get(FINDINGS_URL).content.decode()

    assert reverse("finding:inspect", args=[finding.pk]) in html
    assert reverse("wagtailadmin_pages:edit", args=[brief.pk]) in html


def test_site_findings_show_their_path(admin_client: Client, run: AuditRun) -> None:
    Finding.objects.create(
        run=run,
        code="redirect.loop",
        severity=Finding.Severity.ERROR,
        message="Redirect loop.",
        url="/en/old-path",
    )

    assert (
        "<code>/en/old-path</code>" in admin_client.get(FINDINGS_URL).content.decode()
    )


def test_findings_are_read_only(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    finding = add_finding(run, make_brief(), "a11y.img_alt")

    assert admin_client.get("/admin/finding/new/", follow=True).status_code == 404
    assert (
        admin_client.get(f"/admin/finding/edit/{finding.pk}/", follow=True).status_code
        == 404
    )
    assert (
        admin_client.get(
            f"/admin/finding/delete/{finding.pk}/", follow=True
        ).status_code
        == 404
    )
    assert (
        'href="/admin/finding/new/"'
        not in admin_client.get(FINDINGS_URL).content.decode()
    )


def test_inspect_view_shows_the_full_message(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    finding = add_finding(run, make_brief(), "a11y.img_alt")

    response = admin_client.get(reverse("finding:inspect", args=[finding.pk]))

    assert response.status_code == 200
    assert "Message for a11y.img_alt." in response.content.decode()


def test_filters_by_status_category_and_language(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    brief = make_brief()
    add_finding(run, brief, "i18n.missing_translation", language_code="fr")
    add_finding(run, brief, "a11y.img_alt")
    add_finding(run, brief, "redirect.loop", is_resolved=True)

    assert listed_codes(admin_client, status="open") == {
        "i18n.missing_translation",
        "a11y.img_alt",
    }
    assert listed_codes(admin_client, status="resolved") == {"redirect.loop"}
    assert listed_codes(admin_client, category="a11y.") == {"a11y.img_alt"}
    assert listed_codes(admin_client, category="redirect.") == {"redirect.loop"}
    assert listed_codes(admin_client, locale="fr") == {"i18n.missing_translation"}


def test_searches_codes_and_messages(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    brief = make_brief()
    add_finding(run, brief, "i18n.missing_translation")
    add_finding(run, brief, "a11y.img_alt")

    assert listed_codes(admin_client, q="img_alt") == {"a11y.img_alt"}


def test_editor_needs_view_permission(
    client: Client, django_user_model: Any, site_structure: object
) -> None:
    editor: User = django_user_model.objects.create_user(
        username="editor", password=None
    )
    editor.user_permissions.add(Permission.objects.get(codename="access_admin"))
    client.force_login(editor)
    assert client.get(FINDINGS_URL).status_code == 302

    editor.user_permissions.add(Permission.objects.get(codename="view_finding"))

    assert client.get(FINDINGS_URL).status_code == 200


def test_index_query_count_does_not_grow_with_findings(
    admin_client: Client, run: AuditRun, make_brief: BriefFactory
) -> None:
    brief = make_brief()
    add_finding(run, brief, "a11y.img_alt")
    admin_client.get(FINDINGS_URL)
    with CaptureQueriesContext(connection) as few:
        admin_client.get(FINDINGS_URL)

    for number in range(9):
        add_finding(run, make_brief(title=f"Brief {number}"), "a11y.img_alt")
    with CaptureQueriesContext(connection) as many:
        admin_client.get(FINDINGS_URL)

    assert len(many) == len(few)


def test_lists_runs(admin_client: Client, run: AuditRun) -> None:
    response = admin_client.get(reverse("auditrun:index"))

    assert response.status_code == 200
    assert "Succeeded" in response.content.decode()


def test_admin_menu_has_site_health_section(admin_client: Client) -> None:
    html = admin_client.get("/admin/").content.decode()

    assert "Site health" in html
