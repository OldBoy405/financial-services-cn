---
name: idea-generation
description: Systematic stock screening and investment idea sourcing. Combines quantitative screens, thematic research, and pattern recognition to surface new long and short ideas. Use when looking for new ideas, running screens, or conducting thematic sweeps. Triggers on "idea generation", "stock screen", "find ideas", "what looks interesting", "screen for", "new ideas", or "pitch me something".
---

# Idea Generation

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-04`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [5 筛选, 4]
- **保留的旧约束（不静默删除）**：输出候选清单与理由、标注数据来源、不把筛选结果当研究结论；筛选条件（方向/行业/风格/市值）追问保留。
- **中文等价口径**：美系 screener 字段改为 A/H 可得字段（市值、行业分类、涨跌幅、估值分位、两融/资金指标仅在授权域可用）；筛选工具分层声明为 `westock-tool` → `tdx-connector` / `wind-finance`。
- **明确缺口**：筛选等价口径未核实即停机，不偷偷替换工具；无授权域不返回数据；非上市主体不可筛选。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

## Workflow

### Step 1: Define Search Criteria

Ask the user for parameters:
- **Direction**: Long ideas, short ideas, or both
- **Market cap**: Large, mid, small, micro
- **Sector**: Specific sector or cross-sector
- **Style**: Value, growth, quality, special situation, event-driven
- **Geography**: US, international, global
- **Theme**: Any specific thematic angle (AI, reshoring, aging demographics, etc.)

### Step 2: Quantitative Screens

Run screens based on the style:

**Value Screen**
- P/E below sector median
- EV/EBITDA below historical average
- Free cash flow yield >5%
- Price/book below 1.5x
- Insider buying in last 90 days
- Dividend yield above market average

**Growth Screen**
- Revenue growth >15% YoY
- Earnings growth >20% YoY
- Revenue acceleration (growth rate increasing)
- Expanding margins
- High return on invested capital (>15%)
- Strong net retention (>110% for SaaS)

**Quality Screen**
- Consistent revenue growth (5+ years)
- Stable or expanding margins
- ROE >15%
- Low debt/equity
- High free cash flow conversion
- Insider ownership >5%

**Short Screen**
- Declining revenue or decelerating growth
- Margin compression
- Rising receivables / inventory vs. sales
- Insider selling
- Valuation premium to peers without justification
- High short interest with deteriorating fundamentals
- Accounting red flags (auditor changes, restatements)

**Special Situation Screen**
- Recent IPOs / SPACs with lockup expirations
- Spin-offs in last 12 months
- Companies emerging from restructuring
- Activist involvement
- Management changes at underperforming companies

### Step 3: Thematic Sweep

For thematic ideas, research the theme and identify beneficiaries:

1. Define the thesis (e.g., "AI infrastructure spending accelerates through 2026")
2. Map the value chain — who benefits directly vs. indirectly?
3. Identify pure-play vs. diversified exposure
4. Assess which names are already "priced in" vs. under-appreciated
5. Look for second-order beneficiaries that the market hasn't connected to the theme

### Step 4: Idea Presentation

For each idea that passes the screen, present:

**[Company Name] — [Long/Short] — [One-Line Thesis]**

| Metric | Value | vs. Peers |
|--------|-------|-----------|
| Market cap | | |
| EV/EBITDA (NTM) | | |
| P/E (NTM) | | |
| Revenue growth | | |
| EBITDA margin | | |
| FCF yield | | |

**Thesis (3-5 bullets):**
- Why this is mispriced
- What the market is missing
- Catalyst to realize value

**Key Risks:**
- What would make this wrong

**Suggested Next Steps:**
- Build full model? Deep-dive diligence? Expert call?

### Step 5: Output

- Shortlist of 5-10 ideas with one-page summaries
- Screening criteria and methodology documented
- Comparison table across all ideas
- Prioritized list: which ideas to research first

## Important Notes

- Screens surface candidates, not conclusions — every screen output needs fundamental work
- The best ideas often come from intersections (e.g., quality company at value price due to temporary headwind)
- Avoid crowded trades — check ownership data, short interest, and how many analysts cover the name
- Contrarian ideas need a catalyst — being early without a catalyst is the same as being wrong
- Track idea hit rates over time — which screens and approaches produce the best ideas?
- Short ideas need higher conviction — timing is harder and risk is asymmetric
