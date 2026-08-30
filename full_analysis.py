"""
Full-scale analysis of book-depth vs. game outcome, controlling for rating.
Same logic already hand-verified at n=4,149 - now run against the full
~868K game population.

Sections:
  1. Load + clean (drop draws)
  2. Derive book_breaker (who deviated from theory first, via ply parity)
  3. Mediation check: does rating correlate with book depth?
  4. Collinearity check: are the two regression predictors entangled?
  5. Three-model comparison: rating alone vs book depth alone vs both,
     with a likelihood ratio test to see if book depth adds anything
     beyond what rating already explains.
"""
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2

# --- 1. Load + clean ---
df = pd.read_csv("results_full.csv")
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

df["rating_diff"] = df["white_elo"] - df["black_elo"]
df["breaker_rating_diff"] = df.apply(
    lambda r: r["rating_diff"] if r["book_breaker"] == "white" else -r["rating_diff"],
    axis=1
)

print("=== Did the player who broke book first win or lose? ===")
print(df["breaker_won"].value_counts(normalize=True))
print(f"Breaker win rate: {df['breaker_won'].mean():.4f}\n")

# --- 3. Mediation check: rating vs book depth ---
df["avg_rating"] = (df["white_elo"] + df["black_elo"]) / 2
corr_rating_depth = df["avg_rating"].corr(df["book_depth_plies"])
print(f"Correlation (avg rating vs book depth): {corr_rating_depth:.4f}")

df["rating_band"] = pd.cut(df["avg_rating"], bins=[0, 700, 800, 900, 1000])
print("\nAverage book depth by rating band:")
print(df.groupby("rating_band", observed=True)["book_depth_plies"].agg(["mean", "count"]))
print()

# --- 4. Collinearity check between regression predictors ---
corr_predictors = df["book_depth_plies"].corr(df["breaker_rating_diff"])
print(f"Correlation between book_depth_plies and breaker_rating_diff: {corr_predictors:.4f}")
print("(Near zero = the two predictors aren't entangled with each other)\n")

# --- 5. Three-model comparison ---
y = df["breaker_won"]

X1 = sm.add_constant(df[["breaker_rating_diff"]])
m1 = sm.Logit(y, X1).fit(disp=0)

X2 = sm.add_constant(df[["book_depth_plies"]])
m2 = sm.Logit(y, X2).fit(disp=0)

X3 = sm.add_constant(df[["breaker_rating_diff", "book_depth_plies"]])
m3 = sm.Logit(y, X3).fit(disp=0)

print("=== Model comparison ===")
print(f"Model 1 (rating only):      Log-Likelihood={m1.llf:.2f}  Pseudo R2={m1.prsquared:.4f}")
print(f"Model 2 (book depth only):  Log-Likelihood={m2.llf:.2f}  Pseudo R2={m2.prsquared:.4f}")
print(f"Model 3 (both):             Log-Likelihood={m3.llf:.2f}  Pseudo R2={m3.prsquared:.4f}\n")

lr_stat = 2 * (m3.llf - m1.llf)
p_value = chi2.sf(lr_stat, df=1)
print("Likelihood ratio test (does book_depth add anything beyond rating?):")
print(f"  LR statistic = {lr_stat:.4f}, p-value = {p_value:.6f}")
print(f"  (p > 0.05 -> book_depth adds nothing once rating is known)")
print(f"  (p < 0.05 -> book_depth adds a statistically detectable, but check")
print(f"   Pseudo R2 above to judge if it's practically meaningful)\n")

print("=== Full Model 3 summary ===")
print(m3.summary())
