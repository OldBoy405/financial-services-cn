# CR-2026-002 数据与授权 — 声明修正（G4）

一张固定表 `declarations.md#声明修正`（`DCL-NN`），列名与列序取 `tests/_evidence.py#TABLE_COLUMNS` 注册值。
本文件是 TASK-04 唯一写入面，G5（TASK-05）只逐条复验其闭合，不在此追加修正。

结论（由 `cmd-04` 机械断言，`cmd-05` 复验）：**本轮两行均为 `无需修正`，三处声明面零差异**；
该结论的成立条件是「目标机未实测出不符」，而 0.11.0 的目标校验本轮未执行（`reinstall.md#重装步骤/RIN-02`），
因此两行的依据都是**最近一次在案的目标机识别链**（0.10.0 安装件）加仓库侧零差异机检，不是 0.11.0 的校验回执。
按 SDD §3.2 统一口径，一旦 0.11.0 的目标校验指出不符，先在 `DCL` 追加登记（对比对象、目标机结果、不符项）再按 §4.7 做最小修正，
未受影响条目逐条零差异，九项路由集合、`Clarify`/`Stop`/`Route` 三态、既有守卫 reason 语义、七域顺序与四个连接器构成的集合始终不变。

## 声明修正

| ID | 触发 | 涉及文件 | 前后差异 | 回归范围 | 回归证据 | 结论 |
|---|---|---|---|---|---|---|
| DCL-01 | 目标机校验/识别对 manifest `dependencies.connectors` 四标识与导出校验常量的实测结果（§4.7 首行的标识层） | `workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json`；`scripts/export_workbuddy_experts.py` 的 `EXPECTED_CONNECTORS` | 未修正，零差异：源清单四标识 `wind-finance / tdx-connector / neodata / westock-mcp` 与 `EXPECTED_CONNECTORS` 逐项相等且仍为四个；本轮除 `plugin.json#version` 的 `0.10.0 → 0.11.0`（§5 包版本行，属 TASK-04 的既定改动而非标识修正）外，两文件其余字段、数组元素与其余常量逐字未改 | 不适用（未修正 ⇒ 无受影响回归对象）；`RIN-01` 的导出两次一致是对该零差异的现算复核，不属修正后回归 | 不适用（未修正）；零差异由 `cmd-04` 现算：导出物内 `plugin.json` 的 `dependencies.connectors` 与脚本 `EXPECTED_CONNECTORS` 逐项相等，且 `ALLOWED_PKG_FILES` 与敏感模式集合不变；标识被目标版本实际接受的最近实物链是 0.10.0 安装件（`reinstall.md#环境依赖排查/ENV-02` 实测安装件 `plugin.json` SHA-256 与 `installedAt`），该链只证明标识写法本身可被目标机识别，不代替 0.11.0 的校验回执 | 无需修正（依据＝未执行 0.11.0 目标校验故无实测不符项，加上述仓库侧零差异机检与 0.10.0 在案识别链；缺口与重授权路径见 `RIN-02`） |
| DCL-02 | 采集会话实测出的 entry 名不符事实转给 G4 闭环（`safety-branches.md#失败回执摘录对象/FC-02`），以及目标机对声明条目/路由说明的识别结果 | `workbuddy-experts/equity-research/agents/equity-research.md`；`plugins/vertical-plugins/equity-research/skills/**`（仅作归属判定，未修改） | 未修正，零差异：`FC-02` 的不符对象是 tdx 连接器自带技能文档里的 entry 名 `CWServ.tdxf10_gg_ybpj`（现网 503「模块不存在」）与现网可用名 `TdxSharePCCW.tdxf10_gg_ybpj`（200），该串不出现在本 CR 的包内声明面——`agents/equity-research.md`、九项技能源与 0.11.0 导出物全文对该串的命中均为 0，即修正对象不在 §4.7 允许的两类对象内，也不在 TASK-04 的写入面（§5 明令不改 `plugins/**`） | 不适用（未修正）；TASK-03 新增节与既有条目零差异由 `cmd-03` 的 CR1 SHA 前缀哈希断言持续复核 | 不适用（未修正）；`cmd-04` 现算两项：包内声明面对该 entry 名命中 0；`agents/equity-research.md` 的既有内容对 `index.md#CR1 输入核对` 登记的 CR1 SHA 反向核验零差异（与 `cmd-03` 同一判据） | 无需修正（依据＝实测不符项的载体不是本 CR 声明条目；把不符事实留在 `FC-02` 与 `LAT`/`DCL` 记录面，由连接器文档归属方处理，本节点不借修正之名扩权改包外文件） |
