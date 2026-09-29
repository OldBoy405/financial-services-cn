---
description: Draft a morning meeting note
argument-hint: ""
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-15`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [4, 7 资金/龙虎榜/两融]
- **保留的旧约束（不静默删除）**：简洁早报体裁（隔夜动态/业绩反应/交易想法）；不输出未核实的交易建议；覆盖范围可配置。
- **中文等价口径**：美元指数与外盘栏目改为「以 A/H 为主、外盘为参考」并标注来源；A/H 交易时段差异显式说明；日期锚改为交易日。
- **明确缺口**：盘前/盘后价格序列无等价项；资金/龙虎榜/两融存在覆盖缺口，须在使用处标明。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `morning-note` skill and draft a concise morning note covering overnight developments, earnings reactions, and trade ideas across the coverage universe.
