# Equity Research 单 Agent 专家包（源工作区）

本目录是 CR-2026-001 的 WorkBuddy 专家**包源**：`.codebuddy-plugin/plugin.json`（manifest）、`agents/equity-research.md`（唯一 Agent）、`README.md`（基线/映射/样例索引）、`avatars/expert.png`（头像，待授权提供）、`ACCEPTANCE.md`（分层验收记录位）。

技能正文的唯一可编辑位置仍是 `plugins/vertical-plugins/equity-research/skills/`；本目录不复制技能正文，只在导出时从该唯一源读取（见 `scripts/export_workbuddy_experts.py`）。

---

## 1. 基线（BaselineEvidence）

<!-- baseline-evidence:start -->
```yaml
upstream-repo: https://github.com/anthropics/financial-services.git
source-head-sha: 574ed3624aebd0418c7e96cd101262f30210ab26
baseline-tag: baseline/upstream-574ed36
baseline-tag-object-sha: 6ca92532bb7cb43fdb9ef0a61411a4cab2b2070e
baseline-tag-commit-sha: 574ed3624aebd0418c7e96cd101262f30210ab26
target-trunk: workbuddy/main
target-trunk-sha: e03543279019854bb2b14be5aa249d22516ce98f
trunk-merge-base-sha: 574ed3624aebd0418c7e96cd101262f30210ab26
cr-branch: requirement/CR-2026-001
collected-at: "2026-09-28T21:20:00+08:00"
collected-by: dev-agent
structure:
  vertical-plugins: 6
  agent-plugins: 10
  equity-research-commands: 9
  equity-research-skills: 9
```
<!-- baseline-evidence:end -->

**采集事实（本轮实测，命令与出口码见 `ACCEPTANCE.md` 基线分栏）**

| 事实 | 值 | 取证方式 |
|---|---|---|
| 原源仓库 | `anthropics/financial-services`（remote `upstream`） | `git remote -v` |
| 原源 HEAD（40 位） | `574ed3624aebd0418c7e96cd101262f30210ab26` | `upstream/main` 解析值 |
| baseline tag | `baseline/upstream-574ed36`（附注 tag） | `rev-parse --verify refs/tags/baseline/upstream-574ed36` |
| tag 对象 SHA | `6ca92532bb7cb43fdb9ef0a61411a4cab2b2070e` | 同上（tag 对象） |
| tag 解析（peel）后 SHA | `574ed3624aebd0418c7e96cd101262f30210ab26` | `rev-parse --verify refs/tags/baseline/upstream-574ed36^{commit}` |
| 目标 trunk | `workbuddy/main` = `e03543279019854bb2b14be5aa249d22516ce98f` | `rev-parse origin/workbuddy/main` |
| trunk 与原源关系 | merge-base = `574ed36…`，即 `workbuddy/main` = 原源 HEAD + 本地提交 `e035432`（"方案文档"） | `merge-base origin/workbuddy/main upstream/main` |
| CR 工作分支 | `requirement/CR-2026-001` | `rev-parse --abbrev-ref HEAD` |

tag 写入由已获授权的平台通道完成（tag 不在 `crctl git` 白名单内，本 CR 不写 tag）；测试只做只读 `rev-parse --verify` 反查，tag 目标与上表 40 位源 SHA 必须相同。

**结构盘点（16 专家结构未改动）**

- 6 个 vertical：`equity-research`、`financial-analysis`、`fund-admin`、`investment-banking`、`operations`、`private-equity`（`.claude-plugin/marketplace.json` 的 6 条 vertical 条目）。
- 10 个具名 Agent：`earnings-reviewer`、`gl-reconciler`、`kyc-screener`、`market-researcher`、`meeting-prep-agent`、`model-builder`、`month-end-closer`、`pitch-agent`、`statement-auditor`、`valuation-reviewer`。
- marketplace 共 19 条目 = 16 个专家（6 vertical + 10 具名 Agent，本 CR 不改变其清单条目与目录形态）+ 2 条 `partner-built`（`lseg`、`sp-global`）+ 1 条 `claude-for-msft-365-install` 安装工具（三者均不在本 CR 范围，保持原样）。
- `equity-research` 9 组入口（命令 → 技能）：`commands/*.md` 9 个、`skills/*/SKILL.md` 9 个，另含 `hooks/hooks.json` 与 `.claude-plugin/plugin.json`（Claude 插件元信息，不是 WorkBuddy manifest）。
- 数据源引用盘点：vertical 目录下**没有** `connectors/` 目录；`.mcp.json` 不存在。可复用能力来自 `plugins/agent-plugins/{earnings-reviewer,market-researcher}/`（具名 Agent 及其捆绑副本，本 CR 只同步受影响副本，不复制为 Team）。

