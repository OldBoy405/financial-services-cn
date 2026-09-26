# financial-services 项目接入 WorkBuddy 专家库 — 改造分析与实施方案

> 分析对象：`C:\Users\GOBAO\WorkBuddy\Worktrees\financial-services\main-e3167e12`
> 目标格式：WorkBuddy 专家包规范 v2.0（权威来源为 expert-manager 的 `init_expert.py` / `validate_expert.py` / `register_expert.py` 脚本）
> 约束：**原有功能不降级** —— 每一项改造均附功能验证方式。

---

## 0. 结论摘要

1. **整体可行性**：该项目（Anthropic `claude-for-financial-services` 插件市场）可整体、近无损地迁移为 WorkBuddy 专家库。19 个已注册插件中，建议转化为 **16 个专家**（10 个 Agent 型 + 1 个 Team 型 + 3 个纵向技能专家 + 2 个合作方专家），1 个插件（claude-for-msft-365-install）不建议转化。
2. **三类硬性阻断**（不改则校验直接失败，详见 §4/§5）：
   - 全部 16 个 Agent MD 的 frontmatter 含 `tools:` 字段（专家规范明令禁止），advisor 插件另含 `model:` 字段；
   - 各插件含 `commands/`（50 个斜杠命令）与 `hooks/`（4 个空 hooks.json）目录，专家包明令禁止；
   - `financial-analysis/.mcp.json` 存在 **JSON 语法错误**（egnyte 条目后缺逗号），任何自动合并都会在解析期失败。
3. **最大功能降级风险**：10 个命名 Agent 中有 **7 个依赖仓库内未声明的企业内部 MCP 服务器**（capiq / crm / internal-gl / subledger / screening / portfolio / nav），其 URL 需要机构侧补配到 `~/.workbuddy/mcp.json`，否则数据获取链路断裂（各 Agent 凭 `[UNSOURCED]` 标记与 EDGAR 回退兜底，属真实降级）。
4. **斜杠命令（50 个）**：专家包无 slash command 机制，但其中 41 个命令与同名 Skill 一一对应、其余 9 个亦有对应 Skill，**功能由 Skill 承载而非丢失**；需把命令的触发问法回填到 Skill description 与 Agent MD 工作流中。
5. **Managed Agent（CMA）部署链**（agent.yaml / subagents / steering / deploy 脚本）是 Claude Managed Agents API 专属能力，WorkBuddy 运行时没有对应物，**不迁移不构成专家能力降级**；如需保留子代理分解结构，可二期将 Agent 升级为 Team 型（成本较高，列为可选项）。

---

## 1. 项目现状盘点

### 1.1 目录结构与资产清单

```
financial-services/
├── .claude-plugin/marketplace.json      # 市场清单：注册 19 个插件
├── .githooks/pre-commit + .github/workflows/  # version-bump / validate / secret-scan CI
├── CLAUDE.md · README.md · LICENSE (Apache-2.0) · .gitignore
├── plugins/
│   ├── agent-plugins/                   # 10 个命名 Agent（自包含：agents/*.md + skills/ 副本）
│   │   ├── pitch-agent · meeting-prep-agent · market-researcher · earnings-reviewer
│   │   ├── model-builder · valuation-reviewer · gl-reconciler · month-end-closer
│   │   └── statement-auditor · kyc-screener
│   ├── vertical-plugins/                # 6 个纵向插件（48 个技能源 + 33 个命令 + 4 个空 hooks）
│   │   ├── financial-analysis (核心, 12 技能 + 12 MCP + 7 命令)
│   │   ├── investment-banking (9 技能 + 7 命令, .mcp.json 为空 {})
│   │   ├── equity-research (9 技能 + 9 命令)
│   │   ├── private-equity (10 技能 + 10 命令)
│   │   ├── fund-admin (6 技能) · operations (2 技能)
│   └── partner-built/                   # lseg (8 技能+8 命令+1 MCP) · spglobal (3 技能+1 MCP)
├── claude-for-financial-advisors/       # 顶层插件：6 个叶子 Agent + 8 技能 + 23 MCP（未注册进 marketplace.json）
├── claude-for-msft-365-install/         # 独立管理工具：9 命令 + 1 技能 + py/ps1/sh 脚本（Azure/Graph 供应）
├── managed-agent-cookbooks/             # 10 份 CMA 菜谱：agent.yaml + 3 个 subagents/*.yaml + steering + README
└── scripts/                             # check.py · validate.py · sync-agent-skills.py · deploy-managed-agent.sh
                                         # orchestrate.py · version_bump.py · test-cookbooks.sh
```

