"""

Full-scale analysis of book-depth vs. game outcome.

PRIMARY ANALYSIS (matches Task 1 exactly):
  Game outcome - specifically whether the player who first departs from
  known opening theory (the "book breaker") ultimately wins or loses - is
  modeled using logistic regression, with opening book depth (plies of
  known theory followed before the first deviation) as the SOLE predictor.
  Evaluated via: Pseudo R-squared, coefficient significance, a likelihood
  ratio test against the null (intercept-only) model, and a Pearson
  correlation between book depth and outcome. Rating is used only to
  stratify games into one of four bands before this script ever runs -
  it is not a term in this regression.

SECONDARY / EXPLORATORY (does book depth's effect hold up once rating
  is controlled for, or is it proxying for rating?):
  A three-model comparison (rating alone / book depth alone / both) with
  a second LRT isolating book depth's marginal contribution once rating
  is already known.

Usage:
    python3 full_analysis.py <input_file.csv>

Output is printed to the console AND saved automatically to
<input_file_stem>_analysis_log.txt in the same directory.

"""

import sys
import os
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, pearsonr


class Tee:
    """Writes everything to both the real stdout and a log file at once,
    so console output is preserved automatically without extra effort."""

    def __init__(self, filepath, stream):
        self.file = open(filepath, "w")
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.file.write(data)

    def flush(self):
        self.stream.flush()
        self.file.flush()


# --- 0. Get input filename from command line ---
if len(sys.argv) != 2:
    print("Usage: python3 full_analysis.py <sample_or_results_file.csv>")
    sys.exit(1)
input_file = sys.argv[1]

stem = os.path.splitext(os.path.basename(input_file))[0]
log_path = f"{stem}_analysis_log.txt"
_real_stdout = sys.stdout
sys.stdout = Tee(log_path, _real_stdout)

print(f"=== Analyzing {input_file} ===\n")

# --- 1. Load + clean ---
df = pd.read_csv(input_file)
print(f"Total rows loaded: {len(df):,}")
df = df[df["result"].isin(["1-0", "0-1"])].copy()
print(f"Rows after dropping draws/incomplete: {len(df):,}\n")

# --- 2. Derive who broke book first ---
# book_depth_plies = N means plies 1..N matched known theory.
# The deviating move is ply N+1. Odd plies = White, even plies = Black.
df["book_breaker"] = df["book_depth_plies"].apply(
    lambda n: "white" if n % 2 == 0 else "black"
)
df["breaker_won"] = (
    ((df["book_breaker"] == "white") & (df["result"] == "1-0")) |
    ((df["book_breaker"] == "black") & (df["result"] == "0-1"))
).astype(int)

print("=== Did the player who broke book first win or lose? ===")
print(df["breaker_won"].value_counts(normalize=True))
print(f"Breaker win rate: {df['breaker_won'].mean():.4f}\n")

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

# ============================================================
# PRIMARY ANALYSIS - matches Task 1 exactly
# ============================================================
print("=" * 60)
print("PRIMARY ANALYSIS (per Task 1 design)")
print("Predictor: book_depth_plies (sole predictor)")
print("Outcome:   breaker_won")
print("=" * 60)

# --- Pearson correlation: book depth vs outcome ---
r_stat, r_pvalue = pearsonr(df["book_depth_plies"], df["breaker_won"])
print(f"\nPearson correlation (book_depth_plies vs breaker_won):")
print(f"  r = {r_stat:.4f}, p-value = {r_pvalue:.6f}")

# --- Logistic regression: book depth as sole predictor ---
y = df["breaker_won"]
X_primary = sm.add_constant(df[["book_depth_plies"]])
m_primary = sm.Logit(y, X_primary).fit(disp=0)

print(f"\nLogistic regression (book_depth_plies -> breaker_won):")
print(f"  Pseudo R2 = {m_primary.prsquared:.4f}")
print(f"  Log-Likelihood = {m_primary.llf:.2f}")
print(f"  LL-Null        = {m_primary.llnull:.2f}")

