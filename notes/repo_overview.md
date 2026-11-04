# Repo overview：carbon-pricing-concordance

> 通读日期：2026-11-04。本文件只做诊断，没有修改 repo 里任何已有文件。
> 所有“实际运行”都在 repo 的一份临时拷贝里进行（原因见 §4：有两个脚本会无条件覆盖 `output/` 下已提交的文件）。

---

## 1. 这个项目在做什么

**一句话**：给一家只有美国 SIC 1987 四位行业码的公司（典型是 Compustat 的 `sic`/`sich`），找到它所在行业、所在国家、所在年份面对的**碳价**。

链条（代码与数据实际实现的版本）：

```
SIC 1987 ─► NAICS 2002 ─► NAICS 2007 ─► ISIC Rev.4 ─► GLORIA 行业 ─► ecp_edgar
(Census 对照表)  (Census 版本桥)  (Census/UNSD 对照表) (GLORIA 按 ISIC 聚合)  (Dolphin & Merkle 2024,
                                                                         行业×GLORIA 地区×年, 2021 美元/tCO2e)
```

- 碳价来源是 Dolphin & Merkle (2024) 的 *emissions-weighted carbon price*（ECP）行业文件 `ecp_gloria_edgar_industry_CO2.csv`，1990–2021 年。
- 项目背景：作者 Xiaoke (Coco) Dai 在 Anh V. Persson 教授（UIUC Gies）的“碳定价与企业投资”项目中做 RA（2026 年 5–8 月）的产出；`docs/` 里的 PDF 是据此写的写作样本（research note，2026 年 10 月）。repo 不含任何公司层面数据和项目的实证结果。
- 核心发现（来自 README 和 PDF）：
  - 1,005 个 SIC 码中有 342 个（34%）对应多个 GLORIA 行业（“一对多”）。
  - 在制造业里，这种一对多基本无所谓（候选行业的价格差不多）；
  - 在运输/公用事业、批发、零售、服务业，候选行业常常横跨碳定价机制的覆盖边界（一个在 ETS 里、一个不在），选哪个直接决定公司“有没有被定价”。
  - 因此仓库同时给出 **strict**（每个 SIC 取一个“众数”行业）和 **broad**（所有候选行业的价格区间）两种口径，方便做稳健性检验。
- 明确**没做**的事：没有和真实公司数据合并，没有跑任何回归。

---

## 2. 目录结构与各脚本

```
carbon-pricing-concordance/
├── README.md                 项目说明、复现命令、headline 数字
├── LICENSE                   MIT
├── requirements.txt          pandas>=1.5, matplotlib>=3.5（无上限、未锁版本）
├── .gitignore                忽略 data/ecp/ 和 output/firms_with_ecp.csv
├── data/
│   ├── README.md             各对照表说明、ECP 下载说明
│   ├── crosswalks/           6 个对照表（已随 repo 分发）
│   └── ecp/                  ← 不存在；需从 Zenodo 手动下载
├── src/                      5 个脚本（见下表）
├── output/                   已提交的结果：table1–6、stats_summary.json、figure1（均为 2019 年）
├── examples/demo_firms.csv   12 行虚构的公司-年数据
└── docs/
    ├── methodology.md        方法说明（2026 年 7 月版改写，部分内容已过时，见 §5）
    └── Dai_Xiaoke_WritingSample_CarbonPricingConcordance.pdf   写作样本，7 页
```

### 脚本一览（README 建议的运行顺序）

