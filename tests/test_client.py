from __future__ import annotations

import datetime as dt

import httpx
import pytest

import typesearch
from typesearch import (
    DEFAULT_BASE_URL,
    APITimeoutError,
    BadRequestError,
    JobFailedError,
    NotFoundError,
    Typesearch,
    TypesearchError,
)
from typesearch.types import Result, SearchResponse

from .fake_api import KEY, FakeApi


def test_key_from_argument_or_environment_or_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TYPESEARCH_API_KEY", raising=False)
    monkeypatch.delenv("TYPESEARCH_BASE_URL", raising=False)
    with pytest.raises(TypesearchError, match="TYPESEARCH_API_KEY"):
        Typesearch()
    assert Typesearch("ts_live_a").base_url == DEFAULT_BASE_URL
    assert Typesearch("ts_live_a", base_url="http://localhost:3000/").base_url == "http://localhost:3000"
    monkeypatch.setenv("TYPESEARCH_API_KEY", " ts_live_env ")
    monkeypatch.setenv("TYPESEARCH_BASE_URL", "http://127.0.0.1:9/")
    c = Typesearch()
    assert c.base_url == "http://127.0.0.1:9"
    assert (c.timeout, c.max_retries) == (70.0, 2)
    assert "ts_live_env" not in repr(c)


def test_version() -> None:
    from importlib.metadata import version

    assert typesearch.__version__ == version("typesearch")


def test_headers(api: FakeApi, ts: Typesearch) -> None:
    ts.usage()
    assert api.last.headers["authorization"] == f"Bearer {KEY}"
    assert api.last.headers["user-agent"] == f"typesearch-python/{typesearch.__version__}"
    assert api.last.headers["accept"] == "application/json"
    with Typesearch(KEY, base_url=api.url, default_headers={"X-Trace": "a", "User-Agent": "mine/1"}) as other:
        other.usage(extra_headers={"x-trace": "b"})
    assert api.last.headers["user-agent"] == "mine/1"
    assert api.last.headers["x-trace"] == "b"


def test_search_sends_the_query_and_options_as_the_api_names_them(api: FakeApi, ts: Typesearch) -> None:
    res = ts.search(
        "el dólar",
        mode="normal",
        max_results=10,
        include_domains=["reddiaria.example", "diarioejemplo.example"],
        published_after="2026-09-20",
        highlights=True,
        tone=None,  # None means "the API's default": left out
    )
    assert (api.last.method, api.last.path) == ("POST", "/v1/search")
    assert api.last.headers["content-type"] == "application/json"
    assert api.last.body == {
        "query": "el dólar",
        "mode": "normal",
        "max_results": 10,
        "include_domains": ["reddiaria.example", "diarioejemplo.example"],
        "published_after": "2026-09-20",
        "highlights": True,
    }
    assert isinstance(res, SearchResponse)
    assert isinstance(res.results[0], Result)
    assert f"{res.results[0].score:.2f}" == "0.95"
    assert res.results[0].highlights == []


def test_several_queries_days_none_dates_and_questions(api: FakeApi, ts: Typesearch) -> None:
    res = ts.search(
        ("el dólar", "el FMI"),
        mode="fast",
        days=None,
        published_after=dt.date(2026, 9, 20),
        published_before=dt.datetime(2026, 9, 22, 12, 0, tzinfo=dt.timezone.utc),
        questions={
            "stance": {"type": "choice", "instructions": "What is the stance?", "criteria": {"supportive": None, "critical": None}},
            "impact": {"type": "score", "instructions": "How much?", "criteria": ["None", "High"]},
        },
    )
    body = api.last.body
    assert body["query"] == ["el dólar", "el FMI"]
    assert body["days"] is None
    assert body["published_after"] == "2026-09-20"
    assert body["published_before"] == "2026-09-22T12:00:00+00:00"
    assert body["questions"]["stance"]["criteria"] == {"supportive": None, "critical": None}
    assert res.queries == ["el dólar", "el FMI"]


def test_countries_and_languages_filter_the_sources_and_each_result_says_its_own(api: FakeApi, ts: Typesearch) -> None:
    res = ts.search("inflación", countries=["AR", "UY"], languages=("es",))
    assert api.last.body == {"query": "inflación", "countries": ["AR", "UY"], "languages": ["es"]}
    assert (res.results[0].country, res.results[0].language) == ("AR", "es")


def test_a_datetime_without_time_zone_is_refused_before_sending(api: FakeApi, ts: Typesearch) -> None:
    with pytest.raises(ValueError, match="time zone"):
        ts.search("el dólar", published_after=dt.datetime(2026, 9, 20, 10, 0))
    assert api.requests == []


