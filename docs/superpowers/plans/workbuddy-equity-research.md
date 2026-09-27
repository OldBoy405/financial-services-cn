# WorkBuddy 二级市场研究专家 Implementation Plan

> **执行方式：**按下方任务顺序实施；每个任务的验收通过后再进入下一任务。本文是实施方案，不代表专家已安装、已发布或功能已通过验证。
> **版本：**v1.2（2026-09-26 修订）。沿革：2026-09-24 初版 → v1.1（2026-09-25，融入 WorkBuddy 基础设施逐项排查确认的新事实）→ 本版（融入 grill 会话 2026-09-25/26 三轮定稿的 10 项决策，见"决策台账"）。任务顺序、安全纪律与已核实事实框架不变；与 v1.1 冲突处以本版为准。主要变更：phase-1 定位本机自用、市场锚定 A股/港股（任务形态等价判据）、里程碑两级、数据源优先级表定稿、**美系 MCP 全部移除（设计性排除）**、任务 5 降级为发布就绪检查、验收留痕（ACCEPTANCE.md）、产物规格本地化。同日追补：D4 上游策略细化为根目录 `CUSTOM.md` 台账驱动的增量合并总则（取代"永久分叉"口径）。

**Goal:** 在明确排除 Microsoft 365 管理命令、Claude Managed Agents（CMA）编排及**美系 MCP 数据源（D10，设计性排除）**的前提下，原生构建 WorkBuddy 专家，先交付**以 A股为主、港股为辅**的二级市场研究能力，phase-1 面向本机自用；专家市场发布为 phase-2 独立目标，后续按相同验收标准扩展其他金融领域。任何已宣称迁移的能力不得以无来源数据、缺失产物或未经验证的回退路径冒充原功能。

**Architecture:** 原仓库的 `vertical-plugins/` 技能仍是方法论的唯一来源；WorkBuddy 目录保存专家定义、展示信息和连接器声明，导出时把所需技能及子资源复制成自包含专家包。首期采用一个 Agent 型研究专家和按需加载的技能，不为了复刻插件/命令目录先做 9 个专家或 Team。后续是否拆出专职专家由真实任务验收决定。

