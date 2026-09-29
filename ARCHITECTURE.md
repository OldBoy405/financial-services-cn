---
id: financial-services-architecture
type: ARCHITECTURE
title: Financial Services Plugins 架构地图
status: living
owner: Ray
created: 2026-09-27
updated: 2026-09-27
---

# ARCHITECTURE.md — Financial Services Plugins

> 本文档记录本仓库变化慢的边界、依赖方向与可检查的不变量；具体技能行为以源文件为准。

## 1. 鸟瞰（Bird's Eye View）

本仓库维护金融行业的 Claude 插件、具名 Agent 插件及 Managed Agent cookbook；WorkBuddy 本地化是以原技能源为输入的独立交付面，不等于原插件的安装方式。市场清单中的六个 vertical 插件与十个具名 Agent 插件是两种结构，不是十六个可直接复制的 WorkBuddy Agent。

核心数据流：`plugins/vertical-plugins/*/skills/` → 同步到具名 Agent 的捆绑技能 → 插件市场或 cookbook 装配；其他宿主的分发物必须从源生成，而非反向改写源。

## 2. 入口点（Entry Points）

| 想理解… | 从这里开始 |
|---|---|
| 仓库编辑与检查纪律 | `CLAUDE.md`、`scripts/check.py` |
| 插件目录与来源 | `.claude-plugin/marketplace.json` |
| 股票研究入口与方法论 | `plugins/vertical-plugins/equity-research/commands/`、`skills/` |
| 具名 Agent 的装配 | `plugins/agent-plugins/earnings-reviewer/agents/earnings-reviewer.md`、`managed-agent-cookbooks/earnings-reviewer/agent.yaml` |
| 捆绑技能同步 | `scripts/sync-agent-skills.py` |

## 3. 代码地图（Code Map）

### `plugins/vertical-plugins/`

按行业组织原插件、命令、技能与插件元数据；`equity-research` 的任务入口与技能正文从这里阅读。

**架构不变量**：要修改可在具名 Agent 中复用的技能正文，先修改 vertical 源，再运行同步脚本；不反向编辑捆绑副本。

### `plugins/agent-plugins/`

具名 Agent 的定义和所需技能副本；这些副本不是另一套独立的源技能正文。对没有 vertical 源的特殊捆绑技能遵守 `.vendored-only` 约定。

### `managed-agent-cookbooks/`

Managed Agent 的系统文件、技能引用与子代理清单；这是独立装配面，不是 WorkBuddy 专家包。

### `scripts/`、`.claude-plugin/`

脚本校验引用、同步技能及处理既有交付；市场清单给出插件来源路径。`claude-for-msft-365-install/` 是另一条安装工具链。

## 4. 分层与依赖方向

```text
宿主装配（marketplace / named agents / cookbooks / 新增分发面）
                  ↓ 引用或导出
vertical-plugins 的技能与命令源
                  ↓
独立的引用素材与产物模板（references / assets）
```

规则：各装配面引用或复制原源；不通过修改生成物、捆绑副本或被忽略的构建目录来定义新的权威技能行为。cookbook 可以装配具名 Agent，但不使 cookbook 变成技能源。

## 5. 硬不变量（Invariants）

违反下列任意一条即为 bug；需要改变时先修订本文档。

1. **单一技能正文**：有 vertical 源的具名 Agent 技能副本必须能由 `scripts/sync-agent-skills.py` 重建；无源副本必须明确标记 `.vendored-only`。（核查：同步后运行 `python scripts/check.py`，比较改动范围。）
2. **引用有效**：市场清单插件来源、cookbook 的 `system.file`、`skills.path/from_plugin` 与子代理清单必须指向存在的对象。（核查：`python scripts/check.py`。）
3. **生成物不是源**：`out/` 中的产物不作为唯一的可版本化验收证据或手工编辑的技能正文。（核查：`.gitignore`、源码与交付记录。）

## 6. 刻意不做（Negative Space）

| 不做什么 | 为什么 | 何时重新考虑 |
|---|---|---|
| 把全部具名 Agent 或 cookbook 拼成一个 Team 以交付单一 WorkBuddy 专家 | 与单 Agent 入口及原有两种装配面不符 | 有独立的 Team 需求和验收时 |
| 把宿主专用连接器配置或私有凭据复制到通用技能正文 | 授权与配置属于宿主侧，不应随源技能或导出包泄露 | 宿主提供经过验证的分发契约时 |

## 7. 横切关注点（Cross-Cutting Concerns）

- **错误处理**：同步脚本在缺 vertical 源时报告并非零退出；校验脚本累积问题并非零退出。新导出路径须对缺文件、非法路径、部分包失败给出可核查的拒绝结果。
- **测试**：`python scripts/check.py` 检查清单 JSON/YAML、引用及捆绑技能漂移；新交付面另以自身验收记录保存导出一致性和目标宿主验证，不拿仓库静态检查代替宿主验证。
- **可观测性**：以脚本的退出码/报告及版本化验收记录定位失败；`out/` 的临时内容不能单独证明验收。
- **配置**：插件市场、具名 Agent、cookbook 各依自己的清单；不要把宿主私有配置作为跨宿主安装前提。

## 8. 本文档的维护规则

- 顶层模块、依赖方向或硬不变量改变，以及正式否决/采纳新的装配方式时修订本文档。
- 普通技能文案与资源变更不触发架构文档改写；架构级变更先经过设计评审。
- 技术设计评审对照 §4、§5、§6；本文档首稿随 CR-2026-001 的 SDD 评审和架构审批一起确认。
