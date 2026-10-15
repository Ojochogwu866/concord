import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

R2_REGION = "auto"


def get_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Set the {name} environment variable.")
    return value


def get_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_required_list(name: str) -> list[str]:
    values = get_list(name)
    if not values:
        raise ImproperlyConfigured(
            f"Set the {name} environment variable to a comma-separated list."
        )
    return values


def r2_storage() -> dict[str, object] | None:
    if not os.environ.get("R2_BUCKET_NAME", "").strip():
        return None
    bucket_url = urlsplit(get_required("R2_BUCKET_URL"))
    if bucket_url.scheme != "https" or not bucket_url.netloc:
        raise ImproperlyConfigured("Set R2_BUCKET_URL to the bucket's https:// URL.")
    public_host = urlsplit(os.environ.get("R2_PUBLIC_URL", "").strip()).netloc
    return {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": get_required("R2_BUCKET_NAME"),
            "endpoint_url": f"https://{bucket_url.netloc}",
            "access_key": get_required("R2_ACCESS_KEY_ID"),
            "secret_key": get_required("R2_SECRET_ACCESS_KEY"),
            "region_name": R2_REGION,
            "signature_version": "s3v4",
            "file_overwrite": False,
            # Private buckets need signed URLs; a public custom domain does not.
            "custom_domain": public_host or None,
            "querystring_auth": not public_host,
        },
    }