**资产计数**：Agent 插件 10 个（内嵌 51 份技能副本，约 40 个唯一技能）；纵向/合作方/advisor 唯一技能共 **67 个**；斜杠命令 **50 个**；MCP 连接器条目 **37 条（去重后 30 个唯一服务器）**；CMA 子代理 **30 个**；Python/Shell 脚本 7 个仓库级 + 若干技能内脚本。

### 1.2 核心功能矩阵

| 功能层 | Claude 侧机制 | 说明 |
|---|---|---|
| 端到端工作流 | `plugins/agent-plugins/<slug>/agents/<slug>.md`（系统提示词） | 10 个：pitch / meeting-prep / market-research / earnings-review / model-build / valuation / gl-recon / month-end / statement-audit / kyc-screen |
| 领域知识方法 | `skills/<name>/SKILL.md`（自动触发） | 建模（DCF/comps/LBO/3-statement）、研报（earnings、initiation、morning-note）、PE（ sourcing→IC memo→portfolio）、fund admin（recon/accrual/NAV）、KYC 规则引擎、deck QC、Excel/PPT 产出 |
| 显式动作 | `commands/*.md`（`/comps`、`/dcf`、`/ic-memo`…） | 50 个，绝大多数是"加载同名 Skill + 参数化工作流"的薄封装 |
| 数据连接 | 各插件 `.mcp.json`（`type: http` + `url`） | 30 个唯一服务器；另有 7 个企业内部服务器仅在 Agent 正文以 `mcp__<name>__*` 引用、未声明 URL |
| 多代理分解 | `managed-agent-cookbooks/<slug>/`（agent.yaml + 3 leaf subagents + output_schema） | Claude Managed Agents API（Research Preview）专属 |
| 仓库治理 | check.py（lint/引用解析/漂移检测/PS1 ASCII 门禁）+ pre-commit 版本自增 + CI | 不随专家迁移（见 §4-H） |
| 顾问插件 | advisor 插件 6 个叶子 Agent 被 Skill 调度（`claude-for-financial-advisors:compliance-lookup`） | 需改写为 WorkBuddy Team 调度协议 |

### 1.3 依赖清单

| 依赖 | 用途 | 迁移影响 |
|---|---|---|
| Claude Cowork / Claude Code 运行时 | 插件发现、命令、agent 调度 | 替换为 WorkBuddy 专家运行时 |
| Claude Managed Agents API (`/v1/agents`) | CMA 部署（deploy-managed-agent.sh、agent.yaml） | WorkBuddy 无对应物，不迁移（非专家能力） |
| MCP 服务器（http）30 个 | 全部数据来源 | 合并进 `~/.workbuddy/mcp.json` |
| 企业内部 MCP 7 个（capiq/crm/internal-gl/subledger/screening/portfolio/nav） | Agent 数据链路 | 需机构补配 URL，**P0 风险** |
| Python 3 + pyyaml | check.py、orchestrate.py、技能脚本 | 技能脚本（validate_dcf.py、extract_numbers.py 等）在 WorkBuddy 托管 Python 3.13 下运行；openpyxl/requests（dcf-model/requirements.txt）需装进托管 venv |
| jq + python3 | deploy-managed-agent.sh | 随 CMA 链不迁移 |
| `mcp__office__excel_*` / `mcp__office__powerpoint_*` | xlsx-author / pptx-author 技能的 Cowork 模式分支 | WorkBuddy 无此连接器；该技能的 headless 产文件分支正是 WorkBuddy 原生模式，需文字适配 |

---

## 2. 目标规范：WorkBuddy 专家包 v2.0

### 2.1 权威结构（以可执行脚本为准）

```
my-experts/plugins/<expert-name>/          # 必须位于 $WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins
├── .codebuddy-plugin/plugin.json          # ⚠️ 权威目录名（validate 仅认 .codebuddy-plugin；SKILL.md 行文中的 .workbuddy-plugin 仅 register 接受）
├── agents/<agentName>.md                  # frontmatter: name/description/displayName/profession/maxTurns（+可选 skills[]）
├── skills/<skill-name>/SKILL.md           # 与 Claude 技能格式兼容（name+description frontmatter）
├── avatars/                               # 512×512 PNG/JPG ≤500KB
├── README.md
└── settings.json                          # 仅 Team 型（{"agent": "<team>-team-lead"}）
```

**明令禁止**：`commands/`、`hooks/`、`.lsp.json`；`agents/`、`skills/`、`bin/`、`avatars/` 不得放进 `.codebuddy-plugin/` 内；frontmatter 不得含 `tools:` 字段；专家不得放在专家目录之外（validate 硬校验）。

### 2.2 plugin.json 关键字段（相对 Claude 侧的增量）