---

## 2. 九项映射（MappingRow，恰九项）

固定九行（顺序与 PRD FR-02 表一致）；每行扩展见 §2.1～§2.9。状态枚举：`接受` / `明确缺口` / `待验`。

| # | 原命令 | 唯一技能 | 状态 | 验收方法 |
|---|---|---|---|---|
| 1 | `/earnings` | `earnings-analysis` | 明确缺口 | cmd-02 + cmd-05（客户端 CN/EN 路由） |
| 2 | `/initiate` | `initiating-coverage` | 明确缺口 | cmd-02 + cmd-05（含 Task 2→3 守卫） |
| 3 | `/model-update` | `model-update` | 明确缺口 | cmd-02 + cmd-05 |
| 4 | `/screen` | `idea-generation` | 明确缺口 | cmd-02 + cmd-05 |
| 5 | `/catalysts` | `catalyst-calendar` | 明确缺口 | cmd-02 + cmd-05 |
| 6 | `/morning-note` | `morning-note` | 明确缺口 | cmd-02 + cmd-05 |
| 7 | `/earnings-preview` | `earnings-preview` | 明确缺口 | cmd-02 + cmd-05 |
| 8 | `/sector` | `sector-overview` | 明确缺口 | cmd-02 + cmd-05 |
| 9 | `/thesis` | `thesis-tracker` | 明确缺口 | cmd-02 + cmd-05 |

> §3.3 数据域优先级（`wind-finance → neodata → tdx-connector F10` 等七域）在 `agents/equity-research.md` 声明，各 MappingRow 的"A/H 机制与数据源"只引用域，不重复列路由表。

### 2.1 MR-01 `/earnings` → `earnings-analysis`

```yaml
row: MR-01
command: /earnings
skill: earnings-analysis
source-files: [plugins/vertical-plugins/equity-research/commands/earnings.md, plugins/vertical-plugins/equity-research/skills/earnings-analysis/SKILL.md]
ah-mechanism: 定期报告（年报/中报/季报）+ 业绩预告/快报 + 交易所互动平台问答；A 股五档评级（买入/增持/中性/减持/卖出）与 CNY 目标价；H 股按港交所披露易公告与 HKD 目标价
ah-data-domains: [机构财务/公告/事件, 券商一致预期, 公开行情/K线/公告/日历]
input-followups: [证券代码+交易所（沪深北/港交所）, 报告期（如 2025Q3/2025H1）, 财报类型（正式定期报告或业绩快报/预告）, 数据口径（扣非/归母、合并/母公司）, 数据来源与授权说明]
required-data: [最近一期定期报告, 业绩预告或快报（若有）, 一致预期（同口径、带日期）, 定期报告全文与公告日历, 上一期与本期的量化对比口径]
source-date: 每张图表与表格标注来源与日期（公告日期、披露平台、一致预期生成日期）
kept-behavior: [24-48 小时快速更新节奏, beat/miss 量化, 1-3 张摘要表, 8-12 张图, 8-12 页, Sources 段（引用与来源清单，每个图表标注文档与日期）, DOCX 报告 + 文字摘要, 发布后三个月时效规则, transcript/纪要日期与发布日期的对应核对, 八项交付前质检]
cn-equivalence: 篇幅锚由"8-12 页 / 3,000-5,000 英文词"改为"8-12 页 / 3,000-5,000 中文汉字（含图表标签与中文文件名）"；评级与目标价货币改为 A 股五档 + CNY（H 股为 HKD）；"10-Q/EDGAR 链接"改为"定期报告全文 + 交易所披露页链接"
gaps: [options-implied move 无 A/H 等价项（标缺口，不造数）; 盘前/盘后价格序列在 A/H 主要交易所无等价序列（标缺口）; 电话会 transcript 在 A 股多不公开，以业绩说明会/互动平台问答替代并标注替代性质]
status: 明确缺口
acceptance-method: cmd-02 核对本行九字段与源文件实际约束；cmd-05 用 CN/EN 各一条请求核对唯一技能选择
```

