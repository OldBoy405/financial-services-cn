# CR-2026-002 数据与授权 — 重装链路与复现（G4）

三张固定表：`重装步骤`（`RIN-NN`）、`环境依赖排查`（`ENV-NN`）、`重装后复现`（`REP-NN`）。
列名、列序与 ID 前缀取 `tests/_evidence.py#TABLE_COLUMNS`（CR-2026-002-TASK-01 §6）注册值，本文件不另立第二套定义。
`run-id` 沿用 `index.md#RunWindow` 的 `CR-2026-002-20261003`。

链路结论（由 `cmd-04` 机械断言，不得漂移）：**实际通过 1 行**（`RIN-01` 导出，本机实跑可重算）、**未执行缺口 5 行**
（`RIN-02`/`RIN-04`/`RIN-05`/`RIN-06`/`RIN-07`），另有 1 行 `不适用（无条件性修正）`（`RIN-03`，因目标校验未执行而无实测不符项），
`REP-01`～`REP-03` 全部 `未验证（待最终包安装）`。原因是 0.11.0 从未提交给目标机 WorkBuddy 客户端校验，本机亦无 `expert-manager`
通道（`ENV-05`）；按 §4.6/§4.7 与 TASK-04 §4，不得以静态文件比对充当安装或召唤回执，故本轮不以失败 `RIN` 签完成，TASK-04 未签 `done`。

## 重装步骤

| ID | 阶段 | 实际步骤 | 客户端/校验器/包版本 | 结果 | 证据引用 |
|---|---|---|---|---|---|
| RIN-01 | 导出（两次一致） | 2026-10-03 在本机仓根实跑 `python scripts/export_workbuddy_experts.py` 两次：两次 exit=0，单次耗时 0.134s / 0.133s（预算 120s 内），导出 24 件，两次相对路径与逐文件 SHA-256 集合全等；`evidence/` 未进入导出物 | 客户端=未参与 校验器=未参与 包=0.11.0 | 通过 | 本文件「导出与安装态实测」机器块 `导出两次一致`（`digest_set_sha256=b29844659c145f1609970e6915c2cd0db8bef21aabf1574bf577c843226080c9`、`files=24`、`identical=true`），由 `cmd-04` 现重跑两次并与本值比对；`plugin.json#version` 实测值见同块 `manifest_version` |
| RIN-02 | 目标校验（注册） | 未执行：0.11.0 包未提交目标机 WorkBuddy 客户端校验/注册。本机 `expert-manager` CLI 不存在（`ENV-05`），注册条目 `installed_plugins.json` 由客户端在安装时写入，本节点未手写、未伪造回执 | 客户端=37.10.3-24 校验器=未实测 包=0.11.0 | 阻塞（未执行） | 不适用（未执行；可重授权路径＝在目标机 WorkBuddy 客户端内从 `my-experts` 本地市场对 0.11.0 执行安装，使客户端写出注册条目并留下 `installedAt`/`version`/`installPath` 回执，随后把该回执的本机实测值登记到本行与 `RIN-05`；round3 的 `task04-target-machine.md` 已给出该途径在本机的实物先例，见「投递件哈希锚点」） |
| RIN-03 | 条件性修正 | 未发生：目标校验未执行，本轮没有任何实测不符项可修正，因此未改 `dependencies.connectors`、未改 `EXPECTED_CONNECTORS`、未改 `agents/equity-research.md` 声明条目；三处零差异是仓库侧机检结论，不是目标机接受回执（见 `DCL-01`、`DCL-02`） | 客户端=未参与 校验器=未参与 包=0.11.0 | 不适用（无条件性修正） | `DCL-01`、`DCL-02`；三处零差异由 `cmd-04` 现算比对 `scripts/export_workbuddy_experts.py` 的 `ALLOWED_PKG_FILES`/`EXPECTED_CONNECTORS` 与 `plugin.json` |
| RIN-04 | 卸下或隔离旧包 | 未执行：本节点未卸载、未删除、未改写任何插件注册项或 cache 目录。旧包现状只读登记于 `ENV-02`（0.10.0 与 2.1.0 两条目并存，版本化 cache 目录天然隔离） | 客户端=37.10.3-24 校验器=未参与 包=0.11.0 | 阻塞（未执行） | 不适用（未执行；可重授权路径＝安装 0.11.0 时在客户端卸下或隔离 `equity-research@my-experts 0.10.0`，并把客户端给出的卸除/隔离结果登记到本行；先例形态见 `ENV-02` 与 round3 投递件第二节第 4 步） |
| RIN-05 | 安装最终包 | 未执行：0.11.0 未进入安装态；安装产物目录仍只有 `my-experts/equity-research/0.10.0`（`ENV-02` 只读实测） | 客户端=37.10.3-24 校验器=未实测 包=0.11.0 | 阻塞（未执行） | 不适用（未执行；可重授权路径＝经 `RIN-02` 校验通过的最终包在客户端安装，登记注册条目实测值与安装件内 `plugin.json` 的 SHA-256；被安装件必须含 TASK-03 新增节，见 `agents/equity-research.md#数据动作判定顺序与降级/停止行为（FR-06 / FR-07）`） |
| RIN-06 | 新会话（仅保留包声明依赖） | 未执行：安装未发生，无新会话可观察；本节点运行在 Qoder CLI runtime，无连接器工具面（与 `safety-branches.md#登记口径` 第 1 条同一事实），不能自造会话回执 | 客户端=37.10.3-24 校验器=未实测 包=0.11.0 | 阻塞（未执行） | 不适用（未执行；可重授权路径＝安装 0.11.0 后在 WorkBuddy 新开会话，确认仅包声明的四个连接器在场，登记会话内实际工具面） |
| RIN-07 | 逐项复现 | 未执行：复现项 `REP-01`～`REP-03` 逐项待装后重放；本行不引用任何静态比对作为复现证据 | 客户端=37.10.3-24 校验器=未实测 包=0.11.0 | 阻塞（未执行） | 不适用（未执行；可重授权路径＝装后新会话逐条实际召唤与实取，把结果逐行写回 `REP-01`、`REP-02`、`REP-03`，其复现基准与重放参数已写在那三行的 `证据引用` 列） |

