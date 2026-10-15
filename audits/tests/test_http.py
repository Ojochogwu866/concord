import socket
from collections.abc import Iterator

import httpx
import pytest
import respx

from audits.http import (
    ExternalLinkChecker,
    HostRateLimiter,
    LinkCheckerLimits,
    UnsafeURLError,
    assert_public_url,
)

ADDRESSES = {
    "public.example": "93.184.216.34",
    "other.example": "93.184.216.35",
    "internal.example": "10.0.0.5",
    "metadata.example": "169.254.169.254",
    "loopback.example": "127.0.0.1",
    "ipv6-loopback.example": "::1",
}
LIMITS = LinkCheckerLimits(
    max_redirects=3, max_retries=1, retry_backoff_seconds=2.0, max_body_bytes=1024
)


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def getaddrinfo(
        host: str, port: int | None, *args: object
    ) -> list[tuple[object, ...]]:
        if host not in ADDRESSES:
            raise socket.gaierror("unknown host")
        address = ADDRESSES[host]
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (address, port or 443))]

    monkeypatch.setattr("audits.http.socket.getaddrinfo", getaddrinfo)


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def network() -> Iterator[respx.MockRouter]:
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def checker(
    network: respx.MockRouter, sleeps: list[float]
) -> Iterator[ExternalLinkChecker]:
    with httpx.Client() as client:
        yield ExternalLinkChecker(
            client, HostRateLimiter(0), LIMITS, sleep=sleeps.append
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://internal.example/",
        "https://metadata.example/latest/",
        "https://loopback.example/",
        "https://ipv6-loopback.example/",
        "ftp://public.example/file",
        "https://unknown.example/",
    ],
)
def test_blocks_private_unresolvable_and_non_http_urls(url: str) -> None:
    with pytest.raises(UnsafeURLError):
        assert_public_url(url)


def test_allows_public_urls() -> None:
    assert_public_url("https://public.example/page")


@pytest.mark.parametrize(
    ("status", "is_ok", "is_broken"),
    [(200, True, False), (404, False, True), (410, False, True), (503, False, True)],
)
def test_classifies_head_responses(
    network: respx.MockRouter,
    checker: ExternalLinkChecker,
    status: int,
    is_ok: bool,
    is_broken: bool,
) -> None:
    network.head("https://public.example/page").respond(status)

    result = checker.check("https://public.example/page")

    assert (result.status_code, result.is_ok, result.is_broken) == (
        status,
        is_ok,
        is_broken,
    )


@pytest.mark.parametrize("status", [401, 403, 429])
def test_bot_protection_is_inconclusive(
    network: respx.MockRouter,
    checker: ExternalLinkChecker,
    status: int,
) -> None:
    network.head("https://public.example/page").respond(status)

    result = checker.check("https://public.example/page")

    assert not result.is_ok
    assert not result.is_broken


def test_falls_back_to_get_when_head_is_not_allowed(
    network: respx.MockRouter,
    checker: ExternalLinkChecker,
) -> None:
    network.head("https://public.example/page").respond(405)
    get = network.get("https://public.example/page").respond(200, content=b"x" * 4096)

    result = checker.check("https://public.example/page")

    assert result.is_ok
    assert get.called


def test_follows_redirects_to_the_final_status(
    network: respx.MockRouter, checker: ExternalLinkChecker
) -> None:
    network.head("https://public.example/old").respond(
        301, headers={"Location": "/new"}
    )
    network.head("https://public.example/new").respond(200)

    assert checker.check("https://public.example/old").status_code == 200


def test_refuses_redirects_to_private_addresses(
    network: respx.MockRouter, checker: ExternalLinkChecker
) -> None:
    network.head("https://public.example/hop").respond(
        302, headers={"Location": "https://metadata.example/latest/"}
    )

    result = checker.check("https://public.example/hop")

    assert result.is_broken
    assert "private address" in result.error


def test_stops_after_too_many_redirects(
    network: respx.MockRouter, checker: ExternalLinkChecker
) -> None:
    network.head("https://public.example/loop").respond(
        302, headers={"Location": "/loop"}
    )

    result = checker.check("https://public.example/loop")

    assert result.error == "Too many redirects."


def test_retries_a_timeout_once_with_backoff(
    network: respx.MockRouter,
    checker: ExternalLinkChecker,
    sleeps: list[float],
) -> None:
    route = network.head("https://public.example/slow").mock(
        side_effect=httpx.ReadTimeout("slow")
    )

    result = checker.check("https://public.example/slow")

    assert route.call_count == LIMITS.max_retries + 1
    assert sleeps == [LIMITS.retry_backoff_seconds]
    assert (result.is_broken, result.error) == (True, "Timed out.")


def test_recovers_when_the_retry_succeeds(
    network: respx.MockRouter, checker: ExternalLinkChecker
) -> None:
    network.head("https://public.example/flaky").mock(
        side_effect=[httpx.ConnectError("refused"), httpx.Response(200)]
    )

    assert checker.check("https://public.example/flaky").is_ok


def test_rate_limiter_spaces_requests_to_the_same_host() -> None:
    now = [100.0]
    slept: list[float] = []
    limiter = HostRateLimiter(1.0, clock=lambda: now[0], sleep=slept.append)

    limiter.wait("public.example")
    limiter.wait("public.example")
    limiter.wait("other.example")

    assert slept == [1.0]