| 脚本 | 输入 | 输出 | 作用 | 依赖 |
|---|---|---|---|---|
| `src/verify_crosswalk.py` | `master`、`strict` 两张表；可选 `--ecp <行业 ECP 文件>` | 只打印检查结果；有失败时退出码 1 | 完整性检查：①每个 SIC 都能到 ISIC；②每个 ISIC 都能到 GLORIA；③strict 表覆盖的 SIC 集合与 master 相同；④（需 ECP）master 里用到的 GLORIA 名称都能在 ECP 文件中逐字找到 | 只用标准库 |
| `src/make_strict_crosswalk.py` | `master` | 打印摘要；`--out` 时写 CSV；`--check` 时与 `sic_to_gloria_strict.csv` 比对 | 用“众数规则”重新生成 strict 表：每个 SIC 取 master 中**出现行数最多**的 GLORIA 行业，并列时取 Census 表中排在最前面的 | 标准库 |
| `src/concordance_stats.py` | `master` | `output/table1_multiplicity_by_division.csv`、`table2_candidate_count_distribution.csv`、`table3_most_ambiguous_codes.csv`、`stats_summary.json`（**固定写入 `output/`，会覆盖已提交的文件**） | 按 SIC 大类统计一对多比例、候选数分布、最模糊的 25 个码 | 标准库 |
| `src/price_dispersion.py` | `master`、`strict`、ECP 行业文件；参数 `--year`（默认 2019）、`--example-region`（默认 Germany）、`--priced-threshold`（默认 0） | `output/table4_dispersion_by_jurisdiction_<year>.csv`、`table5_dispersion_pooled_<year>.csv`、`table6_examples_<year>.csv`、`figure1_price_range_<year>.png`（**同样固定写入 `output/`**） | 对每个一对多 SIC × 每个有正碳价的地区，比较候选行业的价格：价差、是否“有的被定价有的没有”、strict 选项为 0 而其他候选 >0 的比例 | pandas、matplotlib（matplotlib 缺失时跳过画图） |
| `src/merge_firms_to_ecp.py` | 公司-年 CSV（列 `sic`、`fic`、`year`，可用 `--col-*` 改名）；`master`、`strict`、`strict_overrides`、`gloria_region_to_fic_crosswalk`、ECP 行业文件 | 默认 `output/firms_with_ecp.csv`（被 .gitignore 忽略），新增列：`gloria_region`、`gloria_sector_strict`、`n_candidates`、`ecp_strict`、`ecp_min`、`ecp_max`、`merge_note` | 给公司面板挂碳价。strict 口径**会**应用 `strict_overrides.csv` 的手动修正；broad 口径给出所有候选行业价格的最小/最大值 | 标准库 |

注：脚本输出文件的编号（table1–6）和 PDF 里的表号（Table 1–3）不是一一对应的：PDF Table 1 = `table1_*`，PDF Table 2 = `table5_*`，PDF Table 3 = `table6_*`，PDF Figure 1 = `figure1_*`；`table2_*`、`table3_*`、`table4_*` 只在正文里被引用数字。

---

## 3. 数据文件：哪些在、哪些缺

### 在 repo 里的

| 文件 | 行数 | 被谁用 | 我的核对结果 |
|---|---|---|---|
| `data/crosswalks/sic_naics_isic_gloria_master.csv` | 4,521 | 全部 5 个脚本 | 1,005 个 SIC、420 个 ISIC、96 个 GLORIA 行业，与文档一致。无完全重复的路径；但有 **1,271 行是同一个 (SIC, ISIC) 经不同 NAICS 路径重复出现**（影响 strict 规则，见 §5 H3）。97 行标注 `isic_gloria_relation = 1:n(GLORIA finer)` |
| `data/crosswalks/sic1987_to_isic4_full.csv` | 4,521 | **没有脚本使用** | 与 master 的路径逐行完全相同（只少 GLORIA 列）；`relation` 列（1:1 / 1:n）与实际 ISIC 个数一致 |
| `data/crosswalks/isic4_to_gloria.csv` | 420 | **没有脚本使用** | 与 master 中的 ISIC→GLORIA 完全一致（0 处不符）。5 个 ISIC 类标为 `1:n(GLORIA finer)`：0111、0729、1010、2011、2420（见 §6） |
| `data/crosswalks/sic_to_gloria_strict.csv` | 1,005 | verify、make_strict --check、price_dispersion、merge | `make_strict_crosswalk.py --check` 通过 |
| `data/crosswalks/strict_overrides.csv` | 2 | 仅 merge | 1311 → Petroleum extraction；7372 → Publishing |
| `data/crosswalks/gloria_region_to_fic_crosswalk.csv` | 164 | 仅 merge | 153 country / 7 historical / 4 aggregate。**Niger 被编成 `NGA`（应为 `NER`）**；`YEM` 对应两个历史地区；**没有 Taiwan**；`in_our_list` 列无任何脚本使用，也无文档说明 |
| `examples/demo_firms.csv` | 12 | merge | 虚构数据 |
| `output/*` | — | 无（结果文件） | 用当前代码重跑 `concordance_stats.py`，4 个输出与已提交文件**逐字节相同**。table4–6 和 figure1 因缺 ECP 无法重现 |

