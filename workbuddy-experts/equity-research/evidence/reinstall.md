# CR-2026-002 数据与授权 — 重装链路与复现（G4）

三张固定表：`重装步骤`（`RIN-NN`）、`环境依赖排查`（`ENV-NN`）、`重装后复现`（`REP-NN`）。
列名、列序与 ID 前缀取 `tests/_evidence.py#TABLE_COLUMNS`（CR-2026-002-TASK-01 §6）注册值，本文件不另立第二套定义。
`run-id` 沿用 `index.md#RunWindow` 的 `CR-2026-002-20261003`（跨日延伸口径见「登记口径」第 8 条）。

链路结论（由 `cmd-04` 机械断言，不得漂移）：**实际通过 4 行**（`RIN-01` 导出、`RIN-02` 目标校验/注册、
`RIN-04` 卸旧隔离、`RIN-05` 安装最终包）、**未执行缺口 2 行**（`RIN-06` 新会话仅保留包声明依赖、
`RIN-07` 逐项复现的容器会话），另有 1 行 `不适用（无条件性修正）`（`RIN-03`，目标校验实测 0 error ⇒ 无不符项可修正）。
`REP-01`/`REP-02`/`REP-03` = `是`。`REP-03` 由本轮（第二次派发）改判：0.11.0 安装（`2026-10-04T00:37:46.455+08:00`）之后，
采集会话用同一连接器同一工具 `mcp__tushare__cyq_perf` 实际调用得到服务端接口级权限拒绝原文 `40203`，属 `permission-denied`
本体而非 `tool-not-mounted` 冒充；判据、两处偏差与证据层级见 `REP-03` 行与「登记口径」第 9 条，改判不改变 `cmd-04` 的红。
0.11.0 已由目标机 WorkBuddy 客户端校验（`validate_expert.py` EXIT=0）并原生安装（注册条目 `version=0.11.0`）。
唯一剩余缺口是 `RIN-06` 的动态前提：重管（`14:35`）之后没有任何可登记的新客户端会话面（`ENV-10`），而本节点的 run 会话
属另一通道、不能替代它（`ENV-09`）；连接器的持久 `enabled` 态在本 run 期间又被写回全断（`ENV-11`）。
按 §4.6「失败保持域阻塞并给重授权路径」保持阻塞，不缩小 AC、不改写 `cmd-04` 的复现断言（plan 风险与回滚 4），
也不以节点自身会话面或状态文件现值冒充客户端工具面。因此 TASK-04 未签 `done`，`crctl task done` 未调用。

## 重装步骤

