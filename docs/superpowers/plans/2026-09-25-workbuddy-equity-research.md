# WorkBuddy 二级市场研究专家｜phase-1 总览

> **文档状态：**原实施方案保留为总览；不表示专家已安装、数据已接通、研究任务已验收或已上架。原方案 2026-09-24 初版、2026-09-25 v1.1、2026-09-26 v1.2；本次仅按交付边界拆成四份 phase-1 CR 需求文档。实施与验收以对应 CR 文档的具体标准为准。原方案中尚未经端到端实测的能力，仍是待验证前提。

## 目标与边界

- **目标：**基于原仓库 `plugins/vertical-plugins/equity-research/` 的九项任务，构建一个 WorkBuddy Agent 型二级市场研究专家；A股为主、港股为辅，phase-1 仅本机自用。原技能源是方法论的单一来源：仓库 `workbuddy-experts/equity-research/` 保存 `.codebuddy-plugin/plugin.json`、Agent 定义与展示资料，导出脚本把九个完整技能目录复制到 `out/workbuddy-experts/equity-research/`，导出物不作第二份手工源。初始化、校验、注册和打包复用目标 WorkBuddy 内置 `expert-manager`，不自建校验器。
- **等价口径：**任务形态等价，即保留原任务的追问、时效校验、产物清单和负例处理；不承诺相同市场覆盖、数据源或 slash 命令语法。自然语言路由可替代 slash 入口，不能静默删除原命令额外的要求。
- **范围内：**九项任务对应的九个技能、取数与授权、模型及文档交付、跨会话续作、九项真实任务验收和本机重装。
- **范围外：**Microsoft 365 命令/供应流程、CMA 子代理及编排、原仓库美系 MCP 服务器（如 FactSet、LSEG、Daloopa、Morningstar、S&P Global 等）、公开市场提交与审核、其他金融领域。美股机构级数据是**设计性排除**，不是“以后补齐”的 phase-1 缺口。
- **成功定义：**M1 三项通过可作为内部中间成果；只有九项均经真实任务正例和负例验收并在 `workbuddy-experts/equity-research/ACCEPTANCE.md` 留痕，才可称 phase-1 二级市场研究功能迁移完成。包可安装、路由正确、工具配置存在、单次连接实测，均不能替代研究能力验收；phase-1 完成不等于公开上架。

## 决策台账 D1–D10（统一维护）

| 编号 | 决策 | 约束 |
| --- | --- | --- |
| D1 | 终局定位 | phase-1 本机自用；任务 5 仅为发布就绪检查；专家市场上架归 phase-2 独立立项。 |
| D2 | 市场锚定 | A股为主、港股为辅；等价是任务形态等价（追问、时效、产物、负例），不是市场或数据源覆盖等价。 |
| D3 | 两级里程碑 | M1 = `earnings`、`initiate`、`model-update` 真实可用；M2 = 其余六项；“迁移完成”只在 9/9 留痕通过后使用。 |
| D4 | 本地化与上游 | 深度本地化可改数据源/环境引用，必须逐条保留行为要求；每处改动登记等价映射表和根目录 `CUSTOM.md`。动工前按当时 HEAD 打 baseline tag（建议名 `baseline/upstream-fca3cc8`，以实际 HEAD 为准），走 `workbuddy/main` 分支；上游按 `CUSTOM.md` 总则增量合并，不采取永久分叉口径。本地化文件加 `WB-CUSTOM` 标记；改动后按仓库 `CLAUDE.md` 执行技能同步与检查。 |
| D5 | 节奏 | 基线工作时间盒为一个工作节拍；真实研究任务排入日常工作完成验收，反例可边跑边补，不因时间盒而签署未满足的功能等价。 |
| D6 | 数据源纪律 | 同一任务同一指标单源取数，跨源标注来源和口径；数据域的首选/降级顺序见下表。`wb-finance-skill` 是禁编造、时效、历史周期、免责声明等底层纪律层，不代替数据路由。 |
| D7 | 验收留痕 | `ACCEPTANCE.md` 每项记录日期、测试问法、产物链接、负例结果和裁决；用户是唯一裁决人。phase-1 只做本机重装；第二安装用户干净环境复测归 phase-2。 |
| D8 | 等价映射硬规则 | A股评级五档：买入/增持/中性/减持/卖出，目标价以 CNY 标注；无充分数据则不输出评级/目标价并标缺口。两融↔short interest、增减持↔insider windows、NMPA↔FDA、限售解禁↔lockup、业绩预告/快报↔whisper/guidance、央行/LPR/国常会↔Fed/FOMC、盘后披露+次日反映↔pre-market/after-hours。无对应物（options-implied move、盘前盘后价格序列）明确标缺口，禁止发明替代指标。产物全中文（含图表标签）、8–12 页锚、中文文件名（如 `[公司]_[年]Q[季]_季报点评.docx`），字体用 `tencent-docx` 内置模板。 |
| D9 | 固定样例 | 动工时按“最近完整披露＋研报覆盖充分＋Wind 可查”三条件选定可合法使用的财报样例，条件写入基线，不预先指定公司。 |
| D10 | 美系 MCP 移除 | 专家包零美系 MCP 声明、无包内 `.mcp.json`。美股个股请求不拒答，只走 `westock-data`/`neodata` 公开面，并显式标注“本专家不接入美系机构数据源，以下基于公开数据”；不得把公开数据冒充机构级共识或估值。 |

