from collections.abc import Callable

import pytest
from django.test import Client
from pytest_django.fixtures import DjangoCaptureOnCommitCallbacks
from wagtail.contrib.redirects.models import Redirect

from briefs.models import BriefPage
from briefs.tests.fixtures import BriefFactory

RenameBrief = Callable[[BriefPage, str], BriefPage]


@pytest.fixture
def rename(
    django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks,
) -> RenameBrief:
    def rename_brief(brief: BriefPage, slug: str) -> BriefPage:
        # Wagtail sends page_slug_changed, which creates the redirect, on commit.
        with django_capture_on_commit_callbacks(execute=True):
            brief.slug = slug
            brief.save_revision().publish()
        renamed: BriefPage = BriefPage.objects.get(pk=brief.pk)
        return renamed

    return rename_brief


def test_renaming_a_brief_permanently_redirects_its_old_url(
    client: Client, make_brief: BriefFactory, rename: RenameBrief
) -> None:
    brief = make_brief(title="Grid storage")
    old_url = brief.url

    renamed = rename(brief, "grid-storage-auctions")
    response = client.get(old_url)

    assert response.status_code == 301
    assert response["Location"] == renamed.url
    assert client.get(renamed.url).status_code == 200


def test_rename_creates_one_automatic_redirect_with_language_prefix(
    make_brief: BriefFactory, rename: RenameBrief
) -> None:
    brief = make_brief(title="Grid storage")

    rename(brief, "grid-storage-auctions")

    redirect = Redirect.objects.get()
    assert redirect.old_path == "/en/briefs/grid-storage"
    assert redirect.redirect_page_id == brief.pk
    assert redirect.automatically_created
