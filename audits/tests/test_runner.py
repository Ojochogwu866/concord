import pytest
from django.core.management import CommandError, call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from wagtail.models import Locale, Page

from audits.checks.translations import MISSING_TRANSLATION
from audits.models import AuditRun, Finding
from audits.rendering import PageRenderError
from audits.runner import run_page_audit
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory

ACCESSIBLE_HTML = '<html lang="en"><body><h1>Page</h1></body></html>'


@pytest.fixture
def static_render(monkeypatch: pytest.MonkeyPatch) -> None:
    def render(path: str) -> str:
        return ACCESSIBLE_HTML.replace('lang="en"', f'lang="{path.split("/")[1]}"')

    monkeypatch.setattr("audits.runner.render_page_html", render)


def open_findings(code: str = MISSING_TRANSLATION) -> list[Finding]:
    return list(Finding.objects.filter(code=code, resolved_at__isnull=True))


def test_records_successful_run_with_findings(make_brief: BriefFactory) -> None:
    brief = make_brief(title="Untranslated brief")

    run = run_page_audit()

    assert run.status == AuditRun.Status.SUCCEEDED
    assert run.pages_inspected == Page.objects.live().filter(depth__gt=1).count()
    assert run.finished_at is not None
    french = Locale.objects.get(language_code="fr")
    assert [(f.page_id, f.locale_id) for f in open_findings()] == [
        (brief.pk, french.pk)
    ]
    assert run.summary["open_by_code"] == {MISSING_TRANSLATION: 1}


def test_rerun_keeps_one_open_finding_per_problem(make_brief: BriefFactory) -> None:
    make_brief()
    run_page_audit()
    first = open_findings()[0]

    run_page_audit()

    findings = open_findings()
    assert [finding.pk for finding in findings] == [first.pk]
    assert findings[0].last_seen_at > first.last_seen_at


def test_resolves_finding_once_problem_is_fixed(make_brief: BriefFactory) -> None:
    brief = make_brief()
    run_page_audit()

    brief.copy_for_translation(
        Locale.objects.get(language_code="fr")
    ).save_revision().publish()
    run_page_audit()

    assert open_findings() == []
    assert Finding.objects.get(page=brief).resolved_at is not None


def test_failed_page_is_recorded_and_keeps_its_findings(
    make_brief: BriefFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    brief = make_brief()
    run_page_audit()

    def render(path: str) -> str:
        if path == brief.url:
            raise PageRenderError("Rendering returned HTTP 500.")
        return ACCESSIBLE_HTML

    monkeypatch.setattr("audits.runner.render_page_html", render)
    run = run_page_audit()

    assert run.status == AuditRun.Status.PARTIAL
    assert run.pages_failed == 1
    assert run.summary["failed_pages"][0]["page_id"] == brief.pk
    assert [f.page_id for f in open_findings()] == [brief.pk]


def test_run_fails_when_no_page_renders(
    make_brief: BriefFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_brief()

    def render(path: str) -> str:
        raise PageRenderError("Rendering returned HTTP 503.")

    monkeypatch.setattr("audits.runner.render_page_html", render)

    assert run_page_audit().status == AuditRun.Status.FAILED
    with pytest.raises(CommandError, match="No page could be rendered"):
        call_command("run_audits")


def test_unexpected_error_marks_run_failed_and_propagates(
    make_brief: BriefFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_brief()

    def render(path: str) -> str:
        raise RuntimeError("database went away")

    monkeypatch.setattr("audits.runner.render_page_html", render)

    with pytest.raises(RuntimeError):
        run_page_audit()
    assert AuditRun.objects.get().status == AuditRun.Status.FAILED


def test_query_count_does_not_grow_with_pages(
    make_brief: BriefFactory, static_render: None
) -> None:
    make_brief(title="First")
    run_page_audit()
    with CaptureQueriesContext(connection) as few_pages:
        run_page_audit()

    for number in range(4):
        make_brief(title=f"Extra {number}")
    run_page_audit()
    with CaptureQueriesContext(connection) as more_pages:
        run_page_audit()

    assert len(more_pages) == len(few_pages)


def test_command_reports_the_run(
    make_brief: BriefFactory, capsys: pytest.CaptureFixture[str]
) -> None:
    make_brief()

    call_command("run_audits")

    output = capsys.readouterr().out
    assert "inspected" in output
    assert "1 open findings" in output


def test_rendering_reaches_real_pages(make_brief: BriefFactory) -> None:
    brief = make_brief()

    run_page_audit()

    assert BriefPage.objects.get(pk=brief.pk).live
    assert AuditRun.objects.get().pages_failed == 0
