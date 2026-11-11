from collections.abc import Callable
from typing import cast

from django.http import HttpRequest

REQUEST_CACHE_ATTRIBUTE = "_concord_request_cache"


def cached_for_request[T](
    request: HttpRequest | None, key: str, compute: Callable[[], T]
) -> T:
    if request is None:
        return compute()
    cache: dict[str, object] = request.__dict__.setdefault(REQUEST_CACHE_ATTRIBUTE, {})
    if key not in cache:
        cache[key] = compute()
    return cast(T, cache[key])
