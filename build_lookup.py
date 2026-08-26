"""
Builds a lookup of known opening move sequences from the Lichess chess-openings
TSV files. Each known line is converted into a tuple of SAN moves (stripped of
move numbers), and every PREFIX of that line is marked as "known" so we can
check, ply by ply, whether a game is still following book.

Output: a set of move-sequence tuples representing every valid book prefix,
plus a dict mapping full known sequences -> (eco, name) for reference.
"""
import csv
import re
import pickle

FILES = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]

def parse_pgn_moves(pgn_str):
    """Convert '1. Nh3 d5 2. g3 e5' -> ('Nh3', 'd5', 'g3', 'e5')"""
    # Strip move numbers like "1." or "12..."
    tokens = re.sub(r'\d+\.+', '', pgn_str).split()
    return tuple(tokens)

known_prefixes = set()       # every valid prefix of every known line
full_line_lookup = {}        # full move tuple -> (eco, name)

for fname in FILES:
    with open(fname, encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            moves = parse_pgn_moves(row["pgn"])
            if not moves:
                continue
            full_line_lookup[moves] = (row["eco"], row["name"])
            # register every prefix (1 move, 2 moves, ... full line) as known
            for i in range(1, len(moves) + 1):
                known_prefixes.add(moves[:i])

print(f"Total known full lines: {len(full_line_lookup)}")
print(f"Total known prefixes (all depths): {len(known_prefixes)}")

with open("eco_lookup.pkl", "wb") as out:
    pickle.dump({"prefixes": known_prefixes, "full_lines": full_line_lookup}, out)

print("Saved eco_lookup.pkl")
