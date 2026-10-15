from typing import Any

from django import forms
from django.db import models
from django.http import Http404, HttpRequest
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalManyToManyField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, PageQuerySet, TranslatableMixin
from wagtail.search import index

from briefs.blocks import PARAGRAPH_FEATURES, BriefBodyBlock, HomeBodyBlock
from briefs.forms import BriefPageForm
from briefs.reading_time import estimate_reading_minutes, stream_text

SUMMARY_MAX_LENGTH = 300
LATEST_BRIEFS_COUNT = 3


class Topic(TranslatableMixin, models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)

    panels = [FieldPanel("name"), FieldPanel("slug")]

    class Meta(TranslatableMixin.Meta):
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "slug"], name="briefs_topic_unique_slug_per_locale"
            )
        ]

    def __str__(self) -> str:
        return self.name


class HomePage(Page):
    heading = models.CharField(max_length=120, default="")
    lead = models.TextField(max_length=400, default="")
    repository_url = models.URLField(
        blank=True, help_text=_("Shown as a secondary link in the hero.")
    )
    body = StreamField(HomeBodyBlock(), blank=True)

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel(
            [FieldPanel("heading"), FieldPanel("lead"), FieldPanel("repository_url")],
            heading=_("Hero"),
        ),
        FieldPanel("body"),
    ]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["briefs.BriefIndexPage"]


class BriefIndexPage(Page):
    intro = RichTextField(blank=True, features=PARAGRAPH_FEATURES)

    content_panels = [*Page.content_panels, FieldPanel("intro")]

    parent_page_types = ["briefs.HomePage"]
    subpage_types = ["briefs.BriefPage"]
    max_count_per_parent = 1

    def get_briefs(self, topic: Topic | None = None) -> PageQuerySet:
        briefs = (
            BriefPage.objects.child_of(self).live().order_by("-published_date", "-pk")
        )
        if topic is not None:
            briefs = briefs.filter(topics=topic)
        return briefs

    def get_context(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(request, *args, **kwargs)
        topics = list(Topic.objects.filter(locale_id=self.locale_id))
        selected_topic = self._get_selected_topic(request, topics)
        context.update(
            briefs=self.get_briefs(selected_topic),
            topics=topics,
            selected_topic=selected_topic,
        )
        return context

    @staticmethod
    def _get_selected_topic(request: HttpRequest, topics: list[Topic]) -> Topic | None:
        slug = request.GET.get("topic")
        if not slug:
            return None
        for topic in topics:
            if topic.slug == slug:
                return topic
        raise Http404("Unknown topic")


class BriefPage(Page):
    summary = models.TextField(
        max_length=SUMMARY_MAX_LENGTH,
        help_text=_("One or two sentences shown in brief listings."),
    )
    author = models.CharField(max_length=120)
    published_date = models.DateField()
    topics = ParentalManyToManyField(Topic, blank=True, related_name="briefs")
    body = StreamField(BriefBodyBlock())
    reading_time = models.PositiveSmallIntegerField(
        _("reading time in minutes"), null=True, blank=True, editable=False
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("author"),
                FieldPanel("published_date"),
                FieldPanel("topics", widget=forms.CheckboxSelectMultiple),
            ],
            heading=_("Byline"),
        ),
        FieldPanel("body"),
    ]

    search_fields = [
        *Page.search_fields,
        index.SearchField("summary"),
        index.SearchField("body"),
    ]

    base_form_class = BriefPageForm

    parent_page_types = ["briefs.BriefIndexPage"]
    subpage_types: list[str] = []

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._use_topic_translations()
        self.reading_time = estimate_reading_minutes(
            f"{self.summary} {stream_text(self.body.raw_data)}"
        )
        super().save(*args, **kwargs)

    def topics_in_own_language(self) -> list[Topic]:
        return [
            topic for topic in self.topics.all() if topic.locale_id == self.locale_id
        ]

    def _use_topic_translations(self) -> None:
        # Translating a page copies its topics unchanged, so swap in this locale's ones.
        topics = list(self.topics.all())
        if all(topic.locale_id == self.locale_id for topic in topics):
            return
        self.topics = [
            topic.get_translation_or_none(self.locale) or topic for topic in topics
        ]

    @classmethod
    def latest_for_locale(
        cls, locale_id: int, limit: int = LATEST_BRIEFS_COUNT
    ) -> PageQuerySet:
        return (
            cls.objects.live()
            .filter(locale_id=locale_id)
            .order_by("-published_date", "-pk")[:limit]
        )
