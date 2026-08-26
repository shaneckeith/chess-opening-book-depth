"""
For each game in a PGN file, replays the moves and finds the deepest ply
at which the game's move sequence still matches a known opening line
(prefix match against the Lichess chess-openings reference).

Outputs one row per game: book_depth (in plies), matched_eco, matched_name,
white_elo, black_elo, result.
"""
import chess.pgn
import pickle
import csv
import sys

with open("eco_lookup.pkl", "rb") as fh:
    lookup = pickle.load(fh)

KNOWN_PREFIXES = lookup["prefixes"]
FULL_LINES = lookup["full_lines"]

def book_depth_for_game(game):
    """Walk the game's mainline moves in SAN, tracking the deepest ply that
    still matches a known opening prefix."""
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
            # sequence no longer matches any known line -> book ends here
            break

    return depth, best_match_eco, best_match_name


def process_pgn(path, out_csv):
    results = []
    with open(path, encoding="utf-8") as pgn_fh:
        while True:
            game = chess.pgn.read_game(pgn_fh)
            if game is None:
                break
            h = game.headers
            depth, eco, name = book_depth_for_game(game)
            results.append({
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
            })

    with open(out_csv, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    return results


if __name__ == "__main__":
    infile = sys.argv[1] if len(sys.argv) > 1 else "test_games.pgn"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "book_depth_results.csv"
    results = process_pgn(infile, outfile)
    print(f"Processed {len(results)} games -> {outfile}\n")
    for r in results:
        print(r)