### 缺失的

| 文件 | 被谁用 | 说明 |
|---|---|---|
| `data/ecp/ecp_gloria_edgar_industry_CO2.csv`（≈96 MB） | verify（`--ecp` 时）、price_dispersion、merge | **缺失**。按设计不分发，需从 Zenodo 10.5281/zenodo.12181508 下载。没有下载脚本，也没有记录版本号/校验和 |
| `data/ecp/ecp_CO2.csv`（国家/次国家级） | **没有脚本使用** | data/README 要求下载，但代码里没用到。methodology 里说的“2022 年用国家价格兜底”和 `ecp_all_jurCO2` 列都没有实现 |
| 构建 master 表的原始文件：Census 1987 SIC→2002 NAICS、2002→2007 NAICS、2007 NAICS→ISIC Rev.4，以及 GLORIA↔ISIC 对照表 | 无 | **既没有原始文件，也没有构建脚本**。master 表是怎么拼出来的只有文字描述，无法从源头复现 |
| methodology.md 里列出的文件：`SIC_to_ECP_crosswalk_no_IPCC.xlsx`、`ecp_edgar_by_gloria_country_year_ourlist.csv`、`merge_firms_to_ecp_no_ipcc.py` | 无 | repo 里都不存在（文档过时，见 §5） |

---

## 4. 现在能不能跑通

**结论：一半能跑。** 只依赖对照表的两个半脚本能跑通且结果与已提交输出一致；所有需要碳价文件的步骤都跑不了，因为 ECP 文件不在 repo 里，而且这个云端环境的网络策略禁止访问 zenodo.org（代理返回 403），我没法替你下载。

环境：Python 3.13.18。系统自带 pandas 3.0.5，**没装 matplotlib**；我另建了临时虚拟环境按 `requirements.txt` 安装（pandas 3.1.1、matplotlib 3.11.2）。

### 按 README 的命令逐条运行（真实结果）

| 命令 | 结果 |
|---|---|
| `python3 src/verify_crosswalk.py` | ✅ 退出码 0。`[1] SIC 1005, 无 ISIC 0 OK`；`[2] ISIC 420, 无 GLORIA 0 OK`；`[3] True` |
| `python3 src/verify_crosswalk.py --ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv` | ❌ 前三项通过后报错 `FileNotFoundError: [Errno 2] No such file or directory: 'data/ecp/ecp_gloria_edgar_industry_CO2.csv'`（verify_crosswalk.py:46） |
| `python3 src/make_strict_crosswalk.py --check` | ✅ `SIC codes: 1,005 \| map to >1 GLORIA sector: 342 (34.0%)`；`check passed` |
| `python3 src/concordance_stats.py` | ✅ 结果与已提交的 table1/2/3、stats_summary.json 逐字节相同 |
| `python3 src/price_dispersion.py --ecp ... --year 2019 --example-region Germany` | ❌ `FileNotFoundError: ... 'data/ecp/ecp_gloria_edgar_industry_CO2.csv'`（在 price_dispersion.py:72 的 `pd.read_csv`） |
| `python3 src/merge_firms_to_ecp.py examples/demo_firms.csv --ecp ...` | ❌ `FileNotFoundError: ... 'data/ecp/ecp_gloria_edgar_industry_CO2.csv'`（merge_firms_to_ecp.py:48） |
| 从 Zenodo 下载 ECP | ❌ `curl: (56) CONNECT tunnel failed, response 403`（环境网络策略拦截 zenodo.org） |

### 用“假价格文件”做的代码路径测试（只测代码会不会崩，数字没有任何意义）

为了不让缺数据挡住找 bug，我在临时拷贝里造了一个列名与真文件相同（`year,country,sector,ecp_edgar`）、价格随机的小文件，只含 5 个地区。**这些运行产生的数字不代表任何结果，不应引用。**