## 环境依赖排查

| ID | 排查对象 | 方法 | 结果 | 影响 |
|---|---|---|---|---|
| ENV-01 | 用户级全局 MCP 配置是否与新包声明依赖冲突 | 只读查看 `%USERPROFILE%\.workbuddy\mcp.json` 与 `%USERPROFILE%\.workbuddy\plugins\installed_plugins.json` 的通道分工 | 用户级 `mcp.json` 只有 `context-mode` 一个非插件通道 server；四个连接器的 MCP 定义在各自插件目录内的 `mcp.json`，由插件注册表管理，两者不是同一通道 | 重装后「新会话仅保留包声明依赖」的核对面是插件注册表与连接器的 `mcp.json`，不看用户级 `mcp.json`；本行同时说明 `safety-branches.md` 里 `~/.qoder/mcp.json` 空对象与本文件所用连接器不是同一通道 |
| ENV-02 | 旧包与版本隔离态 | 只读列举 `%USERPROFILE%\.workbuddy\plugins\cache\*\equity-research\*`，按注册条目逐条读 manifest | 并存两条：`equity-research@my-experts 0.10.0`（`installPath` 指向 `cache/my-experts/equity-research/0.10.0`，`installedAt=2026-09-29T06:54:07.733Z`，其安装件 `plugin.json` 实测 SHA-256 `2f7ef4ce4f2c7d869995d93585b04fd506936e1d9943779338d82ff327b0c5ab`，`dependencies.connectors` 为四标识）与 `equity-research@experts 2.1.0`（安装件 `plugin.json` SHA-256 `b8c153c80b08d32c5af99bcba64fc1347e56cf67342527a4a8cd3e7538743d2b`，无 `dependencies.connectors`）；版本化 cache 目录互不覆盖 | 升级 0.11.0 即新增版本目录并更新 `my-experts` 条目，0.10.0 留在 cache 即隔离态；两条不同市场的同名专家若同会话都启用会互相覆盖召唤入口，`RIN-04` 执行时须在客户端确认只启用 `my-experts` 那条 |
| ENV-03 | 安装态文件集与导出物文件集的差集 | 只读列举已装 0.10.0 安装件与 `out/workbuddy-experts/equity-research` 的文件清单逐字比较 | 安装件 25 件、导出物 24 件，差集只有一件宿主运行标记 `.in_use/6560`；两边都无 `evidence/**` 路径 | 重装后的对比判据是「导出物 ⊆ 安装件且差集仅宿主运行态文件」，不是两边字节集合相等；若 `.in_use` 残留在卸旧后仍指向已卸版本，按阻塞处理并写明清理路径 |
| ENV-04 | 私有绝对路径、凭据与敏感文件残留 | 用导出脚本同源的两组正则（dep-3：`SENSITIVE_NAME_RE` / `SENSITIVE_CONTENT_RE`）扫 0.11.0 导出物 24 件与本 CR `evidence/**` | 文件名命中 0、内容命中 0；凭据面只登记存储机制与位置（连接器账户由宿主插件托管），本轮未读取任何凭据内容 | 导出物可进入目标机安装态；`REP-03` 的缺权限负例复现须在同一账户内实际调用，不能由本行的扫描结论代替 |
| ENV-05 | 校验器版本与校验通道 | `which expert-manager` 探测；只读 `installed_plugins.json` 内 `@workbuddy-builtin` 各插件 `version` 与 `lastUpdated` | 本机无 `expert-manager`（未命中）；宿主插件套件现值 `5.6.2-wb.39298511.g37a65c0b.he233403f909a`（`lastUpdated` 2026-10-01T13:31），CR1 记录的历史校验器值 `5.5.6-wb.38337834.g5f969292.h7826dc9400fd` 只作参考点 | 0.11.0 的「校验器版本」只能取重装时客户端实测回执，本轮两个参考点都不是回执，故 `index.md#RunWindow` 的该行保持 `待确认`；不自制校验器（§4.6 与 NFR-02） |
| ENV-06 | 目标机身份与 G4 目标机条件 | 读本机 `version` 文件与主机名，并与 round3 投递件第三节逐字段比对（`客户端版本`/`主机名`/`连接器在场`） | 主机名 `DESKTOP-OT18TRG`、WorkBuddy `37.10.3-24`、四连接器安装条目齐备且被 round3 采集会话实际调用成功（`SBC-07-NC`/`SBC-07-AT`/`SBC-08-HQ` 三次 neodata 真实请求）——采集会话所在机具备 G4 重装链路的全部条件 | 本行只登记事实层结论：本机可执行 G4 链路。「G4 目标机」的正式指定不由本行代替（round3 投递件自身声明该指定归 TASK-04 实施与 Ray，Ray 侧尚未书面指定），因此 `RIN-02`～`RIN-07` 仍以人工安装回执为前提，不因本行而放行 |

