import datetime
from collections.abc import Callable

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from briefs.models import BriefIndexPage, Topic
from briefs.tests.conftest import BriefFactory


def test_lists_live_briefs_newest_first(
    client: Client, brief_index: BriefIndexPage, make_brief: BriefFactory
) -> None:
    make_brief(title="Older brief", published_date=datetime.date(2026, 1, 5))
    make_brief(title="Newer brief", published_date=datetime.date(2026, 6, 5))
    make_brief(title="Unpublished brief", is_live=False)

    response = client.get(brief_index.url)

    html = response.content.decode()
    assert response.status_code == 200
    assert html.index("Newer brief") < html.index("Older brief")
    assert "Unpublished brief" not in html


def test_filters_briefs_by_topic(
    client: Client,
    brief_index: BriefIndexPage,
    make_brief: BriefFactory,
    make_topic: Callable[[str, str], Topic],
) -> None:
    energy = make_topic("Energy", "energy")
    make_brief(title="Grid brief", topics=[energy])
    make_brief(title="Housing brief")

    response = client.get(brief_index.url, {"topic": "energy"})

    html = response.content.decode()
    assert "Grid brief" in html
    assert "Housing brief" not in html
    assert 'aria-current="page">Energy</a>' in html


def test_unknown_topic_returns_not_found(
    client: Client, brief_index: BriefIndexPage
) -> None:
    response = client.get(brief_index.url, {"topic": "missing"})

    assert response.status_code == 404


def test_shows_empty_state_when_nothing_is_published(
    client: Client, brief_index: BriefIndexPage
) -> None:
    response = client.get(brief_index.url)

    assert "No briefs have been published yet." in response.content.decode()


def test_shows_empty_state_for_topic_without_briefs(
    client: Client,
    brief_index: BriefIndexPage,
    make_brief: BriefFactory,
    make_topic: Callable[[str, str], Topic],
) -> None:
    make_topic("Transport", "transport")
    make_brief(title="Housing brief")

    response = client.get(brief_index.url, {"topic": "transport"})

    html = response.content.decode()
    assert "Nothing filed under “Transport” yet." in html
    assert "Show all briefs" in html


@pytest.mark.django_db
def test_query_count_does_not_grow_with_briefs(
    client: Client,
    brief_index: BriefIndexPage,
    make_brief: BriefFactory,
    make_topic: Callable[[str, str], Topic],
) -> None:
    topic = make_topic("Energy", "energy")
    make_brief(title="First brief", topics=[topic])
    client.get(brief_index.url)
    with CaptureQueriesContext(connection) as one_brief:
        client.get(brief_index.url)

    for number in range(4):
        make_brief(title=f"Extra brief {number}", topics=[topic])
    with CaptureQueriesContext(connection) as five_briefs:
        client.get(brief_index.url)

    assert len(five_briefs) == len(one_brief)