- `verify_crosswalk.py --ecp`：第 [4] 项能正常运行。
- `price_dispersion.py --year 2019`：在 pandas 3.1.1 下能跑完，开 `-W error::FutureWarning` 也没有弃用警告；能生成全部表和图。
- `price_dispersion.py --year 2022`（或任何文件里没有的年份）：❌ 崩溃，报错 `KeyError: 'jurisdiction'`，看不出原因是“该年没有数据”。
- `merge_firms_to_ecp.py examples/demo_firms.csv`：能跑完。用各种格式的输入测试后发现：
  - `sic = 3312.0`（Stata/pandas 导出的浮点格式）→ 静默变成 “SIC not in concordance”
  - `year = 2019.0` → 静默无价格，`merge_note` 却写 “year outside 1990-2021 or sector missing”（提示有误导性）
  - `fic = deu`（小写）→ “no GLORIA region for fic”
  - `fic = NER`（Niger）→ 匹配不到（对照表里 Niger 写成了 NGA）
  - `fic = BMU`（百慕大，Compustat 常见注册地）→ 无地区
  - 空输入文件 → `IndexError: list index out of range`（merge_firms_to_ecp.py:96）
  - 列名不是 `sic`（如 Compustat 的 `sich`）且没传 `--col-sic` → 裸 `KeyError: 'sic'`
- Compustat 常见的“非四位细类”行业码，在对照表中**全部找不到**：`7370、6770、9997、9995、2800、3310、4900、6199、1000、3670、5000、3570、8000、2830、3600` 都返回 “SIC not in concordance”。对照表里没有任何以 0 结尾的 SIC 码。

### 你要跑通需要做的

1. 从 Zenodo 下载 `ecp_gloria_edgar_industry_CO2.csv` 放到 `data/ecp/`（在本地做最简单）。如果想在这个云端环境里跑，需要在环境设置的 Network access 里把 `zenodo.org` 加到允许域名（步骤：https://code.claude.com/docs/en/cloud-environments#network-access）。
2. `pip install -r requirements.txt`（至少补装 matplotlib）。
3. **在 repo 根目录下运行**（命令里的 `--ecp` 和 `examples/` 都是相对路径）。注意第 3、4 步会覆盖 `output/` 里的已提交文件。

---

## 5. 发现的问题（按严重程度排序）

严重程度标准：**高** = 会让结果错误或不可复现，且不容易被注意到；**中** = 会造成困惑、报错或口径不一致，但能被发现；**低** = 代码质量/小毛病。

### 高

**H1. 合并真实 Compustat 数据时，大量行业码会静默落空。** 对照表只有 Census 的 4 位细类码，而 Compustat 的 `sic`/`sich` 经常是 3 位或 2 位汇总码补 0（如 7370、2800、3670、4900）和特殊码（6770 空壳公司、9995/9997 非经营/综合企业）。我测的 15 个常见码全部匹配不到。`merge_note` 会标出来，但代码没有任何处理，README 也没提醒。（怎么处理是研究判断，见 §6 Q5）

**H2. merge 对输入格式非常敏感，而且失败时不报错。** `sic` 是 `3312.0`、`year` 是 `2019.0`、`fic` 是小写，都会静默得到空价格。导出的面板里出现浮点格式很常见。年份失败时提示写的是 “year outside 1990-2021 or sector missing”，会误导排查方向。（merge_firms_to_ecp.py:71–82）

**H3. strict 规则的代码实现与文档描述不一致。** data/README 写的是“modal candidate (most ISIC classes)”，PDF 写的是“reached by the largest number of ISIC classes”；但代码（make_strict_crosswalk.py:29、:32）数的是 master 的**行数**，即 SIC×NAICS×ISIC 路径数。master 里有 1,271 行是同一 (SIC, ISIC) 经不同 NAICS 路径重复出现，所以两种数法结果不同：**如果按“不同 ISIC 类的个数”数，有 21 个 SIC 码的 strict 行业会变**，例如：
  - 2819 Industrial inorganic chemicals：现为 Basic organic chemicals → 按 ISIC 个数应为 Dyes, paints, glues…
  - 4212 Local trucking：Road transport → Waste collection, treatment, and disposal
  - 3731 Ship building：Repair and installation of machinery → Services to transport
  - 1629 Heavy construction NEC：Civil engineering → Building construction
  - 其余：2034、2499、2531、2869、3089、3399、3497、3699、3961、5699、5714 等

  这些码正好会进入 PDF Table 3 和 price_dispersion 的统计。（采用哪种口径是研究判断，见 §6 Q1）

