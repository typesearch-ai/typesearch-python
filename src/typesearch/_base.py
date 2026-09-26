"""Lo que comparten el cliente sincrónico y el asincrónico: configuración, cuerpo de los pedidos y reintentos."""

from __future__ import annotations

import datetime as dt
import os
import random
from typing import Any, Dict, Mapping, Optional, Sequence, Union
from urllib.parse import quote

import httpx

from ._errors import TypesearchError
from ._params import NULLABLE
from ._version import __version__

DEFAULT_BASE_URL = "https://api.typesearch.ai"
DEFAULT_TIMEOUT = 70.0  # a deep search can take about a minute
DEFAULT_MAX_RETRIES = 2
DEFAULT_POLL_INTERVAL = 2.0
DEFAULT_WAIT_TIMEOUT = 120.0


class BaseClient:
    base_url: str
    timeout: float
    max_retries: int

    def __init__(
        self,
        api_key: Optional[str],
        base_url: Optional[str],
        timeout: float,
        max_retries: int,
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        api_key = (api_key or os.environ.get("TYPESEARCH_API_KEY") or "").strip()
        if not api_key:
            raise TypesearchError(
                "Missing API key: pass `api_key` or set the TYPESEARCH_API_KEY environment variable. Get one at https://app.typesearch.ai"
            )
        self._api_key = api_key
        self.base_url = (base_url or os.environ.get("TYPESEARCH_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._default_headers = {k.lower(): v for k, v in (default_headers or {}).items()}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.base_url!r})"

    def _headers(self, stream: bool, extra: Optional[Mapping[str, str]]) -> Dict[str, str]:
        return {
            "accept": "text/event-stream" if stream else "application/json",
            "authorization": f"Bearer {self._api_key}",
            "user-agent": f"typesearch-python/{__version__}",
            **self._default_headers,
            **{k.lower(): v for k, v in (extra or {}).items()},
        }

    def _build(
        self,
        http: Union[httpx.Client, httpx.AsyncClient],
        method: str,
        path: str,
        body: Optional[Dict[str, Any]],
        stream: bool,
        timeout: Optional[float],
        extra_headers: Optional[Mapping[str, str]],
    ) -> httpx.Request:
        return http.build_request(
            method,
            f"{self.base_url}{path}",
            json=body,
            headers=self._headers(stream, extra_headers),
            timeout=httpx.Timeout(self.timeout if timeout is None else timeout),
        )


def body(positional: Dict[str, Any], options: Mapping[str, Any]) -> Dict[str, Any]:
    """The request body: the positional arguments plus the options, with dates as ISO strings.

    ``None`` is sent as ``null`` only where it means something (``days=None``: the whole index); anywhere
    else it means "the API's default" and the field is left out. Options the SDK does not know yet are sent
    as they are: the API validates them.
    """
    out = dict(positional)
    for key, value in options.items():
        if value is None:
            if key in NULLABLE:
                out[key] = None
            continue
        out[key] = _json(key, value)
    return out


def _json(key: str, value: Any) -> Any:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{key}: a datetime needs a time zone (tzinfo). Pass a date for a whole day.")
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json(key, v) for v in value]
    if isinstance(value, Mapping):
        return {k: _json(key, v) for k, v in value.items()}
    return value


def as_list(value: Union[str, Sequence[str]]) -> Any:
    return [value] if isinstance(value, str) else list(value)


def job_path(job_id: str) -> str:
    return f"/v1/jobs/{quote(job_id, safe='')}"


def should_retry(status: int, code: str) -> bool:
    """408, 409, 429 and 5xx are retried; the daily quota is not: it resets at 00:00 UTC."""
    if code == "quota_exceeded":
        return False
    return status in (408, 409, 429) or status >= 500


def retry_delay(attempt: int, retry_after: Optional[float]) -> float:
    """``Retry-After`` when it asks for up to a minute; otherwise exponential backoff with jitter (0.5 s, 1 s, 2 s… up to 8 s)."""
    if retry_after is not None and retry_after <= 60:
        return retry_after
    return float(min(0.5 * 2.0**attempt, 8.0)) * (1 - random.random() * 0.25)
