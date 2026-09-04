"""
plot_band_comparison.py

Reads the four full-population analysis logs and produces a two-panel
matplotlib figure comparing breaker win rate and book depth coefficient
across rating bands. Built for Task 2/3 visual communication (rubric C6).

Values are parsed directly from full_*_analysis_log.txt rather than
hardcoded, so the chart stays tied to the actual script output instead
of a manually transcribed copy that could drift or contain a typo.

Usage:
    python3 plot_band_comparison.py
"""

import re
import matplotlib.pyplot as plt

BANDS = ["under1000", "1000_1399", "1400_1799", "1800_1999"]
BAND_LABELS = ["Under 1000", "1000-1399", "1400-1799", "1800-1999"]

DATA_DIR = "../"  # log files live one level up, in chess_capstone/

def parse_log(band_name):
    """Extract breaker win rate, depth coefficient, its std err, and the
    primary LRT p-value from one full_<band>_analysis_log.txt file."""
    path = f"{DATA_DIR}full_{band_name}_analysis_log.txt"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    win_rate = float(re.search(r"Breaker win rate:\s*([\d.]+)", text).group(1))

    # statsmodels summary row: "book_depth_plies    -0.0020      0.001 ..."
    coef_match = re.search(
        r"book_depth_plies\s+(-?[\d.]+)\s+(-?[\d.]+)", text
    )
    depth_coef = float(coef_match.group(1))
    depth_stderr = float(coef_match.group(2))

    # Pull from the model summary's "LLR p-value" line instead of the
    # earlier printed line, which truncates to 0.000000 for very small
    # p-values due to :.6f formatting in full_analysis.py.
    p_match = re.search(r"LLR p-value:\s*([\d.e-]+)", text)
    lrt_pvalue = float(p_match.group(1))

    n_match = re.search(r"Rows after dropping draws/incomplete:\s*([\d,]+)", text)
    n_games = int(n_match.group(1).replace(",", ""))

    return {
        "win_rate": win_rate,
        "depth_coef": depth_coef,
        "depth_stderr": depth_stderr,
        "lrt_pvalue": lrt_pvalue,
        "n_games": n_games,
    }

# --- Parse all four bands ---
data = {band: parse_log(band) for band in BANDS}

print("Parsed values (spot-check these against the console output before trusting the chart):")
for band, label in zip(BANDS, BAND_LABELS):
    d = data[band]
    print(f"  {label}: N={d['n_games']:,}  win_rate={d['win_rate']:.4f}  "
          f"depth_coef={d['depth_coef']:.4f}  p={d['lrt_pvalue']:.4g}")

# --- Build the figure ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Panel 1: breaker win rate by band
win_rates = [data[b]["win_rate"] * 100 for b in BANDS]
ax1.bar(BAND_LABELS, win_rates, color="#378ADD", width=0.6)
ax1.axhline(50, color="#888780", linestyle="--", linewidth=1, label="50% (no advantage)")
ax1.set_ylabel("Breaker win rate (%)")
ax1.set_title("Book breaker win rate by rating band")
ax1.set_ylim(45, 51)
for i, v in enumerate(win_rates):
    ax1.text(i, v + 0.1, f"{v:.2f}%", ha="center", fontsize=9)
ax1.legend(loc="upper left", fontsize=9)

# Panel 2: depth coefficient by band, with error bars (std err) and
# significance markers based on the primary LRT p-value per band
depth_coefs = [data[b]["depth_coef"] for b in BANDS]
depth_errs = [data[b]["depth_stderr"] for b in BANDS]
colors = ["#B4B2A9" if data[b]["lrt_pvalue"] >= 0.05 else "#D85A30" for b in BANDS]

ax2.bar(BAND_LABELS, depth_coefs, yerr=depth_errs, color=colors,
        width=0.6, capsize=4)
ax2.axhline(0, color="#888780", linestyle="-", linewidth=1)
ax2.set_ylabel("Book depth coefficient (log-odds per ply)")
ax2.set_title("Depth effect by rating band\n(gray = not significant, p >= 0.05)")

plt.tight_layout()
output_path = "band_comparison.png"
plt.savefig(output_path, dpi=150)
print(f"\nSaved chart to {output_path}")
