# CUSTOM.md — financial-services-cn 二开台账

本文件记录 `workbuddy/main` 相对 [anthropics/financial-services](https://github.com/anthropics/financial-services) 的定制与合并责任；任务实施细节见 [WorkBuddy 二级市场研究专家方案](docs/superpowers/plans/2026-09-25-workbuddy-equity-research.md)。每次合并前核对下表，每次新增、修改或退役定制时更新同一行；新定制追加稳定 ID `#N`，不重排旧号。

## 当前状态（2026-09-26）

- `upstream/main`、本地及 `origin/main`：`574ed36`。`main` 仅作上游镜像；`origin` 为 `OldBoy405/financial-services-cn`（推送仓），`upstream` 为 Anthropic（按约定只拉取，不向其推送）。
- `workbuddy/main` 与 `origin/workbuddy/main`：`1c14ced`，自上游基线有 3 个本地提交（`b9b99d1`、`5686c0d`、`1c14ced`）。
- 不移动的起始标签：`baseline/upstream-574ed36`，指向纯上游 `574ed36`；用 `git diff baseline/upstream-574ed36..workbuddy/main` 看累计二开。当前定制边界则用 `git diff main...workbuddy/main` 核对。
- 本轮验证：`python scripts/check.py` → 82 个文件、0 问题；`python scripts/version_bump.py --check --base main` → OK。Windows 本机 `python3` 是不可用的 WindowsApps 存根，运行仓库脚本用 `python`；其他环境用实际可运行的 `python3`。

## 合并冲突总则

执行 `git merge main` 时，**先看《定制明细》，再按上游新代码定位定制**；没有文本冲突也照此核对。

- **台账先行**：每个已实施的 fork 改动都要有稳定 ID、路径和验证方式。合并前逐行核查；发现未登记的改动先补台账，再判断是否保留，不能靠 Git 的冲突列表代替核查。
- **以上游为基底**：上游重构、重命名或移动文件时，先理解新入口，再把仍必要的本地增量贴回新位置；不能直接整文件取“ours”或“theirs”。若上游提供了**满足相同约束**的能力，优先采用上游实现，删除本地重复部分并在原台账行注明已上游化；不等价的 A股/港股行为仍需保留并验收。
- **新增与摘除分开处理**：纯新增的 WorkBuddy 文件原则上保留；若上游出现同名功能，先比对语义再选真源。未来按方案摘除美系 MCP 属于**减法定制**：上游更新后须在新基底重新检查和执行摘除，不能按“双方都保留”处理；当前尚未实施，不把它记为已完成。
- **源优先于副本**：`plugins/vertical-plugins/*/skills/` 是普通技能的真源；冲突先改源，再运行 `scripts/sync-agent-skills.py`，不要手工修 agent bundle。三个带 `.vendored-only` 的 meeting-prep 技能是上游删除真源后的例外；若上游恢复源，先比对内容和调用关系，再取消例外。`out/` 中的导出物不作为可手工合并的源。
- **挂钩逐一保留或明确退役**：后续本地化技能中的 `WB-CUSTOM`、等价映射和数据源/安全边界，按上游新结构逐处复核；没有标记的文档、脚本和清单按下表路径核对。上游改变宿主逻辑时，不机械保留失效的挂钩；在台账行记录替代或退役原因。
- **验收后才能推送**：无冲突合并也须跑 `check.py`、插件版本检查和每行所列最小验证；上游已有失败先在纯上游水位复现并登记，不用它掩盖本地回归。验证未通过就在 `workbuddy/main` 修复并记录阻塞，不强推覆盖远端。

## 定期同步流程

**节奏：每双周至少检查一次上游；遇上游 release、安全修复或本地改写对应文件，提前检查。** 由维护者触发并记录结果；本仓库未配置自动定时任务，不能把未执行的检查记为已同步。

1. **清场并预检**：在干净工作区运行 `git status --short`、`git fetch upstream`、`git log --oneline main..upstream/main`、`git diff --name-status main..upstream/main`。逐项对照下表，特别看上游是否删除、重命名或接管了本地触及的路径；无新提交也在《同步记录》记检查日期与结果。
2. **维护纯净镜像**：`git switch main && git merge --ff-only upstream/main`。无法快进即停下核查，不能在 `main` 制造二开提交或强推。再执行 `git switch workbuddy/main && git merge main`；冲突以上游新结构为基底，逐行恢复仍需要的本地增量。无冲突也逐行核对：Git 的干净合并不等于功能正确。
3. **按真源处理**：改 `plugins/vertical-plugins/*/skills/` 时才运行 `python scripts/sync-agent-skills.py`，让 agent bundle 从真源重建；`meeting-prep-agent` 的三个 `.vendored-only` 目录是源被删后的例外，除非上游恢复源，否则它们自身是唯一副本。若上游已提供等价能力，采用上游实现并从台账中标记本地实现“已上游化/退役”，而非长期保留两套。WorkBuddy 专家包的导出物将来只从源技能生成，不手工合并 `out/`。
4. **逐项验收**：运行 `python scripts/check.py` 和 `python scripts/version_bump.py --check --base main`；如上游抬高了同一插件的版本，确保 fork 的 `plugin.json` 版本高于 `main`，修正后复验。核对 `git diff main...workbuddy/main --name-status` 与下表；涉及新增专家包时再按方案运行导出、目标 WorkBuddy 校验及相应验收（这些工具/产物尚未建成，不把它们计为本轮通过）。合并落树后检查原有 fork 专属路径是否仍在，不只依赖脚本通过。
5. **留痕再推送**：在本文件《同步记录》写上游 SHA、冲突与处置、验证结果，提交 `workbuddy/main` 的后续改动。确认 `git status --short` 为空后推送 `git push origin main workbuddy/main`。若验证失败，保留分支供修复，不推送未验收的 `workbuddy/main`；在记录中明确阻塞项。

适配纪律：在原技能正文做本地化时，按方案保留 `WB-CUSTOM` 标记、等价映射与原要求对照；文档、脚本、插件清单中的改动则靠本台账的**路径 + 验证**核对，不能用标记数量替代逐文件复核。新增能力优先放新文件，与上游源隔离；对源技能的改写必须逐条审查上游更新。

## 定制明细（稳定 ID）

以下各项均已在 `workbuddy/main`，截至 `1c14ced`；`#1` 包含本台账自身（本文件建立后待提交）。每行“合并注意”既用于预判冲突，也用于无冲突的复核。

| # | 位置 | 本地改动 / 用途 | 合并注意与最小验证 |
|---|---|---|---|
| #1 | `CUSTOM.md`、`codebuddy-financial-research-adaptation-plan.md`、`workbuddy-expert-migration.md`、`docs/superpowers/plans/2026-09-24-workbuddy-equity-research.md`、`docs/superpowers/plans/2026-09-25-workbuddy-equity-research.md` | 增加 fork 台账、迁移调研与二级市场研究方案；后两份计划有版本先后，执行以 09-25 的 v1.2 为准。 | 上游重组插件时更新调研中的路径与本台账水位；不要把计划写成已实施。验证：逐路径存在，核对方案的未做项。 |
| #2 | `.gitignore` | 忽略本地代理记忆 `.workbuddy/`；`out/` 原已忽略。 | 保留忽略规则，不把本地记忆、凭据或生成产物推到 origin。验证：`git check-ignore .workbuddy/memory/2026-09-26.md`。 |
| #3 | `.gitattributes`、`.githooks/pre-commit` | Bash hook / `*.sh` 强制 LF；hook 选择真正能执行的 `python3` 或 `python`，避开 WindowsApps 存根。 | 上游改 hook 时合并其逻辑和本地 Windows 兜底；维持 LF。验证：`bash .githooks/pre-commit`、`git check-attr eol -- .githooks/pre-commit`。 |
| #4 | `scripts/check.py` | 所有文本输入显式 UTF-8，输出以 UTF-8 写入；无 vertical 源的 bundle 仅在有 `.vendored-only` 标记时豁免。源一旦出现仍比较漂移。 | 不能把任意孤儿 bundle 自动放行；上游恢复源时按真源比对。验证：`python scripts/check.py`；无标记孤儿应报错。 |
| #5 | `scripts/sync-agent-skills.py` | 无源但有 `.vendored-only` 的 bundle 跳过同步；其他无源 bundle 仍失败。 | 上游若恢复源，应按真源复制并移除过时标记。验证：有源技能变动后运行同步脚本，再运行 `check.py`。 |
| #6 | `plugins/agent-plugins/meeting-prep-agent/skills/{client-report,client-review,investment-proposal}/.vendored-only`、同插件 `.claude-plugin/plugin.json` | 上游 #349 删除 `wealth-management` vertical 真源但保留这三个 agent bundle；标记唯一副本以保留 agent 工作流，插件版本按仓库规则从 0.1.1 升至 0.1.2。 | 不直接删除这些技能来消警；上游恢复/替代功能时重新判定真源。验证：`check.py` + `version_bump.py --check --base main`，核对 agent 仍引用三项技能。 |
| #7 | `scripts/version_bump.py` | 文本读写显式 UTF-8，写回保留非 ASCII 描述；Git 路径改 POSIX 分隔符，修复 Windows 下基线 `git show <ref>:<path>` 静默失败导致从不 bump。 | 上游改版本比较或基线策略时保留跨平台路径正确性。验证：`python scripts/version_bump.py --check --base main`；在暂存插件变更时确认 hook 只 bump 一次。 |
| #8 | `scripts/validate.py`、`scripts/deploy-managed-agent.sh` | JSON/YAML 和部署脚本内嵌 Python 读文件显式 UTF-8，避免 Windows ANSI 默认解码。 | 上游增加新的文件读取点时沿用显式编码；部署验证需在具备 `jq` 与凭据的环境另测，当前不宣称已部署。验证：`check.py`，有管理代理变更时再跑对应校验/部署 dry run。 |

新增二开：先在此表追加路径、原因和可运行的最小验收，再合并上游；同一事项改路径时更新原行，ID 保持不变。删除/上游化时保留原行并注明日期及替代版本，避免下轮误恢复。

## 同步记录（新记录追加在顶部）

| 日期 | 上游水位 | 结果 / 验证 |
|---|---|---|
| 2026-09-26 | `upstream/main` @ `574ed36`（从 `fca3cc8` 前进 1 提交） | `main` 快进并推送 origin；上游仅删除 `claude-for-financial-advisors/`（24 文件），与本地原有跟踪改动零冲突。打 `baseline/upstream-574ed36`；建并推送 `workbuddy/main`（前三个本地提交）。`check.py` 82/82、0 问题；`sync-agent-skills.py` 同步 48 个有源 bundle；版本校验通过。本地 `.workbuddy/` 保留、未提交。 |

## 上游既有失败基线（不能冒充本 fork 新回归）

在**未修改的** `574ed36` 上，`PYTHONUTF8=1 python scripts/check.py` 曾报 3 个 `bundled-skill` 无 vertical 源：`meeting-prep-agent/skills/{client-report,client-review,investment-proposal}`。未设置 UTF-8 的 Windows cp936 环境还会在读取 YAML 时抛 `UnicodeDecodeError`。fork 由 #3–#8 修复，当前 `check.py` 为 0 问题，**无待豁免失败**。以后上游变化若出现新失败，应在干净上游水位复现、记录 SHA 和症状，再决定是上游缺陷还是本地回归；不能只因“上游也失败”就跳过 fork 验证。

## 尚未实施（别把计划算进台账完成项）

- 二级市场研究 9 技能的 A股/港股本地化尚未动工：深改 `earnings-analysis`、`initiating-coverage`；中改 `catalyst-calendar`、`earnings-preview`、`morning-note`、`idea-generation`；轻改 `thesis-tracker`、`sector-overview`、`model-update`。动工后逐技能追加台账行，保留原要求与等价映射；先改 vertical 真源再同步 bundle。
- `workbuddy-experts/equity-research/`、导出脚本、目标环境验收/发布尚未完成；具体门禁与数据源边界以 09-25 方案 v1.2 为准。
- 双周同步是维护节奏，不是已部署的定时器；每轮以《同步记录》中的实测结果为准。
