"""
Q3 Analysis: Does the book-breaker win-rate effect (Q1) and the book-depth
effect (Q2a) formally vary across the four rating bands?

This script answers Q3 with two SEPARATE statistical tests:

  1. Likelihood Ratio Test (LRT)
     Question: does the relationship between book_depth_plies and breaker_won
     differ depending on which rating band a game is in?
     How: fit two logistic regression models on the pooled data. Model A
     assumes one single depth slope works for every band. Model B lets each
     band have its own depth slope. If Model B fits meaningfully better than
     Model A, that's evidence the depth effect genuinely varies by band.

  2. Chi-square test of independence
     Question: does the raw breaker win rate (ignoring depth entirely) differ
     across the four bands?
     How: a straightforward contingency table test between band and
     breaker_won.

Input:  the four full_*_enriched.csv files already produced by full_analysis.py
Output: printed results, also saved to q3_analysis_log.txt via `tee` when run
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from scipy.stats import chi2_contingency
from scipy.stats import chi2 as chi2_dist


# -----------------------------------------------------------------------
# STEP 1: Load the four band files and stack them into one pooled table.
# We add a "band" column so the pooled data still knows which band each
# row came from. Nothing about the underlying numbers changes here, we're
# just combining four tables into one so a single model can see all of it
# at once.
# -----------------------------------------------------------------------

files = {
    "under1000": "full_under1000_enriched.csv",
    "1000_1399": "full_1000_1399_enriched.csv",
    "1400_1799": "full_1400_1799_enriched.csv",
    "1800_1999": "full_1800_1999_enriched.csv",
}

dfs = []
for band_name, filename in files.items():
    df = pd.read_csv(filename)
    df["band"] = band_name
    dfs.append(df)
    print(f"Loaded {filename}: {len(df):,} rows")

pooled = pd.concat(dfs, ignore_index=True)
print(f"\nPooled total (before cleaning): {len(pooled):,} rows")

# The enriched files should already be decisive win/loss games only, but
# confirm nothing slipped through with missing values in the two columns
# the models below actually use.
pooled = pooled.dropna(subset=["book_depth_plies", "breaker_won"])
print(f"Pooled total (after dropping missing): {len(pooled):,} rows")

# Make "band" a categorical variable with under1000 as the reference level.
# This just controls which band the model treats as the baseline for
# comparison; it doesn't change the underlying test.
pooled["band"] = pd.Categorical(
    pooled["band"],
    categories=["under1000", "1000_1399", "1400_1799", "1800_1999"],
    ordered=False,
)


# -----------------------------------------------------------------------
# STEP 2: Fit the MAIN EFFECTS model (no interaction).
#
# Formula: breaker_won ~ book_depth_plies + C(band)
#
# This model assumes book_depth_plies has ONE slope, the same in every
# band. It does let each band have its own intercept (its own baseline
# win rate), but the effect of an extra ply of book depth is forced to be
# identical across bands. This is the "depth matters, band matters, but
# band doesn't change how much depth matters" model.
# -----------------------------------------------------------------------

print("\nFitting main effects model (this may take a minute on ~10.4M rows)...")
main_model = smf.logit(
    "breaker_won ~ book_depth_plies + C(band)",
    data=pooled,
).fit(disp=0)

print("\n=== MAIN EFFECTS MODEL (single depth slope for all bands) ===")
print(main_model.summary())


# -----------------------------------------------------------------------
# STEP 3: Fit the INTERACTION model.
#
# Formula: breaker_won ~ book_depth_plies * C(band)
#
# The "*" tells statsmodels to include book_depth_plies, band, AND their
# interaction. This lets each band have its OWN depth slope, estimated
# simultaneously inside one model, rather than four separate models.
# -----------------------------------------------------------------------

print("\nFitting interaction model...")
interaction_model = smf.logit(
    "breaker_won ~ book_depth_plies * C(band)",
    data=pooled,
).fit(disp=0)

print("\n=== INTERACTION MODEL (depth slope allowed to vary by band) ===")
print(interaction_model.summary())


# -----------------------------------------------------------------------
# STEP 4: Likelihood Ratio Test comparing the two models.
#
# The interaction model will always fit at least as well as the main
# effects model, because it has more free parameters (three extra depth
# slopes, one per non-reference band). The LRT asks whether that
# improvement in fit is bigger than what you'd expect just from adding
# more parameters by chance.
#
#   LR statistic = 2 * (log-likelihood of bigger model - log-likelihood
#                        of smaller model)
#   This statistic follows a chi-square distribution with degrees of
#   freedom equal to the difference in number of parameters between the
#   two models.
# -----------------------------------------------------------------------

llf_main = main_model.llf
llf_interaction = interaction_model.llf
df_diff = interaction_model.df_model - main_model.df_model

lr_stat = 2 * (llf_interaction - llf_main)
lr_pvalue = chi2_dist.sf(lr_stat, df_diff)

print("\n=== LIKELIHOOD RATIO TEST: does the DEPTH EFFECT vary by band? ===")
print(f"Main model Log-Likelihood:        {llf_main:.2f}")
print(f"Interaction model Log-Likelihood: {llf_interaction:.2f}")
print(f"Degrees of freedom difference:    {df_diff}")
print(f"LR statistic:                     {lr_stat:.4f}")
print(f"p-value:                          {lr_pvalue:.6f}")
if lr_pvalue < 0.05:
    print("(p < 0.05 -> the depth effect DOES significantly vary across bands)")
else:
    print("(p >= 0.05 -> cannot reject the null; no evidence the depth effect varies by band)")


# -----------------------------------------------------------------------
# STEP 5: Chi-square test - does the RAW breaker win rate differ by band?
#
# This is a separate, simpler question from Step 4. It ignores
# book_depth_plies entirely and just asks: is the proportion of breaker
# wins actually different across the four bands, or could the upward
# trend we saw (0.478 -> 0.482 -> 0.487 -> 0.488) be chance?
# -----------------------------------------------------------------------

contingency = pd.crosstab(pooled["band"], pooled["breaker_won"])
print("\n=== CONTINGENCY TABLE: band vs breaker_won (counts) ===")
print(contingency)

chi2_stat, chi2_pvalue, dof, expected = chi2_contingency(contingency)

print("\n=== CHI-SQUARE TEST: does breaker WIN RATE vary by band? ===")
print(f"Chi-square statistic: {chi2_stat:.4f}")
print(f"Degrees of freedom:   {dof}")
print(f"p-value:              {chi2_pvalue:.10f}")
if chi2_pvalue < 0.05:
    print("(p < 0.05 -> breaker win rate DOES significantly differ across bands)")
else:
    print("(p >= 0.05 -> cannot reject the null; no evidence win rate differs by band)")

print("\n=== DONE ===")
