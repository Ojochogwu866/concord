import datetime
from collections.abc import Callable, Iterable
from typing import Any

import pytest

from briefs.models import BriefIndexPage, BriefPage, Topic
from briefs.site_setup import SiteStructure, ensure_site_structure

BriefFactory = Callable[..., BriefPage]


@pytest.fixture
def site_structure(db: None) -> SiteStructure:
    return ensure_site_structure()


@pytest.fixture
def brief_index(site_structure: SiteStructure) -> BriefIndexPage:
    return site_structure.brief_index


@pytest.fixture
def make_brief(brief_index: BriefIndexPage) -> BriefFactory:
    def factory(
        title: str = "Grid storage after the 2025 auctions",
        published_date: datetime.date = datetime.date(2026, 9, 1),
        topics: Iterable[Topic] = (),
        is_live: bool = True,
        **fields: Any,
    ) -> BriefPage:
        brief = BriefPage(
            title=title,
            summary=fields.pop("summary", "What changed and who it affects."),
            author=fields.pop("author", "Dickson Ojochogwu"),
            published_date=published_date,
            live=is_live,
            **fields,
        )
        brief_index.add_child(instance=brief)
        brief.topics.set(topics)
        brief.save()
        return brief

    return factory


@pytest.fixture
def make_topic(db: None) -> Callable[[str, str], Topic]:
    def factory(name: str, slug: str) -> Topic:
        return Topic.objects.create(name=name, slug=slug)

    return factory
