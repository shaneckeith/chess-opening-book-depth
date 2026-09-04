"""
depth_milestone_breakdown.py

Q2b: Does book depth matter non-linearly, at specific milestones, rather
than as a smooth linear slope? full_analysis.py's primary logistic
regression assumes a constant per-ply effect. This script checks that
assumption by bucketing book_depth_plies into fixed-width ranges and
reporting breaker_won rate per bucket, per rating band - independent of
any linearity assumption.

Reads the four full_<band>_enriched.csv files (already contain
book_breaker/breaker_won, computed once in full_analysis.py).

Usage:
    python3 depth_milestone_breakdown.py
"""

import pandas as pd
import matplotlib.pyplot as plt

BANDS = ["under1000", "1000_1399", "1400_1799", "1800_1999"]
BAND_LABELS = ["Under 1000", "1000-1399", "1400-1799", "1800-1999"]

# Fixed-width buckets, identical across all four bands so results stay
# directly comparable band-to-band.
BUCKET_EDGES = [-1, 2, 4, 6, 8, 999]
BUCKET_LABELS = ["0-2", "3-4", "5-6", "7-8", "9+"]

results = {}

for band in BANDS:
    path = f"full_{band}_enriched.csv"
    df = pd.read_csv(path)

    df["depth_bucket"] = pd.cut(
        df["book_depth_plies"], bins=BUCKET_EDGES, labels=BUCKET_LABELS
    )

    summary = df.groupby("depth_bucket", observed=True)["breaker_won"].agg(
        ["mean", "count"]
    )
    results[band] = summary

    print(f"\n=== {band} ===")
    print(summary)

# --- Chart: grouped bar, one group per bucket, one bar per band ---
fig, ax = plt.subplots(figsize=(10, 6))

x = range(len(BUCKET_LABELS))
bar_width = 0.2
colors = ["#B4B2A9", "#378ADD", "#1D9E75", "#D85A30"]

for i, (band, label, color) in enumerate(zip(BANDS, BAND_LABELS, colors)):
    win_rates = [
        results[band].loc[b, "mean"] * 100 if b in results[band].index else None
        for b in BUCKET_LABELS
    ]
    offsets = [xi + (i - 1.5) * bar_width for xi in x]
    ax.bar(offsets, win_rates, width=bar_width, label=label, color=color)

ax.axhline(50, color="#888780", linestyle="--", linewidth=1, label="50% (no advantage)")
ax.set_ylim(42, 52)
ax.set_xticks(list(x))
ax.set_xticklabels(BUCKET_LABELS)
ax.set_xlabel("Book depth at deviation (plies)")
ax.set_ylabel("Breaker win rate (%)")
ax.set_title("Breaker win rate by depth milestone, across rating bands")
ax.legend(loc="upper right", fontsize=9)

plt.tight_layout()
output_path = "visuals/depth_milestone_breakdown.png"
plt.savefig(output_path, dpi=150)
print(f"\nSaved chart to {output_path}")
