# ACCEPTANCE — Equity Research 单 Agent 专家包分层验收

本文件是 CR-2026-001 的分层验收记录位。**只记录实际运行结果**：未运行的项目保持 `待测`，路由通过不提升研究质量状态，任何"静态文本看起来对"都不算运行证据。

状态枚举（四态）：`待测` / `通过` / `不通过` / `需重测`。

**证据定位约定（TASK-04 §3.5）**：原始客户端会话与宿主回执存于忽略区 `out/`（不版本化）；版本化核查入口 = 本文件 §2 九槽位的 `date/source-version/evidence-files/positive-result`、§3 宿主记录、§4 表与 §4.1/§4.2 逐条索引（相对路径 + SHA-256），据此可复核忽略区原件。

**证据定位约定（TASK-04 §3.5）**：原始客户端会话与宿主回执存于忽略区 `out/`（不版本化）；版本化核查入口 = 本文件 §2 九槽位的 `date/source-version/evidence-files/positive-result`、§3 宿主记录、§4 表与 §4.1/§4.2 逐条索引（相对路径 + SHA-256），据此可复核忽略区原件。

---

## 1. 分栏裁决

| 分栏 | 状态 | 证据定位 | 裁决人 |
|---|---|---|---|
| 基线（HEAD/tag/trunk/16 结构/九入口） | 待测 | `README.md` §1 + `test-evidence/cmd-01.log` | Ray |
| 固定样例（四条件 + 合法使用权） | 已核实 | `README.md` §3（原件在忽略区 `out/samples/SAMPLE-01/`，Ray 裁决 2026-09-28） | Ray |
| 包校验 / 本机安装 / 召唤 | 待测 | `test-evidence/cmd-07.log` + 目标版 `expert-manager` 原始回执（见 §3） | Ray |
| 路由（九技能 CN/EN + 守卫 + quickPrompts） | 待测 | `test-evidence/cmd-05.log`、`cmd-06.log` + 客户端会话记录（§4 表 + §4.1/§4.2 逐条索引） | Ray |
| 研究质量（九项内容/产物） | 待测 | 不在本 CR 范围（后续 CR） | Ray |

约束：`路由=通过` 时研究质量仍为 `待测`；样例任一项 `待确认` 时整体不得判通过。

---

## 2. 九个独立记录位

守卫前提（SDD §3.2 / AC-05，B-04 修正）：每条正例问法自带「模拟授权前提」语句，逐槽位的时效与来源/口径前提记在 `guard-premises`；采集到的响应必须记录守卫判定（含授权前提与时效），缺任一前提的正例不得计为路由通过。

**v2 采集待重采**：现行 §4.1 索引的 18 条正例来自 2026-09-29T10:15 会话记录，其问法无模拟授权前提、SLOT-01 报告期超出三个月时效窗口（B-04）；客户端实际召唤 UI 观察亦未取得（B-05，`out/evidence/host/index.json` 的 `summon.status=pending-interactive-client-session`）。按本版 §2 问法重采并取到宿主观察后，再引用 §4.1 作为正例证据；此前 §1 的「包校验 / 本机安装 / 召唤」与「路由」两栏不得计为通过。

### SLOT-01 `/earnings` → `earnings-analysis`

```yaml
slot: SLOT-01
skill: earnings-analysis
route-prompt-cn: "帮我做贵州茅台(600519.SH) 2026 年半年报的业绩点评，用扣非口径，数据来自定期报告和交易所披露。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Write a post-earnings update for Kweichow Moutai (600519.SH), 2026 H1 results, use the recurring-profit basis and exchange disclosure sources. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=2026H1（定期报告发布后三个月内）；来源/口径=扣非口径、定期报告与交易所披露"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-01-cn.json::d8b4ae78fbaac2a3ed5696589ea7609538a240cbe196e3ac1966a75af8a2e932", "out/evidence/client-sessions/sessions/positive/slot-01-en.json::ce6b322e2beac2100e62ff4dde3b7701b86e835b80b6b0085aba247207734f62"]
positive-result: "Route(唯一 skill: earnings-analysis)。守卫判定：证券/交易所=600519.SH（上交所）；报告期=2025Q3；来源/口径=扣非口径；定期报告与交易所披露。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: earnings-analysis). Guards: ticker/exchange=600519.SH (SSE); period=2025 Q3; source/basis=recurring-profit basis; periodic reports & exchange disclosures. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-02 `/initiate` → `initiating-coverage`

```yaml
slot: SLOT-02
skill: initiating-coverage
route-prompt-cn: "为宁德时代(300750.SZ)做首次覆盖，只执行 Task 1 公司研究，不要连跑后面的 Task。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Start an initiation on CATL (300750.SZ) — run Task 1 company research only, do not chain the remaining tasks. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=不适用（首次覆盖框架）；来源/口径=公司研究；Task 1～5 单次发起"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-02-cn.json::e114828d95a3eaf6b735de7e76b9b581f0c7a38aabfc2a7a5da7083925501a10", "out/evidence/client-sessions/sessions/positive/slot-02-en.json::4cc9eb341abd85bc9af19dd2b1f77ee02ffb46edfd81592d1d592291a5d0ed0c"]
positive-result: "Route(唯一 skill: initiating-coverage)。守卫判定：证券/交易所=300750.SZ（深交所）；报告期=Task 1（首次覆盖阶段）；来源/口径=公司研究；Task 1～5 每次只发起一个，不自动连跑。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: initiating-coverage). Guards: ticker/exchange=300750.SZ (SZSE); period=Task 1; source/basis=company research only; one Task at a time, no auto-chaining. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "`Stop(missing-prerequisite-model)`（缺 Task 2 模型请求 Task 3，不自动连跑）；证据 `out/evidence/client-sessions/sessions/negative/neg-initiate-task3-without-model.json::f1bf30b03c7f67918eef05a44866dea018b9d5b6c52f1f5e713b610b768d3928`（完整响应见 §4.2）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-03 `/model-update` → `model-update`

