import ipaddress
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
from urllib.parse import urljoin, urlsplit

import httpx

ALLOWED_SCHEMES = {"http", "https"}
GET_FALLBACK_STATUSES = {HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.NOT_IMPLEMENTED}
BROKEN_CLIENT_STATUSES = {HTTPStatus.NOT_FOUND, HTTPStatus.GONE}


class UnsafeURLError(Exception):
    pass


@dataclass(frozen=True)
class LinkResult:
    url: str
    status_code: int | None
    error: str = ""

    @property
    def is_broken(self) -> bool:
        if self.status_code is None:
            return True
        return (
            self.status_code in BROKEN_CLIENT_STATUSES
            or self.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
        )

    @property
    def is_ok(self) -> bool:
        return (
            self.status_code is not None and self.status_code < HTTPStatus.BAD_REQUEST
        )

    @property
    def reason(self) -> str:
        return f"HTTP {self.status_code}" if self.status_code else self.error


def resolve_public_address(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise UnsafeURLError(f"Only http and https links can be checked: {url}")
    try:
        addresses = socket.getaddrinfo(parts.hostname, parts.port or None)
    except socket.gaierror as error:
        raise UnsafeURLError(f"Could not resolve {parts.hostname}.") from error
    for *_, sockaddr in addresses:
        if not ipaddress.ip_address(sockaddr[0]).is_global:
            raise UnsafeURLError(f"{parts.hostname} points to a private address.")
    # Prefer IPv4: a pinned request cannot fall back to another address the way an
    # unpinned one can, and IPv6 is often unreachable even when the site is up.
    families = [family for family, *_ in addresses]
    preferred = families.index(socket.AF_INET) if socket.AF_INET in families else 0
    return str(addresses[preferred][4][0])


@dataclass(frozen=True)
class PinnedRequest:
    url: str
    headers: dict[str, str]
    extensions: dict[str, str]


def pin_to_address(url: str, address: str) -> PinnedRequest:
    # Connecting to the address that passed the check, instead of letting the HTTP
    # client resolve the name again, closes the DNS-rebinding gap.
    parts = urlsplit(url)
    port = f":{parts.port}" if parts.port else ""
    host = f"[{address}]" if ":" in address else address
    hostname = parts.hostname or ""
    return PinnedRequest(
        url=parts._replace(netloc=f"{host}{port}").geturl(),
        headers={"Host": f"{hostname}{port}"},
        extensions={"sni_hostname": hostname} if parts.scheme == "https" else {},
    )


class HostRateLimiter:
    def __init__(
        self,
        interval_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._interval = interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_slot: dict[str, float] = {}

    def wait(self, host: str) -> None:
        with self._lock:
            now = self._clock()
            slot = max(now, self._next_slot.get(host, now))
            self._next_slot[host] = slot + self._interval
        if slot > now:
            self._sleep(slot - now)


@dataclass(frozen=True)
class LinkCheckerLimits:
    max_redirects: int
    max_retries: int
    retry_backoff_seconds: float
    max_body_bytes: int


class ExternalLinkChecker:
    def __init__(
        self,
        client: httpx.Client,
        rate_limiter: HostRateLimiter,
        limits: LinkCheckerLimits,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._limits = limits
        self._sleep = sleep

    def check(self, url: str) -> LinkResult:
        last_error = ""
        for attempt in range(self._limits.max_retries + 1):
            try:
                return self._follow(url)
            except UnsafeURLError as error:
                return LinkResult(url=url, status_code=None, error=str(error))
            except httpx.TransportError as error:
                last_error = _describe(error)
                if attempt < self._limits.max_retries:
                    self._sleep(self._limits.retry_backoff_seconds * (attempt + 1))
        return LinkResult(url=url, status_code=None, error=last_error)

    def _follow(self, url: str) -> LinkResult:
        current = url
        for _ in range(self._limits.max_redirects + 1):
            pinned = pin_to_address(current, resolve_public_address(current))
            self._rate_limiter.wait(urlsplit(current).hostname or "")
            status, location = self._request(pinned)
            if location is None:
                return LinkResult(url=url, status_code=status)
            current = urljoin(current, location)
        return LinkResult(url=url, status_code=None, error="Too many redirects.")

    def _request(self, pinned: PinnedRequest) -> tuple[int, str | None]:
        response = self._client.head(
            pinned.url, headers=pinned.headers, extensions=pinned.extensions
        )
        if response.status_code in GET_FALLBACK_STATUSES:
            with self._client.stream(
                "GET", pinned.url, headers=pinned.headers, extensions=pinned.extensions
            ) as streamed:
                received = 0
                for chunk in streamed.iter_bytes():
                    received += len(chunk)
                    if received >= self._limits.max_body_bytes:
                        break
                return streamed.status_code, _redirect_location(streamed)
        return response.status_code, _redirect_location(response)


def _redirect_location(response: httpx.Response) -> str | None:
    if response.has_redirect_location:
        return response.headers["location"]
    return None


def _describe(error: httpx.TransportError) -> str:
    if isinstance(error, httpx.TimeoutException):
        return "Timed out."
    if isinstance(error, httpx.ConnectError):
        return "Could not connect."
    return "Network error."
