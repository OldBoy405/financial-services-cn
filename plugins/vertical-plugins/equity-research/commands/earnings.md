---
description: Analyze quarterly earnings and create an earnings update report
argument-hint: "[company name or ticker] [quarter, e.g. Q3 2024]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-10`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1 机构财务/公告/事件, 2 券商一致预期, 4 公开行情/K线/公告/日历]
- **保留的旧约束（不静默删除）**：8-12 页、8-12 张图、1-3 张摘要表、beat/miss 量化到具体数值、发布后 24-48 小时时效、发布后三个月时效规则、transcript/纪要日期与发布日期的对应核对、引用与 Sources 清单（每个图表标注文档与日期）、DOCX 报告交付、八项交付前质检（见 `commands/earnings.md` Quality Checklist）
- **中文等价口径**：定期报告（交易所披露页/巨潮资讯/港交所披露易）替代 10-Q + EDGAR 链接；一致预期改用境内可得来源并标注生成日期与口径；金额改为 CNY（A 股）/HKD（H 股）；篇幅锚改为「8-12 页 / 3,000-5,000 中文汉字（含图表标签与中文文件名）」；评级改为 A 股五档口径；英文篇幅限制不删除，改为中文等价验收口径。
- **明确缺口**：`options-implied move` 无 A/H 等价项；盘前/盘后价格序列在 A/H 主要交易所无等价序列；A 股电话会 transcript 多不公开，改用业绩说明会/互动平台问答并标注替代性质。三项均标缺口，不造数。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

# Earnings Analysis Command

Create a professional equity research earnings update report analyzing quarterly results.

## Workflow

### Step 1: Gather Information

Parse the input for:
- 公司名称或证券代码 + 交易所（A 股 `.SH`/`.SZ`/`.BJ`，H 股 `.HK`）
- 报告期（如 2025Q3、2025H1、2024 年报；A 股中报/季报与年报口径不同时须说明）

If not provided, ask:
- "What company's earnings would you like to analyze?"
- "Which quarter? (e.g., Q3 2024)"

### Step 2: Verify Timeliness

**CRITICAL**: Before proceeding, verify you have the latest data:
1. Search for "[Company] latest earnings results [current year]"
2. Verify the earnings release is within the last 3 months
3. Confirm transcript date matches release date（A 股电话会 transcript 多不公开：改用业绩说明会/互动平台问答并标注替代性质）
4. 确认计价货币与口径（A 股 CNY、H 股 HKD；扣非/归母并列记录）

If data is stale, inform the user and search for the latest.

### Step 3: Load Earnings Analysis Skill

Use `skill: "earnings-analysis"` to create the report:

1. **Data Collection** (search for latest):
   - Earnings release (press release)
   - 定期报告（交易所披露页：上交所/深交所/北交所；H 股为港交所披露易）+ 业绩预告/快报
   - Earnings call transcript（A 股以业绩说明会/互动平台问答替代并标注）
   - Investor presentation/supplemental materials（投资者关系公告与业绩演示材料）
   - 一致预期（境内可得来源，标注生成日期与口径）

2. **Beat/Miss Analysis**:
   - 营业收入 vs 一致预期：超/低于预期 CNY X 亿元或 X%
   - 每股收益 vs 一致预期：超/低于预期 CNY X 元或 X%
   - Key segment performance vs expectations
   - Explain WHY results differed

3. **Key Metrics Analysis**:
   - Revenue breakdown by segment/geography
   - Margin trends (gross, operating, net)
   - Guidance: raised/maintained/lowered
   - Updated forward estimates

4. **Generate Charts** (8-12):
   - Quarterly revenue progression
   - Quarterly EPS progression
   - Margin trends
   - Revenue by segment
   - Beat/miss summary
   - Estimate revisions
   - Valuation charts

5. **Create Report** (8-12 pages):
   - Page 1: Summary with rating and price target
   - Pages 2-3: Detailed results analysis
   - Pages 4-5: Key metrics & guidance
   - Pages 6-7: Updated investment thesis
   - Pages 8-10: Valuation & estimates
   - Sources section with clickable hyperlinks

### Step 4: Deliver Output

Provide:
1. **DOCX report** - 8-12 page earnings update（中文交付；文件名与图表标签用中文）
2. **Summary** highlighting:
   - Beat/miss on key metrics
   - Guidance changes
   - Thesis impact (positive/negative/neutral)

## Report Structure Reference

```
PAGE 1: EARNINGS SUMMARY
┌─────────────────────────────────────────────────────────────────┐
│ [Company] Q3 2024 Earnings Update                               │
│ 评级：买入（A 股五档）| 目标价：CNY XXX（原 CNY XXX）          │
├─────────────────────────────────────────────────────────────────┤
│ KEY TAKEAWAYS                                                   │
│ • Revenue beat by X% on strong [segment] performance            │
│ • EPS beat by $X.XX driven by margin expansion                  │
│ • FY guidance raised to $X.XX-$X.XX (from $X.XX-$X.XX)         │
│ • Thesis intact; maintain BUY rating                            │
├─────────────────────────────────────────────────────────────────┤
│ RESULTS SNAPSHOT                                                │
│ ┌─────────────┬──────────┬──────────┬──────────┐               │
│ │ Metric      │ Actual   │ Consensus│ Beat/Miss│               │
│ │ 营业收入    │ CNY X.X 亿 │ CNY X.X 亿 │ +X.X%    │               │
│ │ 每股收益    │ CNY X.XX  │ CNY X.XX  │ +CNY X.X │               │
│ │ Gross Margin│ XX.X%    │ XX.X%    │ +XXbps   │               │
│ └─────────────┴──────────┴──────────┴──────────┘               │
└─────────────────────────────────────────────────────────────────┘

PAGES 2-3: DETAILED RESULTS
- Segment-by-segment analysis
- Geographic breakdown
- Key drivers of beat/miss

PAGES 4-5: METRICS & GUIDANCE
- Margin analysis
- Full-year guidance comparison
- Updated quarterly estimates

PAGES 6-7: THESIS UPDATE
- What's changed
- Risks and catalysts
- Investment recommendation

PAGES 8-10: VALUATION
- Updated DCF/comps if material
- Price target justification
- Scenario analysis

SOURCES SECTION (with clickable hyperlinks):
- Earnings Release: [hyperlink]
- 定期报告：交易所披露页链接（A 股：上交所/深交所/北交所；H 股：港交所披露易）
- 电话会/业绩说明会记录：[hyperlink，标注替代性质]
- 一致预期：[境内来源] as of [date]（标注口径）
```

## Quality Checklist

Before delivery:
- [ ] Earnings data is from latest quarter (not stale)
- [ ] Beat/miss quantified with specific numbers
- [ ] All charts embedded (8-12 total)
- [ ] Sources section with clickable hyperlinks
- [ ] Every figure/table has source citation
- [ ] Guidance changes clearly documented
- [ ] Rating and price target stated upfront
- [ ] 8-12 页、3,000-5,000 中文汉字（中文等价口径；含图表标签与中文文件名）