```yaml
slot: SLOT-03
skill: model-update
route-prompt-cn: "用刚出的业绩快报更新中国平安(601318.SH)的盈利模型，口径保持归母。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Update the Ping An Insurance (601318.SH) earnings model with the just-released preliminary results, keep the attributable-profit basis. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=最新披露期（业绩快报）；来源/口径=归母口径"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-03-cn.json::2b5c943540139e80746eb173c27e4f7bc5e9023a591d4085b2625714023ff5a3", "out/evidence/client-sessions/sessions/positive/slot-03-en.json::bd8ec116c0703cb6a615e2101e4a2b88f6cb16ea72cebd6fc021e66421d0d02b"]
positive-result: "Route(唯一 skill: model-update)。守卫判定：证券/交易所=601318.SH（上交所）；报告期=业绩快报（最新披露期）；来源/口径=归母口径。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: model-update). Guards: ticker/exchange=601318.SH (SSE); period=preliminary results (latest disclosure); source/basis=attributable-profit basis. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-04 `/screen` → `idea-generation`

```yaml
slot: SLOT-04
skill: idea-generation
route-prompt-cn: "在 A 股里筛一批低估值的中盘制造业标的，给出筛选口径和数据来源。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Screen A-share mid-cap industrials on a low-valuation basis, and state the screening criteria and data source. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=不适用（筛选口径定义）；来源/口径=低估值；筛选域 westock-tool → tdx-connector / wind-finance，等价口径未核实则停"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-04-cn.json::d4b95a05c51528067813b7ee61013f3567a3e9bba11d8639f62c0f28dd2b3f5b", "out/evidence/client-sessions/sessions/positive/slot-04-en.json::2adaea633e1b5c0c326b67c7f5940d1dc240c6ea6d854e76761746b967860e37"]
positive-result: "Route(唯一 skill: idea-generation)。守卫判定：证券/交易所=筛选类请求，不适用单一证券代码守卫；报告期=未指定（由筛选口径定义）；来源/口径=低估值；筛选域 westock-tool → tdx-connector / wind-finance，等价口径未核实则停。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: idea-generation). Guards: ticker/exchange=screening request; single-name guard not applicable; period=unspecified (defined by screen criteria); source/basis=low-valuation; screening domain westock-tool → tdx-connector / wind-finance, stop if equivalence unverified. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-05 `/catalysts` → `catalyst-calendar`

```yaml
slot: SLOT-05
skill: catalyst-calendar
route-prompt-cn: "看一下我自选池未来两周的催化剂日历，包括定期报告披露和限售解禁。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Show the catalyst calendar for my watchlist over the next two weeks, including scheduled disclosures and lock-up expiries. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=未来两周；来源/口径=定期报告披露、限售解禁；域 westock-data → neodata"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-05-cn.json::013d73977aec9299b9d926a2de3229b39bb6cb97bbe1abae5b7a2a1db21c0b0f", "out/evidence/client-sessions/sessions/positive/slot-05-en.json::0b7c43836a8ced6e18071eea7aac51496d6f365f3e376d8002994df6ad31b5c8"]
positive-result: "Route(唯一 skill: catalyst-calendar)。守卫判定：证券/交易所=自选池（以会话自选池清单为准）；报告期=未来两周；来源/口径=定期报告披露 + 限售解禁；数据域 westock-data → neodata。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: catalyst-calendar). Guards: ticker/exchange=user watchlist (per session watchlist); period=next two weeks; source/basis=scheduled disclosures + lock-up expiries; domain westock-data → neodata. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-06 `/morning-note` → `morning-note`

```yaml
slot: SLOT-06
skill: morning-note
route-prompt-cn: "写一份今天的 A 股晨会纪要，覆盖隔夜外盘和昨天盘后的披露。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Draft today's A-share morning note covering the overnight offshore session and yesterday's after-close disclosures. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=今日；来源/口径=隔夜外盘、昨日盘后披露"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-06-cn.json::dad69db9fd58313c72c9dc19bebb8a0e9cd3a14c68bd38de83659ed23e49990d", "out/evidence/client-sessions/sessions/positive/slot-06-en.json::bd4fccbc56d07ae7087357e10255a32c7a99c7744a17a7111974566477f6d26f"]
positive-result: "Route(唯一 skill: morning-note)。守卫判定：证券/交易所=不适用（全市场晨报）；报告期=今日；来源/口径=隔夜外盘 + 昨日盘后披露。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: morning-note). Guards: ticker/exchange=n/a (market-wide note); period=today; source/basis=overnight offshore session + after-close disclosures. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-07 `/earnings-preview` → `earnings-preview`

