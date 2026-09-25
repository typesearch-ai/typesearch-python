# Generado por scripts/generate_models.py desde el OpenAPI de la API (1.0.0, 336df2c4e996).
# No editar a mano: `python scripts/generate_models.py` (con --fetch trae el vivo).
"""Response models of the typesearch API, generated from its OpenAPI document."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

__all__ = [
    "Answer",
    "Answers",
    "BooleanAnswer",
    "Budget",
    "ChoiceAnswer",
    "ContentsError",
    "ContentsResponse",
    "ContentsResult",
    "ContentsUsage",
    "CountryCoverage",
    "Credit",
    "DateWindow",
    "Diffusion",
    "DiffusionDay",
    "DiffusionSource",
    "Discovery",
    "Duplicate",
    "Essential",
    "EssentialExcerpt",
    "FieldError",
    "FirstPublication",
    "IndexInfo",
    "Job",
    "LanguageCoverage",
    "Mode",
    "PagePricing",
    "Pricing",
    "Problem",
    "QueryDate",
    "QueryGroup",
    "Reading",
    "Reference",
    "RequestPricing",
    "ResponseWarning",
    "Result",
    "ResultTone",
    "ScoreAnswer",
    "SearchResponse",
    "SearchUsage",
    "Source",
    "SourceTone",
    "Sources",
    "ToneCounts",
    "ToneSummary",
    "Usage",
    "UsageKey",
    "UsageLimits",
    "UsagePeriod",
    "UsageToday",
]


class _Model(BaseModel):
    """Every response model keeps the fields it does not know, so a newer API never breaks an older SDK."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, use_attribute_docstrings=True, protected_namespaces=())

    # Built without validation, a model can hold values its annotations do not expect (a new enum value): no
    # serializer warnings for them.
    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("warnings", False)
        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
        kwargs.setdefault("warnings", False)
        return super().model_dump_json(*args, **kwargs)


Mode = Literal["ultra", "fast", "normal", "deep"]


class SearchResponse(_Model):
    id: str
    """The request id, also in the ``X-Request-Id`` header."""
    object: Literal["search", "site_search", "similar"]
    mode: Mode
    queries: List[str]
    found: bool
    """Whether any result scored 0.5 or more."""
    total: int
    """How many relevant articles exist; it can be more than ``max_results``."""
    results: List[Result]
    """The relevant articles, most relevant first."""
    groups: Optional[List[QueryGroup]]
    """With several queries: the breakdown for each one."""
    near_misses: List[Result]
    """If nothing was found: the closest matches."""
    rejected: List[Result]
    """The headline looked relevant, but reading the article ruled it out."""
    diffusion: Optional[Diffusion]
    """Articles per day and per source, and who published first."""
    tone: Optional[ToneSummary]
    """Tone counts overall and by source, when ``tone=True``."""
    essential: Optional[Essential]
    """Up to three verbatim excerpts that capture the story, when ``essential`` is on."""
    reference: Optional[Reference]
    """The reference article, in a ``similar`` response."""
    temporal: Optional[QueryDate]
    """How the date in the query was read: the topic was judged without it, and the results from that day go first. Null when the query names none."""
    site: Optional[str]
    """The site searched, in a live site search."""
    index: Optional[IndexInfo]
    usage: SearchUsage
    """Model tokens, calls, time and what this request was billed (``cost_usd``)."""
    budget: Optional[Budget]
    """The ``max_tokens`` cap and how much of it was used."""
    discovery: Optional[Discovery]
    """Discovery: when the index has fewer than 3 good matches, typesearch looks for sources beyond it and reads them at the original site. Null only in partial events, while it is still running."""
    incomplete: bool
    """The token cap (max_tokens) or the discovery time budget ran out: there may be more."""
    cached_at: Optional[str]
    """When the cached result was computed; ``None`` if it was computed now."""
    warnings: List[ResponseWarning]
    """Things that did not stop the request, such as a domain that is not indexed."""


class Result(_Model):
    url: str
    """The article URL."""
    title: str
    """The headline."""
    source: Optional[str]
    """The outlet that published it."""
    country: Optional[str]
    """Country of the source (ISO 3166-1 alpha-2), when known."""
    language: Optional[str]
    """Language of the source (ISO 639-1), when known: for a source in several languages, the one asked for in `languages`, or its main one."""
    published_at: Optional[str]
    """Publication date-time (ISO 8601, UTC), when known."""
    section: Optional[str]
    """The section the outlet declares, or the first segment of the URL path."""
    snippet: Optional[str]
    """The standfirst or description, as the outlet published it."""
    score: float
    """Probability that the article is about the query: from reading it if it was read, otherwise from its headline."""
    headline_relevance: float
    """Probability that the headline alone is about the query."""
    read: Optional[Reading]
    """Set when the article was opened and read: its probability and how central the topic is (0–3)."""
    highlights: List[str]
    """Short verbatim excerpts about the query (up to 25 words), from articles that were read."""
    tone: Optional[ResultTone]
    """Tone relative to the query, when ``tone=True``."""
    answers: Optional[Answers]
    """Answers to your ``questions``, when you asked some."""
    duplicates: List[Duplicate]
    """The same story from other outlets, when ``dedupe=True``."""
    date_match: Optional[Literal["exact", "adjacent", "unknown", "outside"]]
    """When the query names a date: whether the article is about that day (exact), the day before or after (adjacent), cannot tell (unknown) or another date (outside). Null otherwise."""
    referenced_date: Optional[str]
    """When the query names a date: the day the article is about (YYYY-MM-DD, in the request time zone), from its headline, its publication date or reading it."""
    found_in: Literal["index", "homepage", "section", "site_search", "discovery"]
    """Where it was found: the index; a live site (homepage, section, site_search); or discovery, a source beyond the index read at the original site for this request."""
    queries: Optional[List[str]] = None
    """With several queries: which ones this result belongs to."""


