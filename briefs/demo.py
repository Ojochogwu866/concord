import json
from typing import Any

from django.db import transaction
from wagtail.models import Locale

from briefs.demo_content import (
    AUTHOR,
    DEMO_BRIEFS,
    DEMO_TOPICS,
    FRENCH_DEMO_TRANSLATIONS,
    TRANSLATED_BRIEF_SLUGS,
)
from briefs.models import BriefIndexPage, BriefPage, Topic
from briefs.translation import ensure_translation

DEMO_TRANSLATIONS = {"fr": FRENCH_DEMO_TRANSLATIONS}


@transaction.atomic
def ensure_demo_content(brief_index: BriefIndexPage) -> list[BriefPage]:
    topics = {
        topic["slug"]: _ensure_topic(topic, brief_index.locale) for topic in DEMO_TOPICS
    }
    briefs = [_ensure_brief(brief_index, data, topics) for data in DEMO_BRIEFS]

    for language_code, strings in DEMO_TRANSLATIONS.items():
        locale = Locale.objects.get(language_code=language_code)
        for topic in topics.values():
            ensure_translation(topic, locale, strings)
        for brief in briefs:
            if brief.slug in TRANSLATED_BRIEF_SLUGS:
                ensure_translation(brief, locale, strings)
    return briefs


def _ensure_topic(data: dict[str, str], locale: Locale) -> Topic:
    topic, _ = Topic.objects.get_or_create(
        slug=data["slug"], locale=locale, defaults={"name": data["name"]}
    )
    return topic


def _ensure_brief(
    brief_index: BriefIndexPage, data: dict[str, Any], topics: dict[str, Topic]
) -> BriefPage:
    existing: BriefPage | None = (
        BriefPage.objects.child_of(brief_index).filter(slug=data["slug"]).first()
    )
    if existing is not None:
        return existing
    brief = BriefPage(
        title=data["title"],
        slug=data["slug"],
        summary=data["summary"],
        author=AUTHOR,
        published_date=data["published_date"],
        body=json.dumps(data["body"]),
    )
    brief_index.add_child(instance=brief)
    brief.topics.set([topics[slug] for slug in data["topics"]])
    brief.save_revision().publish()
    return brief
