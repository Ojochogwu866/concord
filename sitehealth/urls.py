from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import URLPattern, URLResolver, include, path
from django.views.decorators.csp import csp_override
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.utils.urlpatterns import decorate_urlpatterns

from sitehealth.views import healthz


def admin_urlpatterns() -> list[URLPattern | URLResolver]:
    patterns: list[URLPattern | URLResolver] = wagtailadmin_urls.urlpatterns
    decorate_urlpatterns(patterns, csp_override(settings.ADMIN_CSP))
    return patterns


urlpatterns: list[URLPattern | URLResolver] = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", include(admin_urlpatterns())),
    path("documents/", include(wagtaildocs_urls)),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += i18n_patterns(path("", include(wagtail_urls)))
