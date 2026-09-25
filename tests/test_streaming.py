from __future__ import annotations

import json
from typing import List, Optional, Tuple

import pytest

from typesearch import APIConnectionError, BudgetError, InternalServerError, SearchStream, Typesearch, TypesearchError
from typesearch._streaming import SSEDecoder
from typesearch.types import PartialEvent, ResultEvent, StepEvent

from .fake_api import STEP, FakeApi, Scripted, problem, search_response


def decode(*lines: str) -> List[Tuple[str, str]]:
    d = SSEDecoder()
    out = [m for m in (d.feed(line) for line in lines) if m]
    tail: Optional[Tuple[str, str]] = d.flush()
    return out + ([tail] if tail else [])


def test_decoder_events_comments_and_multi_line_data() -> None:
    assert decode(": latido", "", "event: step", 'data: {"a":1}', "", "data: line 1", "data: line 2", "") == [
        ("step", '{"a":1}'),
        ("message", "line 1\nline 2"),
    ]


def test_decoder_delivers_a_last_message_without_a_blank_line() -> None:
    assert decode("event: result", "data: {}") == [("result", "{}")]
    assert decode("event: result") == []


def test_search_stream_events_in_order(api: FakeApi, ts: Typesearch) -> None:
    with ts.search_stream("el dólar", mode="deep") as stream:
        events = list(stream)
    assert api.last.body == {"query": "el dólar", "mode": "deep", "stream": True}
    assert api.last.headers["accept"] == "text/event-stream"
    assert [e.type for e in events] == ["step", "partial", "step", "result"]
    step, partial, _, result = events
    assert isinstance(step, StepEvent) and step.step.status == "running" and step.step.text.startswith("The model")
    assert isinstance(partial, PartialEvent) and len(partial.response.results) == 1
    assert isinstance(result, ResultEvent) and len(result.response.results) == 2


def test_final_response(api: FakeApi, ts: Typesearch) -> None:
    assert ts.search_stream("el dólar").final_response().total == 2
    stream = ts.search_stream("el dólar")
    for _ in stream:
        pass
    assert stream.final_response().total == 2
    with pytest.raises(TypesearchError, match="once"):
        list(stream)


def test_the_request_starts_when_iteration_does(api: FakeApi, ts: Typesearch) -> None:
    stream = ts.search_stream("el dólar")
    assert api.requests == []
    stream.final_response()
    assert len(api.requests) == 1


def test_an_error_event_is_raised_as_the_typed_error(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(events=[{"event": "step", "data": STEP}, {"event": "error", "data": problem(402, "budget_too_small")}]))
    seen = []
    with pytest.raises(BudgetError) as e:
        for event in ts.search_stream("el dólar", max_tokens=2000):
            seen.append(event.type)
    assert seen == ["step"]
    assert e.value.code == "budget_too_small"


def test_a_stream_that_ends_before_the_result(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(raw=f"event: step\ndata: {json.dumps(STEP)}\n\n"))
    with pytest.raises(APIConnectionError, match="before the final result"):
        ts.search_stream("el dólar").final_response()


def test_unknown_events_are_skipped_and_bad_json_is_an_error(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(raw=f"event: novelty\ndata: {{}}\n\nevent: result\ndata: {json.dumps(search_response())}\n\n"))
    assert [e.type for e in ts.search_stream("el dólar")] == ["result"]
    api.next(Scripted(raw="event: result\ndata: {oops\n\n"))
    with pytest.raises(TypesearchError, match="not valid JSON"):
        ts.search_stream("el dólar").final_response()


def test_a_5xx_before_the_stream_starts_is_retried(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(status=503, headers={"retry-after": "0"}, body=problem(503, "upstream_unavailable")))
    assert ts.search_stream("el dólar").final_response().total == 2
    assert len(api.requests) == 2
    failing = Scripted(status=500, headers={"retry-after": "0"}, body=problem(500, "internal_error"))
    api.next(failing, failing, failing)
    with pytest.raises(InternalServerError):
        ts.search_stream("el dólar").final_response()


def test_leaving_the_loop_closes_the_connection(api: FakeApi, ts: Typesearch) -> None:
    api.next(Scripted(events=[{"event": "step", "data": STEP}], hang=True))
    with ts.search_stream("el dólar") as stream:
        for event in stream:
            assert event.type == "step"
            break
    assert api.wait_closed()


def test_site_search_stream(api: FakeApi, ts: Typesearch) -> None:
    stream: SearchStream = ts.site_search_stream("diarioejemplo.example", "el dólar", mode="normal")
    final = stream.final_response()
    assert api.last.path == "/v1/search/site"
    assert api.last.body == {"site": "diarioejemplo.example", "query": "el dólar", "mode": "normal", "stream": True}
    assert final.site == "diarioejemplo.example"
