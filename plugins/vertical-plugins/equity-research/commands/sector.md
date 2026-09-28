---
description: Create a sector overview report
argument-hint: "[sector or industry]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-17`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [3, 4, 6]
- **保留的旧约束（不静默删除）**：四段结构（市场规模与增长、竞争格局、关键玩家、主题趋势）；概览 5-10 页 / 深挖 20-30 页两档深度；用途与视角追问保留。
- **中文等价口径**：美元市场规模改为 CNY/HKD 并标注统计口径与年份；美系行业分类改为境内行业分类并标注映射差异；关键玩家以 A/H 上市公司披露为准。
- **明确缺口**：非上市主体数据可得性受限须标注；主题观点不得当作研究结论发布；无授权域不返回数据。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `sector-overview` skill and create an industry landscape report covering market sizing, competitive dynamics, and investment implications.

If a sector is provided, use it. Otherwise ask the user which industry to cover.
