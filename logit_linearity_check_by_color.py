"""
Reruns the Box-Tidwell linearity check separately for White-broke-book
games (even book_depth_plies) and Black-broke-book games (odd
book_depth_plies), within each rating band.

Purpose: the original logit_linearity_check.py found statistically
significant nonlinearity (Box-Tidwell interaction term) in three of
four bands. Since book_depth_plies parity is structurally identical to
Book Breaker color (confirmed 100% agreement, all 9,915,469 games,
see breaker_color_check.py), this script tests whether splitting by
color removes or reduces the detected nonlinearity -- i.e. whether the
"curve" Box-Tidwell found is actually the alternating even/odd color
effect rather than genuine curvature in the depth relationship itself.

Usage:
    python3 logit_linearity_check_by_color.py full_under1000_enriched.csv full_1000_1399_enriched.csv full_1400_1799_enriched.csv full_1800_1999_enriched.csv
"""

import sys
import numpy as np
import pandas as pd
import statsmodels.api as sm

def box_tidwell(df, label):
    """Fit breaker_won ~ book_depth_plies + book_depth_plies*log(book_depth_plies)
    and report the interaction term's coefficient and p-value.
    Requires book_depth_plies > 0."""
    d = df[df["book_depth_plies"] > 0].copy()
    n = len(d)

    d["log_depth"] = np.log(d["book_depth_plies"])
    d["depth_x_log_depth"] = d["book_depth_plies"] * d["log_depth"]

    X = sm.add_constant(d[["book_depth_plies", "depth_x_log_depth"]])
    y = d["breaker_won"]

    model = sm.Logit(y, X).fit(disp=0)

    coef = model.params["depth_x_log_depth"]
    pval = model.pvalues["depth_x_log_depth"]
    verdict = "LINEARITY VIOLATED (p < .05)" if pval < 0.05 else "Linearity holds (p >= .05)"

    return {
        "subset": label,
        "n": n,
        "coef": coef,
        "p": pval,
        "verdict": verdict,
    }

def analyze_band(filepath):
    df = pd.read_csv(filepath)
    band_name = filepath.replace("full_", "").replace("_enriched.csv", "")

    white_broke = df[df["book_depth_plies"] % 2 == 0]
    black_broke = df[df["book_depth_plies"] % 2 == 1]

    results = []
    results.append(box_tidwell(df, f"{band_name} - ALL (unsplit, original check)"))
    results.append(box_tidwell(white_broke, f"{band_name} - White broke book (even depth)"))
    results.append(box_tidwell(black_broke, f"{band_name} - Black broke book (odd depth)"))
    return results

def main():
    filepaths = sys.argv[1:]
    if not filepaths:
        print("Usage: python3 logit_linearity_check_by_color.py <file1_enriched.csv> ...")
        sys.exit(1)

    all_results = []
    for fp in filepaths:
        all_results.extend(analyze_band(fp))

    print(f"{'Subset':<45} {'n':>10} {'coef':>12} {'p':>12} {'verdict':<28}")
    for r in all_results:
        print(f"{r['subset']:<45} {r['n']:>10,} {r['coef']:>12.6f} {r['p']:>12.6f} {r['verdict']:<28}")

    out_df = pd.DataFrame(all_results)
    out_path = "linearity_check_by_color.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved full results to {out_path}")

if __name__ == "__main__":
    main()
