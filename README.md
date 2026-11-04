# carbon-pricing-concordance

**From a firm's US SIC code to the carbon price its industry faces.**

A reproducible concordance `SIC 1987 → NAICS 2002 → NAICS 2007 → ISIC Rev. 4 → GLORIA industry → emissions-weighted carbon price`,
plus the diagnostics that show where it is one-to-many and whether that matters.

Built as a research assistant on Professor Anh V. Persson's project on carbon pricing and corporate
investment (University of Illinois, Gies College of Business, May–August 2026). The write-up is
*Measuring Firms' Exposure to Carbon Pricing: An Industry Concordance and Its Limits* (`docs/`).
No firm-level data are included; the project's results are not reported here.

## What is in the box

```
run_all.py         runs every step below in order (see Reproduce)
config.py          every input and output path, relative to the repository root
data/crosswalks/   the concordance tables (distributed; see data/README.md for sources)
data/ecp/          Dolphin & Merkle (2024) price files — download from Zenodo, not distributed
src/               scripts, in the order you would run them
output/            tables and the figure produced by the scripts
examples/          a synthetic firm panel to exercise the merge
docs/              methodology note
```

| Script | What it does |
|---|---|
| `src/verify_crosswalk.py` | Integrity checks: every SIC reaches an ISIC class, every ISIC class a GLORIA industry, every GLORIA name exists in the price file. |
| `src/make_strict_crosswalk.py` | Derives the one-to-one "strict" mapping (modal candidate) from the master table; `--check` confirms it matches the distributed file. |
| `src/concordance_stats.py` | Table 1 (one-to-many codes by SIC division), candidate-count distribution, most ambiguous codes. |
| `src/price_dispersion.py` | For each one-to-many code and each pricing jurisdiction, how far apart the candidate prices are and whether the strict choice flips priced/unpriced. Produces Tables 2–3 and Figure 1. |
| `src/merge_firms_to_ecp.py` | Attaches `ecp_strict`, `ecp_min`, `ecp_max`, `n_candidates` to a firm-year panel with `sic`, `fic`, `year`. |

## Headline numbers (2019, 42 pricing jurisdictions)

- 1,005 SIC codes → 420 ISIC classes → 96 GLORIA industries; all three links verified end to end.
- 342 SIC codes (34%) map to more than one GLORIA industry; 178 of them are in manufacturing.
- For manufacturing codes the choice rarely matters: candidates disagree on whether the firm is priced in 6% of code-jurisdiction pairs, median gap $1.2/t.
- Outside manufacturing it matters: in transport/utilities, wholesale, retail and services the candidates disagree on coverage in 39–46% of pairs, median gap $7–12/t, because the candidates straddle the boundary of the pricing scheme.
- The modal rule is a default, not a recommendation: `data/crosswalks/strict_overrides.csv` lists codes where it is wrong on its face (e.g. SIC 7372 software → "Printing").

## Reproduce

1. Install the pinned dependencies (verified on Python 3.12; the pins need 3.11+):

   ```bash
   pip install -r requirements.txt
   ```

2. Download the ECP file from https://doi.org/10.5281/zenodo.12181508 into `data/ecp/`.
   `data/README.md` gives the version, the exact file names and where they go.

3. Run everything:

   ```bash
   python3 run_all.py
   ```

`run_all.py` checks the Python and package versions and the input files, then runs the
five steps below in order. It prints a start and an end line for each step and stops at
the first failure, naming the step. Without the ECP file, `python3 run_all.py --skip-ecp`
runs the steps that need no downloaded data (Tables 1–3 and checks 1–3).

The steps it runs, which also work one at a time:

```bash
python3 src/verify_crosswalk.py --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv
python3 src/make_strict_crosswalk.py --check
python3 src/concordance_stats.py
python3 src/price_dispersion.py --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv --year 2019 --example-region Germany
python3 src/merge_firms_to_ecp.py examples/demo_firms.csv --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv
```

`pandas` and `matplotlib` are needed only for `price_dispersion.py`. Nothing in the
pipeline is random. File locations are set in `config.py`.

## Sources

- Dolphin, G. and M. Merkle (2024). Emissions-weighted carbon price: sources and methods. *Scientific Data* 11:1017. Data: Zenodo 10.5281/zenodo.12181508.
- US Census Bureau, NAICS concordances (1987 SIC→2002 NAICS; 2002→2007 NAICS; 2007 NAICS→ISIC Rev.4). census.gov/naics/concordances
- UN Statistics Division, ISIC Rev.4 correspondence tables. unstats.un.org/unsd/classifications/Econ
- Lenzen, M. et al. (2017). The Global MRIO Lab. *Economic Systems Research* 29(2).

## License

Code: MIT. Crosswalk tables: derived from public US Census, UNSD and GLORIA classifications; cite the sources above. ECP data: see the Zenodo record's license.

## Author

Xiaoke (Coco) Dai · cocodai2@illinois.edu
