from __future__ import annotations

import json
from types import TracebackType
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator, List, Optional, Tuple, Type, Union

import httpx
from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal

from ._construct import construct
from ._errors import APIConnectionError, TypesearchError, error_for
from ._models import SearchResponse

__all__ = ["AsyncSearchStream", "PartialEvent", "ResultEvent", "SearchStream", "SearchStreamEvent", "Step", "StepEvent"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", use_attribute_docstrings=True)


class Step(_Model):
    """A step of a streamed search: judging headlines, reading articles, classifying tone…"""

    id: str
    """Stable id of the step, such as ``juicio-indice``. Use it, and ``status``, in code."""
    text: str
    """Meant for people; it can change. In English unless the request asks for Spanish (``Accept-Language: es``)."""
    status: Literal["running", "done", "skipped", "failed"]
    detail: Optional[str] = None


class StepEvent(_Model):
    type: Literal["step"]
    step: Step


class PartialEvent(_Model):
    """Results judged so far. Each one is confirmed in place as its article is read."""

    type: Literal["partial"]
    response: SearchResponse


class ResultEvent(_Model):
    """The final result. The stream ends after it."""

    type: Literal["result"]
    response: SearchResponse


SearchStreamEvent = Union[StepEvent, PartialEvent, ResultEvent]
"""An event of ``search_stream()`` or ``site_search_stream()``. An ``error`` event is raised as an ``APIError``."""


class SSEDecoder:
    """Turns the lines of a Server-Sent Events body into ``(event, data)`` messages."""

    def __init__(self) -> None:
        self._event = "message"
        self._data: List[str] = []

    def feed(self, line: str) -> Optional[Tuple[str, str]]:
        if line == "":
            if not self._data:
                self._event = "message"
                return None
            message = (self._event, "\n".join(self._data))
            self._event, self._data = "message", []
            return message
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            self._event = value
        elif field == "data":
            self._data.append(value)
        return None

    def flush(self) -> Optional[Tuple[str, str]]:
        """A body that ends without the blank line still delivers its last message."""
        return self.feed("")


def _event(message: Tuple[str, str], response: httpx.Response) -> Optional[SearchStreamEvent]:
    name, data = message
    try:
        payload: Any = json.loads(data) if data else None
    except ValueError:
        raise TypesearchError(f"The API sent an event that is not valid JSON: {data[:200]}") from None
    if name == "step":
        return construct(StepEvent, {"type": "step", "step": payload})
    if name == "partial":
        return construct(PartialEvent, {"type": "partial", "response": payload})
    if name == "result":
        return construct(ResultEvent, {"type": "result", "response": payload})
    if name == "error":
        problem = payload if isinstance(payload, dict) else {}
        status = problem.get("status")
        raise error_for(status if isinstance(status, int) else 500, problem, response.headers)
    # Other events are new in the API: skipped, so an older SDK keeps working.
    return None


_ENDED = "The stream ended before the final result."


class SearchStream:
    """A streamed search. Iterate it for events, or call :meth:`final_response`. The request starts when
    you start iterating; use it as a context manager to close the connection when you are done::

        with ts.search_stream("el dólar", mode="deep") as stream:
            for event in stream:
                if event.type == "step":
                    print("·", event.step.text)
                elif event.type in ("partial", "result"):
                    render(event.response.results)
    """

    def __init__(self, open_response: Callable[[], httpx.Response]) -> None:
        self._open = open_response
        self._response: Optional[httpx.Response] = None
        self._final: Optional[SearchResponse] = None
        self._consumed = False

    def __iter__(self) -> Iterator[SearchStreamEvent]:
        if self._consumed:
            raise TypesearchError("A SearchStream can only be iterated once.")
        self._consumed = True
        self._response = self._open()
        decoder = SSEDecoder()
        try:
            try:
                for line in self._response.iter_lines():
                    message = decoder.feed(line)
                    if message:
                        yield from self._emit(message, self._response)
            except httpx.TransportError as e:
                raise APIConnectionError("The connection dropped while reading the stream.") from e
            tail = decoder.flush()
            if tail:
                yield from self._emit(tail, self._response)
            if self._final is None:
                raise APIConnectionError(_ENDED)
        finally:
            self.close()

    def _emit(self, message: Tuple[str, str], response: httpx.Response) -> Iterator[SearchStreamEvent]:
        event = _event(message, response)
        if event is not None:
            if isinstance(event, ResultEvent):
                self._final = event.response
            yield event

    def final_response(self) -> SearchResponse:
        """Consumes the stream and returns the final result (the ``result`` event)."""
        if not self._consumed:
            for _ in self:
                pass
        if self._final is None:
            raise APIConnectionError(_ENDED)
        return self._final

    def close(self) -> None:
        """Closes the connection. Safe to call more than once."""
        if self._response is not None:
            self._response.close()

    def __enter__(self) -> SearchStream:
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], tb: Optional[TracebackType]) -> None:
        self.close()


class AsyncSearchStream:
    """The async version of :class:`SearchStream`::

    async with ts.search_stream("el dólar") as stream:
        async for event in stream:
            ...
    """

    def __init__(self, open_response: Callable[[], Awaitable[httpx.Response]]) -> None:
        self._open = open_response
        self._response: Optional[httpx.Response] = None
        self._final: Optional[SearchResponse] = None
        self._consumed = False

    async def __aiter__(self) -> AsyncIterator[SearchStreamEvent]:
        if self._consumed:
            raise TypesearchError("A SearchStream can only be iterated once.")
        self._consumed = True
        self._response = await self._open()
        decoder = SSEDecoder()
        try:
            try:
                async for line in self._response.aiter_lines():
                    message = decoder.feed(line)
                    if message:
                        event = self._take(message, self._response)
                        if event is not None:
                            yield event
            except httpx.TransportError as e:
                raise APIConnectionError("The connection dropped while reading the stream.") from e
            tail = decoder.flush()
            if tail:
                event = self._take(tail, self._response)
                if event is not None:
                    yield event
            if self._final is None:
                raise APIConnectionError(_ENDED)
        finally:
            await self.close()

    def _take(self, message: Tuple[str, str], response: httpx.Response) -> Optional[SearchStreamEvent]:
        event = _event(message, response)
        if isinstance(event, ResultEvent):
            self._final = event.response
        return event

    async def final_response(self) -> SearchResponse:
        """Consumes the stream and returns the final result (the ``result`` event)."""
        if not self._consumed:
            async for _ in self:
                pass
        if self._final is None:
            raise APIConnectionError(_ENDED)
        return self._final

    async def close(self) -> None:
        """Closes the connection. Safe to call more than once."""
        if self._response is not None:
            await self._response.aclose()

    async def __aenter__(self) -> AsyncSearchStream:
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], tb: Optional[TracebackType]) -> None:
        await self.close()
