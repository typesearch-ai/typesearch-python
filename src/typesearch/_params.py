# Generado por scripts/generate_models.py desde el OpenAPI de la API (1.0.0, 336df2c4e996).
# No editar a mano: `python scripts/generate_models.py` (con --fetch trae el vivo).
"""Request options of the typesearch API, generated from its OpenAPI document."""

from __future__ import annotations

import datetime as _dt
from typing import Any, FrozenSet, List, Mapping, Optional, Sequence, Union

from typing_extensions import Literal, NotRequired, Required, TypedDict

__all__ = [
    "BooleanCriteria",
    "BooleanQuestion",
    "ChoiceQuestion",
    "ContentsOptions",
    "DateLike",
    "JsonValue",
    "Mode",
    "NULLABLE",
    "Question",
    "ScoreQuestion",
    "SearchOptions",
    "SimilarOptions",
    "SiteSearchOptions",
]

DateLike = Union[str, _dt.date, _dt.datetime]
"""A date (``"2026-09-20"`` or ``datetime.date``) or a date-time with a time zone (a string or an aware ``datetime``)."""

JsonValue = Union[str, int, float, bool, None, List[Any], Mapping[str, Any]]
"""Any JSON value."""

NULLABLE: FrozenSet[str] = frozenset({"days", "max_tokens"})
"""Options where ``None`` means something (``days=None``: the whole index) and is sent as ``null``."""


Mode = Literal["ultra", "fast", "normal", "deep"]
"""ultra: headlines only, the cheapest · fast: headlines and standfirsts · normal: reads the best matches · deep: more headlines, the topic also in other words (synonyms and acronyms), twice the reading, snippets and the essentials of each article, and the search of the sites that cover the topic when the index falls short."""


class SearchOptions(TypedDict, total=False):
    """Keyword arguments of ``search()`` and ``search_stream()``: every field of ``POST /v1/search`` but ``query``."""

    sources: NotRequired[Sequence[str]]
    """Only these index sources, by domain, such as example.com. GET /v1/sources?domain=… tells you whether a domain is covered. 1–100 items."""
    include_domains: NotRequired[Sequence[str]]
    """Only these domains or paths. A domain includes its subdomains. At most 20 items."""
    exclude_domains: NotRequired[Sequence[str]]
    """Never these domains or paths. At most 20 items."""
    countries: NotRequired[Sequence[str]]
    """Only sources from these countries: ISO 3166-1 alpha-2 codes, such as AR or US. GET /v1/sources tells how many sources each country has. 1–50 items."""
    languages: NotRequired[Sequence[str]]
    """Only sources that publish in these languages: ISO 639-1 codes, such as es or en (a BCP 47 tag such as pt-BR counts as pt). 1–20 items."""
    sections: NotRequired[Sequence[str]]
    """Only these sections: the section in the feed, or the start of the URL path. At most 20 items."""
    days: NotRequired[Optional[int]]
    """The last N days; null for the whole index. Defaults to 7 unless dates are given. 1–365."""
    published_after: NotRequired[DateLike]
    """Published on or after this date. A bare date is read in Argentina time (UTC−3)."""
    published_before: NotRequired[DateLike]
    """Published on or before this date; a bare date includes that whole day."""
    mode: NotRequired[Mode]
    """ultra: headlines only, the cheapest · fast: headlines and standfirsts · normal: reads the best matches · deep: more headlines, the topic also in other words (synonyms and acronyms), twice the reading, snippets and the essentials of each article, and the search of the sites that cover the topic when the index falls short. Defaults to ``"normal"``."""
    max_results: NotRequired[int]
    """1–50. Defaults to ``10``."""
    highlights: NotRequired[bool]
    """Very short verbatim excerpts (up to 25 words, never from the first paragraph) from the articles that were read: one per article, two in deep mode. On by default only in deep mode."""
    dedupe: NotRequired[bool]
    """Groups the same story reported by several outlets. Defaults to ``false``."""
    tone: NotRequired[bool]
    """Tone toward the query: positive, neutral or negative. Defaults to ``false``."""
    essential: NotRequired[bool]
    """The essentials: very short verbatim excerpts across several articles. On by default only in deep mode."""
    questions: NotRequired[Mapping[str, Question]]
    """Structured output: typed questions (boolean, choice, score) that the model answers for each result."""
    max_tokens: NotRequired[Optional[int]]
    """Cap on model tokens. If it is reached, the response comes back with incomplete: true. At least 2000."""
    fresh: NotRequired[bool]
    """Skips the result cache (10 minutes). Defaults to ``false``."""
    temporal: NotRequired[Literal["auto", "off"]]
    """auto: a date in the query («today», «yesterday», «tomorrow», «on September 22», «this week») is taken out of the topic, sets the publication window (unless published_after/before are given; days only bounds it) and puts the results from that day first · off: the query is taken literally. Defaults to ``"auto"``."""
    timezone: NotRequired[str]
    """IANA time zone that decides what day «today» is. Defaults to Argentina (America/Argentina/Buenos_Aires)."""


