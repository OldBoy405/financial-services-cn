---
description: Run a stock screen or generate investment ideas
argument-hint: "[screen criteria, e.g. 'undervalued midcap tech']"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-13`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [5 筛选, 4]
- **保留的旧约束（不静默删除）**：输出候选清单与理由、标注数据来源、不把筛选结果当研究结论；筛选条件（方向/行业/风格/市值）追问保留。
- **中文等价口径**：美系 screener 字段改为 A/H 可得字段（市值、行业分类、涨跌幅、估值分位、两融/资金指标仅在授权域可用）；筛选工具分层声明为 `westock-tool` → `tdx-connector` / `wind-finance`。
- **明确缺口**：筛选等价口径未核实即停机，不偷偷替换工具；无授权域不返回数据；非上市主体不可筛选。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `idea-generation` skill and run quantitative screens or thematic sweeps to surface new investment ideas.

If criteria are provided, use them. Otherwise ask the user what they're looking for (long/short, sector, style, theme).
