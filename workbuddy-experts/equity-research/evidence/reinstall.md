# CR-2026-002 数据与授权 — 重装链路与复现（G4）

三张固定表：`重装步骤`（`RIN-NN`）、`环境依赖排查`（`ENV-NN`）、`重装后复现`（`REP-NN`）。
列名、列序与 ID 前缀取 `tests/_evidence.py#TABLE_COLUMNS`（CR-2026-002-TASK-01 §6）注册值，本文件不另立第二套定义。
`run-id` 沿用 `index.md#RunWindow` 的 `CR-2026-002-20261003`（跨日延伸口径见「登记口径」第 8 条）。

链路结论（由 `cmd-04` 机械断言，不得漂移）：**实际通过 4 行**（`RIN-01` 导出、`RIN-02` 目标校验/注册、
`RIN-04` 卸旧隔离、`RIN-05` 安装最终包）、**未执行缺口 2 行**（`RIN-06` 新会话仅保留包声明依赖、
`RIN-07` 逐项复现全项），另有 1 行 `不适用（无条件性修正）`（`RIN-03`，目标校验实测 0 error ⇒ 无不符项可修正）。
`REP-01`/`REP-02` = `是`，`REP-03`（缺权限负例）= `否`：其拒绝前提在装后已消失或不可达（`ENV-08`），
不得以 `tool-not-mounted` 冒充 `permission-denied`（§4.6 与 `safety-branches.md#登记口径` 第 4 条）。
0.11.0 已由目标机 WorkBuddy 客户端校验（`validate_expert.py` EXIT=0）并原生安装（注册条目 `version=0.11.0`），
本轮不再以「未提交校验」为缺口；剩余两项缺口均为需要 Ray 侧建立的动态前提（`RIN-06` 的 GUI 收敛＋新会话、
`REP-03` 的无权限/无积分真实账户），按 §4.6「失败保持域阻塞并给重授权路径」保持阻塞，
不缩小 AC、不改写 `cmd-04` 的复现断言（plan 风险与回滚 4）。因此 TASK-04 未签 `done`，`crctl task done` 未调用。

## 重装步骤

