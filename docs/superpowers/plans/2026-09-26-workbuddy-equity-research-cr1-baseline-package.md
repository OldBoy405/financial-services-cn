# CR1 需求｜基线与专家包

**阶段：**phase-1／原任务 1–2。**目的：**把源仓库九项任务逐条转为 A股/港股等价验收项，产出可从源重建、在目标 WorkBuddy 本机安装并正确路由的**单一 Agent** 专家包。本 CR 只验收基线、包与路由，不验收任何一项真实研究能力。

## 范围

1. **冻结基线。**记录原仓库实际 HEAD，按该 HEAD 创建 baseline tag（建议 `baseline/upstream-fca3cc8`，不得假定哈希不变），在 `workbuddy/main` 开展本地化；保留现有 16 个专家的原始结构。核查 `plugins/vertical-plugins/equity-research/` 下九个 `commands/*.md`、九个 `skills/*/SKILL.md`，并查 `connectors/`、`.mcp.json` 等相关数据源引用。确认原任务的入口映射，不按文件名臆测：

   | 旧命令 | 专家技能 | 旧命令 | 专家技能 | 旧命令 | 专家技能 |
   | --- | --- | --- | --- | --- | --- |
   | `/earnings` | `earnings-analysis` | `/initiate` | `initiating-coverage` | `/model-update` | `model-update` |
   | `/screen` | `idea-generation` | `/catalysts` | `catalyst-calendar` | `/morning-note` | `morning-note` |
   | `/earnings-preview` | `earnings-preview` | `/sector` | `sector-overview` | `/thesis` | `thesis-tracker` |

2. **等价映射。**在 `workbuddy-experts/equity-research/README.md` 建立旧命令/技能→A股、港股数据或机制→保留的行为/产物→缺口→验收方法的逐项对照，逐项写明输入追问、必需数据、日期/来源、产物和安全行为；核查 `initiating-coverage/references/`、`assets/` 与原 `plugins/agent-plugins/{earnings-reviewer,market-researcher}/` 的可复用能力（不复制成 Team）。尤其核对 `/earnings` 命令独有的发布后三个月时效、transcript 日期、beat/miss 量化、8–12 图、8–12 页、英文篇幅、八项质检、引文、DOCX+Summary；`initiating-coverage` 的 Task 1–5 是**五次分别发起、每步等待用户**的请求，而非自动连跑。A股五档评级及 CNY 目标价以充分数据为前提；中文交付（含图表标签）、8–12 页锚、中文文件名等列入验收模板。两融、增减持、NMPA、限售解禁、业绩预告/快报、央行/LPR/国常会、盘后披露+次日反应各有显式映射；options-implied move、盘前盘后价格序列无等价物时记缺口，不造数据。英文长度约束等与中文产物不兼容的旧指标，应记录等价的内容/质量验收口径，不可直接抹去；不得自行对外发布研究结论或写回机构系统。
3. **固定样例与模板。**用“最近完整披露＋研报覆盖充分＋Wind 可查”三个条件选择可合法使用的样例财报，登记来源、日期、证券代码及选取理由，不预设公司；样例文件放在被 `.gitignore` 忽略的 `out/`，不得放客户数据。在 `workbuddy-experts/equity-research/ACCEPTANCE.md` 为九项建立独立记录位：日期、CN/EN 测试问法、来源与版本、文件/链接、正例结果、反例结果、裁决人和“待测/通过/不通过/需重测”状态；另记基线与包的裁决。此时所有未实际测试的能力保持**待测**。
4. **Agent 与本地化。**保持源技能为唯一可编辑的技能正文；在根目录 `CUSTOM.md` 记录每处 WorkBuddy 本地化、映射和上游增量合并规则，本地化文件有 `WB-CUSTOM` 标记；按仓库 `CLAUDE.md` 执行必要的技能同步与检查。把美元、SEC、EDGAR、欧美财报/货币假设改为相应 A股/港股问题与来源，保留停止/追问/产物语义。单 Agent 的定义明确：先确认证券代码+交易所、研究日期/季度、数据时效、授权、来源和口径，再选择九项技能；底层 `wb-finance-skill` 负责禁止编造、历史周期、时效及免责声明，不代替数据域路由。数据域静态路由顺序写入 Agent，供 CR2 真实验证：机构财务/公告/事件 `wind-finance`→`neodata`→`tdx-connector` F10；券商一致预期 `tdx-connector` `yzyq`→`neodata` 盈利预测（须审查口径）；研报评级/目标价/全文 `neodata`（无默认等价备选）；公开行情/K线/公告/日历 `westock-data`→`neodata`；筛选 `westock-tool`→`tdx-connector`/`wind-finance`；宏观 `wind-finance`→`westock-data`；资金/龙虎榜/两融 `neodata`→`westock-data`（标缺口）。同一任务同一指标单源，跨源标注。美股个股走公开面并标明无美系机构数据；不能假装机构研究能力。
5. **可重建的专家包。**仓库源目录为 `workbuddy-experts/equity-research/`：`.codebuddy-plugin/plugin.json`、`agents/equity-research.md`、`README.md`、封面等；`scripts/export_workbuddy_experts.py` 从 `plugins/vertical-plugins/equity-research/skills/` 复制**九个完整技能目录**（含 references/assets），连同专家定义导出到 `out/workbuddy-experts/equity-research/`。导出物只供分发/安装，不作为第二份手工编辑源；缺源技能或相对路径逃出包时导出须失败。`plugin.json` 按目标 WorkBuddy 校验规则声明单 Agent、九项技能、各三条 quickPrompts/tags；三条 quickPrompts 分别示例 `earnings`、`initiate`、`model-update`，不是其余六项验收替代；`dependencies.connectors` 声明 `wind-finance`、`tdx-connector`、`neodata`、`westock-mcp`（实际标识以目标版本校验为准，冲突不得猜测替换）。不把未验收的九项全部宣称为已可用，不往包里加入未经平台认可的 `commands/`、旧 `tools:` 字段、`.mcp.json`、真实凭据或美系 MCP 声明。分发包必须自足，不依赖开发机绝对路径、全局私配或 CodeBuddy 市场插件。按目标机 `expert-manager` 的 init/validate/register 等实际认可流程验证，不自建校验器；先以 earnings 做产物试点，但本 CR 只裁决路由/包，不签产物达标。