**D6 数据域顺序（在 Agent 定义中落地，由数据 CR 实测）：**

| 数据域 | 首选 | 备选/降级 |
| --- | --- | --- |
| A股/港股机构级财务、公告、事件 | `wind-finance` | `neodata` → `tdx-connector` F10 |
| 券商一致预期 | `tdx-connector` `yzyq` | `neodata` 盈利预测，需标明是否可作同口径对照 |
| 研报评级、目标价、全文 | `neodata` | 无可默认为等价的备选 |
| 公开行情、K 线、公告、交易日历 | `westock-data` | `neodata` 行情 |
| 全市场筛选 | `westock-tool` | `tdx-connector` / `wind-finance` 条件选股；标注覆盖范围 |
| 宏观 EDB、宏观日历 | `wind-finance` | `westock-data` 宏观数据 |
| 资金面、龙虎榜、两融 | `neodata` | `westock-data`，标注能力缺口 |

## 四个 phase-1 CR：交付顺序与验收闸门

| 顺序 | 需求文档 | 包含任务 | 通过后能宣称什么／下游门槛 |
| --- | --- | --- | --- |
| CR1 基线与专家包 | [2026-09-26-workbuddy-equity-research-cr1-baseline-package.md](2026-09-26-workbuddy-equity-research-cr1-baseline-package.md) | 原任务 1–2：九项基线、等价映射、固定样例、验收模板、单 Agent、技能导出与路由 | 基线与可复现包已验收、目标 WorkBuddy 可安装且九项可正确路由；**不得宣称研究能力通过**。CR2 接收可安装导出包、已验收的路由和基线。 |
| CR2 数据与授权 | [2026-09-26-workbuddy-equity-research-cr2-data-authorization.md](2026-09-26-workbuddy-equity-research-cr2-data-authorization.md) | 原任务 3：公开/机构源、许可、单源与降级、本机重装 | 必需服务真实取数与许可验证通过，无权限/空结果不伪装完整报告。CR3 接收已验收的**任务所需**数据域可用性与安全降级，不仅是“已配置连接器”。 |
| CR3 研究主链 M1 | [2026-09-26-workbuddy-equity-research-cr3-research-chain-m1.md](2026-09-26-workbuddy-equity-research-cr3-research-chain-m1.md) | 原任务 4 前半：`earnings`、`initiate`、`model-update`，文件交付与跨会话接续 | 三项经真实研究任务验收并留痕，可称 M1 内部可用；不能宣称 9/9。CR4 接收三项已验收结果及对应产物。 |
| CR4 其余能力与收口 | [2026-09-26-workbuddy-equity-research-cr4-remaining-readiness.md](2026-09-26-workbuddy-equity-research-cr4-remaining-readiness.md) | 原任务 4 后半六项＋原任务 5 发布就绪检查 | 六项通过，连同仍有效的 M1 记录累计 **9/9 留痕通过**，本机自用收口；不等于市场审核通过。 |