class Reading(_Model):
    probability: float
    centrality: float
    """0 not mentioned · 3 main topic."""


class ResultTone(_Model):
    label: Literal["positive", "neutral", "negative"]
    probabilities: Dict[str, float]
    basis: Literal["article", "headline"]


class Answers(_Model):
    basis: Literal["article", "headline"]
    values: Dict[str, Answer]


class BooleanAnswer(_Model):
    type: Literal["boolean"]
    probability: float


class ChoiceAnswer(_Model):
    type: Literal["choice"]
    choice: str
    probabilities: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None


class ScoreAnswer(_Model):
    type: Literal["score"]
    score: float
    probabilities: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None


class Duplicate(_Model):
    url: str
    title: str
    source: Optional[str]


class QueryGroup(_Model):
    query: str
    found: bool
    total: int
    results: List[Result]
    near_misses: List[Result]
    rejected: List[Result]
    diffusion: Optional[Diffusion]
    tone: Optional[ToneSummary]
    essential: Optional[Essential]
    temporal: Optional[QueryDate]
    """How the date in the query was read: the topic was judged without it, and the results from that day go first. Null when the query names none."""


class Diffusion(_Model):
    by_day: List[DiffusionDay]
    by_source: List[DiffusionSource]
    first: Optional[FirstPublication]
    undated: int


class DiffusionDay(_Model):
    day: str
    count: int


class DiffusionSource(_Model):
    source: str
    count: int
    first_published_at: str


class FirstPublication(_Model):
    source: Optional[str]
    url: str
    title: str
    published_at: str


class ToneSummary(_Model):
    articles: int
    overall: ToneCounts
    by_source: List[SourceTone]


class ToneCounts(_Model):
    positive: int
    neutral: int
    negative: int


class SourceTone(_Model):
    positive: int
    neutral: int
    negative: int
    source: str


class Essential(_Model):
    excerpts: List[EssentialExcerpt]


class EssentialExcerpt(_Model):
    text: str
    url: str
    source: Optional[str]
    title: str


class QueryDate(_Model):
    expression: Optional[str]
    """The date words in the query, such as «hoy»; null when the query asks for the latest without naming a date."""
    from_: Optional[str] = Field(alias="from")
    """First day of the period the query refers to (YYYY-MM-DD, in `timezone`)."""
    to: Optional[str]
    """Last day of that period; the same as `from` for a single day."""
    timezone: str
    basis: Literal["published", "event", "recency"]
    """published: what was published about that day · event: news about what is scheduled for that day (published before it) · recency: the query asks for the latest without naming a date, so the newest go first."""
    window: Optional[DateWindow]
    """The publication window the date set, when it did. Null when published_after/before (or days) in the request took precedence: then the date only sorts."""
    widened: bool
    """No result is from the requested day: they come from the days around it."""


class DateWindow(_Model):
    from_: str = Field(alias="from")
    to: str


class Reference(_Model):
    url: str
    title: str


class IndexInfo(_Model):
    sources: int
    articles: int
    updated_at: Optional[str]


class SearchUsage(_Model):
    tokens: int
    """Model tokens used by this request. 0 when it came from the cache."""
    calls: int
    cost_usd: Optional[float]
    """What this request was billed, in USD: the list price of its mode (see `pricing` in GET /v1/usage), per query. 0 when it came from the cache. Null in partial results."""
    headlines: int
    from_memory: int
    pages_direct: int
    pages_browser: int
    duration_ms: int


class Budget(_Model):
    max_tokens: int
    used: int
    exhausted: bool


class Discovery(_Model):
    status: Literal["used", "background", "skipped", "budget", "timeout"]
    """used: it searched beyond the index within the time budget · background: in ultra or fast there was nothing to check quickly; it keeps learning in the background · skipped: the index had enough, or it does not apply · budget: the discovery limit was reached · timeout: the time budget ran out (incomplete: true)."""
    sites: int
    """Sites beyond the index that contributed candidates."""
    ms: int
    """Time it added to this request, in milliseconds."""


class ResponseWarning(_Model):
    code: str
    message: str


class ContentsResponse(_Model):
    id: str
    object: Literal["contents"]
    results: List[ContentsResult]
    usage: ContentsUsage


