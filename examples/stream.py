"""Stream a deep search: print each step as it happens and the results as they are confirmed.

    python examples/stream.py "election polls"

The same with ``AsyncTypesearch``: ``async for event in ts.search_stream(...)``.
"""

import sys

from typesearch import Typesearch

query = sys.argv[1] if len(sys.argv) > 1 else "election polls"

with Typesearch() as ts, ts.search_stream(query, mode="deep", max_results=5) as stream:
    for event in stream:
        if event.type == "step" and event.step.status == "running":
            print(f"· {event.step.text}")
        elif event.type == "partial":
            print(f"  {len(event.response.results)} results so far")
        elif event.type == "result":
            print(f"\n{event.response.total} relevant articles:")
            for r in event.response.results:
                print(f"{r.score:.2f}  {r.title}  {r.url}")