| 字段 | 要求 | 本项目适配值 |
|---|---|---|
| `expertType` | agent / team | 10 个 Agent 插件→`agent`；advisor→`team` |
| `agentName` | = agents/ 下 MD 文件名，有业务语义，禁 `team-lead` 通用名 | 沿用插件 slug |
| `displayName` / `profession` | {en, zh} | 需新编（详见 §4-I） |
| `displayDescription` | {en, zh}，**中文 40–50 字** | 需新编 |
| `categoryId` | 固定 12 类 | **08-FinanceInvestment**（kyc-screener 可议 11-SecurityCompliance，需用户确认） |
| `tags` / `quickPrompts` | **各恰好 3 个** {en,zh}；`defaultInitPrompt` = quickPrompts[0] | 需新编 |
| `plugin` | = name | 同 name |
| `version` | 语义化 | 建议 1.0.0（源为 0.1.1） |

### 2.3 本机落地环境（已核实）

- 专家目录 `~/.workbuddy/plugins/marketplaces/my-experts/` **尚不存在**，register_expert.py 会自动创建（marketplace.json 初始 `{"name":"my-experts", ...}`）。
- `~/.workbuddy/mcp.json` **已存在**，含 1 个 stdio 服务器 `plugin_context-mode_context-mode`。合并连接器时必须**读后写、保留现有条目**，不得覆盖。
- 本机 connectors-marketplace 已有大量中文数据连接器（ifind / dzh / gildata / datayes 等），可作为付费西方数据源的可选补充（增强项，非必须）。

---

## 3. 总体映射方案（插件 → 专家拓扑）

| # | 源 | 目标专家 | expertType | 说明 |
|---|---|---|---|---|
| 1–10 | `plugins/agent-plugins/<slug>` ×10 | 同名 10 个专家 | agent | 1:1 映射；skills/ 副本随包迁移 |
| 11 | `claude-for-financial-advisors` | `financial-advisor` | team | 主理人 + 6 成员（compliance-scan/lookup、statement-extract、holdings-sanity、titling-compare、source-extract）+ settings.json |
| 12 | `plugins/vertical-plugins/equity-research` | `equity-research` | agent | 承载 4 个未被 Agent 捆绑的纵向技能（catalyst-calendar、initiating-coverage、thesis-tracker、morning-note）+ 9 命令语义 |
| 13 | `plugins/vertical-plugins/investment-banking` | `investment-banking` | agent | 承载 8 个未捆绑技能（buyer-list、cim-builder、datapack-builder、deal-tracker、merger-model、process-letter、strip-profile、teaser） |
| 14 | `plugins/vertical-plugins/private-equity` | `private-equity` | agent | 承载 7 个未捆绑技能（ai-readiness、dd-checklist、dd-meeting-prep、deal-sourcing、unit-economics、value-creation-plan、deal-screening） |
| 15 | `plugins/partner-built/lseg` | `lseg` | agent | 8 技能 + 1 连接器（URL 与核心插件冲突，见 §5） |
| 16 | `plugins/partner-built/spglobal` | `sp-global` | agent | 3 技能 + 1 连接器 |
| — | `claude-for-msft-365-install` | **不转化** | — | Azure/Graph 管理员供应工具，需外部凭据与管理员同意流；属 IT 运维而非专家对话场景（理由见 §4-H） |

**备选拓扑**（供决策）：
- 精简版 11 专家（10 Agent + 1 Team）：纵向技能就近挂到最相关 Agent 专家（如 initiating-coverage → market-researcher）。代价：19 个纵向技能的归属变模糊，插件边界消失。
- 完整版 20 专家：1:1 含 msft-365。不推荐。
- Team 升级版：10 个 Agent 各自升级为 Team（cookbook 的 3 个子代理转为成员）。保留 CMA 子代理结构，但需 40 张头像、30 份成员 MD、10 套 SOP，且 `callable_agents` 本是 Research Preview。建议二期可选。

---

## 4. 改造项清单（A–K）

> 每项格式：**现状 → 改造要点 → 验证方式**。

### A. 目录与清单骨架

- **现状**：`<plugin>/.claude-plugin/plugin.json` + `agents/` `skills/` `commands/` `hooks/` `.mcp.json`。
- **改造要点**：
  1. 整目录拷贝到 `my-experts/plugins/<name>/`，**删除** `.claude-plugin/`、`commands/`、`hooks/`、`.mcp.json`、`.claude/`（investment-banking 的 `.claude/*.local.md.example`）、`.gitignore`；
  2. 新建 `.codebuddy-plugin/plugin.json`（**不要**用 `.workbuddy-plugin`，validate_expert.py 只认前者）；
  3. 目录名 = plugin.json `name`，全 kebab-case（源名全部合规）；
  4. Team 型（financial-advisor）另需 `settings.json` 与 N+1 头像。