```yaml
slot: SLOT-07
skill: earnings-preview
route-prompt-cn: "给比亚迪(002594.SZ)做一份 2026 年三季报的盘前预览，列出 bull/base/bear 情景。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Build a pre-earnings preview for BYD (002594.SZ) 2026 Q3 results with bull/base/bear scenarios. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=2026Q3 盘前（报告期未发布）；来源/口径=bull/base/bear 情景"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-07-cn.json::ba9c77082e70aaf129e2dd53960819ee81979c9118ab9597406a1aef9ff0a879", "out/evidence/client-sessions/sessions/positive/slot-07-en.json::07d02870df7a08fbbfae545a3bf81112ef081bd90652fd3efe6e83540a718002"]
positive-result: "Route(唯一 skill: earnings-preview)。守卫判定：证券/交易所=002594.SZ（深交所）；报告期=2025Q3 盘前；来源/口径=bull/base/bear 情景。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: earnings-preview). Guards: ticker/exchange=002594.SZ (SZSE); period=Q3 pre-earnings; source/basis=bull/base/bear scenarios. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-08 `/sector` → `sector-overview`

```yaml
slot: SLOT-08
skill: sector-overview
route-prompt-cn: "写一份 A 股光伏行业的概览报告，5-10 页的量级，标注统计口径来源。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Produce an A-share solar industry landscape overview at the 5-10 page level, citing the source of each statistic. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=当前行业周期；来源/口径=光伏；统计口径逐项标注来源"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-08-cn.json::8926c25858daa329a362e67d96561ba15020a04799597205877b45d41555805e", "out/evidence/client-sessions/sessions/positive/slot-08-en.json::096e3b38362eae579d6db3417fbd25d55888648112caee579a90a70d35f1b266"]
positive-result: "Route(唯一 skill: sector-overview)。守卫判定：证券/交易所=不适用（行业任务）；报告期=当前行业周期；来源/口径=光伏；5-10 页量级；统计口径逐项标注来源。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: sector-overview). Guards: ticker/exchange=n/a (sector task); period=current cycle; source/basis=solar; 5-10 pages; per-statistic source citation. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

### SLOT-09 `/thesis` → `thesis-tracker`

```yaml
slot: SLOT-09
skill: thesis-tracker
route-prompt-cn: "更新我对招商银行(600036.SH)的多头论点，新增一条 2026 年二季度的数据点。（模拟授权前提：本会话已获得该请求所需数据域的使用许可，仅用于本次验收模拟。）"
route-prompt-en: "Update my long thesis on China Merchants Bank (600036.SH) with one new 2026 Q2 data point. (Simulated authorization premise: this session already holds the license for the data domains this request needs; acceptance simulation only.)"
guard-premises: "授权=模拟已获许可（仅验收模拟）；时效=2026Q2 数据点；来源/口径=多头论点更新"
date: "2026-09-29"
source-version: "WorkBuddy 37.10.3-24 客户端会话（本机 version 文件）；skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd"
evidence-files: ["out/evidence/client-sessions/sessions/positive/slot-09-cn.json::1439f9b83f5ab2c6530bdddce3f585d4a9be2ead5659c9f6c8e17d7bc67df3dc", "out/evidence/client-sessions/sessions/positive/slot-09-en.json::a60f55f317960c8edcec5710113fe4073f3f5ddc99095ac133a5e194c49ad1b5"]
positive-result: "Route(唯一 skill: thesis-tracker)。守卫判定：证券/交易所=600036.SH（上交所）；报告期=上季度数据点；来源/口径=多头论点更新。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 ｜ Route(unique skill: thesis-tracker). Guards: ticker/exchange=600036.SH (SSE); period=last quarter data point; source/basis=long thesis update. Routing decision only — no claim of data authorization, not a research verdict.（完整逐字响应见 §4.1）"
negative-result: "无该槽位专属动态负例；跨槽位守卫/七域负例见 §4.2（7 例，含证据哈希）"
adjudicator: Ray
state: 待测
research-state: 待测
```

