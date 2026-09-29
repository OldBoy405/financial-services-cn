---
name: earnings-analysis
description: Create professional equity research earnings update reports (8-12 pages, 3,000-5,000 words) analyzing quarterly results for companies already under coverage. Fast-turnaround format focusing on beat/miss analysis, key metrics, updated estimates, and revised thesis. Includes 1-3 summary tables and 8-12 charts. Use when user requests "earnings update", "quarterly update", "earnings analysis", "Q1/Q2/Q3/Q4 results", or post-earnings report.
---

# Equity Research Earnings Update

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-01`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1 机构财务/公告/事件, 2 券商一致预期, 4 公开行情/K线/公告/日历]
- **保留的旧约束（不静默删除）**：8-12 页、8-12 张图、1-3 张摘要表、beat/miss 量化到具体数值、发布后 24-48 小时时效、发布后三个月时效规则、transcript/纪要日期与发布日期的对应核对、引用与 Sources 清单（每个图表标注文档与日期）、DOCX 报告交付、八项交付前质检（见 `commands/earnings.md` Quality Checklist）
- **中文等价口径**：定期报告（交易所披露页/巨潮资讯/港交所披露易）替代 10-Q + EDGAR 链接；一致预期改用境内可得来源并标注生成日期与口径；金额改为 CNY（A 股）/HKD（H 股）；篇幅锚改为「8-12 页 / 3,000-5,000 中文汉字（含图表标签与中文文件名）」；评级改为 A 股五档口径；英文篇幅限制不删除，改为中文等价验收口径。
- **明确缺口**：`options-implied move` 无 A/H 等价项；盘前/盘后价格序列在 A/H 主要交易所无等价序列；A 股电话会 transcript 多不公开，改用业绩说明会/互动平台问答并标注替代性质。三项均标缺口，不造数。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Create professional **EARNINGS UPDATE REPORTS** analyzing quarterly results for companies already under coverage, following institutional standards (JPMorgan, Goldman Sachs, Morgan Stanley format).

**Key Characteristics:**
- **Length**: 8-12 pages
- **Word Count**: 3,000-5,000 words
- **Tables**: 1-3 summary tables (NOT comprehensive)
- **Figures**: 8-12 charts
- **Turnaround**: 1-2 days (within 24-48 hours of earnings)
- **Audience**: Clients already familiar with the company
- **Focus**: What's NEW - beat/miss, updated estimates, thesis impact
- **字体**：中文交付用宋体/黑体（Times New Roman 仅用于拉丁文与数字）

## When to Use

Use when the user requests:
- "Create an earnings update for [Company] Q3 2024"
- "Analyze [Company]'s quarterly results"
- "Post-earnings report for [Company]"
- "Q1/Q2/Q3/Q4 update for [Company]"

**Do NOT use if:**
- User requests "initiation report" → Use different skill
- User requests "flash note" or "quick take" → Different format
- Company is not already covered → Need initiation first

## Critical Requirements

### 1. Speed & Timeliness
- Publish within 24-48 hours of earnings release
- Focus on NEW information only
- Don't rehash company background extensively

### 2. Beat/Miss Analysis
- Lead with whether company beat or missed estimates
- Quantify variances (e.g., "Revenue beat by $120M or 3%")
- Explain WHY results differed from expectations

### 3. Summary Format
- Keep tables to 1-3 (summary only, not comprehensive)
- No full P&L/Cash Flow/Balance Sheet (just key metrics)
- Assume reader has seen initiation report

### 4. Citations & Source Attribution ⭐⭐⭐ MANDATORY

**CRITICAL**: Properly cite all data with SPECIFIC sources and CLICKABLE HYPERLINKS.

**Include specific citations WITH CLICKABLE LINKS in every figure and table:**

```
Source: 2025Q3 定期报告（交易所披露页，披露日 2025-10-28）；公司业绩快报
        [Hyperlink "定期报告" to: 交易所披露页/巨潮资讯/港交所披露易链接]
```

**HOW HYPERLINKS SHOULD APPEAR IN WORD:**
- Document names appear as blue, underlined clickable links
- Reader can Ctrl+Click to open source directly
- Not plain text URLs - formatted hyperlinks with display text

**REQUIRED SOURCES LIST:**

Cite in every earnings update:
- ✅ Earnings release (with date and URL)
- ✅ 定期报告（交易所披露页链接与披露日期；H 股为港交所披露易）
- ✅ 电话会 transcript / 业绩说明会记录（标注替代性质与日期）
- ✅ 投资者演示/补充材料（若有）
- ✅ 一致预期来源（境内可得来源，标注口径与生成日期）
- ✅ Prior guidance (from previous quarter's materials)

**REFERENCE SECTION WITH CLICKABLE HYPERLINKS:**

Include "Sources" section at end of report:

```
SOURCES & REFERENCES

