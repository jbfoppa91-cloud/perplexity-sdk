"""Content snippets: query-relevant excerpts from URLs, sync facade.

Searches the web for a query, then pulls query-relevant text out of the top
hits. Check `error` on every result: an exit without exceptions means the
request succeeded, not that every URL did.

Usage:
    export PERPLEXITY_API_KEY=pplx-...
    python content_snippets.py [query]
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

    hits = pplx_sdk.search.web(query, limit=3)
    if not hits:
        print("No search hits.", file=sys.stderr)
        return 1

    results = pplx_sdk.content.snippets(
        query=query,
        urls=[hit.url for hit in hits],
        max_tokens=2048,  # total budget across all snippets
        max_tokens_per_page=1024,
    )
    for result in results:
        print(result.url)
        if result.error:
            print(f"  ERROR: {result.error}")
        else:
            print(f"  {(result.text or '')[:300]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
