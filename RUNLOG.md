# Run Log

## 2026-08-30 — extract_bands_test.py (10% sample, all 4 bands)
- Input: lichess_db_standard_rated_2023-06.pgn.zst (full file, ~96.6M games)
- Filters: rapid time control (base+40*increment, 480-1499s), both players
  in same rating band, Abandoned excluded, Time forfeit kept
- Sampling: Bernoulli, random.seed(42), SAMPLE_RATE=0.10
- Output: sample_under1000.csv, sample_1000_1399.csv, sample_1400_1799.csv,
  sample_1800_1999.csv
- Command: python3 extract_bands_test.py lichess_db_standard_rated_2023-06.pgn.zst
- Status: [fill in after run completes - total scanned, kept per band, runtime]
