# Data

## `crosswalks/` (distributed)

| File | Rows | What it is |
|---|---|---|
| `sic_naics_isic_gloria_master.csv` | 4,521 | One row per (SIC 1987 × NAICS 2002 × NAICS 2007 × ISIC Rev.4) path, with the GLORIA industry each ISIC class belongs to. 1,005 SIC codes, 420 ISIC classes, 96 GLORIA industries. |
| `sic1987_to_isic4_full.csv` | 4,521 | Same paths without the GLORIA column; `relation` = 1:1 or 1:n at the SIC→ISIC step. |
| `isic4_to_gloria.csv` | 420 | ISIC Rev.4 class → GLORIA industry (by construction: GLORIA is defined on ISIC Rev.4). `gloria_in_file` confirms the name exists in the ECP industry file. |
| `sic_to_gloria_strict.csv` | 1,005 | One GLORIA industry per SIC code: the modal candidate (most ISIC classes), ties broken by Census order. Regenerate with `src/make_strict_crosswalk.py`. |
| `strict_overrides.csv` | 2 | Hand overrides of the modal rule for codes where it is clearly wrong (see the write-up, Table 3). Applied by `merge_firms_to_ecp.py` when present. |
| `gloria_region_to_fic_crosswalk.csv` | 164 | GLORIA region name ↔ ISO3 code, with aggregate regions flagged. |

### How the master table was assembled

The SIC→NAICS→ISIC paths come from three US Census Bureau concordance files
(census.gov/naics/concordances): *1987 SIC to 2002 NAICS*, *2002 NAICS to 2007 NAICS*,
and *2007 NAICS to ISIC Rev. 4* (cross-checked against the UN Statistics Division's
ISIC correspondence tables). The ISIC→GLORIA step uses the GLORIA sector definitions
(Lenzen et al. 2017; GLORIA release notes), with sector names taken verbatim from the
ECP industry file so that the final lookup cannot miss. The assembled table is
distributed here; `src/verify_crosswalk.py` checks its internal consistency and,
given the ECP file, that every GLORIA name resolves.

The 1,005 SIC codes are the 1,004 four-digit codes in the Census table plus the
Census row for auxiliary establishments (`Aux`).

## `ecp/` (not distributed — download)

Dolphin, G. and M. Merkle (2024), *Emissions-weighted Carbon Price*, Scientific Data 11:1017.
Data archive: Zenodo, https://doi.org/10.5281/zenodo.12181508

Place these files in `data/ecp/`:

- `ecp_gloria_edgar_industry_CO2.csv` — industry × GLORIA region × year, 1990–2021 (≈96 MB). Column `ecp_edgar` is the emissions-weighted price in constant 2021 US$/tCO2e; `NA` means the sector has no emissions in that region-year.
- `ecp_CO2.csv` — national/subnational jurisdiction × year, 1990–2022 (≈0.9 MB).

## What is *not* here

No Compustat or other licensed firm data. `examples/demo_firms.csv` is synthetic.
