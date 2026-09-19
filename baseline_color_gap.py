"""
baseline_color_gap.py

Computes the overall White vs. Black win rate across the full population
of each band (no book-breaking filter), to compare against the previously
found breaker-only color gap.
"""

import pandas as pd

BANDS = {
    "under1000": "full_under1000_enriched.csv",
    "1000_1399": "full_1000_1399_enriched.csv",
    "1400_1799": "full_1400_1799_enriched.csv",
    "1800_1999": "full_1800_1999_enriched.csv",
}

LOG_PATH = "baseline_color_gap_log.txt"
log_lines = []
results = []

for band_name, filepath in BANDS.items():
    log_lines.append(f"\n=== Band: {band_name} ===")

    df = pd.read_csv(filepath, usecols=["result"])
    df = df.dropna(subset=["result"])

    # result is presumably '1-0' (white wins), '0-1' (black wins), '1/2-1/2' (draw)
    # count overall white win rate and black win rate across ALL games,
    # regardless of who broke book or whether anyone did
    total = len(df)
    white_wins = (df["result"] == "1-0").sum()
    black_wins = (df["result"] == "0-1").sum()
    draws = (df["result"] == "1/2-1/2").sum()

    white_win_rate = white_wins / total
    black_win_rate = black_wins / total
    draw_rate = draws / total

    baseline_gap_pct_points = (white_win_rate - black_win_rate) * 100

    log_lines.append(f"Total games: {total}")
    log_lines.append(f"White win rate: {white_win_rate:.4%}")
    log_lines.append(f"Black win rate: {black_win_rate:.4%}")
    log_lines.append(f"Draw rate: {draw_rate:.4%}")
    log_lines.append(f"Baseline White-Black win rate gap: {baseline_gap_pct_points:.2f} percentage points")

    results.append({
        "band": band_name,
        "white_win_rate": white_win_rate,
        "black_win_rate": black_win_rate,
        "draw_rate": draw_rate,
        "baseline_gap_pct_points": baseline_gap_pct_points,
    })

with open(LOG_PATH, "w") as f:
    f.write("\n".join(log_lines))
print(f"Log saved to {LOG_PATH}")

print("\n=== Summary ===")
summary_df = pd.DataFrame(results)
print(summary_df.to_string(index=False))
