# Concordance 验证报告

> 由 `validation/validate_concordance.py` 生成。只做检查，不修改任何映射或代码。
> 重新生成：`python3 validation/validate_concordance.py`（有 ECP 文件时加 `--ecp data/ecp/ecp_gloria_edgar_industry_CO2.csv`）

## 输入数据

| 文件 | 行数 | SHA-256（前 12 位） |
|---|---|---|
| data/crosswalks/sic_naics_isic_gloria_master.csv | 4,521 | c3cbffddc644 |
| data/crosswalks/sic1987_to_isic4_full.csv | 4,521 | 31354ba241d3 |
| data/crosswalks/isic4_to_gloria.csv | 420 | a4b9990ef97d |
| data/crosswalks/sic_to_gloria_strict.csv | 1,005 | 20faf3e543c8 |
| data/crosswalks/strict_overrides.csv | 2 | 7fbf46ac1241 |
| data/crosswalks/gloria_region_to_fic_crosswalk.csv | 164 | fe0c6e6d1d4e |
| examples/demo_firms.csv | 12 | 23f71d41be2d |
| data/ecp/ecp_gloria_edgar_industry_CO2.csv | — | 缺失（未随仓库分发） |

## 总览

| # | 检查 | 结果 | 子项 | 主要数字 |
|---|---|---|---|---|
| 1 | 各分类层级的匹配覆盖率 | ❌ 失败 | 通过 12 · 失败 2 · 警告 2 · 无法运行 7 | 源端各环节均为 100%（SIC 1,005/1,005 到 GLORIA）；清单内地区 92/93 可按 fic 查到；目标端缺官方代码表 |
| 2 | 一对多映射的权重之和 = 1 | ⏸ 无法运行 | 无法运行 2 | 映射表没有权重列；未提供 --weights；342 个 SIC 一对多（GLORIA），其中 107 个 strict 选择靠排列顺序 |
| 3 | 没有匹配上的代码清单 | ❌ 失败 | 通过 11 · 失败 1 · 无法运行 6 | 源端 0 个未匹配代码；2 个非汇总地区按 fic 查不到（DR Yemen (Aden)、Niger）；目标端清单缺官方代码表 |
| 4 | 重复映射 | ❌ 失败 | 通过 8 · 失败 1 · 警告 2 | 整行、完整路径和各表主键无重复；fic 重复 2 个（NGA、YEM）；(SIC, ISIC) 对重复 882 个 |
| 5 | 映射前后关键变量总量守恒 | ⏸ 无法运行 | 通过 15 · 无法运行 2 | 数量守恒无法运行（没有数量变量、没有权重）；计数代理 15/15 通过 |

结果取各子项中最差的一项：❌ 失败 > ⚠️ 警告 > ⏸ 无法运行 > ✅ 通过；ℹ️ 信息不计入。

## 1. 各分类层级的匹配覆盖率

覆盖率 = 能连到下一层（源端）或被上一层映射到（目标端）的代码数 / 该层代码总数。master 是路径表（每行一条 SIC → NAICS 2002 → NAICS 2007 → ISIC → GLORIA 路径），源端分母取该层在仓库文件里出现的全部代码；目标端分母需要官方代码表。

### 1a 源端：每层代码能否连到下一层

| 环节 | 总数 | 匹配数 | 覆盖率 | 结果 | 说明 |
|---|---|---|---|---|---|
| SIC 1987 → NAICS 2002（master） | 1,005 | 1,005 | 100.0% | ✅ 通过 |  |
| NAICS 2002 → NAICS 2007（master） | 1,177 | 1,177 | 100.0% | ✅ 通过 |  |
| NAICS 2007 → ISIC Rev.4（master） | 1,173 | 1,173 | 100.0% | ✅ 通过 |  |
| ISIC Rev.4 → GLORIA 部门（master） | 420 | 420 | 100.0% | ✅ 通过 |  |
| ISIC Rev.4 → GLORIA 部门（isic4_to_gloria.csv） | 420 | 420 | 100.0% | ✅ 通过 |  |
| SIC 1987 → GLORIA 部门（端到端） | 1,005 | 1,005 | 100.0% | ✅ 通过 |  |
| SIC 1987 → strict GLORIA（sic_to_gloria_strict.csv） | 1,005 | 1,005 | 100.0% | ✅ 通过 |  |
| GLORIA 部门 → ECP 价格文件（sector 名称） | 96 | — | — | ⏸ 无法运行 | 缺 ECP 文件。isic4_to_gloria.csv 的 gloria_in_file 列记录 420/420 为 yes（构建时记录，本次未复核） |
| SIC 1987 起点完整性（与文档数量比） | 1,004 + Aux | 1,004 + Aux | 100.0% | ✅ 通过 | 只比数量，未与官方代码表逐个核对 |

### 1b 目标端：目标分类有多少被映射到

| 层级 | 被映射到 | 总数 | 覆盖率 | 结果 | 说明 |
|---|---|---|---|---|---|
| NAICS 2002 | 1,177 | — | —（参考约 99.8%） | ⏸ 无法运行 | 仓库里没有 NAICS 2002 官方代码表。参考：US Census 公布的 NAICS 2002 六位行业数为 1,179，本 crosswalk 用到 1,177 个 |
| NAICS 2007 | 1,173 | — | —（参考约 99.8%） | ⏸ 无法运行 | 仓库里没有 NAICS 2007 官方代码表。参考：US Census 公布的 NAICS 2007 六位行业数为 1,175，本 crosswalk 用到 1,173 个 |
| ISIC Rev.4 | 420 | — | —（参考约 99.5%） | ⏸ 无法运行 | 仓库里没有 ISIC Rev.4 官方代码表。参考：UNSD 公布的 ISIC Rev.4 class 数为 419，本 crosswalk 用到 420 个，其中 3 个不是标准 4 位码（`012X`, `014X`, `331X`），参考覆盖率按 417 个标准码计 |
| GLORIA 部门 | 96 | — | —（参考约 80.0%） | ⏸ 无法运行 | 仓库里没有 GLORIA 部门清单。参考：GLORIA 部门数（docs/methodology.md）为 120，本 crosswalk 用到 96 个 |
| ISIC Rev.4 代码格式（4 位数字） | 417 | 420 | 99.3% | ⚠️ 警告 | 见「需要 Coco 判断」 |
| ISIC → GLORIA 粒度（GLORIA 不比 ISIC 细） | 415 | 420 | 98.8% | ⚠️ 警告 | 5 个 ISIC class 标注 1:n(GLORIA finer)，更细的 GLORIA 部门到不了；见「需要 Coco 判断」 |

### 1c 地区维度（gloria_region_to_fic_crosswalk.csv）

