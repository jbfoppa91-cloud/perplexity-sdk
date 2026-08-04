# perplexity-sdk

Search-as-code access to the Perplexity Search API from Python: live web
search and query-relevant page snippets as typed results, with async fan-out
and batch helpers, backed by a compiled Rust core.

## Install

```bash
pip install perplexity-sdk
```

The import name is `pplx_sdk`. PyPI ships prebuilt wheels only (no sdist);
each wheel bundles the open Python wrapper from `src/` plus a closed,
compiled core that is not published, so this repository's tree is not
importable on its own — install the wheel.

## Authentication

Get an API key at [perplexity.ai/account/api](https://www.perplexity.ai/account/api):

```bash
export PERPLEXITY_API_KEY=pplx-...
```

For custom endpoints, the `PPLX_SDK_API_KEY` + `PPLX_SDK_BASE_URL` pair
overrides it. The pair is all-or-nothing: setting only one of the two is a
configuration error; when both are set, the pair takes precedence.

## Quick start (sync)

```python
import pplx_sdk

hits = pplx_sdk.search.web("rust async runtimes", limit=5)
for h in hits:
    print(h.title, h.url, h.snippet)
```

## Async

```python
import asyncio
from pplx_sdk import AsyncPplxClient

async def main():
    async with AsyncPplxClient() as client:
        hits = await client.search.web("rust async runtimes", limit=5)
        snippets = await client.content.snippets(
            query="rust async runtimes",
            urls=[h.url for h in hits],
        )

asyncio.run(main())
```

See [examples/](examples/) for runnable scripts (they need the installed
wheel, not this tree).

## Repository layout

- `src/pplx_sdk/` — the open wrapper source, a one-way mirror of Perplexity's
  internal monorepo overwritten wholesale on each release. PRs against it are
  welcome; maintainers port accepted changes upstream.
- `dist/metadata.json` — the released version, internal source commit, and
  per-wheel SHA-256 hashes. Its version, the PyPI version, and the git tag
  (`v{version}`) are always the same.
- `examples/` and `.github/` — owned and edited in this repository.

## License

Apache-2.0 — see [LICENSE](LICENSE); it also ships inside the wheel.