| ID | 阶段 | 实际步骤 | 客户端/校验器/包版本 | 结果 | 证据引用 |
|---|---|---|---|---|---|
| RIN-01 | 导出（两次一致） | 2026-10-03 在本机仓根实跑 `python scripts/export_workbuddy_experts.py` 两次：两次 exit=0，单次耗时 0.134s / 0.133s（预算 120s 内），导出 24 件，两次相对路径与逐文件 SHA-256 集合全等；`evidence/` 未进入导出物 | 客户端=未参与 校验器=未参与 包=0.11.0 | 通过 | 本文件「导出与安装态实测」机器块 `导出两次一致`（`digest_set_sha256=b29844659c145f1609970e6915c2cd0db8bef21aabf1574bf577c843226080c9`、`files=24`、`identical=true`），由 `cmd-04` 现重跑两次并与本值比对；`plugin.json#version` 实测值见同块 `manifest_version` |
| RIN-02 | 目标校验（注册） | 2026-10-04 目标机 A 段：先把 `out/workbuddy-experts/equity-research`（0.11.0，24 件）同步进用户级市场源 `%USERPROFILE%/.workbuddy/plugins/marketplaces/my-experts/plugins/equity-research`（`diff -rq` 0 行、替换后 24 件，回退点备份 24 件在场），再以客户端自带 expert-manager cache 副本 `5.6.2-wb.39298511.g37a65c0b.he233403f909a/scripts/validate_expert.py` 执行安装前目标校验：`23:45:25~23:45:26+08:00` EXIT=0、输出 `✅ Expert package is valid!`、仅 1 条非阻塞警告（`displayDescription.zh` 100 chars，建议 40-50）；随后 `register_expert.py` 注册 `23:45:27+08:00` EXIT=0（新增分支）与 `23:52:07~08+08:00` EXIT=0（幂等重跑走更新分支，条目数 BEFORE=1 / AFTER=1），终态 `marketplace.json` 为单条目 `source=./plugins/equity-research`（清单本身无版本字段，版本号取自源目录 `plugin.json`）。前提事实：校验必须在同步之后、对专家目录内路径执行；对目录外路径校验器直接 EXIT=1（`专家不在专家目录下`），属路径性拒绝而非包内容拒绝 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 被校验对象实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`（本节点在仓内源清单、`out/` 导出物、市场源目录、安装件四处分别复算，三处目录内同值，见「导出与安装态实测」机器块）；注册条目终态实测（`installed_plugins.json` 由客户端在 `RIN-05` 安装时写入，A 段未触碰该文件）：`installedAt=2026-09-29T06:54:07.733Z`、`lastUpdated=2026-10-03T16:37:46.455Z`、`version=0.11.0`、`installPath` 指向 `cache/my-experts/equity-research/0.11.0`；执行侧原件 `round4/rin02-receipt.md`（哈希见「投递件哈希锚点」）；校验器 cache 副本目录与 `validate_expert.py`/`register_expert.py`/`package_expert.py` 在场由本节点只读复现（`ENV-05`） |
| RIN-03 | 条件性修正 | 未发生：`RIN-02` 的 0.11.0 目标校验实测 0 error（唯一警告是 `displayDescription.zh` 长度建议，属非阻塞），`dependencies.connectors` 的四标识被目标版本按现写法识别，声明条目未被指出不符 ⇒ 未改 `dependencies.connectors`、未改 `EXPECTED_CONNECTORS`、未改 `agents/equity-research.md` 声明条目，三处零差异；本轮不再依赖「未执行校验故无不符项」的前一版依据，改判依据是 0.11.0 的校验回执本身（见 `DCL-01` 结论与 `DCL-02`） | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 不适用（无条件性修正） | `DCL-01`、`DCL-02`（两行结论均为 `无需修正`）；三处零差异由 `cmd-04` 现算比对 `scripts/export_workbuddy_experts.py` 的 `ALLOWED_PKG_FILES`/`EXPECTED_CONNECTORS` 与 `plugin.json`；警告原文与 0 error 结论在 `round4/rin02-receipt.md` A2 段 |
| RIN-04 | 卸下或隔离旧包 | 走「隔离」形态且为客户端原生写入：安装 0.11.0 时客户端于升级同秒对旧 0.10.0 cache 目录写孤儿标记 `.orphaned_at`=1791045466458（= `2026-10-03T16:37:46.458Z`，本地 `00:37:46.458+08:00`），注册条目 `installPath` 改指 0.11.0，0.10.0 脱离激活路径；旧目录内 `.in_use/6560` 为 2026-09-29 旧进程残留锁（procStart `2026-09-29T06:42:07Z`），非当前引用。其后应用户明确指令删除该孤儿目录（删除前置条件：备份 `%USERPROFILE%/.workbuddy/plugins/backup-my-experts-equity-research-0.10.0-20261003-234359` 24 件校验通过、隔离证据已先录入回执）；本节点只读复现：`cache/my-experts/equity-research/` 下现仅 `0.11.0`，备份目录在场且其 `plugin.json` 复算值与登记的前版本安装件哈希同值 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 激活安装件实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`、注册条目 `installedAt=2026-09-29T06:54:07.733Z`／`lastUpdated=2026-10-03T16:37:46.455Z`（本节点直读 `%USERPROFILE%/.workbuddy/plugins/installed_plugins.json` 复算，`equity-research@my-experts` 单条目）；`.orphaned_at` 与删除前后核验在 `round4/rin0405-install-receipt.md`（含「后续清理」注记），其哈希见「投递件哈希锚点」；前版本 manifest 哈希只作差集对比与备份忠实性核对用（机器块 `安装态对照`），本行不以它充当完成标志 |
| RIN-05 | 安装最终包 | 客户端原生安装，无手写注册项：用户在 GUI 重启客户端后触发，安装动作时刻 `2026-10-04T00:37:46.455+08:00`（注册表 `lastUpdated` 原值 `2026-10-03T16:37:46.455Z`）；`installed_plugins.json` 由客户端写入（mtime `2026-10-04T00:37:46.456+08:00`）`equity-research@my-experts` 条目 `version=0.11.0`、`installPath=…\cache\my-experts\equity-research\0.11.0`；cache 目录 mtime `00:37:46.452~48+08:00` 与 `lastUpdated` 同秒；0.11.0 持有当前 `.in_use` 进程锁。本节点 2026-10-04 03:1x 只读复算：安装件 `plugin.json` 与 `out/` 导出物、市场源目录三处 SHA-256 全等于 `f25b4a20…`，条目 `version` 与 `plugin.json#version` 双向一致 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 通过 | 安装件实测 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`（本节点复算）／`installedAt=2026-09-29T06:54:07.733Z`（客户端字段语义＝首次安装时刻，升级保留；本次升级时刻取 `lastUpdated`）；安装件文件集与导出物的差集判据见 `ENV-03`（本节点实测差集仅 4 个 `.in_use` 宿主运行标记）；被安装包内含 TASK-03 新增节由 `cmd-04` 的 `test_agent_declaration_section_ships_in_package` 对导出物断言（安装件与导出物逐文件同哈希，故该断言传递到安装件）；原件 `round4/rin0405-install-receipt.md` |
| RIN-06 | 新会话（仅保留包声明依赖） | 阶段条件仍未达成，本轮把「为什么节点不能自证」写成实测事实，三条：(1) **通道事实**——本节点 run 会话不是客户端连接器通道（`ENV-09`）：本 run 是 Multica dev-agent 的 Qoder 会话（同机 `DESKTOP-OT18TRG`），`%USERPROFILE%/.qoder/mcp.json` 为 `{"mcpServers": {}}`，PATH 上 `codebuddy` CLI 的 `%USERPROFILE%/.codebuddy/mcp.json` 只配 `plugin_context-mode_context-mode`，本会话面四声明连接器 0/4 挂载、`agent-mail` 等捆绑 MCP 亦不在面 ⇒ 既不是「仅保留声明依赖」的收敛面，也不是客户端挂载事实，不能充当台账要求的「新开会话并登记该会话的实际工具面」。(2) **重管后无新会话**——Ray 的 `14:36` 四声明项挂载观测属于会话 `1d95c0ef`，本节点只读实测该会话首启 `2026-10-04T12:21:31+08:00`、`14:24:58` 与 `14:36:25` 各有一次进程心跳续写，早于 `14:35:01` 的重管写入，与 Ray 自述「观测来自重管前旧会话」一致；采集时点（`15:0x`）`sessions/` 内仍无重管后新开的会话（`ENV-10`）。(3) **持久态回落**——连接器状态文件在本 run 期间被客户端于 `2026-10-04T15:02:45+08:00` 再次写为六条 `enabled:false`／`userDisabled:true`（四声明项连同 `teacher-assistant`/`tushare`），即 `ENV-07` 记录过的回落现象重现（`ENV-11`）。上一轮已成立的事实不变：会话 B 的召唤入口解析到 0.11.0、官方 2.1.0 的 7 个独有技能不在面。`agent-mail` 的内置不可断**书面确认已到位**（三条依据在案：不在市场清单、不在 61 个已装插件与用户级 `mcp.json`、`GetMe` 返回 `status=not_bound`），台账按原文规定「按确认登记而不代为判定」入账；Ray 同时指出状态文件与工具面不同步、工具面为权威，故 `ENV-11` 只登记持久态现值、不据以判定挂载结果 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 阻塞（新会话仅保留包声明依赖未达成） | 不适用（未执行——「重管之后的新客户端会话面」至今没有可采信的观察对象：节点 run 会话属另一通道（`ENV-09`），客户端最后活跃会话 `1d95c0ef` 早于重管时刻（`ENV-10`））。可重授权路径＝Ray 在重管**之后新开一个客户端会话**（当前专家选「股票研究专家」= my-experts 0.11.0），在该会话内一次性登记三件：(i) 四声明连接器逐条 `mounted`/`tool-not-mounted`，每条附一次真实调用回执；(ii) 与采集**同帧**的连接器状态文件 `enabled` 现值（否则 `ENV-07`/`ENV-11` 的回落会第三次吞掉挂载证据）；(iii) 该会话面仍在场的全部未声明项清单与逐项可关性——`agent-mail` 已由其书面确认覆盖并按原文入账，`ifind-mcp`（Ray 回执内前后表述不一致，以新会话实测为准）与客户端内置捆绑 `sheetagent`/`genie-baas`/`weixinpay` 的归属需实测清点后再定是否属于「声明依赖之外必须断开」的对象。官方同名 `equity-research@experts 2.1.0` 的耐久停用仍为专家中心 GUI 卸载（`ENV-02`）。会话面原件 `round4/rin06-session-tool-surface.md`、恢复路径原件 `round4/rep02-retest-receipt.md` |
| RIN-07 | 逐项复现 | 三项复现的**数据面**本轮全部有装后实际执行结果：`REP-01` 九项路由在会话 B 内逐条实际召唤（8 Route / 1 项按技能输入契约追问）；`REP-02` 已授权域真实查询在 GUI 重连后按 12 条复核路径原样重发，11 项成功且与 round2/round3 原始记录同构或逐值一致；`REP-03` 缺权限负例在装后由真实账户态实际复现（`2026-10-04T14:24+08:00`，服务端 `40203` 原文，见 `REP-03` 行与「本轮采集回执转录」）。本行仍不成立的原因是**容器**：§4.6 的链路把「逐项复现」排在「新会话仅保留包声明依赖」之后，而该收敛会话至今没有观察对象（`RIN-06`/`ENV-09`/`ENV-10`），三项复现分别落在会话 B、会话 A 与重管前的会话 `1d95c0ef`。本行不引用任何静态文件比对作为复现证据 | 客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0 | 阻塞（收敛新会话未成立，复现容器缺位） | 不适用（未执行——链路第 6 步的会话面未成立，第 7 步虽已逐项实际执行但不占该容器；撤销上一轮自设的「`NZ-01` 须在收敛会话内重放」约束后，本行阻塞理由只剩容器一项，理由与判据见「登记口径」第 9 条）。可重授权路径＝与 `RIN-06` 同一条：Ray 新开一个重管后的客户端会话，在该会话内按 `RIN-06` 的 (i)(ii)(iii) 登记，并在同一会话内重放 `queries.md#查询溯源` 的 12 条复核路径与 `safety-branches.md#负例核验记录对象` 的 `SBC-07-NC`（`REP-03` 的 `NZ-01` 类拒绝已按 `REP-03` 行判定，不要求重复采集；若 Ray 愿意顺手用 `NZ-01` 原参数 `ts_code=603599.SH` 复取一次，可消除 `REP-03` 的参数偏差，它不是本行的前置条件）。执行侧原件 `round4/rin07-rep-receipt.md`（会话 B）与 `round4/rep02-retest-receipt.md`（会话 A 复测） |

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
| ENV-08 | 缺权限负例的拒绝前提是否仍可建立 | 只读转录 round4 复测回执的同参数重发结果（本节点未发起任何真实请求、未做授权注入、未读取凭据值），并与 `safety-branches.md#负例核验记录对象` 的 `NZ-01..04` 原始拒绝原文比对；本轮（第二次派发）再叠加对 Ray 回执原文与执行容器的心跳实测比对（`ENV-10`） | 结论分两层更新：`NZ-01`（tushare `cyq_perf` 40203 接口级权限拒绝）的前提**已在装后重新建立**——`2026-10-04T14:24+08:00` 由真实账户态实际调用得到服务端原文拒绝，判据见 `REP-03`；上一轮「因 tushare 按收敛断开而工具面在场性缺失」只对当时那几个会话成立，不构成该负例永久不可复现，故该判断由本轮实测取代。`NZ-02..04`（wind 账户积分不足连拒）前提仍已消失——`AAPL.O`/`000001.SZ` 原参数重发（02:22:09.421/.423/.426）全部返回成功数据，账户积分恢复非本会话任何操作所致；受控构造方式（`auth` 覆盖注入无效凭据）经 `safety-branches.md#登记口径` 第 4 条实测未复现拒绝（服务端缓存命中，凭据未被实际校验） | `REP-03` 的 `是` 只由 `NZ-01` 类真实拒绝支撑；不得以 `tool-not-mounted` 或空结果代替 `permission-denied`，不得为凑复现而消耗共享账户积分或改写 `NZ-*` 既有成立证据的地位。额度层 `NZ-02..04` 不是 `REP-03` 的判据对象（属 `SBC-01`/`SBC-09` 触发对象），如需重建其前提，路径是 Ray 提供积分实际耗尽的账户态或该接口停机窗口，而非构造 |
| ENV-09 | 节点 run 会话能否充当 `RIN-06` 要求的「新会话」 | 只读本 run 的会话身份与两条候选通道的配置（`%USERPROFILE%/.qoder/mcp.json`、PATH 上 `codebuddy` CLI 的 `%USERPROFILE%/.codebuddy/mcp.json`），并与本会话实际工具面中的 `mcp__*` 条目数比对 | 不能。本 run 是 Multica dev-agent 的 Qoder 会话（主机名 `DESKTOP-OT18TRG`，与 G4 目标机同机；task/slot 见「本轮通道与状态实测」机器块），`%USERPROFILE%/.qoder/mcp.json` 值为 `{"mcpServers": {}}`，`codebuddy` CLI 侧只配 `plugin_context-mode_context-mode`；两通道都没有四声明连接器的 server 条目，本会话面 `mcp__*` 工具数为 0——既无「仅声明依赖」的收敛语义，也无 `agent-mail`/捆绑 MCP 可作对照。`%USERPROFILE%/.workbuddy/mcp-tool-list.json`（mtime `2026-10-04T14:35:01+08:00`，14 个 server 条目，含一个 254 工具的 tushare 条目）是客户端 schema 缓存，其键不可由连接器名反推（本节点按名做 md5 映射 0 命中），缓存条目在场≠会话挂载，不能用作会话面判据 | `RIN-06` 的会话面观测只能来自客户端（WorkBuddy）新会话，「本 run 是新会话」不满足台账字面，节点无自证通道；同时排除两种误读——把「节点会话无连接器」读成「客户端面未挂载」，或把 schema 缓存当作工具面。重授权路径见 `RIN-06` 行 |
| ENV-10 | 14:24 回执与 14:36 观测的执行容器，以及重管后是否已有新会话 | 只读列举 `%USERPROFILE%/.workbuddy/sessions/*.json` 的 `sessionId`/`pid`/`startedAt`/`updatedAt` 与文件 mtime，按 Ray 自述的三个时刻（`14:24` 调用、`14:35:01` 状态文件写入、`14:36` 观测）逐一对齐 | 三个时刻都落在同一会话 `1d95c0ef-…`：首启 `2026-10-04T12:21:31+08:00`，`14:04:18`、`14:24:58`、`14:36:25` 各有进程心跳续写，且 `14:24` 时段客户端唯一有心跳的会话就是它；`12:20` 前最后写入心跳的会话属 `f09480ee`（round2/round3 采集会话）。本节点采集时点（`2026-10-04T15:0x+08:00`）`sessions/` 内没有晚于 `14:35:01` 新开的会话 | 两点直接影响本轮判定：(1) 14:36 的挂载观测属重管**前**的会话，与 Ray 自述一致，不能登记为重管后的新会话面，故 `RIN-06` 仍开不了；(2) `REP-03` 的 14:24 回执有节点实测可识别的执行容器，不是无主转述 |
| ENV-11 | 重管后连接器的持久 `enabled` 态是否留住四声明项 | 只读 `%USERPROFILE%/.workbuddy/connectors/{accountIdentityKey}/connector-states.json` 与同目录 `.v3.json`（实测 mtime `2026-10-04T15:02:45+08:00`；只取 `enabled`/`userDisabled`/`bound` 标志，`headerOverrides` 密文与凭据文件内容一律未读取） | 六条全部 `enabled:false` 且 `userDisabled:true`（`wind-finance`/`tdx-connector`/`neodata`/`westock-mcp` 四个声明项连同 `teacher-assistant`/`tushare`），`enabled` 列表为空、`bound` 均为 `true`；即本 run 期间客户端又一次把持久态写回「全断」，与 `ENV-07`（`03:14:45` 现值）同形。`ifind-mcp` 不在 `connectors` 映射内、只出现在 `headerOverrides`，与「connector-states 无其条目」的观测一致 | 本行只登记持久态现值，不据以判定会话挂载（Ray 指出状态文件与工具面不同步、工具面为权威）。它给 `RIN-06` 的重授权路径加一条采集要求：新会话的工具面观测必须**同帧**附状态文件现值，否则「GUI 重连 → 新会话采集」之间的回落会第三次吞掉挂载证据（`ENV-07`） |

