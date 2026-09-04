# Proposed addition to full_analysis.py — enriched CSV export

Discussed 2026-09-01, not yet applied to the server copy of `full_analysis.py`.
Compare this against the live file before adding.

## Why

`opening_breakdown.py` needs `breaker_won` already computed rather than
re-deriving it independently. Re-deriving the same logic in two places risks
the two implementations silently drifting apart if one gets edited later and
the other doesn't. `full_analysis.py` already derives `book_breaker` and
`breaker_won` from `book_depth_plies` (ply parity) — this addition just
writes that enriched dataframe out to its own CSV right after those columns
are computed, so other scripts can read from one source of truth instead of
recomputing it.

## Where it goes

Insert immediately after this existing block (the breaker win-rate print),
and before the `PRIMARY ANALYSIS` section header:

```python
print("=== Did the player who broke book first win or lose? ===")
print(df["breaker_won"].value_counts(normalize=True))
print(f"Breaker win rate: {df['breaker_won'].mean():.4f}\n")
```

Placed here specifically — not at the end of the script — because later
sections add more columns (`rating_diff`, `breaker_rating_diff`, `avg_rating`,
`rating_band`) that are only needed for the secondary/exploratory analysis,
not for `opening_breakdown.py`'s purpose. Writing the enrichment step right
after the two columns it actually needs (`book_breaker`, `breaker_won`) keeps
the enriched file minimal and its purpose obvious, rather than a dump of
every column this script happens to compute.

## The exact block to add

```python
# ============================================================
# ENRICHED CSV EXPORT
# ============================================================
# Everything above this point derived two new columns that do NOT exist
# in the raw extraction files (full_under1000.csv etc.): book_breaker
# (who deviated first, from ply parity) and breaker_won (did that
# player go on to win). Other scripts - specifically
# opening_breakdown.py - need breaker_won already computed rather than
# re-deriving it themselves. Re-deriving it in a second script would
# mean two independent implementations of the same logic, which could
# silently drift apart if one gets edited later and the other doesn't.
#
# So: write out an "enriched" copy of this band's data, identical to
# the input file but with book_breaker and breaker_won columns added,
# right here, right after they're computed and BEFORE any further
# filtering or column changes happen below. This becomes the single
# source of truth for "which rows are usable and what did they break/win"
# that any other script in this project should read from, instead of
# recomputing it.
#
# Naming convention: <original_filename>_enriched.csv, written to the
# same directory as the input file. E.g. full_under1000.csv produces
# full_under1000_enriched.csv.
enriched_path = input_file.replace(".csv", "_enriched.csv")
df.to_csv(enriched_path, index=False)
print(f"Enriched dataset (with book_breaker, breaker_won columns added) "
      f"saved to {enriched_path}\n")
```

## What changes vs. what doesn't

- Pure addition. No existing lines in `full_analysis.py` are removed or
  reordered — a `diff` should show only these new lines inserted.
- No changes to the primary or secondary/exploratory analysis logic that's
  already been validated.

## Downstream effect

Once added, running `full_analysis.py` against `full_under1000.csv`,
`full_1000_1399.csv`, `full_1400_1799.csv`, and `full_1800_1999.csv` will
automatically produce `full_under1000_enriched.csv`,
`full_1000_1399_enriched.csv`, etc. as a side effect — no separate step
needed. `opening_breakdown.py` is written to expect these `_enriched.csv`
files as its input (it checks for a `breaker_won` column and raises a clear
error if that column isn't present, rather than silently guessing).

## Also produced this session, not yet applied/run

- `extract_bands_full.py` — full-population, no-sampling version of
  `extract_bands_test.py`. Already running on the server as of ~3:40 PM
  CDT tonight (tmux session `extract_full`). Outputs `full_under1000.csv`,
  `full_1000_1399.csv`, `full_1400_1799.csv`, `full_1800_1999.csv`, plus
  `extract_full_summary.txt`.
- `opening_breakdown.py` — exploratory analysis script, groups by
  `matched_name` per band, applies a minimum-game-count filter (default
  100, adjustable via `--min-games`), runs a one-sample t-test against 0.5
  per surviving opening, applies Bonferroni correction based on the actual
  number of openings tested (not the full ~3,810 known lines). Reports
  results in two tiers: statistically significant after correction, vs.
  full ranked list labeled exploratory-only. Requires an `_enriched.csv`
  input (see above) — will error clearly if `breaker_won` isn't present
  rather than guessing at the derivation.

## To do tomorrow

1. Compare this file against the live `full_analysis.py` on the server.
2. Apply the enrichment block if it still looks right.
3. Confirm tonight's `extract_bands_full.py` run finished cleanly
   (check `extract_full_summary.txt`).
4. Run `full_analysis.py` on all four `full_*.csv` files (produces the
   `_enriched.csv` files as a side effect).
5. Run `opening_breakdown.py` on each `_enriched.csv`.