**H4. master 表无法从原始资料复现。** repo 里没有 Census/UNSD/GLORIA 原始对照文件，也没有拼表脚本。整条链最关键的一步（4,521 行路径和 420 个 ISIC→GLORIA 归属）只能信任已分发的 CSV。`verify_crosswalk.py` 只检查内部一致性，不检查它是否忠实于原始资料。

**H5. 运行诊断脚本会覆盖已提交的结果。** `concordance_stats.py` 和 `price_dispersion.py` 把 `OUT = ROOT / "output"` 写死，也没有 `--out` 参数（concordance_stats.py:20–21，price_dispersion.py:30–31）。换个年份或阈值重跑，就会改写 PDF 引用的那些文件。

### 中

**M1. 不同脚本里的“strict”不是同一个东西。** merge 会应用 `strict_overrides.csv`（1311→Petroleum extraction、7372→Publishing），但 `price_dispersion.py` 不会。所以 table4/5/6（以及 PDF 的 Table 2/3）里的 “strict” 统计，与 merge 产出的 `ecp_strict` 口径不同。PDF 是有意展示修正前的状态，但代码和 README 都没有说明这个差别。

**M2. 并列由 Census 表行顺序决定的情况远不止两个。** 在 342 个一对多 SIC 里，**107 个（31%）的 strict 选项是并列后按行序选出来的**（若按不同 ISIC 个数数，会有 151 个并列）。override 只修了 2 个。PDF 说这个规则“reads positions, not titles”，但没有给出规模。

**M3. 国家对照表有错，也有缺。** Niger 被编成 `NGA`（应为 `NER`），所以尼日尔的公司匹配不到；`NGA` 因为字典“后写覆盖前写”恰好落到 Nigeria，不受影响。两个历史地区共用 `YEM`，后一行 “Yemen Arab Republic/Yemen (1990/1991)” 会覆盖 “DR Yemen (Aden)”。没有 Taiwan（TWN）这一行。`region_type=historical` 的说法有误导性：CSSR/Czech Republic、USSR/Russian Federation、Yugoslavia/Serbia 在 2019 年的结果里仍作为地区出现（见 table4），说明它们是这些国家在所有年份使用的名字。

**M4. verify 少了几项关键检查。** 没检查国家对照表里的 `gloria_region` 名称能否在 ECP 文件的 `country` 列里找到：只要名称不一致，merge 就会对整个国家静默给空价格。也没检查 override 的行业是否在该 SIC 的候选集合里、是否存在于 ECP 文件。

**M5. Table 4 与 Table 5 的分母不同，PDF 有一句话可能读错了。** `table4` 的 `share_sign_disagree` 分母是**全部**配对，`table5` 则只算“至少一个候选被定价”的配对。PDF 第 5 节说 ETS 国家 “74 to 78 percent of pairs have any priced candidate and the candidates disagree on coverage in 22 to 24 percent of them”。“of them” 读起来是条件比例，但 22–24% 实际是无条件比例；按条件算约为 30%（如德国 0.235/0.771≈0.305）。

**M6. merge 没有实现 2022 年及以后的兜底，也没用国家文件。** methodology.md 写了“2022 用国家价格兜底”和 `ecp_all_jurCO2` 列，data/README 也要求下载 `ecp_CO2.csv`，但代码没有实现。2022 年及以后的公司-年只会得到空值，提示是 “year outside 1990-2021”。

**M7. merge 输出列的含义不够清楚。**
  - strict 行业在该地区-年为 NA（没有排放）而其他候选有价格时，`ecp_strict` 为空、`ecp_min/max` 有值，`merge_note` 却为空。
  - `n_candidates` 在 merge 里是“全部候选数”，在 price_dispersion 里是“有价格行的候选数”，同名不同义。
  - `ecp_min/max` 静默排除了 NA 候选。

**M8. price_dispersion 的健壮性问题。**
  - 年份不在文件里时崩溃，报 `KeyError: 'jurisdiction'`（price_dispersion.py:101）。
  - “定价地区”的判定固定用 `> 0`（第 77 行），不受 `--priced-threshold` 影响。阈值设为 $1 时，地区集合仍按 $0 选出。是否合理见 §6 Q10。

**M9. merge 遇到异常输入时，报错不友好。** 空输入文件报 `IndexError`；列名不对报裸 `KeyError`。

### 低

