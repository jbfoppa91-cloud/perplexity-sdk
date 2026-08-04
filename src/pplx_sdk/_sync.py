"""Sync facade for ``pplx_sdk.search`` / ``pplx_sdk.content``.

Forwards calls to a lazily-built async client on a daemon-thread event loop.
Methods are mirrored from the async resource classes so ``dir()``, ``help()``,
and ``inspect.signature`` all work.
"""

from __future__ import annotations

import asyncio
import atexit
import importlib.metadata
import inspect
import sys
import threading
import warnings
from collections.abc import Callable, Mapping
from typing import Any

from .pplx_sdk import (  # type: ignore[import-not-found]
    AsyncContentResource,
    AsyncPplxClient,
    AsyncSearchResource,
)
from .utils import FanoutResult, fanout

# Resolved here (not __init__.py) so the client construction below can use it
# without a circular import; __init__.py re-exports it as __version__.
try:
    _SDK_VERSION = importlib.metadata.version("perplexity-sdk")
except importlib.metadata.PackageNotFoundError:
    # Source checkouts / Bazel tests without installed dist metadata.
    _SDK_VERSION = "0.0.0+local"

_USER_AGENT = f"perplexity-sdk-python/{_SDK_VERSION}"

_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is not None:
        return _loop
    with _loop_lock:
        if _loop is None:
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=loop.run_forever,
                name="pplx-sdk-loop",
                daemon=True,
            )
            thread.start()
            _loop = loop
    return _loop


def _run(coro: Any) -> Any:  # noqa: ANN401
    fut = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    return fut.result()


_pplx_client: AsyncPplxClient | None = None
_pplx_client_lock = threading.Lock()


def _get_pplx_client() -> AsyncPplxClient:
    global _pplx_client
    if _pplx_client is not None:
        return _pplx_client
    with _pplx_client_lock:
        if _pplx_client is None:
            _pplx_client = AsyncPplxClient(user_agent=_USER_AGENT)
    return _pplx_client


def _make_sync_wrapper(
    name: str,
    async_method: Any,  # noqa: ANN401
    get_resource: Callable[[], Any],
) -> Callable[..., Any]:
    def call(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        # pyo3_async_runtimes binds the awaitable to the calling thread's loop, so build it on the loop thread.
        async def invoke() -> Any:  # noqa: ANN401
            return await getattr(get_resource(), name)(*args, **kwargs)

        return _run(invoke())

    call.__name__ = name
    call.__qualname__ = name
    call.__doc__ = async_method.__doc__
    try:
        sig = inspect.signature(async_method)
        params = list(sig.parameters.values())
        if params and params[0].name == "self":
            sig = sig.replace(parameters=params[1:])
        call.__signature__ = sig  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        pass
    return call


def _require_list(value: Any, *, method_name: str, parameter: str) -> None:  # noqa: ANN401
    if not isinstance(value, list):
        raise TypeError(
            f"{method_name}: {parameter} must be a list, got {type(value).__name__}"
        )


class _SyncFacade:
    """Sync wrapper that mirrors an async resource class's public methods."""

    def __init__(self, async_cls: type, get_resource: Callable[[], Any]) -> None:
        self._async_cls = async_cls
        for attr_name in dir(async_cls):
            if attr_name.startswith("_"):
                continue
            attr = getattr(async_cls, attr_name)
            if not callable(attr):
                continue
            setattr(self, attr_name, _make_sync_wrapper(attr_name, attr, get_resource))

    def __dir__(self) -> list[str]:
        names = set(super().__dir__())
        names.update(n for n in dir(self._async_cls) if not n.startswith("_"))
        return sorted(names)


def _make_search_many(method_name: str) -> Callable[..., Any]:
    def call(
        queries: list[str | Mapping[str, Any]],
        *,
        concurrency: int = 5,
        limit_per_query: int | None = None,
        **shared: Any,  # noqa: ANN401
    ) -> list[FanoutResult[Any]]:
        _require_list(
            queries,
            method_name=f"{method_name}_many",
            parameter="queries",
        )
        if limit_per_query is not None:
            if "limit" in shared and shared["limit"] != limit_per_query:
                warnings.warn(
                    f"{method_name}_many: both `limit_per_query={limit_per_query}` "
                    f"and `limit={shared['limit']}` were passed; `limit_per_query` wins.",
                    UserWarning,
                    stacklevel=2,
                )
            shared["limit"] = limit_per_query

        specs: list[Mapping[str, Any]] = []
        for q in queries:
            spec: dict[str, Any] = {"query": q} if isinstance(q, str) else dict(q)
            for k, v in shared.items():
                spec.setdefault(k, v)
            specs.append(spec)

        async def invoke() -> list[FanoutResult[Any]]:
            method = getattr(_get_pplx_client().search, method_name)
            return await fanout(method, specs, concurrency=concurrency)

        return _run(invoke())

    call.__name__ = f"{method_name}_many"
    call.__qualname__ = f"{method_name}_many"
    call.__doc__ = (
        f"Run `search.{method_name}` over a list of queries with bounded concurrency.\n\n"
        f"Thin wrapper over `pplx_sdk.utils.fanout`. Reach for `fanout` directly\n"
        f"when you need the same pattern against `content.snippets` or your own\n"
        f"async function.\n\n"
        f"Args:\n"
        f"    queries: A list of query strings (each becomes `{{'query': s}}`) or\n"
        f"        kwargs dicts forwarded directly to `search.{method_name}`.\n"
        f"    concurrency: Maximum simultaneous in-flight calls (default 5).\n"
        f"    limit_per_query: Hits returned for each query (forwards as `limit=`\n"
        f"        to the single-shot `search.{method_name}` call). The renamed\n"
        f"        kwarg is preferred at the `_many` site because `limit=` reads\n"
        f"        ambiguously here — it is per-query, never a batch-wide cap.\n"
        f"    **shared: Other defaults applied to every spec — per-spec values\n"
        f"        win. Accepts every kwarg the single-shot `search.{method_name}`\n"
        f"        accepts, including a raw `limit=` (equivalent to\n"
        f"        `limit_per_query=` but less explicit).\n\n"
        f"Returns:\n"
        f"    `list[FanoutResult]` in input order. Per-call errors land on each\n"
        f"    `FanoutResult.error` so one bad query doesn't fail the batch.\n\n"
        f"Note: spec dicts are shallow-copied; mutable values like `domains=[...]`\n"
        f"are stored by reference. Don't mutate spec values after dispatch.\n\n"
        f"Example:\n"
        f"    hits = pplx_sdk.search.{method_name}_many(\n"
        f"        ['query one', 'query two', 'query three'],\n"
        f"        concurrency=5,\n"
        f"        limit_per_query=10,   # each query returns up to 10 hits\n"
        f"    )\n"
        f"    for r in hits:\n"
        f"        if r.ok:\n"
        f"            print(r.spec['query'], '->', len(r.result))\n"
        f"        else:\n"
        f"            print(r.spec['query'], 'failed:', r.error)"
    )
    return call


search = _SyncFacade(AsyncSearchResource, lambda: _get_pplx_client().search)
content = _SyncFacade(AsyncContentResource, lambda: _get_pplx_client().content)

for _name in ("web",):
    setattr(search, f"{_name}_many", _make_search_many(_name))

sys.modules["pplx_sdk.search"] = search  # type: ignore[assignment]
sys.modules["pplx_sdk.content"] = content  # type: ignore[assignment]


def _shutdown() -> None:
    loop = _loop
    if loop is None:
        return
    try:
        loop.call_soon_threadsafe(loop.stop)
    except Exception:
        pass


atexit.register(_shutdown)