- **验证方式**：`python3 scripts/validate_expert.py <expert-dir>` 退出码 0；对目录树做 diff 复查无 `commands/`、`hooks/`、`.mcp.json` 残留；专家目录路径位于 `.../my-experts/plugins/` 下（否则 validate 报错拒绝）。

### B. plugin.json 字段补全

- **现状**：极简清单（name/version/description/author）。
- **改造要点**：按 §2.2 表补 `expertType`、`agentName`、`agents`、`skills`（列出全部捆绑技能路径）、展示六件套（displayName/profession/displayDescription/categoryId/tags×3/quickPrompts×3）、`defaultInitPrompt`=quickPrompts[0]、`plugin`=name。中文 displayDescription 控制在 40–50 字。各 Agent 专家把 bundled skills 逐一列入（validate 会逐条检查 `skills/<x>/SKILL.md` 存在）。
- **验证方式**：validate_expert.py 字段校验全过；register_expert.py 无 `[TODO]` 残留报错；专家中心卡片六项展示（名字/花名/类型/行业分类/能力介绍/擅长领域/试试这样问我）齐全。

### C. Agent MD frontmatter 改造（16 个 Agent + 6 个 advisor 叶子）

- **现状**：`name` + `description`（+`tools:` ×16，advisor 另有 `model: haiku` ×5）。`tools:` 中含 `mcp__capiq__*` 等 MCP 命名空间声明。
- **改造要点**：
  1. **删除全部 `tools:` 行**（validate 硬失败项；WorkBuddy 工具由系统统一分配）；
  2. **删除 `model:` 行**（无对应机制；副作用：advisor 叶子 Agent 从 haiku 变为默认模型，成本/时延变化需知会用户，属可接受降级）；
  3. 增加 `displayName{en,zh}`、`profession{en,zh}`、`maxTurns`。长流程 Agent（pitch-agent 9 步、model-builder 多模型）建议 `maxTurns: 150`，默认 50 可能截断；
  4. **正文一律不动**（保功能核心）；`description` 保留英文原文（激活判定用）；可选加 `skills: [...]` 预加载关键技能；
  5. `name` 必须与文件名一致（源已满足）。
- **验证方式**：validate_expert.py 无 "must NOT contain 'tools'" 错误；逐专家用其描述中的典型问法触发（见 §6），确认激活路由正确且能正常读写文件（证 tools 删除后能力未受损）。

### D. 斜杠命令转化（50 个）

- **现状**：`commands/*.md`（frontmatter: description + argument-hint；正文多为"加载同名 Skill → 澄清问题 → 产出"）。分布：financial-analysis 7、equity-research 9、investment-banking 7、private-equity 10、lseg 8、msft-365 9。
- **改造要点**：
  1. 专家包无命令机制且禁 `commands/` 目录；**41/50 命令与同名 Skill 一一对应**（/comps→comps-analysis、/dcf→dcf-model、/lbo→lbo-model、/earnings→earnings-analysis、/ic-memo→ic-memo、/analyze-bond-rv→bond-relative-value…），其余 9 个亦有对应 Skill（/debug-model→audit-xls、/ppt-template→ppt-template-creator、/one-pager→strip-profile、/screen→idea-generation、/dd-prep→dd-meeting-prep、/portfolio→portfolio-monitoring、/source→deal-sourcing、/teaser→teaser、/buyer-list→buyer-list）——**功能由 Skill 承载，非丢失**；
  2. 把命令的触发问法与 `argument-hint` 语义回填到对应 Skill 的 `description` 触发词（含中文示例），保证自然语言提问能命中；
  3. quickPrompts 每专家仅 3 个，无法覆盖全部命令——接受该限制，靠 Skill description 触发兜底；
  4. msft-365 的 9 个命令随该插件不迁移。
- **验证方式**：维护"命令 → Skill"crosswalk 清单（附录 B 方法），对 50 个命令各取 1 条代表性自然语言 prompt 做冒烟测试；确认产出物与命令正文描述一致（格式、统计量、清单项）。

### E. Skills 打包（67 个唯一技能 + 51 份捆绑副本）

