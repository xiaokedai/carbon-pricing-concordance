# Data

The pipeline reads two kinds of input:

- **Raw data** (`data/ecp/`): the Dolphin & Merkle (2024) carbon price files. They are
  **not in this repository** (size and licence); download them as described below.
  `.gitignore` keeps them out of git.
- **Crosswalk tables** (`data/crosswalks/`): assembled for this project and distributed
  with the repository. Nothing to download.

Every path the scripts use is set in [`config.py`](../config.py), relative to the
repository root. If you keep the data somewhere else, change it there.

## Raw data: Dolphin & Merkle ECP files (download)

| | |
|---|---|
| Source | Dolphin, G. and M. Merkle (2024), *Emissions-weighted Carbon Price: sources and methods*, Scientific Data 11:1017, DOI 10.1038/s41597-024-03121-6 |
| Archive | Zenodo record 12181508, DOI [10.5281/zenodo.12181508](https://zenodo.org/records/12181508), titled *Emissions-weighted Carbon Price* |
| Version | The record published on 2024-06-20. It has no version label and is the only version of the dataset (concept DOI 10.5281/zenodo.12181507) as of November 2026. If Zenodo later adds a newer version, still take the files from this record: a new release can change the prices and so the results. |
| Licence | CC BY-NC 4.0 |

| File | Expected path | Size (bytes) | MD5 | Used by |
|---|---|---|---|---|
| `ecp_gloria_edgar_industry_CO2.csv` | `data/ecp/ecp_gloria_edgar_industry_CO2.csv` | 96,228,812 | `01f468d20a9203dbf847725291fbf54d` | `verify_crosswalk.py` (check 4), `price_dispersion.py`, `merge_firms_to_ecp.py` |
| `ecp_CO2.csv` | `data/ecp/ecp_CO2.csv` | 852,001 | `027c6607588df23d5b08bd5f1c20fff5` | Not read by the current scripts. It is the economy-wide fallback for 2022 firm-years described in `docs/methodology.md`. |

- `ecp_gloria_edgar_industry_CO2.csv`: GLORIA industry × GLORIA region × year, 1990–2021.
  The scripts read the columns `year`, `country` (GLORIA region name), `sector` (GLORIA
  industry name) and `ecp_edgar` (emissions-weighted price, constant 2021 US$/tCO2e; `NA`
  means the sector has no emissions in that region-year).
- `ecp_CO2.csv`: national/subnational jurisdiction × year, 1990–2022.

The record has four other files (`ecp_gloria_oecd_industry_CO2.csv`,
`ecp_gloria_edgar_finaldem_CO2.csv`, `ecp_gloria_oecd_finaldem_CO2.csv`,
`ecp_sector_CO2.csv`); this project does not use them.

### How to get them

From the repository root:

```bash
mkdir -p data/ecp
```

```bash
curl -L -o data/ecp/ecp_gloria_edgar_industry_CO2.csv "https://zenodo.org/api/records/12181508/files/ecp_gloria_edgar_industry_CO2.csv/content"
```

```bash
curl -L -o data/ecp/ecp_CO2.csv "https://zenodo.org/api/records/12181508/files/ecp_CO2.csv/content"
```

Or download them by hand from the record page, https://zenodo.org/records/12181508, and
move them into `data/ecp/`.

Check the downloads against the MD5 column above (`md5sum data/ecp/*.csv` on Linux,
`md5 data/ecp/*.csv` on macOS). `run_all.py` also checks the industry file before it
starts and stops if it does not match, because a truncated download of a 96 MB file
would otherwise give wrong numbers without any error.

Then run the pipeline:

```bash
python3 run_all.py
```

Without the ECP file, only the steps that need no downloaded data can run:

```bash
python3 run_all.py --skip-ecp
```

## Crosswalk tables: `data/crosswalks/` (distributed)

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

These upstream files are not needed to run the pipeline, and the assembly step is not
part of it:

| Upstream source | Version | Where to get it |
|---|---|---|
| US Census Bureau, 1987 SIC → 2002 NAICS concordance | 1987 SIC, 2002 NAICS | https://www.census.gov/naics/concordances/ |
| US Census Bureau, 2002 NAICS → 2007 NAICS concordance | 2002 → 2007 NAICS | same page |
| US Census Bureau, 2007 NAICS → ISIC Rev. 4 concordance | 2007 NAICS, ISIC Rev. 4 | same page |
| UN Statistics Division, ISIC Rev. 4 correspondence tables (cross-check) | ISIC Rev. 4 | https://unstats.un.org/unsd/classifications/Econ |
| GLORIA sector definitions (Lenzen et al. 2017, *Economic Systems Research* 29(2); GLORIA release notes) | GLORIA 120-sector classification | Global MRIO Lab / ISA, University of Sydney |

The 1,005 SIC codes are the 1,004 four-digit codes in the Census table plus the
Census row for auxiliary establishments (`Aux`).

## What is *not* here

No Compustat or other licensed firm data. `examples/demo_firms.csv` is synthetic.