**Tech Stack:** WorkBuddy 专家包（`.codebuddy-plugin/plugin.json`、`agents/*.md`、`skills/*/SKILL.md`）、专家级连接器依赖（仅 `dependencies.connectors`，包内不创建 `.mcp.json`，见任务 3）、原仓库 Python 技能脚本及交付物；导出脚本优先使用 Python 标准库。专家包的初始化/校验/注册/打包复用 WorkBuddy 内置 `expert-manager` 技能自带脚本，文件交付复用内置腾讯文档 Office 技能（均见下方事实区）。具体字段和发布流程以实施时的 [官方专家文档](https://open.workbuddy.cn/docs/expert)、[技能文档](https://open.workbuddy.cn/docs/skill)及目标客户端校验结果为准。

**Spec:** `workbuddy-expert-migration.md`、`codebuddy-financial-research-adaptation-plan.md`（两份旧方案中与本版决策冲突的范围假设作废，特别是"16 专家全量迁移"与"合并 30 个 MCP 服务器进全局 mcp.json"两条）；本版新增权威依据：**决策台账**（下节）。修订依据：2026-09-24/25 基础设施逐项核查、2026-09-25 连接器实测、2026-09-26 对原 9 技能的市场假设/宿主依赖逐字核查（见事实区末条）。

## 决策台账（2026-09-25/26 grill 会话定稿，共 10 项）

| # | 决策 | 内容 |
| --- | --- | --- |
| D1 | 终局定位 | phase-1 = 本机自用；专家市场上架移 phase-2 独立立项；任务 5 降级为"发布就绪检查" |
| D2 | 市场锚定 | A股为主、港股为辅；**等价 = 任务形态等价**（同样的追问、时效校验、产物清单、负例处理），非市场覆盖等价、非数据源等价；本定义是所有等价性判断与"不静默删除"判定的前提 |
| D3 | 里程碑两级 | M1 = earnings / initiate / model-update 真实可用（研究主链）；M2 = 其余六项轻任务；"迁移完成"对外宣称唯一口径仍为 9/9 全过 |
| D4 | 改写纪律 | 深度本地化允许：数据源/环境引用章节必须重写，行为要求（追问、时效校验、产物清单、负例处理）逐条保留；每处改动登记进任务 1 等价映射表与根目录 `CUSTOM.md` 台账；动工前打 baseline tag + 走 `workbuddy/main` 分支；上游更新按 `CUSTOM.md` 总则增量合并（2026-09-26 追补，取代"永久分叉"口径） |
| D5 | 节奏 | 任务 1 限一个工作节拍（产出基线文档即止，反例可边跑边补）；任务 4 验收排进真实研究日程，用真实工作代替专门测试 |
| D6 | 数据源优先级表 | 定稿表见任务 3；同一任务同一指标单源取数、跨源标注；`wb-finance-skill` 红线为底层纪律层，不抢数据路由 |
| D7 | 验收留痕 | 新建 `workbuddy-experts/equity-research/ACCEPTANCE.md`：每任务一行（日期/测试问法/产物链接/负例结果/裁决）；用户为唯一裁决人；第二安装用户实测移 phase-2，phase-1 仅做本机重装验证 |
| D8 | 等价映射硬规则 | 评级映射 A股五档（买入/增持/中性/减持/卖出）+ CNY 目标价，数据不满足按红线不输出、标缺口；**概念等价物直接映射**：两融↔short interest、增减持↔insider windows、NMPA↔FDA、限售解禁↔lockup、业绩预告/业绩快报↔whisper/guidance（制度升级而非降级）、央行/LPR/国常会↔Fed/FOMC、盘后披露+次日反映↔pre-market/after-hours；**无对应物显式标缺口**（options-implied move、盘前盘后价格序列），禁止发明替代指标；产物全中文（含图表标签）、页数锚 8–12 页照搬、文件命名中文化（`[公司]_[年]Q[季]_季报点评.docx`）、字体走 tencent-docx 内置模板 |
| D9 | 固定样例 | 三条件自动选定：动工时最近完整披露 + 研报覆盖充分 + Wind 可查；三条件写入基线文档，不预先点名标的 |
| D10 | 美系 MCP 移除 | 移植后去除全部美股 MCP（原"默认关闭"口径作废）：专家包零美系声明、不创建包内 `.mcp.json`；美股机构级从"管理缺口"升级为**设计性排除**；美股个股请求不拒答，走公开面（westock-data 美股行情/财报、neodata 美股公开数据）+ 报告显式标注"本专家不接入美系机构数据源，以下基于公开数据" |

## 全局约束与成功定义

- **范围外：**`claude-for-msft-365-install/` 的命令与供应流程；`managed-agent-cookbooks/` 的部署、30 个 CMA 子代理及其编排；**原仓库全部美系 MCP 服务器（FactSet/LSEG/Daloopa/Morningstar/S&P Global/Moody's/MT Newswire/Aiera/PitchBook/Chronograph/Egnyte/Box 等，D10 设计性排除）**。它们不计入本方案的迁移完成率，也不应被宣称已迁移。
- **范围内：**首期二级市场研究的 9 条原命令对应的业务任务（验收市场锚定 A股/港股，D2）、9 个技能及其所需的财务建模、取数、文件交付能力；其后的其他插件分期规划，不预先固定为 16 个专家。
- **交互差异：**WorkBuddy 专家中用自然语言任务入口替代原 slash 命令语法；允许入口形式不同，不允许原命令独有的提问、校验、产出要求被静默删除（判定以任务形态等价为标准，D2）。若 slash 语法本身必须保留，先确认平台确有受支持的机制，否则作为明确的产品差异单独审批。
- **发布口径：**phase-1 为本机自用（D1），不涉及公开发布宣称；"二级市场研究功能迁移完成"仍要求九项全部验收通过并在 ACCEPTANCE.md 留痕（D3/D7）。对外发布与"公开数据摘要"受限能力口径随 phase-2 发布就绪检查再定。
- **安全边界：**不在仓库、专家包或演示素材中写真实 Token、客户数据或内部 URL 凭据。商业及内部数据源需要各安装用户按授权连接；读写范围由连接器/服务端权限控制，不靠 Agent 提示词保证。
- **单一来源与 git 纪律（D4）：**先改 `plugins/vertical-plugins/<vertical>/skills/` 等原技能源，再导出副本；不在已安装专家目录手工维护第二份技能。**动工前先打 baseline tag（`baseline/upstream-fca3cc8`，以动工时实际 HEAD 为准）**，所有改动走 `workbuddy/main` 分支 + commit；上游更新按根目录 `CUSTOM.md`（二开台账 + 合并总则）增量合并，原版要求随时 `git diff baseline/...` 对照，本地化文件加 `WB-CUSTOM` 文件头标记。改动原技能后按 `CLAUDE.md` 执行 `python3 scripts/sync-agent-skills.py` 和 `python3 scripts/check.py`。
- **美股请求红线（D10）：**任何涉及美股个股的任务，输出必须显式标注"本专家不接入美系机构数据源，以下基于公开数据"；机构级共识、估值等缺口不得以公开数据冒充。

## Review Focus

| 高风险输入或运行条件 | 预期行为与归属任务 |
| --- | --- |
| 无商业数据授权、空结果或连接器禁用 | 不编造共识/筛选结果，不宣称完整报告；任务 3 的无权限、空结果测试及任务 4 的 earnings 测试。 |
| 用户指定历史季度而非最新季度 | 查对**指定期间**的数据，不把旧季度误当本期，也不混入当前数据；任务 1 固定输入，任务 4 历史季度反例。 |
| 股票代码/公司名有歧义 | 先确认证券和交易所，再取数或计算；任务 1 的输入定义、任务 4 的错误/歧义代码测试。 |
| 美股个股请求（D10） | 不拒答：走 westock-data/neodata 公开面 + 显式"不接入美系机构数据源"标注；机构级缺口明示，不以公开数据冒充；任务 4 边界用例。 |
| initiate 跨会话缺失旧模型或图表 | 停在对应任务，明确请求原文件，不输出占位估值/报告；任务 2 的前置守卫与任务 4 的重入测试。 |
| 新环境无本机脚本依赖或旧工作目录 | 显式报告失败，不把开发者机器上的成功当可用；任务 4 的产物测试与任务 5 的本机重装验证。 |
| 公开数据工具链（westock CLI、neodata 云服务连接）未安装或未授权 | 显式报告依赖缺口与安装/授权指引，不静默改用网页检索或训练数据；任务 3 的依赖声明与任务 5 的就绪检查。 |

## 当前已核实的事实与需验证的假设

- `plugins/vertical-plugins/equity-research/` 有 9 个技能、9 个命令；命令名称与技能名称不总相同（如 `/screen` → `idea-generation`，`/initiate` → `initiating-coverage`）。命令并非全是空壳：`commands/earnings.md` 另规定季度核实、数据时效、图表、引用及 DOCX 交付。
- `skills/initiating-coverage/SKILL.md` 是 **5 次分别发起、每步交付并等待用户继续** 的流程；产物依次为研究文档、Excel 模型、估值文档并更新模型、图表 ZIP、最终 DOCX。跨会话找到上一步产物是实际验收的一部分。
- `plugins/vertical-plugins/financial-analysis/` 实有 13 个技能；第一份方案漏了 `clean-data-xls`、`ppt-template-creator`、`skill-creator` 的目标归属。后续扩展 financial-analysis 时必须处理，不能沿用旧方案的"12 个/全部覆盖"计数。
- `plugins/vertical-plugins/financial-analysis/.mcp.json` **缺少 egnyte 后的逗号及末尾的一个闭合 `}`**。该缺陷在 D10 之后与本项目无直接关系（专家包不重用该文件），仅作为源仓库已知缺陷记录。
- CodeBuddy CLI 的现成市场插件与 WorkBuddy 专家不是同一个安装物。CodeBuddy 的研究插件、官方 DOCX/XLSX/PPTX 插件和 `$CODEBUDDY_ARTIFACTS` 路径只能作为参考，**不得**作为 WorkBuddy 已有能力的验收证据。
- **（2026-09-24 已核实）WorkBuddy 已原生内置腾讯文档官方 Office 技能，docx/xlsx/pptx 处理不构成能力缺口**，无需 CodeBuddy 市场插件、也无需裸写 `openpyxl`/`python-pptx` 脚本兜底。经读取本机 WorkBuddy 内置插件（v5.5.6）技能定义，以下技能开箱即用：`tencent-docs-routing`（本地 Office/WPS 文件总路由，任何 doc/sheet/slide 任务须最先加载）；`tencent-docx`（从零生成或整篇美化 .docx，自动封面目录；内含 `stock-research-report-expert` 证券研报专家与 doc-writer→doc-formatter→doc-converter 流水线）；`tencent-docs-sheet-generation`（无源表格时 openpyxl 从零建 .xlsx 并以 recalc 校验公式零错误）；`tencent-docs-sheetagent`（已有 .xlsx/.csv 的读写、分析、公式构造、图表、透视、清洗，委派 sheet-agent 子代理）；`tencent-local-office-edit`（经 editor_sdk/edsdk.py 实时打开、编辑、保存本机 docx/xlsx/pptx）；`tencent-pptx`（slidep 生成 .pptx，生成后编辑走 `tencent-local-office-edit`）；`pdf`/`pdfkit-py`（PDF 申报文件解析，附加）。依赖管理结论：openpyxl 由 excel-generation 技能幂等安装兜底、pptx 由托管 Node 环境预装 slidep，初版"不得假定 WorkBuddy 自动安装 `openpyxl`、`python-pptx`"的假设对上述技能不成立；硬约束是必须按各 SKILL.md 强制流程执行（路由优先、编辑前查 schema、sheetagent 原子委派），不得绕过技能直接操作文件。
- **（2026-09-25 已核实）WorkBuddy 内置 `expert-manager` 技能提供专家包全生命周期工具链**：`init_expert.py`、`validate_expert.py`、`register_expert.py`、`package_expert.py`、`batch_create.py`（专家规范 v2.0，支持 Agent 型与 Team 型）。专家在本机的固定安装目录为 `$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins`（默认 `~/.workbuddy/plugins/marketplaces/my-experts/plugins`，未初始化时按需创建）。展示字段规则与本方案假定一致：quickPrompts 与 tags 各固定 3 条。初版"仓库没有 `scripts/validate_expert.py`"的判断只对仓库成立——校验器由 WorkBuddy 宿主侧提供，无需自建；`.codebuddy-plugin/plugin.json` 包结构已在内置插件中确认。工具层成本低于初版预期，导出脚本仍需自写（技能目录复制与一致性比对不在 `expert-manager` 职责内）。
- **（2026-09-25 已核实）公开金融数据层已有现成插件，可覆盖九项任务的公开数据面**：finance-data 插件（v1.6.0）含 `westock-data`（A 股/港股/美股行情、财报、公告、事件、交易日历、宏观）、`westock-tool`（全市场条件/策略/标签/事件/排行筛选）、`neodata-financial-search`（研报评级、目标价、盈利预测、财报全文检索，130+ 工具）；另有 `wb-finance-skill` 金融场景总入口，提供禁编造、固定免责声明模板、指定历史周期不得改写、时效校验等红线，与本方案安全纪律同向（v1.2 起：其红线定位为底层纪律层，数据路由由优先级表决定，D6）。运行依赖：westock 需先执行技能自带 setup 安装 CLI；neodata 需云服务连接授权——两者均属"开发者本机可用 ≠ 市场用户可用"的依赖项，phase-1 本机已具备，phase-2 发布时再按普通用户路径实测声明。
- **（2026-09-25 已核实并连接实测）A 股/港股机构级数据面已由三个已连接连接器覆盖**：`wind-finance`（Wind Alice 万得，30+ 工具：股票财务/事件/公告/指数估值/EDB 宏观/条件选股，机构级口径）、`tdx-connector`（通达信，~15 工具：F10 深度资料 30 接口、券商一致预期 `yzyq`、港股财报回溯 2001 年、A 股/港股条件选股）、`neodata`（MCP 连接器形态，100+ 结构化工具：行情/财报/评级/事件/资金，A 股/港股/美股）。三者已在本机连接并各实测一次通过（港股实体检索、A 股公司档案、A 股日 K 行情；NeoData 返回自带休市状态标注与"省略中间历史行情禁止推断"防幻觉护栏），均走宿主连接器授权体系（非全局 MCP 开关、非打包凭据），专家包经 `dependencies.connectors` 声明即可。已知集成约束：三方技能与 `westock-data`/`neodata` skill/`wb-finance-skill` 各自称数据源权威——v1.2 起由 D6 优先级表定序解决；通达信工具带 MCP App 呈现流程（`presentationContextToken`），子代理委派时需按其约定处理。美股机构级数据面：仍无连接器（事实不变）——v1.2 起按 D10 设计性排除处理，不再作为待补缺口；Wind 订阅授权可得性问题随 phase-1 本机自用定位消解，phase-2 发布前按普通用户路径复测。
- **（2026-09-26 已核实，原 9 技能逐字核查）原技能为纯美股语境，宿主依赖低于预估**：9 技能及 references/assets 全文**零 A股/港股/CN 引用**；硬依赖集中在 `earnings-analysis` 与 `initiating-coverage`（SEC EDGAR 申报硬检查及链接验证、Bloomberg/FactSet 共识、10-K/10-Q/S-4/DEF 14A 申报类型、"10-year Treasury"无风险利率），其余 7 技能的供应商引用多为示例性（"verify against Bloomberg/FactSet"类）。`commands/earnings.md` 是唯一非薄路由命令（约 141 行完整 workflow：release 3 个月时效规则、transcript 日期匹配、beat/miss 逐项量化、8–12 图/8–12 页/3,000–5,000 英文词、ASCII 页面模板、8 项质检清单、DOCX+Summary 交付）。原技能未使用 AskUserQuestion/ToolSearch/ListConnectors 等宿主特有交互（纯对话式 ask-user），亦未引用 `$CODEBUDDY_ARTIFACTS`。重写工作量分层：**2 深**（earnings-analysis、initiating-coverage：数据源+申报类型+交付链全换）、**4 中**（catalyst-calendar、earnings-preview、morning-note、idea-generation：宏观事件表+市场惯例）、**3 轻**（thesis-tracker、sector-overview、model-update：文案与计量单位）。
- **（2026-09-25 已核实）图表 ZIP 产物无专门内置技能**：initiating-coverage Task 4 的多图打包落盘按"最小脚本"路径以最小 matplotlib 脚本补齐（可参考 `skills/initiating-coverage/references/task4-chart-generation.md` 既有 Python 图表代码本地化），属脚本级小工作量，不改变路线。

## 首期能力对照与测试入口

以下为九项业务任务；每项至少覆盖中文、英文各一次触发，以及一条数据不足或前置条件缺失的边界用例。产物规格按 D8 执行（全中文、A股五档评级、8–12 页锚、中文命名）。具体格式以源命令和技能为准，不凭表格摘要降低原要求。

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

## 任务 1：固定基线与真实数据前提（时间盒：一个工作节拍，D5）

**输入：**上表所列 9 个 `commands/*.md`、9 个 `skills/*/SKILL.md` 及 `initiating-coverage/references/`、`assets/`；原仓库 `plugins/agent-plugins/{earnings-reviewer,market-researcher}/` 仅供比对独立能力，不在这一步直接复制为 Team。

**产出：**将上表细化进 `workbuddy-experts/equity-research/README.md`：逐项列出源文件、输入追问、必需数据、来源/日期要求、产物格式、缺失数据时的安全行为、WorkBuddy 的测试问法；**等价映射表**（每处本地化改动的"原要求 → A股/港股等价物 → 残余缺口"三列，D4/D8，含 D10 概念等价映射与无对应物缺口清单）；固定一个可合法使用的财报样例（按 D9 三条件自动选定：动工时最近完整披露 + 研报覆盖充分 + Wind 可查），样例文件放在被 `.gitignore` 忽略的 `out/`，不放客户数据。另新建 `workbuddy-experts/equity-research/ACCEPTANCE.md` 验收留痕模板（D7）。

- [ ] 逐条阅读命令正文，标注技能描述中未覆盖的要求，尤其 `/earnings` 的时效、共识和报告清单。
- [ ] 对 `/initiate` 固定五个**不同用户请求**，记录每步需要读取的上一阶段文件和应停止的情形。
- [ ] 确定每项所需的公开源、商业源及机构源：按 D6 优先级表盘点（westock-data/westock-tool 公开面、wind-finance/tdx/neodata 机构面），超出能力域的查询另列数据源；美股机构级为设计性排除（D10），不再列为待补缺口。拿不到共识、实时筛选数据或历史模型时，先标记"未具备完整验收条件"，不要通过 `[UNSOURCED]` 兜底算通过。
- [ ] 记录原任务中人工确认与外部写入的边界；专家不会自行发布研究结论或写回机构系统。

**验收：**九项都有可复现的正例和缺失数据/前置条件反例；所有数据源的使用者、授权方式、日期口径清楚；等价映射表覆盖 2 深 + 4 中 + 3 轻全部九项；基线文档含 A股/港股市场锚定与任务形态等价声明（D2）；任务 1 裁决登记进 ACCEPTANCE.md。无可合法使用的原始样例时，本任务不能签署"功能等价"，但可继续进行内部技术试点。

## 任务 2：构建一个原生 Agent 型专家与可复现包

**文件：**

- 新建 `workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json`：专家标识、Agent/技能路径、双语展示、头像与依赖声明（`dependencies.connectors`：wind-finance、tdx-connector、neodata、westock-mcp；**无 `.mcp.json`、零美系声明**，D10）；展示字段按当前官方校验要求填写。
- 新建 `workbuddy-experts/equity-research/agents/equity-research.md`：研究入口、九项任务路由、证据与边界规则；**内嵌 D6 数据源优先级表、D10 美股请求红线、D8 产物规格纪律**；不照搬原 `tools:` 字段。
- 更新任务 1 创建的 `workbuddy-experts/equity-research/README.md` 并添加所需头像；九项命令对照及用户问法保存在 README，不往专家包加入未经目标环境认可的 `commands/`。
- 新建 `scripts/export_workbuddy_experts.py`：将上述专家定义和 `plugins/vertical-plugins/equity-research/skills/` 的 **9 个完整目录**复制到 `out/workbuddy-experts/equity-research/`，保留 `references/`、`assets/`，拒绝源技能缺失或目标路径不在包内。导出物不作为另一份手工编辑源。

- [ ] 先只用 `earnings` 做路由和产物试点；其他技能虽随包携带，但未验收前不在专家卡片中宣称九项全部可用。
- [ ] 为九项各写一个中文和一个英文触发问法；三条 quickPrompts 用于 M1 核心三件示例（提案文案，可改）：zh「分析 [公司] 最新季报，生成季报点评报告」/「对 [股票] 发起首次覆盖研究」/「用最新公告更新 [股票] 的估值模型」，en "Analyze [company]'s latest quarterly results and produce an earnings note" / "Initiate coverage on [stock]" / "Update the valuation model for [stock] with the latest announcements"；不视为其余六项的替代入口（专家规范 quickPrompts 固定 3 条，与本项一致）。
- [ ] `initiating-coverage` 的每步只按当前任务加载所需参考文件、核验前置产物并等待下一次用户请求；绝不自动越过五个任务间的人工关口。
- [ ] 导出后核对 9 个 `SKILL.md` 及其子资源、清单中每条相对路径，并在目标 WorkBuddy 环境按**实际安装位置**调用当前校验器。校验器不自建（2026-09-25 核实）：WorkBuddy 内置 `expert-manager` 技能自带 `validate_expert.py`（另有 `init_expert.py`/`register_expert.py`/`package_expert.py`），按其在宿主插件目录的实际路径调用；本仓库不新增校验脚本，旧方案中指向仓库内相对路径的调用方式作废。

**验收：**导出两次内容一致；来源与生成的技能文件一致；九种问法可路由到预期技能；请求 Task 3 而没有 Task 2 模型时明确阻止；目标客户端能召唤专家。此时只说明"包和路由通过"，不说明金融研究功能全部通过。任务 2 裁决登记进 ACCEPTANCE.md。

## 任务 3：接通必要数据且不扩大权限

**文件（v1.2 修订）：**`workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json` 的 `dependencies.connectors`（wind-finance、tdx-connector、neodata、westock-mcp）；**包内不创建 `.mcp.json`**——当前无需要包内声明的远程 MCP 服务（D10：美系全部移除，A股/港股数据全走宿主连接器授权体系），未来出现真实需要时再单独评估。v1.1 中"重用原 financial-analysis/.mcp.json（先修复语法）"与"比较同名 FactSet/LSEG 端点"两条款作废。

- [ ] 公开数据面优先复用已装 finance-data 插件（2026-09-25 核实）：`westock-data` 覆盖 `/earnings`、`/morning-note`、`/catalysts` 的行情/公告/事件/日历，`westock-tool` 覆盖 `/screen` 的全市场筛选，`neodata-financial-search` 覆盖共识的公开替代面（研报评级/目标价/盈利预测）。逐项实测覆盖面与口径，超出能力域的查询按任务 1 清单另列数据源；遵守其单一数据源纪律，不与其它来源混口径。westock CLI 安装、neodata 云服务连接属运行依赖，phase-1 本机已具备；phase-2 发布时按普通用户环境实测并在就绪材料中显式声明。
- [ ] 机构级数据面按 **D6 数据源优先级表（定稿，写入 agent 定义）** 接入：

| 数据域 | 首选 | 备选/降级 | 备注 |
| --- | --- | --- | --- |
| 机构级财务/公告/事件（A股/港股） | wind-finance | neodata → tdx F10 | 机构级口径基准 |
| 券商一致预期 | tdx `yzyq` | neodata 盈利预测（交叉校验） | 专功能接口 |
| 研报评级/目标价/研报全文 | neodata | — | 无重叠者 |
| 行情/K线/公告/交易日历（公开面） | westock-data | neodata 行情 | 公开基准 |
| 全市场筛选 | westock-tool | tdx / wind 条件选股 | 筛选主入口 |
| 宏观 EDB/宏观日历 | wind-finance | westock 宏观 | |
| 资金面/龙虎榜/两融 | neodata | westock | A股特色数据面 |

  纪律：同一任务同一指标**单源取数**，跨源必标注；`wb-finance-skill` 红线（禁编造、历史周期不得改写、免责声明）为底层纪律层全程适用、不抢路由；Wind 实测若有一致预期工具，再评估是否升档；Wind 不可用时的降级路径（neodata/tdx + 标注覆盖缺口）预先写明。**美股机构级 = 设计性排除（D10）**，不寻找 FactSet/LSEG 等价物。
- [ ] 为每个服务列出专家实际需要的工具、只读/写入动作、许可主体和用户侧认证方式；不一次性合并旧方案中的 30 多个服务。
- [ ] 以 `dependencies.connectors` 声明包级依赖，遵循 [WorkBuddy 官方说明](https://open.workbuddy.cn/docs/expert)用授权流程取得凭据，禁止打包真实密钥；不创建包内 `.mcp.json`，不改用仅在开发机有效的全局配置。
- [ ] **本机重装验证（D7，v1.2 替代"另一安装用户实测"）**：从导出包在本机重装、开新会话、仅保留包声明的依赖，实际连接并各调用一次必需工具，验证工具可见、结果时间与许可范围——防止开发机全局配置造成假阳性。"未参与开发的安装用户干净环境实测"整体移至 phase-2 发布门槛执行。不能连通的商业/机构连接器列为 phase-2 发布阻断项。
- [ ] 检查报告中每个用于计算或结论的关键数字能追到文件/链接、日期和单位；无共识时既不伪造 beat/miss，也不宣称完成机构级报告。

**验收：**必需服务真实返回数据；未授权用户不能越权读取；断网、空结果和权限拒绝均被明确标示且不会生成貌似完整的报告；本机重装验证通过；美股请求带 D10 标注。只修改开发机全局 `mcp.json` 或仅看到服务器"已配置"均不算通过。任务 3 裁决登记进 ACCEPTANCE.md。

## 任务 4：验证交付物和跨会话研究流程

**目标：**先在 WorkBuddy 运行 `earnings`，然后是 `model-update` 与 `initiate`（M1 核心三件，D3），最后跑完表中剩余六项（M2）。验收排进真实研究日程（D5）。文件生成使用 WorkBuddy 实测可用的原生能力；若不满足原要求，再按缺口引入最小脚本和依赖。

**已核实（2026-09-24，工具层就绪）：**本任务的 docx/xlsx/pptx 需求可由 WorkBuddy 原生内置技能满足，不需要 CodeBuddy 市场插件，也不需要裸脚本兜底。路由约定：DOCX 交付走 `tencent-docx`（研报类经其内置 `stock-research-report-expert`）；新建 Excel 模型走 `tencent-docs-sheet-generation`（openpyxl + recalc 公式校验）；更新既有模型走 `tencent-docs-sheetagent`（委派 sheet-agent 子代理，保留活公式/引用/假设）；本机 `.md`/`.xlsx`/`.zip`/`.docx` 的打开核对走 `tencent-local-office-edit`（edsdk.py）与宿主预览。图表 ZIP 无专门技能，按最小 matplotlib 脚本补齐（2026-09-25 核实；可参考 task4-chart-generation.md 既有代码本地化）。注意口径：以上仅证明"工具就绪"，不等于"产物达标"；未经端到端实测前不得宣称文件交付能力验收通过。

- [ ] 用有明确来源和使用权的财报完成 earnings：验证指定季度、共识来源/缺口、数据表、图表、引文与下载后可打开的 DOCX；对比原 `commands/earnings.md` 的质量清单。**产物规格按 D8 核对**：全中文（含图表标签）、A股五档评级 + CNY 目标价（数据不满足不输出、标缺口）、8–12 页锚、中文命名（`[公司]_[年]Q[季]_季报点评.docx`）、字体走 tencent-docx 内置模板；等价映射表逐条对照无静默删除。若数据条件不齐，改为标注"公开数据摘要"试点而非完整版 earnings。DOCX 生成经 `tencent-docx`（研报体量走其内置 `stock-research-report-expert`，默认常规点评档）。
- [ ] 更新既有 Excel 模型：打开文件检查公式仍可计算、引用不断链、假设和变动出处保留；静态数字表不算替代模型。更新动作经 `tencent-docs-sheetagent` 委派 sheet-agent 子代理执行，不得以静态表覆盖公式区。
- [ ] 逐次执行 initiate Task 1–5，期间退出并重新进入会话，提供先前产物路径；Task 3 缺 Task 2、Task 5 缺图表时必须停止而非生成占位报告。下载、打开 `.md`、`.xlsx`、`.zip`、`.docx` 并核对内容。产物路由：`.md`/`.docx` 走 `tencent-docx`，新建 `.xlsx` 模型走 `tencent-docs-sheet-generation`，更新模型走 `tencent-docs-sheetagent`，图表 ZIP 走最小 matplotlib 脚本，打开核验走 `tencent-local-office-edit`。
- [ ] 对筛选、催化剂、晨会纪要、预览、行业及论点任务，按能力对照表检查数据覆盖、时效、出处和二次更新；至少试一次错误股票代码、历史季度、空结果、无权限、相互矛盾的来源，**及美股个股请求（验证 D10 公开面 + 标注行为）**。

**验收：**九项各有原任务要求的真实结果和负例处理，跨轮产物可恢复；无来源数字不得进入结论。报告的评级、价格目标或投资建议在真实数据/人工审核条件不满足时不能由模型凭空补全。每项裁决登记进 ACCEPTANCE.md（D7）。

## 任务 5：发布就绪检查（v1.2 降级；市场提交移 phase-2）

- [ ] 用目标 WorkBuddy 版本实际认可的校验及注册流程安装导出包，校验与注册经 WorkBuddy 内置 `expert-manager` 技能的 `validate_expert.py`/`register_expert.py`（或目标版本实际认可的等价流程）完成；记录 WorkBuddy 版本、校验器版本、专家包版本和校验结果。`~/.workbuddy/plugins/marketplaces/my-experts/`（未初始化时由 `expert-manager` 按需创建）用于本机验收，**不是公开市场上架证明**；该目录是运行时安装位置，不违反"单一来源"约束——源仍在仓库，经导出脚本复制注册。
- [ ] **合规预检（发布就绪材料，不阻塞 phase-1 使用）**：核对所使用的品牌、开源许可、合作方内容、数据再分发条款及研究免责声明；含金融数据依赖的专家包无公开上架先例，合规审查周期按未知风险预留。若公开市场不允许该数据或内容的发布，phase-2 改为获准的私有分发范围，不绕开权限。
- [ ] **依赖路径文档化**：确认专家包不依赖开发机全局配置或绝对路径；westock CLI、neodata 云服务等公开数据依赖对普通用户有明确、可复现的安装/授权路径说明。
- [ ] **版本纪律**：修改技能、权限或连接器后提高包版本并重做受影响的验收；工作流完成（ACCEPTANCE.md）与市场审核为两个独立状态。

**phase-2 发布门槛（从本任务移出，届时执行）：**未参与开发的安装用户在干净环境完成安装、逐项连接授权、九项任务、文件下载与重新进入会话；按 WorkBuddy 开放平台当时提交流程提交包并记录审核结果。发布判据：专家卡片只列已通过的工作流；九项未全部通过前不使用"原二级市场插件全功能迁移""功能无降级"等表述；用户能拿到产物、能看到缺失数据说明，且市场安装者具备与开发者相同的授权连接路径。

**phase-1 完成判据：**九项任务全部按任务 4 验收通过并登记 ACCEPTANCE.md（即 D3 的 9/9 口径），本机重装验证（任务 3）与发布就绪检查（本任务前三项）通过。

## 后续领域的复用边界

二级市场全部通过后，再分别评估 `financial-analysis`、`investment-banking`、`private-equity`、`fund-admin`、`operations`、partner-built 和顾问场景；不默认一个原插件就是一个专家，也不默认既有 10 个 Agent 都应升级为 Team。扩展 `financial-analysis` 时显式处理未被旧 16 专家映射覆盖的 `clean-data-xls`、`ppt-template-creator`、`skill-creator`；工具层（2026-09-24 核实）中 `clean-data-xls` 对应 WorkBuddy 内置 `tencent-docs-sheetagent`（表格清洗/整理），`ppt-template-creator` 对应 `tencent-pptx`（生成后编辑走 `tencent-local-office-edit`），迁移时按同一路由验收，无需另建文件脚本。**美系 MCP 移除原则（D10）同样适用于后续所有领域：专家包零美系服务器声明。**顾问场景需另做原 `AskUserQuestion`、`ToolSearch`、`ListConnectors` 等交互/连接发现机制的等价验证（2026-09-26 核实：equity-research 九技能未使用这些机制，但不代表其他插件没有）；不能套用二级市场单专家的验收结论。Microsoft 365 和 CMA 保持本方案范围外。

## 自检清单（方案执行完毕时填写）

- [ ] 范围、九项对照、每项宣称一致；无已宣称但未通过的任务。
- [ ] 专家包技能副本与源技能一致；**包内无 `.mcp.json`、零美系声明（D10）**；未打包真实凭据。
- [ ] 本机重装验证与开发环境取数、文件下载、跨轮接续能力一致（第二用户实测为 phase-2 复核项）。
- [ ] 公开数据工具链（westock CLI 安装、neodata 云服务连接）与内置 Office 技能的可用路径已验证并按发布就绪材料声明。
- [ ] 无订阅、无权限、数据过期、来源冲突、缺前置文件、美股请求（D10 标注）时都有明确停止/降级标识，而非伪造完整结果。
- [ ] 工作流完成（ACCEPTANCE.md）与市场审核（phase-2）为**两个独立状态**，有对应的记录。

**参考资料：**[WorkBuddy 专家包规范](https://open.workbuddy.cn/docs/expert) · [技能包规范](https://open.workbuddy.cn/docs/skill) · [连接器接入说明](https://open.workbuddy.cn/docs/connector)。
