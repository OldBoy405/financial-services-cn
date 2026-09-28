# ACCEPTANCE — Equity Research 单 Agent 专家包分层验收

本文件是 CR-2026-001 的分层验收记录位。**只记录实际运行结果**：未运行的项目保持 `待测`，路由通过不提升研究质量状态，任何"静态文本看起来对"都不算运行证据。

状态枚举（四态）：`待测` / `通过` / `不通过` / `需重测`。

---

## 1. 分栏裁决

| 分栏 | 状态 | 证据定位 | 裁决人 |
|---|---|---|---|
| 基线（HEAD/tag/trunk/16 结构/九入口） | 待测 | `README.md` §1 + `test-evidence/cmd-01.log` | Ray |
| 固定样例（四条件 + 合法使用权） | 已核实 | `README.md` §3（原件在忽略区 `out/samples/SAMPLE-01/`，Ray 裁决 2026-09-28） | Ray |
| 包校验 / 本机安装 / 召唤 | 待测 | `test-evidence/cmd-07.log` + 目标版 `expert-manager` 原始回执（见 §3） | Ray |
| 路由（九技能 CN/EN + 守卫 + quickPrompts） | 待测 | `test-evidence/cmd-05.log`、`cmd-06.log` + 客户端会话记录（见 §4） | Ray |
| 研究质量（九项内容/产物） | 待测 | 不在本 CR 范围（后续 CR） | Ray |

约束：`路由=通过` 时研究质量仍为 `待测`；样例任一项 `待确认` 时整体不得判通过。

---

## 2. 九个独立记录位

### SLOT-01 `/earnings` → `earnings-analysis`

```yaml
slot: SLOT-01
skill: earnings-analysis
route-prompt-cn: "帮我做贵州茅台(600519.SH) 2025 年三季报的业绩点评，用扣非口径，数据来自定期报告和交易所披露。"
route-prompt-en: "Write a post-earnings update for Kweichow Moutai (600519.SH), 2025 Q3 results, use the recurring-profit basis and exchange disclosure sources."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-02 `/initiate` → `initiating-coverage`

```yaml
slot: SLOT-02
skill: initiating-coverage
route-prompt-cn: "为宁德时代(300750.SZ)做首次覆盖，只执行 Task 1 公司研究，不要连跑后面的 Task。"
route-prompt-en: "Start an initiation on CATL (300750.SZ) — run Task 1 company research only, do not chain the remaining tasks."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: "缺 Task 2 金融模型时请求 Task 3 估值 → 必须 Stop 并索取模型"
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-03 `/model-update` → `model-update`

```yaml
slot: SLOT-03
skill: model-update
route-prompt-cn: "用刚出的业绩快报更新中国平安(601318.SH)的盈利模型，口径保持归母。"
route-prompt-en: "Update the Ping An Insurance (601318.SH) earnings model with the just-released preliminary results, keep the attributable-profit basis."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-04 `/screen` → `idea-generation`

```yaml
slot: SLOT-04
skill: idea-generation
route-prompt-cn: "在 A 股里筛一批低估值的中盘制造业标的，给出筛选口径和数据来源。"
route-prompt-en: "Screen A-share mid-cap industrials on a low-valuation basis, and state the screening criteria and data source."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-05 `/catalysts` → `catalyst-calendar`

```yaml
slot: SLOT-05
skill: catalyst-calendar
route-prompt-cn: "看一下我自选池未来两周的催化剂日历，包括定期报告披露和限售解禁。"
route-prompt-en: "Show the catalyst calendar for my watchlist over the next two weeks, including scheduled disclosures and lock-up expiries."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-06 `/morning-note` → `morning-note`

```yaml
slot: SLOT-06
skill: morning-note
route-prompt-cn: "写一份今天的 A 股晨会纪要，覆盖隔夜外盘和昨天盘后的披露。"
route-prompt-en: "Draft today's A-share morning note covering the overnight offshore session and yesterday's after-close disclosures."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-07 `/earnings-preview` → `earnings-preview`

```yaml
slot: SLOT-07
skill: earnings-preview
route-prompt-cn: "给比亚迪(002594.SZ)做一份三季报的盘前预览，列出 bull/base/bear 情景。"
route-prompt-en: "Build a pre-earnings preview for BYD (002594.SZ) Q3 results with bull/base/bear scenarios."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-08 `/sector` → `sector-overview`

```yaml
slot: SLOT-08
skill: sector-overview
route-prompt-cn: "写一份 A 股光伏行业的概览报告，5-10 页的量级，标注统计口径来源。"
route-prompt-en: "Produce an A-share solar industry landscape overview at the 5-10 page level, citing the source of each statistic."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

