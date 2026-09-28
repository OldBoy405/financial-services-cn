---
description: Create an initiating coverage report
argument-hint: "[company ticker]"
---

## WorkBuddy 本地化（WB-CUSTOM）

**上游来源**：`anthropics/financial-services` @ `574ed3624aebd0418c7e96cd101262f30210ab26`（tag `baseline/upstream-574ed36`）；记录号见仓库根 `CUSTOM.md`。

- **本地化记录**：`WB-CUSTOM-11`
- **输入契约**：证券代码 + 交易所（`.SH`/`.SZ`/`.BJ`/`.HK`），报告期或日期，来源与口径（扣非/归母、CNY/HKD）；缺任一项先追问，不猜标的、不猜口径。
- **数据域（声明，不执行真实连接器读取）**：见 `agents/equity-research.md` §数据域路由 [1, 3 研报评级/目标价/全文, 4, 6 宏观]
- **保留的旧约束（不静默删除）**：Task 1～5 每次仅执行一个、逐步等待用户（五次独立人工关口，`⚠️ CRITICAL: One Task at a Time`）；Task 3 缺 Task 2 金融模型即停机索取；前置输入核验协议与 Verification Checklist by Task 保留；五份产物类别（研究文档 .md / 模型 .xlsx / 估值分析 .md+Excel 页 / 图表 .zip / 最终报告 .docx）与「不额外产出完成总结类文档」策略保留；不做端到端连跑。
- **中文等价口径**：SEC/EDGAR 资料改为交易所定期报告与披露平台；估值与目标价货币改为 CNY（A 股）/HKD（H 股）；可比公司取 A/H 同行业清单并标注分类口径差异；交付文件名与图表标签用中文。
- **明确缺口**：两融余额、增减持、NMPA 等行业审批、限售解禁、业绩预告/快报、央行/LPR/国常会、盘后披露及次日反应等机制须显式对照，但可得性取决于域授权，未授权时停机而非替代；`options-implied move` 无等价项；不声明美系机构数据能力。
- **安全与停机**：无授权、数据过期、无等价数据源时追问或停机，不编造、不静默替换；不对外发布研究结论、不写回机构系统。

Load the `initiating-coverage` skill and begin the 5-task workflow to create an institutional-quality initiation report.

If a ticker is provided, use it. Otherwise ask the user which company to initiate on.