| ID | 阶段 | 实际步骤 | 客户端/校验器/包版本 | 结果 | 证据引用 |
|---|---|---|---|---|---|
| RIN-01 | 导出（两次一致） | 2026-10-03 在本机仓根实跑 `python scripts/export_workbuddy_experts.py` 两次：两次 exit=0，单次耗时 0.134s / 0.133s（预算 120s 内），导出 24 件，两次相对路径与逐文件 SHA-256 集合全等；`evidence/` 未进入导出物 | 客户端=未参与 校验器=未参与 包=0.11.0 | 通过 | 本文件「导出与安装态实测」机器块 `导出两次一致`（`digest_set_sha256=b29844659c145f1609970e6915c2cd0db8bef21aabf1574bf577c843226080c9`、`files=24`、`identical=true`），由 `cmd-04` 现重跑两次并与本值比对；`plugin.json#version` 实测值见同块 `manifest_version` |
| RIN-02 | 目标校验（注册） | 2026-10-04 目标机 A 段：先把 `out/workbuddy-experts/equity-research`（0.11.0，24 件）同步进用户级市场源 `%USERPROFILE%/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research`（`diff -rq` 0 行、替换后 24 件，回退点备份 24 件在场），再以客户端自带 expert-manager cache 副本 `5.6.2-wb.39298511.g37a65c0b.he233403f909a/scripts/validate_expert.py` 执行安装前目标校验：`23:45:25~23:45:26+08:00` EXIT=0、输出 `✅ Expert package is valid!`、仅 1 条非阻塞警告（`displayDescription.zh` 100 chars，建议 40-50）；随后 `register_expert.py` 注册 `23:45:27+08:00` EXIT=0（新增分支）与 `23:52:07~08+08:00` EXIT=0（幂等重跑走更新分支，条目数 BEFORE=1 / AFTER=1），终态 `marketplace.json` 为单条目 `source=./plugins/equity-research`（清单本身无版本字段，版本号取自源目录 `plugin.json`）。前提事实：校验必须在同步之后、对专家目录内路径执行；对目录外路径校验器直接 EXIT=1（`专家不在专家目录下`），属路径性拒绝而非包内容拒绝 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 被校验对象实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`（本节点在仓内源清单、`out/` 导出物、市场源目录、安装件四处分别复算，三处目录内同值，见「导出与安装态实测」机器块）；注册条目终态实测（`installed_plugins.json` 由客户端在 `RIN-05` 安装时写入，A 段未触碰该文件）：`installedAt=2026-09-29T06:54:07.733Z`、`lastUpdated=2026-10-03T16:37:46.455Z`、`version=0.11.0`、`installPath` 指向 `cache/my-experts/equity-research/0.11.0`；执行侧原件 `round4/rin02-receipt.md`（哈希见「投递件哈希锚点」）；校验器 cache 副本目录与 `validate_expert.py`/`register_expert.py`/`package_expert.py` 在场由本节点只读复现（`ENV-05`） |
| RIN-03 | 条件性修正 | 未发生：`RIN-02` 的 0.11.0 目标校验实测 0 error（唯一警告是 `displayDescription.zh` 长度建议，属非阻塞），`dependencies.connectors` 的四标识被目标版本按现写法识别，声明条目未被指出不符 ⇒ 未改 `dependencies.connectors`、未改 `EXPECTED_CONNECTORS`、未改 `agents/equity-research.md` 声明条目，三处零差异；本轮不再依赖「未执行校验故无不符项」的前一版依据，改判依据是 0.11.0 的校验回执本身（见 `DCL-01` 结论与 `DCL-02`） | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 不适用（无条件性修正） | `DCL-01`、`DCL-02`（两行结论均为 `无需修正`）；三处零差异由 `cmd-04` 现算比对 `scripts/export_workbuddy_experts.py` 的 `ALLOWED_PKG_FILES`/`EXPECTED_CONNECTORS` 与 `plugin.json`；警告原文与 0 error 结论在 `round4/rin02-receipt.md` A2 段 |
| RIN-04 | 卸下或隔离旧包 | 走「隔离」形态且为客户端原生写入：安装 0.11.0 时客户端于升级同秒对旧 0.10.0 cache 目录写孤儿标记 `.orphaned_at`=1791045466458（= `2026-10-03T16:37:46.458Z`，本地 `00:37:46.458+08:00`），注册条目 `installPath` 改指 0.11.0，0.10.0 脱离激活路径；旧目录内 `.in_use/6560` 为 2026-09-29 旧进程残留锁（procStart `2026-09-29T06:42:07Z`），非当前引用。其后应用户明确指令删除该孤儿目录（删除前置条件：备份 `%USERPROFILE%/.workbuddy/plugins/backup-my-experts-equity-research-0.10.0-20261003-234359` 24 件校验通过、隔离证据已先录入回执）；本节点只读复现：`cache/my-experts/equity-research/` 下现仅 `0.11.0`，备份目录在场且其 `plugin.json` 复算值与登记的前版本安装件哈希同值 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 激活安装件实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`、注册条目 `installedAt=2026-09-29T06:54:07.733Z`／`lastUpdated=2026-10-03T16:37:46.455Z`（本节点直读 `%USERPROFILE%/.workbuddy/plugins/installed_plugins.json` 复算，`equity-research@my-experts` 单条目）；`.orphaned_at` 与删除前后核验在 `round4/rin0405-install-receipt.md`（含「后续清理」注记），其哈希见「投递件哈希锚点」；前版本 manifest 哈希只作差集对比与备份忠实性核对用（机器块 `安装态对照`），本行不以它充当完成标志 |
| RIN-05 | 安装最终包 | 客户端原生安装，无手写注册项：用户在 GUI 重启客户端后触发，安装动作时刻 `2026-10-04T00:37:46.455+08:00`（注册表 `lastUpdated` 原值 `2026-10-03T16:37:46.455Z`）；`installed_plugins.json` 由客户端写入（mtime `2026-10-04T00:37:46.456+08:00`）`equity-research@my-experts` 条目 `version=0.11.0`、`installPath=…\cache\my-experts\equity-research\0.11.0`；cache 目录 mtime `00:37:46.452~48+08:00` 与 `lastUpdated` 同秒；0.11.0 持有当前 `.in_use` 进程锁。本节点 2026-10-04 03:1x 只读复算：安装件 `plugin.json` 与 `out/` 导出物、市场源目录三处 SHA-256 全等于 `f25b4a20…`，条目 `version` 与 `plugin.json#version` 双向一致 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 安装件实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`（本节点复算）／`installedAt=2026-09-29T06:54:07.733Z`（客户端字段语义＝首次安装时刻，升级保留；本次升级时刻取 `lastUpdated`）；安装件文件集与导出物的差集判据见 `ENV-03`（本节点实测差集仅 4 个 `.in_use` 宿主运行标记）；被安装包内含 TASK-03 新增节由 `cmd-04` 的 `test_agent_declaration_section_ships_in_package` 对导出物断言（安装件与导出物逐文件同哈希，故该断言传递到安装件）；原件 `round4/rin0405-install-receipt.md` |
| RIN-06 | 新会话（仅保留包声明依赖） | 阶段条件未达成，两侧事实都登记：新会话本身成立——会话 B（`8f4e6e95-aef4-4a00-9be1-bf8007f1b898`）于 `00:48:30+08:00` 启动，是安装后的第一个新会话，Agent 面仅 `equity-research (equity-research@my-experts:agents)`、技能面为 0.11.0 九项、官方 2.1.0 的 7 个独有技能不在面 ⇒ 召唤入口未被同名条目覆盖。但「仅保留包声明依赖」在该会话不成立：四连接器只在 manifest 声明层在场、工具未挂载（12 条代表工具调用全部 `Tool … not found in the deferred tools index`），连接器状态文件六条 `enabled:false`（wind/neodata OAuth 已过期），而非声明的 `agent-mail`（内置服务，13 个工具在场）与 `genie-baas`/`sheetagent`/`weixinpay` 三个捆绑 MCP 仍在工具面。其后用户 GUI 重连使四连接器可调用（02:19~02:22 复测零 `tool-not-mounted`），但那是安装前的旧会话（会话 A `f09480ee`），且 `ifind-mcp` 因重连侧效应回退为 connected。本节点 2026-10-04T03:14:45+08:00 只读复现连接器状态文件现值：`neodata`/`tdx-connector`/`westock-mcp`/`wind-finance`（连同 `teacher-assistant`/`tushare`）六条 `enabled:false`，即当前不存在「四声明连接器在场且仅在场」的会话面（`ENV-07`） | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 阻塞（新会话仅保留包声明依赖未达成） | 不适用（未执行——「新会话仅保留包声明依赖」这一阶段条件在任何已观察会话均未成立：会话 B 缺四连接器工具面且含非声明项，会话 A 非装后新会话且含非声明的 `ifind-mcp`，本节点复现的连接器现值仍是六条 `enabled:false`）。可重授权路径＝Ray 在客户端连接器管理 GUI 重连 `wind-finance`/`tdx-connector`/`neodata`/`westock-mcp`（wind/neodata 需 OAuth 重授权），断开 `agent-mail`（若客户端对该内置服务不提供开关，则由 Ray 书面确认其为内置不可断项，本节点按确认登记而不代为判定），随后**新开会话**并登记该会话的实际工具面与四连接器挂载结果；官方同名 `equity-research@experts 2.1.0` 的耐久停用＝专家中心卸载（本节点只读实测注册表现值已无该条目、备份 `installed_plugins.json.bak-rin06-20261004-010110` 在场，但市场条目与 2.1.0 缓存仍在原处可被重新注册，见 `ENV-02`）。会话面原件 `round4/rin06-session-tool-surface.md`、恢复路径原件 `round4/rep02-retest-receipt.md` |
| RIN-07 | 逐项复现 | 三项复现已逐项实际执行，唯 `REP-03` 无拒绝前提可用：`REP-01` 九项路由在会话 B 内逐条实际召唤（8 Route / 1 Clarify / 0 Stop，`Clarify` 是 `model-update` 输入契约的追问而非缺口，`Stop` 未触发的原因已在回执登记）；`REP-02` 已授权域真实查询在 GUI 重连后按 12 条复核路径原样重发，11 项成功且与 round2/round3 原始记录同构或逐值一致（`VR-06` 一次瞬时限频后重试成功、`SBC-08` 一次参数名偏差后按原始参数修正重发）；`REP-03` 缺权限负例（`NZ-01` tushare 40203、`NZ-02..04` wind 账户积分不足）在装后均不可复现，原因与不可采用的人工构造方式见 `ENV-08`。本行不引用任何静态文件比对作为复现证据 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 阻塞（缺权限负例未复现） | 不适用（未执行——`REP-03` 的 permission-denied 触发前提在 0.11.0 装后不可建立，故「逐项复现」未全项达成；`REP-01`/`REP-02` 的实测结果已分别登记在 `重装后复现` 表内，不因本行阻塞而降格）。可重授权路径＝由 Ray 提供一个对 `cyq_perf` 接口无权限、或 wind 账户积分实际耗尽的真实账户（或该接口停机窗口），在 `RIN-06` 收敛后的新会话内按 `safety-branches.md#负例核验记录对象` 的 `NZ-01`～`NZ-04` 原参数重放并原文留证；不得以 `tool-not-mounted` 冒充 `permission-denied`，不得注入无效凭据构造（该受控方式已实测未复现拒绝，`safety-branches.md#登记口径` 第 4 条）。执行侧原件 `round4/rin07-rep-receipt.md`（会话 B）与 `round4/rep02-retest-receipt.md`（会话 A 复测） |

