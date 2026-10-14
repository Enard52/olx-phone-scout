# Tasks

## 1. Price history

- [ ] 1.1 Add `MEDIAN_WINDOW_DAYS = 60` and `MEDIAN_MIN_SAMPLES = 5` to `src/core/constants.py`; verify `uv run pytest tests/test_config.py` passes
- [ ] 1.2 Extract storage parsing from `get_storage_score` into a helper returning GB or None; verify `uv run pytest tests/test_scoring.py tests/test_scoring_specs.py` still passes plus a test for "12/512" and "256gb"
- [ ] 1.3 Add a price-history store (SQLite at `data/cache/olx_prices.db`, upsert by link: model, storage, price, seen_at); verify with a test that a re-seen link updates one row and an unrecognized model is skipped
- [ ] 1.4 Add the median query (window, storage-then-model fallback, minimum samples) returning median and sample size; verify tests for each spec scenario under "Median used price per model"

## 2. Scoring

- [ ] 2.1 Record every analyzed listing in the history before scoring; verify a test that a fresh history yields medians for a model with 5+ listings in the same run
- [ ] 2.2 Add `MEDIAN_GAP_THRESHOLDS` (10/20/30% below median) and `get_median_gap_score` to `src/analysis/scoring.py`; verify unit tests for 25% below, at and above the median
- [ ] 2.3 Apply the factor in `calculate_value_score`, independent of the launch-price discount, and store `market_median` / `market_median_samples` on the phone; verify a test where a model without a launch-price entry still gets the factor
- [ ] 2.4 Flag listings 50%+ below the median as suspicious with no median points; verify a test for 140k against a 300k median

## 3. Report and docs

- [ ] 3.1 Show median and sample size in the TXT report and the console top 5; verify by running `./run.sh --analyze` on an existing session and reading the report
- [ ] 3.2 Update README.md and README.ru.md ("What it does", scoring) and CLAUDE.md (value scoring); add a CHANGELOG entry noting the score shift
- [ ] 3.3 Run `uv run pytest`, `uv run ruff check .`, `uv run mypy src` and `openspec validate add-olx-market-median --strict`; all pass
