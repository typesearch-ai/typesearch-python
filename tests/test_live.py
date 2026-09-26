"""Contra la API de verdad: corre sólo con ``TYPESEARCH_LIVE=1`` y ``TYPESEARCH_API_KEY`` en el entorno.

    TYPESEARCH_LIVE=1 TYPESEARCH_API_KEY=ts_live_… uv run pytest tests/test_live.py -v

Gasta muy poco: tres búsquedas ``fast`` de 3 resultados y el contenido de una URL; ``usage`` no cobra. Con
``TYPESEARCH_LIVE_FULL=1`` suma ``similar`` y una búsqueda en un sitio en vivo.
``TYPESEARCH_BASE_URL`` apunta a otra API (local o de prueba).
"""

from __future__ import annotations

import os
from typing import Iterator
from urllib.parse import urlparse

import pytest

from typesearch import AsyncTypesearch, AuthenticationError, BadRequestError, Typesearch

KEY = os.environ.get("TYPESEARCH_API_KEY") if os.environ.get("TYPESEARCH_LIVE") == "1" else None
FULL = os.environ.get("TYPESEARCH_LIVE_FULL") == "1"

pytestmark = pytest.mark.skipif(not KEY, reason="set TYPESEARCH_LIVE=1 and TYPESEARCH_API_KEY to run against the real API")


@pytest.fixture(scope="module")
def live() -> Iterator[Typesearch]:
    with Typesearch(KEY) as ts:
        yield ts


@pytest.fixture(scope="module")
def found(live: Typesearch) -> list[str]:
    res = live.search("inflación", mode="fast", max_results=3, days=7)
    assert res.object == "search"
    assert len(res.results) <= 3
    for r in res.results:
        assert r.score >= 0.5
        assert r.url.startswith("http")
    return [r.url for r in res.results]


def test_usage_is_free(live: Typesearch) -> None:
    usage = live.usage()
    assert usage.limits.requests_per_minute > 0


def test_search_and_contents(live: Typesearch, found: list[str]) -> None:
    if found:
        pages = live.contents(found[:1])
        assert pages.results[0].url == found[0]


def test_search_by_country_and_language(live: Typesearch) -> None:
    res = live.search("inflación", mode="fast", max_results=3, days=7, countries=["AR"], languages=["es"])
    for r in res.results:
        assert (r.country, r.language) == ("AR", "es")


def test_stream(live: Typesearch) -> None:
    with live.search_stream("inflación", mode="fast", max_results=3, days=7) as stream:
        types = {e.type for e in stream}
    assert "result" in types


def test_typed_errors(live: Typesearch) -> None:
    with pytest.raises(BadRequestError):
        live.search("x")
    with Typesearch("ts_live_invalid") as bad, pytest.raises(AuthenticationError):
        bad.usage()


@pytest.mark.anyio
async def test_async_usage() -> None:
    async with AsyncTypesearch(KEY) as ts:
        assert (await ts.usage()).object == "usage"


@pytest.mark.skipif(not FULL, reason="set TYPESEARCH_LIVE_FULL=1")
def test_similar_and_live_site_search(live: Typesearch, found: list[str]) -> None:
    if found:
        assert live.similar(found[0], mode="fast", max_results=3).object == "similar"
    host = urlparse(found[0]).hostname if found else "example.com"
    assert live.site_search_and_wait(host or "example.com", "economía", mode="fast", max_results=3).object == "site_search"