## 环境依赖排查

| ID | 排查对象 | 方法 | 结果 | 影响 |
|---|---|---|---|---|
| ENV-01 | 用户级全局 MCP 配置是否与新包声明依赖冲突 | 只读查看 `%USERPROFILE%/.workbuddy/mcp.json` 与 `%USERPROFILE%/.workbuddy/plugins/installed_plugins.json` 的通道分工 | 用户级 `mcp.json` 只有 `context-mode` 一个非插件通道 server；四个连接器的 MCP 定义在各自插件目录内的 `mcp.json`，由插件注册表管理，两者不是同一通道 | 重装后「新会话仅保留包声明依赖」的核对面是插件注册表与连接器的 `mcp.json`，不看用户级 `mcp.json`；本行同时说明 `safety-branches.md` 里 `~/.qoder/mcp.json` 空对象与本文件所用连接器不是同一通道 |
| ENV-02 | 旧包与版本隔离态 | 只读列举 `%USERPROFILE%/.workbuddy/plugins/cache/my-experts/equity-research/*` 与 `installed_plugins.json` 现值，并与回执逐字段比对 | 升级后 cache 下仅 `0.11.0`（本节点实测）；旧 0.10.0 先被客户端写 `.orphaned_at`=1791045466458 隔离、后经用户指令删除，删除前备份 24 件在场，其 `plugin.json` 复算值 = 前版本安装件哈希 `2f7ef4ce4f2c7d869995d93585b04fd506936e1d9943779338d82ff327b0c5ab`（备份忠实）；官方同名 `equity-research@experts 2.1.0` 的注册条目已被移除，本节点只读实测 `installed_plugins.json`（mtime `2026-10-04T01:01:35+08:00`）内 equity 条目仅 `equity-research@my-experts` 一条，同目录留有 `installed_plugins.json.bak-rin06-20261004-010110` | 两条同名条目同会话互相覆盖召唤入口的风险当前未实现（`RIN-06` 实测会话 B 入口=0.11.0）；该停用是文件级注销，市场条目与 2.1.0 缓存仍在原处，客户端下次市场扫描/重启可重新注册，耐久停用需 GUI 卸载（列入 `RIN-06` 可重授权路径）；本行也给出 `cmd-04` 排除「修正前包回执」的现值来源 |
| ENV-03 | 安装态文件集与导出物文件集的差集 | 只读列举已装 0.11.0 安装件与 `out/workbuddy-experts/equity-research` 的相对路径集合，逐字求差集（本节点 2026-10-04 实测） | 安装件 28 件、导出物 24 件；`only_in_installed` = `.in_use/17264`、`.in_use/20880`、`.in_use/21076`、`.in_use/26076` 四个宿主运行标记，`only_in_export` 为空；两边都无 `evidence/**` 路径 | 重装后的对比判据是「导出物 ⊆ 安装件且差集仅宿主运行态文件」，不是两边字节集合相等；本行现值取代 0.10.0 时代的单标记 `.in_use/6560`（该条目随 0.10.0 目录已删除，见 `ENV-02`）；若 `.in_use` 残留在卸旧后仍指向已卸版本，按阻塞处理并写明清理路径 |
| ENV-04 | 私有绝对路径、凭据与敏感文件残留 | 用导出脚本同源的两组正则（dep-3：`SENSITIVE_NAME_RE` / `SENSITIVE_CONTENT_RE`）扫 0.11.0 导出物 24 件与本 CR `evidence/**`；投递件侧另核采集会话自带的自检件 | 文件名命中 0、内容命中 0；凭据面只登记存储机制与位置（连接器账户由宿主插件托管），本轮未读取任何凭据内容——`RIN-06` 的 OAuth 结论只取令牌有效期字段与 `enabled` 标志，不取值；round4 自带 `sensitive-selfcheck.txt` 两次扫描零敏感命中，其 3 处 64 位 HEX 自述为哈希锚点，本节点复算该件哈希并登记（见「投递件哈希锚点」） | 导出物可进入目标机安装态；`REP-03` 的缺权限负例复现须在同一账户内实际调用，不能由本行的扫描结论代替 |
| ENV-05 | 校验器版本与校验通道 | 只读列举 `%USERPROFILE%/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/5.6.2-wb.39298511.g37a65c0b.he233403f909a/scripts/` 目录内容，并与 `RIN-02` 回执声明的执行实体路径比对；另只读 `installed_plugins.json` 内 `@workbuddy-builtin` 各插件 `version` 与 `lastUpdated` | 校验通道存在且是本机 cache 副本：目录内 `validate_expert.py`/`register_expert.py`/`package_expert.py`/`init_expert.py`/`batch_create.py` 在场，版本目录名 `5.6.2-wb.39298511.g37a65c0b.he233403f909a` 与 `RIN-02` 回执的实测值逐字一致；宿主插件套件现值同为该版本（`lastUpdated` 2026-10-01T13:31），CR1 记录的历史校验器值 `5.5.6-wb.38337834.g5f969292.h7826dc9400fd` 只作参考点 | `index.md#RunWindow` 的「校验器版本」现值取 `RIN-02` 实测回执值而非 `待确认`；该值由 `cmd-04` 与 `RIN` 行的 `校验器=` 字段绑定核对（无 `通过` 回执时不得预填，有回执时不得滞留在 `待确认`）；本行同时取代上一轮「本机无 `expert-manager` 通道」的结论——通道是 builtin cache 副本内的脚本，`which expert-manager` 探测不到它，不构成自制校验器 |
| ENV-06 | 目标机身份与 G4 目标机条件 | 读本机 `$COMPUTERNAME`、WorkBuddy 安装目录 `version` 文件，并与 round4 回执声明的执行环境逐字段比对（`主机名`/`客户端版本`/`OS`） | 主机名 `DESKTOP-OT18TRG`、WorkBuddy `37.10.3-24`，与 `RIN-02`/`RIN-04`/`RIN-05`/`RIN-06` 各回执自述的执行环境（`G4 目标机 DESKTOP-OT18TRG / Win10 19045`）同机同版本；round4 各链路步骤（同步、校验、注册、安装、新会话、复测）全部在该机上执行，且本节点就在同一台机上直接复现了注册表与安装件实测值 | 事实层结论：G4 链路在本机执行完毕，`RIN-02`/`RIN-04`/`RIN-05` 的实测值不依赖转述。「G4 目标机」的**书面指定**仍未在案（回执的自述出自采集会话，不出自 Ray）；本节点按「同一主机名＋同一客户端版本＋链路实物均在本机可复算」登记该身份，不把它写成 Ray 的书面指定，也不因此放行任何缺口 |
| ENV-07 | 四连接器 `enabled` 态的持久性（非持久动态前提） | 只读连接器状态文件 `%USERPROFILE%/.workbuddy/connectors/{workspace-id}/connector-states.json`（`version 4`，mtime `2026-10-04T03:14:45+08:00`）与同目录 `.credentials.v3.json` 的 mtime（`02:15:51`，未读取任何值） | 六条全部 `enabled:false`（`wind-finance`/`tdx-connector`/`neodata`/`westock-mcp` 四个声明项连同 `teacher-assistant`/`tushare`），`bound` 均为 `true`；即 `REP-02` 复测时（02:16~02:22 回执记 connected 态）的挂载没有跨过该时刻，凭据文件 mtime 与 GUI 重连时刻吻合 | `RIN-06` 与 `REP-02` 的可复现性依赖「GUI 重连」这一非持久动态前提：任何后续复跑须先只读确认 `enabled` 现值，不能假设上一次的连接态仍在；重连路径见 `RIN-06` 可重授权路径。本行也是 `RIN-06` 现值判 `阻塞` 的直接依据 |
| ENV-08 | 缺权限负例的拒绝前提是否仍可建立 | 只读转录 round4 复测回执的同参数重发结果（本节点未发起任何真实请求、未做授权注入、未读取凭据值），并与 `safety-branches.md#负例核验记录对象` 的 `NZ-01..04` 原始拒绝原文比对 | 前提均已消失或不可达：`NZ-01`（tushare `cyq_perf` 40203 接口级权限拒绝）——tushare 已按收敛设计断开，复测会话的 258 项工具候选面无 `mcp__tushare__*`；`NZ-02..04`（wind 账户积分不足连拒）——`AAPL.O`/`000001.SZ` 原参数重发（02:22:09.421/.423/.426）全部返回成功数据，账户积分已恢复且恢复非本会话任何操作所致；受控构造方式（`auth` 覆盖注入无效凭据）经 `safety-branches.md#登记口径` 第 4 条实测未复现拒绝（服务端缓存命中，凭据未被实际校验） | `REP-03` 保持 `否`/`阻塞`，重授权路径＝Ray 提供对该接口无权限或积分实际耗尽的真实账户（或该接口停机窗口）后在收敛新会话内按原参数重放并原文留证；不得以 `tool-not-mounted` 或空结果代替 `permission-denied`，不得为凑复现而消耗共享账户积分或改写 `NZ-*` 既有成立证据的地位 |

