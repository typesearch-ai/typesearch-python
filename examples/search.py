"""Search the news index and print each result with its calibrated score.

export TYPESEARCH_API_KEY=ts_live_…
python examples/search.py "central bank rates"
"""

import sys

from typesearch import Typesearch

query = sys.argv[1] if len(sys.argv) > 1 else "inflation"

with Typesearch() as ts:  # reads TYPESEARCH_API_KEY
    res = ts.search(
        query,
        mode="fast",  # ~1 s; "ultra" (headlines only) costs less, "normal" reads the top results before ranking them
        max_results=5,
        days=3,
        # include_domains=["diarioejemplo.example"],
    )

print(f'{res.total} relevant articles for "{query}" ({res.usage.duration_ms} ms)')
for r in res.results:
    # score is a calibrated probability: 0.9 means about nine in ten such results are relevant.
    date = r.published_at[:10] if r.published_at else "undated"
    print(f"{r.score:.2f}  {r.title}  ({r.source or 'unknown source'}, {date})")
    print(f"      {r.url}")
if not res.found:
    print("Nothing relevant. Closest:", [r.title for r in res.near_misses])
