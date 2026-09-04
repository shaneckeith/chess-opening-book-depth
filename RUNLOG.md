# Run Log

## 2026-08-30 — extract_bands_test.py (10% sample, all 4 bands)
- Input: lichess_db_standard_rated_2023-06.pgn.zst (full file, ~96.6M games)
- Filters: rapid time control (base+40*increment, 480-1499s), both players
  in same rating band, Abandoned excluded, Time forfeit kept
- Sampling: Bernoulli, random.seed(42), SAMPLE_RATE=0.10
- Output: sample_under1000.csv, sample_1000_1399.csv, sample_1400_1799.csv,
  sample_1800_1999.csv
- Command: python3 extract_bands_test.py lichess_db_standard_rated_2023-06.pgn.zst
- Status: DONE. Total scanned 96,641,906; total kept 1,041,999 (~1.08%).
  Runtime ~1h40m at ~15,700 games/sec (steady throughout).
  Kept per band: under1000 86,150 | 1000_1399 321,723 |
  1400_1799 484,609 | 1800_1999 149,517
  (sums to 1,041,999, matches reported total exactly)

## 2026-08-31 — full_analysis.py (10% sample, all 4 bands)
- Input: sample_under1000.csv, sample_1000_1399.csv, sample_1400_1799.csv,
  sample_1800_1999.csv
- Analysis: primary Task 1-approved model (breaker_won ~ book_depth_plies,
  sole predictor), LRT vs. null model, Pearson correlation
  (book_depth_plies vs. breaker_won), secondary exploratory rating-band
  comparison kept separate from primary results
- Fixed: rating-bin boundary bug (operator precedence) in bin computation
- Command: python3 full_analysis.py sample_under1000.csv (repeated per file)
- Status: DONE. Book-breaker win rate 47.5%-48.7% across all four bands.
  Depth coefficient negative and significant in 3 of 4 bands (direction
  unstable, see full-population entry below)

## 2026-08-31 — full_analysis.py (under1000, full population, OLD single-band
extraction)
- Input: results_under1000.csv, ~813,054 win/loss games (draws dropped),
  from the ORIGINAL pre-multiband single-band extraction script, not
  extract_bands_test.py/extract_bands_full.py
- Analysis: same primary model as above, run against full population
  instead of 10% sample
- Status: DONE. Breaker win rate 47.5%, consistent with 10% sample.
  Depth coefficient flipped positive (contradicts 10% sample direction
  for this band). Investigated 2026-09-01: descriptive stats (win rate,
  book depth by rating band, collinearity) matched closely between old
  full-population file and new 10% sample file, consistent with the two
  extraction pipelines being methodologically equivalent. Sign flip
  attributed to sampling variance on a near-zero true effect (Pseudo R2
  ~0.0000 either way, 4x larger standard error in the 10% sample), not
  a pipeline discrepancy. Superseded by tonight's extract_bands_full.py
  run, which will produce a true full-population under1000 file through
  the SAME pipeline as the other three bands, resolving this ambiguity
  directly rather than by inference.

## 2026-08-31 — classical vs. rapid time control count
- Input: lichess_db_standard_rated_2023-06.pgn.zst (full file, ~96.6M games)
- Purpose: validate rapid time control choice as data-driven rather than
  assumed
- Status: DONE. Classical: 625,261 games (0.65%). Rapid: 13,961,888 games.
  Confirms classical sample size too small to be a viable alternative.

## 2026-09-01 — Research question refinement (conceptual, no code run)
- Reframed the Task 1 research question for precision: "departing from
  known theory" -> "breaking from known theory FIRST", since both
  players always eventually leave the shared book line, only one of
  them does so first, and that first departure is the meaningful event
  being measured.
- Decomposed into one research question with three nested parts, all
  answered by the same per-band logistic regression already in use
  (breaker_won ~ book_depth_plies), not three separate analyses:

  Research question: Does breaking from known opening theory first
  affect a player's probability of winning, and does that effect -
  and the degree to which book depth modifies it - vary across player
  rating bands?

  Q1 (baseline effect, per band): Is first-breaker win rate != 50%?
    H1: first-breaker win rate != 50%
    H0: first-breaker win rate = 50%
    (captured by the regression intercept term)

  Q2 (depth effect, per band): Does book_depth_plies predict
  breaker_won?
    H1: book_depth_plies is associated with breaker_won
    H0: book_depth_plies has no association with breaker_won
    (captured by the book_depth_plies coefficient)

  Q3 (cross-band comparison): Does either effect strengthen, weaken,
  or stay flat as rating increases across the four bands?
    No separate H1/H0 - answered by comparing Pseudo R2, coefficients,
    and win rates across all four bands side by side (the four planned
    visualizations).

- Framing note for Task 2 write-up: present as ONE research question,
  decomposed into three parts from a single model - not three
  independent hypotheses. Q1 and Q2 fall directly out of the existing
  per-band regression already run; Q3 is the reason the four-band
  stratification exists in the first place. No new analysis required
  beyond what was already planned.
- Either outcome for Q1 (50/50 or significantly below) is a legitimate,
  interesting finding - not treating a null result as a failed
  experiment.

## 2026-09-01 — Note: replication practicality (limitation to document in Task 3)
- extract_bands_full.py (full population, all four bands, no sampling)
  is running far slower than the 8/30 10% sample run: ~2,250-2,350
  games/sec steady state vs. ~15,700 games/sec on 8/30, because
  removing the sampling gate means ALL band-eligible games now hit
  the expensive chess.pgn parse + book-depth scoring path, not just
  1 in 10 of them. Projected total runtime ~11-12 hours vs. the
  original ~1h40m estimate (estimate was wrong - reasoned about the
  sampling check being cheap, not about what it was gating).
