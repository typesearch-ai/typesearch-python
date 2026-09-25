from __future__ import annotations

import pytest

from typesearch import APIConnectionError, AsyncSearchStream, AsyncTypesearch, BudgetError, JobFailedError, TypesearchError
from typesearch.types import SearchResponse, Source, Sources

from .fake_api import KEY, STEP, FakeApi, Scripted, problem

pytestmark = pytest.mark.anyio


async def test_endpoints(api: FakeApi, ats: AsyncTypesearch) -> None:
    res = await ats.search(["el dólar", "el FMI"], mode="fast", days=None)
    assert api.last.body == {"query": ["el dólar", "el FMI"], "mode": "fast", "days": None}
    assert isinstance(res, SearchResponse) and res.results[0].url.startswith("https://")

    similar = await ats.similar("https://diarioejemplo.example/a", mode="fast")
    assert similar.reference is not None and similar.reference.url == "https://diarioejemplo.example/a"

    pages = await ats.contents("https://reddiaria.example/economia/a", query="el Presupuesto 2027")
    assert pages.results[0].relevance == 0.97

    assert isinstance(await ats.sources(), Sources)
    site = await ats.sources(domain="diarioejemplo.example")
    assert isinstance(site, Source) and site.covered

    assert (await ats.usage()).today.remaining_tokens == 816080


async def test_site_search_and_jobs(api: FakeApi, ats: AsyncTypesearch) -> None:
    job = await ats.site_search("diarioejemplo.example", "el dólar")
    assert job.status == "queued"
    assert (await ats.jobs.get(job.id)).status == "running"
    res = await ats.site_search_and_wait("diarioejemplo.example", "el dólar", mode="normal", poll_interval=0.01)
    assert res.site == "diarioejemplo.example"
    failed = await ats.site_search("fail.example", "el dólar")
    with pytest.raises(JobFailedError):
        await ats.jobs.wait(failed.id, poll_interval=0.01)


async def test_stream(api: FakeApi, ats: AsyncTypesearch) -> None:
    types = [e.type async for e in ats.search_stream("el FMI", mode="deep")]
    assert types == ["step", "partial", "step", "result"]
    assert api.last.body == {"query": "el FMI", "mode": "deep", "stream": True}
    assert (await ats.search_stream("el FMI").final_response()).total == 2
    stream: AsyncSearchStream = ats.site_search_stream("diarioejemplo.example", "el dólar")
    assert (await stream.final_response()).site == "diarioejemplo.example"
    with pytest.raises(TypesearchError, match="once"):
        async for _ in stream:
            pass


async def test_stream_error_event_and_closing(api: FakeApi, ats: AsyncTypesearch) -> None:
    api.next(Scripted(events=[{"event": "step", "data": STEP}, {"event": "error", "data": problem(402, "budget_too_small")}]))
    with pytest.raises(BudgetError):
        async for _ in ats.search_stream("el dólar"):
            pass
    api.next(Scripted(events=[{"event": "step", "data": STEP}], hang=True))
    async with ats.search_stream("el dólar") as stream:
        async for event in stream:
            assert event.type == "step"
            break
    assert api.wait_closed()


async def test_the_client_as_a_context_manager(api: FakeApi) -> None:
    async with AsyncTypesearch(KEY, base_url=api.url) as client:
        await client.usage()
    assert client._http.is_closed


async def test_stream_edge_cases(api: FakeApi, ats: AsyncTypesearch) -> None:
    api.next(Scripted(raw='event: step\ndata: {"id":"a","text":"a","status":"running","detail":null}\n\n'))
    with pytest.raises(APIConnectionError, match="before the final result"):
        await ats.search_stream("el dólar").final_response()
    api.next(Scripted(raw="event: result\ndata: {oops\n\n"))
    with pytest.raises(TypesearchError, match="not valid JSON"):
        await ats.search_stream("el dólar").final_response()
    api.next(Scripted(raw='event: novelty\ndata: {}\n\nevent: result\ndata: {"id": "x", "results": []}'))
    assert (await ats.search_stream("el dólar").final_response()).id == "x"
