from collections.abc import Callable
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from wagtail.models import Page

from audits.models import Finding


@dataclass(frozen=True)
class FindingData:
    code: str
    severity: Finding.Severity
    message: str
    fingerprint: str = ""
    language_code: str | None = None
    url: str = ""


@dataclass(frozen=True)
class InspectedPage:
    page: Page
    url: str
    html: BeautifulSoup
    translations: dict[str, Page] = field(default_factory=dict)


Check = Callable[[InspectedPage], list[FindingData]]
SiteCheck = Callable[[], list[FindingData]]

_checks: list[Check] = []
_site_checks: list[SiteCheck] = []


def register_check(check: Check) -> Check:
    _checks.append(check)
    return check


def registered_checks() -> tuple[Check, ...]:
    return tuple(_checks)


def register_site_check(check: SiteCheck) -> SiteCheck:
    _site_checks.append(check)
    return check


def registered_site_checks() -> tuple[SiteCheck, ...]:
    return tuple(_site_checks)