- **现状**：`skills/<name>/SKILL.md` + `references/` `scripts/` `templates/` `assets/`；frontmatter 为 name+description（与 WorkBuddy 技能格式兼容，无 tools/model 字段——已核实 0 处违规）。
- **改造要点**：
  1. 目录与正文**原样拷贝**（含 scripts/、requirements.txt、TROUBLESHOOTING.md）；
  2. `xlsx-author` / `pptx-author` 的正文含 Cowork 模式分支（`mcp__office__excel_*`）——WorkBuddy 无此连接器，将该分支文字改为"WorkBuddy 中直接以文件产物模式运行"（headless 分支本就是原生模式，**功能不降级**）；
  3. 副本保留保自包含（xlsx-author×9、audit-xls×7、pptx-author×4 等）；与 WorkBuddy 内置 office 技能（tencent-docx/tencent-pptx/sheet 系）分工需在验收时明确（触发词错开：内置偏"腾讯文档/编辑"，本仓偏"投行/PE 建模规范与审计"）；
  4. `skill-creator` 技能与 WorkBuddy 内置 `skill-creator` 同名——专家技能带插件命名空间前缀通常不硬冲突，但需验收验证无相互遮蔽；亦可直接从专家包中剔除（用内置的）；
  5. 技能脚本用 `#!/usr/bin/env python3`，托管 Python 3.13 可执行；`dcf-model/requirements.txt`（openpyxl、requests）需装入托管 venv；
  6. `compliance-scan.md` 依赖"调度方传绝对路径"读取 `references/sec-compliance-checklist.md`——Team 主理人的分发 prompt 必须携带该路径（见 G）。
- **验证方式**：每个能力域 1–2 条 description 匹配 prompt 做自动触发测试（见 §6）；`validate_dcf.py`、`extract_numbers.py` 实跑通过；Excel 产物抽查（活公式、蓝黑绿约定、无硬编码计算单元格）。

### F. MCP 连接器合并（37 条 → 30 个唯一服务器）

- **现状**：5 个 `.mcp.json`；`financial-analysis` 12 个（**第 46–47 行缺逗号，JSON 非法**）、`claude-for-financial-advisors` 23 个（含 salesforce/snowflake 两条 `"url": ""`）、lseg 1、spglobal 1、IB/PE 为 `{}`。
- **改造要点**：
  1. **先修复语法错误**（egnyte 后补逗号）——`scripts/check.py` 不校验 .mcp.json，属潜伏缺陷，合并脚本解析即会失败；
  2. 合并目标为 **`~/.workbuddy/mcp.json`**（已存在，含 context-mode stdio 服务器）——读后写、保留现有条目，`mcpServers` 下追加（http 与 stdio 形态可共存）；
  3. **保留原服务器键名**——Agent 正文以 `mcp__factset__*`、`mcp__daloopa__*` 等命名空间引用，键名即命名空间，改名即断链；
  4. 冲突裁决（详见附录 A）：`lseg`（`/lfa/mcp` vs `/lfa/mcp/server-cl`）、`factset`（`/mcp` vs `/content/v1`）、`sp-global` vs `spglobal`（同 URL 不同键）、`salesforce`/`snowflake` 空 URL（删除或留待用户补配）；
  5. **7 个未声明内部服务器**（capiq/crm/internal-gl/subledger/screening/portfolio/nav）需机构按实际 URL 补入 mcp.json；不补的后果按 Agent 分级：pitch-agent/meeting-prep（capiq/crm）、market-researcher/model-builder/earnings-reviewer（capiq/factset/daloopa）、gl-reconciler/month-end-closer（internal-gl/subledger）、kyc-screener（screening）、valuation-reviewer（portfolio）、statement-auditor（nav）——7/10 Agent 受影响；
  6. 决策点：连接器策略（全量 30 / 精简常用 12 / 以本机 connectors-marketplace 中文数据源补充）。
- **验证方式**：每个已配置服务器发起一次真实数据请求（如"从 Daloopa 拉 AAPL 最新 10-K 营收"），确认 `mcp__<key>__*` 工具可见且返回；对未配置服务器确认 Agent 走 `[UNSOURCED]` 标记或 EDGAR 回退而非报错崩溃；合并后原有 context-mode 服务器仍正常（`/ctx-stats` 可用）。

### G. Team 型映射（claude-for-financial-advisors → financial-advisor）

- **现状**：8 个 Skill 调度 6 个叶子 Agent（compliance-scan → compliance-lookup/statement-extract/holdings-sanity/titling-compare/source-extract 等），叶子 Agent frontmatter 含 model/tools（需按 C 处理）；23 个连接器（并入 F）。
- **改造要点**：
  1. 新建主理人 `agents/financial-advisor-team-lead.md`：按 team-spec 编写 SOP（intake→extract→sanity/compliance→compare→brief 的 Phase 串并行）、成员能力清单、单 Agent 直调路由表、团队协作铁律（TeamCreate→spawn→SendMessage）；
  2. 6 个成员 MD：删除 model/tools，补 displayName/profession/maxTurns，增加"**SendMessage 回传主理人**"段；
  3. `plugin.json`：`expertType: "team"`、`agentName: "financial-advisor-team-lead"`、`teamInfo{leadAgent, memberAgents[6]}`、`members[]`（含 role=lead 主理人）、`settings.json`；
  4. 改写 Skill 中的调度表述：`claude-for-financial-advisors:compliance-lookup` → WorkBuddy Agent 工具协议（`name`/`subagent_type` 传 MD 文件名）；compliance-scan 依赖的绝对路径由主理人分发 prompt 携带；
  5. 源仓库遗漏注意：advisor 插件**未注册**进 marketplace.json，转换时以目录为源，勿依赖市场清单。