| 环节 | 总数 | 匹配数 | 覆盖率 | 结果 | 说明 |
|---|---|---|---|---|---|
| GLORIA 地区 → fic | 164 | 160 | 97.6% | ✅ 通过 | 4 个无 fic，均为汇总地区（预期如此） |
| 非汇总地区可按 fic 查到（merge 的查法） | 160 | 158 | 98.8% | ❌ 失败 | 查不到：DR Yemen (Aden)（fic YEM 被另一地区占用，见第 4 项）；Niger（fic NGA 被另一地区占用，见第 4 项） |
| 清单内地区（in_our_list=yes）可按 fic 查到 | 93 | 92 | 98.9% | ❌ 失败 | 查不到：Niger（fic NGA 被另一地区占用，见第 4 项） |
| 地区表的地区名 → ECP 文件 country | 164 | — | — | ⏸ 无法运行 | 缺 ECP 文件 |

### 1d 示例 firm panel（examples/demo_firms.csv，合成数据）

| 环节 | firm-year 数 | 匹配数 | 覆盖率 | 结果 | 说明 |
|---|---|---|---|---|---|
| SIC → concordance | 12 | 12 | 100.0% | ✅ 通过 |  |
| fic → GLORIA 地区 | 12 | 12 | 100.0% | ✅ 通过 |  |
| SIC → strict GLORIA 部门 | 12 | 12 | 100.0% | ✅ 通过 |  |
| (地区, 部门, 年份) → ecp_edgar | 12 | — | — | ⏸ 无法运行 | 缺 ECP 文件 |

## 2. 一对多映射的权重之和是否等于 1（容差 1e-6）

| 项目 | 结果 | 数字 |
|---|---|---|
| 映射表中的权重列 | ⏸ 无法运行 | 6 个 crosswalk 文件、共 30 列，没有任何权重/份额列 |
| 外部权重文件（--weights） | ⏸ 无法运行 | 未提供 |

需要权重的一对多链接（仓库里这些链接都没有权重）：

| 环节 | 一对多的源代码 | 源代码总数 | 占比 |
|---|---|---|---|
| SIC 1987 → NAICS 2002 | 453 | 1,005 | 45.1% |
| NAICS 2002 → NAICS 2007 | 13 | 1,177 | 1.1% |
| NAICS 2007 → ISIC Rev.4 | 338 | 1,173 | 28.8% |
| ISIC Rev.4 → GLORIA 部门 | 0 | 420 | 0.0% |
| SIC 1987 → ISIC Rev.4（端到端） | 552 | 1,005 | 54.9% |
| SIC 1987 → GLORIA 部门（端到端） | 342 | 1,005 | 34.0% |

现有管线怎样处理一对多：strict 映射把权重 1 放在众数候选上（和为 1，不需要检验）；broad 映射（`merge_firms_to_ecp.py` 的 `ecp_min`/`ecp_max`）只取候选价格的区间，不加权。如果把 strict 规则的计数看成隐含权重（每个候选的路径数 / 该 SIC 的路径总数），它们按构造和为 1，所以这项检验对现有数据没有信息量。

另外：342 个一对多 SIC 中，有 107 个的众数候选并列，strict 选择实际由 Census 表的排列顺序决定（见「需要 Coco 判断」）。

## 3. 没有匹配上的代码

### 3a 源端

| 源端 | 未匹配数 | 代码 | 结果 |
|---|---|---|---|
| SIC 1987 连不到 NAICS 2002（master） | 0 | — | ✅ 通过 |
| NAICS 2002 连不到 NAICS 2007（master） | 0 | — | ✅ 通过 |
| NAICS 2007 连不到 ISIC Rev.4（master） | 0 | — | ✅ 通过 |
| ISIC Rev.4 连不到 GLORIA 部门（master） | 0 | — | ✅ 通过 |
| ISIC 无 GLORIA 部门（isic4_to_gloria.csv） | 0 | — | ✅ 通过 |
| master 的 ISIC 不在 isic4_to_gloria.csv | 0 | — | ✅ 通过 |
| master 的 SIC 不在 strict 文件 | 0 | — | ✅ 通过 |
| override 的 SIC 不在 master | 0 | — | ✅ 通过 |
| GLORIA 部门名不在 ECP 文件 | — | 缺 ECP 文件 | ⏸ 无法运行 |
| 示例 panel 的 SIC 不在 concordance | 0 | — | ✅ 通过 |
| 示例 panel 的 fic 查不到 GLORIA 地区 | 0 | — | ✅ 通过 |

### 3b 目标端

| 目标端 | 未匹配数 | 代码 | 结果 |
|---|---|---|---|
| NAICS 2002中未被映射到的代码 | — | 缺 NAICS 2002 官方代码表 | ⏸ 无法运行 |
| NAICS 2007中未被映射到的代码 | — | 缺 NAICS 2007 官方代码表 | ⏸ 无法运行 |
| ISIC Rev.4中未被映射到的代码 | — | 缺 ISIC Rev.4 官方代码表 | ⏸ 无法运行 |
| GLORIA 部门中未被映射到的代码 | — | 缺 GLORIA 部门清单 | ⏸ 无法运行 |
| isic4_to_gloria.csv 中未被任何 SIC 到达的 ISIC | 0 | —（注意：此表的 ISIC 集合与 master 完全相同，这一项不能代替官方代码表） | ✅ 通过 |
| 无 fic 的汇总地区 | 4 | Rest of Africa, Rest of Americas, Rest of Asia-Pacific, Rest of Europe | ℹ️ 信息 |
| 非汇总地区按 fic 查不到 | 2 | DR Yemen (Aden)（fic=YEM，in_our_list=no）; Niger（fic=NGA，in_our_list=yes） | ❌ 失败 |
| ECP 文件中的地区不在地区表 | — | 缺 ECP 文件 | ⏸ 无法运行 |

## 4. 重复映射（同一对代码出现多次）

master 是路径表，单个环节的代码对（例如 SIC→NAICS 2002）在路径分叉时本来就会重复，所以这里检查的是：完整路径和整行是否重复、每张一对一查找表的键是否重复，以及端点代码对 (SIC, ISIC) 是否因经过不同 NAICS 而重复出现。

| 文件 | 键 | 行数 | 重复数 | 例子 | 结果 |
|---|---|---|---|---|---|
| sic_naics_isic_gloria_master.csv | 整行 | 4,521 | 0 | — | ✅ 通过 |
| sic_naics_isic_gloria_master.csv | 完整路径 (SIC, NAICS02, NAICS07, ISIC) | 4,521 | 0 | — | ✅ 通过 |
| sic1987_to_isic4_full.csv | 整行 | 4,521 | 0 | — | ✅ 通过 |
| sic1987_to_isic4_full.csv | 完整路径 (SIC, NAICS02, NAICS07, ISIC) | 4,521 | 0 | — | ✅ 通过 |
| isic4_to_gloria.csv | isic_rev4 | 420 | 0 | — | ✅ 通过 |
| sic_to_gloria_strict.csv | sic_1987 | 1,005 | 0 | — | ✅ 通过 |
| strict_overrides.csv | sic_1987 | 2 | 0 | — | ✅ 通过 |
| gloria_region_to_fic_crosswalk.csv | gloria_region | 164 | 0 | — | ✅ 通过 |
| gloria_region_to_fic_crosswalk.csv | fic（非空） | 160 | 2 | `NGA`, `YEM` | ❌ 失败 |
| isic4_to_gloria.csv | isic_title（不同代码同一标题） | 420 | 1 | Other monetary intermediation | ⚠️ 警告 |
| sic_naics_isic_gloria_master.csv | 端点对 (SIC, ISIC) | 3,250 对 | 882 对重复（多出 1,271 行） | 同一 ISIC 经由不同 NAICS 码到达 | ⚠️ 警告 |
| sic_naics_isic_gloria_master.csv | 端点对 (SIC, GLORIA) | 1,798 对 | 685 对出现多于 1 行 | 多个 ISIC/路径汇入同一 GLORIA 部门，是 strict 规则计数的来源 | ℹ️ 信息 |

