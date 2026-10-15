import dj_database_url

from sitehealth.settings.base import *
from sitehealth.settings.environment import (
    get_required,
    get_required_list,
    r2_storage,
)

DEBUG = False

SECRET_KEY = get_required("SECRET_KEY")
ALLOWED_HOSTS = get_required_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = get_required_list("CSRF_TRUSTED_ORIGINS")
WAGTAILADMIN_BASE_URL = get_required("WAGTAILADMIN_BASE_URL")

DATABASES = {
    "default": dj_database_url.parse(
        get_required("DATABASE_URL"),
        conn_max_age=DATABASE_CONN_MAX_AGE,
        conn_health_checks=True,
    )
}
# Neon's pooled endpoint runs PgBouncer in transaction mode, which breaks these.
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

media_storage = r2_storage()
if media_storage is not None:
    STORAGES["default"] = media_storage

STORAGES["staticfiles"]["BACKEND"] = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Kept short until HTTPS on the deployed domain is confirmed stable.
SECURE_HSTS_SECONDS = 60 * 60