## 重装后复现

| ID | 复现项 | 结果 | 证据引用 | 是否可复现 |
|---|---|---|---|---|
| REP-01 | 九项路由（命令→唯一技能，九项映射 MR-01..09） | 阻塞（未执行：0.11.0 未安装、无新会话） | 不适用（未执行；复现基准＝`README.md#2.1` 的九项映射与 `agents/equity-research.md#九项路由（恰九项）`，`cmd-03` 的 `test_agent_existing_routes_and_guards_untouched` 已机检源侧九项未被改动，但源侧比对不等于装后复现；可重授权路径＝装后新会话内逐条命令实际召唤并登记回复选中项） | 未验证（待最终包安装） |
| REP-02 | 已授权域真实查询（七域采用行） | 阻塞（未执行：0.11.0 未安装、本 runtime 无连接器工具面） | 不适用（未执行；复现基准＝`queries.md#查询溯源` 的 `QRY-01`～`QRY-09` 与 `queries.md#单指标单源` 采用裁决，可按各行 `复核路径` 在同一授权账户重发；可重授权路径＝装后新会话按 `复核路径` 逐条重发并比对字段清单与期间覆盖） | 未验证（待最终包安装） |
| REP-03 | 缺权限负例 | 阻塞（未执行：0.11.0 未安装、无新会话） | 不适用（未执行；复现基准＝`safety-branches.md#负例核验记录对象` 的 `NZ-01`～`NZ-04` 与 `#安全分支实测记录对象` 的 `SBC-07-NC`；须按 `safety-branches.md#登记口径` 第 4 条的负面事实另择受控方式，注入无效凭据未复现拒绝，不得用该方式构造本行） | 未验证（待最终包安装） |