## 重装后复现

| ID | 复现项 | 结果 | 证据引用 | 是否可复现 |
|---|---|---|---|---|
| REP-01 | 九项路由（命令→唯一技能，九项映射 MR-01..09） | 通过（装后新会话实际召唤） | 会话 B（`8f4e6e95`，01:05~01:14）经 Agent 工具召唤子代理 `equity-research`（解析到 `equity-research@my-experts:agents`，即安装件 `sha256=f25b4a2053bd5fb1b345e47d9a6b36a21f1af5030a59d62bcd857b909c2d3a55`），九个请求逐项判定 8 Route / 1 Clarify / 0 Stop；唯一非 Route 项是 `model-update`（该技能输入契约要求「来源与口径缺任一项先追问」，属契约行为），`Stop` 未触发是因请求集无 no-authorization / data-stale / missing-prerequisite-model / us-equity 场景（原因如实登记，不写成已触发）。复现基准＝`README.md#2.1` 的九项映射与 `agents/equity-research.md#九项路由（恰九项）`，源侧九项未因升版漂移由 `cmd-03` 的 `test_agent_existing_routes_and_guards_untouched` 与 `cmd-04` 的 `test_manifest_version_and_fields`（`skills` 恰 9）双向机检；原件 `round4/rin07-rep-receipt.md` §1 | 是 |
| REP-02 | 已授权域真实查询（七域采用行） | 通过（12 条复核路径原样重发，11 项成功且与原始一致） | 复测窗口 `2026-10-04T02:19:59.013~02:22:11.800+08:00`（逐条毫秒时间戳与 callId 配对提取方法见原件 §4），基准＝`queries.md#查询溯源` 的 `QRY-01`～`QRY-09` 与 `queries.md#单指标单源` 采用裁决、`safety-branches.md` 的 `SBC-07`/`SBC-08` 记录对象，按各行 `复核路径` 在同一授权账户原参数重发：`VR-01` ROE/营收/净利 1 行 × 3 指标同构、`VR-02` 一致预期 8 条同构同值、`VR-03` 评级月度与盈利预测字段集一致、`VR-04`/`VR-05` 空结果与原始一致、`VR-06` 首发瞬时限频（`error_type=2`）重试成功后 10 根日 K 同窗口、`VR-07` `totalStocks` 825=825、`VR-08` 四个 EDB 指标代码逐字一致、`VR-09` 3 个交易日期间一致、`SBC-07-NC` 不存在代码→空成功、`SBC-07-AT` 2 实体歧义须澄清、`SBC-08-HQ` 首发参数名偏差（`codes` vs `stock_codes`）后按原始参数修正重发并逐字段一致；零 `tool-not-mounted`。会话语境如实登记：执行于会话 A（安装前既有的采集会话），非装后新会话 ⇒ 该项的容器条件由 `RIN-06` 单独判 `阻塞`，本行只判定数据面在装后确实返回真实数据；原件 `round4/rep02-retest-receipt.md` | 是 |
| REP-03 | 缺权限负例 | 通过（装后真实账户态实际复现，节点按转录＋实测容器登记） | 判据对象＝`SBC-02`（权限拒绝）的触发记录 `NZ-01`：tushare 连接器对 `cyq_perf` 接口的服务端原生权限拒绝。本轮实况：安装时刻 `2026-10-04T00:37:46.455+08:00` 之后，采集会话于 `2026-10-04T14:24+08:00` 用同一连接器账户对同一工具 `mcp__tushare__cyq_perf` 实际调用，返回原文「tushare API 错误 [40203]: 抱歉，您没有接口(cyq_perf)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108」，与 `NZ-01` 原文逐字同构，是 `permission-denied` 本体、不是 `tool-not-mounted` 冒充（`ENV-08` 里「不可达」的旧结论由本轮真实回执取代）。两处偏差按「登记口径」第 9 条如实登记、不消除：参数 `ts_code=600519.SH` 与 `NZ-01` 的 `603599.SH` 不同而拒绝原文一致 ⇒ 拒绝属接口权限层；证据形态是平台评论原文转录（评论 ID `01a105a8-a99e-7648-8021-ebd7ba01ab65`，`2026-10-04T06:45:01Z`），无投递件文件级 SHA，层级低于 round4 各件，但执行容器由本节点实测可识别——`14:24` 时段客户端唯一有心跳的会话是 `1d95c0ef`（`ENV-10`），转录文本哈希见「本轮采集回执转录」机器块。归属更正与台账现值一致、无需改写：`SBC-02`/`NZ-01`/`ENV-08` 本就把 `cyq_perf` 记为 tushare。`NZ-02..04` 是账户额度层拒绝（`SBC-01`/`SBC-09` 的触发对象），不是本行判据对象，其前提现状仍按 `ENV-08` 登记（积分已恢复、同参返回成功数据，不得为凑复现消耗共享账户积分或注入无效凭据）。本行结论不改变 `cmd-04` 的红：该断言先由 `RIN-06` 失败，`REP` 分支未参与判定 | 是 |

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
   只能由 Ray 侧建立；注入无效凭据的受控构造方式已实测不复现拒绝。因此本节点**上一轮**保持 `REP-03=否` 与 `RIN-07=阻塞`，
   不改写 `cmd-04` 的复现断言、不缩小 AC、不把 `round2` 既有证据折算成本轮装后复现（plan 风险与回滚 4「任何动态前提不足
   不以缩小 AC、跳过测试或宣布通过来替代」）。该边界本轮不变，但事实变了：Ray 提供的是**装后新产生的真实服务端拒绝**，
   不是把既有证据折算复用，故 `REP-03` 按 `REP-03` 行与第 9 条改判；`RIN-06` 的会话面前提未因回执而满足，
   `cmd-04` 相应保持 1 项红（`test_install_and_summon_receipt_for_final_package`）。