## 重装后复现

| ID | 复现项 | 结果 | 证据引用 | 是否可复现 |
|---|---|---|---|---|
| REP-01 | 九项路由（命令→唯一技能，九项映射 MR-01..09） | 通过（装后新会话实际召唤） | 会话 B（`8f4e6e95`，01:05~01:14）经 Agent 工具召唤子代理 `equity-research`（解析到 `equity-research@my-experts:agents`，即安装件 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`），九个请求逐项判定 8 Route / 1 Clarify / 0 Stop；唯一非 Route 项是 `model-update`（该技能输入契约要求「来源与口径缺任一项先追问」，属契约行为），`Stop` 未触发是因请求集无 no-authorization / data-stale / missing-prerequisite-model / us-equity 场景（原因如实登记，不写成已触发）。复现基准＝`README.md#2.1` 的九项映射与 `agents/equity-research.md#九项路由（恰九项）`，源侧九项未因升版漂移由 `cmd-03` 的 `test_agent_existing_routes_and_guards_untouched` 与 `cmd-04` 的 `test_manifest_version_and_fields`（`skills` 恰 9）双向机检；原件 `round4/rin07-rep-receipt.md` §1 | 是 |
| REP-02 | 已授权域真实查询（七域采用行） | 通过（12 条复核路径原样重发，11 项成功且与原始一致） | 复测窗口 `2026-10-04T02:19:59.013~02:22:11.800+08:00`（逐条毫秒时间戳与 callId 配对提取方法见原件 §4），基准＝`queries.md#查询溯源` 的 `QRY-01`～`QRY-09` 与 `queries.md#单指标单源` 采用裁决、`safety-branches.md` 的 `SBC-07`/`SBC-08` 记录对象，按各行 `复核路径` 在同一授权账户原参数重发：`VR-01` ROE/营收/净利 1 行 × 3 指标同构、`VR-02` 一致预期 8 条同构同值、`VR-03` 评级月度与盈利预测字段集一致、`VR-04`/`VR-05` 空结果与原始一致、`VR-06` 首发瞬时限频（`error_type=2`）重试成功后 10 根日 K 同窗口、`VR-07` `totalStocks` 825=825、`VR-08` 四个 EDB 指标代码逐字一致、`VR-09` 3 个交易日期间一致、`SBC-07-NC` 不存在代码→空成功、`SBC-07-AT` 2 实体歧义须澄清、`SBC-08-HQ` 首发参数名偏差（`codes` vs `stock_codes`）后按原始参数修正重发并逐字段一致；零 `tool-not-mounted`。会话语境如实登记：执行于会话 A（安装前既有的采集会话），非装后新会话 ⇒ 该项的容器条件由 `RIN-06` 单独判 `阻塞`，本行只判定数据面在装后确实返回真实数据；原件 `round4/rep02-retest-receipt.md` | 是 |
| REP-03 | 缺权限负例 | 阻塞（装后不可复现：拒绝前提已消失或不可达） | 复现基准＝`safety-branches.md#负例核验记录对象` 的 `NZ-01`～`NZ-04` 与 `#安全分支实测记录对象` 的 `SBC-07-NC`；本轮逐项实况（`ENV-08`）：`NZ-01` 因 tushare 按收敛断开而工具面在场性缺失、`NZ-02..04` 因 wind 账户积分恢复而同参返回成功数据；`round4/rin07-rep-receipt.md` §3 的会话 B 侧同样无 `permission-denied` 可留证（12/12 停在挂载前）。`round2` 的 `NZ-01..04` 拒绝原文（2026-10-03 17:41~17:43 实测、canonical 哈希在案）仍是「缺权限负例行为」的既有成立证据，既不被本轮推翻、也不被本轮复现，本行不把它折算成装后复现；构造禁止项见 `safety-branches.md#登记口径` 第 4 条与 §4.6。重授权路径见 `RIN-07` | 否 |

