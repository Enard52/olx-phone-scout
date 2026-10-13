**English** | **[Русский](CONTRIBUTING.ru.md)**

# Contributing

Bug reports with a misdetected title, missing market prices and parser fixes are welcome.

## Setup

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Tests need no network.

## Pull requests

- One change per PR, with a test that fails without it.
- A brand or model detection fix comes with the real listing title as a test case.
- Commit messages: `<type>: <description>`, where type is one of feat, fix, refactor, docs, test, chore, perf, ci.
- Request pacing and retries come from [market-sources](https://github.com/octrow/market-sources); a broken
  OLX transport is usually fixed there.
- Changes to `README.md` go into `README.ru.md` too, and the other way round.

Be polite to OLX and Kimovil: keep request pacing as it is and don't add bulk crawling.
