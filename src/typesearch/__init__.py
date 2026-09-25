"""The official Python SDK for the typesearch API: news search for AI agents.

>>> from typesearch import Typesearch
>>> ts = Typesearch()  # reads TYPESEARCH_API_KEY
>>> res = ts.search("el dólar", mode="fast", max_results=5)
>>> for r in res.results:
...     print(f"{r.score:.2f}", r.title, r.source)
"""

from . import types
from ._async_client import AsyncJobs, AsyncTypesearch
from ._base import DEFAULT_BASE_URL
from ._client import Jobs, Typesearch
from ._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    BudgetError,
    InternalServerError,
    JobFailedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    TypesearchError,
)
from ._streaming import AsyncSearchStream, SearchStream
from ._version import __version__

__all__ = [
    "DEFAULT_BASE_URL",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AsyncJobs",
    "AsyncSearchStream",
    "AsyncTypesearch",
    "AuthenticationError",
    "BadRequestError",
    "BudgetError",
    "InternalServerError",
    "JobFailedError",
    "Jobs",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "SearchStream",
    "Typesearch",
    "TypesearchError",
    "__version__",
    "types",
]
