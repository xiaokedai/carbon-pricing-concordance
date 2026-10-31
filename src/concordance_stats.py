#!/usr/bin/env python3
"""Summary statistics for the SIC 1987 -> NAICS -> ISIC Rev.4 -> GLORIA concordance.

Produces, in output/:
    table1_multiplicity_by_division.csv   one-to-many SIC codes by SIC division
    table2_candidate_count_distribution.csv
    table3_most_ambiguous_codes.csv       SIC codes with the most GLORIA candidates
    stats_summary.json                    headline numbers used in the write-up

Usage:
    python3 src/concordance_stats.py
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "crosswalks" / "sic_naics_isic_gloria_master.csv"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# SIC 1987 divisions (Office of Management and Budget, 1987 SIC Manual)
DIVISIONS = [
    (1, 999, "A", "Agriculture, forestry, fishing"),
    (1000, 1499, "B", "Mining"),
    (1500, 1799, "C", "Construction"),
    (2000, 3999, "D", "Manufacturing"),
    (4000, 4999, "E", "Transportation, communications, utilities"),
    (5000, 5199, "F", "Wholesale trade"),
    (5200, 5999, "G", "Retail trade"),
    (6000, 6799, "H", "Finance, insurance, real estate"),
    (7000, 8999, "I", "Services"),
    (9100, 9999, "J", "Public administration"),
]


def division(sic: str):
    if not sic.isdigit():
        return ("—", "Auxiliary establishments (Census 'Aux')")
    c = int(sic)
    for lo, hi, letter, name in DIVISIONS:
        if lo <= c <= hi:
            return (letter, name)
    return ("?", "Unclassified")


def main():
    rows = list(csv.DictReader(open(MASTER, newline="")))
    sic_title = {}
    gl = defaultdict(list)      # sic -> list of gloria sectors (one per ISIC row)
    isic = defaultdict(set)     # sic -> set of ISIC codes
    for r in rows:
        gl[r["sic_1987"]].append(r["gloria_sector"])
        isic[r["sic_1987"]].add(r["isic_rev4"])
        sic_title[r["sic_1987"]] = r["sic_title"]

    n_sic = len(gl)
    n_isic = len({r["isic_rev4"] for r in rows})
    n_gloria = len({r["gloria_sector"] for r in rows})
    multi_gl = {s for s, v in gl.items() if len(set(v)) > 1}
    multi_isic = {s for s, v in isic.items() if len(v) > 1}

    # Table 1: by division
    tot = Counter(division(s) for s in gl)
    mul = Counter(division(s) for s in multi_gl)
    t1 = []
    for d in sorted(tot, key=lambda x: x[0]):
        t1.append({"division": d[0], "name": d[1], "sic_codes": tot[d],
                   "one_to_many": mul[d], "share_one_to_many": round(mul[d] / tot[d], 3)})
    t1.append({"division": "All", "name": "All divisions", "sic_codes": n_sic,
               "one_to_many": len(multi_gl), "share_one_to_many": round(len(multi_gl) / n_sic, 3)})
    _write(OUT / "table1_multiplicity_by_division.csv", t1)

    # Table 2: distribution of candidate counts
    dist = Counter(len(set(v)) for v in gl.values())
    t2 = [{"n_gloria_candidates": k, "sic_codes": dist[k]} for k in sorted(dist)]
    _write(OUT / "table2_candidate_count_distribution.csv", t2)

    # Table 3: most ambiguous codes
    t3 = sorted(({"sic_1987": s, "sic_title": sic_title[s],
                  "n_isic": len(isic[s]), "n_gloria_candidates": len(set(v)),
                  "candidates": "; ".join(sorted(set(v)))}
                 for s, v in gl.items()),
                key=lambda r: (-r["n_gloria_candidates"], r["sic_1987"]))[:25]
    _write(OUT / "table3_most_ambiguous_codes.csv", t3)

    summary = {
        "sic_codes": n_sic,
        "isic_rev4_codes": n_isic,
        "gloria_sectors_reached": n_gloria,
        "sic_one_to_many_isic": len(multi_isic),
        "sic_one_to_many_gloria": len(multi_gl),
        "share_one_to_many_gloria": round(len(multi_gl) / n_sic, 4),
        "max_gloria_candidates": max(len(set(v)) for v in gl.values()),
        "note": "1,005 SIC codes = the 1,004 four-digit codes in the Census 1987 SIC -> NAICS "
                "concordance plus the Census 'Aux' (auxiliary establishments) row.",
    }
    (OUT / "stats_summary.json").write_text(json.dumps(summary, indent=2))
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("\nTable 1 (one-to-many SIC codes by division):")
    for r in t1:
        print(f"  {r['division']:>3} {r['name']:<42} {r['one_to_many']:>4} / {r['sic_codes']:<4} ({100*r['share_one_to_many']:.0f}%)")


def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
