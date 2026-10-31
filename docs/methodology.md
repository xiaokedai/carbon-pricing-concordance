# Methodology: SIC 1987 → NAICS → ISIC Rev. 4 → GLORIA → emissions-weighted carbon price

*Adapted from the project documentation written in July 2026. The chain ends at the GLORIA industry and reads the price directly from the Dolphin & Merkle industry file; an earlier version that continued to IPCC source categories was dropped in July 2026.*

```
Compustat firm (SIC 1987)
   │  [1] US Census: 1987 SIC → 1997/2002 NAICS
   ▼
NAICS ── [2] Census NAICS revision bridges (1997→2002→2007→2017) ──▶ NAICS 2017
   │  [3] US Census / UNSD: NAICS ↔ ISIC Rev.4
   ▼
ISIC Rev.4
   │  [4] GLORIA MRIO sectoring (ISIC-based) — Lenzen et al. / Global MRIO Lab
   ▼
GLORIA 120 industries
   │  [5] Dolphin & Merkle (2024): industry × jurisdiction × year → ecp_edgar
   ▼
ECP carbon price  (ecp_edgar, 2021 US$/tCO₂e, emissions-weighted)
```

---

## Step 0 — Compustat firm code is US SIC, 1987 vintage

**Source:** S&P Compustat / CRSP documentation (the `sic`/`sich` historical field).
**Logic:** Compustat's 4-digit historical SIC is the firm's *primary* reported activity; by convention
the **1987 US SIC** revision unless the extract states otherwise.
**Reasonableness:** Standard finance-literature assumption; it fixes the `source_vintage` for the whole
chain. A principal SIC is not a firm's full activity portfolio (diversified firms emit outside their
primary code) — verify against the specific extract.

## Step 1 — SIC 1987 → NAICS