## 登记口径（G4 节点裁定）

1. **未达成一律记 `阻塞`，不记 `不适用（无数据）`，也不折算成 `通过`**：`RIN-06`/`RIN-07` 的缺口与 `REP-03=否`
   由 `cmd-04` 与 `RIN` 前言声明同值断言，使「校验与安装已通过」不能被读成「重装链路全绿」；TASK-04 因此未签完成。
   `阻塞` 行的 `证据引用` 以 `不适用（未执行` 起首是 `cmd-04` 的封闭措辞合同（缺口行的引用面判据），其含义在本表按本轮实况读作
   「该阶段条件对应的可采信执行未发生」——`RIN-06`/`RIN-07` 确有观察与尝试，未成立的是阶段条件，不是「没动手」，此处不留歧义。
2. **`客户端=` 与 `包=` 是机器字段**：`cmd-04` 从每行 `RIN` 抽 `包=<v>` 与 `plugin.json#version` 双向核对，抽 `客户端=<v>` 与
   `index.md#RunWindow` 的「客户端版本」现值核对（`未参与` 表示该阶段不经客户端），使版本行不能被写成任意文案。
   `校验器=` 同样是绑定字段：`index.md#RunWindow` 的「校验器版本」必须等于某条 `通过` `RIN` 行的实测值，无 `通过` 行时保持 `待确认`（见 `ENV-05`）。
