#!/usr/bin/env python3
"""How much does the one-to-many choice matter for the carbon price a firm is assigned?

For every SIC code that maps to more than one GLORIA sector, and every jurisdiction
that prices carbon in the chosen year, this script collects the industry-level
emissions-weighted carbon price (ecp_edgar) of each candidate sector and compares
them. The strict (modal) choice is compared with the full candidate set.

Requires the Dolphin & Merkle (2024) industry file, not distributed here:
    ecp_gloria_edgar_industry_CO2.csv   (Zenodo 10.5281/zenodo.12181508)

Outputs, in output/:
    table4_dispersion_by_jurisdiction_<year>.csv
    table5_dispersion_pooled_<year>.csv
    table6_examples_<year>.csv            worked examples for one jurisdiction
    figure1_price_range_<year>.png

Usage:
    python3 src/price_dispersion.py --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv --year 2019 --example-region Germany
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for config.py
from config import (ECP_INDUSTRY, MASTER, OUTPUT_DIR, STRICT, figure1_path, table4_path,
                    table5_path, table6_path)

OUTPUT_DIR.mkdir(exist_ok=True)

EXAMPLE_SICS = ["3312", "1311", "2819", "3499", "2051", "3711", "4213", "7372", "2097"]


def load_crosswalk():
    master = pd.read_csv(MASTER, dtype=str)
    strict = pd.read_csv(STRICT, dtype=str)
    cands = master.groupby("sic_1987")["gloria_sector"].agg(lambda s: sorted(set(s)))
    titles = master.groupby("sic_1987")["sic_title"].first()
    primary = strict.set_index("sic_1987")["gloria_sector_primary"]
    return cands, titles, primary


def sic_division(sic: str) -> str:
    if not sic.isdigit():
        return "Aux"
    c = int(sic)
    bands = [(999, "A Agriculture"), (1499, "B Mining"), (1799, "C Construction"), (3999, "D Manufacturing"),
             (4999, "E Transport/utilities"), (5199, "F Wholesale"), (5999, "G Retail"),
             (6799, "H Finance/real estate"), (8999, "I Services"), (9999, "J Public admin")]
    for hi, name in bands:
        if c <= hi:
            return name
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecp", default=str(ECP_INDUSTRY))
    ap.add_argument("--year", type=int, default=2019)
    ap.add_argument("--example-region", default="Germany")
    ap.add_argument("--priced-threshold", type=float, default=0.0,
                    help="a candidate counts as 'priced' if ecp_edgar > this (US$/tCO2e); default 0")
    a = ap.parse_args()

    cands, titles, primary = load_crosswalk()
    multi = [s for s, c in cands.items() if len(c) > 1]

    # price surface for the year: region x sector -> ecp_edgar
    use = ["year", "country", "sector", "ecp_edgar"]
    ecp = pd.read_csv(a.ecp, usecols=use)
    ecp = ecp[ecp["year"] == a.year]
    ecp = ecp.dropna(subset=["ecp_edgar"])          # sectors with no emissions carry NA, not 0
    price = {(r.country, r.sector): float(r.ecp_edgar) for r in ecp.itertuples(index=False)}
    regions = sorted(ecp["country"].unique())
    pricing = [g for g in regions if any(price.get((g, s), 0) > 0 for s in ecp.loc[ecp.country == g, "sector"])]

    rows = []
    for g in pricing:
        for s in multi:
            ps = [price.get((g, c)) for c in cands[s]]
            ps = [p for p in ps if p is not None]       # drop candidates with no price row (NA)
            if len(ps) < 2:
                continue                                 # choice cannot matter here
            pmin, pmax = min(ps), max(ps)
            strict_p = price.get((g, primary[s]))
            thr = a.priced_threshold
            n_pos = sum(p > thr for p in ps)
            rows.append({
                "jurisdiction": g, "sic_1987": s, "division": sic_division(s),
                "n_candidates": len(ps), "p_min": pmin, "p_max": pmax, "p_range": pmax - pmin,
                "p_strict": strict_p, "n_positive": n_pos,
                "sign_disagree": int(0 < n_pos < len(ps)),
                "any_priced": int(pmax > thr),
                "strict_is_zero_but_other_priced": int(strict_p is not None and strict_p <= thr and pmax > thr),
            })
    df = pd.DataFrame(rows)

    # Table 4: by jurisdiction
    g4 = df.groupby("jurisdiction").agg(
        multi_sic_codes=("sic_1987", "count"),
        share_any_candidate_priced=("any_priced", "mean"),
        share_sign_disagree=("sign_disagree", "mean"),
        share_strict_zero_other_priced=("strict_is_zero_but_other_priced", "mean"),
        median_range_usd=("p_range", "median"),
        p90_range_usd=("p_range", lambda x: x.quantile(0.9)),
    ).reset_index().sort_values("share_sign_disagree", ascending=False)
    g4.round(3).to_csv(table4_path(a.year), index=False)

    # Table 5: pooled over pricing jurisdictions, by SIC division, conditional on any candidate priced
    d = df[df.any_priced == 1]
    g5 = d.groupby("division").agg(
        sic_x_jurisdiction_pairs=("sic_1987", "count"),
        share_sign_disagree=("sign_disagree", "mean"),
        share_strict_zero_other_priced=("strict_is_zero_but_other_priced", "mean"),
        median_range_usd=("p_range", "median"),
        median_range_over_max=("p_range", lambda x: (x / d.loc[x.index, "p_max"]).median()),
    ).reset_index()
    allrow = pd.DataFrame([{
        "division": "All", "sic_x_jurisdiction_pairs": len(d),
        "share_sign_disagree": d.sign_disagree.mean(),
        "share_strict_zero_other_priced": d.strict_is_zero_but_other_priced.mean(),
        "median_range_usd": d.p_range.median(),
        "median_range_over_max": (d.p_range / d.p_max).median(),
    }])
    g5 = pd.concat([g5, allrow]).round(3)
    g5.to_csv(table5_path(a.year), index=False)

    # Table 6: examples in one jurisdiction
    ex = []
    for s in EXAMPLE_SICS:
        if s not in cands.index:
            continue
        for c in cands[s]:
            ex.append({"sic_1987": s, "sic_title": titles[s], "gloria_sector": c,
                       "is_strict_choice": int(c == primary[s]),
                       f"ecp_edgar_{a.example_region}_{a.year}": price.get((a.example_region, c))})
    pd.DataFrame(ex).to_csv(table6_path(a.year), index=False)

    # Figure 1: distribution of the price range across candidates (pairs with any priced candidate)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.5, 3.6))
        ax.hist(d.p_range.clip(upper=40), bins=40, color="#4a6fa5", edgecolor="white")
        ax.set_xlabel(f"Highest minus lowest candidate price, {a.year} (2021 US$/tCO2e, capped at 40)")
        ax.set_ylabel("SIC × jurisdiction pairs")
        ax.set_title("How far apart are the candidate prices for one-to-many SIC codes?", fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        fig.savefig(figure1_path(a.year), dpi=200)
    except Exception as e:  # matplotlib optional
        print("figure skipped:", e)

    print(f"year {a.year}: {len(pricing)} pricing jurisdictions, {len(multi)} one-to-many SIC codes, priced threshold > {a.priced_threshold}")
    print(f"pairs with any candidate priced: {len(d):,} of {len(df):,}")
    print(f"  share with sign disagreement (some candidates priced, some not): {d.sign_disagree.mean():.3f}")
    print(f"  share where strict choice = 0 but another candidate > 0:        {d.strict_is_zero_but_other_priced.mean():.3f}")
    print(f"  median range (US$/t): {d.p_range.median():.2f}; median range/max: {(d.p_range/d.p_max).median():.2f}")
    print("\nTable 5:\n", g5.to_string(index=False))


if __name__ == "__main__":
    main()
