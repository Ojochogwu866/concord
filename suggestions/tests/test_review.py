from typing import Any

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from audits.models import AuditRun, Finding
from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory
from suggestions.models import ProviderCall, Suggestion, Task
from suggestions.review import ReviewError, approve, reject

PROPOSED_TITLE = "Grid storage after the auctions"


@pytest.fixture
def editor(django_user_model: Any) -> User:
    user: User = django_user_model.objects.create_superuser(
        username="editor", email="editor@example.com", password=None
    )
    return user


@pytest.fixture
def suggestion(make_brief: BriefFactory) -> Suggestion:
    brief = make_brief(title="Grid storage after the 2025 auctions in nine countries")
    run = AuditRun.objects.create(
        status=AuditRun.Status.SUCCEEDED, finished_at=timezone.now()
    )
    finding = Finding.objects.create(
        run=run,
        page=brief,
        locale=brief.locale,
        code="seo.long_title",
        severity=Finding.Severity.WARNING,
        message="Title is too long.",
    )
    call = ProviderCall.objects.create(
        task=Task.SEO_TITLE,
        provider="test",
        prompt="Write a title.",
        response=PROPOSED_TITLE,
    )
    return Suggestion.objects.create(
        finding=finding, task=Task.SEO_TITLE, proposed_text=PROPOSED_TITLE, call=call
    )


def test_approving_saves_a_draft_without_publishing(
    suggestion: Suggestion, editor: User
) -> None:
    approve(suggestion, editor)

    page = BriefPage.objects.get(pk=suggestion.finding.page_id)
    assert page.seo_title == ""
    assert page.has_unpublished_changes
    assert page.get_latest_revision_as_object().seo_title == PROPOSED_TITLE
    suggestion.refresh_from_db()
    assert (suggestion.status, suggestion.reviewed_by) == (
        Suggestion.Status.APPROVED,
        editor,
    )


def test_approving_keeps_an_editors_unpublished_draft(
    suggestion: Suggestion, editor: User
) -> None:
    page = BriefPage.objects.get(pk=suggestion.finding.page_id)
    page.summary = "An unpublished edit."
    page.save_revision(user=editor)

    approve(suggestion, editor)

    draft = BriefPage.objects.get(pk=page.pk).get_latest_revision_as_object()
    assert (draft.summary, draft.seo_title) == ("An unpublished edit.", PROPOSED_TITLE)


def test_rejecting_records_the_note(suggestion: Suggestion, editor: User) -> None:
    reject(suggestion, editor, "  Too vague.  ")

    suggestion.refresh_from_db()
    assert (suggestion.status, suggestion.review_note) == (
        Suggestion.Status.REJECTED,
        "Too vague.",
    )


def test_a_suggestion_is_reviewed_only_once(
    suggestion: Suggestion, editor: User
) -> None:
    reject(suggestion, editor)

    with pytest.raises(ReviewError, match="already been reviewed"):
        approve(suggestion, editor)


def test_reviewing_requires_permission_to_edit_the_page(
    suggestion: Suggestion, django_user_model: Any
) -> None:
    viewer = django_user_model.objects.create_user(username="viewer", password=None)

    with pytest.raises(ReviewError, match="permission to edit"):
        approve(suggestion, viewer)


def test_review_screen_shows_current_and_proposed_text(
    client: Client, suggestion: Suggestion, editor: User
) -> None:
    client.force_login(editor)

    html = client.get(
        reverse("suggestion:inspect", args=[suggestion.pk])
    ).content.decode()

    assert PROPOSED_TITLE in html
    assert "Approve as draft" in html


def test_approve_and_reject_only_accept_post(
    client: Client, suggestion: Suggestion, editor: User
) -> None:
    client.force_login(editor)

    assert (
        client.get(reverse("suggestion:approve", args=[suggestion.pk])).status_code
        == 405
    )

    response = client.post(reverse("suggestion:approve", args=[suggestion.pk]))

    assert response.status_code == 302
    suggestion.refresh_from_db()
    assert suggestion.status == Suggestion.Status.APPROVED


def test_editor_without_view_permission_cannot_open_suggestions(
    client: Client, django_user_model: Any, suggestion: Suggestion
) -> None:
    user = django_user_model.objects.create_user(username="limited", password=None)
    user.user_permissions.add(Permission.objects.get(codename="access_admin"))
    client.force_login(user)

    assert client.get(reverse("suggestion:index")).status_code == 302
