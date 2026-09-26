from __future__ import annotations

import time
from types import TracebackType
from typing import Any, Dict, Mapping, Optional, Sequence, Type, TypeVar, Union

import anyio
import httpx
from pydantic import BaseModel
from typing_extensions import Unpack

from ._base import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_WAIT_TIMEOUT,
    BaseClient,
    as_list,
    body,
    job_path,
    retry_delay,
    should_retry,
)
from ._construct import construct
from ._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    JobFailedError,
    TypesearchError,
    error_from_response,
    retry_after_seconds,
)
from ._models import ContentsResponse, Job, SearchResponse, Usage
from ._params import ContentsOptions, SearchOptions, SimilarOptions, SiteSearchOptions
from ._streaming import AsyncSearchStream

M = TypeVar("M", bound=BaseModel)


class AsyncTypesearch(BaseClient):
    """The async typesearch API client, with the same methods as :class:`Typesearch`, awaitable.

    >>> from typesearch import AsyncTypesearch
    >>> async with AsyncTypesearch() as ts:  # reads TYPESEARCH_API_KEY
    ...     res = await ts.search("el dólar", mode="fast", max_results=5)
    ...     async for event in ts.search_stream("el FMI"):
    ...         ...
    """

    jobs: AsyncJobs
    """Live site search jobs: ``get()`` and ``wait()``."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Args:
            api_key: Your key. Defaults to the ``TYPESEARCH_API_KEY`` environment variable.
            base_url: Defaults to ``TYPESEARCH_BASE_URL``, or ``https://api.typesearch.ai``.
            timeout: Seconds before a request is aborted. A ``deep`` search can take about a minute.
            max_retries: Retries on connection errors, ``429 rate_limited`` and ``5xx``.
            default_headers: Headers sent with every request.
            http_client: Your own ``httpx.AsyncClient``, for proxies or tests. You close it.
        """
        super().__init__(api_key, base_url, timeout, max_retries, default_headers)
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient()
        self.jobs = AsyncJobs(self)

    # --- Endpoints -----------------------------------------------------------------------

    async def search(
        self,
        query: Union[str, Sequence[str]],
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SearchOptions],
    ) -> SearchResponse:
        """Searches the index: one query, or up to five judged together (results merged, plus one entry per
        query in ``groups``). Every result has a calibrated ``score``.

        Keyword arguments have the same names as the HTTP API: https://typesearch.ai/docs/api-reference/search.
        ``days=None`` searches the whole index; leaving ``days`` out keeps the default of 7.
        """
        data = body({"query": query if isinstance(query, str) else list(query)}, options)
        return await self._post("/v1/search", data, SearchResponse, timeout, max_retries, extra_headers)

    def search_stream(
        self,
        query: Union[str, Sequence[str]],
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SearchOptions],
    ) -> AsyncSearchStream:
        """The same search as a stream of events: ``step``, ``partial`` (results so far) and ``result``.

        The request starts when you start iterating. See https://typesearch.ai/docs/guides/streaming.
        """
        data = body({"query": query if isinstance(query, str) else list(query)}, options)
        data["stream"] = True
        return AsyncSearchStream(lambda: self._send("POST", "/v1/search", data, True, timeout, max_retries, extra_headers))

    async def similar(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SimilarOptions],
    ) -> SearchResponse:
        """Articles in the index about the same story as a URL. The response has the shape of a search, with
        the reference article in ``reference``."""
        return await self._post("/v1/similar", body({"url": url}, options), SearchResponse, timeout, max_retries, extra_headers)

    async def contents(
        self,
        urls: Union[str, Sequence[str]],
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[ContentsOptions],
    ) -> ContentsResponse:
        """Metadata and a short verbatim excerpt of up to 10 URLs — never the full text. With ``query``, the
        excerpt about it and each page's ``relevance``. Each URL has its own ``status``."""
        return await self._post(
            "/v1/contents", body({"urls": as_list(urls)}, options), ContentsResponse, timeout, max_retries, extra_headers
        )

    async def site_search(
        self,
        site: str,
        query: str,
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SiteSearchOptions],
    ) -> Job:
        """Searches a live site: its homepage, its sections and its own search box. It can take up to a minute,
        so it returns a job: wait for it with ``jobs.wait()``, or use :meth:`site_search_and_wait`."""
        return await self._post("/v1/search/site", body({"site": site, "query": query}, options), Job, timeout, max_retries, extra_headers)

    async def site_search_and_wait(
        self,
        site: str,
        query: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SiteSearchOptions],
    ) -> SearchResponse:
        """:meth:`site_search`, then waits for the job and returns its result. Raises :class:`JobFailedError`
        if the job fails, and :class:`APITimeoutError` if it takes longer than ``wait_timeout`` seconds."""
        job = await self.site_search(site, query, timeout=timeout, max_retries=max_retries, extra_headers=extra_headers, **options)
        return await self.jobs.wait(job.id, poll_interval=poll_interval, timeout=wait_timeout)

    def site_search_stream(
        self,
        site: str,
        query: str,
        *,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        **options: Unpack[SiteSearchOptions],
    ) -> AsyncSearchStream:
        """A live site search as a stream of events, instead of a job."""
        data = body({"site": site, "query": query}, options)
        data["stream"] = True
        return AsyncSearchStream(lambda: self._send("POST", "/v1/search/site", data, True, timeout, max_retries, extra_headers))

    async def usage(self, *, timeout: Optional[float] = None, extra_headers: Optional[Mapping[str, str]] = None) -> Usage:
        """Usage today and over the last 30 days, the limits of this key, its credit and the price list."""
        return await self._get("/v1/usage", Usage, timeout, extra_headers)

    # --- Lifecycle -----------------------------------------------------------------------

    async def close(self) -> None:
        """Closes the connections, unless you passed your own ``http_client``."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncTypesearch:
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], tb: Optional[TracebackType]) -> None:
        await self.close()

    # --- Transport -----------------------------------------------------------------------

    async def _get(
        self, path: str, model: Type[M], timeout: Optional[float] = None, extra_headers: Optional[Mapping[str, str]] = None
    ) -> M:
        return self._parse(await self._send("GET", path, None, False, timeout, None, extra_headers), model)

    async def _post(
        self,
        path: str,
        data: Dict[str, Any],
        model: Type[M],
        timeout: Optional[float],
        max_retries: Optional[int],
        extra_headers: Optional[Mapping[str, str]],
    ) -> M:
        return self._parse(await self._send("POST", path, data, False, timeout, max_retries, extra_headers), model)

    @staticmethod
    def _parse(response: httpx.Response, model: Type[M]) -> M:
        try:
            return construct(model, response.json())
        except ValueError:
            raise TypesearchError(
                f"The API answered {response.request.method} {response.request.url.path} with a body that is not JSON."
            ) from None

    async def _send(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]],
        stream: bool,
        timeout: Optional[float],
        max_retries: Optional[int],
        extra_headers: Optional[Mapping[str, str]],
    ) -> httpx.Response:
        retries = self.max_retries if max_retries is None else max_retries
        attempt = 0
        while True:
            wait: Optional[float] = None
            request = self._build(self._http, method, path, data, stream, timeout, extra_headers)
            try:
                response = await self._http.send(request, stream=stream)
            except httpx.TimeoutException as e:
                error: TypesearchError = APITimeoutError(f"Request timed out after {self.timeout if timeout is None else timeout} s.")
                error.__cause__ = e
            except httpx.TransportError as e:
                error = APIConnectionError()
                error.__cause__ = e
            else:
                if response.is_success:
                    return response
                try:
                    await response.aread()
                finally:
                    await response.aclose()
                api_error: APIError = error_from_response(response)
                if not should_retry(response.status_code, api_error.code):
                    raise api_error
                error, wait = api_error, retry_after_seconds(response.headers)
            if attempt >= retries:
                raise error
            await anyio.sleep(retry_delay(attempt, wait))
            attempt += 1


class AsyncJobs:
    """Live site search jobs (async)."""

    def __init__(self, client: AsyncTypesearch) -> None:
        self._client = client

    async def get(self, job_id: str) -> Job:
        """A job's status and, when it succeeded, its ``result``. Jobs last one day and are only visible to the
        key that created them."""
        return await self._client._get(job_path(job_id), Job)

    async def wait(
        self, job_id: str, *, poll_interval: float = DEFAULT_POLL_INTERVAL, timeout: float = DEFAULT_WAIT_TIMEOUT
    ) -> SearchResponse:
        """Polls a job until it finishes and returns its result. Raises :class:`JobFailedError` if it fails, and
        :class:`APITimeoutError` if it does not finish within ``timeout`` seconds."""
        deadline = time.monotonic() + timeout
        while True:
            job = await self.get(job_id)
            if job.status == "succeeded" and job.result is not None:
                return job.result
            if job.status == "failed":
                raise JobFailedError(job)
            if time.monotonic() + poll_interval > deadline:
                raise APITimeoutError(f"Job {job_id} did not finish in time (last status: {job.status}).")
            await anyio.sleep(poll_interval)
