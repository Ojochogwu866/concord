import json
from collections.abc import Callable
from pathlib import Path

import pytest
from django.test import Client
from pytest_django.fixtures import Settings
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file

from briefs.models import Topic
from briefs.tests.conftest import BriefFactory


@pytest.fixture
def image(db: None, settings: Settings, tmp_path: Path) -> Image:
    settings.MEDIA_ROOT = tmp_path
    return Image.objects.create(title="Substation", file=get_test_image_file())


def figure_block(
    image: Image, *, alt_text: str, is_decorative: bool
) -> dict[str, object]:
    return {
        "type": "figure",
        "value": {
            "image": {
                "image": image.pk,
                "alt_text": alt_text,
                "decorative": is_decorative,
            },
            "caption": "",
        },
    }


def test_renders_byline_summary_and_body(
    client: Client, make_brief: BriefFactory
) -> None:
    brief = make_brief(
        title="Grid storage",
        summary="Batteries now clear the evening peak.",
        body=json.dumps(
            [
                {"type": "heading", "value": {"text": "What changed", "level": "h2"}},
                {"type": "paragraph", "value": "<p>Prices fell by a third.</p>"},
                {
                    "type": "quote",
                    "value": {"quote": "Storage won.", "attribution": "Grid operator"},
                },
            ]
        ),
    )

    html = client.get(brief.url).content.decode()

    assert "<h1" in html and "Grid storage" in html
    assert "By Dickson Ojochogwu" in html
    assert '<time datetime="2026-09-01">' in html
    assert "Batteries now clear the evening peak." in html
    assert "<h2>What changed</h2>" in html
    assert "<p>Prices fell by a third.</p>" in html
    assert "Storage won." in html
    assert "<figcaption>— Grid operator</figcaption>" in html


def test_links_topics_back_to_filtered_index(
    client: Client,
    make_brief: BriefFactory,
    make_topic: Callable[[str, str], Topic],
) -> None:
    energy = make_topic("Energy", "energy")
    brief = make_brief(topics=[energy])

    html = client.get(brief.url).content.decode()

    assert f'href="{brief.get_parent().url}?topic=energy"' in html


def test_figure_uses_editor_alt_text(
    client: Client, make_brief: BriefFactory, image: Image
) -> None:
    brief = make_brief(
        body=json.dumps(
            [figure_block(image, alt_text="Battery units", is_decorative=False)]
        )
    )

    html = client.get(brief.url).content.decode()

    assert 'alt="Battery units"' in html


def test_decorative_figure_has_empty_alt(
    client: Client, make_brief: BriefFactory, image: Image
) -> None:
    brief = make_brief(
        body=json.dumps([figure_block(image, alt_text="", is_decorative=True)])
    )

    html = client.get(brief.url).content.decode()

    assert 'alt=""' in html