### 2.2 MR-02 `/initiate` → `initiating-coverage`

```yaml
row: MR-02
command: /initiate
skill: initiating-coverage
source-files: [plugins/vertical-plugins/equity-research/commands/initiate.md, plugins/vertical-plugins/equity-research/skills/initiating-coverage/SKILL.md]
ah-mechanism: A/H 股可比公司与行业口径；两融余额、增减持、NMPA（医药）/行业审批、限售解禁、业绩预告/快报、央行/LPR/国常会、盘后披露及次日反应等机制须显式对照
ah-data-domains: [机构财务/公告/事件, 研报评级/目标价/全文, 公开行情/K线/公告/日历, 宏观]
input-followups: [证券代码+交易所, 本次要执行的 Task（1-5 中唯一一个）, 已完成的前序产物（如 Task 3 需 Task 2 的 .xlsx 金融模型）, 口径（合并/母公司、扣非/归母）, 数据来源与授权说明]
required-data: [Task 1: 公司/管理层/行业公开资料, Task 2: 历史财报与假设输入, Task 3: Task 2 的模型文件, Task 4: 图表数据源, Task 5: 前四步产物]
source-date: 每份外部资料与每张图标注来源与日期
kept-behavior: [Task 1-5 每次仅执行一个、逐步等待用户（五次独立人工关口）, Task 3 缺 Task 2 金融模型即停机索取, 前置输入核验协议, 不做端到端连跑, 五份产物类别（研究文档 .md / 模型 .xlsx / 估值分析 .md+Excel 页 / 图表 .zip / 最终报告 .docx）, 不额外产出"完成总结"等文档]
cn-equivalence: 估值方法与目标价货币改为 CNY（A 股）/HKD（H 股）；SEC/EDGAR 资料改为交易所定期报告与披露平台；可比公司取 A/H 同行业清单并标注口径差异；中文交付文件名与图表标签
gaps: [两融/限售解禁/业绩预告等机制的可得性取决于域授权，未获授权时停机而非替代; options-implied move 无等价项（标缺口）; 美股机构数据能力不声明]
status: 明确缺口
acceptance-method: cmd-02 核对 Task 1-5 分开发起与 Task 2→3 守卫；cmd-05 用 CN/EN 各一条请求核对唯一技能选择
```

### 2.3 MR-03 `/model-update` → `model-update`

```yaml
row: MR-03
command: /model-update
skill: model-update
source-files: [plugins/vertical-plugins/equity-research/commands/model-update.md, plugins/vertical-plugins/equity-research/skills/model-update/SKILL.md]
ah-mechanism: 定期报告/业绩预告驱动的假设更新；CNY（A 股）/HKD（H 股）计价；扣非与归母口径并行
ah-data-domains: [机构财务/公告/事件, 券商一致预期]
input-followups: [目标公司与交易所, 现有模型文件（前序产物）, 本次更新的驱动事件（业绩预告/快报/定期报告/一致预期变更）, 更新口径, 数据来源与授权说明]
required-data: [上一版模型, 驱动事件原始披露, 一致预期（带日期与口径）]
source-date: 每项假设改动标注来源与日期
kept-behavior: [只在明确驱动事件下更新, 记录改动理由与前后估算, 不覆盖历史版本]
cn-equivalence: 美元/美系一致预期来源改为 CNY/HKD 与境内一致预期源；披露文件改为交易所定期报告/业绩预告；英文篇幅锚改为中文等价
gaps: [一致预期口径未经核对不得与他源混用; 无授权时停机]
status: 明确缺口
acceptance-method: cmd-02 核对本行九字段；cmd-05 用 CN/EN 请求核对唯一技能选择（含 quickPrompt 路径）
```

### 2.4 MR-04 `/screen` → `idea-generation`

