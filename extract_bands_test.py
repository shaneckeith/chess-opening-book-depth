"""
extract_bands_test.py (v2 - raw text buffering)

Streams a .zst PGN export. For each game, reads the raw text block
(headers + movetext) into memory as plain strings first - no python-chess
involved. Checks rapid/band/termination via simple string search on the
header lines. Only games that pass ALL cheap filters AND the sampling
draw get parsed by chess.pgn (via io.StringIO on the buffered text) for
book-depth scoring. This avoids python-chess parsing entirely for the
~90%+ of games that get filtered out or sampled away.

(v1's read_headers()+seek-back approach was abandoned: the zstd streaming
reader is not seekable, which the seek-based skip pattern requires.)
"""
import zstandard as zstd
import io
import chess.pgn
import pickle
import csv
import random
import sys
import time
import re

SAMPLE_RATE = 0.10
random.seed(42)

BANDS = [
    ("under1000", 0, 999),
    ("1000_1399", 1000, 1399),
    ("1400_1799", 1400, 1799),
    ("1800_1999", 1800, 1999),
]

RE_WHITEELO = re.compile(r'\[WhiteElo "(\d+)"\]')
RE_BLACKELO = re.compile(r'\[BlackElo "(\d+)"\]')
RE_TIMECONTROL = re.compile(r'\[TimeControl "([^"]*)"\]')
RE_TERMINATION = re.compile(r'\[Termination "([^"]*)"\]')

print("Loading ECO lookup table...", flush=True)
with open("eco_lookup.pkl", "rb") as fh:
    lookup = pickle.load(fh)
KNOWN_PREFIXES = lookup["prefixes"]
FULL_LINES = lookup["full_lines"]
print(f"Loaded {len(FULL_LINES):,} known lines, {len(KNOWN_PREFIXES):,} prefixes.", flush=True)


def book_depth_for_game(game):
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
    if not time_control or time_control == "-":
        return False
    try:
        base_str, inc_str = time_control.split("+")
        return 480 <= int(base_str) + 40 * int(inc_str) <= 1499
    except (ValueError, AttributeError):
        return False


def get_band(white_elo, black_elo):
    try:
        w, b = int(white_elo), int(black_elo)
    except (TypeError, ValueError):
        return None
    for band_name, low, high in BANDS:
        if low <= w <= high and low <= b <= high:
            return band_name
    return None


def read_game_blocks(text_stream):
    """Yield raw text blocks, one per game, by watching for the start of a
    new [Event tag - NOT blank lines, since a blank line also separates
    each game's own headers from its movetext (so blank-line splitting
    double-counts every game). Pure text - no python-chess."""
    lines = []
    for line in text_stream:
        if line.startswith("[Event ") and lines:
            yield "".join(lines)
            lines = []
        lines.append(line)
    if lines:
        yield "".join(lines)


def process_zst(zst_path, sample_rate=SAMPLE_RATE):
    print(f"Opening {zst_path} ...", flush=True)
    band_files = {name: open(f"sample_{name}.csv", "w", newline="", encoding="utf-8") for name, _, _ in BANDS}
    band_writers = {name: None for name, _, _ in BANDS}
    band_counts = {name: 0 for name, _, _ in BANDS}

    dctx = zstd.ZstdDecompressor()
    total_games = 0
    kept_games = 0
    start = time.time()

    with open(zst_path, "rb") as compressed:
        with dctx.stream_reader(compressed) as reader:
            text_stream = io.TextIOWrapper(reader, encoding="utf-8")
            print("Stream opened. Beginning scan...", flush=True)

            for block in read_game_blocks(text_stream):
                total_games += 1

                m_white = RE_WHITEELO.search(block)
                m_black = RE_BLACKELO.search(block)
                m_tc = RE_TIMECONTROL.search(block)
                m_term = RE_TERMINATION.search(block)

                white_elo = m_white.group(1) if m_white else None
                black_elo = m_black.group(1) if m_black else None
                time_control = m_tc.group(1) if m_tc else None
                termination = m_term.group(1) if m_term else None

                if termination == "Abandoned":
                    pass
                elif not is_rapid(time_control):
                    pass
                else:
                    band_name = get_band(white_elo, black_elo)
                    if band_name is not None and random.random() < sample_rate:
                        game = chess.pgn.read_game(io.StringIO(block))
                        if game is not None:
                            depth, eco, name = book_depth_for_game(game)
                            h = game.headers
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

                if total_games % 25000 == 0:
                    elapsed = time.time() - start
                    rate = total_games / elapsed if elapsed > 0 else 0
                    print(f"  ...scanned {total_games:,} games, kept {kept_games:,}, "
                          f"{elapsed:.0f}s elapsed, {rate:.0f} games/sec", flush=True)

    for f in band_files.values():
        f.close()
    return total_games, kept_games, band_counts


if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "lichess_db_standard_rated_2023-06.pgn.zst"
    print(f"=== Process started: band extraction (test run, {SAMPLE_RATE:.0%} sample) ===", flush=True)
    print(f"Input file: {infile}", flush=True)
    total, kept, counts = process_zst(infile)
    print("\n=== DONE ===")
    print(f"Total games scanned: {total:,}")
    print(f"Total games kept:    {kept:,}")
    for band_name, _, _ in BANDS:
        print(f"  {band_name}: {counts[band_name]:,} games -> sample_{band_name}.csv")