class BooleanQuestion(TypedDict, total=False):
    type: Required[Literal["boolean"]]
    instructions: Required[Union[str, Mapping[str, JsonValue], Sequence[JsonValue]]]
    criteria: NotRequired[BooleanCriteria]


class BooleanCriteria(TypedDict, total=False):
    true: NotRequired[str]
    false: NotRequired[str]


class ChoiceQuestion(TypedDict, total=False):
    type: Required[Literal["choice"]]
    instructions: Required[Union[str, Mapping[str, JsonValue], Sequence[JsonValue]]]
    criteria: Required[Mapping[str, Optional[str]]]


class ScoreQuestion(TypedDict, total=False):
    type: Required[Literal["score"]]
    instructions: Required[Union[str, Mapping[str, JsonValue], Sequence[JsonValue]]]
    criteria: Required[Sequence[str]]
    """At least 2 items."""


class SimilarOptions(TypedDict, total=False):
    """Keyword arguments of ``similar()``: every field of ``POST /v1/similar`` but ``url``."""

    sources: NotRequired[Sequence[str]]
    """Only these index sources, by domain, such as example.com. GET /v1/sources?domain=… tells you whether a domain is covered. 1–100 items."""
    include_domains: NotRequired[Sequence[str]]
    """Only these domains or paths. A domain includes its subdomains. At most 20 items."""
    exclude_domains: NotRequired[Sequence[str]]
    """Never these domains or paths. At most 20 items."""
    countries: NotRequired[Sequence[str]]
    """Only sources from these countries: ISO 3166-1 alpha-2 codes, such as AR or US. GET /v1/sources tells how many sources each country has. 1–50 items."""
    languages: NotRequired[Sequence[str]]
    """Only sources that publish in these languages: ISO 639-1 codes, such as es or en (a BCP 47 tag such as pt-BR counts as pt). 1–20 items."""
    sections: NotRequired[Sequence[str]]
    """Only these sections: the section in the feed, or the start of the URL path. At most 20 items."""
    days: NotRequired[Optional[int]]
    """The last N days; null for the whole index. Defaults to 7 unless dates are given. 1–365."""
    published_after: NotRequired[DateLike]
    """Published on or after this date. A bare date is read in Argentina time (UTC−3)."""
    published_before: NotRequired[DateLike]
    """Published on or before this date; a bare date includes that whole day."""
    mode: NotRequired[Mode]
    """ultra: headlines only, the cheapest · fast: headlines and standfirsts · normal: reads the best matches · deep: more headlines, the topic also in other words (synonyms and acronyms), twice the reading, snippets and the essentials of each article, and the search of the sites that cover the topic when the index falls short. Defaults to ``"normal"``."""
    max_results: NotRequired[int]
    """1–50. Defaults to ``10``."""
    highlights: NotRequired[bool]
    """Very short verbatim excerpts (up to 25 words, never from the first paragraph) from the articles that were read: one per article, two in deep mode. On by default only in deep mode."""
    dedupe: NotRequired[bool]
    """Groups the same story reported by several outlets. Defaults to ``false``."""
    tone: NotRequired[bool]
    """Tone toward the query: positive, neutral or negative. Defaults to ``false``."""
    essential: NotRequired[bool]
    """The essentials: very short verbatim excerpts across several articles. On by default only in deep mode."""
    questions: NotRequired[Mapping[str, Question]]
    """Structured output: typed questions (boolean, choice, score) that the model answers for each result."""
    max_tokens: NotRequired[Optional[int]]
    """Cap on model tokens. If it is reached, the response comes back with incomplete: true. At least 2000."""
    fresh: NotRequired[bool]
    """Skips the result cache (10 minutes). Defaults to ``false``."""
    temporal: NotRequired[Literal["auto", "off"]]
    """auto: a date in the query («today», «yesterday», «tomorrow», «on September 22», «this week») is taken out of the topic, sets the publication window (unless published_after/before are given; days only bounds it) and puts the results from that day first · off: the query is taken literally. Defaults to ``"auto"``."""
    timezone: NotRequired[str]
    """IANA time zone that decides what day «today» is. Defaults to Argentina (America/Argentina/Buenos_Aires)."""