```yaml
row: MR-04
command: /screen
skill: idea-generation
source-files: [plugins/vertical-plugins/equity-research/commands/screen.md, plugins/vertical-plugins/equity-research/skills/idea-generation/SKILL.md]
ah-mechanism: 筛选因子改用 A/H 可得字段（市值、行业分类、涨跌幅、估值分位、两融/资金指标仅在授权域可用），等价口径未核实即停机
ah-data-domains: [筛选, 公开行情/K线/公告/日历]
input-followups: [方向（多/空）、行业或主题、风格（价值/成长）、市值区间、筛选口径与数据源、授权说明]
required-data: [筛选条件定义, 标的池范围（A 股/H 股）, 字段口径与计算时点]
source-date: 结果每条标注数据源与计算日期
kept-behavior: [输出候选清单与理由, 标注数据来源, 不把筛选结果当研究结论]
cn-equivalence: 美系 screener 字段改为境内可用字段；筛选工具名 `westock-tool`/`tdx-connector`/`wind-finance` 分层声明
gaps: [筛选等价口径未核实即停机，不偷偷替换工具; 无授权域不返回数据]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

### 2.5 MR-05 `/catalysts` → `catalyst-calendar`

```yaml
row: MR-05
command: /catalysts
skill: catalyst-calendar
source-files: [plugins/vertical-plugins/equity-research/commands/catalysts.md, plugins/vertical-plugins/equity-research/skills/catalyst-calendar/SKILL.md]
ah-mechanism: 定期报告披露排期、业绩预告窗口、解禁日、股东大会、央行/LPR/国常会等公开日历事件；覆盖范围为自选股清单
ah-data-domains: [公开行情/K线/公告/日历, 机构财务/公告/事件, 宏观]
input-followups: [时间窗（默认未来两周）, 覆盖标的清单, 事件类型范围, 数据来源与授权说明]
required-data: [标的清单, 事件日历数据源, 已公告事件与预计事件区分]
source-date: 每个事件标注来源与公告/预计日期
kept-behavior: [按影响程度分级色标, 归档已发生事件的实际结果, 覆盖范围默认自选股]
cn-equivalence: 美元事件金额改为 CNY/HKD；美系日历来源改为境内公告日历与宏观日历
gaps: [未公告事件的日期为预计，须标注"预计"而非公告事实; 无授权时不取用私有日历数据]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

### 2.6 MR-06 `/morning-note` → `morning-note`

```yaml
row: MR-06
command: /morning-note
skill: morning-note
source-files: [plugins/vertical-plugins/equity-research/commands/morning-note.md, plugins/vertical-plugins/equity-research/skills/morning-note/SKILL.md]
ah-mechanism: 隔夜外盘与境内盘前信息、前一日盘后披露、当日公告；A/H 交易时段差异须显式说明
ah-data-domains: [公开行情/K线/公告/日历, 资金/龙虎榜/两融]
input-followups: [覆盖标的或范围, 日期（默认当日）, 需要的栏目（隔夜、盘后披露、交易想法）, 数据来源与授权说明]
required-data: [上一交易日行情与公告, 隔夜外盘数据（若引用须标来源）, 资金/两融数据（若在授权域）]
source-date: 每条资讯标注来源与时间
kept-behavior: [简洁早报体裁, 覆盖隔夜动态/业绩反应/交易想法, 不输出未核实的交易建议]
cn-equivalence: 美元/美系指数改为以 A/H 为主、外盘为参考并标注；交易时段差异显式说明
gaps: [盘前/盘后价格序列无等价项（标缺口）; 资金/龙虎榜/两融有覆盖缺口须标注]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

### 2.7 MR-07 `/earnings-preview` → `earnings-preview`

```yaml
row: MR-07
command: /earnings-preview
skill: earnings-preview
source-files: [plugins/vertical-plugins/equity-research/commands/earnings-preview.md, plugins/vertical-plugins/equity-research/skills/earnings-preview/SKILL.md]
ah-mechanism: 预约披露日/业绩预告/快报驱动的盘前预览；一致预期以境内口径（带日期）为准
ah-data-domains: [机构财务/公告/事件, 券商一致预期]
input-followups: [证券代码+交易所, 报告期, 关注的关键指标, 一致预期来源与口径, 授权说明]
required-data: [预约披露日期或预告, 一致预期, 上期对比基数]
source-date: 一致预期与预告均标注来源与日期
kept-behavior: [bull/base/bear 情景, 关键指标观察清单, 不含已发布结果的结论]
cn-equivalence: 美元预期改为 CNY/HKD；美系一致预期来源改为境内可得来源并标注口径
gaps: [预告/快报覆盖不全时以定期报告为准并标注; 无等价数据源时停机]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

### 2.8 MR-08 `/sector` → `sector-overview`