### SLOT-09 `/thesis` → `thesis-tracker`

```yaml
slot: SLOT-09
skill: thesis-tracker
route-prompt-cn: "更新我对招商银行(600036.SH)的多头论点，新增一条上季度的数据点。"
route-prompt-en: "Update my long thesis on China Merchants Bank (600036.SH) with one new data point from last quarter."
date: ""
source-version: ""
evidence-files: []
positive-result: ""
negative-result: ""
adjudicator: ""
state: 待测
research-state: 待测
```

---

## 3. 包校验 / 本机安装 / 召唤记录（G4 填写）

| 项 | 期望记录 | 当前值 |
|---|---|---|
| 目标客户端名称与版本 | 版本号 + 来源 | **WorkBuddy 37.10.3-24**（`D:\Program Files (x86)\WorkBuddy\version`，2026-09-29 读取） |
| `expert-manager` 校验器版本与路径 | 版本 + 可执行位置 | **skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd**（user scope：`C:\Users\GOBAO\.workbuddy\plugins\cache\workbuddy-builtin\skill-expert-manager\5.5.6-…\scripts`） |
| init/validate/register 步骤与原始输出 | 实际命令 + 完整输出 | `out/evidence/host/index.json`（steps + 原始日志 sha256）：validate-installed exit 0（`Expert package is valid!`）、register exit 0（写入 `my-experts/.codebuddy-plugin/marketplace.json`）、package exit 0（24 files → `out/dist/equity-research.zip`）；导出暂存区预装校验 exit 1 为安装前置事实（校验器要求专家位于宿主专家目录下） |
| 本机安装与召唤观察 | 界面/CLI 实际观察 | 安装：包已复制到 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research` 并注册可见；召唤：需 WorkBuddy GUI 交互（专家中心发起会话），留待 Ray 与 cmd-05/06 会话采集同轮执行 |
| author 邮箱、头像来源与授权 | 授权依据 + SHA-256 | author：OldBoy405 <403562935@qq.com>（Ray 2026-09-28 确认）；头像：Ray 本人自绘、可随包分发，PNG 500×610、307,262 字节、SHA-256 `616fd6bb…f3897`（完整值见 `out/evidence/host/index.json` `avatar-authorization`） |

manifest 已按目标校验器 5.5.6 实际 schema 校正：i18n 字段（displayName/profession/displayDescription/defaultInitPrompt/quickPrompts/tags）改 `{zh,en}` 对象、新增 `description` 字段、`categoryId` 取 `08-FinanceInvestment`（12 个合法枚举之一）；`defaultInitPrompt` 与第一条 quickPrompt 逐字相等（SDD §3.1「与第一条 quickPrompt 相同」语义在目标 schema 形态下保持）。校验遗留 1 条非阻断 warning：displayDescription.zh 100 字符（建议 40-50）。

---

## 4. 路由与安全负例记录（G4 填写）

| 项 | 期望记录 | 当前值 |
|---|---|---|
| 18 条 CN/EN 正例逐条输入/响应 | 客户端版本 + 输入 + 输出 + 证据文件/哈希 | 待记录 |
| 三条 quickPrompts（earnings/initiate/model-update） | 各自启动的路径 | 待记录 |
| 歧义请求 | Clarify 追问字段 | 待记录 |
| 缺证券代码或交易所 | Clarify 追问字段 | 待记录 |
| 无授权 / 过期数据 | Stop 理由 | 待记录 |
| `/initiate` Task 3 无 Task 2 模型 | Stop 理由 | 待记录 |
| 无等价数据源 | 明确降级或停机 | 待记录 |
| 美股个股 | 仅公开面声明 | 待记录 |

静态规则核查（`cmd-06` 的一部分，可作为规则一致性证据但不作为动态负例通过依据）：

- 七域优先顺序见 `agents/equity-research.md` §数据域路由；顺序与 PRD FR-06 表逐字一致。
- 同一指标单源、跨源逐项标注日期/来源/口径；无授权、过期、无等价源时 `Stop`。美股个股仅公开面且声明无美系机构能力。
- 负例的**动态**证据必须来自实际客户端会话；只有静态规则文本时 `cmd-05`/`cmd-06` 必须失败。

---

## 5. 研究质量（本 CR 始终待测）

九项研究内容与 DOCX/XLSX 的端到端合格判定不在本 CR 范围（`sdd.md` §8 `scope_out`）。即使 `earnings` 作为产物试点，也只验包与路由，**不**签研究产物质量。本 CR 交付时"研究质量=通过"的项数必须为 **0**。