7. **`entry` 名不符的归属**：`safety-branches.md` 转给 G4 的 tdx entry 名不符事实，其不符对象不在本 CR 包内声明条目（源清单、导出物与
   `agents/equity-research.md` 全文均无该串，见 `DCL-02`），故按 §4.7 登记而不修正，不改 `plugins/**`。
8. **节点 run 会话不等于客户端新会话（本轮新增，纠正上一轮的表述）**：上一轮 `RIN-06` 的可重授权路径要求「新开会话并登记该会话的
   实际工具面」，其可执行主体只能是客户端（WorkBuddy）侧新开的会话。本节点的 run 会话属另一通道（`ENV-09`：Qoder 会话，
   `%USERPROFILE%/.qoder/mcp.json` 为空对象、`codebuddy` CLI 只配 `context-mode`，本会话面 `mcp__*` 工具数 0），
   因此「本次 run 也是新会话」不构成该阶段的观察对象；上一轮把会话 B（`8f4e6e95`）说成节点自身的 run 会话，属表述错误，
   本轮按 `ENV-10` 的会话心跳实测更正——会话 A/B 与 `1d95c0ef` 都是客户端采集会话。
9. **`REP-03` 的判据、两处偏差与容器约束的撤销（本轮裁定，判定权连同 `review-code`）**：(a) 判据按时点表达——
   §4.6/AC-08 原文是「缺权限负例在**重装后**可复现」，而非「在收敛会话内可复现」；上一轮 `RIN-07` 可重授权路径里
   「在 `RIN-06` 收敛后的新会话内按 `NZ-01..04` 原参数重放」是节点自设的容器约束，而 `NZ-01` 的源 tushare 不是包声明依赖
   （`SBC-02` 已登记该源层边界），收敛会话按定义不可能挂载它 ⇒ 该自设约束使路径不可满足，本轮撤销它，
   这不属于缩小 AC（AC 从未要求该容器）。(b) 判据对象按 `AC-08` 的第三项原文收窄回其本义：`REP-03` 的复现项是**缺权限**负例
   ＝`SBC-02`/`NZ-01`；`NZ-02..04` 是账户额度层拒绝（`SBC-01`/`SBC-09` 触发对象），本轮仍不可建立且禁止构造，
   但不作为 `REP-03` 的判据对象——这一收窄是把判据对齐 AC 原文的第三项，不改变任何 `SBC-*` 行的既有成立地位。
   (c) 两处偏差不消除、如实写入 `REP-03` 行：参数 `ts_code=600519.SH` ≠ `NZ-01` 的 `603599.SH`（拒绝原文逐字一致 ⇒
   拒绝发生在接口权限层）；证据形态是平台评论的原文转录（评论 ID 与 UTC 时刻在案、执行容器由 `ENV-10` 实测识别），
   无投递件文件级 SHA-256，层级低于 round4 各件，按第 5(b) 类处理并额外登记转录件哈希（「本轮采集回执转录」机器块）。

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