(SIC, ISIC) 重复本身是路径表的结构，但它会影响 strict 规则：`make_strict_crosswalk.py` 按行计数，一个 ISIC class 经过几个 NAICS 码就被数几次。影响见「需要 Coco 判断」。

## 5. 映射前后关键变量的总量是否守恒

### 5a 数量变量的守恒

| 项目 | 结果 | 说明 |
|---|---|---|
| 数量变量按 strict 映射后总量不变 | ⏸ 无法运行 | 仓库里没有任何 SIC 层面的数量变量（就业、产值、排放等）；示例 panel 只有 sic、fic、year |
| 数量变量按加权 broad 映射后总量不变 | ⏸ 无法运行 | 同上，且一对多链接没有权重（见第 2 项） |

ECP 价格（`ecp_edgar`）是价格，不能加总，所以不适用总量守恒。如果不加权地把一个 SIC 的数量全额分给每个候选部门，总量会被放大到 1.789 倍（1,798 个 SIC–GLORIA 对 / 1,005 个 SIC）——这就是做数量分配必须有权重的原因。

### 5b 代理检查：代码数和记录数在各文件、各输出之间守恒

仓库里能检验的“总量”只有计数。下面检查 SIC 代码数、路径行数和 firm-year 数在映射和各输出表之间是否一致。

| 项目 | 应为 | 实际 | 结果 | 说明 |
|---|---|---|---|---|
| SIC 代码数：master → sic1987_to_isic4_full | 1,005 | 1,005 | ✅ 通过 |  |
| SIC 代码数：master → strict 文件 | 1,005 | 1,005 | ✅ 通过 |  |
| 路径行数：master → sic1987_to_isic4_full | 4,521 | 4,521 | ✅ 通过 |  |
| strict 映射后各 GLORIA 部门的 SIC 数之和 | 1,005 | 1,005 | ✅ 通过 | 分布在 89 个部门 |
| 加 override 后各 GLORIA 部门的 SIC 数之和 | 1,005 | 1,005 | ✅ 通过 |  |
| Table 1 各 SIC 大类的代码数之和 | 1,005 | 1,005 | ✅ 通过 |  |
| Table 1 各大类一对多代码数之和 | 342 | 342 | ✅ 通过 |  |
| Table 2 候选数分布之和 | 1,005 | 1,005 | ✅ 通过 |  |
| Table 2 候选数 > 1 的代码数 | 342 | 342 | ✅ 通过 |  |
| stats_summary.json：sic_codes | 1,005 | 1,005 | ✅ 通过 |  |
| stats_summary.json：isic_rev4_codes | 420 | 420 | ✅ 通过 |  |
| stats_summary.json：gloria_sectors_reached | 96 | 96 | ✅ 通过 |  |
| stats_summary.json：sic_one_to_many_gloria | 342 | 342 | ✅ 通过 |  |
| stats_summary.json：sic_one_to_many_isic | 552 | 552 | ✅ 通过 |  |
| 示例 panel：firm-year 数 → 拿到唯一 strict 部门和地区的 firm-year 数 | 12 | 12 | ✅ 通过 | 无丢失、无重复 |

## 需要 Coco 判断

以下 7 项是检查中发现的异常，按严重程度排列。本次没有修正其中任何一项。

### 1. [高] fic `NGA` 对应 2 个 GLORIA 地区

**异常是什么：** `merge_firms_to_ecp.py` 按 fic 建字典，后出现的行覆盖前面的，所以 `NGA` → Nigeria（Nigeria 能查到只是因为它在文件里排在后面）；Niger 按任何 fic 都查不到，该地区的 firm 拿不到价格。

**涉及的代码：**

| gloria_region | fic | region_type | in_our_list |
|---|---|---|---|
| Niger | NGA | country | yes |
| Nigeria | NGA | country | yes |

**可能的原因：**

- 两个不同国家（region_type 都是 country）共用一个代码，至少有一行填错。
- 按 ISO 3166-1 alpha-3：Niger = NER，Nigeria = NGA。
- Niger 一行的 fic 疑似录入错误；地区表里没有 `NER`。

**需要判断：** 是否要更正这一行的 fic？

### 2. [中] strict 规则按路径行数计数，与 README 的“ISIC class 最多”不一致（40 个 SIC 受影响）

**异常是什么：** `make_strict_crosswalk.py` 数的是 master 的行（脚本说明写的是 “ISIC Rev.4 rows”），而 `data/README.md` 写的是 “the modal candidate (most ISIC classes)”。master 里同一 ISIC class 经过几个 NAICS 码就有几行，所以两种口径会给出不同的 strict 部门。按不同 ISIC class 计数，有 40 个 SIC 的 strict 部门会变，其中 21 个在新口径下又是并列，要靠排列顺序决定。

**涉及的代码：**

<details>
<summary>展开 40 个受影响的 SIC</summary>

