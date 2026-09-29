---
name: earnings-preview
description: Build pre-earnings analysis with estimate models, scenario frameworks, and key metrics to watch. Use before a company reports quarterly earnings to prepare positioning notes, set up bull/bear scenarios, and identify what will move the stock. Triggers on "earnings preview", "what to watch for [company] earnings", "pre-earnings", "earnings setup", or "preview Q[X] for [company]".
---

# Earnings Preview

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-07`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1, 2]
- **保留的旧约束（不静默删除）**：bull/base/bear 三情景；关键指标观察清单；不包含已发布结果的结论（预览与点评不混用）；缺标的时追问。
- **中文等价口径**：美元预期改为 CNY/HKD；美系一致预期来源改为境内可得来源并标注口径与日期；预约披露日/业绩预告/快报作为驱动事件显式对照。
- **明确缺口**：预告/快报覆盖不全时以定期报告为准并标注；无等价数据源时停机。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

## Workflow

### Step 1: Gather Context

- Identify the company and reporting quarter
- Pull consensus estimates via web search (revenue, EPS, key segment metrics)
- Find the earnings date and time (pre-market vs. after-hours)
- Review the company's prior quarter earnings call for any guidance or commentary

### Step 2: Key Metrics Framework

Build a "what to watch" framework specific to the company:

**Financial Metrics:**
- Revenue vs. consensus (total and by segment)
- EPS vs. consensus
- Margins (gross, operating, net) — expanding or contracting?
- Free cash flow
- Forward guidance vs. consensus

**Operational Metrics** (sector-specific):
- Tech/SaaS: ARR, net retention, RPO, customer count
- Retail: Same-store sales, traffic, basket size
- Industrials: Backlog, book-to-bill, price vs. volume
- Financials: NIM, credit quality, loan growth, fee income
- Healthcare: Scripts, patient volumes, pipeline updates

### Step 3: Scenario Analysis

Build 3 scenarios with stock price implications:

| Scenario | Revenue | EPS | Key Driver | Stock Reaction |
|----------|---------|-----|------------|----------------|
| Bull | | | | |
| Base | | | | |
| Bear | | | | |

For each scenario:
- What would need to happen operationally
- What management commentary would signal this
- Historical context — how has the stock moved on similar prints?

### Step 4: Catalyst Checklist

Identify the 3-5 things that will determine the stock's reaction:

1. [Metric] vs. [consensus/whisper number] — why it matters
2. [Guidance item] — what the buy-side expects to hear
3. [Narrative shift] — any strategic changes, M&A, restructuring

### Step 5: Output

One-page earnings preview with:
- Company, quarter, earnings date
- Consensus estimates table
- Key metrics to watch (ranked by importance)
- Bull/base/bear scenario table
- Catalyst checklist
- Trading setup: recent stock performance, implied move from options

## Important Notes

- Consensus estimates change — always note the source and date of estimates
- "Whisper numbers" from buy-side surveys are often more relevant than published consensus
- Historical earnings reactions help calibrate expectations (search for "[company] earnings reaction history")
- Options-implied move tells you what the market expects — compare to your scenarios
