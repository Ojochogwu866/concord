import os
from pathlib import Path

from django.utils.csp import CSP

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

INSTALLED_APPS = [
    "briefs",
    "audits",
    "suggestions",
    "wagtail_localize",
    "wagtail_localize.locales",
    "whitenoise.runserver_nostatic",
    "wagtail.contrib.redirects",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "sitehealth.urls"
WSGI_APPLICATION = "sitehealth.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sitehealth.context_processors.site_credits",
            ],
        },
    },
]

DATABASE_CONN_MAX_AGE = 600

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{validator}"}
    for validator in (
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    )
]

MAILERS = {"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("fr", "Français")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [PROJECT_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES: dict[str, dict[str, object]] = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Wagtail's live preview renders pages in a same-origin iframe.
X_FRAME_OPTIONS = "SAMEORIGIN"

# Inline style attributes carry animation order and view-transition names; inline
# scripts are allowed only with the per-request nonce.
SECURE_CSP: dict[str, list[str]] = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.SELF],
}
# Wagtail's editor panels and date widgets ship inline scripts without nonces, so
# the admin allows inline scripts while still refusing anything from other origins.
ADMIN_CSP: dict[str, list[str]] = {
    **SECURE_CSP,
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "img-src": [CSP.SELF, "data:", "blob:"],
}
WAGTAIL_GRAVATAR_PROVIDER_URL = None
# Keeps the admin from contacting releases.wagtail.org, which the CSP also blocks.
WAGTAIL_ENABLE_UPDATE_CHECK = False

# Wagtail's page editor can exceed Django's default limit of 1000 fields.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000

WAGTAIL_SITE_NAME = "Concord"
DESIGNER_PROFILE_URL = "https://github.com/Ojochogwu866"

SEO_TITLE_MAX_LENGTH = 60
SEO_DESCRIPTION_MAX_LENGTH = 160

LINK_CHECK_TIMEOUT_SECONDS = 10
LINK_CHECK_FAILURE_THRESHOLD = 3
LINK_CHECK_MAX_WORKERS = 8
LINK_CHECK_MAX_REDIRECTS = 5
LINK_CHECK_MAX_RETRIES = 1
LINK_CHECK_RETRY_BACKOFF_SECONDS = 2.0
LINK_CHECK_HOST_INTERVAL_SECONDS = 1.0
LINK_CHECK_MAX_BODY_BYTES = 64 * 1024

# AI suggestions stay off unless a provider is configured, so no model is called
# (or billed) by accident. Dotted path to a class implementing SuggestionProvider.
SUGGESTIONS_PROVIDER = os.environ.get("SUGGESTIONS_PROVIDER", "")
SUGGESTIONS_MAX_PER_RUN = 20
WAGTAILLOCALIZE_MACHINE_TRANSLATOR = {
    "CLASS": "suggestions.translator.ConcordTranslator"
}
WAGTAIL_I18N_ENABLED = True
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "http://localhost:8000")
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILDOCS_EXTENSIONS = ["csv", "docx", "odt", "pdf", "pptx", "rtf", "txt", "xlsx"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {"django_tasks": {"level": "WARNING"}},
}
