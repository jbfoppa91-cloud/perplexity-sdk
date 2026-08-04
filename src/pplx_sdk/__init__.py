"""
Perplexity SDK

Python SDK for the Perplexity Search API: web search and query-relevant
page snippets, backed by a Rust core with Python bindings via PyO3.

Sync usage (recommended for scripts / pipelines / REPL):

    >>> import pplx_sdk
    >>> hits = pplx_sdk.search.web("Rust programming", limit=5)
    >>> snippets = pplx_sdk.content.snippets("rust language", [h.url for h in hits])

``search.web`` returns ``list[WebHit]``. ``content.snippets`` returns
``list[SnippetResult]``.

Async usage (explicit concurrency control):

    >>> import asyncio
    >>> from pplx_sdk import AsyncPplxClient
    >>> async def main():
    ...     async with AsyncPplxClient() as client:
    ...         hits = await client.search.web("Rust programming", limit=10)
    ...         print(len(hits), hits[0].url)
    >>> asyncio.run(main())

Authentication: set ``PERPLEXITY_API_KEY``. The ``PPLX_SDK_BASE_URL`` +
``PPLX_SDK_API_KEY`` pair (must be set together) overrides it for custom
endpoints.
"""

from ._json import install_json_encoder as _install_json_encoder
from ._sync import _SDK_VERSION, content, search
from .pplx_sdk import (  # type: ignore[import-not-found]
    APIError,
    AsyncContentResource,
    AsyncPplxClient,
    AsyncSearchResource,
    AuthenticationError,
    BadRequestError,
    ConnectError,
    DomainTrust,
    ForbiddenError,
    InternalServerError,
    NotAcceptableError,
    NotFoundError,
    PplxSdkError,
    RateLimitError,
    SnippetResult,
    TimeoutError,
    ValidationError,
    WebHit,
)
from .utils import (
    Checkpoint,
    FanoutResult,
    dedup_by_field,
    dedup_by_url,
    fanout,
    flatten_fanout_rows,
    now_timestamp,
    output_file_name,
    partition,
    preview,
    print_preview_jsonl,
    read_jsonl,
    save_and_print,
    write_jsonl,
)

__version__ = _SDK_VERSION

_install_json_encoder()

__all__ = [
    "APIError",
    "AsyncContentResource",
    # Async client (for explicit concurrency control)
    "AsyncPplxClient",
    "AsyncSearchResource",
    "AuthenticationError",
    "BadRequestError",
    "Checkpoint",
    "ConnectError",
    "DomainTrust",
    # Fan-out primitive
    "FanoutResult",
    "ForbiddenError",
    "InternalServerError",
    "NotAcceptableError",
    "NotFoundError",
    # Exceptions
    "PplxSdkError",
    "RateLimitError",
    "SnippetResult",
    "TimeoutError",
    "ValidationError",
    # Search hits
    "WebHit",
    "content",
    "dedup_by_field",
    "dedup_by_url",
    "fanout",
    "flatten_fanout_rows",
    "now_timestamp",
    "output_file_name",
    "partition",
    "preview",
    "print_preview_jsonl",
    "read_jsonl",
    "save_and_print",
    # Sync facades
    "search",
    "write_jsonl",
]
