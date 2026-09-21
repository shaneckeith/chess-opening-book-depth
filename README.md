# Chess Opening Book Depth: Does Breaking Theory First Cost You the Game?

A WGU Data Analytics capstone analyzing whether the player who first departs
from known opening theory (the "Book Breaker") wins less often than their
opponent, and whether the depth of that departure predicts the outcome
differently across skill levels.

**Full writeup, methodology, and findings:** see the capstone report (link to
be added once published).

## Research question

Does breaking from known opening theory first affect a player's probability
of winning, and does that effect — and the degree to which book depth
modifies it — vary across player rating bands?

## Data

- **Source:** [Lichess Open Database](https://database.lichess.org/), June
  2023 standard-rated game export (~96.6M games), CC0 license
- **Opening reference:** [Lichess chess-openings](https://github.com/lichess-org/chess-openings)
  repository (~3,810 known ECO lines)
- **Scope:** Rapid time control, filtered to four player rating bands:
  under 1000, 1000–1399, 1400–1799, 1800–1999
- **Analyzed population:** ~9.9 million games across all four bands (full
  population, not sampled)

Raw source data (`.pgn.zst`) and the large extracted/intermediate CSVs are
not committed to this repo due to size — see [Reproducing](#reproducing-the-analysis)
below.

## Method

A logistic regression (`breaker_won ~ book_depth_plies`) was fit separately
for each rating band, supplemented by a likelihood ratio test and a
chi-square test to formally compare effects across bands. Full details,
including two structural limitations discovered during assumption
verification (a color confound and a linearity violation in the depth
predictor), are documented in the capstone report and in `RUNLOG.md`.

## Repository structure

### Pipeline (run in this order)

| Script | Purpose |
|---|---|
| `build_lookup.py` | Builds `eco_lookup.pkl` from the five ECO reference TSVs (`a.tsv`–`e.tsv`) |
| `extract_bands_test.py` | Extracts a 10% sample, filtered by rating band and time control |
| `extract_bands_full.py` | Extracts the full population (no sampling); ~11–12 hr single-threaded runtime |
| `full_analysis.py` | Fits the primary logistic regression model per band |
| `q3_band_comparison.py` | Likelihood ratio and chi-square tests comparing effects across bands |

### Assumption verification & follow-up analysis

| Script | Purpose |
|---|---|
| `spot_check_samples.py` | Validates extraction output against a manually verified sample of games |
| `logit_linearity_check.py` | Box-Tidwell test for the model's linearity-in-the-logit assumption |
| `breaker_color_check.py` | Checks whether book depth parity structurally overlaps with Book Breaker color |
| `breaker_color_effect.py` | Quantifies the color effect (`breaker_won ~ breaker_is_black`) |
| `baseline_color_gap.py` | Measures the baseline White-vs-Black win rate gap, independent of book-breaking |
| `logit_linearity_check_by_color.py` | Rechecks linearity within each color, to isolate it from the color confound |
| `verify_band_coefficients.py` | Verifies the confidence intervals plotted in `band_comparison.png` |

### Visualization

| Script | Output |
|---|---|
| `visuals/plot_band_comparison.py` | `visuals/band_comparison.png` — win rate and depth coefficient by band |
| `depth_milestone_breakdown.py` | `visuals/depth_milestone_breakdown.png` — win rate by depth milestone |

### Other files

- `book_depth.py` — an early, standalone prototype of the book-depth-scoring
  logic, superseded by the extraction pipeline above; kept for provenance
- `book_depth_distribution.png` — exploratory chart (10% sample) of book
  depth distribution by band; not one of the two headline visualizations
- `eco_lookup.pkl` — generated cache built by `build_lookup.py`; not
  source data, not meant to be hand-edited
- `full_analysis_enrichment.md` — notes on the enriched CSV outputs
  (`book_breaker`, `breaker_won` columns added for reuse in later analysis)
- `*_log.txt` — captured terminal output for each script run
- `RUNLOG.md` — full run history with dates, parameters, and outcomes;
  the authoritative record of what was run, when, and what it found

## Reproducing the analysis

```bash
# 1. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Download the source data
wget https://database.lichess.org/standard/lichess_db_standard_rated_2023-06.pgn.zst

# 3. Build the ECO opening reference lookup
python3 build_lookup.py

# 4. Extract and filter games (full population; ~11-12 hrs single-threaded)
python3 extract_bands_full.py lichess_db_standard_rated_2023-06.pgn.zst

# 5. Fit the primary model per band
python3 full_analysis.py full_under1000.csv
python3 full_analysis.py full_1000_1399.csv
python3 full_analysis.py full_1400_1799.csv
python3 full_analysis.py full_1800_1999.csv

# 6. Cross-band comparison
python3 q3_band_comparison.py
```

A 10% sample can be substituted for steps 4–6 via `extract_bands_test.py`
for a faster end-to-end run (~1h40m vs. ~11-12 hrs), at the cost of
statistical power — see `RUNLOG.md` for why the full population was used
for the final reported results.

## Findings

Full results, statistical significance, practical significance, and named
limitations are reported in the capstone document. In brief: the Book
Breaker's win rate was below 50% in all four bands (statistically
significant), and book depth was a significant predictor of outcome in
three of four bands, with a non-monotonic effect size across bands. Two
structural limitations were identified and documented during assumption
verification rather than corrected within the capstone's scope: a
color confound (book depth's parity is mathematically tied to Book Breaker
color) and a linearity violation in the depth predictor in three of four
bands.

## License

Data used under Lichess's CC0 license. Code is released under the MIT License; see LICENSE for details.