- **验证方式**：端到端触发"对这封客户信做合规预检"→ 观察 TeamCreate→成员 spawn→SendMessage 回传→主理人汇总全链路；确认专业产出由成员输出（非主理人代写）；切换英文提问验证双语路由。

### H. 不迁移项与双源维护策略

- **不迁移**：
  - `claude-for-msft-365-install`：Azure 管理员同意/Graph 写入类外部动作、需凭据、含 .ps1（受 check.py 的纯 ASCII 门禁约束）——与专家对话式定位不符，保留原仓库即可；
  - `managed-agent-cookbooks/` + `scripts/`（deploy-managed-agent.sh、orchestrate.py、validate.py、test-cookbooks.sh）：CMA API 专属，WorkBuddy 无 `/v1/agents`；其中 subagent 的 `output_schema` 可作为 Team 成员 MD 的输出模板参考（知识保留，机制不保留）；
  - `.githooks` + `.github/workflows` + `version_bump.py` + `check.py` + `sync-agent-skills.py`：源仓库治理基建，继续服务 Claude 侧，与专家目录无交互。
- **双源维护策略**：以本仓库为唯一 source of truth；编写 `scripts/export_experts.py`（可复用 sync-agent-skills.py 的索引逻辑）**脚本化再生成**专家包，避免手改两份导致漂移；专家侧修改必须回流仓库。
- **验证方式**：转换后源仓库 `python3 scripts/check.py` 仍 OK；重跑 export 脚本生成物与已注册专家一致（diff 为空或仅展示字段差异）。

### I. 展示字段双语化

- **现状**：资产几乎全英文；专家上架要求全部展示字段 en+zh。
- **改造要点**：为 16 个专家新编 displayName、profession、displayDescription（中文 40–50 字）、tags×3、quickPrompts×3、defaultInitPrompt（=quickPrompts[0]）；Agent MD 正文可维持英文（专家能力以英文系统提示词运行），但 quickPrompts 建议中文化以贴合中文用户。
- **验证方式**：专家中心中/英切换展示完整无 `[TODO]`；中文提问路由与应答正常；displayDescription 中文字符数用脚本核对在 40–50 区间。

### J. 头像生成

- **改造要点**：15 个 Agent 专家 ×1 张 + Team（团队 1 + 主理人 1 + 成员 6）= 8 张，共 **23 张**；ImageGen `size=1024x1024`，落 `avatars/`；08-FinanceInvestment 背景色调"dark blue with gold accent"；团队头像需风格锚定词统一。
- **验证方式**：`avatars/` 文件存在且 plugin.json `avatar` 路径指向正确、单张 ≤500KB；专家中心头像渲染正常。

### K. 注册与版本

- **改造要点**：逐个 `python3 scripts/register_expert.py <expert-dir>`（校验 → 写入 `my-experts/.codebuddy-plugin/marketplace.json` → 写 `.created-by-session`）；`version` 语义化；**任何后续修改都必须重跑 register**（规范铁律）；`package_expert.py` 用于分享打包。
- **验证方式**：marketplace.json 含全部 16 条目；专家中心"我的专家"全部可见可启用；`validate_expert.py` 全量复跑退出码 0。

---

## 5. 兼容性风险与冲突点（按严重度）

### P0 — 不处理则校验失败或功能断裂

| # | 风险 | 影响 | 对策 |
|---|---|---|---|
| 1 | Agent MD frontmatter 含 `tools:`（16 处）与 `model:`（5 处） | validate_expert.py 硬失败 | §4-C 删除 |
| 2 | `commands/`、`hooks/` 目录存在 | validate "Forbidden directory" 硬失败 | §4-A 删除（hooks 全为空 `{"hooks":{}}`，删除零损失） |
| 3 | `financial-analysis/.mcp.json` JSON 语法错误（egnyte 后缺逗号） | 合并脚本解析失败；check.py 不覆盖 .mcp.json 故长期潜伏 | §4-F 先修复 |
| 4 | 7 个企业内部 MCP 服务器未声明 URL | 7/10 Agent 数据链路断裂（有 [UNSOURCED] 兜底，仍属真实降级） | §4-F 机构补配 URL |

### P1 — 需决策或验收期重点验证

