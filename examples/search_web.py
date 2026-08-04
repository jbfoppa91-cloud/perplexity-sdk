"""Web search: ranked hits for a query, sync facade.

Usage:
    export PERPLEXITY_API_KEY=pplx-...
    python search_web.py [query]
"""

import os
import sys

import pplx_sdk


def main() -> int:
    if not os.environ.get("PERPLEXITY_API_KEY"):
        print(
            "Set PERPLEXITY_API_KEY first (create a key at"
            " https://www.perplexity.ai/account/api).",
            file=sys.stderr,
        )
        return 1

    query = sys.argv[1] if len(sys.argv) > 1 else "rust async runtimes"

    # `intent` is optional; one sentence stating the search objective helps
    # ranking. Domain filters and date bounds are also available — see
    # help(pplx_sdk.search.web).
    hits = pplx_sdk.search.web(
        query,
        limit=5,
        intent=f"Find authoritative, current pages about: {query}",
    )
    for hit in hits:
        print(hit.title)
        print(f"  {hit.url}")
        print(f"  {(hit.snippet or '')[:200]}")
        print()
    print(f"{len(hits)} hits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
