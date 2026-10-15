from django.contrib.auth.models import AnonymousUser, User
from django.db import transaction
from django.utils import timezone
from wagtail.models import Page, Revision

from suggestions.models import Suggestion, Task

FIELD_FOR_TASK = {
    Task.SEO_TITLE: "seo_title",
    Task.META_DESCRIPTION: "search_description",
}


class ReviewError(Exception):
    pass


def can_review(suggestion: Suggestion, user: User | AnonymousUser) -> bool:
    page = suggestion.finding.page
    return page is not None and bool(page.permissions_for_user(user).can_edit())


@transaction.atomic
def approve(suggestion: Suggestion, user: User | AnonymousUser) -> Revision:
    page = _check_reviewable(suggestion, user)
    # Re-read and lock the page so the draft builds on its true latest revision and
    # never discards unpublished edits saved since this suggestion was loaded.
    locked_page = Page.objects.select_for_update().get(pk=page.pk)
    draft = locked_page.get_latest_revision_as_object()
    setattr(draft, FIELD_FOR_TASK[Task(suggestion.task)], suggestion.proposed_text)
    revision: Revision = draft.save_revision(user=user, log_action=True)
    _mark_reviewed(suggestion, user, Suggestion.Status.APPROVED)
    return revision


@transaction.atomic
def reject(suggestion: Suggestion, user: User | AnonymousUser, note: str = "") -> None:
    _check_reviewable(suggestion, user)
    suggestion.review_note = note.strip()
    _mark_reviewed(suggestion, user, Suggestion.Status.REJECTED)


def _check_reviewable(suggestion: Suggestion, user: User | AnonymousUser) -> Page:
    if suggestion.status != Suggestion.Status.PENDING:
        raise ReviewError("This suggestion has already been reviewed.")
    page = suggestion.finding.page
    if page is None:
        raise ReviewError("The page this suggestion was for no longer exists.")
    if not can_review(suggestion, user):
        raise ReviewError("You need permission to edit this page.")
    return page


def _mark_reviewed(
    suggestion: Suggestion, user: User | AnonymousUser, status: Suggestion.Status
) -> None:
    suggestion.status = status
    suggestion.reviewed_by = user if isinstance(user, User) else None
    suggestion.reviewed_at = timezone.now()
    suggestion.save(
        update_fields=["status", "reviewed_by", "reviewed_at", "review_note"]
    )
