import datetime

from django.test import Client
from django.utils import timezone
from wagtail.models import Locale

from audits.models import AuditRun, Finding
from audits.reports import LOG_ENTRY_LIMIT
from audits.runner import run_page_audit
from briefs.models import BriefPage
from briefs.site_setup import SiteStructure
from briefs.tests.fixtures import BriefFactory


def home_html(client: Client, language: str = "en") -> str:
    return client.get(f"/{language}/").content.decode()


def finished_run(status: AuditRun.Status = AuditRun.Status.SUCCEEDED) -> AuditRun:
    return AuditRun.objects.create(
        status=status, finished_at=timezone.now(), pages_inspected=9
    )


def add_finding(
    run: AuditRun, page: BriefPage, code: str, severity: Finding.Severity
) -> Finding:
    return Finding.objects.create(
        run=run,
        page=page,
        locale=page.locale,
        code=code,
        severity=severity,
        message="Example finding.",
    )


def test_shows_empty_state_before_first_run(
    client: Client, site_structure: SiteStructure
) -> None:
    assert "No inspection has run yet." in home_html(client)


def test_shows_first_run_failure(client: Client, site_structure: SiteStructure) -> None:
    finished_run(AuditRun.Status.FAILED)

    assert "The first inspection failed." in home_html(client)


def test_lists_findings_from_a_real_run(
    client: Client, make_brief: BriefFactory
) -> None:
    make_brief(title="Untranslated brief")
    run_page_audit()

    html = home_html(client)

    assert "Untranslated brief" in html
    assert "i18n.missing_translation" in html
    assert '<span class="severity-error">Error</span>' in html


def test_shows_all_clear_when_nothing_is_open(
    client: Client, site_structure: SiteStructure
) -> None:
    run_page_audit()

    assert "All clear." in home_html(client)


def test_notes_pages_that_could_not_be_inspected(
    client: Client, make_brief: BriefFactory
) -> None:
    run = finished_run(AuditRun.Status.PARTIAL)
    run.pages_failed = 2
    run.save()
    add_finding(run, make_brief(), "i18n.missing_translation", Finding.Severity.ERROR)

    assert "2 pages couldn’t be inspected on this run" in home_html(client)


def test_keeps_last_results_when_latest_run_failed(
    client: Client, make_brief: BriefFactory
) -> None:
    run = finished_run()
    add_finding(run, make_brief(), "i18n.missing_translation", Finding.Severity.ERROR)
    AuditRun.objects.create(
        status=AuditRun.Status.FAILED,
        started_at=timezone.now() + datetime.timedelta(minutes=5),
        finished_at=timezone.now() + datetime.timedelta(minutes=6),
    )

    html = home_html(client)

    assert "These results are from the last run that finished." in html
    assert "i18n.missing_translation" in html


def test_shows_errors_first_and_counts_the_rest(
    client: Client, make_brief: BriefFactory
) -> None:
    run = finished_run()
    brief = make_brief()
    for number in range(LOG_ENTRY_LIMIT + 1):
        add_finding(run, brief, f"seo.warning_{number}", Finding.Severity.WARNING)
    add_finding(run, brief, "a11y.img_alt", Finding.Severity.ERROR)

    html = home_html(client)

    assert html.index("a11y.img_alt") < html.index("seo.warning_")
    assert html.count('class="severity-') == LOG_ENTRY_LIMIT
    assert "2 more findings are in the Wagtail admin." in html


def test_french_log_names_pages_in_french(
    client: Client, make_brief: BriefFactory
) -> None:
    brief = make_brief(title="Grid storage")
    translation = brief.copy_for_translation(Locale.objects.get(language_code="fr"))
    translation.title = "Stockage sur le réseau"
    translation.save_revision().publish()
    add_finding(
        finished_run(), brief, "i18n.stale_translation", Finding.Severity.WARNING
    )

    html = home_html(client, "fr")

    assert "Stockage sur le réseau" in html
    assert "Avertissement" in html