```yaml
row: MR-08
command: /sector
skill: sector-overview
source-files: [plugins/vertical-plugins/equity-research/commands/sector.md, plugins/vertical-plugins/equity-research/skills/sector-overview/SKILL.md]
ah-mechanism: 行业规模与竞争格局以境内行业协会/统计口径与上市公司披露为准，标注口径来源；主题研究须区分政策驱动与景气驱动
ah-data-domains: [研报评级/目标价/全文, 公开行情/K线/公告/日历, 宏观]
input-followups: [行业/子行业范围, 用途（客户报告/内部研究）, 深度（5-10 页概览或 20-30 页深挖）, 视角（中性概览或主题观点）, 是否含非上市主体]
required-data: [行业规模与增速来源, 主要公司清单与财务事实, 政策与事件时间线]
source-date: 每项规模/份额数据标注来源与年份
kept-behavior: [市场规模/增长、竞争格局、关键玩家、主题趋势四段结构, 概览/深挖两档深度]
cn-equivalence: 美元市场规模改为 CNY/HKD 并标注统计口径；美系行业分类改为境内行业分类并标注映射差异
gaps: [非上市主体数据可得性受限须标注; 主题观点不得当作研究结论发布]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

### 2.9 MR-09 `/thesis` → `thesis-tracker`

```yaml
row: MR-09
command: /thesis
skill: thesis-tracker
source-files: [plugins/vertical-plugins/equity-research/commands/thesis.md, plugins/vertical-plugins/equity-research/skills/thesis-tracker/SKILL.md]
ah-mechanism: 论点支柱与风险以 A/H 可得数据点（定期报告、公告、政策事件）跟踪；目标价与止损触发以 CNY/HKD 表达
ah-data-domains: [公开行情/K线/公告/日历, 机构财务/公告/事件]
input-followups: [标的与交易所, 方向（多/空）, 新数据点或待复核论点, 目标价/止损口径, 授权说明]
required-data: [论点支柱与风险清单, 新数据点原始来源, 估值口径]
source-date: 每个数据点标注来源与日期
kept-behavior: [论点计分卡, 更新日志（日期/数据点/影响/动作/信心）, 催化剂日历, 至少季度复核, 可证伪性要求]
cn-equivalence: 美元目标价/止损改为 CNY（A 股）/HKD（H 股）；英文晨会/投委会格式改为中文等价模板
gaps: [大股东增减持、股权质押等 A 股特有数据点依赖授权域，未授权时标注缺失]
status: 明确缺口
acceptance-method: cmd-02 核对本行；cmd-05 用 CN/EN 请求核对唯一技能选择
```

---

## 3. 固定样例（SampleIndex）

<!-- sample-index:start -->
```yaml
sample-id: SAMPLE-01
status: 已核实
securities-code: "603599"
exchange: SH
disclosure-date: 2026-04-27
verified-at: 2026-09-28
source-and-version: 巨潮资讯网，2025 年年报原件（广信股份 2026-04-27 披露）
selection-rationale: 公司简单经营健康
original-relative-path: out/samples/SAMPLE-01/
original-files: [out/samples/SAMPLE-01/603599_20260427_SSAP.pdf::473cac8783fe3f971a036f6819be5ddbb59745f288603921202137ead64df226]
conditions:
  latest-complete-disclosure: 已核实
  research-coverage-sufficient: 已核实
  wind-queryable: 已核实
  legal-usage-right: 已核实
conditions-evidence:
  latest-complete-disclosure: 巨潮资讯网 2026-04-27 披露的 2025 年年报，原件落盘 out/samples/SAMPLE-01/603599_20260427_SSAP.pdf（SHA-256 见 original-files）
  research-coverage-sufficient: 近半年覆盖研报超过 10 篇，最近一份 2026-08-25，来源慧博检索页（research-page）
  wind-queryable: 2026-09-28 在慧博（hibor.com.cn）检索到该标的该期报告；实际可复核渠道为慧博而非 Wind，按实际渠道如实记录（research-page）
  legal-usage-right: 交易所公开披露渠道取得的公开文件，允许本机自用
