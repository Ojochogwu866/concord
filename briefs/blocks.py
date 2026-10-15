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
