"""
opening_breakdown.py

Exploratory analysis: for a given band's CSV, breaks down first-breaker
win rate by matched opening (matched_name), with a minimum sample-size
filter and a Bonferroni-corrected significance test to guard against
false positives from running many comparisons at once.

This is deliberately kept separate from full_analysis.py's primary
Q1/Q2 analysis - it's an exploratory extension, not part of the
Task 1-approved core hypothesis. Results should be reported as
descriptive/exploratory unless they clear the Bonferroni-corrected
threshold.

Usage:
    python3 opening_breakdown.py <input_csv> [--min-games N]

Example:
    python3 opening_breakdown.py full_1400_1799.csv --min-games 100
"""
import sys
import argparse
import pandas as pd
import numpy as np
from scipy import stats


def load_and_prepare(path):
    df = pd.read_csv(path)
    before = len(df)
    # breaker_won must exist; if not already derived, this script assumes
    # full_analysis.py's preprocessing (dropping draws/incomplete games,
    # deriving breaker_won from ply parity) has already been applied
    # upstream. If breaker_won isn't present, bail out loudly rather than
    # silently guessing.
    if "breaker_won" not in df.columns:
        raise ValueError(
            "Column 'breaker_won' not found. This script expects the same "
            "preprocessed input full_analysis.py uses (draws/incomplete "
            "games already dropped, breaker_won already derived). Run "
            "full_analysis.py's preprocessing first or point this script "
            "at that same intermediate dataframe."
        )
    df = df.dropna(subset=["breaker_won", "matched_name"])
    after = len(df)
    print(f"Loaded {before:,} rows, {after:,} usable after dropping "
          f"missing breaker_won/matched_name.")
    return df


def opening_breakdown(df, min_games):
    grouped = df.groupby("matched_name").agg(
        games=("breaker_won", "count"),
        breaker_win_rate=("breaker_won", "mean"),
    ).reset_index()

    total_openings = len(grouped)
    filtered = grouped[grouped["games"] >= min_games].copy()
    print(f"{len(filtered)} of {total_openings} distinct matched openings "
          f"have >= {min_games} games in this band.")

    if len(filtered) == 0:
        print("No openings meet the minimum game count. Try a lower "
              "--min-games threshold.")
        return None

    n_tests = len(filtered)
    bonferroni_alpha = 0.05 / n_tests
    print(f"Running {n_tests} one-sample tests against 0.5. "
          f"Bonferroni-corrected alpha = {bonferroni_alpha:.6f} "
          f"(uncorrected 0.05 / {n_tests})")

    p_values = []
    for name in filtered["matched_name"]:
        opening_games = df.loc[df["matched_name"] == name, "breaker_won"]
        _, p_val = stats.ttest_1samp(opening_games, 0.5)
        p_values.append(p_val)

    filtered["p_value"] = p_values
    filtered["significant_after_bonferroni"] = filtered["p_value"] < bonferroni_alpha
    filtered = filtered.sort_values("breaker_win_rate").reset_index(drop=True)

    return filtered, bonferroni_alpha


def print_report(filtered, bonferroni_alpha, top_n=15):
    sig = filtered[filtered["significant_after_bonferroni"]]

    print("\n" + "=" * 70)
    print("TIER 1: Statistically significant after Bonferroni correction")
    print("(these are the ones you can actually claim differ from 50%,")
    print(" accounting for having run many comparisons)")
    print("=" * 70)
    if len(sig) == 0:
        print("None. No individual opening clears the corrected threshold "
              "in this band. This is itself a legitimate finding - it "
              "suggests any opening-level pattern in the full ranked list "
              "below is more likely noise than a real per-opening effect.")
    else:
        print(sig[["matched_name", "games", "breaker_win_rate", "p_value"]]
              .to_string(index=False))

    print("\n" + "=" * 70)
    print(f"TIER 2: Full ranked list (lowest breaker win rate first), "
          f"exploratory only")
    print("(NOT individually significance-tested for your report - report")
    print(" this as descriptive pattern-spotting, not a confirmed result)")
    print("=" * 70)
    print(f"\n-- Bottom {top_n} (worst for the first-breaker) --")
    print(filtered.head(top_n)[["matched_name", "games", "breaker_win_rate"]]
          .to_string(index=False))
    print(f"\n-- Top {top_n} (best for the first-breaker) --")
    print(filtered.tail(top_n)[["matched_name", "games", "breaker_win_rate"]]
          .to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--min-games", type=int, default=100,
                         help="Minimum games in a band for an opening to "
                              "be included (default: 100)")
    args = parser.parse_args()

    print(f"=== Opening-level breakdown: {args.input_csv} "
          f"(min_games={args.min_games}) ===\n")

    df = load_and_prepare(args.input_csv)
    result = opening_breakdown(df, args.min_games)
    if result is not None:
        filtered, bonferroni_alpha = result
        print_report(filtered, bonferroni_alpha)

        out_path = args.input_csv.replace(".csv", "_opening_breakdown.csv")
        filtered.to_csv(out_path, index=False)
        print(f"\nFull results (all openings meeting min-games) saved to "
              f"{out_path}")

    print("\n=== DONE ===")
