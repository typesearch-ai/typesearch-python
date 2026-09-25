from __future__ import annotations

import time
from email.utils import formatdate
from typing import Any, Dict, Type

import pytest

from typesearch import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncTypesearch,
    AuthenticationError,
    BadRequestError,
    BudgetError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    Typesearch,
    TypesearchError,
)

from .fake_api import KEY, FakeApi, Scripted, problem, search_response


def fail(status: int, code: str, headers: Dict[str, str] | None = None, **extra: Any) -> Scripted:
    return Scripted(status=status, headers=headers or {}, body=problem(status, code, **extra))


@pytest.mark.parametrize(
    ("status", "code", "cls"),
    [
        (400, "invalid_request", BadRequestError),
        (401, "invalid_api_key", AuthenticationError),
        (402, "insufficient_credits", BudgetError),
        (402, "budget_too_small", BudgetError),
        (403, "robots_disallowed", PermissionDeniedError),
        (403, "source_unavailable", PermissionDeniedError),
        (404, "job_not_found", NotFoundError),
        (429, "quota_exceeded", RateLimitError),
        (499, "cancelled", APIError),
    ],
)
def test_typed_errors(api: FakeApi, ts: Typesearch, status: int, code: str, cls: Type[APIError]) -> None:
    api.next(fail(status, code, {"retry-after": "3600"}))
    with pytest.raises(cls) as e:
        ts.search("el dólar")
    err = e.value
    assert isinstance(err, APIError) and isinstance(err, TypesearchError)
    assert (err.status, err.code, err.request_id) == (status, code, "req_fakeerr1")
    assert str(err) == f"detail of {code}"
    assert code in repr(err)
    assert len(api.requests) == 1  # none of them is retried


def test_a_real_401_from_the_api(api: FakeApi) -> None:
    with Typesearch("ts_live_wrong", base_url=api.url) as other, pytest.raises(AuthenticationError) as e:
        other.usage()
    assert e.value.code == "invalid_api_key"


def test_an_error_body_that_is_not_json(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(status=400, body="<html>Bad gateway</html>"))
    with pytest.raises(BadRequestError) as e:
        ts.usage()
    assert e.value.code == "unknown_error"
    assert e.value.request_id == "req_fakescr1"


def test_a_successful_answer_that_is_not_json(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(status=200, body="<html>"))
    with pytest.raises(TypesearchError, match="not JSON"):
        ts.usage()


def test_rate_limited_is_retried_after_retry_after(api: FakeApi, ts: Typesearch) -> None:
    api.next(fail(429, "rate_limited", {"retry-after": "0"}), fail(429, "rate_limited", {"retry-after": "0"}))
    assert ts.usage().object == "usage"
    assert len(api.requests) == 3
    api.reset()
    api.next(fail(429, "rate_limited", {"retry-after": "7"}))
    with Typesearch(KEY, base_url=api.url, max_retries=0) as once, pytest.raises(RateLimitError) as e:
        once.usage()
    assert e.value.retry_after == 7


def test_retry_after_as_an_http_date(api: FakeApi, ts: Typesearch) -> None:
    api.next(fail(503, "upstream_unavailable", {"retry-after": formatdate(time.time() + 1.2, usegmt=True)}))
    t0 = time.monotonic()
    ts.usage()
    assert time.monotonic() - t0 >= 0.15
    assert len(api.requests) == 2


def test_quota_exceeded_is_never_retried(api: FakeApi, ts: Typesearch) -> None:
    api.next(fail(429, "quota_exceeded", {"retry-after": "0"}))
    with pytest.raises(RateLimitError):
        ts.usage()
    assert len(api.requests) == 1


def test_5xx_is_retried_then_raised(api: FakeApi, ts: Typesearch) -> None:
    api.next(
        fail(503, "shutting_down", {"retry-after": "0"}),
        fail(502, "site_unreachable", {"retry-after": "0"}),
        fail(500, "internal_error", {"retry-after": "0"}),
    )
    with pytest.raises(InternalServerError) as e:
        ts.search("el dólar")
    assert e.value.code == "internal_error"
    assert len(api.requests) == 3
    assert all(r.body == api.requests[0].body for r in api.requests)


def test_max_retries_per_request(api: FakeApi, ts: Typesearch) -> None:
    api.next(fail(503, "upstream_unavailable", {"retry-after": "0"}))
    with pytest.raises(InternalServerError):
        ts.search("el dólar", max_retries=0)
    assert len(api.requests) == 1


def test_exponential_backoff_without_retry_after(api: FakeApi, ts: Typesearch) -> None:
    api.next(fail(503, "upstream_unavailable"))
    t0 = time.monotonic()
    ts.usage()
    assert 0.37 <= time.monotonic() - t0 < 2


def test_a_dropped_connection_is_retried_then_raised(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(destroy=True))
    assert ts.usage().object == "usage"
    api.reset()
    api.next(Scripted(destroy=True), Scripted(destroy=True))
    with pytest.raises(APIConnectionError) as e:
        ts.search("el dólar", max_retries=1)
    assert e.value.__cause__ is not None


def test_a_slow_server_is_a_timeout_and_is_retried(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(delay=0.5, body=search_response()), Scripted(delay=0.5, body=search_response()))
    with pytest.raises(APITimeoutError) as e:
        ts.search("el dólar", timeout=0.1, max_retries=1)
    assert isinstance(e.value, APIConnectionError)
    assert len(api.requests) == 2


@pytest.mark.anyio
async def test_async_retries_and_errors(api: FakeApi, ats: AsyncTypesearch) -> None:
    api.next(fail(503, "upstream_unavailable", {"retry-after": "0"}), Scripted(destroy=True))
    assert (await ats.usage()).object == "usage"
    assert len(api.requests) == 3
    api.next(fail(429, "quota_exceeded"))
    with pytest.raises(RateLimitError):
        await ats.usage()
    api.next(Scripted(delay=0.5, body=search_response()))
    with pytest.raises(APITimeoutError):
        await ats.search("el dólar", timeout=0.1, max_retries=0)


def test_retry_after_parsing() -> None:
    from typesearch._errors import retry_after_seconds

    assert retry_after_seconds({"retry-after-ms": "1500"}) == 1.5
    assert retry_after_seconds({"Retry-After": "2"}) == 2
    assert retry_after_seconds({"retry-after-ms": "x", "retry-after": "3"}) == 3
    assert retry_after_seconds({"retry-after": "soon"}) is None
    assert retry_after_seconds({"retry-after": "-1"}) is None
    assert retry_after_seconds({"retry-after": " "}) is None
    assert retry_after_seconds({}) is None
