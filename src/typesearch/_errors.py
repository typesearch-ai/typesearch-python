from __future__ import annotations

import math
import time
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

if TYPE_CHECKING:
    import httpx

    from ._models import Job

__all__ = [
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "BudgetError",
    "InternalServerError",
    "JobFailedError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "TypesearchError",
]


class TypesearchError(Exception):
    """Base class for every error raised by the SDK."""


class APIError(TypesearchError):
    """The API answered with an error (RFC 9457 problem details).

    ``code`` is stable and meant for programs (``rate_limited``, ``invalid_request``…); the message is meant
    for people and can change. ``request_id`` identifies the request: include it when you contact support.
    """

    status: int
    """The HTTP status."""
    code: str
    """The stable error code, such as ``invalid_request`` or ``rate_limited``."""
    request_id: Optional[str]
    errors: List[Dict[str, str]]
    """One ``{"path", "message"}`` per invalid field, when the request was invalid."""
    problem: Dict[str, Any]
    """The whole problem details object, as the API sent it."""

    def __init__(self, status: int, problem: Mapping[str, Any], headers: Optional[Mapping[str, str]] = None) -> None:
        headers = headers or {}
        self.status = status
        self.problem = dict(problem)
        self.code = str(problem.get("code") or "unknown_error")
        self.message = str(problem.get("detail") or problem.get("title") or f"Request failed with status {status}")
        self.request_id = problem.get("request_id") or _header(headers, "x-request-id")
        errors = problem.get("errors")
        self.errors = list(errors) if isinstance(errors, list) else []
        self.headers = dict(headers)
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(status={self.status}, code={self.code!r}, request_id={self.request_id!r}, message={self.message!r})"


class BadRequestError(APIError):
    """400: the request is malformed or a field is invalid (``errors`` lists each one)."""


class AuthenticationError(APIError):
    """401: the API key is missing, invalid or revoked."""


class BudgetError(APIError):
    """402: ``budget_too_small`` (``max_tokens`` is too small to judge even the headlines),
    ``insufficient_credits`` (no credit left) or ``spend_limit_reached`` (the key hit its monthly limit)."""


class PermissionDeniedError(APIError):
    """403: ``robots_disallowed`` (the site's robots.txt disallows it) or ``source_unavailable``."""


class NotFoundError(APIError):
    """404: the job does not exist for this key, or it expired (jobs last one day)."""


class RateLimitError(APIError):
    """429: the per-minute limit (``rate_limited``, retried) or the daily token quota (``quota_exceeded``, never retried)."""

    retry_after: Optional[float]
    """Seconds to wait, from ``Retry-After``, when the server sent it."""

    def __init__(self, status: int, problem: Mapping[str, Any], headers: Optional[Mapping[str, str]] = None) -> None:
        super().__init__(status, problem, headers)
        seconds = retry_after_seconds(headers or {})
        self.retry_after = None if seconds is None else float(math.ceil(seconds))


class InternalServerError(APIError):
    """5xx: something failed on our side, or the site you asked for did. Retried automatically."""


class APIConnectionError(TypesearchError):
    """The request never got an answer: network failure, DNS, connection reset."""

    def __init__(self, message: str = "Could not reach the typesearch API.") -> None:
        super().__init__(message)


class APITimeoutError(APIConnectionError):
    """The request took longer than ``timeout``, or a job did not finish in time."""


class JobFailedError(TypesearchError):
    """A live site search job ended in ``failed``. The job, with its ``error``, is in ``job``."""

    def __init__(self, job: Job) -> None:
        self.job = job
        error = job.error
        self.code: str = (error.code if error is not None else None) or "unknown_error"
        """The stable error code of the job, such as ``site_unreachable``."""
        super().__init__((error.detail if error is not None else None) or f"Job {job.id} failed.")


def error_for(status: int, problem: Mapping[str, Any], headers: Optional[Mapping[str, str]] = None) -> APIError:
    """The right error class for an HTTP status."""
    classes = {
        400: BadRequestError,
        401: AuthenticationError,
        402: BudgetError,
        403: PermissionDeniedError,
        404: NotFoundError,
        429: RateLimitError,
    }
    cls = classes.get(status) or (InternalServerError if status >= 500 else APIError)
    return cls(status, problem, headers)


def error_from_response(response: httpx.Response) -> APIError:
    try:
        data = response.json()
    except ValueError:
        data = {}
    return error_for(response.status_code, data if isinstance(data, dict) else {}, response.headers)


def retry_after_seconds(headers: Mapping[str, str]) -> Optional[float]:
    """``Retry-After`` (seconds or an HTTP date) or ``retry-after-ms``, in seconds; ``None`` if absent or unreadable."""
    ms = _header(headers, "retry-after-ms")
    if ms is not None:
        try:
            value = float(ms)
            if value >= 0:
                return value / 1000
        except ValueError:
            pass
    raw = _header(headers, "retry-after")
    if raw is None or not raw.strip():
        return None
    try:
        seconds = float(raw)
        return seconds if seconds >= 0 else None
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:  # pragma: no cover - Python < 3.10 returns None for bad dates
        return None
    return max(0.0, when.timestamp() - time.time())


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    value = headers.get(name)
    if value is None:
        for k, v in headers.items():
            if k.lower() == name:
                return v
    return value
