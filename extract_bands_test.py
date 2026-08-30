"""
extract_bands_test.py

Streams a Lichess .zst PGN export and, for a ~10% random sample of eligible
rapid-rated games, buckets each game into one of four rating bands and
computes book_depth_plies using the same prefix-matching logic as
book_depth.py. Writes one output CSV per band.

Sampling method: since a .zst file can't be seek-sampled (it must be
decompressed sequentially, start to finish), each game that passes the
non-random filters gets an independent Bernoulli trial - keep it with
probability SAMPLE_RATE. Over millions of games this converges to ~10%
of eligible games.

Band assignment: BOTH players' ratings must fall in the same band for the
game to be included. Games with either player >= 2000, or with players in
different bands, are skipped entirely.
    under1000   :    0 -  999
    1000_1399   : 1000 - 1399
    1400_1799   : 1400 - 1799
    1800_1999   : 1800 - 1999

Rapid definition (Lichess formula): base + 40*increment must fall in
[480, 1499] seconds. "Abandoned" terminations are excluded; "Time forfeit"
is kept as a legitimate outcome.
"""

import zstandard as zstd
import io
import chess.pgn
import pickle
import csv
import random
import sys
import time

SAMPLE_RATE = 0.10
random.seed(42)  # fixed seed -> reproducible test run

BANDS = [
    ("under1000", 0, 999),
    ("1000_1399", 1000, 1399),
    ("1400_1799", 1400, 1799),
    ("1800_1999", 1800, 1999),
]

with open("eco_lookup.pkl", "rb") as fh:
    lookup = pickle.load(fh)
KNOWN_PREFIXES = lookup["prefixes"]
FULL_LINES = lookup["full_lines"]


def book_depth_for_game(game):
    """Same logic as book_depth.py: walk mainline SAN moves, track deepest
    ply that still matches a known opening prefix."""
    board = game.board()
    san_moves = []
    depth = 0
    best_match_name = None
    best_match_eco = None
    for move in game.mainline_moves():
        san = board.san(move)
        board.push(move)
        san_moves.append(san)
        seq = tuple(san_moves)
        if seq in KNOWN_PREFIXES:
            depth = len(seq)
            if seq in FULL_LINES:
                best_match_eco, best_match_name = FULL_LINES[seq]
        else:
            break
    return depth, best_match_eco, best_match_name


def is_rapid(time_control):
    """Lichess rapid definition: base + 40*increment in [480, 1499] seconds."""
    if not time_control or time_control == "-":
        return False
    try:
        base_str, inc_str = time_control.split("+")
        base = int(base_str)
        inc = int(inc_str)
    except (ValueError, AttributeError):
        return False
    estimated = base + 40 * inc
    return 480 <= estimated <= 1499


def get_band(white_elo, black_elo):
    """Return the band name if both players fall in the SAME band, else None."""
    try:
        w = int(white_elo)
        b = int(black_elo)
    except (TypeError, ValueError):
        return None
    for band_name, low, high in BANDS:
        if low <= w <= high and low <= b <= high:
            return band_name
    return None


def process_zst(zst_path, sample_rate=SAMPLE_RATE):
    band_files = {}
    band_writers = {}
    band_counts = {name: 0 for name, _, _ in BANDS}

    for band_name, _, _ in BANDS:
        f = open(f"sample_{band_name}.csv", "w", newline="", encoding="utf-8")
        band_files[band_name] = f
        band_writers[band_name] = None  # created lazily once we know fieldnames

    dctx = zstd.ZstdDecompressor()
    total_games = 0
    kept_games = 0
    start = time.time()

    with open(zst_path, "rb") as compressed:
        with dctx.stream_reader(compressed) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")
            while True:
                game = chess.pgn.read_game(text_stream)
                if game is None:
                    break
                total_games += 1

                h = game.headers

                if h.get("Termination") == "Abandoned":
                    continue
                if not is_rapid(h.get("TimeControl")):
                    continue

                band_name = get_band(h.get("WhiteElo"), h.get("BlackElo"))
                if band_name is None:
                    continue

                if random.random() >= sample_rate:
                    continue

                depth, eco, name = book_depth_for_game(game)

                row = {
                    "white_elo": h.get("WhiteElo"),
                    "black_elo": h.get("BlackElo"),
                    "result": h.get("Result"),
                    "termination": h.get("Termination"),
                    "time_control": h.get("TimeControl"),
                    "book_depth_plies": depth,
                    "matched_eco": eco,
                    "matched_name": name,
                    "header_eco": h.get("ECO"),
                    "header_opening": h.get("Opening"),
                }

                if band_writers[band_name] is None:
                    writer = csv.DictWriter(band_files[band_name], fieldnames=row.keys())
                    writer.writeheader()
                    band_writers[band_name] = writer
                band_writers[band_name].writerow(row)

                band_counts[band_name] += 1
                kept_games += 1

                if total_games % 100000 == 0:
                    elapsed = time.time() - start
                    print(f"  ...scanned {total_games:,} games, kept {kept_games:,} "
                          f"({elapsed:.0f}s elapsed)", flush=True)

    for f in band_files.values():
        f.close()

    return total_games, kept_games, band_counts


if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "lichess_db_standard_rated_2023-06.pgn.zst"
    print(f"Starting band extraction (test run, {SAMPLE_RATE:.0%} sample) from {infile}")
    total, kept, counts = process_zst(infile)
    print("\n=== DONE ===")
    print(f"Total games scanned: {total:,}")
    print(f"Total games kept:    {kept:,}")
    for band_name, _, _ in BANDS:
        print(f"  {band_name}: {counts[band_name]:,} games -> sample_{band_name}.csv")