- Confirmed via `top` this is NOT AWS CPU credit throttling or a
  hardware issue (%st steal time negligible at 1.7%, instance type
  confirmed t3a.large via AWS dashboard). Genuinely just ~10x more
  expensive-path work than the validated 8/30 run.
- Ruled out code error as the cause: `diff extract_bands_test.py
  extract_bands_full.py` confirmed only the intended changes (sampling
  gate removed, output filenames changed, summary persistence added,
  docstrings updated) - core filtering/band/book-depth logic untouched
  and byte-identical between the two scripts.
- Verified correctness of partial output mid-run: row counts climbing
  as expected, header/band assignment correct, book_depth_plies values
  plausible, matched_eco/matched_name agreeing with Lichess's own
  header_eco/header_opening tags on every spot-checked row.
- Practical implication worth naming as a documented limitation in
  Task 3 (C1 or D): a full-population extraction across ~96.6M games,
  on a 2-vCPU cloud instance, single-threaded, takes ~11-12 hours.
  Independent replication of this exact run is not impossible (code
  is public in the GitHub repo, dataset is CC0-licensed and public),
  but it is impractical for a casual reviewer to actually re-run and
  verify firsthand. The realistic standard for this project is
  auditability (documented process, verifiable code, spot-checked
  output) rather than cheap reproducibility.
- Multiprocessing across both vCPUs was discussed as a future fix
  (could roughly halve runtime) but deliberately NOT implemented
  mid-run, to avoid introducing untested changes to already-validated
  scoring logic under time pressure. Worth considering for any future
  full-population re-run, not this one.

## 2026-09-02 — extract_bands_full.py (full population, all 4 bands)
- Input: lichess_db_standard_rated_2023-06.pgn.zst (full file, ~96.6M games)
- Same filters as extract_bands_test.py; sampling gate fully removed
  (not set to 1.0, stripped entirely)
- Output: full_under1000.csv, full_1000_1399.csv, full_1400_1799.csv,
  full_1800_1999.csv, plus extract_full_summary.txt
- Verified via diff against extract_bands_test.py before running: only
  intended changes present (sampling gate removed, filenames changed,
  summary persistence added), core logic byte-identical
- Command: python3 extract_bands_full.py lichess_db_standard_rated_2023-06.pgn.zst
  (launched ~3:40 PM CDT inside tmux session `extract_full`)
- Status: DONE, ran overnight ~11-12 hours as projected in the 9/1
  runtime note. Total kept across all 4 bands: under1000 861,219 |
  1000_1399 3,206,728 | 1400_1799 4,841,040 | 1800_1999 1,492,492
  (~10.4M total). Supersedes the OLD single-band under1000 extraction
  noted in the 8/31 entry above; all four bands now come from the
  same pipeline, eliminating that ambiguity directly.

## 2026-09-02/03 — full_analysis.py (full population, all 4 bands)
- Input: full_under1000.csv, full_1000_1399.csv, full_1400_1799.csv,
  full_1800_1999.csv
- Same primary model as the 10% sample run (breaker_won ~
  book_depth_plies). Enriched output also saved as full_*_enriched.csv
  (book_breaker, breaker_won columns added) for reuse in Q3.
- Command: python3 full_analysis.py full_under1000.csv (repeated per file)
- Status: DONE.
  - under1000: n=808,801, breaker win rate 47.77%, depth coefficient
    -0.0020, NOT significant (p=0.121). Resolves the sign-flip noted
    8/31 — the true full-population result via the correct multi-band
    pipeline is a genuine null in this band, not a sampling artifact.
  - 1000_1399: n=3,063,662, breaker win rate 48.22%, depth coefficient
    -0.0124, significant (p<0.001)
  - 1400_1799: n=4,630,322, breaker win rate 48.65%, depth coefficient
    -0.0105, significant (p<0.001)
  - 1800_1999: n=1,412,684, breaker win rate 48.77%, depth coefficient
    -0.0068, significant (p<0.001)
  - Breaker win rate rises monotonically toward 50% with rating band.
    Depth coefficient magnitude is NOT monotonic: near-zero at
    under1000, peaks at 1000_1399, then weakens through 1400_1799 and
    1800_1999.

## 2026-09-03 — q3_band_comparison.py (Q3: cross-band comparison, full population, pooled)
- Input: full_under1000_enriched.csv, full_1000_1399_enriched.csv,
  full_1400_1799_enriched.csv, full_1800_1999_enriched.csv, pooled
  into one table (n=9,915,469) with a band column
- Analysis: two separate tests.
  1. LRT comparing breaker_won ~ book_depth_plies + C(band) (one
     shared depth slope) vs. breaker_won ~ book_depth_plies * C(band)
     (per-band depth slopes)
  2. Chi-square test of independence, band vs. breaker_won (raw win
     rate comparison, ignoring depth)
- Command: python3 q3_band_comparison.py | tee q3_band_analysist_log.txt
- Status: DONE.
  - LRT: LR statistic 78.37, df=3, p<0.001 — the depth effect DOES
    significantly vary across bands. Per-band slopes recovered from
    the interaction model match the four separate band models exactly
    (under1000 -0.0020, 1000_1399 -0.0124, 1400_1799 -0.0104,
    1800_1999 -0.0068).
  - Chi-square: statistic 350.64, df=3, p<0.001 — breaker win rate
    DOES significantly differ across bands.
  - Formally answers Q3: both the win-rate disadvantage (Q1) and the
    depth-penalty magnitude (Q2a) vary significantly by rating band,
    with formal statistical support rather than just a visible trend.
