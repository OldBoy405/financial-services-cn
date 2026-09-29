---
description: Create or update an investment thesis
argument-hint: "[company ticker]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-18`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [4, 1]
- **保留的旧约束（不静默删除）**：论点计分卡（支柱/原预期/当前状态/趋势）；更新日志字段（日期/数据点/论点影响/动作/更新后信心）；催化剂日历；至少季度复核；可证伪性要求；存储为可跨会话引用的结构化格式。
- **中文等价口径**：目标价与止损触发改为 CNY（A 股）/HKD（H 股）；英文晨会/投委会格式改为中文等价模板；数据点来源改为定期报告/公告/政策事件。
- **明确缺口**：大股东增减持、股权质押等 A 股特有数据点依赖授权域，未授权时标注缺失；不把未核实数据点写入论点计分卡。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `thesis-tracker` skill to create a new thesis or update an existing one with new data points.

If a ticker is provided, use it. Otherwise ask the user which position to review.
