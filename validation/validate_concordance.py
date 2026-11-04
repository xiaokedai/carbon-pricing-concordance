#!/usr/bin/env python3
"""Validation checks on the SIC 1987 -> NAICS -> ISIC Rev.4 -> GLORIA concordance.

Read-only: nothing in data/ or src/ is changed. Writes output/validation_report.md.

Checks
  1. match coverage at each classification level (matched / total), source and target side
  2. weights of one-to-many mappings sum to 1 (tolerance 1e-6)
  3. unmatched codes, listed separately for the source and the target side
  4. duplicate mappings (the same pair of codes more than once)
  5. totals of a key variable are the same before and after mapping

A check that needs data the repository does not have is reported as "无法运行",
with what is missing. These optional inputs make such checks runnable:
  --ecp PATH            Dolphin & Merkle industry file: list of GLORIA sectors and regions
  --universe LEVEL=PATH official code list for a level (sic_1987, naics_2002, naics_2007,
                        isic_rev4, gloria_sector); codes are read from the column named
                        LEVEL, else from the first column. Repeatable.
  --weights PATH        one row per (source code, target code, weight); column names set
                        by --weight-src, --weight-dst, --weight-col
  --values PATH         a quantity by SIC code (e.g. employment, emissions) to test that
                        mapping preserves its total; columns set by --value-key, --value-col

Exit status is 1 if any check fails, 0 otherwise.

Usage:
    python3 validation/validate_concordance.py
    python3 validation/validate_concordance.py --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW = ROOT / "data" / "crosswalks"
OUT = ROOT / "output"

FILES = {
    "master": CW / "sic_naics_isic_gloria_master.csv",
    "full": CW / "sic1987_to_isic4_full.csv",
    "isic2gloria": CW / "isic4_to_gloria.csv",
    "strict": CW / "sic_to_gloria_strict.csv",
    "overrides": CW / "strict_overrides.csv",
    "regions": CW / "gloria_region_to_fic_crosswalk.csv",
}
DEMO = ROOT / "examples" / "demo_firms.csv"
STATS = OUT / "stats_summary.json"
TABLE1 = OUT / "table1_multiplicity_by_division.csv"
TABLE2 = OUT / "table2_candidate_count_distribution.csv"
DEFAULT_ECP = ROOT / "data" / "ecp" / "ecp_gloria_edgar_industry_CO2.csv"

TOL = 1e-6

PASS, FAIL, WARN, SKIP, INFO = "✅ 通过", "❌ 失败", "⚠️ 警告", "⏸ 无法运行", "ℹ️ 信息"
SEVERITY_ORDER = {"高": 0, "中": 1, "低": 2}

CHAIN = ["sic_1987", "naics_2002", "naics_2007", "isic_rev4", "gloria_sector"]
LABEL = {"sic_1987": "SIC 1987", "naics_2002": "NAICS 2002", "naics_2007": "NAICS 2007",
         "isic_rev4": "ISIC Rev.4", "gloria_sector": "GLORIA 部门"}
UNIVERSE_NAME = {"sic_1987": " SIC 1987 官方代码表", "naics_2002": " NAICS 2002 官方代码表",
                 "naics_2007": " NAICS 2007 官方代码表", "isic_rev4": " ISIC Rev.4 官方代码表",
                 "gloria_sector": " GLORIA 部门清单"}

# Published size of each classification. Shown for context only: these numbers are not
# data in this repository, so no pass/fail result uses them as a denominator.
REFERENCE_TOTALS = {
    "sic_1987": (1004, "1987 SIC Manual 的四位行业数（data/README.md 记载 1,004 + Census 'Aux' 行）"),
    "naics_2002": (1179, "US Census 公布的 NAICS 2002 六位行业数"),
    "naics_2007": (1175, "US Census 公布的 NAICS 2007 六位行业数"),
    "isic_rev4": (419, "UNSD 公布的 ISIC Rev.4 class 数"),
    "gloria_sector": (120, "GLORIA 部门数（docs/methodology.md）"),
}

# Reference facts used only to word the report. Nothing here changes a mapping.
ISO3_HINT = {"Niger": "NER", "Nigeria": "NGA"}
ISIC_TITLE_HINT = {
    "6419": "Other monetary intermediation",
    "6619": "Other activities auxiliary to financial service activities",
}

WEIGHT_NAME = re.compile(r"weight|wgt|share|alloc|fraction|prop", re.I)


# ----------------------------------------------------------------------------- helpers

def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha12(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def n(x) -> str:
    return f"{x:,}"


def pct(a, b) -> str:
    return "—" if not b else f"{100 * a / b:.1f}%"


def codes(xs, limit=None) -> str:
    xs = list(xs)
    if not xs:
        return "—"
    shown = xs if limit is None else xs[:limit]
    s = ", ".join(f"`{x}`" for x in shown)
    return s + (f" …（共 {n(len(xs))} 个）" if limit is not None and len(xs) > limit else "")


def cell(x) -> str:
    return str(x).replace("|", "\\|").replace("\n", " ")


def table(headers, rows) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return out


def details(summary, lines) -> list[str]:
    return ["<details>", f"<summary>{summary}</summary>", "", *lines, "", "</details>"]


def is_isic_class(code: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", code))


def modal(cands):
    """The strict rule of src/make_strict_crosswalk.py: most frequent candidate,
    ties broken by first appearance. Returns (choice, tied candidates, counts)."""
    counts = Counter(cands)
    best = max(counts.values())
    tied = [c for c in dict.fromkeys(cands) if counts[c] == best]
    return tied[0], tied, counts


class Report:
    def __init__(self):
        self.lines: list[str] = []
        self.status: dict[int, list[str]] = defaultdict(list)
        self.key: dict[int, str] = {}
        self.anomalies: list[dict] = []
        self.missing: list[tuple[str, str, str]] = []
        self.appendix: list[str] = []

    def add(self, *lines):
        self.lines.extend(lines)

    def mark(self, check: int, status: str) -> str:
        self.status[check].append(status)
        return status

    def worst(self, check: int) -> str:
        for s in (FAIL, WARN, SKIP, PASS):
            if s in self.status[check]:
                return s
        return INFO

    def tally(self, check: int) -> str:
        c = Counter(self.status[check])
        parts = [f"{s.split()[1]} {c[s]}" for s in (PASS, FAIL, WARN, SKIP) if c[s]]
        return " · ".join(parts)

    def anomaly(self, severity, title, what, involved, causes, question):
        self.anomalies.append(dict(severity=severity, title=title, what=what,
                                   involved=involved, causes=causes, question=question))

    def need(self, check, missing, how):
        if (check, missing, how) not in self.missing:
            self.missing.append((check, missing, how))


# ----------------------------------------------------------------------------- data

class Data:
    def __init__(self, a):
        self.master = read_csv(FILES["master"])
        self.full = read_csv(FILES["full"])
        self.isic2gl = read_csv(FILES["isic2gloria"])
        self.strict = read_csv(FILES["strict"])
        self.overrides = read_csv(FILES["overrides"]) if FILES["overrides"].exists() else []
        self.regions = read_csv(FILES["regions"])
        self.demo = read_csv(DEMO) if DEMO.exists() else None

        self.rows_by_sic = defaultdict(list)          # sic -> master rows, in file order
        for r in self.master:
            self.rows_by_sic[r["sic_1987"]].append(r)
        self.sic_title = {s: rs[0]["sic_title"] for s, rs in self.rows_by_sic.items()}
        self.cands = {s: sorted({r["gloria_sector"] for r in rs}) for s, rs in self.rows_by_sic.items()}
        self.reached = {lv: {r[lv] for r in self.master if r[lv]} for lv in CHAIN}

        self.strict_map = {r["sic_1987"]: r["gloria_sector_primary"] for r in self.strict}
        self.strict_final = dict(self.strict_map)
        for r in self.overrides:
            self.strict_final[r["sic_1987"]] = r["gloria_sector_override"]
        self.overridden = {r["sic_1987"] for r in self.overrides}

        # fic -> region exactly as src/merge_firms_to_ecp.py builds it (a later row wins)
        self.fic2reg = {r["fic"]: r["gloria_region"] for r in self.regions
                        if r["fic"] and r["region_type"] != "aggregate"}

        self.ecp_path = Path(a.ecp) if a.ecp else DEFAULT_ECP
        self.ecp_sectors = self.ecp_regions = None
        if self.ecp_path.exists():
            self.ecp_sectors, self.ecp_regions = set(), set()
            with open(self.ecp_path, newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    self.ecp_sectors.add(r["sector"])
                    self.ecp_regions.add(r["country"])

        self.universe: dict[str, set] = {}
        self.universe_src: dict[str, str] = {}
        for spec in a.universe or []:
            level, _, path = spec.partition("=")
            if level not in CHAIN or not path:
                sys.exit(f"--universe expects LEVEL=PATH with LEVEL in {CHAIN}; got {spec!r}")
            rows = read_csv(Path(path))
            col = level if level in rows[0] else next(iter(rows[0]))
            self.universe[level] = {r[col].strip() for r in rows if r[col].strip()}
            self.universe_src[level] = path
        if "gloria_sector" not in self.universe and self.ecp_sectors is not None:
            self.universe["gloria_sector"] = self.ecp_sectors
            self.universe_src["gloria_sector"] = str(self.ecp_path.relative_to(ROOT)) \
                if self.ecp_path.is_relative_to(ROOT) else str(self.ecp_path)

        self.weights = None
        if a.weights:
            self.weights = read_csv(Path(a.weights))
            for c in (a.weight_src, a.weight_dst, a.weight_col):
                if c not in self.weights[0]:
                    sys.exit(f"--weights file has no column {c!r}")
        self.values = None
        if a.values:
            self.values = read_csv(Path(a.values))
            for c in (a.value_key, a.value_col):
                if c not in self.values[0]:
                    sys.exit(f"--values file has no column {c!r}")


# ----------------------------------------------------------------------------- check 1

def check_coverage(d: Data, R: Report):
    C = 1
    R.add("## 1. 各分类层级的匹配覆盖率", "",
          "覆盖率 = 能连到下一层（源端）或被上一层映射到（目标端）的代码数 / 该层代码总数。"
          "master 是路径表（每行一条 SIC → NAICS 2002 → NAICS 2007 → ISIC → GLORIA 路径），"
          "源端分母取该层在仓库文件里出现的全部代码；目标端分母需要官方代码表。", "")

    # 1a source side
    rows = []
    for a, b in zip(CHAIN, CHAIN[1:]):
        src = {r[a] for r in d.master if r[a]}
        ok = {r[a] for r in d.master if r[a] and r[b]}
        blank_src = sum(1 for r in d.master if not r[a])
        st = R.mark(C, PASS if len(ok) == len(src) and not blank_src else FAIL)
        note = f"{blank_src} 行源码为空" if blank_src else ""
        rows.append([f"{LABEL[a]} → {LABEL[b]}（master）", n(len(src)), n(len(ok)), pct(len(ok), len(src)), st, note])
    ig_ok = sum(1 for r in d.isic2gl if r["gloria_sector"])
    rows.append(["ISIC Rev.4 → GLORIA 部门（isic4_to_gloria.csv）", n(len(d.isic2gl)), n(ig_ok),
                 pct(ig_ok, len(d.isic2gl)), R.mark(C, PASS if ig_ok == len(d.isic2gl) else FAIL), ""])
    sics = set(d.rows_by_sic)
    e2e = {s for s, rs in d.rows_by_sic.items() if any(r["gloria_sector"] for r in rs)}
    rows.append(["SIC 1987 → GLORIA 部门（端到端）", n(len(sics)), n(len(e2e)), pct(len(e2e), len(sics)),
                 R.mark(C, PASS if e2e == sics else FAIL), ""])
    st_ok = {s for s in sics if d.strict_map.get(s)}
    rows.append(["SIC 1987 → strict GLORIA（sic_to_gloria_strict.csv）", n(len(sics)), n(len(st_ok)),
                 pct(len(st_ok), len(sics)), R.mark(C, PASS if st_ok == sics else FAIL), ""])
    used = d.reached["gloria_sector"]
    if d.ecp_sectors is not None:
        hit = used & d.ecp_sectors
        rows.append(["GLORIA 部门 → ECP 价格文件（sector 名称）", n(len(used)), n(len(hit)), pct(len(hit), len(used)),
                     R.mark(C, PASS if hit == used else FAIL), ""])
    else:
        recorded = sum(1 for r in d.isic2gl if r["gloria_in_file"] == "yes")
        rows.append(["GLORIA 部门 → ECP 价格文件（sector 名称）", n(len(used)), "—", "—", R.mark(C, SKIP),
                     f"缺 ECP 文件。isic4_to_gloria.csv 的 gloria_in_file 列记录 {recorded}/{len(d.isic2gl)} 为 yes（构建时记录，本次未复核）"])
        R.need("1、3", "`data/ecp/ecp_gloria_edgar_industry_CO2.csv`（Dolphin & Merkle 2024，Zenodo 10.5281/zenodo.12181508）",
               "用 `--ecp` 指定；可复核 GLORIA 部门名、列出未被映射的 GLORIA 部门和地区名")
    numeric = sum(1 for s in sics if s.isdigit() and len(s) == 4)
    ref = REFERENCE_TOTALS["sic_1987"][0]
    rows.append(["SIC 1987 起点完整性（与文档数量比）", n(ref) + " + Aux", n(numeric) + (" + Aux" if "Aux" in sics else ""),
                 pct(numeric, ref), R.mark(C, PASS if numeric == ref else WARN),
                 "只比数量，未与官方代码表逐个核对" if "sic_1987" not in d.universe else ""])
    R.add("### 1a 源端：每层代码能否连到下一层", "",
          *table(["环节", "总数", "匹配数", "覆盖率", "结果", "说明"], rows), "")

    # 1b target side
    rows = []
    for lv in CHAIN[1:]:
        got = d.reached[lv]
        ref_n, ref_src = REFERENCE_TOTALS[lv]
        if lv in d.universe:
            uni = d.universe[lv]
            hit, extra = got & uni, got - uni
            st = FAIL if extra else (PASS if hit == uni else WARN)
            note = f"代码表：{d.universe_src[lv]}"
            if extra:
                note += f"；crosswalk 中有 {len(extra)} 个代码不在代码表里：{codes(sorted(extra), 10)}"
            rows.append([LABEL[lv], n(len(hit)), n(len(uni)), pct(len(hit), len(uni)), R.mark(C, st), note])
        else:
            note = f"仓库里没有{UNIVERSE_NAME[lv]}。参考：{ref_src}为 {n(ref_n)}，本 crosswalk 用到 {n(len(got))} 个"
            usable = len(got)
            if lv == "isic_rev4":
                bad = sorted(c for c in got if not is_isic_class(c))
                usable -= len(bad)
                note += f"，其中 {len(bad)} 个不是标准 4 位码（{codes(bad)}），参考覆盖率按 {n(usable)} 个标准码计"
            rows.append([LABEL[lv], n(len(got)), "—", f"—（参考约 {pct(min(usable, ref_n), ref_n)}）", R.mark(C, SKIP), note])
            what = {"naics_2002": "US Census NAICS 2002 六位代码表",
                    "naics_2007": "US Census NAICS 2007 六位代码表",
                    "isic_rev4": "UNSD ISIC Rev.4 class 代码表（419 个）",
                    "gloria_sector": "GLORIA 120 个部门名称（ECP 文件的 sector 列即可）"}[lv]
            how = f"用 `--universe {lv}=PATH` 指定" + ("，或给 `--ecp`" if lv == "gloria_sector" else "")
            R.need("1、3", what, how)
    isic = d.reached["isic_rev4"]
    std = sum(1 for c in isic if is_isic_class(c))
    rows.append(["ISIC Rev.4 代码格式（4 位数字）", n(std), n(len(isic)), pct(std, len(isic)),
                 R.mark(C, PASS if std == len(isic) else WARN), "见「需要 Coco 判断」" if std < len(isic) else ""])
    finer = [r for r in d.isic2gl if r["relation"].startswith("1:n")]
    rows.append(["ISIC → GLORIA 粒度（GLORIA 不比 ISIC 细）", n(len(d.isic2gl) - len(finer)), n(len(d.isic2gl)),
                 pct(len(d.isic2gl) - len(finer), len(d.isic2gl)), R.mark(C, WARN if finer else PASS),
                 f"{len(finer)} 个 ISIC class 标注 1:n(GLORIA finer)，更细的 GLORIA 部门到不了；见「需要 Coco 判断」" if finer else ""])
    R.add("### 1b 目标端：目标分类有多少被映射到", "",
          *table(["层级", "被映射到", "总数", "覆盖率", "结果", "说明"], rows), "")

    # 1c regions
    rows = []
    regs = d.regions
    with_fic = [r for r in regs if r["fic"]]
    no_fic_non_agg = [r for r in regs if not r["fic"] and r["region_type"] != "aggregate"]
    rows.append(["GLORIA 地区 → fic", n(len(regs)), n(len(with_fic)), pct(len(with_fic), len(regs)),
                 R.mark(C, FAIL if no_fic_non_agg else PASS),
                 f"{len(regs) - len(with_fic)} 个无 fic，均为汇总地区（预期如此）" if not no_fic_non_agg else
                 f"{len(no_fic_non_agg)} 个非汇总地区无 fic"])
    reachable = set(d.fic2reg.values())

    def unreachable_note(rs):
        lost = [r for r in rs if r["gloria_region"] not in reachable]
        why = lambda r: f"fic {r['fic']} 被另一地区占用，见第 4 项" if r["fic"] else "无 fic"
        return "查不到：" + "；".join(f"{r['gloria_region']}（{why(r)}）" for r in lost) if lost else ""

    non_agg = [r for r in regs if r["region_type"] != "aggregate"]
    ok = [r for r in non_agg if r["gloria_region"] in reachable]
    rows.append(["非汇总地区可按 fic 查到（merge 的查法）", n(len(non_agg)), n(len(ok)), pct(len(ok), len(non_agg)),
                 R.mark(C, PASS if len(ok) == len(non_agg) else FAIL), unreachable_note(non_agg)])
    ours = [r for r in regs if r["in_our_list"] == "yes"]
    ok2 = [r for r in ours if r["gloria_region"] in reachable]
    rows.append(["清单内地区（in_our_list=yes）可按 fic 查到", n(len(ours)), n(len(ok2)), pct(len(ok2), len(ours)),
                 R.mark(C, PASS if len(ok2) == len(ours) else FAIL), unreachable_note(ours)])
    if d.ecp_regions is not None:
        names = {r["gloria_region"] for r in regs}
        hit = names & d.ecp_regions
        rows.append(["地区表的地区名 → ECP 文件 country", n(len(names)), n(len(hit)), pct(len(hit), len(names)),
                     R.mark(C, PASS if hit == names else FAIL), ""])
    else:
        rows.append(["地区表的地区名 → ECP 文件 country", n(len(regs)), "—", "—", R.mark(C, SKIP), "缺 ECP 文件"])
    R.add("### 1c 地区维度（gloria_region_to_fic_crosswalk.csv）", "",
          *table(["环节", "总数", "匹配数", "覆盖率", "结果", "说明"], rows), "")

    # 1d demo panel
    if d.demo is not None:
        rows = []
        dem = d.demo
        sic_ok = [r for r in dem if str(r["sic"]).zfill(4) in d.rows_by_sic]
        fic_ok = [r for r in dem if r["fic"] in d.fic2reg]
        st_ok = [r for r in dem if d.strict_final.get(str(r["sic"]).zfill(4))]
        for name, k in (("SIC → concordance", sic_ok), ("fic → GLORIA 地区", fic_ok), ("SIC → strict GLORIA 部门", st_ok)):
            rows.append([name, n(len(dem)), n(len(k)), pct(len(k), len(dem)), R.mark(C, PASS if len(k) == len(dem) else FAIL), ""])
        rows.append(["(地区, 部门, 年份) → ecp_edgar", n(len(dem)), "—", "—", R.mark(C, SKIP), "缺 ECP 文件"])
        R.add("### 1d 示例 firm panel（examples/demo_firms.csv，合成数据）", "",
              *table(["环节", "firm-year 数", "匹配数", "覆盖率", "结果", "说明"], rows), "")

    R.key[C] = (f"源端各环节{'均为 100%' if len(e2e) == len(sics) else '有缺口'}（SIC {n(len(e2e))}/{n(len(sics))} 到 GLORIA）；"
                f"清单内地区 {len(ok2)}/{len(ours)} 可按 fic 查到；目标端缺官方代码表")


# ----------------------------------------------------------------------------- check 2

def check_weights(d: Data, R: Report, a):
    C = 2
    R.add("## 2. 一对多映射的权重之和是否等于 1（容差 1e-6）", "")
    cols = {k: list(read_csv(p)[0].keys()) for k, p in FILES.items() if p.exists()}
    weight_cols = {k: [c for c in cs if WEIGHT_NAME.search(c)] for k, cs in cols.items()}
    found = {k: v for k, v in weight_cols.items() if v}
    n_cols = sum(len(v) for v in cols.values())

    rows = []
    if found:
        rows.append(["映射表中的权重列", R.mark(C, INFO),
                     "找到疑似权重列：" + "; ".join(f"{k}: {', '.join(v)}" for k, v in found.items()) +
                     "。本脚本不猜测其含义，请用 --weights 指定"])
    else:
        rows.append(["映射表中的权重列", R.mark(C, SKIP),
                     f"{len(cols)} 个 crosswalk 文件、共 {n_cols} 列，没有任何权重/份额列"])
    if d.weights is None:
        rows.append(["外部权重文件（--weights）", R.mark(C, SKIP), "未提供"])
        R.need("2、5", "一对多链接的权重（每个源代码一组、和为 1 的份额，例如按就业或产值）",
               "用 `--weights PATH` 指定，列名用 `--weight-src/--weight-dst/--weight-col` 设置。"
               "可能来源：Census 1997 Economic Census 的 NAICS–SIC bridge 表（按机构数、销售额、就业给出份额）")
    R.add(*table(["项目", "结果", "数字"], rows), "")

    # which links would need weights
    def one_to_many(a_, b_):
        m = defaultdict(set)
        for r in d.master:
            m[r[a_]].add(r[b_])
        return sum(1 for v in m.values() if len(v) > 1), len(m)
    rows = []
    for a_, b_ in list(zip(CHAIN, CHAIN[1:])) + [("sic_1987", "isic_rev4"), ("sic_1987", "gloria_sector")]:
        k, tot = one_to_many(a_, b_)
        rows.append([f"{LABEL[a_]} → {LABEL[b_]}" + ("（端到端）" if a_ == "sic_1987" and b_ != "naics_2002" else ""),
                     n(k), n(tot), pct(k, tot)])
    R.add("需要权重的一对多链接（仓库里这些链接都没有权重）：", "",
          *table(["环节", "一对多的源代码", "源代码总数", "占比"], rows), "")

    ties = [s for s, rs in d.rows_by_sic.items() if len(modal([r["gloria_sector"] for r in rs])[1]) > 1]
    multi = sum(1 for c in d.cands.values() if len(c) > 1)
    R.add("现有管线怎样处理一对多：strict 映射把权重 1 放在众数候选上（和为 1，不需要检验）；"
          "broad 映射（`merge_firms_to_ecp.py` 的 `ecp_min`/`ecp_max`）只取候选价格的区间，不加权。"
          "如果把 strict 规则的计数看成隐含权重（每个候选的路径数 / 该 SIC 的路径总数），"
          "它们按构造和为 1，所以这项检验对现有数据没有信息量。", "",
          f"另外：{n(multi)} 个一对多 SIC 中，有 {n(len(ties))} 个的众数候选并列，strict 选择实际由 Census 表的排列顺序决定"
          f"（见「需要 Coco 判断」）。", "")

    if d.weights is not None:
        src, dst, wc = a.weight_src, a.weight_dst, a.weight_col
        sums, bad_val, neg, gt1 = defaultdict(float), [], [], []
        pairs = set()
        for r in d.weights:
            try:
                w = float(r[wc])
            except ValueError:
                bad_val.append(r[src]); continue
            sums[r[src]] += w
            pairs.add((r[src], r[dst]))
            if w < -TOL:
                neg.append(r[src])
            if w > 1 + TOL:
                gt1.append(r[src])
        off = sorted((s for s, v in sums.items() if abs(v - 1) > TOL))
        rows = [["权重之和 = 1 ± 1e-6", R.mark(C, PASS if not off else FAIL),
                 f"{n(len(sums) - len(off))}/{n(len(sums))} 个源代码通过" + (f"；不通过：{codes(off, 20)}" if off else "")],
                ["权重为负", R.mark(C, PASS if not neg else FAIL), codes(sorted(set(neg)), 20) if neg else "0"],
                ["单个权重 > 1", R.mark(C, PASS if not gt1 else FAIL), codes(sorted(set(gt1)), 20) if gt1 else "0"],
                ["权重无法解析为数字", R.mark(C, PASS if not bad_val else FAIL), codes(sorted(set(bad_val)), 20) if bad_val else "0"]]
        if src in CHAIN and dst in CHAIN:
            known = {(r[src], r[dst]) for r in d.master}
            stray = sorted(pairs - known)
            m = defaultdict(set)
            for s_, t_ in known:
                m[s_].add(t_)
            need = {s_ for s_, v in m.items() if len(v) > 1}
            lacking = sorted(need - set(sums))
            rows.append(["权重中的代码对不在 concordance 里", R.mark(C, PASS if not stray else FAIL),
                         f"{len(stray)} 对" + (f"：{codes([f'{x}→{y}' for x, y in stray], 10)}" if stray else "")])
            rows.append(["一对多的源代码缺权重", R.mark(C, PASS if not lacking else FAIL),
                         f"{len(lacking)}/{len(need)}" + (f"：{codes(lacking, 20)}" if lacking else "")])
        R.add(f"外部权重文件检查（{a.weights}，{src} → {dst}，列 {wc}）：", "",
              *table(["项目", "结果", "数字"], rows), "")
        if off:
            R.anomaly("高", "权重之和不等于 1", f"{len(off)} 个源代码的权重之和偏离 1 超过 1e-6。",
                      [codes(off, 50)], ["权重可能在别的层级上归一化，或漏了某些目标代码。"],
                      "这些代码的权重应如何补齐或重新归一化？")

    R.key[C] = (f"映射表没有权重列{'；未提供 --weights' if d.weights is None else ''}；"
                f"{n(multi)} 个 SIC 一对多（GLORIA），其中 {n(len(ties))} 个 strict 选择靠排列顺序")


# ----------------------------------------------------------------------------- check 3

def check_unmatched(d: Data, R: Report):
    C = 3
    R.add("## 3. 没有匹配上的代码", "")
    rows = []
    for a_, b_ in zip(CHAIN, CHAIN[1:]):
        src = {r[a_] for r in d.master if r[a_]}
        miss = sorted(src - {r[a_] for r in d.master if r[a_] and r[b_]})
        rows.append([f"{LABEL[a_]} 连不到 {LABEL[b_]}（master）", n(len(miss)), codes(miss, 30),
                     R.mark(C, PASS if not miss else FAIL)])
    miss = sorted(r["isic_rev4"] for r in d.isic2gl if not r["gloria_sector"])
    rows.append(["ISIC 无 GLORIA 部门（isic4_to_gloria.csv）", n(len(miss)), codes(miss, 30), R.mark(C, PASS if not miss else FAIL)])
    miss = sorted(d.reached["isic_rev4"] - {r["isic_rev4"] for r in d.isic2gl})
    rows.append(["master 的 ISIC 不在 isic4_to_gloria.csv", n(len(miss)), codes(miss, 30), R.mark(C, PASS if not miss else FAIL)])
    miss = sorted(set(d.rows_by_sic) - set(d.strict_map))
    rows.append(["master 的 SIC 不在 strict 文件", n(len(miss)), codes(miss, 30), R.mark(C, PASS if not miss else FAIL)])
    miss = sorted(r["sic_1987"] for r in d.overrides if r["sic_1987"] not in d.rows_by_sic)
    rows.append(["override 的 SIC 不在 master", n(len(miss)), codes(miss), R.mark(C, PASS if not miss else FAIL)])
    if d.ecp_sectors is not None:
        miss = sorted(d.reached["gloria_sector"] - d.ecp_sectors)
        rows.append(["GLORIA 部门名不在 ECP 文件", n(len(miss)), codes(miss), R.mark(C, PASS if not miss else FAIL)])
    else:
        rows.append(["GLORIA 部门名不在 ECP 文件", "—", "缺 ECP 文件", R.mark(C, SKIP)])
    if d.demo is not None:
        miss = sorted({str(r["sic"]).zfill(4) for r in d.demo if str(r["sic"]).zfill(4) not in d.rows_by_sic})
        rows.append(["示例 panel 的 SIC 不在 concordance", n(len(miss)), codes(miss), R.mark(C, PASS if not miss else FAIL)])
        miss = sorted({r["fic"] for r in d.demo if r["fic"] not in d.fic2reg})
        rows.append(["示例 panel 的 fic 查不到 GLORIA 地区", n(len(miss)), codes(miss), R.mark(C, PASS if not miss else FAIL)])
    src_missing = sum(int(r[1].replace(",", "")) for r in rows if r[1] != "—")
    R.add("### 3a 源端", "", *table(["源端", "未匹配数", "代码", "结果"], rows), "")

    rows = []
    for lv in CHAIN[1:]:
        if lv in d.universe:
            miss = sorted(d.universe[lv] - d.reached[lv])
            extra = sorted(d.reached[lv] - d.universe[lv])
            rows.append([f"{LABEL[lv]}：代码表中未被映射到", n(len(miss)), codes(miss, 40), R.mark(C, PASS if not miss else WARN)])
            rows.append([f"{LABEL[lv]}：crosswalk 中不在代码表里的代码", n(len(extra)), codes(extra, 40), R.mark(C, PASS if not extra else FAIL)])
        else:
            rows.append([f"{LABEL[lv]}中未被映射到的代码", "—", f"缺{UNIVERSE_NAME[lv]}", R.mark(C, SKIP)])
    miss = sorted({r["isic_rev4"] for r in d.isic2gl} - d.reached["isic_rev4"])
    rows.append(["isic4_to_gloria.csv 中未被任何 SIC 到达的 ISIC", n(len(miss)), codes(miss, 30) +
                 ("（注意：此表的 ISIC 集合与 master 完全相同，这一项不能代替官方代码表）" if not miss else ""),
                 R.mark(C, PASS if not miss else WARN)])
    agg = [r["gloria_region"] for r in d.regions if not r["fic"] and r["region_type"] == "aggregate"]
    rows.append(["无 fic 的汇总地区", n(len(agg)), ", ".join(agg) or "—", R.mark(C, INFO)])
    reachable = set(d.fic2reg.values())
    shadow = [r for r in d.regions if r["region_type"] != "aggregate" and r["gloria_region"] not in reachable]
    rows.append(["非汇总地区按 fic 查不到", n(len(shadow)),
                 "; ".join(f"{r['gloria_region']}（fic={r['fic'] or '空'}，in_our_list={r['in_our_list']}）" for r in shadow) or "—",
                 R.mark(C, PASS if not shadow else FAIL)])
    if d.ecp_regions is not None:
        miss = sorted(d.ecp_regions - {r["gloria_region"] for r in d.regions})
        rows.append(["ECP 文件中的地区不在地区表", n(len(miss)), ", ".join(miss) or "—", R.mark(C, PASS if not miss else WARN)])
    else:
        rows.append(["ECP 文件中的地区不在地区表", "—", "缺 ECP 文件", R.mark(C, SKIP)])
    R.add("### 3b 目标端", "", *table(["目标端", "未匹配数", "代码", "结果"], rows), "")

    R.key[C] = (f"源端 {n(src_missing)} 个未匹配代码；{len(shadow)} 个非汇总地区按 fic 查不到"
                f"{'（' + '、'.join(r['gloria_region'] for r in shadow) + '）' if shadow else ''}；目标端清单缺官方代码表")


# ----------------------------------------------------------------------------- check 4

def check_duplicates(d: Data, R: Report):
    C = 4
    R.add("## 4. 重复映射（同一对代码出现多次）", "",
          "master 是路径表，单个环节的代码对（例如 SIC→NAICS 2002）在路径分叉时本来就会重复，所以这里检查的是："
          "完整路径和整行是否重复、每张一对一查找表的键是否重复，以及端点代码对 (SIC, ISIC) 是否因经过不同 NAICS 而重复出现。", "")
    rows = []
    hard_dups = 0          # whole-row, full-path and lookup-key duplicates
    path_key = ["sic_1987", "naics_2002", "naics_2007", "isic_rev4"]

    def dup_count(rs, key):
        c = Counter(tuple(r[k] for k in key) for r in rs)
        return sum(v - 1 for v in c.values() if v > 1), [k for k, v in c.items() if v > 1]

    for name, rs in (("sic_naics_isic_gloria_master.csv", d.master), ("sic1987_to_isic4_full.csv", d.full)):
        k, ex = dup_count(rs, list(rs[0].keys()))
        hard_dups += k
        rows.append([name, "整行", n(len(rs)), n(k), codes(["/".join(x[:4]) for x in ex], 10), R.mark(C, PASS if not k else FAIL)])
        k, ex = dup_count(rs, path_key)
        hard_dups += k
        rows.append([name, "完整路径 (SIC, NAICS02, NAICS07, ISIC)", n(len(rs)), n(k), codes(["/".join(x) for x in ex], 10),
                     R.mark(C, PASS if not k else FAIL)])
    for name, rs, key in (("isic4_to_gloria.csv", d.isic2gl, ["isic_rev4"]),
                          ("sic_to_gloria_strict.csv", d.strict, ["sic_1987"]),
                          ("strict_overrides.csv", d.overrides, ["sic_1987"]),
                          ("gloria_region_to_fic_crosswalk.csv", d.regions, ["gloria_region"])):
        if not rs:
            continue
        k, ex = dup_count(rs, key)
        hard_dups += k
        rows.append([name, key[0], n(len(rs)), n(k), codes([x[0] for x in ex]), R.mark(C, PASS if not k else FAIL)])
    k, ex = dup_count([r for r in d.regions if r["fic"]], ["fic"])
    rows.append(["gloria_region_to_fic_crosswalk.csv", "fic（非空）", n(sum(1 for r in d.regions if r["fic"])), n(k),
                 codes(sorted(x[0] for x in ex)), R.mark(C, PASS if not k else FAIL)])
    k, ex = dup_count(d.isic2gl, ["isic_title"])
    rows.append(["isic4_to_gloria.csv", "isic_title（不同代码同一标题）", n(len(d.isic2gl)), n(k),
                 "; ".join(x[0] for x in ex) or "—", R.mark(C, PASS if not k else WARN)])

    pair = Counter((r["sic_1987"], r["isic_rev4"]) for r in d.master)
    rep = {p: v for p, v in pair.items() if v > 1}
    extra = sum(v - 1 for v in rep.values())
    rows.append(["sic_naics_isic_gloria_master.csv", "端点对 (SIC, ISIC)", n(len(pair)) + " 对", f"{n(len(rep))} 对重复（多出 {n(extra)} 行）",
                 "同一 ISIC 经由不同 NAICS 码到达", R.mark(C, WARN if rep else PASS)])
    gp = Counter((r["sic_1987"], r["gloria_sector"]) for r in d.master)
    rows.append(["sic_naics_isic_gloria_master.csv", "端点对 (SIC, GLORIA)", n(len(gp)) + " 对",
                 f"{n(sum(1 for v in gp.values() if v > 1))} 对出现多于 1 行", "多个 ISIC/路径汇入同一 GLORIA 部门，是 strict 规则计数的来源", R.mark(C, INFO)])
    R.add(*table(["文件", "键", "行数", "重复数", "例子", "结果"], rows), "")
    if rep:
        R.add("(SIC, ISIC) 重复本身是路径表的结构，但它会影响 strict 规则：`make_strict_crosswalk.py` 按行计数，"
              "一个 ISIC class 经过几个 NAICS 码就被数几次。影响见「需要 Coco 判断」。", "")

    fic_dup = [f for f, v in Counter(r["fic"] for r in d.regions if r["fic"]).items() if v > 1]
    R.key[C] = (f"整行、完整路径和各表主键{'无重复' if not hard_dups else f'有 {n(hard_dups)} 处重复'}；fic 重复 {len(fic_dup)} 个{'（' + '、'.join(sorted(fic_dup)) + '）' if fic_dup else ''}；"
                f"(SIC, ISIC) 对重复 {n(len(rep))} 个")


# ----------------------------------------------------------------------------- check 5

def check_conservation(d: Data, R: Report, a):
    C = 5
    R.add("## 5. 映射前后关键变量的总量是否守恒", "")
    sics = set(d.rows_by_sic)
    multi = sum(1 for c in d.cands.values() if len(c) > 1)
    pairs = sum(len(c) for c in d.cands.values())

    # 5a: a quantity by SIC code
    R.add("### 5a 数量变量的守恒", "")
    if d.values is None:
        R.add(*table(["项目", "结果", "说明"], [
            ["数量变量按 strict 映射后总量不变", R.mark(C, SKIP), "仓库里没有任何 SIC 层面的数量变量（就业、产值、排放等）；示例 panel 只有 sic、fic、year"],
            ["数量变量按加权 broad 映射后总量不变", R.mark(C, SKIP), "同上，且一对多链接没有权重（见第 2 项）"],
        ]), "")
        R.add(f"ECP 价格（`ecp_edgar`）是价格，不能加总，所以不适用总量守恒。如果不加权地把一个 SIC 的数量全额分给每个候选部门，"
              f"总量会被放大到 {pairs / len(sics):.3f} 倍（{n(pairs)} 个 SIC–GLORIA 对 / {n(len(sics))} 个 SIC）——这就是做数量分配必须有权重的原因。", "")
        R.need("5", "一个按 SIC（或按 firm）给出的数量变量，例如 Compustat 的 emp/sale，或 Census 的行业就业/产值",
               "用 `--values PATH --value-key sic --value-col <列名>` 指定；加权 broad 映射另需 `--weights`")
    else:
        key, col = a.value_key, a.value_col
        vals, bad = [], 0
        for r in d.values:
            try:
                vals.append((str(r[key]).zfill(4), float(r[col])))
            except ValueError:
                bad += 1
        before = sum(v for _, v in vals)
        lost = sum(v for s, v in vals if s not in d.strict_final)
        by_sector = defaultdict(float)
        for s, v in vals:
            if s in d.strict_final:
                by_sector[d.strict_final[s]] += v
        after = sum(by_sector.values())
        ok = abs(before - after) <= TOL * max(1.0, abs(before))
        rows = [["strict 映射前后总量", R.mark(C, PASS if ok else FAIL),
                 f"前 {before:,.6g}，后 {after:,.6g}，差 {before - after:,.6g}（SIC 不在 concordance 的部分 {lost:,.6g}；{bad} 行无法解析）"]]
        if d.weights is not None and a.weight_src == "sic_1987":
            w = defaultdict(list)
            for r in d.weights:
                try:
                    w[r[a.weight_src]].append((r[a.weight_dst], float(r[a.weight_col])))
                except ValueError:
                    pass
            alloc = sum(v * wt for s, v in vals for _, wt in w.get(s, []))
            covered = sum(v for s, v in vals if s in w)
            ok2 = abs(covered - alloc) <= TOL * max(1.0, abs(covered))
            rows.append(["加权 broad 映射前后总量", R.mark(C, PASS if ok2 else FAIL),
                         f"有权重的 SIC 上：前 {covered:,.6g}，后 {alloc:,.6g}，差 {covered - alloc:,.6g}"])
        else:
            rows.append(["加权 broad 映射前后总量", R.mark(C, SKIP), "需要以 sic_1987 为源的 --weights"])
        R.add(f"数量文件：{a.values}（列 {col}）", "", *table(["项目", "结果", "说明"], rows), "")
        if not ok:
            R.anomaly("高", "strict 映射后数量总量不守恒", f"映射前 {before:,.6g}，映射后 {after:,.6g}。",
                      [f"不在 concordance 的 SIC：{codes(sorted({s for s, _ in vals if s not in d.strict_final}), 50)}"],
                      ["数量文件里有 concordance 不认识的 SIC 代码（格式不同或不是 1987 版）。"], "这些代码应如何处理？")

    # 5b: counts as a proxy
    rows = []
    stats = json.loads(STATS.read_text()) if STATS.exists() else {}
    t1 = read_csv(TABLE1) if TABLE1.exists() else []
    t2 = read_csv(TABLE2) if TABLE2.exists() else []

    def row(name, expected, got, note=""):
        rows.append([name, n(expected), n(got) if isinstance(got, int) else got, R.mark(C, PASS if expected == got else FAIL), note])

    row("SIC 代码数：master → sic1987_to_isic4_full", len(sics), len({r["sic_1987"] for r in d.full}))
    row("SIC 代码数：master → strict 文件", len(sics), len(d.strict))
    row("路径行数：master → sic1987_to_isic4_full", len(d.master), len(d.full))
    by_gl = Counter(d.strict_map[s] for s in sics if s in d.strict_map)
    row("strict 映射后各 GLORIA 部门的 SIC 数之和", len(sics), sum(by_gl.values()), f"分布在 {len(by_gl)} 个部门")
    by_gl2 = Counter(d.strict_final[s] for s in sics if s in d.strict_final)
    row("加 override 后各 GLORIA 部门的 SIC 数之和", len(sics), sum(by_gl2.values()))
    if t1:
        divs = [r for r in t1 if r["division"] != "All"]
        row("Table 1 各 SIC 大类的代码数之和", len(sics), sum(int(r["sic_codes"]) for r in divs))
        row("Table 1 各大类一对多代码数之和", multi, sum(int(r["one_to_many"]) for r in divs))
    if t2:
        row("Table 2 候选数分布之和", len(sics), sum(int(r["sic_codes"]) for r in t2))
        row("Table 2 候选数 > 1 的代码数", multi, sum(int(r["sic_codes"]) for r in t2 if int(r["n_gloria_candidates"]) > 1))
    if stats:
        row("stats_summary.json：sic_codes", len(sics), stats.get("sic_codes"))
        row("stats_summary.json：isic_rev4_codes", len(d.reached["isic_rev4"]), stats.get("isic_rev4_codes"))
        row("stats_summary.json：gloria_sectors_reached", len(d.reached["gloria_sector"]), stats.get("gloria_sectors_reached"))
        row("stats_summary.json：sic_one_to_many_gloria", multi, stats.get("sic_one_to_many_gloria"))
        isic_multi = sum(1 for rs in d.rows_by_sic.values() if len({r["isic_rev4"] for r in rs}) > 1)
        row("stats_summary.json：sic_one_to_many_isic", isic_multi, stats.get("sic_one_to_many_isic"))
    if d.demo is not None:
        assigned = [r for r in d.demo if d.strict_final.get(str(r["sic"]).zfill(4)) and r["fic"] in d.fic2reg]
        row("示例 panel：firm-year 数 → 拿到唯一 strict 部门和地区的 firm-year 数", len(d.demo), len(assigned), "无丢失、无重复")
    R.add("### 5b 代理检查：代码数和记录数在各文件、各输出之间守恒", "",
          "仓库里能检验的“总量”只有计数。下面检查 SIC 代码数、路径行数和 firm-year 数在映射和各输出表之间是否一致。", "",
          *table(["项目", "应为", "实际", "结果", "说明"], rows), "")

    n_proxy = sum(1 for r in rows if r[3] == PASS)
    R.key[C] = f"数量守恒{'无法运行（没有数量变量、没有权重）' if d.values is None else '已运行'}；计数代理 {n_proxy}/{len(rows)} 通过"


# ----------------------------------------------------------------------------- anomalies

def find_anomalies(d: Data, R: Report):
    # A. one fic for several regions
    by_fic = defaultdict(list)
    for r in d.regions:
        if r["fic"] and r["region_type"] != "aggregate":
            by_fic[r["fic"]].append(r)
    for fic, rs in sorted(by_fic.items()):
        if len(rs) < 2:
            continue
        picked = d.fic2reg[fic]
        lost = [r["gloria_region"] for r in rs if r["gloria_region"] != picked]
        all_country = all(r["region_type"] == "country" for r in rs)
        involved = table(["gloria_region", "fic", "region_type", "in_our_list"],
                         [[r["gloria_region"], r["fic"], r["region_type"], r["in_our_list"]] for r in rs])
        causes = []
        if all_country:
            causes.append("两个不同国家（region_type 都是 country）共用一个代码，至少有一行填错。")
            hints = [f"{r['gloria_region']} = {ISO3_HINT[r['gloria_region']]}" for r in rs if r["gloria_region"] in ISO3_HINT]
            if hints:
                causes.append("按 ISO 3166-1 alpha-3：" + "，".join(hints) + "。")
                wrong = [r for r in rs if r["gloria_region"] in ISO3_HINT and ISO3_HINT[r["gloria_region"]] != fic]
                for r in wrong:
                    present = ISO3_HINT[r["gloria_region"]] in by_fic
                    causes.append(f"{r['gloria_region']} 一行的 fic 疑似录入错误；地区表里{'有' if present else '没有'} `{ISO3_HINT[r['gloria_region']]}`。")
        else:
            causes.append("这些是 GLORIA 的历史地区（国家合并或分立前后的名称），共用今天的 ISO3 代码可能是有意为之。")
        R.anomaly("高" if all_country else "低", f"fic `{fic}` 对应 {len(rs)} 个 GLORIA 地区",
                  f"`merge_firms_to_ecp.py` 按 fic 建字典，后出现的行覆盖前面的，所以 `{fic}` → {picked}"
                  f"（{picked} 能查到只是因为它在文件里排在后面）；"
                  f"{'、'.join(lost)} 按任何 fic 都查不到，该地区的 firm 拿不到价格。",
                  involved, causes,
                  "是否要更正这一行的 fic？" if all_country else "历史地区是否需要按年份区分查找，还是保持现状？")

    # B. strict rule counts paths, not distinct ISIC classes
    rep_pairs = sum(1 for v in Counter((r["sic_1987"], r["isic_rev4"]) for r in d.master).values() if v > 1)
    diffs, example = [], ""
    for s, rs in d.rows_by_sic.items():
        by_rows, _, c_rows = modal([r["gloria_sector"] for r in rs])
        seen, distinct = set(), []
        for r in rs:
            if r["isic_rev4"] not in seen:
                seen.add(r["isic_rev4"])
                distinct.append(r["gloria_sector"])
        by_isic, tied_isic, c_isic = modal(distinct)
        if by_rows != by_isic:
            diffs.append([s, d.sic_title[s][:60], f"{by_rows}（{c_rows[by_rows]} 行）",
                          f"{by_isic}（{c_isic[by_isic]} 个 ISIC）", "是" if len(tied_isic) > 1 else "否",
                          "是" if s in d.overridden else ""])
            if s == "3312":           # used as the worked example below (Table 6 in output/)
                example = (f"例如 {s}（钢铁）按行计数是 {by_rows}，按 ISIC class 计数则 {len(tied_isic)} 个候选并列，"
                           f"排序会选中 {by_isic}。")
    if diffs:
        n_tied = sum(1 for x in diffs if x[4] == "是")
        R.anomaly("中", f"strict 规则按路径行数计数，与 README 的“ISIC class 最多”不一致（{len(diffs)} 个 SIC 受影响）",
                  "`make_strict_crosswalk.py` 数的是 master 的行（脚本说明写的是 “ISIC Rev.4 rows”），"
                  "而 `data/README.md` 写的是 “the modal candidate (most ISIC classes)”。master 里同一 ISIC class 经过几个 NAICS 码就有几行，"
                  f"所以两种口径会给出不同的 strict 部门。按不同 ISIC class 计数，有 {len(diffs)} 个 SIC 的 strict 部门会变，"
                  f"其中 {n_tied} 个在新口径下又是并列，要靠排列顺序决定。",
                  details(f"展开 {len(diffs)} 个受影响的 SIC", table(
                      ["SIC", "标题", "现行 strict（按行）", "按不同 ISIC class", "新口径下并列", "已 override"], diffs)),
                  [f"master 是路径表，(SIC, ISIC) 端点对有 {n(rep_pairs)} 对重复（见第 4 项）；按行计数等于按 NAICS 路径数加权。",
                   "两种口径各有道理：按行相当于给“覆盖更多 NAICS 细分行业”的 ISIC 更大权重，按 ISIC class 则与文档描述一致。"
                   + example],
                  "strict 规则的本意是哪一种？README 和脚本说明是否需要统一表述？")

    # C. ties decided by listing order
    ties = []
    for s, rs in d.rows_by_sic.items():
        choice, tied, counts = modal([r["gloria_sector"] for r in rs])
        if len(tied) > 1:
            ties.append([s, d.sic_title[s][:60], len(tied), "; ".join(tied), choice,
                         d.strict_final[s] if s in d.overridden else ""])
    if ties:
        multi = sum(1 for c in d.cands.values() if len(c) > 1)
        R.anomaly("中", f"{len(ties)} 个 SIC 的 strict 部门由 Census 排列顺序决定",
                  f"这些 SIC 的众数候选并列（占 {n(multi)} 个一对多 SIC 的 {pct(len(ties), multi)}），"
                  f"`make_strict_crosswalk.py` 取 Census 表中最先出现的那个。`strict_overrides.csv` 只人工处理了其中 "
                  f"{sum(1 for x in ties if x[5])} 个。",
                  details(f"展开 {len(ties)} 个并列的 SIC", table(
                      ["SIC", "标题", "并列候选数", "并列候选（按出现顺序）", "现行 strict", "override 为"], ties)),
                  ["最常见的情形是每个候选部门各由一个 ISIC class 到达"
                   + ("（例如已 override 的 1311 原油天然气、7372 软件）" if {"1311", "7372"} <= {x[0] for x in ties} else "")
                   + "；Census 表的行序没有经济含义。"],
                  "是否逐个复核这些代码？可以先只复核在定价辖区里候选价格差别大的那些（需要 ECP 文件来筛）。")

    # D. ISIC classes where GLORIA is finer
    finer = [r for r in d.isic2gl if r["relation"].startswith("1:n")]
    if finer:
        fset = {r["isic_rev4"] for r in finer}
        any_f = sorted(s for s, rs in d.rows_by_sic.items() if any(r["isic_rev4"] in fset for r in rs))
        only_f = [s for s in any_f if all(r["isic_rev4"] in fset for r in d.rows_by_sic[s])]
        rows = [[s, d.sic_title[s][:60], "; ".join(d.cands[s])] for s in only_f]
        R.anomaly("中", f"{len(finer)} 个 ISIC class 内 GLORIA 更细，但只映射到一个部门（{len(any_f)} 个 SIC 经过，{len(only_f)} 个完全落在其中）",
                  "isic4_to_gloria.csv 用 relation=1:n(GLORIA finer) 标注了这些 class：GLORIA 在其内部分得更细，"
                  "但 crosswalk 只给一个部门（多为 n.e.c. 类）。下表列出全部路径都经过这些 class 的 SIC——它们拿不到更细的 GLORIA 部门。",
                  table(["ISIC", "标题", "映射到"], [[r["isic_rev4"], r["isic_title"], r["gloria_sector"]] for r in finer]) + [""] +
                  details(f"展开 {len(only_f)} 个完全落在这些 class 里的 SIC", table(["SIC", "标题", "GLORIA 部门"], rows)),
                  ["ISIC 4 位码区分不了 GLORIA 的细分，整类只能进一个部门。",
                   "部分 SIC 标题比 ISIC 更具体，落到的部门名与标题不符，例如 2812 Alkalies and Chlorine、2813 Industrial Gases（无机）→ "
                   "Basic organic chemicals，0116 Soybeans → Growing cereals n.e.c，3334 Primary Aluminum → Basic non-ferrous metals n.e.c.。"
                   if {"2812", "2813", "0116", "3334"} <= set(only_f) else "部分 SIC 标题比 ISIC 更具体，落到的部门名与标题不一定相符。"],
                  "这些 SIC 是否要在 SIC 层面直接指定更细的 GLORIA 部门（像 strict_overrides.csv 那样）？铝、铜等 ETS 覆盖的行业价格差异可能较大。")

    # E. ISIC codes that are not ISIC Rev.4 classes
    gl_of = {r["isic_rev4"]: r["gloria_sector"] for r in d.isic2gl}
    title_of = {r["isic_rev4"]: r["isic_title"] for r in d.isic2gl}
    bad = sorted(c for c in d.reached["isic_rev4"] if not is_isic_class(c))
    if bad:
        rows = []
        for c in bad:
            comp = sorted(k for k in gl_of if is_isic_class(k) and k.startswith(c.rstrip("X")))
            comp_gl = sorted({gl_of[k] for k in comp})
            used = [r for r in d.master if r["isic_rev4"] == c]
            rows.append([c, title_of.get(c, ""), gl_of.get(c, ""), f"{len(comp)} 个 class → {len(comp_gl)} 个部门：{'; '.join(comp_gl)}",
                         codes(sorted({r["sic_1987"] for r in used})), codes(sorted({r["naics_2007"] for r in used}))])
        std = len([c for c in d.reached["isic_rev4"] if is_isic_class(c)])
        R.anomaly("中", f"{len(bad)} 个 ISIC 代码不是 ISIC Rev.4 class（{', '.join(bad)}）",
                  f"这些代码在 ISIC Rev.4 里不存在，是组（3 位）一级的占位码。它们让 crosswalk 的 ISIC 数成为 "
                  f"{len(d.reached['isic_rev4'])}（README 写“420 ISIC classes”）；标准 4 位码只有 {std} 个，官方 class 是 419 个。",
                  table(["代码", "标题", "映射到的 GLORIA", "同组标准 class 的 GLORIA 部门", "经过它的 SIC", "对应的 NAICS 2007"], rows),
                  ["Census 的 NAICS 2007 → ISIC Rev.4 对照表对少数 NAICS 码（如 “all other” 类）只给到 ISIC 组一级，构建时用 X 补位。",
                   "如果同组的标准 class 映射到不同 GLORIA 部门，把整个组放进某一个部门就是一个选择；同组都映射到同一部门时不影响结果。"],
                  "这些占位码的 GLORIA 归属是否可以接受？README 的 ISIC 计数是否要说明其中有非标准码？")

    # F. different ISIC codes with the same title
    by_title = defaultdict(list)
    for r in d.isic2gl:
        by_title[r["isic_title"]].append(r)
    for t, rs in by_title.items():
        if len(rs) < 2:
            continue
        gls = {r["gloria_sector"] for r in rs}
        rows = []
        for r in rs:
            used = [m for m in d.master if m["isic_rev4"] == r["isic_rev4"]]
            rows.append([r["isic_rev4"], r["isic_title"], ISIC_TITLE_HINT.get(r["isic_rev4"], "（未知）"), r["gloria_sector"],
                         codes(sorted({m["naics_2007"] for m in used}), 8), len({m["sic_1987"] for m in used})])
        R.anomaly("低", f"ISIC {' 和 '.join(r['isic_rev4'] for r in rs)} 用了同一个标题",
                  f"isic4_to_gloria.csv 和 master 中这几个代码的 isic_title 都是 “{t}”。"
                  + (f"它们映射到同一 GLORIA 部门（{next(iter(gls))}），所以不影响价格，只影响标签。" if len(gls) == 1 else "它们映射到不同 GLORIA 部门。"),
                  table(["ISIC", "文件中的标题", "ISIC Rev.4 官方标题", "GLORIA", "对应 NAICS 2007", "经过的 SIC 数"], rows),
                  ["标题很可能是从相邻行复制时出错；从对应的 NAICS 码看（如 523930 投资咨询、523991 信托），代码本身是对的，错的是标题。"
                   if any(r["isic_rev4"] in ISIC_TITLE_HINT for r in rs) else "至少一个标题有误。"],
                  "是否更正标题？")


# ----------------------------------------------------------------------------- appendix

def consistency(d: Data, R: Report):
    rows = []
    gl_m = defaultdict(set)
    for r in d.master:
        gl_m[r["isic_rev4"]].add(r["gloria_sector"])
    multi = sorted(k for k, v in gl_m.items() if len(v) > 1)
    rows.append(["master 中每个 ISIC 只对应一个 GLORIA 部门", PASS if not multi else FAIL, codes(multi) if multi else f"{n(len(gl_m))} 个 ISIC"])
    ig = {r["isic_rev4"]: r["gloria_sector"] for r in d.isic2gl}
    diff = sorted(k for k, v in gl_m.items() if ig.get(k) not in v)
    rows.append(["master 与 isic4_to_gloria.csv 的 ISIC → GLORIA 一致", PASS if not diff else FAIL, codes(diff) if diff else "一致"])
    shared = [c for c in d.full[0] if c in d.master[0]]
    same = len(d.full) == len(d.master) and all(all(a[c] == b[c] for c in shared) for a, b in zip(d.full, d.master))
    rows.append(["sic1987_to_isic4_full.csv 与 master 的共同列逐行相同", PASS if same else FAIL, ", ".join(shared)])
    rel_bad = []
    n_isic = {s: len({r["isic_rev4"] for r in rs}) for s, rs in d.rows_by_sic.items()}
    for r in d.full:
        want = "1:n" if n_isic[r["sic_1987"]] > 1 else "1:1"
        if r["relation"] != want:
            rel_bad.append(r["sic_1987"])
    rows.append(["full 文件的 relation（1:1 / 1:n）与不同 ISIC 数一致", PASS if not rel_bad else FAIL, codes(sorted(set(rel_bad)), 10) if rel_bad else "一致"])
    regen = {s: modal([r["gloria_sector"] for r in rs])[0] for s, rs in d.rows_by_sic.items()}
    mism = sorted(s for s in regen if d.strict_map.get(s) != regen[s])
    rows.append(["按 make_strict_crosswalk.py 的规则重算 strict，与发布文件一致", PASS if not mism else FAIL, codes(mism, 20) if mism else "1,005/1,005 一致"])
    nc = sorted(r["sic_1987"] for r in d.strict if int(r["n_candidate_gloria"]) != len(d.cands.get(r["sic_1987"], [])))
    rows.append(["strict 文件的 n_candidate_gloria 与 master 一致", PASS if not nc else FAIL, codes(nc, 20) if nc else "一致"])
    ov_bad = [r["sic_1987"] for r in d.overrides if r["gloria_sector_override"] not in d.cands.get(r["sic_1987"], [])]
    rows.append(["override 的部门属于该 SIC 的候选集合", PASS if not ov_bad else FAIL, codes(ov_bad) if ov_bad else f"{len(d.overrides)}/{len(d.overrides)}"])
    for r in rows:
        if r[1] == FAIL:
            R.mark(4, FAIL)
    R.appendix = ["## 附录：跨文件一致性", "", "辅助检查，结果计入第 4 项。", "", *table(["项目", "结果", "说明"], rows), ""]


# ----------------------------------------------------------------------------- main

def build(a) -> tuple[str, list, bool]:
    d = Data(a)
    body = Report()
    check_coverage(d, body)
    check_weights(d, body, a)
    check_unmatched(d, body)
    check_duplicates(d, body)
    check_conservation(d, body, a)
    find_anomalies(d, body)
    consistency(d, body)

    out = ["# Concordance 验证报告", "",
           "> 由 `validation/validate_concordance.py` 生成。只做检查，不修改任何映射或代码。",
           "> 重新生成：`python3 validation/validate_concordance.py`"
           + ("" if d.ecp_sectors is not None else "（有 ECP 文件时加 `--ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv`）"), ""]

    inputs = [[str(p.relative_to(ROOT)), n(len(read_csv(p))), sha12(p)] for p in list(FILES.values()) + [DEMO] if p.exists()]
    ecp_rel = str(d.ecp_path.relative_to(ROOT)) if d.ecp_path.is_relative_to(ROOT) else str(d.ecp_path)
    inputs.append([ecp_rel, "—" if d.ecp_sectors is None else "已读取", "缺失（未随仓库分发）" if d.ecp_sectors is None else sha12(d.ecp_path)])
    for lv, p in d.universe_src.items():
        if lv != "gloria_sector" or d.ecp_sectors is None:
            inputs.append([p, n(len(d.universe[lv])), sha12(Path(p))])
    for label, p in (("--weights", a.weights), ("--values", a.values)):
        if p:
            inputs.append([f"{p}（{label}）", n(len(read_csv(Path(p)))), sha12(Path(p))])
    out += ["## 输入数据", "", *table(["文件", "行数", "SHA-256（前 12 位）"], inputs), ""]

    names = {1: "各分类层级的匹配覆盖率", 2: "一对多映射的权重之和 = 1", 3: "没有匹配上的代码清单",
             4: "重复映射", 5: "映射前后关键变量总量守恒"}
    summary = [[k, names[k], body.worst(k), body.tally(k), body.key.get(k, "")] for k in names]
    out += ["## 总览", "", *table(["#", "检查", "结果", "子项", "主要数字"], summary), "",
            "结果取各子项中最差的一项：❌ 失败 > ⚠️ 警告 > ⏸ 无法运行 > ✅ 通过；ℹ️ 信息不计入。", ""]

    out += body.lines

    out += ["## 需要 Coco 判断", "",
            f"以下 {len(body.anomalies)} 项是检查中发现的异常，按严重程度排列。本次没有修正其中任何一项。", ""]
    for i, x in enumerate(sorted(body.anomalies, key=lambda x: SEVERITY_ORDER[x["severity"]]), 1):
        out += [f"### {i}. [{x['severity']}] {x['title']}", "",
                f"**异常是什么：** {x['what']}", "", "**涉及的代码：**", "", *x["involved"], "",
                "**可能的原因：**", "", *[f"- {c}" for c in x["causes"]], "",
                f"**需要判断：** {x['question']}", ""]
    if not body.anomalies:
        out += ["没有发现异常。", ""]

    out += ["## 缺少的数据", "", "下列检查因为仓库里没有相应数据而无法运行（或只能部分运行）。", ""]
    out += table(["影响的检查", "缺什么", "怎样补上"], body.missing) if body.missing else ["无。"]
    out += ["", *body.appendix]

    failed = any(FAIL in v for v in body.status.values())
    return "\n".join(out).rstrip() + "\n", summary, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ecp", default=None, help=f"ECP industry file (default: {DEFAULT_ECP.relative_to(ROOT)} if present)")
    ap.add_argument("--universe", action="append", metavar="LEVEL=PATH", help="official code list for a level; repeatable")
    ap.add_argument("--weights", default=None, help="CSV of one-to-many weights")
    ap.add_argument("--weight-src", default="sic_1987")
    ap.add_argument("--weight-dst", default="gloria_sector")
    ap.add_argument("--weight-col", default="weight")
    ap.add_argument("--values", default=None, help="CSV with a quantity by SIC code")
    ap.add_argument("--value-key", default="sic")
    ap.add_argument("--value-col", default=None)
    ap.add_argument("--out", default=str(OUT / "validation_report.md"))
    a = ap.parse_args()
    if a.values and not a.value_col:
        ap.error("--values needs --value-col")

    text, summary, failed = build(a)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"wrote {a.out}")
    for k, name, status, tally, _ in summary:
        print(f"  [{k}] {status:<8} {name}（{tally}）")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
