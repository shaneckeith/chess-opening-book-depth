"""
spot_check_samples.py

Validates the four sample_<band>.csv files produced by extract_bands_test.py
before trusting them as input to full_analysis.py. Checks:
  1. Row counts match the reported kept totals from the extraction run.
  2. Both white_elo and black_elo actually fall inside each file's band.
  3. No "Abandoned" terminations slipped through.
  4. Every time_control value satisfies the rapid formula
     (base + 40*increment in [480, 1499] seconds).
  5. Prints a few known-opening matches for manual ply-count verification.
  6. Plots the book_depth_plies distribution per band, for a quick visual
     sanity check (also usable directly in the Panopto walkthrough).

Run from the same directory as the sample_*.csv files.
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed on a headless EC2 instance
import matplotlib.pyplot as plt

# Must match extract_bands_test.py's BANDS exactly.
BANDS = {
    "under1000": (0, 999),
    "1000_1399": (1000, 1399),
    "1400_1799": (1400, 1799),
    "1800_1999": (1800, 1999),
}

# Fill in with the actual "kept" counts printed by extract_bands_test.py's
# === DONE === summary, to cross-check row counts below.
EXPECTED_COUNTS = {
    "under1000": 86150,   # e.g. 86150
    "1000_1399": 321723,   # e.g. 321723
    "1400_1799": 484609,   # e.g. 484609
    "1800_1999": 149517,   # e.g. 149517
}


def check_band(name, low, high):
    path = f"sample_{name}.csv"
    print(f"\n{'=' * 60}")
    print(f"Checking {path}  (expected band: {low}-{high})")
    print("=" * 60)

    df = pd.read_csv(path)
    n = len(df)
    print(f"Row count: {n:,}")

    expected = EXPECTED_COUNTS.get(name)
    if expected is not None:
        status = "OK" if n == expected else "MISMATCH"
        print(f"Expected (from extraction summary): {expected:,}  [{status}]")
    else:
        print("Expected count not set - fill in EXPECTED_COUNTS to enable this check.")

    # --- Band boundary check ---
    bad_white = df[(df["white_elo"] < low) | (df["white_elo"] > high)]
    bad_black = df[(df["black_elo"] < low) | (df["black_elo"] > high)]
    print(f"white_elo range in file: {df['white_elo'].min()} - {df['white_elo'].max()}")
    print(f"black_elo range in file: {df['black_elo'].min()} - {df['black_elo'].max()}")
    if len(bad_white) or len(bad_black) > 0:
        print(f"  !! {len(bad_white)} rows with white_elo out of band, "
              f"{len(bad_black)} rows with black_elo out of band")
    else:
        print("  Band boundaries OK - no rows outside the expected range.")

    # --- Abandoned termination check ---
    abandoned = (df["termination"] == "Abandoned").sum()
    print(f"Abandoned terminations found: {abandoned} "
          f"({'OK' if abandoned == 0 else 'SHOULD BE 0'})")

    # --- Rapid time control check ---
    def is_rapid(tc):
        try:
            base_str, inc_str = str(tc).split("+")
            return 480 <= int(base_str) + 40 * int(inc_str) <= 1499
        except (ValueError, AttributeError):
            return False

    non_rapid = df[~df["time_control"].apply(is_rapid)]
    print(f"Non-rapid time_control values found: {len(non_rapid)} "
          f"({'OK' if len(non_rapid) == 0 else 'SHOULD BE 0'})")
    if len(non_rapid) > 0:
        print(f"  Examples: {non_rapid['time_control'].unique()[:5]}")

    # --- Known opening spot-check (manual verification aid) ---
    italian = df[df["matched_name"].astype(str).str.contains("Italian Game", na=False)]
    if len(italian) > 0:
        print(f"\nSample 'Italian Game' matches for manual ply-count verification:")
        print(italian[["book_depth_plies", "matched_eco", "matched_name"]].head(3).to_string(index=False))
    else:
        print("\nNo 'Italian Game' matches in this file to spot-check.")

    return df


def main():
    all_dfs = {}
    for name, (low, high) in BANDS.items():
        try:
            all_dfs[name] = check_band(name, low, high)
        except FileNotFoundError:
            print(f"\n!! sample_{name}.csv not found - skipping.")

    # --- Book depth distribution plot, one panel per band ---
    if all_dfs:
        fig, axes = plt.subplots(1, len(all_dfs), figsize=(5 * len(all_dfs), 4), sharey=True)
        if len(all_dfs) == 1:
            axes = [axes]
        for ax, (name, df) in zip(axes, all_dfs.items()):
            ax.hist(df["book_depth_plies"], bins=30, color="steelblue", edgecolor="white")
            ax.set_title(name)
            ax.set_xlabel("book_depth_plies")
        axes[0].set_ylabel("Number of games")
        fig.suptitle("Book depth distribution by rating band (10% sample)")
        fig.tight_layout()
        fig.savefig("book_depth_distribution.png", dpi=150)
        print("\nSaved book_depth_distribution.png")


if __name__ == "__main__":
    main()
