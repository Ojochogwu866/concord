import os

import dj_database_url

from sitehealth.settings.base import *

SECRET_KEY = "test-only-secret-key"

ALLOWED_HOSTS = ["testserver", "localhost"]

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://sitehealth:sitehealth@localhost:5434/sitehealth"
    )
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Serve static files from finders so tests do not depend on collectstatic.
WHITENOISE_AUTOREFRESH = True

SUGGESTIONS_PROVIDER = os.environ.get(
    "SUGGESTIONS_PROVIDER", "suggestions.providers.offline.OfflineProvider"
)