## 本轮通道与状态实测

本节点（第二次派发，`2026-10-04T15:0x+08:00`）在同一台目标机上直接只读实测的现值，全部可重算；不含任何本机私有绝对路径。

```json
{
  "说明": "G4 节点第二次派发的实测现值；ENV-09/10/11 的机器来源",
  "本run会话": {
    "身份": "Multica dev-agent run（Qoder 会话，非 WorkBuddy 客户端会话）",
    "task-id": "01a105b0-5347-7a19-9d99-5678641c6f95",
    "agent-id": "ff6fcbb6-6bb6-42fb-9d88-03493c771411",
    "主机名": "DESKTOP-OT18TRG",
    "本会话mcp工具数": 0,
    "qoder通道": {"path_tail": "%USERPROFILE%/.qoder/mcp.json", "mcpServers": []},
    "codebuddy_cli通道": {"path_tail": "%USERPROFILE%/.codebuddy/mcp.json", "mcpServers": ["plugin_context-mode_context-mode"]},
    "结论": "两通道均无四声明连接器的 server 条目；本会话面 0/4 挂载，不能作为 RIN-06 的客户端会话面（ENV-09）"
  },
  "四声明连接器挂载结果_本run会话": {
    "wind-finance": "tool-not-mounted（本通道无该 server，非客户端会话结论）",
    "tdx-connector": "tool-not-mounted（同上）",
    "neodata": "tool-not-mounted（同上）",
    "westock-mcp": "tool-not-mounted（同上）"
  },
  "客户端会话心跳实测": {
    "path_tail": "%USERPROFILE%/.workbuddy/sessions/*.json",
    "14:24与14:36所属会话": {"sessionId_head": "1d95c0ef", "startedAt": "2026-10-04T12:21:31+08:00", "heartbeats": ["14:04:18", "14:24:58", "14:36:25"]},
    "当日其它有心跳会话": ["f09480ee（末次写入 12:20:24）", "8616b185（早于 13:00）"],
    "重管后新客户端会话": "未观测到（采集时点 15:0x）"
  },
  "连接器状态现值": {
    "path_tail": "%USERPROFILE%/.workbuddy/connectors/{accountIdentityKey}/connector-states.json",
    "file_mtime": "2026-10-04T15:02:45+08:00",
    "version": 4,
    "enabled": [],
    "userDisabled_true": ["teacher-assistant", "tdx-connector", "westock-mcp", "tushare", "neodata", "wind-finance"],
    "bound_true_all": true,
    "ifind_in_connectors_map": false,
    "credentials_content_read": false,
    "header_overrides_read": false
  },
  "客户端schema缓存": {
    "path_tail": "%USERPROFILE%/.workbuddy/mcp-tool-list.json",
    "file_mtime": "2026-10-04T14:35:01+08:00",
    "server_entries": 14,
    "max_entry_tools": 254,
    "name_to_key_md5_probe": "0 命中（键不可由连接器名反推）",
    "结论": "缓存条目在场≠会话挂载，不用作 RIN-06 判据（ENV-09）"
  }
}
```