research-page: https://www.hibor.com.cn/newweb/HuiSou/s?gjc=广信股份&sslb=1&sjfw=24&cxzd=qb%28qw%29&px=zh&bgys=&gs=&sdhy=&sdgs=&sdhgcl=&mhss=&hy=&gp=
adjudicator: Ray
```
<!-- sample-index:end -->

**四条件逐项核验表（任一项待确认即不得判样例通过）**

| 条件 | 需要的可复核依据 | 当前状态 | 裁决人 |
|---|---|---|---|
| 最近完整披露 | 定期报告披露日期与完整报告原文位置（披露平台 + 日期） | 已核实：巨潮资讯网 2026-04-27 披露 2025 年年报，原件在 `out/samples/SAMPLE-01/` | Ray |
| 研报覆盖充分 | 覆盖该标的的研报数量与最近一份研报日期及来源 | 已核实：近半年超过 10 篇，最近 2026-08-25，来源慧博检索页 | Ray |
| 研报可查 | 检索日期 + 在可复核渠道检索到该标的对应报告期的记录 | 已核实：2026-09-28 在慧博（hibor.com.cn）检索到该标的该期报告 | Ray |
| 合法使用权 | 样例原件使用权的可核查依据（不依赖机构连接器许可） | 已核实：交易所公开披露渠道取得的公开文件，允许本机自用 | Ray |

说明：第三项条件在本索引中的机器键名沿用 `wind-queryable`（测试接口常量），但实际可复核渠道是**慧博**（hibor.com.cn）而非 Wind 终端；按「如实记录、不伪称渠道」原则，证据与上表均按慧博记载。检索页链接见上方机器块 `research-page`。

**原件位置与版本化边界**：样例原件只放 `.gitignore` 覆盖的 `out/` 独立样例区（相对路径 `out/samples/SAMPLE-01/`），**不**提交原件、**不**复制进分发包、**不**版本化商业正文；本索引只保存上述元数据与证据定位。`original-files` 每项格式为 `<仓库根相对路径>::<sha256>`，四项条件核验为 `已核实` 且 `adjudicator` 已填（Ray，2026-09-28）。

**当前事实**：Ray 已于 2026-09-28 提供样例原件与四条件逐项依据（见本节机器块与核验表），`out/samples/SAMPLE-01/603599_20260427_SSAP.pdf` 已落盘并登记 SHA-256；`cmd-03` 按 AC-03 复核原件、哈希与四项裁决。

---

## 4. 标识分层与不含项

- `westock-data`、`westock-tool` 是**数据域路由名**（Agent 层，见 §3.3 表）；`westock-mcp` 是 **manifest 连接器 ID**（宿主层）。两者不同层，不互相重命名、不假设等价；目标平台校验冲突时按合同阻断上报。
- manifest 不含 `teamInfo`、`dependencies.mcpServers`、旧 `tools:` 字段、`.mcp.json`、美系 MCP、开发机绝对路径或凭据；不含 `commands/`。
- 研究内容质量（九项）在本 CR 始终为 `待测`；路由命中不提升研究质量状态。

## 5. 导出与宿主联调记录（G4，2026-09-29）

- **真实导出成功**：`python scripts/export_workbuddy_experts.py --repo-root .` → 24 file(s)，0.06s，输出忽略区 `out/workbuddy-experts/equity-research/`；manifest 与 Agent、README、头像、九个完整技能目录（含 references/assets）齐备，无 ACCEPTANCE/tests/样例原件。
- **manifest 按目标校验器实际 schema 校正**（validate_expert.py 5.5.6-wb.38337834.g5f969292.h7826dc9400fd）：i18n 字段（`displayName`/`profession`/`displayDescription`/`defaultInitPrompt`/`quickPrompts`/`tags`）为 `{zh,en}` 对象、新增目标必填 `description` 字段（SDD §3.1 认可）、`categoryId=08-FinanceInvestment`（目标 12 枚举之一）；`defaultInitPrompt` 与第一条 quickPrompt 逐字相等。四连接器 ID 声明不变；校验器无连接器 ID 检查项。
- **头像追溯**：`avatars/expert.png`（PNG 500×610、307,262 字节、SHA-256 `616fd6bbe88fd811ecbb97defb7bbe815c5c9c05368bc33569341e43877f3897`），来源/授权方 Ray 本人（自绘授权），范围可随包分发；装进客户端后的专家中心渲染目视验收留观。
- **宿主回执**：`out/evidence/host/index.json`（client WorkBuddy 37.10.3-24；validate-installed exit 0、register exit 0、package exit 0 → `out/dist/equity-research.zip` 24 files/429.2KB；各步原始日志含 sha256）。安装位：`~/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research`，marketplace.json 已登记。
- **未完成（下一轮）**：客户端召唤与 18 条 CN/EN 正例 + 负例会话采集（cmd-05/06 动态证据），需 WorkBuddy GUI 交互。