- **L1. 文件句柄没有关闭。** 多处写成 `csv.DictReader(open(...))`（verify:29–30，make_strict:60，concordance_stats:49，merge:39、42、45），开启 ResourceWarning 时 verify 一个脚本就报 4 条。
- **L2.** `make_strict_crosswalk.py --check` 在行数不同时打印 “0 codes differ”，有误导性（第 64–65 行）。
- **L3.** verify 的第 [3] 项不像其他项那样打印 OK/FAIL（第 41 行）。
- **L4.** requirements 没锁版本。目前 pandas 3.x 下能跑，但将来不保证；README 写 Python 3.9+，也没有在 3.9 上测试过。
- **L5.** merge 用纯 Python 把约 96 MB 的 ECP 全部读进字典，较慢，内存占用也大（没有按年份或地区过滤）。

### 硬编码

（没有发现本机绝对路径。所有路径都基于 `ROOT = Path(__file__).parents[1]`，这一点做得好。）

- 输出目录 `output/` 写死在 concordance_stats、price_dispersion 中（见 H5）。
- `EXAMPLE_SICS = ["3312","1311",...]`（price_dispersion.py:33）。PDF Table 3 用的 SIC 列表写在代码里。
- ECP 文件默认路径 `data/ecp/ecp_gloria_edgar_industry_CO2.csv`（price_dispersion:60、merge:59）。
- 覆盖年份 “1990-2021” 写死在 merge 的提示文字里（第 82 行）。
- SIC 大类边界写死在两处（concordance_stats:24–35、price_dispersion:49–51）。
- README 的命令使用相对路径，必须在 repo 根目录下运行。

### 重复代码

- **读 master 表、构造“SIC→候选行业集合”的逻辑重复了 4 次**：make_strict（csv）、concordance_stats（csv）、price_dispersion（pandas）、merge（csv），实现方式各不相同。
- **SIC 大类划分写了两套**，对区间空隙的处理还不一样：concordance_stats 把空隙归为 “?”，price_dispersion 把空隙归到下一个大类。目前没有 SIC 码落在空隙里，所以结果一致，但这是隐患。
- **读 ECP 文件写了三套**：verify 和 merge 用 csv，price_dispersion 用 pandas。对 NA 的处理也分散在各处。
- **override 逻辑只在 merge 里**，没有被其他需要 strict 的脚本复用（这也是 M1 的根源）。
- `ROOT`、`CW`、`OUT` 常量和 `_write` 写 CSV 的写法在多个文件里重复。

### 缺少或过时的文档

- **`docs/methodology.md` 有不少过时内容，与代码和数据不符：**
  - 说 SIC→**1997** NAICS，再沿 1997→2002→2007→**2017** 逐级换版。实际是 SIC→NAICS 2002→2007→ISIC。
  - 提到 `relation_type`、`naics_vintage` 列，实际数据里都不存在。
  - 说 merge 的输入有 `state` 列、会输出 `ecp_all_jurCO2`，实际都没有。
  - “Files this documents” 列出的 xlsx、`_ourlist.csv`、`merge_firms_to_ecp_no_ipcc.py` 都不在 repo 里，还写着后者 “Supersedes `merge_firms_to_ecp.py`”。
  - 说 strict 表 “keeps the primary”，没有说明众数规则。
  - 提到 “118-country panel”，但对照表里 `in_our_list=yes` 只有 93 个地区，两者关系没有说明。
- `in_our_list` 列没有任何文档说明。
- `isic4_to_gloria.csv` 中 5 个 `1:n(GLORIA finer)` 的 ISIC 类在文档里没有解释。PDF 写的是 “each ISIC class belongs to exactly one GLORIA industry”，与这个标注矛盾。
- GLORIA 共 120 个行业，链条只到达 96 个。没到达的 24 个是哪些、为什么到不了，没有说明。
- 输出表没有数据字典：例如 table4/table5 各列是条件还是无条件比例（见 M5），`median_range_over_max` 的含义。
- README 说 price_dispersion “Produces Tables 2–3 and Figure 1”，但实际输出文件名是 table4/5/6，与 concordance_stats 的 table2/3 重名混淆。
- 没有记录 ECP 文件的 Zenodo 版本号和校验和，也没有下载脚本。
- 没有测试，没有 CI。
- PDF Table 1 的注释说 “The Census auxiliary-establishment row is omitted”，但 All 行的 1,005 包含它。
- README headline 没有提农业：农业的候选不一致率是 85%，是所有大类里最高的。