## 本轮采集回执转录

`REP-03` 的改判依据是 Ray 在 Issue AIFI-43 的原文回执。该件不是投递文件（无文件级 SHA-256），锚点取「平台评论 ID + 正文哈希」：
正文哈希由本节点用 `multica issue comment list` 取回该评论的 `content` 字段后对 UTF-8 字节直接计算，任何后续节点或评审
可用同一命令重算比对，因此它比纯转述可核，但层级仍低于 round4 各件（`登记口径` 第 5(b)、第 9(c) 条）。

```json
{
  "说明": "转录锚点；正文不含凭据值",
  "source": "Issue AIFI-43 comment 01a105a8-a99e-7648-8021-ebd7ba01ab65",
  "created_at_utc": "2026-10-04T06:45:01Z",
  "content_sha256": "686b032ec83f87170a32aac55c95c68f8b4e6c618ae42c9b7c73e62450cc9f0b",
  "content_bytes": 4761,
  "content_chars": 2899,
  "拒绝原文转录": "tushare API 错误 [40203]: 抱歉，您没有接口(cyq_perf)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108",
  "调用对象": "mcp__tushare__cyq_perf，ts_code=600519.SH，执行时刻自述 2026-10-04T14:24+08:00",
  "与NZ-01的差异": "ts_code 不同（NZ-01 为 603599.SH），拒绝原文逐字一致",
  "agent_mail书面确认转录": "已实测确认为内置不可断项，无用户侧开关；三条依据＝不在市场清单 connectors-marketplace/.codebuddy-connector/connectors.json（456KB 全文检索无命中）、不在 installed_plugins.json 的 61 个已装插件内且不在用户级 mcp.json 且无独立插件目录、活体调用 agent-mail.GetMe 返回 status=not_bound",
  "确认登记地位": "按 RIN-06 原文规定「本节点按确认登记而不代为判定」入账，不写成节点自己的判定"
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
