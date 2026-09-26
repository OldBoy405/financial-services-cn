# WorkBuddy 二级市场研究专家 Implementation Plan

> **执行方式：**按下方任务顺序实施；每个任务的验收通过后再进入下一任务。本文是实施方案，不代表专家已安装、已发布或功能已通过验证。

**Goal:** 在明确排除 Microsoft 365 管理命令及 Claude Managed Agents（CMA）编排的前提下，原生构建 WorkBuddy 专家，先交付二级市场研究能力，再按相同验收标准扩展其他金融领域；任何已宣称迁移的能力不得以无来源数据、缺失产物或未经验证的回退路径冒充原功能。

**Architecture:** 原仓库的 `vertical-plugins/` 技能仍是方法论的唯一来源；WorkBuddy 目录保存专家定义、展示信息和连接器声明，导出时把所需技能及子资源复制成自包含专家包。首期采用一个 Agent 型研究专家和按需加载的技能，不为了复刻插件/命令目录先做 9 个专家或 Team。后续是否拆出专职专家由真实任务验收决定。

**Tech Stack:** WorkBuddy 专家包（`.codebuddy-plugin/plugin.json`、`agents/*.md`、`skills/*/SKILL.md`）、专家级 MCP/连接器依赖、原仓库 Python 技能脚本及交付物；导出脚本优先使用 Python 标准库。具体字段和发布流程以实施时的 [官方专家文档](https://open.workbuddy.cn/docs/expert)、[技能文档](https://open.workbuddy.cn/docs/skill)及目标客户端校验结果为准。

**Spec:** `workbuddy-expert-migration.md`、`codebuddy-financial-research-adaptation-plan.md`；用户本次确认的范围与分阶段要求优先于两份旧方案中的范围假设。

## 全局约束与成功定义

- **范围外：**`claude-for-msft-365-install/` 的命令与供应流程；`managed-agent-cookbooks/` 的部署、30 个 CMA 子代理及其编排。它们不计入本方案的迁移完成率，也不应被宣称已迁移。
- **范围内：**首期二级市场研究的 9 条原命令对应的业务任务、9 个技能及其所需的财务建模、取数、文件交付能力；其后的其他插件分期规划，不预先固定为 16 个专家。
- **交互差异：**WorkBuddy 专家中用自然语言任务入口替代原 slash 命令语法；允许入口形式不同，不允许原命令独有的提问、校验、产出要求被静默删除。若 slash 语法本身必须保留，先确认平台确有受支持的机制，否则作为明确的产品差异单独审批。
- **发布口径：**试点只能标注已通过的能力；“二级市场研究功能迁移完成”要求下表全部 9 项及其所需数据链路验收通过。缺商业订阅时，公开资料摘要可以单独作为受限能力发布，但不能宣称完整覆盖一致预期、实时筛选或机构级估值研究。
- **安全边界：**不在仓库、专家包或演示素材中写真实 Token、客户数据或内部 URL 凭据。商业及内部数据源需要各安装用户按授权连接；读写范围由连接器/服务端权限控制，不靠 Agent 提示词保证。
- **单一来源：**先改 `plugins/vertical-plugins/<vertical>/skills/` 等原技能源，再导出副本；不在已安装专家目录手工维护第二份技能。改动原技能后按 `CLAUDE.md` 执行 `python3 scripts/sync-agent-skills.py` 和 `python3 scripts/check.py`。

## Review Focus

| 高风险输入或运行条件 | 预期行为与归属任务 |
| --- | --- |
| 无商业数据授权、空结果或连接器禁用 | 不编造共识/筛选结果，不宣称完整报告；任务 3 的无权限、空结果测试及任务 4 的 earnings 测试。 |
| 用户指定历史季度而非最新季度 | 查对**指定期间**的数据，不把旧季度误当本期，也不混入当前数据；任务 1 固定输入，任务 4 历史季度反例。 |
| 股票代码/公司名有歧义 | 先确认证券和交易所，再取数或计算；任务 1 的输入定义、任务 4 的错误/歧义代码测试。 |
| initiate 跨会话缺失旧模型或图表 | 停在对应任务，明确请求原文件，不输出占位估值/报告；任务 2 的前置守卫与任务 4 的重入测试。 |
| 新用户无本机脚本依赖或旧工作目录 | 显式报告失败，不把开发者机器上的成功当市场可用；任务 4 的产物测试与任务 5 的干净环境安装测试。 |

## 当前已核实的事实与需验证的假设

- `plugins/vertical-plugins/equity-research/` 有 9 个技能、9 个命令；命令名称与技能名称不总相同（如 `/screen` → `idea-generation`，`/initiate` → `initiating-coverage`）。命令并非全是空壳：`commands/earnings.md` 另规定季度核实、数据时效、图表、引用及 DOCX 交付。
- `skills/initiating-coverage/SKILL.md` 是 **5 次分别发起、每步交付并等待用户继续** 的流程；产物依次为研究文档、Excel 模型、估值文档并更新模型、图表 ZIP、最终 DOCX。跨会话找到上一步产物是实际验收的一部分。
- `plugins/vertical-plugins/financial-analysis/` 实有 13 个技能；第一份方案漏了 `clean-data-xls`、`ppt-template-creator`、`skill-creator` 的目标归属。后续扩展 financial-analysis 时必须处理，不能沿用旧方案的“12 个/全部覆盖”计数。
- `plugins/vertical-plugins/financial-analysis/.mcp.json` **缺少 egnyte 后的逗号及末尾的一个闭合 `}`**。不要直接合并或打包该文件。官方专家规范支持包内 `.mcp.json` 和 `plugin.json` 的 `dependencies.mcpServers`；不能只修改开发者本机 `~/.workbuddy/mcp.json`。
- CodeBuddy CLI 的现成市场插件与 WorkBuddy 专家不是同一个安装物。CodeBuddy 的研究插件、官方 DOCX/XLSX/PPTX 插件和 `$CODEBUDDY_ARTIFACTS` 路径只能作为参考，**不得**作为 WorkBuddy 已有能力的验收证据。
- **（2026-09-24 已核实）WorkBuddy 已原生内置腾讯文档官方 Office 技能，docx/xlsx/pptx 处理不构成能力缺口**，无需 CodeBuddy 市场插件、也无需裸写 `openpyxl`/`python-pptx` 脚本兜底。经读取本机 WorkBuddy 内置插件（v5.5.6）技能定义，以下技能开箱即用：`tencent-docs-routing`（本地 Office/WPS 文件总路由，任何 doc/sheet/slide 任务须最先加载）；`tencent-docx`（从零生成或整篇美化 .docx，自动封面目录；内含 `stock-research-report-expert` 证券研报专家与 doc-writer→doc-formatter→doc-converter 流水线）；`tencent-docs-sheet-generation`（无源表格时 openpyxl 从零建 .xlsx 并以 recalc 校验公式零错误）；`tencent-docs-sheetagent`（已有 .xlsx/.csv 的读写、分析、公式构造、图表、透视、清洗，委派 sheet-agent 子代理）；`tencent-local-office-edit`（经 editor_sdk/edsdk.py 实时打开、编辑、保存本机 docx/xlsx/pptx）；`tencent-pptx`（slidep 生成 .pptx，生成后编辑走 `tencent-local-office-edit`）；`pdf`/`pdfkit-py`（PDF 申报文件解析，附加）。依赖管理结论：openpyxl 由 excel-generation 技能幂等安装兜底、pptx 由托管 Node 环境预装 slidep，原“WorkBuddy 不自动安装 openpyxl/python-pptx”的假设对上述技能不成立；硬约束是必须按各 SKILL.md 强制流程执行（路由优先、编辑前查 schema、sheetagent 原子委派），不得绕过技能直接操作文件。

## 首期能力对照与测试入口

以下为九项业务任务；每项至少覆盖中文、英文各一次触发，以及一条数据不足或前置条件缺失的边界用例。具体格式以源命令和技能为准，不凭表格摘要降低原要求。

| 原命令 | 原技能 | 交付/关键约束（首期测试重点） |
| --- | --- | --- |
| `/earnings [公司] [季度]` | `earnings-analysis` | 对应季度的公告、申报文件和获许可的共识数据；核对时效、口径、图表、逐数字来源与可打开的 DOCX。 |
| `/earnings-preview [股票]` | `earnings-preview` | 发布前的情景、关键指标与共识对比；共识不可得时不得编造。 |
| `/initiate [股票]` | `initiating-coverage` | 5 次分步执行，逐步核验前置文件及用户确认；按源技能输出 `.md`、`.xlsx`、估值分析/模型、`.zip`、`.docx`。 |
| `/model-update [股票]` | `model-update` | 用新公告/指引更新原模型，保留活公式、假设、来源与变动说明，不以静态表代替。 |
| `/morning-note` | `morning-note` | 所覆盖股票的隔夜事件、市场反应与出处；无实时/获许可数据则标明覆盖缺口。 |
| `/screen [条件]` | `idea-generation` | 按指定筛选条件形成候选及可复核依据；没有完整行情/股票池不得声称全市场筛选。 |
| `/sector [行业]` | `sector-overview` | 行业格局、可比公司、规模口径与来源；不得混用不同币种/时间点。 |
| `/thesis [股票]` | `thesis-tracker` | 创建或更新论点，区分历史论据、新数据、催化剂及反证，并能找回旧版本。 |
| `/catalysts [时间窗]` | `catalyst-calendar` | 在指定时间窗列出有来源及日期的事件；能追加/更新而非凭空生成日期。 |

## 任务 1：固定基线与真实数据前提

**输入：**上表所列 9 个 `commands/*.md`、9 个 `skills/*/SKILL.md` 及 `initiating-coverage/references/`、`assets/`；原仓库 `plugins/agent-plugins/{earnings-reviewer,market-researcher}/` 仅供比对独立能力，不在这一步直接复制为 Team。

**产出：**将上表细化进 `workbuddy-experts/equity-research/README.md`：逐项列出源文件、输入追问、必需数据、来源/日期要求、产物格式、缺失数据时的安全行为、WorkBuddy 的测试问法；固定一个可合法使用的财报样例及预期产物，样例文件放在被 `.gitignore` 忽略的 `out/`，不放客户数据。

- [ ] 逐条阅读命令正文，标注技能描述中未覆盖的要求，尤其 `/earnings` 的时效、共识和报告清单。
- [ ] 对 `/initiate` 固定五个**不同用户请求**，记录每步需要读取的上一阶段文件和应停止的情形。
- [ ] 确定每项所需的公开源、商业源及机构源；拿不到共识、实时筛选数据或历史模型时，先标记“未具备完整验收条件”，不要通过 `[UNSOURCED]` 兜底算通过。
- [ ] 记录原任务中人工确认与外部写入的边界；专家不会自行发布研究结论或写回机构系统。

**验收：**九项都有可复现的正例和缺失数据/前置条件反例；所有数据源的使用者、授权方式、日期口径清楚。无可合法使用的原始样例时，本任务不能签署“功能等价”，但可继续进行内部技术试点。

## 任务 2：构建一个原生 Agent 型专家与可复现包

**文件：**

- 新建 `workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json`：专家标识、Agent/技能路径、双语展示、头像与依赖声明；展示字段按当前官方校验要求填写。
- 新建 `workbuddy-experts/equity-research/agents/equity-research.md`：研究入口、九项任务路由、证据与边界规则；不照搬原 `tools:` 字段。
- 更新任务 1 创建的 `workbuddy-experts/equity-research/README.md` 并添加所需头像；九项命令对照及用户问法保存在 README，不往专家包加入未经目标环境认可的 `commands/`。
- 新建 `scripts/export_workbuddy_experts.py`：将上述专家定义和 `plugins/vertical-plugins/equity-research/skills/` 的 **9 个完整目录**复制到 `out/workbuddy-experts/equity-research/`，保留 `references/`、`assets/`，拒绝源技能缺失或目标路径不在包内。导出物不作为另一份手工编辑源。

- [ ] 先只用 `earnings` 做路由和产物试点；其他技能虽随包携带，但未验收前不在专家卡片中宣称九项全部可用。
- [ ] 为九项各写一个中文和一个英文触发问法；三条 quickPrompts 用于高频示例，不视为其余六项的替代入口。
- [ ] `initiating-coverage` 的每步只按当前任务加载所需参考文件、核验前置产物并等待下一次用户请求；绝不自动越过五个任务间的人工关口。
- [ ] 导出后核对 9 个 `SKILL.md` 及其子资源、清单中每条相对路径，并在目标 WorkBuddy 环境按**实际安装位置**调用当前校验器；仓库没有 `scripts/validate_expert.py`，不得把旧方案中的该相对命令直接当作已可执行。

**验收：**导出两次内容一致；来源与生成的技能文件一致；九种问法可路由到预期技能；请求 Task 3 而没有 Task 2 模型时明确阻止；目标客户端能召唤专家。此时只说明“包和路由通过”，不说明金融研究功能全部通过。

## 任务 3：接通必要数据且不扩大权限

**文件：**`workbuddy-experts/equity-research/.mcp.json`（仅有确实使用的远程服务）及清单中的 `dependencies`；若重用原 `financial-analysis/.mcp.json`，先修复上述两处语法错误，并以 `python -m json.tool plugins/vertical-plugins/financial-analysis/.mcp.json` 校验。

- [ ] 为每个服务列出专家实际需要的工具、只读/写入动作、许可主体和用户侧认证方式；不一次性合并旧方案中的 30 多个服务。
- [ ] 以 `dependencies.mcpServers` / `dependencies.connectors` 声明包级依赖，遵循 [WorkBuddy 官方说明](https://open.workbuddy.cn/docs/expert)用变量/授权流程取得凭据，禁止打包真实密钥。若本地校验器拒绝官方文档允许的包内 `.mcp.json`，先确认版本及市场规范，解决冲突后再继续，不改用仅在开发机有效的全局配置。比较同名 FactSet/LSEG 端点时以所需工具与返回口径实测决定，不能仅凭 URL 合并或起别名。
- [ ] 在**另一安装用户**环境实际连接并各调用一次必需工具，验证工具可见、结果时间与许可范围；不能连通的商业/机构 MCP 列为该功能的发布阻断项。
- [ ] 检查报告中每个用于计算或结论的关键数字能追到文件/链接、日期和单位；无共识时既不伪造 beat/miss，也不宣称完成机构级报告。

**验收：**必需服务真实返回数据；未授权用户不能越权读取；断网、空结果和权限拒绝均被明确标示且不会生成貌似完整的报告。只修改开发机全局 `mcp.json` 或仅看到服务器“已配置”均不算通过。

## 任务 4：验证交付物和跨轮研究流程

**目标：**先在 WorkBuddy 运行 `earnings`，然后是 `model-update` 与 `initiate`，最后跑完表中剩余六项。文件生成使用 WorkBuddy 实测可用的原生能力；若不满足原要求，再按缺口引入最小脚本和依赖。不得假定 CodeBuddy 市场 `docx/xlsx/pptx` 插件在 WorkBuddy 可用，也不得假定 WorkBuddy 自动安装 `openpyxl`、`python-pptx`。

**已核实（2026-09-24，工具层就绪）：**本任务的 docx/xlsx/pptx 需求可由 WorkBuddy 原生内置技能满足，不需要 CodeBuddy 市场插件，也不需要裸脚本兜底。路由约定：DOCX 交付走 `tencent-docx`（研报类经其内置 `stock-research-report-expert`）；新建 Excel 模型走 `tencent-docs-sheet-generation`（openpyxl + recalc 公式校验）；更新既有模型走 `tencent-docs-sheetagent`（委派 sheet-agent 子代理，保留活公式/引用/假设）；本机 `.md`/`.xlsx`/`.zip`/`.docx` 的打开核对走 `tencent-local-office-edit`（edsdk.py）与宿主预览。注意口径：以上仅证明“工具就绪”，不等于“产物达标”；未经端到端实测前不得宣称文件交付能力验收通过。

- [ ] 用有明确来源和使用权的财报完成 earnings：验证指定季度、共识来源/缺口、数据表、图表、引文与下载后可打开的 DOCX；对比原 `commands/earnings.md` 的质量清单。若数据条件不齐，改为标注“公开数据摘要”试点而非完整版 earnings。DOCX 生成经 `tencent-docx`（研报体量走其内置 `stock-research-report-expert`，默认常规点评档）。
- [ ] 更新既有 Excel 模型：打开文件检查公式仍可计算、引用不断链、假设和变动出处保留；静态数字表不算替代模型。更新动作经 `tencent-docs-sheetagent` 委派 sheet-agent 子代理执行，不得以静态表覆盖公式区。
- [ ] 逐次执行 initiate Task 1–5，期间退出并重新进入会话，提供先前产物路径；Task 3 缺 Task 2、Task 5 缺图表时必须停止而非生成占位报告。下载、打开 `.md`、`.xlsx`、`.zip`、`.docx` 并核对内容。产物路由：`.md`/`.docx` 走 `tencent-docx`，新建 `.xlsx` 模型走 `tencent-docs-sheet-generation`，更新模型走 `tencent-docs-sheetagent`，打开核验走 `tencent-local-office-edit`。
- [ ] 对筛选、催化剂、晨会纪要、预览、行业及论点任务，按能力对照表检查数据覆盖、时效、出处和二次更新；至少试一次错误股票代码、历史季度、空结果、无权限及相互矛盾的来源。

**验收：**九项各有原任务要求的真实结果和负例处理，跨轮产物可恢复；无来源数字不得进入结论。报告的评级、价格目标或投资建议在真实数据/人工审核条件不满足时不能由模型凭空补全。

## 任务 5：从本机试用走到专家市场发布

- [ ] 用目标 WorkBuddy 版本实际认可的校验及注册流程安装导出包；记录 WorkBuddy 版本、校验器版本、专家包版本和校验结果。`~/.workbuddy/plugins/marketplaces/my-experts/` 可用于本机验收，**不是公开市场上架证明**。
- [ ] 用未参与开发的安装用户在干净环境完成安装、逐项连接授权、九项任务、文件下载与重新进入会话；确认专家包不依赖开发机全局配置或绝对路径。
- [ ] 核对所使用的品牌、开源许可、合作方内容、数据再分发条款及研究免责声明；如果公开市场不允许该数据或内容的发布，改为获准的私有分发范围，不绕开权限。
- [ ] 按 WorkBuddy 开放平台当前提交流程提交包，记录提交与审核结果；修改技能、权限或连接器后提高包版本并重做受影响的验收。

**发布判据：**专家卡片只列已经通过的工作流；九项未全部通过前不使用“原二级市场插件全功能迁移”“功能无降级”等表述。用户能拿到产物、能看到缺失数据说明，且市场安装者具备与开发者相同的授权连接路径。

## 后续领域的复用边界

二级市场全部通过后，再分别评估 `financial-analysis`、`investment-banking`、`private-equity`、`fund-admin`、`operations`、partner-built 和顾问场景；不默认一个原插件就是一个专家，也不默认既有 10 个 Agent 都应升级为 Team。扩展 `financial-analysis` 时显式处理未被旧 16 专家映射覆盖的 `clean-data-xls`、`ppt-template-creator`、`skill-creator`；工具层（2026-09-24 核实）中 `clean-data-xls` 对应 WorkBuddy 内置 `tencent-docs-sheetagent`（表格清洗/整理），`ppt-template-creator` 对应 `tencent-pptx`（生成后编辑走 `tencent-local-office-edit`），迁移时按同一路由验收，无需另建文件脚本。顾问场景需另做原 `AskUserQuestion`、`ToolSearch`、`ListConnectors` 等交互/连接发现机制的等价验证；不能套用二级市场单专家的验收结论。Microsoft 365 和 CMA 保持本方案范围外。

## 自检清单（方案执行完毕时填写）

- [ ] 范围、九项对照、每项发布宣称一致；无已发布但未通过的任务。
- [ ] 专家包技能副本与源技能一致，MCP JSON 可解析，未打包真实凭据。
- [ ] 新安装用户和开发者得到同样的取数、文件下载与跨轮接续能力。
- [ ] 无订阅、无权限、数据过期、来源冲突、缺前置文件时都有明确停止/降级标识，而非伪造完整结果。
- [ ] 工作流完成与市场审核为**两个独立状态**，有对应的记录。

**参考资料：**[WorkBuddy 专家包规范](https://open.workbuddy.cn/docs/expert) · [技能包规范](https://open.workbuddy.cn/docs/skill) · [连接器接入说明](https://open.workbuddy.cn/docs/connector)。
