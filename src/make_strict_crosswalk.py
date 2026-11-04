#!/usr/bin/env python3
"""Derive the strict (one-to-one) SIC -> GLORIA crosswalk from the master table.

Rule: for each SIC 1987 code, the strict GLORIA sector is the *modal* candidate,
i.e. the GLORIA sector reached by the largest number of ISIC Rev.4 rows for that
SIC. Ties are broken by the order in which the Census concordance lists the rows.

Usage:
    python3 src/make_strict_crosswalk.py [--check]

--check compares the result with data/crosswalks/sic_to_gloria_strict.csv and
exits non-zero if they differ.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for config.py
from config import MASTER, STRICT, rel


def build_strict(master_path: Path):
    order = defaultdict(list)
    with open(master_path, newline="") as f:
        for r in csv.DictReader(f):
            order[r["sic_1987"]].append(r["gloria_sector"])
    rows = []
    for sic, cands in order.items():
        counts = Counter(cands)
        best = max(counts.values())
        # first-listed among the tied modal candidates
        primary = next(c for c in cands if counts[c] == best)
        rows.append({"sic_1987": sic,
                     "gloria_sector_primary": primary,
                     "n_candidate_gloria": len(set(cands))})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=None, help="write result here (default: stdout summary only)")
    a = ap.parse_args()

    rows = build_strict(MASTER)
    n = len(rows)
    multi = sum(1 for r in rows if r["n_candidate_gloria"] > 1)
    print(f"SIC codes: {n:,} | map to >1 GLORIA sector: {multi:,} ({100*multi/n:.1f}%)")

    if a.out:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print("wrote", a.out)

    if a.check:
        ref = {r["sic_1987"]: r for r in csv.DictReader(open(STRICT, newline=""))}
        bad = [r["sic_1987"] for r in rows
               if ref.get(r["sic_1987"], {}).get("gloria_sector_primary") != r["gloria_sector_primary"]
               or int(ref.get(r["sic_1987"], {}).get("n_candidate_gloria", -1)) != r["n_candidate_gloria"]]
        if bad or len(ref) != n:
            print(f"MISMATCH with distributed strict file: {len(bad)} codes differ", file=sys.stderr)
            sys.exit(1)
        print(f"check passed: matches {rel(STRICT)}")


if __name__ == "__main__":
    main()
