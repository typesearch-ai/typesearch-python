from __future__ import annotations

import inspect
import warnings

import typesearch
from typesearch import AsyncTypesearch, Typesearch, types
from typesearch._construct import construct
from typesearch.types import BooleanAnswer, ChoiceAnswer, Job, QueryDate, Result, ScoreAnswer, SearchResponse

from .fake_api import check, search_response


def test_the_examples_meet_the_contract() -> None:
    check("SearchResponse", search_response())


def test_responses_keep_what_they_do_not_know_and_tolerate_what_is_new() -> None:
    data = search_response(brand_new={"a": 1})
    data["results"][0].update(found_in="archive", novel=1)
    res = construct(SearchResponse, data)
    r = res.results[0]
    assert isinstance(r, Result)
    assert r.found_in == "archive"  # a value the SDK does not know yet
    assert r.novel == 1  # type: ignore[attr-defined]
    assert res.brand_new == {"a": 1}  # type: ignore[attr-defined]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dumped = res.model_dump()
        res.model_dump_json()
    assert dumped["results"][0]["novel"] == 1
    assert dumped["brand_new"] == {"a": 1}


def test_missing_fields_are_none_and_nothing_raises() -> None:
    res = construct(SearchResponse, {"id": "x", "results": [{"url": "u"}]})
    assert res.results[0].title is None  # type: ignore[comparison-overlap]
    assert res.usage is None  # type: ignore[comparison-overlap]
    assert construct(SearchResponse, None).id is None  # type: ignore[comparison-overlap]


def test_answers_are_built_as_the_variant_their_type_names() -> None:
    values = {
        "a": {"type": "boolean", "probability": 0.93},
        "b": {"type": "choice", "choice": "critical", "probabilities": {"critical": 0.81}, "confidence": 0.81},
        "c": {"type": "score", "score": 2.6, "confidence": 0.74},
        "d": {"type": "ranking", "order": [1, 2]},
    }
    r = construct(Result, {"answers": {"basis": "article", "values": values}})
    assert r.answers is not None
    v = r.answers.values
    assert isinstance(v["a"], BooleanAnswer) and v["a"].probability == 0.93
    assert isinstance(v["b"], ChoiceAnswer) and v["b"].choice == "critical"
    assert isinstance(v["c"], ScoreAnswer) and v["c"].score == 2.6
    assert v["d"].order == [1, 2]  # type: ignore[union-attr]


def test_reserved_words_are_fields_with_an_underscore() -> None:
    d = construct(
        QueryDate,
        {
            "expression": "today",
            "from": "2026-09-22",
            "to": "2026-09-22",
            "timezone": "UTC",
            "basis": "published",
            "window": None,
            "widened": False,
        },
    )
    assert d.from_ == "2026-09-22"
    assert d.model_dump(by_alias=True)["from"] == "2026-09-22"


def test_job_result_is_a_search_response() -> None:
    j = construct(Job, {"id": "job_1", "status": "succeeded", "result": search_response()})
    assert isinstance(j.result, SearchResponse)


def test_the_public_names() -> None:
    for name in typesearch.__all__:
        assert hasattr(typesearch, name), name
    for name in types.__all__:
        assert hasattr(types, name), name
    for name in [
        "SearchOptions",
        "SimilarOptions",
        "SiteSearchOptions",
        "ContentsOptions",
        "Result",
        "SearchResponse",
        "Mode",
        "Question",
        "Step",
    ]:
        assert name in types.__all__


def test_sync_and_async_clients_have_the_same_methods_and_arguments() -> None:
    def public(cls: type) -> dict[str, list[str]]:
        return {n: list(inspect.signature(f).parameters) for n, f in inspect.getmembers(cls, inspect.isfunction) if not n.startswith("_")}

    assert public(Typesearch) == public(AsyncTypesearch)
    assert public(type(Typesearch("k").jobs)) == public(type(AsyncTypesearch("k").jobs))