---

## 6. 需要你做研究判断的问题（只列问题，不替你决定）

**strict / broad 口径**

- **Q1.** strict 的“众数”应该按 master 的**路径行数**数，还是按**不同 ISIC 类的个数**数？两种数法有 21 个 SIC 码结果不同（见 H3）。文档和代码需要统一成哪一种？
- **Q2.** 107 个并列码目前按 Census 行序取第一个。是继续用行序，还是换成别的规则（按标题人工判断、按排放、按产出或就业加权……）？override 要扩展到多少个码？
- **Q3.** SIC 1311（原油和天然气）现在 override 成 Petroleum extraction，override 文件自己也提到 Gas extraction 是备选。你要哪个，还是两者都报？
- **Q4.** broad 口径在回归里怎么用：min、max、区间、简单平均，还是加权平均？如果加权，用什么权重？还是直接剔除一对多的码？

**对照链本身**

- **Q5.** 5 个 ISIC 类在 GLORIA 里更细，但表里只指了一个 GLORIA 行业：0111 谷物→“Growing cereals n.e.c”（SIC 0111 小麦、0115 玉米也落在这里）；0729→“Other non-ferrous ores”；1010 肉类加工→“Other meat products”（SIC 2011 meat packing）；2011 基础化学品→“Basic organic chemicals”（SIC 2812 碱和氯、2813 工业气体也落在这里）；2420 有色金属→“Basic non-ferrous metals n.e.c.”（SIC 3334 原铝、3331 铜冶炼也落在这里）。这些是否应该指向 GLORIA 里更具体的行业？
- **Q6.** 一些对照结果在字面上说得通，但经济含义上值得商榷：2097 制冰→电力；7389、3999、2099 这类 “NEC” 兜底码有 13–18 个候选。是保留、手动指定，还是剔除？
- **Q7.** Census 的 “Aux”（辅助机构）被映射到 Professional services。样本里如果出现这个码，要保留吗？

**公司数据端**

- **Q8.** Compustat 的汇总码（以 0 或 00 结尾）和特殊码（6770、9995、9997），对照表里都没有。是剔除、映射到其下所有 4 位码的候选并集，还是改用 Compustat 自带的 NAICS 走另一条链？
- **Q9.** 用 `sich`（历史 SIC）还是 `sic`（当前 SIC）？`sich` 缺失时要不要用 `sic` 回填？
- **Q10.** 国家用 `fic`（注册地）还是 `loc`（总部所在地）？注册在百慕大、开曼等地、没有 GLORIA 地区的公司怎么处理？Taiwan 不在对照表里，被并入 GLORIA 的哪个地区，怎么处理？

**价格端**

- **Q11.** 行业文件不含次国家级碳价（美国各州、加拿大各省、中国试点省份），国家文件含。对美国、加拿大、中国的公司用哪一个？需不需要引入州或省变量？
- **Q12.** 2022 年及以后的公司-年：用国家价格兜底、把 2021 年的价格往后延，还是剔除？
- **Q13.** “被定价”的阈值用 $0 还是 $1（PDF 报告了两种的差别）？“定价地区”的判定要不要跟着同一个阈值走（见 M8）？
- **Q14.** ECP 中的 NA（该行业在该地区-年没有排放）和 0 怎么区分处理？strict 行业是 NA 而其他候选有价格时，该公司记为缺失、0，还是用其他候选的价格？
- **Q15.** ECP 只算 CO₂，采矿业（甲烷为主）会显得几乎没被定价。需要调整，还是只作为局限性说明？
- **Q16.** 价格是 2021 年不变美元，公司财务数据是名义值。是否需要统一？

**呈现**

- **Q17.** 诊断只做了 2019 年。要不要在其他年份（例如 EU ETS 价格很低的 2010–2017 年）检验结论是否稳健？
- **Q18.** 农业的候选不一致率最高（85%），但 README headline 和 PDF 正文都没有着重讨论。要不要写进去？
- **Q19.** PDF 第 5 节关于 ETS 国家 “22 to 24 percent of them” 的表述（见 M5），你的本意是条件比例还是无条件比例？