3. **投递件路径一律写包内相对路径**：round3/round4 投递件所在的本机绝对路径不进入本文件；`cmd-04` 与 `cmd-03` 同口径做私有绝对路径扫描。
   本机的用户级目录只以 `%USERPROFILE%` 形态出现，不带盘符与用户名。
4. **`my-experts` 市场目录不是源目录**：`%USERPROFILE%/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research`
   是 §4.6 末行所说的安装位置形态；`RIN-02` 把导出物同步进该目录是目标校验的前置（校验器只接受专家目录内路径），
   本节点不把它当源目录，也不把它的存在当市场或安装证明——安装证据只取 `installed_plugins.json` 与安装件哈希。
5. **round4 的三层登记口径（G4 节点裁定）**：(a) 本节点在同一台目标机上直接只读实测的事实（注册表现值、四处 `plugin.json`
   同值哈希、cache 目录形态、安装件/导出物差集、连接器状态文件现值、校验器副本在场、主机名与客户端版本）＝仓外可重算、
   本文件写实测值；(b) 采集会话的一次性动作（`23:45` 校验与注册 EXIT、`00:37:46` 客户端写入、`01:19~02:22` 逐条请求与毫秒时间戳）
   ＝逐字转录并以投递件文件级 SHA-256 锚定，本节点无法事后重算，因此这些行的证据引用同时给出「原件名＋本节点可复算的对应物」；
   (c) 判定权在本节点：round4 状态矩阵自述的 `RIN-06=⚠️ 部分`、`REP-03=交 dev-agent 裁决` 两条，按 (a) 的现值分别判 `阻塞` 与 `否`，
   不采用投递件的自述汇总当作结论，也不为迎合汇总而改写实测行。
