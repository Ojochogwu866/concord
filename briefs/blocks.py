from typing import Any

from django.apps import apps
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageBlock

PARAGRAPH_FEATURES = ["bold", "italic", "link", "ol", "ul"]


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=120)
    level = blocks.ChoiceBlock(
        choices=[("h2", _("Section heading")), ("h3", _("Subheading"))],
        default="h2",
    )

    class Meta:
        icon = "title"
        template = "briefs/blocks/heading.html"


class FigureBlock(blocks.StructBlock):
    image = ImageBlock()
    caption = blocks.CharBlock(required=False, max_length=250)

    class Meta:
        icon = "image"
        template = "briefs/blocks/figure.html"


class QuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock()
    attribution = blocks.CharBlock(required=False, max_length=120)

    class Meta:
        icon = "openquote"
        template = "briefs/blocks/quote.html"


class BriefBodyBlock(blocks.StreamBlock):
    heading = HeadingBlock()
    paragraph = blocks.RichTextBlock(features=PARAGRAPH_FEATURES)
    figure = FigureBlock()
    quote = QuoteBlock()


class InspectionLogBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=120)
    note = blocks.TextBlock(required=False, max_length=300)

    class Meta:
        icon = "list-ul"
        template = "briefs/blocks/inspection_log.html"


class LatestBriefsBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=120)
    note = blocks.TextBlock(required=False, max_length=300)

    class Meta:
        icon = "doc-full"
        template = "briefs/blocks/latest_briefs.html"

    def get_context(
        self, value: blocks.StructValue, parent_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context)
        page = (parent_context or {}).get("page")
        brief_model = apps.get_model("briefs", "BriefPage")
        context["briefs"] = (
            brief_model.latest_for_locale(page.locale_id) if page else []
        )
        return context


class TextSectionBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=120)
    body = blocks.RichTextBlock(features=PARAGRAPH_FEATURES)

    class Meta:
        icon = "pilcrow"
        template = "briefs/blocks/text_section.html"


class HomeBodyBlock(blocks.StreamBlock):
    inspection_log = InspectionLogBlock()
    latest_briefs = LatestBriefsBlock()
    text = TextSectionBlock()