def test_an_unknown_option_reaches_the_api_and_comes_back_as_a_typed_error(api: FakeApi, ts: Typesearch) -> None:
    with pytest.raises(BadRequestError) as e:
        ts.search("el dólar", colour="red")  # type: ignore[call-arg]
    assert e.value.status == 400
    assert e.value.code == "invalid_request"
    assert "colour" in e.value.errors[0]["message"]
    assert e.value.request_id == "req_fakeerr1"
    assert len(api.requests) == 1  # a 400 is not retried


def test_similar(api: FakeApi, ts: Typesearch) -> None:
    res = ts.similar("https://diarioejemplo.example/economia/nota", mode="fast", exclude_domains=["diarioejemplo.example"])
    assert api.last.path == "/v1/similar"
    assert api.last.body == {
        "url": "https://diarioejemplo.example/economia/nota",
        "mode": "fast",
        "exclude_domains": ["diarioejemplo.example"],
    }
    assert res.object == "similar"
    assert res.reference is not None and res.reference.url == "https://diarioejemplo.example/economia/nota"
    ts.similar("https://diarioejemplo.example/economia/nota", countries=["AR"], languages=["es"])
    assert api.last.body == {"url": "https://diarioejemplo.example/economia/nota", "countries": ["AR"], "languages": ["es"]}


def test_contents_with_a_list_or_one_url(api: FakeApi, ts: Typesearch) -> None:
    res = ts.contents(["https://reddiaria.example/economia/a", "https://unreachable.example/b"], query="el Presupuesto 2027")
    assert api.last.body == {
        "urls": ["https://reddiaria.example/economia/a", "https://unreachable.example/b"],
        "query": "el Presupuesto 2027",
    }
    assert [p.status for p in res.results] == ["ok", "error"]
    assert res.results[0].relevance == 0.97
    assert res.results[1].error is not None and res.results[1].error.code == "site_unreachable"
    ts.contents("https://reddiaria.example/economia/a")
    assert api.last.body == {"urls": ["https://reddiaria.example/economia/a"]}


def test_site_search_returns_the_job(api: FakeApi, ts: Typesearch) -> None:
    job = ts.site_search("diarioejemplo.example", "el dólar", mode="normal")
    assert api.last.body == {"site": "diarioejemplo.example", "query": "el dólar", "mode": "normal"}
    assert job.status == "queued"
    assert ts.jobs.get(job.id).status == "running"
    assert api.last.path == f"/v1/jobs/{job.id}"


def test_site_search_and_wait(api: FakeApi, ts: Typesearch) -> None:
    res = ts.site_search_and_wait("diarioejemplo.example", "el dólar", mode="normal", max_results=10, poll_interval=0.01)
    assert res.site == "diarioejemplo.example"
    assert res.object == "site_search"
    assert [r.method for r in api.requests] == ["POST", "GET", "GET"]
    assert "poll_interval" not in api.requests[0].body


def test_jobs_wait_raises_job_failed_error(api: FakeApi, ts: Typesearch) -> None:
    job = ts.site_search("fail.example", "el dólar")
    with pytest.raises(JobFailedError) as e:
        ts.jobs.wait(job.id, poll_interval=0.01)
    assert e.value.code == "site_unreachable"
    assert e.value.job.id == job.id
    assert str(e.value) == "The site did not answer."


def test_jobs_wait_gives_up_after_its_timeout(api: FakeApi, ts: Typesearch) -> None:
    job = ts.site_search("diarioejemplo.example", "el dólar")
    with pytest.raises(APITimeoutError, match="did not finish"):
        ts.jobs.wait(job.id, poll_interval=0.05, timeout=0.01)


def test_an_unknown_job_is_not_found_and_the_id_is_escaped(api: FakeApi, ts: Typesearch) -> None:
    with pytest.raises(NotFoundError):
        ts.jobs.get("job_nope/../x")
    assert api.last.path == "/v1/jobs/job_nope%2F..%2Fx"


def test_the_index_coverage_is_not_part_of_the_public_api() -> None:
    assert not hasattr(Typesearch, "sources")
    assert not hasattr(typesearch.AsyncTypesearch, "sources")


def test_usage(api: FakeApi, ts: Typesearch) -> None:
    u = ts.usage()
    assert api.last.path == "/v1/usage"
    assert u.today.remaining_tokens == 816080
    assert u.limits.requests_per_minute == 600


def test_your_own_http_client_is_used_and_not_closed(api: FakeApi) -> None:
    http = httpx.Client(headers={"x-from": "mine"})
    with Typesearch(KEY, base_url=api.url, http_client=http) as ts:
        ts.usage()
    assert api.last.headers["x-from"] == "mine"
    assert not http.is_closed
    http.close()
