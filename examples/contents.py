"""Search, then get metadata and a short verbatim excerpt about the query for the top results.

``contents()`` never returns the full text: at most one excerpt of up to 25 words per article.

    python examples/contents.py "energy prices"
"""

import sys

from typesearch import Typesearch

query = sys.argv[1] if len(sys.argv) > 1 else "energy prices"

with Typesearch() as ts:
    found = ts.search(query, mode="fast", max_results=3)
    if not found.results:
        sys.exit(f'Nothing found for "{query}"')
    # With a query, the excerpt is the one about it, and each page gets a relevance score.
    pages = ts.contents([r.url for r in found.results], query=query)

for page in pages.results:
    if page.status == "error":
        print(f"✗ {page.url}: {page.error.code if page.error else 'error'}")
        continue
    relevance = f"{page.relevance:.2f}" if page.relevance is not None else "–"
    print(f"{relevance}  {page.title} ({page.source})")
    print(f"      {page.description or ''}")
    for h in page.highlights:
        print(f"      “{h}”")
