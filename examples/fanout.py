"""Batched search with bounded concurrency and per-query error isolation.

Two equivalent paths:
- sync: `pplx_sdk.search.web_many` (shown when run without --async)
- async: `pplx_sdk.utils.fanout` over `client.search.web` (shown with --async)

A failing query lands on its `FanoutResult.error`; the rest of the batch is
unaffected.

Usage:
    export PERPLEXITY_API_KEY=pplx-...
    python fanout.py [--async]
"""

import asyncio
import os
import sys
from collections.abc import Sequence

import pplx_sdk
from pplx_sdk import AsyncPplxClient, WebHit
from pplx_sdk.utils import FanoutResult, fanout

QUERIES = [
    "rust async runtimes",
    "python 3.13 free-threading status",
    "postgres 17 new features",
]


def run_sync() -> None:
    results = pplx_sdk.search.web_many(QUERIES, concurrency=3, limit_per_query=5)
    report(results)


async def run_async() -> None:
    async with AsyncPplxClient() as client:
        results = await fanout(
            client.search.web,
            [{"queries": q, "limit": 5} for q in QUERIES],
            concurrency=3,
        )
    report(results)


def report(results: Sequence[FanoutResult[list[WebHit]]]) -> None:
    for r in results:
        label = r.spec.get("query") or r.spec.get("queries")
        if r.ok:
            print(f"{label!r}: {len(r.result)} hits")
        else:
            print(f"{label!r}: FAILED: {r.error}")


def main() -> int:
    if not os.environ.get("PERPLEXITY_API_KEY"):
        print(
            "Set PERPLEXITY_API_KEY first (create a key at"
            " https://www.perplexity.ai/account/api).",
            file=sys.stderr,
        )
        return 1

    if "--async" in sys.argv[1:]:
        asyncio.run(run_async())
    else:
        run_sync()
    return 0


if __name__ == "__main__":
    sys.exit(main())
