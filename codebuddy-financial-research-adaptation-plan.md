# 金融服务插件在 CodeBuddy 的不降级适配方案

> 状态：讨论与实施方案，未安装插件、未修改原项目、未完成运行态验收。
> 依据：前次只读核验（2026-09-21）与本次对本地 Anthropic `financial-services` 原版关键文件的只读复核。市场内容和产品能力可能随版本变化，实施时应重新核对。

## 1. 目标与边界

目标是在 **CodeBuddy CLI** 中使用二级市场股票研究插件，尽量保持原工作流的五项能力：斜杠命令可触发、所需 skill 可调用、代理/多步骤流程可执行、研究数字可溯源、真正的 DOCX/XLSX/PPTX 交付物可被使用方取得。

本方案**只针对 CodeBuddy**；不改造 Multica，不把 WorkBuddy 视为与 CodeBuddy 插件机制等价。商业行情和研究数据的授权不在技术适配范围内：缺少订阅或可用数据时，不能宣称“全功能不降级”。

## 2. 已知现状

| 对象 | 前次只读核验结论 | 对方案的影响 |
|---|---|---|
| `cb_teams_marketplace` | 有 `equity-research`、`financial-analysis`，还有 `a-share-analysis`、`finance-data` 等。股票研究 skill 主体已被移植，个别文档技能引用改成了 CodeBuddy 名称。 | **先复用现成插件，不先改 Anthropic 原仓库。** |
| `codebuddy-plugins-official` | 有 `docx`、`xlsx`、`pptx`、`pdf` 插件。 | 优先安装并验证，再决定是否需要自己编写文档技能。 |
| 斜杠命令 | 前次检查中，移植版 `equity-research` 缺少原版 9 个 `commands/*.md`，`financial-analysis` 也缺少原版命令。 | 若要求原命令体验，需要在独立的适配副本中补回并逐个验证。 |
| 命名 agent | 前次检查中，Teams 市场未移植 `market-researcher`、`earnings-reviewer` 等独立 agent 插件。 | 需要按实际使用场景恢复，不必一次搬运全部 agent。 |
| 数据连接器 | 上游 `financial-analysis/.mcp.json` 提供多个远程 MCP 定义；前次检查中移植版未包含。连接器本身不附带订阅或凭据。 | 按需注册、完成鉴权，并验证可用性与数据许可。 |
| 规则和 hooks | 前次检查中部分移植版携带 `rules/`，但没有可使其生效的 hook；`financial-analysis` 的 Windows PowerShell SessionStart 脚本存在编码兼容问题。 | 规则是否注入成功必须在新会话验证，不可只看目录存在。 |

### 本次复核发现的修正

上游 `plugins/vertical-plugins/financial-analysis/.mcp.json` **不是合法 JSON**：`egnyte` 条目之后缺少逗号，`box` 条目与外层对象也缺少闭合结构。因此不能“原样复制上游 `.mcp.json` 并注册”。应在**适配副本**中修复语法、通过 JSON 解析校验，再逐个测试实际要用的 MCP；勿把密钥提交进仓库。此前关于连接器数量的口头估计不作为实施依据，以修复后的清单为准。

## 3. 实施路径

### 阶段 A：先验证现成能力（不改插件）

1. 在 CodeBuddy 的插件界面确认 `cb_teams_marketplace` 和 `codebuddy-plugins-official` 当前可用，安装/启用 `equity-research`、`financial-analysis` 与实际需要的 `docx`、`xlsx`；仅在要制作演示文稿/处理 PDF 时补 `pptx`、`pdf`。
2. 打开新会话，确认 `/plugin` 中状态正常；通过帮助/技能列表和一个小型财报样例，验证 `earnings-analysis`、文档技能以及文件生成功能真的可调用，而不只是“已安装”。
3. 若使用自定义模型，先确认 `/model` 可选该模型，且它支持工具调用；模型不可见时先排查 `models.json`、`availableModels` 与进程重载，避免把模型配置故障误判成插件故障。
4. 记录插件版本、CodeBuddy 版本和测试结果。若这里已满足实际业务需求，**停止改造**。

### 阶段 B：恢复原版交互与编排（适配副本，不改上游原件）

