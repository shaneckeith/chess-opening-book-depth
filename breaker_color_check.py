"""
breaker_color_check.py

Checks whether book_depth_plies parity predicts the actual book_breaker
color, per rating band. Confirms or refutes the hypothesis that the
even/odd zigzag in the linearity check is driven by breaker color.
"""

import pandas as pd

BANDS = {
    "under1000": "full_under1000_enriched.csv",
    "1000_1399": "full_1000_1399_enriched.csv",
    "1400_1799": "full_1400_1799_enriched.csv",
    "1800_1999": "full_1800_1999_enriched.csv",
}

LOG_PATH = "breaker_color_check_log.txt"

log_lines = []
summary = []

for band_name, filepath in BANDS.items():
    log_lines.append(f"\n=== Band: {band_name} ===")

    df = pd.read_csv(filepath, usecols=["book_depth_plies", "book_breaker"])
    df = df.dropna(subset=["book_depth_plies", "book_breaker"])

    # Prediction: even depth -> White breaks (plays ply depth+1, which is odd)
    #             odd depth  -> Black breaks (plays ply depth+1, which is even)
    df["predicted_breaker"] = df["book_depth_plies"].apply(
        lambda d: "white" if d % 2 == 0 else "black"
    )

    df["match"] = df["predicted_breaker"] == df["book_breaker"]
    agreement_rate = df["match"].mean()

    crosstab = pd.crosstab(df["book_depth_plies"] % 2, df["book_breaker"])
    crosstab.index = crosstab.index.map({0: "even depth", 1: "odd depth"})

    log_lines.append(f"Agreement rate between depth-parity prediction and actual book_breaker: {agreement_rate:.4%}")
    log_lines.append(f"\nCrosstab (depth parity vs. actual breaker color):")
    log_lines.append(crosstab.to_string())

    summary.append({
        "band": band_name,
        "agreement_rate": agreement_rate,
        "n": len(df),
    })

with open(LOG_PATH, "w") as f:
    f.write("\n".join(log_lines))
print(f"Log saved to {LOG_PATH}")

print("\n=== Summary ===")
summary_df = pd.DataFrame(summary)
print(summary_df.to_string(index=False))