## 登记口径（G4 节点裁定）

1. **未执行的阶段一律记 `阻塞（未执行）`，不记 `不适用（无数据）`**：`RIN-02`～`RIN-07` 的缺口由 `cmd-04` 与 `RIN` 前言声明同值断言，
   使「导出通过」不能被读成「重装链路通过」；TASK-04 因此未签完成，`crctl task done` 未调用。
2. **`客户端=` 与 `包=` 是机器字段**：`cmd-04` 从每行 `RIN` 抽 `包=<v>` 与 `plugin.json#version` 双向核对，抽 `客户端=<v>` 与
   `index.md#RunWindow` 的「客户端版本」现值核对（`未参与` 表示该阶段不经客户端），使版本行不能被写成任意文案。
3. **投递件路径一律写包内相对路径**：round3 投递件所在的本机绝对路径不进入本文件；`cmd-04` 与 `cmd-03` 同口径做私有绝对路径扫描。
4. **`my-experts` 市场目录不是源目录**：`~/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research` 是安装位置形态
   （§4.6 末行），本节点未向该目录写入任何内容，也不把它的存在当作市场或安装证明。
5. **entry 名不符的归属**：`safety-branches.md` 转给 G4 的 tdx entry 名不符事实，其不符对象不在本 CR 包内声明条目（源清单、导出物与
   `agents/equity-research.md` 全文均无该串，见 `DCL-02`），故按 §4.7 登记而不修正，不改 `plugins/**`。

## 导出与安装态实测

```json
{
  "说明": "本节点实跑值；由 cmd-04 现重跑比对，不含任何本机私有绝对路径",
  "导出两次一致": {
    "命令": "python scripts/export_workbuddy_experts.py（仓根，两次）",
    "exit": [0, 0],
    "files": 24,
    "identical": true,
    "elapsed_s": [0.134, 0.133],
    "digest_set_sha256": "b29844659c145f1609970e6915c2cd0db8bef21aabf1574bf577c843226080c9",
    "manifest_version": "0.11.0",
    "connectors": ["wind-finance", "tdx-connector", "neodata", "westock-mcp"],
    "evidence_in_export": []
  },
  "安装态对照": {
    "installed_0.10.0_manifest_sha256": "2f7ef4ce4f2c7d869995d93585b04fd506936e1d9943779338d82ff327b0c5ab",
    "installed_0.10.0_file_count": 25,
    "export_file_count": 24,
    "diff_only_in_installed": [".in_use/6560"],
    "marketplace_2.1.0_manifest_sha256": "b8c153c80b08d32c5af99bcba64fc1347e56cf67342527a4a8cd3e7538743d2b"
  }
}
```

## 投递件哈希锚点

`round3/task04-target-machine.md` 是本 TASK 目标机事实的输入件；下表为包内相对路径与本机实测 SHA-256，
清单为 CRLF，按 `safety-branches.md#登记口径` 第 8 条的归一口径复核（`tr -d '\r' | sha256sum -c --strict -` 6/6 OK、exit=0）。

```json
{
  "说明": "包内相对路径与实测值；不含任何本机私有绝对路径",
  "round3/SHA256SUMS.txt": "dbb3d86b0efc5b0a30e5cfdd9045ce6803290dcc3774bff328635367de418602",
  "round3/task04-target-machine.md": "fc47f7ce5eace5721c4cb8662440f5e67fc78c144c66cf4face759a58d2dd3a6",
  "round3/verify-records.json": "e9b0271ace9f4679ada8a5216b5174ee47a72a8806bf8a8fff343425b9f25536",
  "round3/verify-records.sha256.json": "d40eb0fb3558e834277d4ad413d994f8803ccca1a93981034e842dfd80732c15",
  "round3/sensitive-selfcheck.txt": "473f46823104689929b6cecd0582102ba444fb8d3fed797aa42a402ae6b4e2a4"
}
```