---

## 3. 包校验 / 本机安装 / 召唤记录（G4 已记录，裁决人 Ray）

| 项 | 期望记录 | 当前值 |
|---|---|---|
| 目标客户端名称与版本 | 版本号 + 来源 | **WorkBuddy 37.10.3-24**（`D:\Program Files (x86)\WorkBuddy\version`，2026-09-29 读取） |
| `expert-manager` 校验器版本与路径 | 版本 + 可执行位置 | **skill-expert-manager 5.5.6-wb.38337834.g5f969292.h7826dc9400fd**（user scope：`C:\Users\GOBAO\.workbuddy\plugins\cache\workbuddy-builtin\skill-expert-manager\5.5.6-…\scripts`） |
| init/validate/register 步骤与原始输出 | 实际命令 + 完整输出 | `out/evidence/host/index.json`（steps + 原始日志 sha256）：validate-installed exit 0（`Expert package is valid!`）、register exit 0（写入 `my-experts/.codebuddy-plugin/marketplace.json`）、package exit 0（24 files → `out/dist/equity-research.zip`）；导出暂存区预装校验 exit 1 为安装前置事实（校验器要求专家位于宿主专家目录下） |
| 本机安装与召唤观察 | 界面/CLI 实际观察 | 安装：包复制到 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research` 并在 `.codebuddy-plugin/marketplace.json` 注册可见（2026-09-29T00:29:24+08:00；见 `out/evidence/host/index.json`，sha256 `8dbfa6206d37ae1b9040efc9d2a49c3947316bcc17baa1b2ca7984cd11bcd1d2`）。召唤：**待实测**（B-05）——`out/evidence/host/index.json` 的 `summon.status=pending-interactive-client-session`；v2 会话记录不构成召唤的 UI 观察回执（专家中心 GUI 截图/宿主输出未取得）。取得人类 owner 的客户端召唤观察后回填本行与 host 回执；在此之前本行不得计为通过。 |
| author 邮箱、头像来源与授权 | 授权依据 + SHA-256 | author：OldBoy405 <403562935@qq.com>（Ray 2026-09-28 确认）；头像：Ray 本人自绘、可随包分发，PNG 500×610、307,262 字节、SHA-256 `616fd6bb…f3897`（完整值见 `out/evidence/host/index.json` `avatar-authorization`） |

manifest 已按目标校验器 5.5.6 实际 schema 校正：i18n 字段（displayName/profession/displayDescription/defaultInitPrompt/quickPrompts/tags）改 `{zh,en}` 对象、新增 `description` 字段、`categoryId` 取 `08-FinanceInvestment`（12 个合法枚举之一）；`defaultInitPrompt` 与第一条 quickPrompt 逐字相等（SDD §3.1「与第一条 quickPrompt 相同」语义在目标 schema 形态下保持）。校验遗留 1 条非阻断 warning：displayDescription.zh 100 字符（建议 40-50）。

---

## 4. 路由与安全负例记录（G4 已记录，裁决人 Ray）

| 项 | 期望记录 | 当前值 |
|---|---|---|
| 18 条 CN/EN 正例逐条输入/响应 | 客户端版本 + 输入 + 输出 + 证据文件/哈希 | v2 已记录 18 条（SLOT-01..SLOT-09 各 CN/EN 一条）：输入 = §2 槽位问法逐字，响应 = 该槽位唯一 `Route`（CN/EN）且声明不代表研究结论合格；问法与响应逐条见 §4.1。**按 §2 新问法（模拟授权前提 + 时效修正）待重采**：v2 问法无模拟授权前提、SLOT-01 报告期超时效窗口（B-04）；重采前本行与 §4.1 不得作为正例通过证据。 |
| 三条 quickPrompts（earnings/initiate/model-update） | 各自启动的路径 | qp-01/02/03 输入 = manifest `quickPrompts[0..2].zh` 逐字；实测响应均为 `Clarify(...)`（入口即确认缺失字段，不调用任何技能）；观察记录命中的技能路径与哈希见 §4.1。 |
| 歧义请求 | Clarify 追问字段 | `Clarify(["securities-code","exchange","period","source","basis"])`：五字段逐项追问，补齐前不选中任何技能。证据 `out/evidence/client-sessions/sessions/negative/neg-ambiguous-request.json::4d4f0709a913cdb72b1f43b8eaaaad7d70f7a7559f5baeddb5ee702506fcb057`；完整响应见 §4.2。 |
| 缺证券代码或交易所 | Clarify 追问字段 | `Clarify(["securities-code","exchange"])`：本次不调用任何技能。证据 `out/evidence/client-sessions/sessions/negative/neg-missing-security-code.json::e4381e9db0fe361d9fcb7d89b2fd29a82a8f1c85b4efd1399a330cc43a3755c1`；完整响应见 §4.2。 |
| 无授权 / 过期数据 | Stop 理由 | 无授权 → `Stop("no-authorization")`，不静默替换、不编造；过期（2024 年报超发布后三个月窗口）→ `Stop("data-stale")`。证据 `out/evidence/client-sessions/sessions/negative/neg-no-authorization.json::66e6836515ed6fc11050813dd9ba3f1aa2b6ad61eed9d5a0e003a09003b40707`、`out/evidence/client-sessions/sessions/negative/neg-stale-data.json::a00b37087e710b6d19a11c8c41ddc3fd9872f8f7abc921549a4fc60079fd22d0`；完整响应见 §4.2。 |
| `/initiate` Task 3 无 Task 2 模型 | Stop 理由 | `Stop("missing-prerequisite-model")`：缺 Task 2 金融模型不得自动连跑、不得现场补建。证据 `out/evidence/client-sessions/sessions/negative/neg-initiate-task3-without-model.json::f1bf30b03c7f67918eef05a44866dea018b9d5b6c52f1f5e713b610b768d3928`；完整响应见 §4.2。 |
| 无等价数据源 | 明确降级或停机 | `Stop("no-equivalent-source")`：研报域仅 neodata，缺席不静默替换为其他域数据。证据 `out/evidence/client-sessions/sessions/negative/neg-no-equivalent-source.json::bb8d34b34819d86aed6d80f250f9904284457ead64a7b8f378dfcaa3d1c5caa4`；完整响应见 §4.2。 |
| 美股个股 | 仅公开面声明 | `Stop(降级说明)`：仅公开面（IR 财报/公开披露整理），不伪装机构研究。证据 `out/evidence/client-sessions/sessions/negative/neg-us-listing-public-only.json::f06f241c1df8a993712b726a4820bb0ec7185fea1c722aedf3916e72abda3ebe`；完整响应见 §4.2。 |

静态规则核查（`cmd-06` 的一部分，可作为规则一致性证据但不作为动态负例通过依据）：

- 七域优先顺序见 `agents/equity-research.md` §数据域路由；顺序与 PRD FR-06 表逐字一致。
- 同一指标单源、跨源逐项标注日期/来源/口径；无授权、过期、无等价源时 `Stop`。美股个股仅公开面且声明无美系机构能力。
- 负例的**动态**证据必须来自实际客户端会话；只有静态规则文本时 `cmd-05`/`cmd-06` 必须失败。

---

### 4.1 正例与 quickPrompts 逐条索引（版本化入口；原件在忽略区）

客户端与口径：WorkBuddy **37.10.3-24**（来源 D:\Program Files (x86)\WorkBuddy\version (client本体, read 2026-09-29); note: 5.5.6 in the first issue was the skill-expert-manager version, misrecorded as the client version）。下表每行「实测响应」为客户端会话
原始响应文字，`sha256` 与忽略区证据文件字节一致（索引 `out/evidence/client-sessions/index.json` 生成于 2026-09-29T10:15:12+08:00；
原件不版本化，仅索引版本化）。

| 用例 | 槽位/入口 | 原始输入（逐字） | 实测响应（逐字） | 证据文件（相对 CR 根） | sha256 |
| --- | --- | --- | --- | --- | --- |
| slot-01-cn | SLOT-01 / zh-CN | 帮我做贵州茅台(600519.SH) 2025 年三季报的业绩点评，用扣非口径，数据来自定期报告和交易所披露。 | Route(唯一 skill: earnings-analysis)。守卫判定：证券/交易所=600519.SH（上交所）；报告期=2025Q3；来源/口径=扣非口径；定期报告与交易所披露。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-01-cn.json | d8b4ae78fbaac2a3ed5696589ea7609538a240cbe196e3ac1966a75af8a2e932 |
| slot-01-en | SLOT-01 / en-US | Write a post-earnings update for Kweichow Moutai (600519.SH), 2025 Q3 results, use the recurring-profit basis and exchange disclosure sources. | Route(unique skill: earnings-analysis). Guards: ticker/exchange=600519.SH (SSE); period=2025 Q3; source/basis=recurring-profit basis; periodic reports & exchange disclosures. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-01-en.json | ce6b322e2beac2100e62ff4dde3b7701b86e835b80b6b0085aba247207734f62 |
| slot-02-cn | SLOT-02 / zh-CN | 为宁德时代(300750.SZ)做首次覆盖，只执行 Task 1 公司研究，不要连跑后面的 Task。 | Route(唯一 skill: initiating-coverage)。守卫判定：证券/交易所=300750.SZ（深交所）；报告期=Task 1（首次覆盖阶段）；来源/口径=公司研究；Task 1～5 每次只发起一个，不自动连跑。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-02-cn.json | e114828d95a3eaf6b735de7e76b9b581f0c7a38aabfc2a7a5da7083925501a10 |
| slot-02-en | SLOT-02 / en-US | Start an initiation on CATL (300750.SZ) — run Task 1 company research only, do not chain the remaining tasks. | Route(unique skill: initiating-coverage). Guards: ticker/exchange=300750.SZ (SZSE); period=Task 1; source/basis=company research only; one Task at a time, no auto-chaining. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-02-en.json | 4cc9eb341abd85bc9af19dd2b1f77ee02ffb46edfd81592d1d592291a5d0ed0c |
| slot-03-cn | SLOT-03 / zh-CN | 用刚出的业绩快报更新中国平安(601318.SH)的盈利模型，口径保持归母。 | Route(唯一 skill: model-update)。守卫判定：证券/交易所=601318.SH（上交所）；报告期=业绩快报（最新披露期）；来源/口径=归母口径。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-03-cn.json | 2b5c943540139e80746eb173c27e4f7bc5e9023a591d4085b2625714023ff5a3 |
| slot-03-en | SLOT-03 / en-US | Update the Ping An Insurance (601318.SH) earnings model with the just-released preliminary results, keep the attributable-profit basis. | Route(unique skill: model-update). Guards: ticker/exchange=601318.SH (SSE); period=preliminary results (latest disclosure); source/basis=attributable-profit basis. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-03-en.json | bd8ec116c0703cb6a615e2101e4a2b88f6cb16ea72cebd6fc021e66421d0d02b |
| slot-04-cn | SLOT-04 / zh-CN | 在 A 股里筛一批低估值的中盘制造业标的，给出筛选口径和数据来源。 | Route(唯一 skill: idea-generation)。守卫判定：证券/交易所=筛选类请求，不适用单一证券代码守卫；报告期=未指定（由筛选口径定义）；来源/口径=低估值；筛选域 westock-tool → tdx-connector / wind-finance，等价口径未核实则停。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-04-cn.json | d4b95a05c51528067813b7ee61013f3567a3e9bba11d8639f62c0f28dd2b3f5b |
| slot-04-en | SLOT-04 / en-US | Screen A-share mid-cap industrials on a low-valuation basis, and state the screening criteria and data source. | Route(unique skill: idea-generation). Guards: ticker/exchange=screening request; single-name guard not applicable; period=unspecified (defined by screen criteria); source/basis=low-valuation; screening domain westock-tool → tdx-connector / wind-finance, stop if equivalence unverified. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-04-en.json | 2adaea633e1b5c0c326b67c7f5940d1dc240c6ea6d854e76761746b967860e37 |
| slot-05-cn | SLOT-05 / zh-CN | 看一下我自选池未来两周的催化剂日历，包括定期报告披露和限售解禁。 | Route(唯一 skill: catalyst-calendar)。守卫判定：证券/交易所=自选池（以会话自选池清单为准）；报告期=未来两周；来源/口径=定期报告披露 + 限售解禁；数据域 westock-data → neodata。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-05-cn.json | 013d73977aec9299b9d926a2de3229b39bb6cb97bbe1abae5b7a2a1db21c0b0f |
| slot-05-en | SLOT-05 / en-US | Show the catalyst calendar for my watchlist over the next two weeks, including scheduled disclosures and lock-up expiries. | Route(unique skill: catalyst-calendar). Guards: ticker/exchange=user watchlist (per session watchlist); period=next two weeks; source/basis=scheduled disclosures + lock-up expiries; domain westock-data → neodata. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-05-en.json | 0b7c43836a8ced6e18071eea7aac51496d6f365f3e376d8002994df6ad31b5c8 |
| slot-06-cn | SLOT-06 / zh-CN | 写一份今天的 A 股晨会纪要，覆盖隔夜外盘和昨天盘后的披露。 | Route(唯一 skill: morning-note)。守卫判定：证券/交易所=不适用（全市场晨报）；报告期=今日；来源/口径=隔夜外盘 + 昨日盘后披露。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-06-cn.json | dad69db9fd58313c72c9dc19bebb8a0e9cd3a14c68bd38de83659ed23e49990d |
| slot-06-en | SLOT-06 / en-US | Draft today's A-share morning note covering the overnight offshore session and yesterday's after-close disclosures. | Route(unique skill: morning-note). Guards: ticker/exchange=n/a (market-wide note); period=today; source/basis=overnight offshore session + after-close disclosures. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-06-en.json | bd4fccbc56d07ae7087357e10255a32c7a99c7744a17a7111974566477f6d26f |
| slot-07-cn | SLOT-07 / zh-CN | 给比亚迪(002594.SZ)做一份三季报的盘前预览，列出 bull/base/bear 情景。 | Route(唯一 skill: earnings-preview)。守卫判定：证券/交易所=002594.SZ（深交所）；报告期=2025Q3 盘前；来源/口径=bull/base/bear 情景。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-07-cn.json | ba9c77082e70aaf129e2dd53960819ee81979c9118ab9597406a1aef9ff0a879 |
| slot-07-en | SLOT-07 / en-US | Build a pre-earnings preview for BYD (002594.SZ) Q3 results with bull/base/bear scenarios. | Route(unique skill: earnings-preview). Guards: ticker/exchange=002594.SZ (SZSE); period=Q3 pre-earnings; source/basis=bull/base/bear scenarios. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-07-en.json | 07d02870df7a08fbbfae545a3bf81112ef081bd90652fd3efe6e83540a718002 |
| slot-08-cn | SLOT-08 / zh-CN | 写一份 A 股光伏行业的概览报告，5-10 页的量级，标注统计口径来源。 | Route(唯一 skill: sector-overview)。守卫判定：证券/交易所=不适用（行业任务）；报告期=当前行业周期；来源/口径=光伏；5-10 页量级；统计口径逐项标注来源。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-08-cn.json | 8926c25858daa329a362e67d96561ba15020a04799597205877b45d41555805e |
| slot-08-en | SLOT-08 / en-US | Produce an A-share solar industry landscape overview at the 5-10 page level, citing the source of each statistic. | Route(unique skill: sector-overview). Guards: ticker/exchange=n/a (sector task); period=current cycle; source/basis=solar; 5-10 pages; per-statistic source citation. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-08-en.json | 096e3b38362eae579d6db3417fbd25d55888648112caee579a90a70d35f1b266 |
| slot-09-cn | SLOT-09 / zh-CN | 更新我对招商银行(600036.SH)的多头论点，新增一条上季度的数据点。 | Route(唯一 skill: thesis-tracker)。守卫判定：证券/交易所=600036.SH（上交所）；报告期=上季度数据点；来源/口径=多头论点更新。本响应仅记录技能路由决策，不代表数据已授权，也不代表研究结论合格。 | out/evidence/client-sessions/sessions/positive/slot-09-cn.json | 1439f9b83f5ab2c6530bdddce3f585d4a9be2ead5659c9f6c8e17d7bc67df3dc |
| slot-09-en | SLOT-09 / en-US | Update my long thesis on China Merchants Bank (600036.SH) with one new data point from last quarter. | Route(unique skill: thesis-tracker). Guards: ticker/exchange=600036.SH (SSE); period=last quarter data point; source/basis=long thesis update. Routing decision only — no claim of data authorization, not a research verdict. | out/evidence/client-sessions/sessions/positive/slot-09-en.json | a60f55f317960c8edcec5710113fe4073f3f5ddc99095ac133a5e194c49ad1b5 |
| qp-01 | quickPrompts[0] (earnings-analysis) | 帮我做一份 A 股业绩点评：先确认证券代码与交易所、报告期和数据来源。 | Clarify(["securities-code","exchange","period","source","basis"])。请确认：1) 证券代码与交易所（.SH/.SZ/.BJ/.HK 或中文交易所名）；2) 报告期（如 2025Q3）；3) 数据来源与口径（扣非/归母、合并/母公司）。确认后路由至唯一技能 earnings-analysis。本次不调用任何技能。 | out/evidence/client-sessions/sessions/quickprompts/qp-01.json | 5bccb9e7c13e7f2f952b42c1da40f7df08c7c64018a3e5b1ae873fda9c8e4382 |
| qp-02 | quickPrompts[1] (initiating-coverage) | 为一家 A 股公司开始首次覆盖，只执行 Task 1 公司研究，不要连跑后面的 Task。 | Clarify(["securities-code","exchange"])。已收到约束：仅执行 Task 1 公司研究，不自动连跑后续 Task（Task 1～5 每次只发起一个）。请提供标的证券代码与交易所后发起。本次不调用任何技能。 | out/evidence/client-sessions/sessions/quickprompts/qp-02.json | f3d0b461e4c4085c6ec4fada8b8c1921d4b1bf04c3300d17a2d4f239d27b65ae |
| qp-03 | quickPrompts[2] (model-update) | 用新披露的数据更新这家公司的盈利模型，口径保持不变。 | Clarify(["securities-code","exchange","period","data-source"])。『这家公司』与『新披露的数据』不可判定：请提供证券代码与交易所、报告期、新数据的来源与披露日期；口径沿用原模型设定。确认后路由至唯一技能 model-update。本次不调用任何技能。 | out/evidence/client-sessions/sessions/quickprompts/qp-03.json | 37536b0882793c7b4dd7cc5db84f17747cbfceba8c06ebdc5deeef93302acaff |

### 4.2 安全负例逐条索引（版本化入口；原件在忽略区）

| 用例 | 客户端 | 原始输入（逐字） | 实测响应（逐字） | 证据文件（相对 CR 根） | sha256 |
| --- | --- | --- | --- | --- | --- |
| no-authorization | 37.10.3-24 | 用 wind-finance 拉贵州茅台(600519.SH) 2025Q3 机构财务明细做业绩点评。 | Stop("no-authorization")。当前会话未获 wind-finance 数据域授权，机构财务域的机构级明细不可读取。按守卫规则：无授权即停机，不静默替换数据源、不编造数据。请先在客户端说明/完成该数据域的授权；如改用已授权的公开面来源，属明确降级，须逐项标注来源、日期与口径。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-no-authorization.json | 66e6836515ed6fc11050813dd9ba3f1aa2b6ad61eed9d5a0e003a09003b40707 |
| stale-data | 37.10.3-24 | 帮我点评比亚迪(002594.SZ) 2024 年年报业绩（发布距今已超过一年）。 | Stop("data-stale")。业绩点评时效窗口为报告发布后三个月，2024 年年报已超窗口。不使用过期数据出点评、不静默替换为其他期数据。可选：a) 改用最新一期定期报告重新发起；b) 明确接受过期口径后按历史分析处理，数据一律标注 [STALE]。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-stale-data.json | a00b37087e710b6d19a11c8c41ddc3fd9872f8f7abc921549a4fc60079fd22d0 |
| us-listing-public-only | 37.10.3-24 | 给英伟达(NVDA.US)做机构级深度研究：要一致预期、机构目标价和卖方评级分布。 | Stop(降级说明)。美股个股只能走公开面：本 Agent 不具备美系机构数据能力（一致预期、机构目标价、评级分布属机构域），不伪装机构研究。可提供的公开面替代：公司 IR 公开财报与指引、公开新闻与公开披露的整理与框架分析，逐项标注来源与日期。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-us-listing-public-only.json | f06f241c1df8a993712b726a4820bb0ec7185fea1c722aedf3916e72abda3ebe |
| no-equivalent-source | 37.10.3-24 | 拉招商银行(600036.SH)最新的券商研报评级和目标价；neodata 缺席的话你自己找别的源补上。 | Stop("no-equivalent-source")。研报评级/目标价/全文域的声明来源为仅 neodata，缺席即无默认等价备选；按守卫规则不得静默替换为其他域数据、不编造。如需继续：先确认 neodata 授权与覆盖，或明确降级为『公开面评级新闻整理』（逐项标注来源/日期/口径，且不等价于研报域）。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-no-equivalent-source.json | bb8d34b34819d86aed6d80f250f9904284457ead64a7b8f378dfcaa3d1c5caa4 |
| ambiguous-request | 37.10.3-24 | 帮我点评一下这家公司最新业绩，口径你看着办。 | Clarify(["securities-code","exchange","period","source","basis"])。以下字段不可判定，请补充：1) securities-code：『这家公司』指哪只标的；2) exchange：.SH/.SZ/.BJ/.HK 或中文交易所名；3) period：『最新业绩』指哪个报告期；4) source：数据来源授权说明；5) basis：合并/母公司、扣非/归母口径。补齐前不选中任何技能、不编造数据。 | out/evidence/client-sessions/sessions/negative/neg-ambiguous-request.json | 4d4f0709a913cdb72b1f43b8eaaaad7d70f7a7559f5baeddb5ee702506fcb057 |
| missing-security-code | 37.10.3-24 | 帮我做 2025Q3 的业绩点评。 | Clarify(["securities-code","exchange"])。缺少证券代码与交易所（.SH/.SZ/.BJ/.HK 或中文交易所名），无法判定标的。补充后路由至唯一技能（业绩点评 → earnings-analysis）。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-missing-security-code.json | e4381e9db0fe361d9fcb7d89b2fd29a82a8f1c85b4efd1399a330cc43a3755c1 |
| initiate-task3-without-model | 37.10.3-24 | 继续宁德时代(300750.SZ)的首次覆盖，直接做 Task 3 估值，模型文件没有就现场建一个。 | Stop("missing-prerequisite-model")。/initiate 的 Task 2→3 为前置链：缺 Task 2 金融模型时请求 Task 3 估值必须停机，不得自动连跑、不得默认现场补建。请先交付/确认 Task 2 金融模型（三表联动 + 盈利预测），再发起 Task 3。本次不调用任何技能。 | out/evidence/client-sessions/sessions/negative/neg-initiate-task3-without-model.json | f1bf30b03c7f67918eef05a44866dea018b9d5b6c52f1f5e713b610b768d3928 |

上述七例为 AC-06 的验收负例；首轮采集的七条合规观察（域外闲聊/技术任务、违规荐股、内幕信息、实时行情、
全仓指令、市场操纵）保留在忽略区 `sessions/negative/neg-01..07.json`，经 `retired-compliance-negatives`
标注为**非** AC-06 验收用例，不参与判定。

---

## 5. 研究质量（本 CR 始终待测）

九项研究内容与 DOCX/XLSX 的端到端合格判定不在本 CR 范围（`sdd.md` §8 `scope_out`）。即使 `earnings` 作为产物试点，也只验包与路由，**不**签研究产物质量。本 CR 交付时"研究质量=通过"的项数必须为 **0**。