6. **缺口不刷绿的边界（交评审面板复核）**：AC-08 要求「缺权限负例在重装后可复现」，而该负例的前提（无权限/无积分的真实账户态）
   只能由 Ray 侧建立；注入无效凭据的受控构造方式已实测不复现拒绝。因此本节点保持 `REP-03=否` 与 `RIN-07=阻塞`，
   不改写 `cmd-04` 的复现断言、不缩小 AC、不把 `round2` 既有证据折算成本轮装后复现（plan 风险与回滚 4「任何动态前提不足
   不以缩小 AC、跳过测试或宣布通过来替代」）。`cmd-04` 相应保持 1 项红（`test_install_and_summon_receipt_for_final_package`）。
7. **`entry` 名不符的归属**：`safety-branches.md` 转给 G4 的 tdx entry 名不符事实，其不符对象不在本 CR 包内声明条目（源清单、导出物与
   `agents/equity-research.md` 全文均无该串，见 `DCL-02`），故按 §4.7 登记而不修正，不改 `plugins/**`。

## 导出与安装态实测

```json
{
  "说明": "本节点实跑值；由 cmd-04 现重跑比对，不含任何本机私有绝对路径（用户级目录一律 %USERPROFILE% 形态）",
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
    "marketplace_2.1.0_manifest_sha256": "b8c153c80b08d32c5af99bcba64fc1347e56cf67342527a4a8cd3e7538743d2b",
    "note_superseded": "以上 4 个键是 2026-10-03 只读实测的历史现值，保留作 cmd-04 排除修正前包回执的对比对象；0.10.0 安装目录与 2.1.0 注册条目已被本轮取代，实况见 0.11.0 实测块"
  },
  "0.11.0 最终包实测": {
    "采集时刻": "2026-10-04T03:1x+08:00（本节点只读复算）",
    "manifest_sha256_四处一致": "f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55",
    "四处": ["仓内 .codebuddy-plugin/plugin.json", "out/ 导出物", "marketplaces/my-experts/plugins/equity-research", "cache/my-experts/equity-research/0.11.0"],
    "注册条目": {
      "key": "equity-research@my-experts",
      "version": "0.11.0",
      "installPath_tail": "cache/my-experts/equity-research/0.11.0",
      "installedAt": "2026-09-29T06:54:07.733Z",
      "lastUpdated": "2026-10-03T16:37:46.455Z",
      "installed_plugins_json_mtime": "2026-10-04T00:37:46.456+08:00",
      "equity_entries_now": 1
    },
    "安装件与导出物差集": [".in_use/17264", ".in_use/20880", ".in_use/21076", ".in_use/26076"],
    "安装件文件数": 28,
    "市场清单": {"path_tail": "marketplaces/my-experts/.codebuddy-plugin/marketplace.json", "条目数": 1, "source": "./plugins/equity-research", "mtime": "2026-10-04T00:23:06+08:00"},
    "校验器副本在场": "%USERPROFILE%/.workbuddy/plugins/cache/workbuddy-builtin/skill-expert-manager/5.6.2-wb.39298511.g37a65c0b.he233403f909a/scripts/",
    "旧包隔离与备份": {
      "orphaned_at": 1791045466458,
      "cache_versions_now": ["0.11.0"],
      "backup_dir_tail": "plugins/backup-my-experts-equity-research-0.10.0-20261003-234359",
      "backup_files": 24,
      "backup_manifest_sha256": "2f7ef4ce4f2c7d869995d93585b04fd506936e1d9943779338d82ff327b0c5ab"
    },
    "连接器状态现值": {
      "file_mtime": "2026-10-04T03:14:45+08:00",
      "version": 4,
      "enabled_false": ["teacher-assistant", "tdx-connector", "westock-mcp", "tushare", "neodata", "wind-finance"],
      "bound_true_all": true,
      "credentials_file_mtime": "2026-10-04T02:15:51+08:00",
      "credentials_content_read": false
    },
    "目标机身份": {"主机名": "DESKTOP-OT18TRG", "客户端版本": "37.10.3-24", "回执自述": "G4 目标机 DESKTOP-OT18TRG / Win10 19045", "Ray 书面指定": "未在案"}
  }
}
```