**Source:** US Census Bureau, *1987 SIC → 1997 NAICS* concordance
(https://www.census.gov/naics/concordances/).
**Logic:** SIC was retired in 1997 and replaced by NAICS; Census publishes the official correspondence.
**Reasonableness:** Official, government-maintained, canonical.
**One-to-many:** A single SIC can split into several NAICS — kept as candidates with a `relation_type`;
the strict file keeps the primary, the master file keeps all.

## Step 2 — NAICS vintage alignment (1997 → 2002 → 2007 → 2017)

**Source:** US Census Bureau NAICS revision concordances (same page).
**Logic:** NAICS is revised every five years; codes are added, merged, or renumbered. To land on the
vintage used by the NAICS↔ISIC table, the code is walked through each revision.
**Reasonableness:** Prevents the classic silent vintage mismatch. `naics_vintage` recorded at each hop.

## Step 3 — NAICS → ISIC Rev.4

**Source:** US Census *NAICS ↔ ISIC Rev.4* correspondence, cross-checked with UNSD
(https://unstats.un.org/unsd/classifications/Econ).
**Logic:** NAICS is North American; ISIC Rev.4 is the UN international standard and the language
GLORIA/Dolphin speak. This is the point where the chain becomes internationally comparable — exactly
what a 118-country panel needs.
**Reasonableness:** Both endpoints official; UNSD is the authority on ISIC.
**One-to-many:** Frequent; all plausible ISIC matches carried into strict vs broad measures.

## Step 4 — ISIC Rev.4 → GLORIA 120 industries

**Nature of the step:** NOT an external probabilistic concordance — it is **by construction**. GLORIA's
industrial classification is itself based on ISIC Rev.4, so ISIC → GLORIA is an aggregation of ISIC
classes into the 120 GLORIA sectors.
**Sources:**
- GLORIA Technical Documentation (ISIC Rev.4 basis; 120-sector list).
- GLORIA MRIO Release Note (ISA, Univ. of Sydney) — official GLORIA↔ISIC concordance spreadsheet.
- Lenzen, M., et al. (2017). *The Global MRIO Lab.* Economic Systems Research 29(2).
**Reasonableness:** Using GLORIA's own sectoring keeps the mapping consistent with how the ECP data is
built. The 120 GLORIA sector names are taken **verbatim** from `ecp_gloria_edgar_industry_CO2.csv`;
all 96 GLORIA sectors reached by the crosswalk match that file exactly (0 misses).

## Step 5 — GLORIA industry → ECP carbon price (`ecp_edgar`)

**Source:** Dolphin, G. & Merkle, M. (2024), *Emissions-weighted Carbon Price*, **Scientific Data**
11:1017, DOI 10.1038/s41597-024-03121-6; data Zenodo DOI 10.5281/zenodo.12181508 (v1).
File: `ecp_gloria_edgar_industry_CO2.csv`, column `ecp_edgar`.
**Logic:** For each (GLORIA industry × GLORIA region × year), the file gives the emissions-weighted
carbon price applied to that industry in that jurisdiction-year. We read it directly — **no IPCC
routing**. The industry's emissions used for weighting come from EDGAR (columns `co2_edgar_*`), but we
do not need to touch those to obtain the price.
**Reasonableness:** This is the data's own peer-reviewed industry-level price. Taking it directly is
simpler and more transparent than re-deriving an IPCC-sector price, and it is the level the professor
asked for.

**The price is not a property of the SIC code alone:**
> `ecp_edgar` = f(GLORIA industry, country/GLORIA region, year), in **constant 2021 US$/tCO₂e**,
> emissions-weighted. The crosswalk lands a firm on a GLORIA industry; the price is then a lookup by
> (GLORIA industry × country × year).

**Coverage note:** the GLORIA-industry price file spans **1990–2021**. This is **one year shorter** than
the national ECP file (`ecp_CO2.csv`, 1990–2022). For 2022 firm-years there is no industry-level
`ecp_edgar`; use the economy-wide national price as a fallback, or treat 2021 as the last industry year.

---

## Structural cautions carried in the crosswalk

- **Refining (SIC 29 → ISIC 1920 → GLORIA "Refined petroleum products")** is an IPCC **Energy** industry
  (combustion in the energy sector), not manufacturing. Its `ecp_edgar` reflects energy-sector pricing.
- **Wholesale/retail (SIC 50–59 → ISIC 46/47)** is **commercial**, usually outside ETS → typically
  `ecp_edgar` ≈ 0 even in pricing countries (e.g. UK grocery retail 2018 = $0).
- **Mining (SIC 10–14)** emissions are dominated by fugitive **methane**; the ECP is **CO₂-only**, so
  these appear near-zero-priced (understated).
- **Cement / steel / chemicals (32/33/28)** carry **process** emissions separate from combustion; some
  mechanisms exempt process. `ecp_edgar` reflects whatever price actually applies to the industry.
- **One-to-many SIC → industry** remains an open specification choice: **strict** (primary GLORIA) vs
  **broad** (all candidate GLORIA industries).

## Worked examples (2019, `ecp_edgar`, 2021 US$/tCO₂e)

| Firm | SIC | Country | GLORIA industry | ecp_edgar |
|---|---|---|---|---|
| Electric utility | 4911 | Germany | Electric power generation… | ~27.4 |
| Oil refiner | 2911 | Germany | Refined petroleum products | ~25.8 |
| Steel | 3312 | Germany | Basic iron and steel | ~25.8 |
| Railroad | 4011 | Germany | Rail transport | 0 (EU ETS excludes rail) |
| Electric utility | 4911 | USA | Electric power generation… | 0 (no US national ETS) |

## Files this documents

- `SIC_to_ECP_crosswalk_no_IPCC.xlsx` — flat crosswalk (SIC→NAICS→ISIC→GLORIA) + worked examples +
  price sample.
- `ecp_edgar_by_gloria_country_year_ourlist.csv` — full price surface (GLORIA industry × listed country
  × year → `ecp_edgar`), the "→ ECP price" endpoint.
- `merge_firms_to_ecp_no_ipcc.py` — pipeline: firm panel (sic, fic, state, year) → `ecp_edgar`
  (+ economy-wide `ecp_all_jurCO2` for reference). Supersedes `merge_firms_to_ecp.py`.
- `sic_naics_isic_gloria_master.csv` / `sic_to_gloria_strict.csv` — the SIC→…→GLORIA bridges.
- `gloria_region_to_fic_crosswalk.csv` — GLORIA region ↔ jurisdiction (fic).

## Citations

1. US Census Bureau. *NAICS Concordances.* https://www.census.gov/naics/concordances/concordances.html
2. UN Statistics Division. *ISIC Rev.4 and correspondence tables.* https://unstats.un.org/unsd/classifications/Econ
3. Lenzen, M., Geschke, A., et al. *GLORIA / Global MRIO Lab.* Economic Systems Research 29(2), 2017.
4. Dolphin, G. & Merkle, M. (2024). *Emissions-weighted Carbon Price.* Scientific Data 11:1017.
   DOI 10.1038/s41597-024-03121-6. Data: Zenodo 10.5281/zenodo.12181508.
5. Dolphin, G., Xiahou, Q., et al. (2022). *World Carbon Pricing Database.* Scientific Data 9:573.
   DOI 10.1038/s41597-022-01659-x.
