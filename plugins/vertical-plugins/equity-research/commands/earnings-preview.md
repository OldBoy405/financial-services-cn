---
description: Build a pre-earnings preview with scenarios
argument-hint: "[company ticker]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-16`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1, 2]
- **保留的旧约束（不静默删除）**：bull/base/bear 三情景；关键指标观察清单；不包含已发布结果的结论（预览与点评不混用）；缺标的时追问。
- **中文等价口径**：美元预期改为 CNY/HKD；美系一致预期来源改为境内可得来源并标注口径与日期；预约披露日/业绩预告/快报作为驱动事件显式对照。
- **明确缺口**：预告/快报覆盖不全时以定期报告为准并标注；无等价数据源时停机。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `earnings-preview` skill and build a pre-earnings analysis with consensus estimates, key metrics to watch, and bull/base/bear scenarios.

If a ticker is provided, use it. Otherwise ask the user which company is reporting.
