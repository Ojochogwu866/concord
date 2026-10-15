import os

import dj_database_url

from sitehealth.settings.base import *

DEBUG = True

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-local-development-only")

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://sitehealth:sitehealth@localhost:5434/sitehealth",
        conn_max_age=DATABASE_CONN_MAX_AGE,
    )
}

MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
