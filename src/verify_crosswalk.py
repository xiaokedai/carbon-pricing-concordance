#!/usr/bin/env python3
"""Integrity checks on the distributed crosswalk tables.

Checks:
  1. every SIC 1987 code in the master table reaches at least one ISIC Rev.4 code
  2. every ISIC Rev.4 code in the master table reaches a GLORIA sector
  3. the strict file covers exactly the SIC codes in the master table
  4. (optional, --ecp) every GLORIA sector name used in the crosswalk exists verbatim
     in the Dolphin & Merkle industry file, so the price lookup cannot silently miss

Usage:
    python3 src/verify_crosswalk.py [--ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv]
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = ROOT / "data" / "crosswalks"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecp", default=None)
    a = ap.parse_args()
    fails = 0

    master = list(csv.DictReader(open(CW / "sic_naics_isic_gloria_master.csv", newline="")))
    strict = list(csv.DictReader(open(CW / "sic_to_gloria_strict.csv", newline="")))

    sics = {r["sic_1987"] for r in master}
    no_isic = {r["sic_1987"] for r in master if not r["isic_rev4"]}
    no_gl = {r["isic_rev4"] for r in master if not r["gloria_sector"]}
    print(f"[1] SIC codes: {len(sics)}; without ISIC: {len(no_isic)}", "OK" if not no_isic else "FAIL")
    print(f"[2] ISIC codes: {len({r['isic_rev4'] for r in master})}; without GLORIA: {len(no_gl)}", "OK" if not no_gl else "FAIL")
    fails += bool(no_isic) + bool(no_gl)

    ssics = {r["sic_1987"] for r in strict}
    ok3 = ssics == sics and len(strict) == len(sics)
    print(f"[3] strict file covers master SIC set: {ok3}")
    fails += not ok3

    if a.ecp:
        sectors = set()
        with open(a.ecp, newline="") as f:
            for r in csv.DictReader(f):
                sectors.add(r["sector"])
        used = {r["gloria_sector"] for r in master}
        missing = used - sectors
        print(f"[4] GLORIA sectors used: {len(used)}; in ECP file: {len(sectors)}; missing: {len(missing)}",
              "OK" if not missing else f"FAIL {sorted(missing)[:5]}")
        fails += bool(missing)

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
