from http import HTTPStatus

from django.conf import settings
from wagtail.contrib.redirects.models import Redirect

from audits.models import Finding
from audits.registry import FindingData, register_site_check
from audits.rendering import fetch_final_status

REDIRECT_CHAIN = "redirect.chain"
REDIRECT_LOOP = "redirect.loop"
BROKEN_TARGET = "redirect.broken_target"

ARROW = " → "


@register_site_check
def check_redirects() -> list[FindingData]:
    redirects = list(Redirect.objects.select_related("redirect_page"))
    by_old_path = {redirect.old_path: redirect for redirect in redirects}
    findings = []
    for redirect in redirects:
        target = _target_path(redirect)
        if target is None or target not in by_old_path:
            broken = _broken_target_finding(redirect, target)
            if broken is not None:
                findings.append(broken)
            continue
        findings.append(_follow_chain(redirect, by_old_path))
    return findings


def _follow_chain(redirect: Redirect, by_old_path: dict[str, Redirect]) -> FindingData:
    hops = [redirect.old_path]
    path = _target_path(redirect)
    while path is not None and path in by_old_path:
        if path in hops:
            return _finding(
                redirect,
                REDIRECT_LOOP,
                Finding.Severity.ERROR,
                f"Redirect loop: {ARROW.join([*hops, path])} never reaches a page.",
            )
        hops.append(path)
        path = _target_path(by_old_path[path])
    destination = path or "nowhere"
    return _finding(
        redirect,
        REDIRECT_CHAIN,
        Finding.Severity.WARNING,
        f"Redirect chain: {ARROW.join([*hops, destination])}. "
        f"Point {redirect.old_path} straight to {destination}.",
    )


def _broken_target_finding(
    redirect: Redirect, target: str | None
) -> FindingData | None:
    if target is None:
        reason = "has no target"
    elif redirect.redirect_page is not None:
        if redirect.redirect_page.live:
            return None
        reason = f"points to {target}, which is not published"
    elif target.startswith("/"):
        status = fetch_final_status(target)
        if status < HTTPStatus.BAD_REQUEST:
            return None
        reason = f"points to {target}, which returns HTTP {status}"
    else:
        return None
    return _finding(
        redirect,
        BROKEN_TARGET,
        Finding.Severity.ERROR,
        f"Redirect from {redirect.old_path} {reason}.",
    )


def _target_path(redirect: Redirect) -> str | None:
    if redirect.redirect_page is not None:
        url: str | None = redirect.redirect_page.url
        return Redirect.normalise_path(url) if url else None
    if redirect.redirect_link:
        link: str = redirect.redirect_link
        return Redirect.normalise_path(link) if link.startswith("/") else link
    return None


def _finding(
    redirect: Redirect, code: str, severity: Finding.Severity, message: str
) -> FindingData:
    return FindingData(
        code=code,
        severity=severity,
        message=message,
        fingerprint=redirect.old_path,
        language_code=_language_from_path(redirect.old_path),
        url=redirect.old_path,
    )


def _language_from_path(path: str) -> str | None:
    prefix = path.strip("/").split("/")[0]
    content_languages = {code for code, _ in settings.WAGTAIL_CONTENT_LANGUAGES}
    return prefix if prefix in content_languages else None
