---
description: View or update the catalyst calendar
argument-hint: "[timeframe, e.g. 'next 2 weeks']"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-14`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [4, 1, 6]
- **保留的旧约束（不静默删除）**：事件按影响程度分级色标；已发生事件归档实际结果；覆盖范围默认自选股清单；时间窗默认未来两周（可覆盖）。
- **中文等价口径**：美元事件金额改为 CNY/HKD；美系日历来源改为境内公告日历与宏观日历；定期报告披露排期、业绩预告窗口、解禁日、股东大会、央行/LPR/国常会等机制显式对照。
- **明确缺口**：未公告事件的日期为预计，必须标注「预计」而非公告事实；无授权时不取用私有日历数据。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `catalyst-calendar` skill to build or review upcoming catalysts across the coverage universe.

If a timeframe is provided, use it. Otherwise default to the next 2 weeks.