## 投递件哈希锚点

`round3/` 与 `round4/` 投递件是本 TASK 目标机事实的输入件；下表为包内相对路径与本机实测 SHA-256（本节点 `sha256sum` 直跑复算，
round4 清单为 LF，`sha256sum -c SHA256SUMS.txt --strict` 9/9 OK、exit=0；round3 清单为 CRLF，按 `safety-branches.md#登记口径`
第 8 条的归一口径 `tr -d '\r' | sha256sum -c --strict -` 6/6 OK、exit=0）。

```json
{
  "说明": "包内相对路径与实测值；不含任何本机私有绝对路径",
  "round3/SHA256SUMS.txt": "dbb3d86b0efc5b0a30e5cfdd9045ce6803290dcc3774bff328635367de418602",
  "round3/task04-target-machine.md": "fc47f7ce5eace5721c4cb8662440f5e67fc78c144c66cf4face759a58d2dd3a6",
  "round3/verify-records.json": "e9b0271ace9f4679ada8a5216b5174ee47a72a8806bf8a8fff343425b9f25536",
  "round3/verify-records.sha256.json": "d40eb0fb3558e834277d4ad413d994f8803ccca1a93981034e842dfd80732c15",
  "round3/sensitive-selfcheck.txt": "473f46823104689929b6cecd0582102ba444fb8d3fed797aa42a402ae6b4e2a4",
  "round4/SHA256SUMS.txt": "5017b82993a753136fb5752f3b7bb5b1d66586de45b36087b9a94a597a9a71b5",
  "round4/README.md": "030ad69c0a2f455316558fc9a440c3e6de622019c92fb0cceccfb28fbb4896e5",
  "round4/rin02-receipt.md": "383e213140cef4fb992b2ecaff2e1f626df427414dc2ed39d151a0c792e4dda7",
  "round4/rin0405-install-receipt.md": "6f4680b675a28b8f97ccf00da07e00e667c4efd64b553fa7b3c28b23697746cb",
  "round4/rin0407-stage-b-card.md": "370f342dea13e1c9c74a1b78975124162c2fcf29c18d71596d953c66dc852259",
  "round4/rin06-session-tool-surface.md": "f53e03952a872a2e79e694db0e4481f4a58e440c4027962152b7e9097d612eb9",
  "round4/rin07-rep-receipt.md": "839c589645e50a508348fdd6c0e2bd017dca8a7e37fb7f4e703749a252c173b4",
  "round4/rep02-retest-receipt.md": "c6fce21dba602456b309be9114073115f60576c6726899736c76371107e9b102",
  "round4/sensitive-selfcheck.txt": "b0036c833e1a3e1440b258de91a3093b46d29e0506746822910377767075f12a",
  "round4/dist/equity-research.zip": "e7c215f141f1c322d5fbd201465846ef0501fdc70acc0672494a7daf84c6b50d"
}
```

`round4/dist/equity-research.zip` 是采集会话用同一 cache 副本的 `package_expert.py` 产出的 0.11.0 打包件（24 files / 431.7KB），
本节点登记其哈希只作「官方打包通道确实产出 0.11.0」的旁证；安装链路实际走的是市场源目录同步（`RIN-02`），
不以该 zip 代替安装件哈希，也不把它当第二套导出结论。
