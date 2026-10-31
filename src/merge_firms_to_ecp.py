#!/usr/bin/env python3
"""Attach an industry-level carbon price to a firm-year panel.

Chain:  SIC 1987 -> NAICS 2002 -> NAICS 2007 -> ISIC Rev.4 -> GLORIA sector -> ecp_edgar
The industry price is Dolphin & Merkle's (2024) emissions-weighted carbon price for
(GLORIA sector x jurisdiction x year), in constant 2021 US$/tCO2e. Coverage 1990-2021.

Two mappings are produced for every firm-year:
    ecp_strict   price of the single (modal) GLORIA sector for the firm's SIC,
                 after the hand overrides in data/crosswalks/strict_overrides.csv
    ecp_min / ecp_max / n_candidates   range across all candidate sectors (broad mapping)
so that a researcher can test how much the one-to-many choice matters.

Input CSV columns (rename with --col-* if different):
    sic   4-digit US SIC (1987 vintage, as in Compustat `sich`/`sic`)
    fic   ISO3 country code
    year  calendar year

No Compustat data is distributed with this repository; examples/demo_firms.csv is synthetic.

Usage:
    python3 src/merge_firms_to_ecp.py examples/demo_firms.csv --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = ROOT / "data" / "crosswalks"


def load(ecp_path):
    cands = defaultdict(set)
    with open(CW / "sic_naics_isic_gloria_master.csv", newline="") as f:
        for r in csv.DictReader(f):
            cands[r["sic_1987"]].add(r["gloria_sector"])
    strict = {r["sic_1987"]: r["gloria_sector_primary"]
              for r in csv.DictReader(open(CW / "sic_to_gloria_strict.csv", newline=""))}
    ov = CW / "strict_overrides.csv"           # hand overrides of the modal rule (see data/README.md)
    if ov.exists():
        for r in csv.DictReader(open(ov, newline="")):
            strict[r["sic_1987"]] = r["gloria_sector_override"]
    fic2reg = {r["fic"]: r["gloria_region"]
               for r in csv.DictReader(open(CW / "gloria_region_to_fic_crosswalk.csv", newline=""))
               if r["fic"] and r["region_type"] != "aggregate"}
    price = {}
    with open(ecp_path, newline="") as f:
        for r in csv.DictReader(f):
            if r["ecp_edgar"] in ("", "NA"):
                continue                                 # sector carries no emissions in this region-year
            price[(r["country"], r["sector"], r["year"])] = float(r["ecp_edgar"])
    return cands, strict, fic2reg, price


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("firms", help="CSV with sic, fic, year columns")
    ap.add_argument("--ecp", default=str(ROOT / "data" / "ecp" / "ecp_gloria_edgar_industry_CO2.csv"))
    ap.add_argument("--out", default=str(ROOT / "output" / "firms_with_ecp.csv"))
    ap.add_argument("--col-sic", default="sic")
    ap.add_argument("--col-fic", default="fic")
    ap.add_argument("--col-year", default="year")
    a = ap.parse_args()

    cands, strict, fic2reg, price = load(a.ecp)
    rows = list(csv.DictReader(open(a.firms, newline="")))
    add = ["gloria_region", "gloria_sector_strict", "n_candidates", "ecp_strict", "ecp_min", "ecp_max", "merge_note"]
    n_ok = 0
    for r in rows:
        sic = str(r[a.col_sic]).zfill(4)
        reg = fic2reg.get(r[a.col_fic], "")
        yr = str(r[a.col_year])
        cs = cands.get(sic, set())
        note = []
        if not reg:
            note.append("no GLORIA region for fic")
        if not cs:
            note.append("SIC not in concordance")
        ps = [price[(reg, c, yr)] for c in cs if (reg, c, yr) in price]
        if cs and reg and not ps:
            note.append("year outside 1990-2021 or sector missing")
        sp = price.get((reg, strict.get(sic, ""), yr))
        r.update({
            "gloria_region": reg,
            "gloria_sector_strict": strict.get(sic, ""),
            "n_candidates": len(cs),
            "ecp_strict": "" if sp is None else sp,
            "ecp_min": min(ps) if ps else "",
            "ecp_max": max(ps) if ps else "",
            "merge_note": "; ".join(note),
        })
        n_ok += sp is not None
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {a.out}: {len(rows)} firm-years, {n_ok} with a strict price")
    for r in rows[:8]:
        print("  ", {k: r[k] for k in [a.col_sic, a.col_fic, a.col_year, "gloria_sector_strict", "ecp_strict", "ecp_min", "ecp_max", "n_candidates"]})


if __name__ == "__main__":
    main()
