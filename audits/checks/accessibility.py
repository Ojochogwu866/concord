from bs4 import Tag

from audits.models import Finding
from audits.registry import FindingData, InspectedPage, register_check

HEADING_SKIP = "a11y.heading_skip"
IMAGE_ALT = "a11y.img_alt"
EMPTY_LINK = "a11y.empty_link"
MISSING_LABEL = "a11y.label"
LANGUAGE_MISMATCH = "a11y.lang"

HEADING_LEVELS = {f"h{level}": level for level in range(1, 7)}
FORM_CONTROLS = ["input", "select", "textarea"]
UNLABELLED_INPUT_TYPES = {"hidden", "submit", "button", "reset", "image"}
FINGERPRINT_MAX_LENGTH = 255


@register_check
def check_heading_order(inspected: InspectedPage) -> list[FindingData]:
    findings = []
    previous_level = 0
    for heading in inspected.html.find_all(list(HEADING_LEVELS)):
        level = HEADING_LEVELS[heading.name]
        if previous_level and level > previous_level + 1:
            text = heading.get_text(" ", strip=True)
            findings.append(
                FindingData(
                    code=HEADING_SKIP,
                    severity=Finding.Severity.WARNING,
                    message=(
                        f"Heading “{text}” jumps from h{previous_level} to h{level}."
                    ),
                    fingerprint=_fingerprint(heading.name, text),
                )
            )
        previous_level = level
    return findings


@register_check
def check_image_alt_text(inspected: InspectedPage) -> list[FindingData]:
    return [
        FindingData(
            code=IMAGE_ALT,
            severity=Finding.Severity.ERROR,
            message="Image has no alt attribute. Describe it, or mark it decorative.",
            fingerprint=_fingerprint(_attribute(image, "src")),
        )
        for image in inspected.html.find_all("img")
        if not image.has_attr("alt")
    ]


@register_check
def check_link_text(inspected: InspectedPage) -> list[FindingData]:
    return [
        FindingData(
            code=EMPTY_LINK,
            severity=Finding.Severity.ERROR,
            message="Link has no text, so screen readers cannot say where it goes.",
            fingerprint=_fingerprint(_attribute(link, "href")),
        )
        for link in inspected.html.find_all("a", href=True)
        if not _has_accessible_name(link)
    ]


@register_check
def check_form_labels(inspected: InspectedPage) -> list[FindingData]:
    findings = []
    for control in inspected.html.find_all(FORM_CONTROLS):
        if _attribute(control, "type").lower() in UNLABELLED_INPUT_TYPES:
            continue
        if _is_labelled(control, inspected):
            continue
        name = _attribute(control, "name") or _attribute(control, "id")
        findings.append(
            FindingData(
                code=MISSING_LABEL,
                severity=Finding.Severity.ERROR,
                message=f"Form field “{name}” has no label.",
                fingerprint=_fingerprint(control.name, name),
            )
        )
    return findings


@register_check
def check_document_language(inspected: InspectedPage) -> list[FindingData]:
    expected = inspected.page.locale.language_code
    html_tag = inspected.html.find("html")
    declared = _attribute(html_tag, "lang") if isinstance(html_tag, Tag) else ""
    if declared.split("-")[0].lower() == expected:
        return []
    return [
        FindingData(
            code=LANGUAGE_MISMATCH,
            severity=Finding.Severity.ERROR,
            message=f"Page declares lang=“{declared}” but its content is “{expected}”.",
        )
    ]


def _has_accessible_name(link: Tag) -> bool:
    if link.get_text(strip=True):
        return True
    if _attribute(link, "aria-label").strip() or link.has_attr("aria-labelledby"):
        return True
    return any(_attribute(image, "alt").strip() for image in link.find_all("img"))


def _is_labelled(control: Tag, inspected: InspectedPage) -> bool:
    if control.has_attr("aria-label") or control.has_attr("aria-labelledby"):
        return True
    if control.find_parent("label") is not None:
        return True
    control_id = _attribute(control, "id")
    return bool(control_id and inspected.html.find("label", attrs={"for": control_id}))


def _attribute(element: Tag, name: str) -> str:
    value = element.get(name, "")
    return " ".join(value) if isinstance(value, list) else str(value)


def _fingerprint(*parts: str) -> str:
    return ":".join(parts)[:FINGERPRINT_MAX_LENGTH]
