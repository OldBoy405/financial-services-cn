# CR-2026-002 数据与授权 — 证据索引（G1）

本文件是 CR-2026-002 证据链的入口：`RunWindow` 运行窗口、`Cr1IntakeRow` CR1 输入核对、
四类交付物入口，以及由证据命令计算、与 `out/evidence/data-authorization/coverage.json`
同值的覆盖率摘要。安装/连接/许可的实际授权状态在 `data-sources.md` 台账逐条登记；
未获 Ray 目标机与账户事实的行按封闭枚举如实记为 `待确认`/`缺账号权限`/`阻塞`，不补造。

## RunWindow

| 字段 | 值 |
|---|---|
| run-id | CR-2026-002-20261003 |
| 首次采集时间 | 2026-10-03T14:58:00+08:00 |
| 末次采集时间 | 2026-10-03T15:20:00+08:00 |
| 客户端版本 | 待确认（目标机 WorkBuddy 客户端未在本工作区采集，属 G4 目标机实测） |
| 校验器版本 | 待确认（目标机校验器未在本工作区采集，属 G4 目标机实测） |
| 包版本 | 0.10.0（G4 前源清单现值；`plugin.json#version` 由 0.10.0 升至 0.11.0 在 G4 落盘） |

## CR1 输入核对

核对 CR1（workbuddy/main，HEAD `9a407adc0adc6cb72645648a872b283137daf7f6`）的只读沿用件。
`CR1 版本/SHA` 为对应文件在代码仓 CR worktree 的实测 SHA-256；`核对结果` 表示该 CR1 记录是否
已核到（非研究质量裁决）。

| 核对项 | CR1 版本/SHA | 证据位置 | 核对结果 |
|---|---|---|---|
| CR1 导出包源清单（manifest） | a8df0b13a4e962d2c6a82bd7aedc15f04abd04579803b1985324baf1b9fdda9b | workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json | 通过 |
| 九项路由记录（命令→唯一技能） | 1d6f5f1aa78bc075d5b75d207536026d9f19615e01662a3b77a033dc2611c6af | workbuddy-experts/equity-research/README.md#2 | 通过 |
| 九项映射 MR-01..09 | 1d6f5f1aa78bc075d5b75d207536026d9f19615e01662a3b77a033dc2611c6af | workbuddy-experts/equity-research/README.md#2.1 | 通过 |
| 固定样例 SAMPLE-01（603599/SH/2025 年报） | 1d6f5f1aa78bc075d5b75d207536026d9f19615e01662a3b77a033dc2611c6af | workbuddy-experts/equity-research/README.md#3 | 通过 |
| ACCEPTANCE 分层裁决与记录位模板 | c9594c68c037237448f5eb4a09236ae5bc51bb8ca24d26211259d1db5d58b866 | workbuddy-experts/equity-research/ACCEPTANCE.md | 通过 |
| Agent 七域声明（数据域路由） | 822aba6fb3cd818aab4e0673d18aae5b5b490373a524f4ca67bbb4202f8f01e9 | workbuddy-experts/equity-research/agents/equity-research.md | 通过 |
| 导出与宿主联调回执（G4 host receipt） | 1d6f5f1aa78bc075d5b75d207536026d9f19615e01662a3b77a033dc2611c6af | workbuddy-experts/equity-research/README.md#5 | 阻塞 |

说明：`导出与宿主联调回执` 的版本化记录存在且自洽（24 files、校验器 5.5.6-wb.38337834.g5f969292.h7826dc9400fd、
头像 SHA `616fd6bbe88fd811ecbb97defb7bbe815c5c9c05368bc33569341e43877f3897` 与 README §5 一致），但其原始件与安装
产物落在被忽略区 `out/`，本工作区未呈现，重装有效性的复核对齐 CR-2026-002 G4 目标机实测后解除，故 CR1 输入核对
该项如实记 `阻塞`（不伪称本机已复核到实装件）。SAMPLE-01 的 `阻塞`/`通过` 只判定 CR1 索引记录是否核到；原件只放
`out/`，本 CR 只读沿用、不复制原件、不重新裁决。

## 交付物入口

四类交付物入口，指向 `evidence/**` 各文件（`queries/safety-branches/reinstall/domain-readiness/declarations`
由 G2～G5 落盘，本 TASK 先立入口）。路径为仓库根相对路径。

| 交付物类别 | 入口路径 | 说明 |
|---|---|---|
| 台账 | workbuddy-experts/equity-research/evidence/data-sources.md | LAT/CON/LIC 安装·连接·许可台账（G1） |
| 逐域查询证据 | workbuddy-experts/equity-research/evidence/queries.md | SMP/QRY/SRC/口径审查（G2 落盘） |
| 正反例与降级记录 | workbuddy-experts/equity-research/evidence/safety-branches.md | ORD/SBC 判定顺序与九场景实测（G3 落盘） |
| 重装与版本记录 | workbuddy-experts/equity-research/evidence/reinstall.md | RIN/ENV/REP 重装链路与 DCL 声明修正（G4 落盘） |

## 覆盖率摘要

数值由证据命令计算并与 `coverage.json` 同键同值；G1 可算的指标如实登记，依赖 G2～G5 数据的
指标在当前无对应 `evidence` 行时为 0，由 cmd-05 复核后刷新。不手写估算数。

| 指标 | 计数 | 生成时间 |
|---|---|---|
| 六入口台账条数 | 6 | 2026-10-03T15:20:00+08:00 |
| 连接器标识条数 | 4 | 2026-10-03T15:20:00+08:00 |
| 许可记录条数 | 18 | 2026-10-03T15:20:00+08:00 |
| 用途许可已确认数 | 6 | 2026-10-03T17:00:00+08:00 |
| 七域实取成功数 | 0 | 2026-10-03T15:20:00+08:00 |
| 域可用计数 | 0 | 2026-10-03T15:20:00+08:00 |
| 安全场景实测数 | 0 | 2026-10-03T15:20:00+08:00 |
| CR1 输入核对通过数 | 6 | 2026-10-03T15:20:00+08:00 |
| 交付物入口数 | 4 | 2026-10-03T15:20:00+08:00 |