## 交付物

- 已记录 HEAD/tag/分支的基线记录；九项旧命令与技能逐条等价映射表（含未等价缺口）、固定样例与可核查来源。
- 根目录 `CUSTOM.md` 和已打标的本地化改动；`workbuddy-experts/equity-research/README.md`、`.codebuddy-plugin/plugin.json`、Agent、封面，及可重复运行的导出脚本与 `out/workbuddy-experts/equity-research/` 中九个完整技能目录副本。
- `workbuddy-experts/equity-research/ACCEPTANCE.md` 九项验收模板；包校验、安装及 CN/EN 路由测试记录（与研究验收记录分开）。

## 验收标准

- 能从记录的源版本重跑导出；九个完整技能目录（包括 references/assets）与当前源一致，重复导出不产生未解释的差异；包中所有相对路径合法，目标 WorkBuddy 版本通过实际校验并可本机安装/召唤。记录客户端/校验器/包版本和安装步骤。
- 九项 CN/EN 自然语言请求各能选择预期技能；含歧义时要求澄清；三个 M1 quickPrompts 能启动对应路径。`initiate` 在缺 Task 2 模型时请求 Task 3 必须停止，且不能自动越过五次人工关口。该检查只证明**路由与前置守卫**，不可填“研究通过”。
- 对照表覆盖九项旧命令及命令额外约束；映射项有接受、明确缺口或待验标签，无静默删除。固定样例满足三条件且有使用权；`ACCEPTANCE.md` 九项均已建位，未测项仍标待测。
- 静态检查与包文件核对：无 `.mcp.json`、美系 MCP 声明、真实凭据、开发机绝对路径；Agent 有单源、时效、追问、无权限停/降级和美股公开面标注规则。**这里不声称规则在真实取数时已奏效。**

## 不包含／交接条件

不包含真实取数与许可核验、九项研究内容或 DOCX/XLSX 的端到端合格判定、非开发者干净环境安装、公开上架。向 CR2 交接的**已验收产物**是可重建且已本机安装/正确路由的包、九项等价映射、样例和验收模板；不得把“声明了连接器”说成“连接器已授权”。若基线/导出未通过，CR2 可以准备取数方案，但不能把包可用当成前提。