| # | 风险 | 说明 | 对策 |
|---|---|---|---|
| 5 | `factset` 双 URL（`/mcp` vs `/content/v1`）、`lseg` 双 URL（`/lfa/mcp` vs `/lfa/mcp/server-cl`） | 同名键不同端点 | 附录 A 裁决表；建议主键沿用 core 插件 URL，次 URL 以别名键保留 |
| 6 | `sp-global`（core）与 `spglobal`（partner）同 URL 不同键 | 工具命名空间分裂，agent 正文引用 `sp-global` | 统一为 `sp-global`，`spglobal` 作为别名或剔除 |
| 7 | `skill-creator` 专家技能 vs WorkBuddy 内置 `skill-creator` | 潜在激活遮蔽 | 验收期专项验证；或从专家包剔除 |
| 8 | `xlsx-author`/`pptx-author` vs 内置 office 技能触发重叠 | 双技能抢触发 | description 触发词错开；README 写明分工 |
| 9 | 内置金融技能（wb-finance-skill / westock-data / westock-tool）与本专家技能同场 | 触发竞争 | 触发词错开；实测路由 |
| 10 | 双源漂移（repo 与 my-experts 两份） | 技能副本各自演化 | §4-H 脚本化再生成 |
| 11 | advisor 插件未在源 marketplace.json 注册 | 依赖市场清单的转换会漏掉它 | 以目录为源枚举 |

### P2 — 可接受降级 / 习惯迁移

| # | 风险 | 说明 | 对策 |
|---|---|---|---|
| 12 | `model: haiku` 丢失 | advisor 叶子 Agent 升为默认模型，成本上升 | 知会用户；可在使用观察后再评估 |
| 13 | maxTurns 默认 50 | pitch-agent 等 9 步长流程可能截断 | 显式调高至 150 |
| 14 | 50 个斜杠命令形态消失 | 用户习惯迁移成本 | quickPrompts + Skill description 触发词缓解；附录 B crosswalk 培训 |
| 15 | CMA 子代理结构不迁移 | 10×3 子代理分解在专家侧不存在（agent 型为单代理） | 二期可选 Team 升级；或依赖 Agent 自身长流程能力 |

---

## 6. 功能不降级验收矩阵

| 能力域 | 冒烟测试（代表性 prompt） | 期望结果 |
|---|---|---|
| pitch | "Build a pitch deck for CRWD exploring strategic alternatives" | xlsx（comps+precedents+DCF+LBO+足球场，**活公式**）+ pptx（图表绑定模型、deck QC 通过） |
| comps | "Run comps for MSFT vs peers" | 经营统计+估值倍数两张表，含 Max/75th/Median/25th/Min |
| dcf | "DCF for AAPL with WACC sensitivity" | `validate_dcf.py` 通过；敏感性表存在 |
| 3-statement / lbo | "3-statement model from these filings" / "LBO at market leverage" | 三表联动/来源与用途+回报敏感性 |
| earnings | "Update the model and draft a note from this transcript" | 模型更新 + note 草稿（结构符合 report-structure.md） |
| market research | "Industry overview + peer comps for cybersecurity" | sector-overview + comps + ideas shortlist |
| PE | "Screen this CIM" / "Draft an IC memo" / "IRR/MOIC sensitivity" | pass/fail+理由 / IC memo / 敏感性表 |
| fund admin | "Reconcile this GL export and trace breaks" / "Accruals + roll-forward + variance commentary" | 差异清单+签署路由 / 三件套产物 |
| KYC | "Screen this onboarding pack" | 规则引擎结果 + 缺口标记（screening MCP 未配时走降级路径并明示） |
| statement audit | "Audit this LP statement before distribution" | 差异标记 + 拦截项 |
| valuation | "Run the valuation template on this GP package and stage LP reporting" | 估值模板结果 + 暂存 LP 报告 |
| advisor team | "Prep for tomorrow's Smith family meeting" + "Compliance pre-check on this letter" | TeamCreate→成员产出→SendMessage→主理人汇总全链路；合规扫描逐条引用原文 |
| connectors | 每服务器一次真实取数 | `mcp__<key>__*` 可见、返回正确；未配置服务器走兜底不崩 |
| office 产物 | 打开全部 xlsx/pptx 产物 | 可打开、公式活、蓝黑绿约定、无硬编码计算单元格 |
| 激活路由 | 每专家 quickPrompts 逐条 | 命中正确专家，无跨专家误触发 |

---

## 7. 分阶段路线图