| SIC | 标题 | 现行 strict（按行） | 按不同 ISIC class | 新口径下并列 | 已 override |
|---|---|---|---|---|---|
| 0831 | Forest Nurseries and Gathering of Forest Products (forest pr | Forestry and logging（3 行） | Growing crops n.e.c.（2 个 ISIC） | 是 |  |
| 1629 | Heavy Construction, NEC (right-of-way clearing and line slas | Civil engineering construction（8 行） | Building construction（4 个 ISIC） | 否 |  |
| 2034 | Dried and Dehydrated Fruits, Vegetables, and Soup Mixes (sou | Fruit products（3 行） | Food products and feeds n.e.c.（2 个 ISIC） | 否 |  |
| 2499 | Wood Products, NEC (mirror and picture frames) | Sawmill products（6 行） | Furniture and other manufacturing n.e.c（5 个 ISIC） | 否 |  |
| 2531 | Public Building and Related Furniture (blackboards) | Textiles and clothing（3 行） | Other transport equipment（3 个 ISIC） | 是 |  |
| 2819 | Industrial Inorganic Chemicals, NEC (alumina) | Basic organic chemicals（3 行） | Dyes, paints, glues, detergents and other chemical products（3 个 ISIC） | 否 |  |
| 2865 | Cyclic Organic Crudes and Intermediates and Organic Dyes and | Basic organic chemicals（3 行） | Refined petroleum products（1 个 ISIC） | 是 |  |
| 2869 | Industrial Organic Chemicals, NEC (synthetic hydraulic fluid | Basic organic chemicals（7 行） | Dyes, paints, glues, detergents and other chemical products（3 个 ISIC） | 否 |  |
| 3089 | Plastics Products, NEC (inflatable plastic life jackets) | Plastic products（4 行） | Furniture and other manufacturing n.e.c（3 个 ISIC） | 否 |  |
| 3312 | Steel Works, Blast Furnaces (Including Coke Ovens), and Roll | Basic iron and steel（2 行） | Sawmill products（1 个 ISIC） | 是 |  |
| 3315 | Steel Wiredrawing and Steel Nails and Spikes (nails, spikes, | Fabricated metal products（2 行） | Basic iron and steel（1 个 ISIC） | 是 |  |
| 3399 | Primary Metal Products, NEC (laminating steel for the trade) | Basic non-ferrous metals n.e.c.（3 行） | Fabricated metal products（2 个 ISIC） | 否 |  |
| 3497 | Metal Foil and Leaf (foil and foil containers) | Basic non-ferrous metals n.e.c.（2 行） | Fabricated metal products（2 个 ISIC） | 否 |  |
| 3699 | Electrical Machinery, Equipment, and Supplies, NEC (other el | Electrical equipment（7 行） | Machinery and equipment（5 个 ISIC） | 否 |  |
| 3714 | Motor Vehicle Parts and Accessories (except truck and bus bo | Motor vehicles, trailers and semi-trailers（10 行） | Machinery and equipment（3 个 ISIC） | 是 |  |
| 3721 | Aircraft (research and development not producing prototypes) | Professional, scientific and technical services（2 行） | Other transport equipment（1 个 ISIC） | 是 |  |
| 3724 | Aircraft Engines and Engine Parts (research and development  | Professional, scientific and technical services（2 行） | Machinery and equipment（1 个 ISIC） | 是 |  |
| 3728 | Aircraft Parts and Auxiliary Equipment, NEC (research and de | Other transport equipment（2 行） | Basic iron and steel（1 个 ISIC） | 是 |  |
| 3731 | Ship Building and Repairing (repair services provided by flo | Repair and installation of machinery and equipment (service)（2 行） | Services to transport（2 个 ISIC） | 否 |  |
| 3761 | Guided Missiles and Space Vehicles (research and development | Professional, scientific and technical services（2 行） | Other transport equipment（1 个 ISIC） | 是 |  |
| 3764 | Guided Missile and Space Vehicle Propulsion Units and Propul | Professional, scientific and technical services（2 行） | Other transport equipment（1 个 ISIC） | 是 |  |
| 3769 | Guided Missile and Space Vehicle Parts and Auxiliary Equipme | Professional, scientific and technical services（2 行） | Other transport equipment（1 个 ISIC） | 是 |  |
| 3861 | Photographic Equipment and Supplies (except photographic fil | Machinery and equipment（2 行） | Dyes, paints, glues, detergents and other chemical products（1 个 ISIC） | 是 |  |
| 3961 | Costume Jewelry and Costume Novelties, Except Precious Metal | Fabricated metal products（2 行） | Furniture and other manufacturing n.e.c（2 个 ISIC） | 否 |  |
| 3993 | Signs and Advertising Specialties (signs) | Printing（2 行） | Textiles and clothing（1 个 ISIC） | 是 |  |
| 4212 | Local Trucking Without Storage (other waste collection witho | Road transport（3 行） | Waste collection, treatment, and disposal（2 个 ISIC） | 否 |  |
| 5699 | Miscellaneous Apparel and Accessory Stores (miscellaneous ap | Textiles and clothing（3 行） | Wholesale and retail trade; repair of motor vehicles and motorcycles（2 个 ISIC） | 否 |  |
| 5714 | Drapery, Curtain, and Upholstery Stores (upholstery material | Textiles and clothing（2 行） | Wholesale and retail trade; repair of motor vehicles and motorcycles（2 个 ISIC） | 否 |  |
| 6798 | Real Estate Investment Trusts | Property and real estate（4 行） | Finance and insurance（1 个 ISIC） | 是 |  |
| 7231 | Beauty Shops (manicure and pedicure salons) | Other services（2 行） | Education（1 个 ISIC） | 是 |  |
| 7299 | Miscellaneous Personal Services, NEC (except diet and weight | Other services（5 行） | Administrative services（4 个 ISIC） | 否 |  |
| 7319 | Advertising, NEC (except media buying, display advertising,  | Professional, scientific and technical services（4 行） | Air transport（1 个 ISIC） | 是 |  |
| 7334 | Photocopying and Duplicating Services (except quick printing | Administrative services（2 行） | Printing（1 个 ISIC） | 是 |  |
| 7361 | Employment Agencies (except executive placement services) | Administrative services（2 行） | Finance and insurance（1 个 ISIC） | 是 |  |
| 7549 | Automotive Services, Except Repair and Carwashes (except aut | Wholesale and retail trade; repair of motor vehicles and motorcycles（3 行） | Services to transport（1 个 ISIC） | 是 |  |
| 7622 | Radio and Television Repair Shops (telecommunication equipme | Other services（5 行） | Repair and installation of machinery and equipment (service)（3 个 ISIC） | 否 |  |
| 7819 | Services Allied to Motion Picture Production (film directors | Information services（3 行） | Administrative services（3 个 ISIC） | 是 |  |
| 8641 | Civic, Social, and Fraternal Associations (Indian and Alaska | Other services（3 行） | Government; social security; defence; public order（2 个 ISIC） | 否 |  |
| 8741 | Management Services (except construction management) | Civil engineering construction（10 行） | Building construction（4 个 ISIC） | 否 |  |
| 8999 | Services, NEC (authors, artists, and related technical servi | Information services（10 行） | Publishing（5 个 ISIC） | 否 |  |

</details>

**可能的原因：**

- master 是路径表，(SIC, ISIC) 端点对有 882 对重复（见第 4 项）；按行计数等于按 NAICS 路径数加权。
- 两种口径各有道理：按行相当于给“覆盖更多 NAICS 细分行业”的 ISIC 更大权重，按 ISIC class 则与文档描述一致。例如 3312（钢铁）按行计数是 Basic iron and steel，按 ISIC class 计数则 4 个候选并列，排序会选中 Sawmill products。

**需要判断：** strict 规则的本意是哪一种？README 和脚本说明是否需要统一表述？

### 3. [中] 107 个 SIC 的 strict 部门由 Census 排列顺序决定

**异常是什么：** 这些 SIC 的众数候选并列（占 342 个一对多 SIC 的 31.3%），`make_strict_crosswalk.py` 取 Census 表中最先出现的那个。`strict_overrides.csv` 只人工处理了其中 2 个。

**涉及的代码：**

<details>
<summary>展开 107 个并列的 SIC</summary>

| SIC | 标题 | 并列候选数 | 并列候选（按出现顺序） | 现行 strict | override 为 |
|---|---|---|---|---|---|
| 0133 | Sugarcane and Sugar Beets (sugar beet farms) | 2 | Growing sugar beet and cane; Growing vegetables, roots, tubers | Growing sugar beet and cane |  |
| 0191 | General Farms, Primarily Crop | 2 | Growing crops n.e.c.; Fishing | Growing crops n.e.c. |  |
| 0259 | Poultry and Eggs, NEC | 2 | Raising of poultry; Raising of animals n.e.c.; services to agriculture | Raising of poultry |  |
| 0723 | Crop Preparation Services for Market, Except Cotton Ginning  | 3 | Raising of animals n.e.c.; services to agriculture; Seeds and plant propagation; Food products and feeds n.e.c. | Raising of animals n.e.c.; services to agriculture |  |
| 0751 | Livestock Services, Except Veterinary (custom slaughtering) | 3 | Raising of animals n.e.c.; services to agriculture; Professional, scientific and technical services; Other meat products | Raising of animals n.e.c.; services to agriculture |  |
| 0752 | Animal Specialty Services, Except Veterinary (pet care servi | 3 | Raising of animals n.e.c.; services to agriculture; Professional, scientific and technical services; Other services | Raising of animals n.e.c.; services to agriculture |  |
| 0811 | Timber Tracts (long term timber farms) | 3 | Growing crops n.e.c.; Seeds and plant propagation; Forestry and logging | Growing crops n.e.c. |  |
| 1094 | Uranium-Radium-Vanadium Ores | 2 | Uranium ores; Other non-ferrous ores | Uranium ores |  |
| 1099 | Miscellaneous Metal Ores, NEC | 2 | Uranium ores; Other non-ferrous ores | Uranium ores |  |
| 1311 | Crude Petroleum and Natural Gas | 3 | Hard coal; Petroleum extraction; Gas extraction | Hard coal | Petroleum extraction |
| 1382 | Oil and Gas Field Exploration Services (geophysical surveyin | 2 | Mining and quarrying n.e.c.; services to mining; Professional, scientific and technical services | Mining and quarrying n.e.c.; services to mining |  |
| 1422 | Crushed and Broken Limestone | 2 | Quarrying of stone, sand and clay; Chemical and fertilizer minerals | Quarrying of stone, sand and clay |  |
| 1459 | Clay, Ceramic, and Refractory Minerals, NEC | 2 | Quarrying of stone, sand and clay; Mining and quarrying n.e.c.; services to mining | Quarrying of stone, sand and clay |  |
| 1479 | Chemical and Fertilizer Mineral Mining, NEC | 2 | Chemical and fertilizer minerals; Extraction of salt | Chemical and fertilizer minerals |  |
| 1542 | General Contractors - Nonresidential Buildings, Other than I | 2 | Building construction; Civil engineering construction | Building construction |  |
| 1611 | Highway and Street Construction, Except Elevated Highways | 2 | Civil engineering construction; Building construction | Civil engineering construction |  |
| 2022 | Natural, Processed, and Imitation Cheese | 2 | Dairy products; Food products and feeds n.e.c. | Dairy products |  |
| 2033 | Canned Fruits, Vegetables, Preserves, Jams, and Jellies | 2 | Fruit products; Food products and feeds n.e.c. | Fruit products |  |
| 2034 | Dried and Dehydrated Fruits, Vegetables, and Soup Mixes (sou | 2 | Fruit products; Food products and feeds n.e.c. | Fruit products |  |
| 2035 | Pickled Fruits and Vegetables, Vegetable Sauces and Seasonin | 2 | Fruit products; Food products and feeds n.e.c. | Fruit products |  |
| 2041 | Flour and Other Grain Mill Products | 2 | Fruit products; Cereal products | Fruit products |  |
| 2043 | Cereal Breakfast Foods (grain based coffee substitutes) | 2 | Cereal products; Food products and feeds n.e.c. | Cereal products |  |
| 2046 | Wet Corn Milling (refining purchased corn oil) | 2 | Vegetable oils and fats; Food products and feeds n.e.c. | Vegetable oils and fats |  |
| 2048 | Prepared Feeds and Feed Ingredients for Animals and Fowls, E | 2 | Food products and feeds n.e.c.; Other meat products | Food products and feeds n.e.c. |  |
| 2082 | Malt Beverages (except malt extract) | 4 | Extraction of salt; Fruit products; Food products and feeds n.e.c.; Alcoholic and other  beverages | Extraction of salt |  |
| 2096 | Potato Chips, Corn Chips, and Similar Snacks | 2 | Fruit products; Cereal products | Fruit products |  |
| 2295 | Coated Fabrics, Not Rubberized | 2 | Textiles and clothing; Rubber products | Textiles and clothing |  |
| 2393 | Textile Bags | 3 | Textiles and clothing; Leather and footwear; Plastic products | Textiles and clothing |  |
| 2499 | Wood Products, NEC (mirror and picture frames) | 2 | Sawmill products; Furniture and other manufacturing n.e.c | Sawmill products |  |
| 2531 | Public Building and Related Furniture (blackboards) | 3 | Textiles and clothing; Other transport equipment; Furniture and other manufacturing n.e.c | Textiles and clothing |  |
| 2671 | Packaging Paper and Plastics Film, Coated and Laminated (sin | 3 | Pulp and paper; Basic non-ferrous metals n.e.c.; Plastic products | Pulp and paper |  |
| 2673 | Plastics, Foil, and Coated Paper Bags (single-web and multi- | 3 | Pulp and paper; Fabricated metal products; Plastic products | Pulp and paper |  |
| 2819 | Industrial Inorganic Chemicals, NEC (alumina) | 2 | Basic organic chemicals; Dyes, paints, glues, detergents and other chemical products | Basic organic chemicals |  |
| 2823 | Cellulosic Manmade Fibers | 2 | Basic organic chemicals; Plastic products | Basic organic chemicals |  |
| 2861 | Gum and Wood Chemicals | 2 | Basic organic chemicals; Dyes, paints, glues, detergents and other chemical products | Basic organic chemicals |  |
| 2874 | Phosphatic Fertilizers | 2 | Basic organic chemicals; Nitrogenous fertilizers | Basic organic chemicals |  |
| 2999 | Products of Petroleum and Coal, NEC | 3 | Sawmill products; Coke oven products; Refined petroleum products | Sawmill products |  |
| 3052 | Rubber and Plastics Hose and Belting | 2 | Rubber products; Plastic products | Rubber products |  |
| 3053 | Gaskets, Packing, and Sealing Devices | 8 | Textiles and clothing; Leather and footwear; Sawmill products; Pulp and paper; Rubber products; Plastic products; Other non-metallic mineral products n.e.c.; Machinery and equipment | Textiles and clothing |  |
| 3089 | Plastics Products, NEC (inflatable plastic life jackets) | 2 | Plastic products; Furniture and other manufacturing n.e.c | Plastic products |  |
| 3172 | Personal Leather Goods, Except Women's Handbags and Purses ( | 3 | Leather and footwear; Fabricated metal products; Furniture and other manufacturing n.e.c | Leather and footwear |  |
| 3251 | Brick and Structural Clay Tile (slumped brick) | 2 | Clay building materials; Other non-metallic mineral products n.e.c. | Clay building materials |  |
| 3259 | Structural Clay Products, NEC | 2 | Clay building materials; Other non-metallic mineral products n.e.c. | Clay building materials |  |
| 3275 | Gypsum Products | 2 | Cement, lime and plaster products; Other non-metallic mineral products n.e.c. | Cement, lime and plaster products |  |
| 3296 | Mineral Wool | 2 | Glass and other ceramics n.e.c.; Other non-metallic mineral products n.e.c. | Glass and other ceramics n.e.c. |  |
| 3321 | Gray and Ductile Iron Foundries | 2 | Basic iron and steel; Machinery and equipment | Basic iron and steel |  |
| 3322 | Malleable Iron Foundries | 2 | Basic iron and steel; Machinery and equipment | Basic iron and steel |  |
| 3351 | Rolling, Drawing, and Extruding of Copper | 2 | Basic non-ferrous metals n.e.c.; Fabricated metal products | Basic non-ferrous metals n.e.c. |  |
| 3355 | Aluminum Rolling and Drawing, NEC | 3 | Basic non-ferrous metals n.e.c.; Fabricated metal products; Electrical equipment | Basic non-ferrous metals n.e.c. |  |
| 3356 | Rolling, Drawing, and Extruding of Nonferrous Metals, Except | 2 | Basic non-ferrous metals n.e.c.; Fabricated metal products | Basic non-ferrous metals n.e.c. |  |
| 3433 | Heating Equipment, Except Electric and Warm Air Furnaces | 2 | Fabricated metal products; Machinery and equipment | Fabricated metal products |  |
| 3482 | Small Arms Ammunition | 3 | Pulp and paper; Dyes, paints, glues, detergents and other chemical products; Fabricated metal products | Pulp and paper |  |
| 3483 | Ammunition, Except for Small Arms | 2 | Dyes, paints, glues, detergents and other chemical products; Fabricated metal products | Dyes, paints, glues, detergents and other chemical products |  |
| 3492 | Fluid Power Valves and Hose Fittings | 3 | Basic iron and steel; Basic non-ferrous metals n.e.c.; Machinery and equipment | Basic iron and steel |  |
| 3494 | Valves and Pipe Fittings, NEC (metal pipe hangers and suppor | 2 | Machinery and equipment; Fabricated metal products | Machinery and equipment |  |
| 3495 | Wire Springs (clock and watch springs) | 2 | Fabricated metal products; Computers; electronic products; optical and precision instruments | Fabricated metal products |  |
| 3496 | Miscellaneous Fabricated Wire Products (shopping carts made  | 2 | Fabricated metal products; Furniture and other manufacturing n.e.c | Fabricated metal products |  |
| 3497 | Metal Foil and Leaf (foil and foil containers) | 2 | Basic non-ferrous metals n.e.c.; Fabricated metal products | Basic non-ferrous metals n.e.c. |  |
| 3498 | Fabricated Pipe and Pipe Fittings | 2 | Basic iron and steel; Basic non-ferrous metals n.e.c. | Basic iron and steel |  |
| 3519 | Internal Combustion Engines, NEC (stationary engine radiator | 2 | Machinery and equipment; Motor vehicles, trailers and semi-trailers | Machinery and equipment |  |
| 3536 | Overhead Traveling Cranes, Hoists, and Monorail Systems | 2 | Machinery and equipment; Other transport equipment | Machinery and equipment |  |
| 3578 | Calculating and Accounting Machines, Except Electronic Compu | 2 | Machinery and equipment; Computers; electronic products; optical and precision instruments | Machinery and equipment |  |
| 3596 | Scales and Balances, Except Laboratory | 2 | Computers; electronic products; optical and precision instruments; Machinery and equipment | Computers; electronic products; optical and precision instruments |  |
| 3624 | Carbon and Graphite Products | 2 | Other non-metallic mineral products n.e.c.; Electrical equipment | Other non-metallic mineral products n.e.c. |  |
| 3652 | Phonograph Records and Prerecorded Audio Tapes and Disks (in | 2 | Printing; Information services | Printing |  |
| 3694 | Electrical Equipment for Internal Combustion Engines | 2 | Machinery and equipment; Motor vehicles, trailers and semi-trailers | Machinery and equipment |  |
| 3728 | Aircraft Parts and Auxiliary Equipment, NEC (research and de | 2 | Other transport equipment; Professional, scientific and technical services | Other transport equipment |  |
| 3731 | Ship Building and Repairing (repair services provided by flo | 2 | Repair and installation of machinery and equipment (service); Services to transport | Repair and installation of machinery and equipment (service) |  |
| 3743 | Railroad Equipment (except locomotive fuel lubricating or co | 3 | Machinery and equipment; Motor vehicles, trailers and semi-trailers; Other transport equipment | Machinery and equipment |  |
| 3911 | Jewelry, Precious Metal | 2 | Fabricated metal products; Furniture and other manufacturing n.e.c | Fabricated metal products |  |
| 3915 | Jewelers' Findings and Materials, and Lapidary Work (except  | 2 | Computers; electronic products; optical and precision instruments; Furniture and other manufacturing n.e.c | Computers; electronic products; optical and precision instruments |  |
| 3961 | Costume Jewelry and Costume Novelties, Except Precious Metal | 2 | Fabricated metal products; Furniture and other manufacturing n.e.c | Fabricated metal products |  |
| 3965 | Fasteners, Buttons, Needles, and Pins | 3 | Fabricated metal products; Machinery and equipment; Furniture and other manufacturing n.e.c | Fabricated metal products |  |
| 4212 | Local Trucking Without Storage (other waste collection witho | 2 | Road transport; Waste collection, treatment, and disposal | Road transport |  |
| 4225 | General Warehousing and Storage (miniwarehouses and self-sto | 2 | Services to transport; Property and real estate | Services to transport |  |
| 4741 | Rental of Railroad Cars (rental of railroad cars) | 2 | Services to transport; Administrative services | Services to transport |  |
| 4832 | Radio Broadcasting Stations (except networks) | 2 | Information services; Telecommunications | Information services |  |
| 4833 | Television Broadcasting Stations | 2 | Information services; Telecommunications | Information services |  |
| 4923 | Natural Gas Transmission and Distribution (transmission) | 2 | Distribution of gaseous fuels through mains; Transport via pipeline | Distribution of gaseous fuels through mains |  |
| 4941 | Water Supply | 2 | Water collection, treatment and supply; sewerage; Transport via pipeline | Water collection, treatment and supply; sewerage |  |
| 4971 | Irrigation Systems | 2 | Water collection, treatment and supply; sewerage; Transport via pipeline | Water collection, treatment and supply; sewerage |  |
| 5551 | Boat Dealers | 2 | Repair and installation of machinery and equipment (service); Wholesale and retail trade; repair of motor vehicles and motorcycles | Repair and installation of machinery and equipment (service) |  |
| 5699 | Miscellaneous Apparel and Accessory Stores (miscellaneous ap | 2 | Textiles and clothing; Wholesale and retail trade; repair of motor vehicles and motorcycles | Textiles and clothing |  |
| 5714 | Drapery, Curtain, and Upholstery Stores (upholstery material | 2 | Textiles and clothing; Wholesale and retail trade; repair of motor vehicles and motorcycles | Textiles and clothing |  |
| 5722 | Household Appliance Stores | 2 | Wholesale and retail trade; repair of motor vehicles and motorcycles; Other services | Wholesale and retail trade; repair of motor vehicles and motorcycles |  |
| 5736 | Musical Instruments Stores | 2 | Wholesale and retail trade; repair of motor vehicles and motorcycles; Other services | Wholesale and retail trade; repair of motor vehicles and motorcycles |  |
| 5941 | Sporting Goods Stores and Bicycle Shops | 2 | Wholesale and retail trade; repair of motor vehicles and motorcycles; Other services | Wholesale and retail trade; repair of motor vehicles and motorcycles |  |
| 5944 | Jewelry Stores | 2 | Wholesale and retail trade; repair of motor vehicles and motorcycles; Other services | Wholesale and retail trade; repair of motor vehicles and motorcycles |  |
| 5946 | Camera and Photographic Supply Stores | 2 | Repair and installation of machinery and equipment (service); Wholesale and retail trade; repair of motor vehicles and motorcycles | Repair and installation of machinery and equipment (service) |  |
| 5948 | Luggage and Leather Goods Stores | 2 | Wholesale and retail trade; repair of motor vehicles and motorcycles; Other services | Wholesale and retail trade; repair of motor vehicles and motorcycles |  |
| 5995 | Optical Goods Stores (except  labs grinding prescription len | 2 | Furniture and other manufacturing n.e.c; Wholesale and retail trade; repair of motor vehicles and motorcycles | Furniture and other manufacturing n.e.c |  |
| 6792 | Oil Royalty Traders (oil and gas royalty leasing) | 3 | Finance and insurance; Property and real estate; Administrative services | Finance and insurance |  |
| 7219 | Laundry and Garment Services, NEC (diaper service) | 2 | Repair and installation of machinery and equipment (service); Other services | Repair and installation of machinery and equipment (service) |  |
| 7241 | Barber Shops (except barber colleges) | 2 | Education; Other services | Education |  |
| 7322 | Adjustment and Collection Services | 2 | Administrative services; Government; social security; defence; public order | Administrative services |  |
| 7331 | Direct Mail Advertising Services (except mailing list compil | 2 | Publishing; Professional, scientific and technical services | Publishing |  |
| 7335 | Commercial Photography (except using general purpose aircraf | 2 | Air transport; Professional, scientific and technical services | Air transport |  |
| 7372 | Prepackaged Software (software publishing) | 2 | Printing; Publishing | Printing | Publishing |
| 7374 | Computer Processing and Data Preparation and Processing Serv | 2 | Information services; Professional, scientific and technical services | Information services |  |
| 7383 | News Syndicates (independent news correspondents) | 5 | Information services; Furniture and other manufacturing n.e.c; Repair and installation of machinery and equipment (service); Professional, scientific and technical services; Arts, entertainment and recreation | Information services |  |
| 7521 | Automobile Parking | 2 | Services to transport; Other services | Services to transport |  |
| 7532 | Top, Body, and Upholstery Repair Shops and Paint Shops | 2 | Motor vehicles, trailers and semi-trailers; Wholesale and retail trade; repair of motor vehicles and motorcycles | Motor vehicles, trailers and semi-trailers |  |
| 7534 | Tire Retreading and Repair Shops (tire repair) | 3 | Rubber products; Wholesale and retail trade; repair of motor vehicles and motorcycles; Professional, scientific and technical services | Rubber products |  |
| 7819 | Services Allied to Motion Picture Production (film directors | 3 | Information services; Administrative services; Professional, scientific and technical services | Information services |  |
| 8744 | Facilities Support Management Services | 2 | Administrative services; Government; social security; defence; public order | Administrative services |  |
| 8999 | Services, NEC (authors, artists, and related technical servi | 2 | Information services; Publishing | Information services |  |
| 9661 | Space Research and Technology | 2 | Air transport; Government; social security; defence; public order | Air transport |  |

</details>

**可能的原因：**

- 最常见的情形是每个候选部门各由一个 ISIC class 到达（例如已 override 的 1311 原油天然气、7372 软件）；Census 表的行序没有经济含义。

**需要判断：** 是否逐个复核这些代码？可以先只复核在定价辖区里候选价格差别大的那些（需要 ECP 文件来筛）。

### 4. [中] 5 个 ISIC class 内 GLORIA 更细，但只映射到一个部门（66 个 SIC 经过，19 个完全落在其中）

**异常是什么：** isic4_to_gloria.csv 用 relation=1:n(GLORIA finer) 标注了这些 class：GLORIA 在其内部分得更细，但 crosswalk 只给一个部门（多为 n.e.c. 类）。下表列出全部路径都经过这些 class 的 SIC——它们拿不到更细的 GLORIA 部门。

**涉及的代码：**

| ISIC | 标题 | 映射到 |
|---|---|---|
| 0111 | Growing of cereals (except rice), leguminous crops and oil seeds | Growing cereals n.e.c |
| 0729 | Mining of other non-ferrous metal ores | Other non-ferrous ores |
| 1010 | Processing and preserving of meat | Other meat products |
| 2011 | Manufacture of basic chemicals | Basic organic chemicals |
| 2420 | Manufacture of basic precious and other non-ferrous metals | Basic non-ferrous metals n.e.c. |

<details>
<summary>展开 19 个完全落在这些 class 里的 SIC</summary>

| SIC | 标题 | GLORIA 部门 |
|---|---|---|
| 0111 | Wheat | Growing cereals n.e.c |
| 0115 | Corn | Growing cereals n.e.c |
| 0116 | Soybeans | Growing cereals n.e.c |
| 0119 | Cash Grains, NEC (except popcorn, dry pea and bean, oilseed  | Growing cereals n.e.c |
| 1021 | Copper Ores | Other non-ferrous ores |
| 1031 | Lead and Zinc Ores | Other non-ferrous ores |
| 1041 | Gold Ores | Other non-ferrous ores |
| 1044 | Silver Ores | Other non-ferrous ores |
| 2011 | Meat Packing Plants | Other meat products |
| 2812 | Alkalies and Chlorine | Basic organic chemicals |
| 2813 | Industrial Gases | Basic organic chemicals |
| 2816 | Inorganic Pigments (bone and lamp black) | Basic organic chemicals |
| 2895 | Carbon Black | Basic organic chemicals |
| 3331 | Primary Smelting and Refining of Copper | Basic non-ferrous metals n.e.c. |
| 3334 | Primary Production of Aluminum | Basic non-ferrous metals n.e.c. |
| 3339 | Primary Smelting and Refining of Nonferrous Metals, Except C | Basic non-ferrous metals n.e.c. |
| 3341 | Secondary Smelting and Refining of Nonferrous Metals (except | Basic non-ferrous metals n.e.c. |
| 3353 | Aluminum Sheet, Plate, and Foil | Basic non-ferrous metals n.e.c. |
| 3354 | Aluminum Extruded Products | Basic non-ferrous metals n.e.c. |

</details>

**可能的原因：**

- ISIC 4 位码区分不了 GLORIA 的细分，整类只能进一个部门。
- 部分 SIC 标题比 ISIC 更具体，落到的部门名与标题不符，例如 2812 Alkalies and Chlorine、2813 Industrial Gases（无机）→ Basic organic chemicals，0116 Soybeans → Growing cereals n.e.c，3334 Primary Aluminum → Basic non-ferrous metals n.e.c.。

**需要判断：** 这些 SIC 是否要在 SIC 层面直接指定更细的 GLORIA 部门（像 strict_overrides.csv 那样）？铝、铜等 ETS 覆盖的行业价格差异可能较大。

### 5. [中] 3 个 ISIC 代码不是 ISIC Rev.4 class（012X, 014X, 331X）

**异常是什么：** 这些代码在 ISIC Rev.4 里不存在，是组（3 位）一级的占位码。它们让 crosswalk 的 ISIC 数成为 420（README 写“420 ISIC classes”）；标准 4 位码只有 417 个，官方 class 是 419 个。

**涉及的代码：**

| 代码 | 标题 | 映射到的 GLORIA | 同组标准 class 的 GLORIA 部门 | 经过它的 SIC | 对应的 NAICS 2007 |
|---|---|---|---|---|---|
| 012X | Growing of perennial crops | Growing crops n.e.c. | 9 个 class → 5 个部门：Growing beverage crops (coffee, tea etc); Growing crops n.e.c.; Growing fruits and nuts; Growing grapes; Growing spices, aromatic, drug and pharmaceutical crops | `0139`, `0179`, `0191`, `0831`, `0919`, `2099` | `111336`, `111998` |
| 014X | Animal production | Raising of animals n.e.c.; services to agriculture | 7 个 class → 5 个部门：Raising of animals n.e.c.; services to agriculture; Raising of cattle; Raising of poultry; Raising of sheep and goats; Raising of swine/pigs | `0219`, `0279`, `0291` | `112990` |
| 331X | Repair of fabricated metal products, machinery and equipment | Repair and installation of machinery and equipment (service) | 6 个 class → 1 个部门：Repair and installation of machinery and equipment (service) | `1796`, `1799`, `7622` | `238290` |

**可能的原因：**

- Census 的 NAICS 2007 → ISIC Rev.4 对照表对少数 NAICS 码（如 “all other” 类）只给到 ISIC 组一级，构建时用 X 补位。
- 如果同组的标准 class 映射到不同 GLORIA 部门，把整个组放进某一个部门就是一个选择；同组都映射到同一部门时不影响结果。

**需要判断：** 这些占位码的 GLORIA 归属是否可以接受？README 的 ISIC 计数是否要说明其中有非标准码？

### 6. [低] fic `YEM` 对应 2 个 GLORIA 地区

**异常是什么：** `merge_firms_to_ecp.py` 按 fic 建字典，后出现的行覆盖前面的，所以 `YEM` → Yemen Arab Republic/Yemen (1990/1991)（Yemen Arab Republic/Yemen (1990/1991) 能查到只是因为它在文件里排在后面）；DR Yemen (Aden) 按任何 fic 都查不到，该地区的 firm 拿不到价格。

**涉及的代码：**

| gloria_region | fic | region_type | in_our_list |
|---|---|---|---|
| DR Yemen (Aden) | YEM | historical | no |
| Yemen Arab Republic/Yemen (1990/1991) | YEM | historical | no |

**可能的原因：**

- 这些是 GLORIA 的历史地区（国家合并或分立前后的名称），共用今天的 ISO3 代码可能是有意为之。

**需要判断：** 历史地区是否需要按年份区分查找，还是保持现状？

### 7. [低] ISIC 6419 和 6619 用了同一个标题

**异常是什么：** isic4_to_gloria.csv 和 master 中这几个代码的 isic_title 都是 “Other monetary intermediation”。它们映射到同一 GLORIA 部门（Finance and insurance），所以不影响价格，只影响标签。

**涉及的代码：**

| ISIC | 文件中的标题 | ISIC Rev.4 官方标题 | GLORIA | 对应 NAICS 2007 | 经过的 SIC 数 |
|---|---|---|---|---|---|
| 6419 | Other monetary intermediation | Other monetary intermediation | Finance and insurance | `522110`, `522120`, `522130`, `522190`, `522390` | 10 |
| 6619 | Other monetary intermediation | Other activities auxiliary to financial service activities | Finance and insurance | `522310`, `522320`, `523930`, `523991`, `523999` | 9 |

**可能的原因：**

- 标题很可能是从相邻行复制时出错；从对应的 NAICS 码看（如 523930 投资咨询、523991 信托），代码本身是对的，错的是标题。

**需要判断：** 是否更正标题？

## 缺少的数据

下列检查因为仓库里没有相应数据而无法运行（或只能部分运行）。

| 影响的检查 | 缺什么 | 怎样补上 |
|---|---|---|
| 1、3 | `data/ecp/ecp_gloria_edgar_industry_CO2.csv`（Dolphin & Merkle 2024，Zenodo 10.5281/zenodo.12181508） | 用 `--ecp` 指定；可复核 GLORIA 部门名、列出未被映射的 GLORIA 部门和地区名 |
| 1、3 | US Census NAICS 2002 六位代码表 | 用 `--universe naics_2002=PATH` 指定 |
| 1、3 | US Census NAICS 2007 六位代码表 | 用 `--universe naics_2007=PATH` 指定 |
| 1、3 | UNSD ISIC Rev.4 class 代码表（419 个） | 用 `--universe isic_rev4=PATH` 指定 |
| 1、3 | GLORIA 120 个部门名称（ECP 文件的 sector 列即可） | 用 `--universe gloria_sector=PATH` 指定，或给 `--ecp` |
| 2、5 | 一对多链接的权重（每个源代码一组、和为 1 的份额，例如按就业或产值） | 用 `--weights PATH` 指定，列名用 `--weight-src/--weight-dst/--weight-col` 设置。可能来源：Census 1997 Economic Census 的 NAICS–SIC bridge 表（按机构数、销售额、就业给出份额） |
| 5 | 一个按 SIC（或按 firm）给出的数量变量，例如 Compustat 的 emp/sale，或 Census 的行业就业/产值 | 用 `--values PATH --value-key sic --value-col <列名>` 指定；加权 broad 映射另需 `--weights` |

## 附录：跨文件一致性

辅助检查，结果计入第 4 项。

| 项目 | 结果 | 说明 |
|---|---|---|
| master 中每个 ISIC 只对应一个 GLORIA 部门 | ✅ 通过 | 420 个 ISIC |
| master 与 isic4_to_gloria.csv 的 ISIC → GLORIA 一致 | ✅ 通过 | 一致 |
| sic1987_to_isic4_full.csv 与 master 的共同列逐行相同 | ✅ 通过 | sic_1987, sic_title, naics_2002, naics_2007, isic_rev4, isic_title |
| full 文件的 relation（1:1 / 1:n）与不同 ISIC 数一致 | ✅ 通过 | 一致 |
| 按 make_strict_crosswalk.py 的规则重算 strict，与发布文件一致 | ✅ 通过 | 1,005/1,005 一致 |
| strict 文件的 n_candidate_gloria 与 master 一致 | ✅ 通过 | 一致 |
| override 的部门属于该 SIC 的候选集合 | ✅ 通过 | 2/2 |
