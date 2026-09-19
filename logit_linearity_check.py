"""
logit_linearity_check.py (v2)

Checks the linearity-of-the-logit assumption for the book_depth_plies
predictor, per rating band, using two methods:
  1. Exact-integer empirical logit plot (visual check)
  2. Box-Tidwell test (formal statistical check)

Run from ~/chess_capstone/ with the venv activated.
"""

import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt

BANDS = {
    "under1000": "full_under1000_enriched.csv",
    "1000_1399": "full_1000_1399_enriched.csv",
    "1400_1799": "full_1400_1799_enriched.csv",
    "1800_1999": "full_1800_1999_enriched.csv",
}

MIN_N_PER_VALUE = 500  # drop sparse high-depth values from the plot to avoid noisy single-game bins
LOG_PATH = "logit_linearity_check_log.txt"
PLOT_PATH = "visuals/logit_linearity_check.png"

results = []
log_lines = []

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, (band_name, filepath) in enumerate(BANDS.items()):
    log_lines.append(f"\n=== Band: {band_name} ===")

    df = pd.read_csv(filepath, usecols=["book_depth_plies", "breaker_won"])
    df = df.dropna(subset=["book_depth_plies", "breaker_won"])

    # --- 1. Exact-integer empirical logit ---
    grouped = df.groupby("book_depth_plies").agg(
        win_rate=("breaker_won", "mean"),
        n=("breaker_won", "size"),
    ).reset_index()

    # keep only depth values with enough games to trust the win rate
    plot_data = grouped[grouped["n"] >= MIN_N_PER_VALUE].copy()
    dropped = grouped[grouped["n"] < MIN_N_PER_VALUE]

    plot_data["win_rate_clipped"] = plot_data["win_rate"].clip(0.001, 0.999)
    plot_data["empirical_logit"] = np.log(
        plot_data["win_rate_clipped"] / (1 - plot_data["win_rate_clipped"])
    )

    ax = axes[i]
    ax.scatter(plot_data["book_depth_plies"], plot_data["empirical_logit"])
    ax.plot(plot_data["book_depth_plies"], plot_data["empirical_logit"], alpha=0.5)
    ax.set_title(f"{band_name} (depth values shown: {len(plot_data)}, min n={MIN_N_PER_VALUE})")
    ax.set_xlabel("book_depth_plies (exact value)")
    ax.set_ylabel("Empirical logit of win rate")

    log_lines.append("Full distribution by exact depth value:")
    log_lines.append(grouped.to_string(index=False))
    log_lines.append(f"\nDepth values dropped from plot (n < {MIN_N_PER_VALUE}): {dropped['book_depth_plies'].tolist()}")

    # --- 2. Box-Tidwell test (unchanged, uses raw continuous values, not the plot's grouping) ---
    bt_df = df[df["book_depth_plies"] > 0].copy()
    bt_df["log_depth"] = np.log(bt_df["book_depth_plies"])
    bt_df["depth_x_log_depth"] = bt_df["book_depth_plies"] * bt_df["log_depth"]

    model = smf.logit(
        "breaker_won ~ book_depth_plies + depth_x_log_depth",
        data=bt_df,
    ).fit(disp=0)

    interaction_coef = model.params["depth_x_log_depth"]
    interaction_p = model.pvalues["depth_x_log_depth"]

    verdict = "LINEARITY VIOLATED (p < .05)" if interaction_p < 0.05 else "Linearity holds (p >= .05)"

    log_lines.append(f"\nBox-Tidwell interaction term (depth_x_log_depth):")
    log_lines.append(f"  coefficient = {interaction_coef:.6f}")
    log_lines.append(f"  p-value     = {interaction_p:.6f}")
    log_lines.append(f"  verdict     = {verdict}")

    results.append({
        "band": band_name,
        "bt_interaction_coef": interaction_coef,
        "bt_interaction_p": interaction_p,
        "verdict": verdict,
    })

plt.tight_layout()
plt.savefig(PLOT_PATH, dpi=150)
print(f"Plot saved to {PLOT_PATH}")

with open(LOG_PATH, "w") as f:
    f.write("\n".join(log_lines))
print(f"Log saved to {LOG_PATH}")

print("\n=== Summary ===")
summary_df = pd.DataFrame(results)
print(summary_df.to_string(index=False))