class SiteSearchOptions(TypedDict, total=False):
    """Keyword arguments of ``site_search()``: every field of ``POST /v1/search/site`` but ``site`` and ``query``."""

    sections: NotRequired[Sequence[str]]
    """Only these sections: the section in the feed, or the start of the URL path. At most 20 items."""
    exclude_domains: NotRequired[Sequence[str]]
    """Never these domains or paths. At most 20 items."""
    mode: NotRequired[Mode]
    """ultra: headlines only, the cheapest · fast: headlines and standfirsts · normal: reads the best matches · deep: more headlines, the topic also in other words (synonyms and acronyms), twice the reading, snippets and the essentials of each article, and the search of the sites that cover the topic when the index falls short. Defaults to ``"normal"``."""
    max_results: NotRequired[int]
    """1–50. Defaults to ``10``."""
    highlights: NotRequired[bool]
    """Very short verbatim excerpts (up to 25 words, never from the first paragraph) from the articles that were read: one per article, two in deep mode. On by default only in deep mode."""
    dedupe: NotRequired[bool]
    """Groups the same story reported by several outlets. Defaults to ``false``."""
    tone: NotRequired[bool]
    """Tone toward the query: positive, neutral or negative. Defaults to ``false``."""
    essential: NotRequired[bool]
    """The essentials: very short verbatim excerpts across several articles. On by default only in deep mode."""
    questions: NotRequired[Mapping[str, Question]]
    """Structured output: typed questions (boolean, choice, score) that the model answers for each result."""
    max_tokens: NotRequired[Optional[int]]
    """Cap on model tokens. If it is reached, the response comes back with incomplete: true. At least 2000."""
    fresh: NotRequired[bool]
    """Skips the result cache (10 minutes). Defaults to ``false``."""
    temporal: NotRequired[Literal["auto", "off"]]
    """auto: a date in the query («today», «yesterday», «tomorrow», «on September 22», «this week») is taken out of the topic, sets the publication window (unless published_after/before are given; days only bounds it) and puts the results from that day first · off: the query is taken literally. Defaults to ``"auto"``."""
    timezone: NotRequired[str]
    """IANA time zone that decides what day «today» is. Defaults to Argentina (America/Argentina/Buenos_Aires)."""


class ContentsOptions(TypedDict, total=False):
    """Keyword arguments of ``contents()``: every field of ``POST /v1/contents`` but ``urls``."""

    query: NotRequired[str]
    """With a query, the model picks the excerpt about it and says how much each article covers it."""
    highlights: NotRequired[bool]
    """Defaults to ``true``."""
    max_tokens: NotRequired[Optional[int]]
    """Cap on model tokens. If it is reached, the response comes back with incomplete: true. At least 2000."""


Question = Union[BooleanQuestion, ChoiceQuestion, ScoreQuestion]