# --- LRT: this model vs the null (intercept-only) model ---
# statsmodels computes this automatically on any fitted model - .llr and
# .llr_pvalue compare the fitted model directly against its own null.

print(f"\nLikelihood ratio test (book_depth_plies model vs. null model):")
print(f"  LR statistic = {m_primary.llr:.4f}, p-value = {m_primary.llr_pvalue:.6f}")
if m_primary.llr_pvalue < 0.05:
    print(f"  (p < 0.05 -> book_depth_plies explains outcome better than chance)")
else:
    print(f"  (p >= 0.05 -> cannot reject the null; book_depth_plies does not")
    print(f"   explain outcome better than chance in this band)")
print(f"\n=== Primary model summary ===")
print(m_primary.summary())

# ============================================================
# SECONDARY / EXPLORATORY - robustness check against rating
# ============================================================
print("\n" + "=" * 60)
print("SECONDARY / EXPLORATORY ANALYSIS")
print("Does book depth's effect hold up once rating is controlled for,")
print("or is it proxying for rating?")
print("=" * 60)

df["rating_diff"] = df["white_elo"] - df["black_elo"]
df["breaker_rating_diff"] = df.apply(
    lambda r: r["rating_diff"] if r["book_breaker"] == "white" else -r["rating_diff"],
    axis=1
)

df["avg_rating"] = (df["white_elo"] + df["black_elo"]) / 2
corr_rating_depth = df["avg_rating"].corr(df["book_depth_plies"])
print(f"\nCorrelation (avg rating vs book depth): {corr_rating_depth:.4f}")

# Fixed 100-point-wide bins, anchored to the actual data range in this file,
# so bin widths stay comparable across separate runs on different bands.
low = int(df["avg_rating"].min() // 100 * 100)
high = int(df["avg_rating"].max() // 100 * 100 + 100)
bin_edges = list(range(low, high + 1, 100))
df["rating_band"] = pd.cut(df["avg_rating"], bins=bin_edges)

print("\nAverage book depth by 100-point rating band:")
print(df.groupby("rating_band", observed=True)["book_depth_plies"].agg(["mean", "count"]))
print()

corr_predictors = df["book_depth_plies"].corr(df["breaker_rating_diff"])
print(f"Correlation between book_depth_plies and breaker_rating_diff: {corr_predictors:.4f}")
print("(Near zero = the two predictors aren't entangled with each other)\n")

X1 = sm.add_constant(df[["breaker_rating_diff"]])
m1 = sm.Logit(y, X1).fit(disp=0)
X3 = sm.add_constant(df[["breaker_rating_diff", "book_depth_plies"]])
m3 = sm.Logit(y, X3).fit(disp=0)

print("=== Three-model comparison ===")
print(f"Model 1 (rating only):      Log-Likelihood={m1.llf:.2f}  Pseudo R2={m1.prsquared:.4f}")
print(f"Model 2 (book depth only):  Log-Likelihood={m_primary.llf:.2f}  Pseudo R2={m_primary.prsquared:.4f}")
print(f"Model 3 (both):             Log-Likelihood={m3.llf:.2f}  Pseudo R2={m3.prsquared:.4f}\n")

lr_stat = 2 * (m3.llf - m1.llf)
p_value = chi2.sf(lr_stat, df=1)
print("Incremental LRT (does book_depth add anything BEYOND rating, once rating is known?):")
print(f"  LR statistic = {lr_stat:.4f}, p-value = {p_value:.6f}")
print(f"  (this is a different question from the primary analysis above -")
print(f"   it's asking about book_depth's marginal value on top of rating,")
print(f"   not book_depth's standalone relationship to outcome)\n")

print(f"\n=== DONE === (output saved to {log_path})")
_tee = sys.stdout
sys.stdout = _real_stdout  # restore real stdout before closing the log file
_tee.file.close()
