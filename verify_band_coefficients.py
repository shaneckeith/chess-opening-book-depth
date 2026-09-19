"""
Verify per-band depth coefficient standard errors and confidence intervals.

Fits the same primary model (breaker_won ~ book_depth_plies) used in
full_analysis.py against each band's full-population CSV, and prints
the coefficient, standard error, 95% CI, and book_depth_plies variance
so the whisker widths in band_comparison.png can be checked directly.

Usage:
    python3 verify_band_coefficients.py full_under1000.csv full_1000_1399.csv full_1400_1799.csv full_1800_1999.csv
"""

import sys
import pandas as pd
import statsmodels.api as sm

def analyze_band(filepath):
    df = pd.read_csv(filepath)

    X = sm.add_constant(df["book_depth_plies"])
    y = df["breaker_won"]

    model = sm.Logit(y, X).fit(disp=0)

    coef = model.params["book_depth_plies"]
    se = model.bse["book_depth_plies"]
    ci_low, ci_high = model.conf_int().loc["book_depth_plies"]
    depth_var = df["book_depth_plies"].var()
    depth_std = df["book_depth_plies"].std()

    return {
        "file": filepath,
        "n": len(df),
        "coef": coef,
        "se": se,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "ci_width": ci_high - ci_low,
        "depth_std": depth_std,
        "depth_var": depth_var,
    }

def main():
    filepaths = sys.argv[1:]
    if not filepaths:
        print("Usage: python3 verify_band_coefficients.py <file1.csv> <file2.csv> ...")
        sys.exit(1)

    results = [analyze_band(fp) for fp in filepaths]

    print(f"{'Band file':<25} {'n':>10} {'coef':>10} {'SE':>10} {'95% CI':>22} {'CI width':>10} {'depth SD':>10}")
    for r in results:
        ci_str = f"[{r['ci_low']:.5f}, {r['ci_high']:.5f}]"
        print(f"{r['file']:<25} {r['n']:>10,} {r['coef']:>10.5f} {r['se']:>10.5f} {ci_str:>22} {r['ci_width']:>10.5f} {r['depth_std']:>10.3f}")

    out_df = pd.DataFrame(results)
    out_path = "band_coefficient_verification.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved full results to {out_path}")

if __name__ == "__main__":
    main()