1. **命令**：按需将上游 `plugins/vertical-plugins/equity-research/commands/*.md` 放入适配插件的 `commands/`；用 `/help` 和实际调用逐项确认 `/equity-research:earnings` 等命令能找到目标 skill。留意裸 skill 名称在 CodeBuddy 中是否需要插件命名空间，按测试结果修正引用。
2. **代理**：仅对要用的场景补 `market-researcher`、`earnings-reviewer` 等 `agents/*.md`。原版 `market-researcher` 的 `tools` 只列 `Read, Write, Edit, mcp__capiq__*, mcp__factset__*`；原版 `earnings-reviewer` 也偏向付费 MCP。先确认当前 CodeBuddy 版本允许哪些工具名，再为实际需要的 skill 调用、联网取数及文件处理增加最小授权，避免照搬后代理无法完成自身流程。
3. **多步骤工作流**：对 `initiating-coverage` 等任务明确输入、顺序、上一步产物和人工审核点。先尝试主 agent 顺序执行；只有被实测证实需要并行/隔离时才引入子代理，不假设 Claude 的 Task 编排行为自动等价。
4. **规则与 hook**：核实移植版 `rules/` 在新会话是否生效；无效时采用 CodeBuddy 支持的插件级 hook 或项目级规则。若使用前次发现的 `financial-analysis/hooks/session-start.ps1`，在 Windows PowerShell 5.1 环境中修复其 UTF-8 BOM/ASCII 兼容问题，并验证 SessionStart 无解析错误。不要把“目录里有文件”当成规则已生效。
5. 变更后按实际插件缓存/版本机制更新适配副本版本并重装或刷新，防止读到旧内容。

### 阶段 C：数据与交付物闭环

1. **数据**：有商业授权时，仅注册研究任务必需的 MCP，使用本机安全凭据完成认证；先修复上游 `.mcp.json` 的语法，再验证连接、权限、数据时效与引用来源。无授权时使用用户提供的财报/公告及获准的公开来源；`finance-data` 可作为可用性试点，**不等同于商业数据完整覆盖**。无法核验的数字保留 `[UNSOURCED]`，不编造一致预期、行情或估值倍数。
2. **交付物**：优先调用已安装的官方 DOCX/XLSX/PPTX 技能；如其接口或效果不能满足要求，再按缺口补脚本化方案。把最终文件写到当前 CodeBuddy 环境约定的交付目录（前次建议为 `$CODEBUDDY_ARTIFACTS`，实施时以实际版本文档/运行结果确认），并从使用方视角验证文件可取得、可打开、内容和表格正确。
3. **A 股/港股**：可复用研究方法论，但需另定数据源、会计口径、币种、交易日历和信息披露来源；不能直接将偏美股的 SEC/电话会模板当作覆盖完成。

## 4. 优先级与验收

| 优先级 | 工作 | 完成判据 |
|---|---|---|
| P0 | 安装现成插件、验证模型工具调用与官方文档技能 | 插件在新会话可用；给定财报样例能执行分析，生成可打开的 DOCX/XLSX 草稿。 |
| P1 | 补所需命令/agent、校验规则与 hook、打通交付目录 | `/help` 能看到所需命令；指定 agent 可完成流程；SessionStart 无错误；使用方能拿到文件。 |
| P1（取决于数据授权） | 修复并接通必要的 MCP，或建立可核验的公开数据路径 | 报告中每个关键数字有来源、日期与口径；无源数据显式标注，不将草稿冒充完整研究报告。 |
| P2 | 固定运行依赖与版本、补充复现与审计记录 | 换新会话/新机器按文档可复现，依赖和权限有记录。 |

**最小端到端测试**：选一份有明确来源的财报/公告 → 在新会话触发 `earnings` 路径 → 核对 skill/代理调用和数字出处 → 生成 DOCX/XLSX → 从交付入口下载并打开 → 检查 SessionStart 日志与未知数字标注。失败时记录具体断点，而非笼统归因于“平台降级”。

## 5. WorkBuddy 的单独结论

前次资料仅支持“两者属于同一产品线、底层能力有共通性”，**不支持推断 WorkBuddy 与 CodeBuddy 具有同样的插件安装、斜杠命令、代理工具白名单、MCP、hook 或交付目录机制**。因此本方案不能原样作为 WorkBuddy 实施说明。

若以后要适配 WorkBuddy，应先只读确认其当前版本对上述六类能力的实际入口，再用同一份财报样例分别验证“触发—取数—分析—产物—交付”。若任一环节无对应机制，就应记为明确的功能差距，提出 WorkBuddy 专用方案，而不是宣称“不降级”。

## 6. 风险与决策点

- **必须先确认**：实际使用的 CodeBuddy 版本/市场插件是否仍与前次核验一致；不能把旧快照当作当前运行事实。
- **必须先确认**：可用的数据授权、合规边界及报告用途；缺订阅时不能保证与原商业研究流程等价。
- **建议先选一个试点**：优先做 `earnings`，跑通后再扩到 `initiate`、`market-researcher` 等复杂流程。
- **本文件仅为方案**：未对原始插件、当前 CodeBuddy 安装或 WorkBuddy 环境作任何实施改动。
