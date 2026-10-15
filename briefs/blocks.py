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


class ItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=80)
    description = blocks.TextBlock(max_length=300)
    code = blocks.CharBlock(
        required=False,
        max_length=60,
        help_text=_("Optional label shown in monospace, such as a finding code."),
    )


class FeatureListBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=120)
    items = blocks.ListBlock(ItemBlock(), min_num=1)

    class Meta:
        icon = "list-ul"
        template = "briefs/blocks/feature_list.html"


class StepListBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=120)
    steps = blocks.ListBlock(ItemBlock(), min_num=1)
    image = ImageBlock(required=False)

    class Meta:
        icon = "list-ol"
        template = "briefs/blocks/step_list.html"


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
    features = FeatureListBlock()
    steps = StepListBlock()
    latest_briefs = LatestBriefsBlock()
    text = TextSectionBlock()
