---
description: Update a financial model with new data
argument-hint: "[company ticker]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-12`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1, 2]
- **保留的旧约束（不静默删除）**：只在明确驱动事件（业绩预告/快报/定期报告/一致预期变更）下更新；记录每项改动理由与前后估算；不覆盖历史版本；GAAP/调整后口径的对立改为「扣非/归母」并列记录。
- **中文等价口径**：美元与美系一致预期来源改为 CNY/HKD 与境内一致预期源（标注日期）；披露文件改为交易所定期报告/业绩预告；英文篇幅与术语锚改为中文等价表述。
- **明确缺口**：一致预期口径未经核对不得与他源混用；无授权域不返回数据。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `model-update` skill and plug in new earnings, guidance, or revised assumptions.

If a ticker is provided, use it. Otherwise ask the user which model to update and what changed.
