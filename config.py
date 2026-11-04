"""Every file path the pipeline reads or writes, in one place.

Paths are written relative to the repository root and resolved against it, so the
scripts give the same result whatever directory they are started from. To move a
file, change it here; the scripts in src/ and run_all.py read their paths from this
module.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def repo_path(rel: str) -> Path:
    """A location given relative to the repository root."""
    return ROOT / rel


def rel(path: Path) -> str:
    """The repository-relative form of a path from this module, for messages."""
    return Path(path).relative_to(ROOT).as_posix()


# --- Scripts -------------------------------------------------------------------
SRC_DIR = repo_path("src")

# --- Crosswalk tables (distributed with the repository; see data/README.md) -----
MASTER = repo_path("data/crosswalks/sic_naics_isic_gloria_master.csv")
STRICT = repo_path("data/crosswalks/sic_to_gloria_strict.csv")
STRICT_OVERRIDES = repo_path("data/crosswalks/strict_overrides.csv")
REGION_TO_FIC = repo_path("data/crosswalks/gloria_region_to_fic_crosswalk.csv")

# --- Raw data (not distributed: download it, see data/README.md) ------------------
ECP_INDUSTRY = repo_path("data/ecp/ecp_gloria_edgar_industry_CO2.csv")

# --- Example input ------------------------------------------------------------------
DEMO_FIRMS = repo_path("examples/demo_firms.csv")

# --- Outputs --------------------------------------------------------------------------
OUTPUT_DIR = repo_path("output")
TABLE1 = repo_path("output/table1_multiplicity_by_division.csv")
TABLE2 = repo_path("output/table2_candidate_count_distribution.csv")
TABLE3 = repo_path("output/table3_most_ambiguous_codes.csv")
STATS_SUMMARY = repo_path("output/stats_summary.json")
FIRMS_WITH_ECP = repo_path("output/firms_with_ecp.csv")


def table4_path(year: int) -> Path:
    return repo_path(f"output/table4_dispersion_by_jurisdiction_{year}.csv")


def table5_path(year: int) -> Path:
    return repo_path(f"output/table5_dispersion_pooled_{year}.csv")


def table6_path(year: int) -> Path:
    return repo_path(f"output/table6_examples_{year}.csv")


def figure1_path(year: int) -> Path:
    return repo_path(f"output/figure1_price_range_{year}.png")