class ContentsResult(_Model):
    url: str
    status: Literal["ok", "error"]
    """``ok``, or ``error`` with the reason in ``error``. One URL failing never fails the request."""
    error: Optional[ContentsError]
    title: Optional[str]
    description: Optional[str]
    published_at: Optional[str]
    source: Optional[str]
    excerpt: Optional[str]
    """A very short verbatim excerpt (up to 25 words), never from the first paragraph: the one about the query if there is one. Null when the article can’t be quoted (short, paid, or the publisher asked for no snippets)."""
    highlights: List[str]
    relevance: Optional[float]
    """With query: probability that the article is about it."""


class ContentsUsage(_Model):
    tokens: int
    """Model tokens used by this request. 0 when it came from the cache."""
    calls: int
    cost_usd: Optional[float]
    """What this request was billed, in USD: the list price of its mode (see `pricing` in GET /v1/usage), per query. 0 when it came from the cache. Null in partial results."""
    duration_ms: int


class Problem(_Model):
    type: str
    title: str
    status: int
    detail: str
    code: str
    request_id: str
    errors: Optional[List[FieldError]] = None


class FieldError(_Model):
    path: str
    message: str


class Job(_Model):
    id: str
    object: Literal["job"]
    status: Literal["queued", "running", "succeeded", "failed"]
    """``queued``, ``running``, ``succeeded`` (with ``result``) or ``failed`` (with ``error``)."""
    created_at: str
    finished_at: Optional[str]
    result: Optional[SearchResponse]
    """The search response, once the job succeeded."""
    error: Optional[Problem]
    """The problem details, if the job failed."""


class Sources(_Model):
    object: Literal["sources"]
    updated_at: Optional[str]
    """The oldest last ingestion across the index: its freshness is that of its most stale source."""
    total: int
    """Sources in the index."""
    articles: int
    """Articles in the whole index."""
    by_country: List[CountryCoverage]
    by_language: List[LanguageCoverage]


class CountryCoverage(_Model):
    country: Optional[str]
    """ISO 3166 alpha-2; null for international sources."""
    sources: int


class LanguageCoverage(_Model):
    language: str
    """ISO 639-1."""
    sources: int


class Source(_Model):
    object: Literal["source"]
    domain: str
    covered: bool
    """Whether the domain is in the index and available."""
    name: Optional[str] = None
    country: Optional[str] = None
    languages: Optional[List[str]] = None
    articles: Optional[int] = None
    last_refreshed_at: Optional[str] = None


class Usage(_Model):
    object: Literal["usage"]
    key: UsageKey
    limits: UsageLimits
    today: UsageToday
    """Since 00:00 UTC."""
    last_30_days: UsagePeriod
    credit: Optional[Credit]
    """The organization credit behind this key. Null for internal keys, which are not billed."""
    pricing: Pricing
    """The list prices: per 1,000 requests for each search mode, similar and live site search (each query in a multi-query request is one search of its mode), and per 1,000 pages for contents."""


class UsageKey(_Model):
    id: str
    name: str


class UsageLimits(_Model):
    tokens_per_day: int
    requests_per_minute: int
    requests_per_second: Optional[int]


class UsageToday(_Model):
    requests: int
    tokens: int
    cost_usd: float
    remaining_tokens: int


class UsagePeriod(_Model):
    requests: int
    tokens: int
    cost_usd: float


class Credit(_Model):
    balance_usd: float
    plan: Literal["payg", "plan"]
    spent_this_month_usd: float
    monthly_limit_usd: Optional[float]


class Pricing(_Model):
    """The list prices: per 1,000 requests for each search mode, similar and live site search (each query in a multi-query request is one search of its mode), and per 1,000 pages for contents."""

    currency: Literal["USD"]
    per_1000_requests: RequestPricing
    per_1000_pages: PagePricing


class RequestPricing(_Model):
    ultra: float
    fast: float
    normal: float
    deep: float
    similar: float
    similar_deep: float
    """Similar in deep mode, which reads eight articles and returns highlights."""
    site_search: float


class PagePricing(_Model):
    contents: float
    contents_with_query: float
    """With a query, the model reads each page and picks the excerpts."""


Answer = Union[BooleanAnswer, ChoiceAnswer, ScoreAnswer]


ContentsError = ResponseWarning


for _model in (SearchResponse, Result, Reading, ResultTone, Answers, BooleanAnswer, ChoiceAnswer, ScoreAnswer, Duplicate, QueryGroup, Diffusion, DiffusionDay, DiffusionSource, FirstPublication, ToneSummary, ToneCounts, SourceTone, Essential, EssentialExcerpt, QueryDate, DateWindow, Reference, IndexInfo, SearchUsage, Budget, Discovery, ResponseWarning, ContentsResponse, ContentsResult, ContentsUsage, Problem, FieldError, Job, Sources, CountryCoverage, LanguageCoverage, Source, Usage, UsageKey, UsageLimits, UsageToday, UsagePeriod, Credit, Pricing, RequestPricing, PagePricing,):
    _model.model_rebuild()