1. **Phase 0 — 阻断项修复（约 0.5 天）**：修复 `.mcp.json` 语法错误；确定附录 A 连接器冲突裁决；补齐 7 个内部 MCP URL 或明确降级清单。
2. **Phase 1 — 试点（约 2 天）**：转化 pitch-agent（Agent 型）与 financial-advisor（Team 型）两个专家，走通 init→填字段→frontmatter 改造→validate→register→冒烟全流程，沉淀转换规范。
3. **Phase 2 — 全量生成（约 3–5 天）**：编写 `scripts/export_experts.py` 脚本化生成其余 14 个专家；批量生成 23 张头像；完成全部双语展示字段。
4. **Phase 3 — 验收（约 2 天）**：跑 §6 全量验收矩阵；专家中心走查（展示、激活、双语）；源仓库 check.py 回归；文档化 crosswalk 与连接器台账。

---

## 附录 A：MCP 连接器冲突裁决表

| 服务器键 | financial-analysis | claude-for-financial-advisors | lseg | spglobal | 建议裁决 |
|---|---|---|---|---|---|
| daloopa | mcp.daloopa.com/server/mcp | 同 | — | — | 保留 1 条（同 URL） |
| morningstar | mcp.morningstar.com/mcp | 同 | — | — | 保留 1 条 |
| sp-global / spglobal | kfinance.kensho.com/integrations/mcp | 同 | — | kfinance.kensho.com/integrations/mcp（键名 spglobal） | 统一 `sp-global`，剔除 `spglobal` 别名 |
| factset | mcp.factset.com/mcp | mcp.factset.com/content/v1 | — | — | 主键 `factset` 用 core URL；`factset-content` 别名键保留另一 URL（agent 正文引用 factset） |
| moodys / mtnewswire / aiera / pitchbook / chronograph / egnyte | 有 | — | — | — | 原样保留 |
| box | mcp.box.com | 同 | — | — | 保留 1 条 |
| lseg | api.analytics.lseg.com/lfa/mcp | — | api.analytics.lseg.com/lfa/mcp/server-cl | — | 主键 `lseg` 用 core URL；lseg 插件URL 以别名键 `lseg-server-cl` 保留 |
| orion-advisor-solutions / wealth-com / wealthbox / addepar / tamarac / zocks / icapital / moneyguide / gmail / google-calendar / google-drive / microsoft-365 / dropbox / slack / blackrock / zoom | — | 有 | — | — | 随 financial-advisor 专家保留 |
| salesforce / snowflake | — | `"url": ""` **空** | — | — | 删除或待用户补配后加入 |
| capiq / crm / internal-gl / subledger / screening / portfolio / nav | **未声明**（仅 agent 正文 mcp__*__* 引用） | — | — | — | 机构按实际 URL 补入（P0） |

## 附录 B：命令 → 机制对照方法（50 个命令）

- **同名 Skill 一一对应（41 个）**：financial-analysis 7（comps/dcf/lbo/3-statement-model/competitive-analysis + debug-model→audit-xls、ppt-template→ppt-template-creator）；equity-research 9（earnings、earnings-preview、initiate、model-update、morning-note、screen→idea-generation、sector、thesis、catalysts）；investment-banking 7（one-pager→strip-profile、cim、teaser、buyer-list、merger-model、process-letter、deal-tracker）；private-equity 10（source、screen-deal、dd-checklist、dd-prep、unit-economics、returns、ic-memo、portfolio、value-creation、ai-readiness）；lseg 8（analyze-bond-rv、analyze-bond-basis、analyze-fx-carry、analyze-option-vol、analyze-swap-curve、macro-rates、research-equity、review-fi-portfolio）。
- **无对应 Skill（9 个）**：均属 msft-365（setup、bootstrap、consent、manifest、entra-app、access-policies、update-user-attrs、export-data、debug）——随该插件不迁移。
- 结论：迁移范围内命令能力 **100% 由 Skill 承接**；回填触发词后按自然语言提问验证（§6）。

## 附录 C：关键事实备查

- 专家清单权威目录为 `.codebuddy-plugin/plugin.json`（init 创建、validate 只认、register 兼容 `.workbuddy-plugin`；SKILL.md 行文与脚本不一致，**以脚本为准**）。
- 专家必须位于 `$WORKBUDDY_CONFIG_DIR/plugins/marketplaces/my-experts/plugins/<name>`（默认 `~/.workbuddy/...`），否则 validate 报错；本机该目录待 register 时自动创建。
- 本机 `~/.workbuddy/mcp.json` 已有 context-mode stdio 服务器，合并时保留。
- 源仓库 `scripts/check.py` 自装 git hooks 并 patch-bump 版本；专家包在仓库外，互不影响。
- 4 个 hooks.json 均为空（`{"hooks": {}}`），删除零损失。
- `.gitignore` 已忽略 `*.local.md`、`out/` 等；advisor/IB 的 `.local.md.example` 机构私有配置约定在专家侧无对应物，机构上下文建议写入 README 或 Skill references。
