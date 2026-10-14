# Design

## Context

See proposal.md - Why. Scoring lives in `AndroidAnalyzer.calculate_value_score` (`src/analysis/analyzer.py`);
the model is recognized by `extract_model_from_title`, storage is parsed inline in `get_storage_score`
(`src/analysis/scoring.py`) and needs pulling out into a helper the price history can reuse. Kimovil already keeps a global SQLite cache in `data/cache/`, so a cross-session
store has a precedent.

## Goals / Non-Goals

**Goals:** a per-model used-price estimate that improves with every run; no manual upkeep.

**Non-Goals:** replacing the launch-price table (release year and tier still come from it); fetching prices
from other marketplaces; price trends or charts.

## Decisions

- **Global SQLite `data/cache/olx_prices.db`, one row per listing link** (upsert on link). Alternative: compute
  from the current run only. Rejected: a run is cut to its price window, so in a 150–160k run every model's
  median lands near 155k and the factor means nothing. Pooling all sessions widens the sample; dedup by link
  stops a listing seen in ten runs from counting ten times.
- **Median, not mean.** OLX has fake 1 KZT and inflated listings; the median ignores them without a separate
  outlier filter.
- **60-day window, minimum 5 samples.** Used prices drift; two months keeps enough data for common models. Both
  values go to `src/core/constants.py` (`MEDIAN_WINDOW_DAYS`, `MEDIAN_MIN_SAMPLES`) so they can be tuned.
- **Storage-aware with fallback to the model** (see spec): a 512GB variant often sells 20–30% above 128GB, but
  most variants have too few samples on their own.
- **Separate factor with its own thresholds** in `scoring.py` (`MEDIAN_GAP_THRESHOLDS`, max ~15 points) rather
  than feeding the median into the launch-price discount. The two measure different things (saving vs new,
  saving vs used market).
- **Record before scoring, within the same run.** The current run's prices count toward the medians it uses, so
  a first run on an empty history still gets medians for common models.

## Risks / Trade-offs

- [Narrow price windows still bias the pool for rare models] → the 5-sample floor; the report shows the sample
  size so the reader can judge.
- [Model recognition errors pollute the history] → only listings with a recognized model are recorded; the same
  recognition already drives the launch-price lookup.
- [Score shift changes the top-N between versions] → expected; note it in the CHANGELOG.

## Migration Plan

No migration: the database is created on first use. Rollback = delete `data/cache/olx_prices.db` and revert;
the launch-price scoring is untouched.