Earnings Materials (Q3 2024):
• Earnings Release (November 7, 2024)
  [Hyperlink entire line to: https://investor.company.com/news/q3-2024-earnings]

• 定期报告（2025 年 10 月 28 日披露）
  [Hyperlink to: 交易所披露页 / 巨潮资讯 / 港交所披露易链接]

• 电话会 / 业绩说明会记录（2025 年 10 月 28 日）
  [Hyperlink to: 公司投资者关系页或互动平台链接]

• 投资者演示材料（2025 年 10 月 28 日）
  [Hyperlink to: 公司投资者关系页链接]
```

**VERIFICATION CHECKLIST:**
- [ ] Every figure has source with specific document and date
- [ ] Every table has source with document reference
- [ ] Beat/miss analysis cites consensus source with date
- [ ] Guidance changes cite current and prior guidance sources
- [ ] Key statistics have footnotes
- [ ] Sources section lists all materials with URLs
- [ ] ALL URLs are CLICKABLE HYPERLINKS (not plain text)
- [ ] 定期报告均链接到交易所披露页（上交所/深交所/北交所/港交所披露易）

### 5. Updated Estimates
- Update forward estimates based on results
- Show old vs. new estimates clearly
- Explain what changed and why

## High-Level Workflow

The earnings update process follows 5 phases:

### Phase 1: Data Collection (30-60 minutes)

**🚨🚨🚨 CRITICAL: TRAINING DATA IS OUTDATED 🚨🚨🚨**

**BEFORE STARTING - COMPLETE THESE 4 STEPS IN ORDER:**
1. **CHECK TODAY'S DATE** - Write down the current date
2. **SEARCH FOR LATEST** - Use web search: "[Company] latest earnings results"
3. **VERIFY THE DATE** - Confirm earnings release is within last 3 months
4. **CHECK TRANSCRIPT DATE** - Verify transcript date matches release date

**COMMON MISTAKE**: Using outdated earnings calls from training data instead of searching for the latest.

**REQUIREMENTS:**
- ✅ Search for latest earnings - do NOT rely on training data
- ✅ Write down today's date and the release date found
- ✅ Verify release date is within 3 months of today
- ✅ Verify transcript date matches release date
- ✅ If dates don't match or are old (>3 months), search again

**See [references/workflow.md](references/workflow.md)** for detailed search procedures and verification steps.

### Phase 2: Analysis (2-3 hours)
- Beat/miss analysis for each key metric
- Segment/geographic/product breakdown
- Margin and guidance analysis
- Update financial model and estimates

**See [references/workflow.md](references/workflow.md)** for detailed analysis framework.

### Phase 3: Chart Generation (1-2 hours)
Create 8-12 charts focusing on quarterly trends and what's new:
- Quarterly revenue progression
- Quarterly EPS progression
- Quarterly margin trends
- Revenue by segment/geography
- Key operating metrics
- Beat/miss summary
- Estimate revisions
- Valuation charts

**See [references/workflow.md](references/workflow.md)** for chart specifications.

### Phase 4: Report Creation (2-3 hours)
Create 8-12 page DOCX report with specific structure.

**See [references/report-structure.md](references/report-structure.md)** for complete page-by-page templates and formatting requirements.

**High-level structure:**
- Page 1: Earnings summary with rating and price target
- Pages 2-3: Detailed results analysis
- Pages 4-5: Key metrics & guidance
- Pages 6-7: Updated investment thesis
- Pages 8-10: Valuation & estimates
- Pages 11-12: Appendix (optional)

### Phase 5: Quality Check & Delivery (30 minutes)
Verify content, formatting, accuracy, and timeliness before delivery.

**See [references/best-practices.md](references/best-practices.md)** for quality checklist and common mistakes to avoid.

## Output Specification

**Primary Deliverable**: DOCX report (8-12 pages)
**File Name**: `[Company]_Q[Quarter]_[Year]_Earnings_Update.docx`
**Example**: `Nike_Q2_FY24_Earnings_Update.docx`

**Contents:**
- Page 1: Summary with rating, price target, key takeaways
- Pages 2-3: Detailed results analysis
- Pages 4-5: Key metrics and guidance
- Pages 6-7: Updated thesis assessment
- Pages 8-10: Valuation and estimates
- Pages 11-12: Appendix (optional)
- 8-12 embedded charts
- 1-3 summary tables
- Complete sources section with clickable hyperlinks

**Optional Deliverable**: XLS model update (optional for earnings updates)

## Key Differences from Initiation Report

| Aspect | Earnings Update | Initiation Report |
|--------|----------------|-------------------|
| **Length** | 8-12 pages | 30-50 pages |
| **Words** | 3,000-5,000 | 10,000-15,000 |
| **Tables** | 1-3 summary | 12-20 comprehensive |
| **Figures** | 8-12 | 25-35 |
| **Turnaround** | 1-2 days | 3-6 weeks |
| **Scope** | Quarterly results | Complete company |
| **Focus** | What's NEW | Everything |
| **Company Background** | Brief mention | 6-10 pages |
| **XLS Model** | Optional | Required |

## Resources

### references/workflow.md
Detailed Phase 1-5 instructions with step-by-step procedures for data collection, analysis, chart generation, and report creation.

### references/report-structure.md
Complete page-by-page templates, table formats, and formatting requirements for the DOCX report.

### references/best-practices.md
Examples of good/bad headlines, tips for success, common mistakes to avoid, and comprehensive quality checklist.

## Dependencies

**Required:**
- Python (matplotlib, pandas, seaborn) for chart generation
- DOCX skill for report creation

**Optional:**
- XLS skill for model updates (not required for earnings updates)