逐 CR 评审、实施、裁决；上游未通过时下游不得将其视为既成能力。若后续修改技能、数据权限或连接器导致前次验收失效，先重做受影响的用例，再计算 9/9。

## 共同安全条件与已知前提

- 不在仓库、专家包、样例或演示素材存放真实 Token、客户数据或内部 URL 凭据；商业/内部数据按安装用户各自授权。权限由连接器/服务端执行，不靠 Agent 提示词保证。无需或无权访问的指标必须标注缺口；来源矛盾须显式说明，不以 `[UNSOURCED]` 算通过。
- 指定历史季度按指定期间核对；有歧义代码先确认证券及交易所；报告中的关键数字追到可合法使用的文件/链接、日期、单位。没有旧模型/图表时停在相应步骤；禁止占位报告、占位估值或静态表冒充模型。
- 原方案曾逐项核查：源仓库九个命令与九个技能不总同名（例如 `/screen`→`idea-generation`、`/initiate`→`initiating-coverage`）；原技能整体是美股语境，`earnings-analysis`、`initiating-coverage` 需深度本地化，其余四项中度、三项轻度调整；`commands/earnings.md` 有独立的发布后三个月时效、图表数量、引用、DOCX+Summary 等约束；`initiating-coverage` 分五次用户请求，图表 ZIP 预期需最小 matplotlib 脚本。源技能仍需在实施时重新逐条核对，不用本段代替基线验收。
- 原方案记录的目标机工具前提：WorkBuddy 内置 `expert-manager` 的 init/validate/register/package 脚本和腾讯文档 Office 技能（文件先经 `tencent-docs-routing`，再走 `tencent-docx`、`tencent-docs-sheet-generation`、`tencent-docs-sheetagent`、`tencent-local-office-edit` 等）；公开面 `finance-data` 的 `westock-data`、`westock-tool`、`neodata-financial-search`；机构面 `wind-finance`、`tdx-connector`、`neodata` 曾各连接实测一次。**这些是方案记录的工具/单次连接事实，不是对本项目研究任务或重装验收通过的声明。**具体字段、连接器标识、许可及版本以目标客户端实施实测为准，不能拿 CodeBuddy CLI 插件或旧开发机全局配置当 WorkBuddy 验收证据。

## phase-2 入口（暂不启动）

条件成熟后**另立第 5 个 CR 并写独立需求文档**：品牌、开源/合作方内容及数据再分发许可与合规确认；未参与开发的非开发者在干净环境完成安装、逐一授权、九项复测、产物下载及跨会话重入；再按届时 WorkBuddy 市场流程提交并记录审核。若数据/内容不允许公开分发，改为获准的私有分发范围，不绕过权限。phase-1 的发布就绪预检不等于上述许可、复测或审核已通过。

其他金融领域（`financial-analysis`、`investment-banking`、`private-equity`、`fund-admin`、`operations` 等）不并入本批 CR；未来另行盘点，不能套用二级市场 9/9 结论。扩展 `financial-analysis` 时须单独处理旧方案漏列的 `clean-data-xls`、`ppt-template-creator`、`skill-creator`，而非沿用“12 个技能/全部覆盖”的计数。

**规范入口：**[WorkBuddy 专家包](https://open.workbuddy.cn/docs/expert) · [技能](https://open.workbuddy.cn/docs/skill) · [连接器](https://open.workbuddy.cn/docs/connector)。
