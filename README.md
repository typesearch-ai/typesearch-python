# typesearch

The official Python client for the [typesearch API](https://typesearch.ai/docs): news search for AI
agents, with a calibrated relevance score on every result.

```bash
pip install typesearch
```

Python 3.9+. Sync and async. Built on `httpx` and `pydantic`: every response is a typed model, and unknown
fields from a newer API are kept instead of breaking your code.

## Quickstart

Create a key in the [dashboard](https://app.typesearch.ai) and set it as `TYPESEARCH_API_KEY`:

```python
from typesearch import Typesearch

ts = Typesearch()  # reads TYPESEARCH_API_KEY

res = ts.search("inflation", mode="fast", max_results=5)

for r in res.results:
    print(f"{r.score:.2f}", r.title, f"({r.source})")
```

Every result carries a `score`: the calibrated probability that it is about your query. Threshold on it
directly — `0.9` means relevant, and anything between `0.35` and `0.65` means the model is undecided.

## Create a client

| Argument | Default | |
| --- | --- | --- |
| `api_key` | `TYPESEARCH_API_KEY` | Your key. |
| `base_url` | `https://api.typesearch.ai` | Or `TYPESEARCH_BASE_URL`. |
| `timeout` | `70.0` | Seconds before a request is aborted. A `deep` search can take about a minute. |
| `max_retries` | `2` | Retries on connection errors, `429 rate_limited` and `5xx`. |
| `default_headers` | — | Headers sent with every request. |
| `http_client` | — | Your own `httpx.Client` (or `httpx.AsyncClient` for async), for proxies or tests. |

Use it as a context manager to close connections when you are done: `with Typesearch() as ts: …`. Keep
keys on the server: never ship one to a browser or a mobile app.

## What you can do

| Method | Endpoint | |
| --- | --- | --- |
| `search(query, **options)` | `POST /v1/search` | Search the index: one query, or up to five judged together. |
| `search_stream(query, **options)` | `POST /v1/search` | The same, as events: steps, partial results, the final result. |
| `similar(url, **options)` | `POST /v1/similar` | Articles about the same story as a URL. |
| `contents(urls, query=…)` | `POST /v1/contents` | Metadata and a short verbatim excerpt of up to 10 URLs. |
| `site_search(site, query, **options)` | `POST /v1/search/site` | Search a live site. Returns a job. |
| `site_search_and_wait(site, query, **options)` | `POST /v1/search/site` | The same, waiting for the result. |
| `site_search_stream(site, query, **options)` | `POST /v1/search/site` | The same, as events. |
| `jobs.get(id)` · `jobs.wait(id)` | `GET /v1/jobs/{id}` | A job's status and result. |
| `sources()` · `sources(domain=…)` | `GET /v1/sources` | Coverage by country and language, or whether one domain is covered. |
| `usage()` | `GET /v1/usage` | Usage, limits and credit of your key. |

Keyword arguments have the same names as the [HTTP API](https://typesearch.ai/docs/api-reference) and are
typed (`SearchOptions`, `SimilarOptions`… in `typesearch.types`), so your editor and type checker know
every one of them. Responses are pydantic models generated from the API's OpenAPI document: `r.title`,
`res.usage.cost_usd`, `res.model_dump()`.

### Search

```python
res = ts.search(
    "el dólar",
    mode="normal",  # "ultra" | "fast" | "normal" | "deep"
    max_results=10,
    include_domains=["reddiaria.example", "diarioejemplo.example"],
    published_after="2026-09-20",  # or a datetime.date / an aware datetime.datetime
    highlights=True,
)

# Several queries at once, judged together
res = ts.search(["el dólar", "el FMI"], mode="fast")
for group in res.groups or []:
    print(group.query, group.total)
```

`days=None` searches the whole index; leaving `days` out keeps the default of 7. Add `questions` for typed
answers on every result, and `tone`, `dedupe` or `essential` for enrichments — see the
[guides](https://typesearch.ai/docs/guides/structured-output).

### Stream

```python
with ts.search_stream("el dólar", mode="deep") as stream:
    for event in stream:
        if event.type == "step":
            print("·", event.step.text)
        elif event.type in ("partial", "result"):
            render(event.response.results)

# Or only the final result
final = ts.search_stream("el dólar").final_response()
```

The request starts when you start iterating. An `error` event is raised as an [`APIError`](#errors).

### Similar and contents

```python
similar = ts.similar("https://diarioejemplo.example/economia/…", exclude_domains=["diarioejemplo.example"])

pages = ts.contents(["https://reddiaria.example/economia/…"], query="el dólar")
for page in pages.results:
    if page.status == "ok":
        print(page.relevance, page.title, page.highlights)
    else:
        print(page.url, page.error.code)
```

`contents()` never returns the full text: at most one excerpt of up to 25 words per article.

### Live site search

```python
# Create the job and wait for it
res = ts.site_search_and_wait("diarioejemplo.example", "el dólar", mode="normal")

# Or handle the job yourself
job = ts.site_search("diarioejemplo.example", "el dólar")
done = ts.jobs.wait(job.id, poll_interval=2, timeout=120)
```

`jobs.wait()` returns the job's result and raises `JobFailedError` if the job fails.

### Coverage and usage

```python
coverage = ts.sources()  # sources and articles, by country and language

site = ts.sources(domain="diarioejemplo.example")
if site.covered:
    print(site.name, site.articles)

usage = ts.usage()
print(usage.today.remaining_tokens, usage.limits.requests_per_minute)
```

## Async

`AsyncTypesearch` has the same methods, awaitable:

```python
import asyncio
from typesearch import AsyncTypesearch


async def main():
    async with AsyncTypesearch() as ts:
        res = await ts.search("el dólar", mode="fast")
        async for event in ts.search_stream("el FMI"):
            ...


asyncio.run(main())
```

## Errors

Every error subclasses `TypesearchError`. API errors are `APIError` subclasses with `status`, `code`
(stable, for programs), `request_id` and, for invalid requests, `errors` per field.

| Class | When |
| --- | --- |
| `BadRequestError` | 400 |
| `AuthenticationError` | 401 |
| `BudgetError` | 402 — `budget_too_small`, `insufficient_credits` or `spend_limit_reached` |
| `PermissionDeniedError` | 403 |
| `NotFoundError` | 404 |
| `RateLimitError` | 429 — with `retry_after` |
| `InternalServerError` | 5xx |
| `APIConnectionError` · `APITimeoutError` | No response, or too slow |
| `JobFailedError` | A live site search job failed |

```python
from typesearch import APIError, BadRequestError, RateLimitError

try:
    ts.search("x")
except BadRequestError as e:
    print(e.code, e.errors)
except RateLimitError as e:
    print(e.code, e.retry_after)
except APIError as e:
    print(e.status, e.code, e.request_id)
```

## Retries and timeouts

Connection errors, timeouts, `429 rate_limited` and `5xx` are retried twice with exponential backoff and
jitter, honouring `Retry-After`; `quota_exceeded` never is. Set `max_retries=0` on the client to handle
them yourself, or override it per call, with the timeout and extra headers:

```python
res = ts.search("el dólar", mode="deep", timeout=90, max_retries=0, extra_headers={"X-Trace-Id": "abc"})
```

## Examples

[`examples/`](examples) has three short scripts: [search](examples/search.py),
[contents](examples/contents.py) and [streaming](examples/stream.py).

## Development

```bash
uv sync
uv run python scripts/generate_models.py          # models from openapi/openapi.json (--fetch pulls the live one)
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pytest --cov                                # against a fake API that validates every request against the OpenAPI
TYPESEARCH_LIVE=1 uv run pytest tests/test_live.py # against the real API: needs TYPESEARCH_API_KEY (spends less than a cent)
```

## License

[MIT](LICENSE)
