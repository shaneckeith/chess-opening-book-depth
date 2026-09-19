"""
breaker_color_effect.py

Fits breaker_won ~ book_breaker (color) directly, per band, to isolate
the color effect on its own, separate from book_depth_plies.
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

BANDS = {
    "under1000": "full_under1000_enriched.csv",
    "1000_1399": "full_1000_1399_enriched.csv",
    "1400_1799": "full_1400_1799_enriched.csv",
    "1800_1999": "full_1800_1999_enriched.csv",
}

LOG_PATH = "breaker_color_effect_log.txt"
log_lines = []
results = []

for band_name, filepath in BANDS.items():
    log_lines.append(f"\n=== Band: {band_name} ===")

    df = pd.read_csv(filepath, usecols=["book_breaker", "breaker_won"])
    df = df.dropna(subset=["book_breaker", "breaker_won"])

    # book_breaker is 'white' or 'black'; make white the reference level (0)
    df["breaker_is_black"] = (df["book_breaker"] == "black").astype(int)

    model = smf.logit("breaker_won ~ breaker_is_black", data=df).fit(disp=0)

    coef = model.params["breaker_is_black"]
    pval = model.pvalues["breaker_is_black"]
    odds_ratio = np.exp(coef)

    white_break_win_rate = df[df["breaker_is_black"] == 0]["breaker_won"].mean()
    black_break_win_rate = df[df["breaker_is_black"] == 1]["breaker_won"].mean()

    log_lines.append(model.summary().as_text())
    log_lines.append(f"\nWhite-breaks win rate: {white_break_win_rate:.4%}")
    log_lines.append(f"Black-breaks win rate: {black_break_win_rate:.4%}")
    log_lines.append(f"Coefficient (breaker_is_black): {coef:.6f}")
    log_lines.append(f"Odds ratio (breaker_is_black): {odds_ratio:.6f}")
    log_lines.append(f"p-value: {pval:.6e}")

    results.append({
        "band": band_name,
        "white_break_win_rate": white_break_win_rate,
        "black_break_win_rate": black_break_win_rate,
        "coef_breaker_is_black": coef,
        "odds_ratio": odds_ratio,
        "p_value": pval,
    })

with open(LOG_PATH, "w") as f:
    f.write("\n".join(log_lines))
print(f"Log saved to {LOG_PATH}")

print("\n=== Summary ===")
summary_df = pd.DataFrame(results)
print(summary_df.to_string(index=False))
