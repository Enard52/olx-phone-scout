# Proposal

## Why

The value score compares the asking price with a hand-maintained launch-price table of 102 models. In the
`alma-ata_90k-380k_android` session, 113 of 209 analyzed Android listings matched no table entry and got no
price-based score at all. The pipeline already collects thousands of OLX prices per run; it can tell what a
model actually sells for used, without anyone updating a table.

## What Changes

- Every run records the price of each analyzed listing, keyed by model (and storage when the title states it),
  in a global price history shared by all sessions.
- The analyzer computes the median asking price per model over a recent window and scores each listing by how
  far below that median it is. This is a new value factor next to the existing launch-price discount, on its own
  scale: used-market gaps are 0–30%, launch-price discounts 50–80%, so the two are not merged.
- A listing far below its model's median is flagged as suspicious instead of rewarded, as the launch-price
  plausibility check already does.
- The report shows the median and the sample size next to the price.

## Capabilities

### New Capabilities
- `olx-market-median`: price history across runs, per-model median used price, and the value factor and
  warnings derived from it.

### Modified Capabilities
<!-- none: openspec/specs/ is empty; the launch-price discount keeps its current behavior -->

## Impact

- `src/analysis/analyzer.py` (scoring), `src/analysis/scoring.py` (thresholds), report output.
- New SQLite file `data/cache/olx_prices.db` (git-ignored with the rest of `data/`).
- No new dependencies (`sqlite3`, `statistics` from the stdlib).
- Scores change for every listing that gets the new factor; top-N order will shift.
