# CR-2026-002 数据与授权 — 七域取数与溯源台账（G2）

四张固定表：`样例登记`（`SMP-NN`）、`查询溯源`（`QRY-NN`）、`单指标单源`（`SRC-NN`）、`口径审查`（`KJ-NN`）。
列名、列序与 ID 前缀取 `tests/_evidence.py#TABLE_COLUMNS`（CR-2026-002-TASK-01 §6）注册值，本文件不另立第二套定义。
七域逐域实取记录由 Ray 目标机采集会话在 `run-id CR-2026-002-20261003`、采集窗口
`2026-10-03T17:40:24+08:00～2026-10-03T17:43:31+08:00` 内直接产生，本 TASK 按 `verify-only` 登记并做对象级哈希固化。

## 登记与裁决口径（G2 节点裁定，三件）

1. **原件位置落法**：本批全部为 `verify-only`，证据对象 = 版本化核验记录本身，因此台账不落任何本机私有绝对路径。
   九条域记录逐字节转录到本文件 `核验记录对象` 节（下方机器块），每条的 canonical SHA-256
   （`json.dumps(record, sort_keys=True, separators=(",",":"), ensure_ascii=False)` 的 SHA-256，与
   `tests/_evidence.py::sha256_record` 全等）由 `cmd-02` 从该转录块现算并与行内值比对；采集会话投递包的链外指纹为
   `verify-records.json` = `afa26daae3407265bb0a3c10e07ef62b7ffa3f55bb2295d05157ad89729dc7cc`、
   `verify-records.sha256.json` = `2fcc5d60a57075e583e131a246b7732df2254b027afab6bf1f259f54fa4b5009`
   （包内清单 7/7 校验通过；投递通道为 AIFI-43 线程 `01a10132-1dbf-7e19-80d6-77d7257ff783` 的评论附件，
   本台账只记指纹与记录 ID，不记该通道所在的私有路径）。`SMP-01` 的 `原件位置与 SHA-256` 逐字取自 CR1
   `README.md#3` 的 `original-files`，为仓库根相对路径，不要求本机重新落盘原件。
2. **§2.3「响应标识」充分性**：SDD §2.3 对 `verify-only` 该列的规范取值是「服务端时间戳／原始链接**或**响应标识」三分支择一，
   §4.3 的防重放判据是同会话直接产生、行内足以复核的请求条件与来源标识、时间落窗、复核路径可同账户重发比对——响应标识是承载手段之一，不是唯一手段。
   据此逐条分层如实登记，不放宽也不判红：`VR-03/04/05/07/09` 有提供方标识（`trace_id`、`portfolioPath`、服务端时间戳）；
   `VR-02` 有 `endpoint`＋`elapsedMs`＋`hitCache`；`VR-08` 有提供方可查指标代码 4 项；
   `VR-01`（wind MCP 明确「无服务端请求标识」）与 `VR-06`（westock 结构化 JSON 无 ID）**只有会话侧时间戳**，
   其可复核性由「按 callId 配对的毫秒级逐条时间戳＋精确到参数的请求条件＋同账户重发比对字段清单」三项承载，
   记录内已显式写明无服务端标识，不伪称有。要求 wind 补一个提供方并不 emit 的请求 ID 等于设一个不可满足的门，故不采纳；
   把「仅会话时间戳」写成「有提供方响应 ID」属伪称，亦不采纳。
3. **RunWindow**：取方案 A（`index.md#RunWindow` 的「末次采集时间」由 `2026-10-03T15:20:00+08:00` 延伸到本次采集末条响应时刻
   `2026-10-03T17:43:31+08:00`，「首次采集时间」保持 `2026-10-03T14:58:00+08:00`），并取方案 B 的行内取值方式——
   每条 `QRY` 的 `数据/获取时间戳` 用该记录 `检索时间`（请求发出时刻）原值，不用窗口末刻，避免把不同请求写成同一时刻。

## 样例登记

| ID | 样例来源 | 适用数据域与任务 | 证券代码 | 交易所 | 报告期间 | 披露日期 | 来源与版本 | 四条件核验与依据 | 原件位置与 SHA-256 | 裁决人 | 裁决日期 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SMP-01 | CR1固定样例 | 域①机构财务（QRY-01）、域②一致预期（QRY-02）、域③研报评级目标价与全文（QRY-03/04/05）、域④公开行情K线（QRY-06）、域⑦资金流向（QRY-09）；服务 MR-01/02/03/06/07/09；域⑤筛选与域⑥宏观为无证券样本查询，按 §2.2 6(a) 非财报类口径免除样例引用（QRY-07/08） | 603599 | SH | 2025 年报 | 2026-04-27 | 巨潮资讯网，2025 年年报原件（广信股份 2026-04-27 披露） | 最近完整披露=已核实（巨潮资讯网 2026-04-27 披露 2025 年年报，原件在 out/samples/SAMPLE-01/）；研报覆盖充分=已核实（近半年超过 10 篇，最近 2026-08-25，来源慧博检索页）；研报可查=已核实（2026-09-28 在慧博 hibor.com.cn 检索到该标的该期报告，实际可复核渠道为慧博而非 Wind，按实际渠道如实记录）；合法使用权=已核实（交易所公开披露渠道取得的公开文件，允许本机自用）。四项逐字沿用 CR1 README §3 SampleIndex 与四条件逐项核验表，本 CR 不重新裁决 | out/samples/SAMPLE-01/603599_20260427_SSAP.pdf::473cac8783fe3f971a036f6819be5ddbb59745f288603921202137ead64df226 | Ray | 2026-09-28 |

## 查询溯源

| ID | 数据域 | 适用任务 | run-id | 查询日期 | 查询条件 | 证券代码/交易所 | 请求期间 | 源 | 口径 | 返回字段与结果状态 | 数据/获取时间戳 | 原始链接或文件引用 | 留证方式 | 证据对象引用 | SHA-256 | 复核路径 | 是否最终采用源 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QRY-01 | 机构财务、公告、事件 | MR-01 /earnings、MR-02 /initiate、MR-03 /model-update | CR-2026-002-20261003 | 2026-10-03 | 问题=查询广信股份(603599.SH)2025-12-31的ROE、营业收入和净利润 | 603599/SH | 2025 年度报告期（2025-12-31） | wind-finance（Wind Alice 1.2.2）／mcp__wind-finance__get_stock_fundamentals | 2025 年报单期披露值，三指标同行返回；许可判定按 §4.1 ② 走「本机自用」用途；响应标识分层=仅会话侧时间戳（§2.3 三分支之一，提供方不 emit 请求 ID）。本条只覆盖财务子项，公告与事件子项未实取，缺口如实留证由 G5 计入域状态 | 成功；1 行 × 3 指标（error=null）；字段清单=Wind代码、证券简称、2025年ROE、2025年营业收入、2025年净利润 | 2026-10-03T17:40:24+08:00 | 无提供方响应 ID（记录「响应标识」已如实标注）；引用 workbuddy-experts/equity-research/evidence/queries.md#核验记录对象 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-01 | d943352513444da12b21c3d1eda64e22076c37778be95a8a67de570ccca2cd3e | 按「查询条件」原参数在 wind-finance 同一授权账户重发并比对结果状态、期间覆盖与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-01（已确认）；重发前置=账户积分恢复（见本文件「wind 账户额度边界」） | 是 |
| QRY-02 | 券商一致预期 | MR-02 /initiate、MR-01 /earnings、MR-09 /thesis | CR-2026-002-20261003 | 2026-10-03 | entry=TdxSharePCCW.tdxf10_gg_ybpj；fixedTag=yzyq；code=603599 | 603599/SH | 2026-04-28～2026-09-04 | tdx-connector（通达信 1.0.0）／mcp__tdx-connector__tdx_api_data | 一致预期统计区间口径（8 条序列＋价格锚点至 2026-09-30）；提供方随响应返回服务端缓存命中标记 hitCache=true，原样登记；成功判据是本次会话内真实发出请求并于 17:40:30 收到 status=200 与 8 条结构，不是复用旧缓存回执（§4.4「旧缓存不构成成功」的边界见本文件「缓存边界」）。本行为域② 采用源，neodata 侧同名指标仅作跨源核对（SRC-04、KJ-01） | 成功；status=200；一致预期 8 条（errorCode=0；hitCache=true）；字段清单=首个预测年度、最新报告期、最新评级日期、T年一致预期每股收益、综合评级、综合目标价、近5/10/20日预期涨幅、统计日期序列、复权因子、收盘价 | 2026-10-03T17:40:24+08:00 | endpoint=http://tdxhub.icfqs.com:7615/TQLEX；auth=mode:tdx；elapsedMs=47；hitCache=true | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-02 | 84c2ab2ad7456c41303be806db124855a5efd523a808ba545ead497a0c943184 | 按「查询条件」的 entry/fixedTag/code 三元组在 tdx-connector 同一授权账户重发并比对字段清单与统计区间；本机自用许可见 data-sources.md#许可台账 LIC-04（已确认）；重发可能再次命中服务端缓存，比对以字段清单与区间为准 | 是 |
| QRY-03 | 研报评级、目标价、全文 | MR-02 /initiate、MR-09 /thesis | CR-2026-002-20261003 | 2026-10-03 | stock_codes=603599.SH | 603599/SH | 2022～2028 | neodata（NeoData 金融数据库 1.1.0）／mcp__neodata__ratings | 域③ 唯一源（声明无默认等价备选，§4.1 ③）；本行返回的盈利预测与目标价序列**不等同**域② 券商一致预期口径，进入备选前须有口径审查记录，已登记于 queries.md#口径审查 KJ-01（结论=不等价，故域② 指标采用 QRY-02，本行仅作跨源核对）。评级为月度聚合、预测为年度序列，两者期间不同不拼接 | 成功；status=success；含近 6 个月机构评级分布、综合目标价与盈利预测序列；字段清单=stock_name、stock_code、opinion_comment、institution_rating（月度买入/持有占比）、target_avg_price、target_price_change_pct、net_profit_history、profit_forecast、profit_forecast_yearly、profit_forecast_actual、基金持仓（fund_count、holding_ratio 等） | 2026-10-03T17:40:24+08:00 | trace_id=22bfe01b2a2c9834d309d3b70f5225ec；服务端时间戳=Sat Oct 03 17:40:27 CST 2026；cost=156 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-03 | 4e393fcc45bbe7de9d1d31448c571b74af131ff5bf2409a80e62bd39388bb1e7 | 按 stock_codes=603599.SH 在 neodata 同一授权账户重发并比对评级月份序列、target_avg_price 字段存在性与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-07（已确认） | 是 |
| QRY-04 | 研报评级、目标价、全文 | MR-01 /earnings | CR-2026-002-20261003 | 2026-10-03 | query=广信股份2025年年度报告收入构成；stock_codes=603599.SH；fiscal_years=2025；report_type=年度报告 | 603599/SH | 限定财年 2025 年度报告 | neodata（NeoData 金融数据库 1.1.0）／mcp__neodata__report_search | 域③ 全文子项检索；结果状态区分「空结果」与「有效零值」——本条为无召回（result=[]），不得据空结果断言该年报无收入构成披露（KJ-03）。非财报正文采用行，故不判成功采用 | 成功但空结果（result=[]，无召回）；字段清单=无（空结果） | 2026-10-03T17:40:24+08:00 | trace_id=c5e28f1d64f3bbf3257d0b08284288d3；服务端时间戳=Sat Oct 03 17:40:27 CST 2026 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-04 | 80484aa8264aab8c640a964f5481a8fa42d0367dad2f6cda5d90bcfdc5742295 | 按同一 query/stock_codes/fiscal_years/report_type 四参数在 neodata 同一授权账户重发并比对召回条数与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-07（已确认）；重发仍空即维持缺口结论 | 否 |
| QRY-05 | 研报评级、目标价、全文 | MR-01 /earnings | CR-2026-002-20261003 | 2026-10-03 | query=广信股份2025年年度报告收入构成；stock_codes=603599.SH（放宽复核：未限定财年与报告类型） | 603599/SH | 不限期间 | neodata（NeoData 金融数据库 1.1.0）／mcp__neodata__report_search | QRY-04 的放宽复核行：去掉财年与报告类型限定后重发，用于排除「参数过窄导致空结果」这一解释；与 QRY-04 构成两次独立实测，不复用同一回执。空结果同样按 KJ-03 区分于有效零值 | 成功但空结果（result=[]，无召回；放宽参数复核结论一致）；字段清单=无（空结果） | 2026-10-03T17:40:58+08:00 | trace_id=34f29ebf6ceaa304d18f6d134cbebfe3；服务端时间戳=Sat Oct 03 17:41:01 CST 2026 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-05 | 3ed9fab56bc522d87337b382c2584595f62816053996abce33b1f0791c86127d | 按放宽后的 query/stock_codes 两参数在 neodata 同一授权账户重发并比对召回条数；本机自用许可见 data-sources.md#许可台账 LIC-07（已确认） | 否 |
| QRY-06 | 公开行情、K 线、公告、日历 | MR-06 /morning-note、MR-07 /earnings-preview | CR-2026-002-20261003 | 2026-10-03 | code=sh603599；period=day；start=2026-09-16；end=2026-10-03；limit=10 | 603599/SH | 2026-09-16～2026-09-30 | westock-data（路由域名，经 westock-mcp 1.0.0 连接器工具面）／mcp__westock-mcp__data_kline | 日频行情区间口径：请求区间至 2026-10-03，实际覆盖到最近交易日 2026-09-30（10 根），末段为非交易日而非缺数；`请求期间` 按证据对象实际期间覆盖登记，与「查询条件」的 start/end 并列可读。本条只覆盖 K 线子项，公告与日历子项未实取，缺口如实留证由 G5 计入域状态。westock-mcp 是宿主层连接器 ID、westock-data 是 Agent 层路由域名，不同层不合并（§1.3） | 成功；10 根日 K（ok=true）；字段清单=date、open、last、high、low、volume、amount、exchange（换手率） | 2026-10-03T17:40:58+08:00 | 无提供方响应 ID（结构化 JSON）；引用 workbuddy-experts/equity-research/evidence/queries.md#核验记录对象 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-06 | 70457cfccec95247b117fddd88bc5abca5294a6751f4549cd31dc87f66a5a683 | 按 code/period/start/end/limit 五参数在 westock-data 同一授权账户重发并比对根数、日期序列与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-10（已确认） | 是 |
| QRY-07 | 筛选 | MR-04 /screen | CR-2026-002-20261003 | 2026-10-03 | preset=low_pe；limit=10（全市场筛选，未指定证券） | 不适用（全市场筛选，无个股标的；§2.2 6(a) 非财报类口径免除样例引用） | 不适用（非财报类全市场快照，无期间参数；基准时间 2026-10-03 17:41:01，行情截至最近交易日 2026-09-30） | westock-tool（路由域名，经 westock-mcp 1.0.0 连接器工具面）／mcp__westock-mcp__tool_filter | 条件筛选表达式 intersect([PE_TTM > 0, PE_TTM < 20])，返回 totalStocks=825 与 limit=10 的样例子集；快照口径（非历史区间），时效以响应内基准时间戳为准。本行是 `不适用` 写法但不掩盖缺口：域⑤ 的备选（tdx-connector／wind-finance）等价口径未核实故不启用，见 SRC-08 | 成功；totalStocks=825；字段清单=totalStocks、stockAmountInUniverse、stocks[code、name、ClosePrice、ChangePCT、PB、PE_TTM、PE_Fwd]、expression、date、portfolioPath | 2026-10-03T17:40:58+08:00 | portfolioPath=b3d790c2-643c-4aa5-8970-a783cbac3908；响应内基准时间戳=2026-10-03 17:41:01 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-07 | 29fdf0fdd69411082144ee9cba7f15ff751e338cbd00ca6db3958efccb4bbf2d | 按 preset=low_pe 与 limit=10 在 westock-tool 同一授权账户重发并比对 totalStocks、表达式串与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-13（已确认）；快照类重发结果随行情日变化，比对以表达式与字段清单为准 | 是 |
| QRY-08 | 宏观 | MR-08 /sector | CR-2026-002-20261003 | 2026-10-03 | executionMode=搜索并提数；question=中国GDP；observation=8 | 不适用（宏观指标，无证券标的；§2.2 6(a) 非财报类口径免除样例引用） | 不适用（宏观时间序列非财报类；请求参数为近 8 期，证据对象覆盖=季频 2018-12-31～2026-06-30 共 31 期、年频 2018～2025 共 8 期） | wind-finance（Wind Alice 1.2.2）／mcp__wind-finance__natural_language_get_edb_data | EDB 指标序列口径，命中 4 个指标代码（M5567876、M0001395、M5567889、M5785610），meta 含 code、name、freq、unit、source、updateDate；季频与年频为两个不同频率序列，不并成一条序列（FR-05 不拼接异口径）。响应标识分层=提供方可查指标代码，无请求 ID | 成功；code=0；命中 4 个 EDB 指标序列（error=null）；字段清单=meta（code、name、freq、unit、source、updateDate）、date[]、value[] | 2026-10-03T17:40:58+08:00 | 指标代码 M5567876、M0001395、M5567889、M5785610；引用 workbuddy-experts/equity-research/evidence/queries.md#核验记录对象 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-08 | 88c3d140e523e3b7d90fd374c44f3d130b271e25bd18fa8366b7ff3c3b41c689 | 按 executionMode/question/observation 三参数在 wind-finance 同一授权账户重发并比对命中的指标代码集合、频率与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-01（已确认）；重发前置=账户积分恢复（见本文件「wind 账户额度边界」） | 是 |
| QRY-09 | 资金、龙虎榜、两融 | MR-06 /morning-note、MR-08 /sector | CR-2026-002-20261003 | 2026-10-03 | codes=603599.SH；start_date=20260926；end_date=20261003 | 603599/SH | 2026-09-28～2026-09-30 | neodata（NeoData 金融数据库 1.1.0）／mcp__neodata__fund_flow | 资金流向按交易日序列口径：请求区间 20260926～20261003，覆盖 3 个交易日（2026-09-28～2026-09-30），区间内非交易日不构成缺口。域⑦ 声明含资金、龙虎榜、两融三个子项，本条只覆盖「资金」子项，龙虎榜与两融未实取且本次未采数，缺口明示不掩盖（§4.4「明示未覆盖字段与缺口」），由 G5 计入 DOM-07 状态；westock-data 备选未启用 | 成功；3 个交易日记录；字段清单=trading_date、main_net_inflow、main_inflow、main_outflow、主力/散户与超大单/大单净流入、近5/10/20日净买入序列 | 2026-10-03T17:40:58+08:00 | trace_id=ea83007c1a63e7e63e72279dc1e03fcb；服务端时间戳=Sat Oct 03 17:41:01 CST 2026 | verify-only | workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-09 | ced94d50ffd6ec0d73d06960e5e8cfb5b8b6d4ffb5b11ed361d281142ead1b14 | 按 codes/start_date/end_date 三参数在 neodata 同一授权账户重发并比对交易日数、日期序列与字段清单；本机自用许可见 data-sources.md#许可台账 LIC-07（已确认） | 是 |

## 单指标单源

| ID | 指标 | 候选源与逐项差异 | 最终采用源 | 裁决依据 |
|---|---|---|---|---|
| SRC-01 | 603599 2025 年净利润 | QRY-01 wind-finance（2025 年报期，6.5691 亿元，披露口径）／QRY-03 neodata profit_forecast_actual.net_profit（2025 年度，656907533 元，预测实际值序列）；差异＝单位与取整表达（亿元 vs 元），数值逐位一致；来源同为本次会话（17:40:24～17:40:30 +08:00），期间同为 2025 年报 | QRY-01 | 域① 首选 wind-finance（agents/equity-research.md 数据域路由 1：wind-finance → neodata → tdx F10）；neodata 侧仅作核对证据不作并列最终值（FR-05 不静默揉合成一个值）；口径核对见 KJ-02 |
| SRC-02 | 603599 2025 年 ROE | QRY-01 wind-finance（6.6406%，2025 年报披露口径）／QRY-03 neodata 一致预期口径（6.66，非同一口径的预测聚合值）；差异＝口径不同（披露值 vs 预测聚合）而非数值分歧，两者不得互换 | QRY-01 | 任务口径为年报披露值，采用披露口径首选源；跨口径近似值不拼接、不替代（FR-05）；neodata 该字段进备选须先过 KJ-01 审查，审查结论为不等价 |
| SRC-03 | 603599 2025 年营业收入 | QRY-01 wind-finance（2025 年报期，单候选）；neodata ratings 返回字段清单不含营业收入项，本次无跨源核对对象 | QRY-01 | 域① 首选且本次唯一取到该指标；「无备选」如实记入本行，不写成有备选也不据此降档；后续如需核对可走域① 第三顺位 tdx-connector F10，须先按 §4.1 ② 核对该动作的本机自用许可 |
| SRC-04 | 603599 一致预期每股收益与综合目标价 | QRY-02 tdx-connector yzyq（统计区间 2026-04-28～2026-09-04，8 条序列，含 T年一致预期每股收益与综合目标价）／QRY-03 neodata（评级月度 202605、202608、202609＋盈利预测 2022～2028 年度序列，target_avg_price）；差异＝聚合口径与统计窗口不同、序列点数不可一一对应 | QRY-02 | 域② 首选 tdx-connector yzyq；neodata 盈利预测未经口径审查不得标成等价券商共识——审查项与结论已登记 KJ-01（结论＝不等价，故本指标不启用该备选）；两行期间与口径逐项列明，不合并 |
| SRC-05 | 603599 机构评级分布与目标价（域③） | QRY-03 neodata ratings（单源；域③ 声明「仅 neodata，缺席则无默认等价备选」） | QRY-03 | §4.1 ③ 首选不可用时只尝试有使用权、同口径且有口径审查记录的备选；域③ 无声明备选，故本指标单源成立，不发明补位指标（FR-04） |
| SRC-06 | 603599 2025 年报全文（收入构成）检索 | QRY-04（限定 fiscal_years=2025、report_type=年度报告）／QRY-05（放宽未限期间）；两次独立实测均 result=[] 无召回，差异＝参数宽窄，结论一致 | 无（两次实测均空结果，不采用任何源；缺口见 KJ-03 与本行依据列） | 空结果不等于有效零值（§4.4），不据空召回断言该年报无收入构成披露，也不改期取数或标 `不适用` 规避；域③ 的评级与目标价子项仍成立（SRC-05），全文子项保留为明确缺口供 G3 场景与 G5 域状态消费 |
| SRC-07 | 603599 日 K 收盘序列（域④） | QRY-06 westock-data data_kline（10 根日 K，2026-09-16～2026-09-30）；neodata 备选未启用（同一指标本次无跨源差异需标注） | QRY-06 | 域④ 首选 westock-data；行情时间与最近交易日一致、字段清单齐备（含换手率 exchange 字段）；公告与日历子项未实取，属域内缺口而非本指标差异 |
| SRC-08 | 低 PE 全市场筛选结果集（域⑤） | QRY-07 westock-tool tool_filter（totalStocks=825，表达式 intersect([PE_TTM > 0, PE_TTM < 20])）；tdx-connector／wind-finance 备选未启用 | QRY-07 | 域⑤ 首选 westock-tool；备选须按 CR1 已验收路由与任务口径核对等价后才可启用（PRD FR-04 表限定「不新增未经确认的顺序」），等价口径本次未核实，故不启用并明示；westock-tool 是路由域名、westock-mcp 是宿主层连接器 ID，不同层不合并（§1.3） |
| SRC-09 | 中国 GDP 季频与年频序列（域⑥） | QRY-08 wind-finance EDB（4 个指标代码，季频 31 期至 2026-06-30、年频 8 期至 2025）；westock-data 备选未启用 | QRY-08 | 域⑥ 首选 wind-finance，且指标、发布频率与更新时间由 meta（code、freq、unit、source、updateDate）可核；季频与年频分列不同频率序列，不拼成一条（FR-05） |
| SRC-10 | 603599 主力资金净流入（域⑦） | QRY-09 neodata fund_flow（3 个交易日，2026-09-28～2026-09-30）；westock-data 备选未启用 | QRY-09 | 域⑦ 首选 neodata；「资金」子项成立，龙虎榜与两融子项未实取属域内缺口（见 QRY-09 口径列），不得由本行推定域⑦ 三子项全覆盖 |

## 口径审查

| ID | 源 | 审查项 | 结论 |
|---|---|---|---|
| KJ-01 | neodata | 盈利预测序列（profit_forecast、profit_forecast_yearly、profit_forecast_actual）与 target_avg_price 是否等同于 tdx-connector yzyq 的券商一致预期口径，可否作为域② 合格备选 | 不等价，不得作为域② 一致预期备选混用。逐项差异：neodata 为评级月度聚合（202605、202608、202609）加 2022～2028 年度预测序列，tdx yzyq 为一致预期统计区间 2026-04-28～2026-09-04 的 8 条序列，两者统计窗口、聚合口径与序列点数均不可一一对应；域② 指标采用源为 QRY-02（SRC-04），neodata 侧仅作跨源核对证据。本审查即 §4.4「neodata 进入合格备选前必须有口径审查记录」所要求的记录 |
| KJ-02 | neodata | 净利润绝对值口径（profit_forecast_actual.net_profit 以元计）与 wind-finance 2025 年净利润（以亿元计）是否同一指标可比 | 可比且数值一致：656907533 元 与 6.5691 亿元 为同一 2025 年报期数值的两种单位表达，差异仅在单位与取整，无口径分歧。作为 SRC-01 的核对证据保留；采用源仍为 QRY-01（域① 首选），不因数值一致而把两源并列为两个最终值（FR-05 单源） |
| KJ-03 | neodata | report_search 的空结果（result=[]，无召回）应判为「无该披露」还是「检索未命中」，可否据此得出该年报收入构成不可得 | 判为检索未命中，不得判为无该披露，亦不得判为有效零值。两次独立实测（QRY-04 限定 fiscal_years=2025 与 report_type=年度报告、QRY-05 放宽未限期间）均无召回且结论一致，仅能证明该工具面对该 query 无召回；SMP-01 的 2025 年年报原件存在（CR1 索引已登记并固化 SHA-256），故「无召回」不等于「无披露」。域③ 全文子项按明确缺口处理（SRC-06），不得改期取数、不得标 `不适用` 规避、也不得据空结果输出缺乏数据支持的结论 |

## 交付边界与事实注记

**港股样例缺口（阻塞，不登记 SMP）**：CR1 索引不含具名港股样例；采集会话于 `hk-sample-decision.md`
（canonical SHA-256 `833d9fba18789918d3d50bbbc2b4c768bdfb69adb09bbbca07891eac6be8c5b5`）明示接受「H 股 `REQ` 与其 `TSK` 保持阻塞」，
未选择「补 `合法使用权` 依据」（该依据为外部书面许可，采集会话无法取得；与 `data-sources.md#许可台账` 12 行 `待确认` 同源）。
因此本文件**不含任何 `.HK` 的 `SMP` 行与 `QRY` 行**：未登记且四条件未全部 `已核实` 的样例不得进入任何 `QRY` 行（§2.2 6(a)），
也不得以 A 股样例或演示数据充当港股样例、以 `不适用` 掩盖该缺口（§4.4）。涉及 H 股的 `REQ`/`TSK` 由 G5 在
`domain-readiness.md` 保持 `阻塞`；如后续取得许可依据，可按 §4.4 登记 `SMP-NN` 后补采。

**wind 账户额度边界**：同一采集会话内 `17:40:24`（A 股财务成功）与 `17:41:05`（EDB 成功）之后，
`17:42:33` 起 wind-finance 连续三次返回「账户积分余额不足，无法完成当前操作」类拒绝（美股、美股重发、A 股对照同拒，属账户额度层而非市场特异）。
QRY-01 与 QRY-08 的成功回执成立于窗口内、不受该后续拒绝影响；但两行的 `复核路径` 重发须先恢复账户积分，本文件如实标注，不把可复核性写成无条件成立。
该拒绝事实本身是负例证据，其场景归属（`SBC` 订阅缺失／权限拒绝）在 G3 的 `safety-branches.md` 登记，本 TASK 不代 G3 落行。

**缓存边界**：QRY-02 的响应带服务端缓存命中标记 `hitCache=true`。§4.4「旧缓存不构成成功」指的是把本机旧缓存回执当本次实取，
本条判据是本次会话内真实发出请求（17:40:24）并于 17:40:30 收到 `status=200` 与 8 条结构，标记由提供方随响应返回，原样登记不抹去。
同一会话的另一事实须传递给 G3：以 `auth` 覆盖注入无效凭据的受控尝试**未复现拒绝**（服务端缓存命中，凭据未被实际校验），
故该受控方式不得用于构造 `SBC` 缺权限场景（负例改用真实拒绝）。

**时间戳与 RunWindow**：每条 `QRY` 的 `数据/获取时间戳` 取该记录的 `检索时间`（请求发出时刻）原值，响应到达时刻记在该记录对象的
`响应标识` 字段内；逐条值互不相同，来源为采集会话自身的工具调用日志（毫秒级 epoch 按 callId 配对，换算 ISO-8601/+08:00）。
`index.md#RunWindow` 的「末次采集时间」按方案 A 延伸到 `2026-10-03T17:43:31+08:00`（本次采集末条响应时刻），窗口下界保持 `2026-10-03T14:58:00+08:00`，
满足 §4.3「落窗且不早于本 CR 首次实测」。

**留证方式裁决**：六入口的 `研究引用展示` 与 `文件中使用` 在 `data-sources.md#许可台账` 均为 `待确认`（12 行 fail-closed 不获准），
按 §2.2 不变量 2 的收窄规则，本批九条全部记 `verify-only`：不落原始响应、不复制字段值与原始内容，证据对象为下方非内容核验记录，
哈希对象为该记录对象的 canonical 序列化。九条记录键集合恒等于 §2.3 `verify-only` 规范的七字段，不含响应正文；
`cmd-02` 对键集合、转录块重算哈希与行内值三者做交叉断言，并对本文件整体做与导出脚本同组的敏感扫描（含 Windows 私有绝对路径形态）。

## ID 前缀注记

`queries.md#口径审查` 的 `ID` 前缀未列在 SDD §3.1 的枚举前缀清单（`LAT-/CON-/LIC-/SMP-/QRY-/SRC-/SBC-/ORD-/RIN-/ENV-/REP-/DOM-/TSK-/DCL-`）中，
本 TASK 取 `KJ-` 并在 `cmd-02` 以 `require_ids(rows, "KJ", minimum=1)` 固定；该表列名与列序仍取 `TABLE_COLUMNS` 注册值，未另立第二套定义。

## 核验记录对象

逐条为 §2.3 `verify-only` 规范的七字段非内容核验记录（请求条件／源与工具／结果状态／期间覆盖／字段清单／响应标识／检索时间），不含响应正文与字段值。本块是采集会话投递件 `verify-records.json#域记录` 的逐字节转录，每条对象的 canonical SHA-256 与投递件 `verify-records.sha256.json` 逐条全等（登记时独立复算 9/9 通过），`cmd-02` 以本块现算哈希为准与 `QRY` 行比对。

```json
{
  "VR-01": {
    "请求条件": "问题=查询广信股份(603599.SH)2025-12-31的ROE、营业收入和净利润",
    "源与工具": "wind-finance（Wind Alice 1.2.2） / mcp__wind-finance__get_stock_fundamentals",
    "结果状态": "成功；返回 1 行 × 3 指标（error=null）",
    "期间覆盖": "2025 年度报告期（2025-12-31），单期",
    "字段清单": "Wind代码、证券简称、2025年ROE、2025年营业收入、2025年净利润",
    "响应标识": "wind MCP 结构化返回；无服务端请求标识；响应接收 2026-10-03T17:40:30+08:00",
    "检索时间": "2026-10-03T17:40:24+08:00"
  },
  "VR-02": {
    "请求条件": "entry=TdxSharePCCW.tdxf10_gg_ybpj；fixedTag=yzyq；code=603599",
    "源与工具": "tdx-connector（通达信 1.0.0） / mcp__tdx-connector__tdx_api_data",
    "结果状态": "成功；status=200；一致预期 8 条（errorCode=0；响应标记 hitCache=true）",
    "期间覆盖": "一致预期统计区间 2026-04-28～2026-09-04（8 条）；价格锚点序列至 2026-09-30",
    "字段清单": "首个预测年度、最新报告期、最新评级日期、T年一致预期每股收益、综合评级、综合目标价、近5/10/20日预期涨幅、统计日期序列、复权因子、收盘价",
    "响应标识": "endpoint=http://tdxhub.icfqs.com:7615/TQLEX；auth=mode:tdx；elapsedMs=47；hitCache=true；响应接收 2026-10-03T17:40:30+08:00",
    "检索时间": "2026-10-03T17:40:24+08:00"
  },
  "VR-03": {
    "请求条件": "stock_codes=603599.SH",
    "源与工具": "neodata（NeoData 金融数据库 1.1.0） / mcp__neodata__ratings",
    "结果状态": "成功；status=success；含近 6 个月机构评级分布、综合目标价与盈利预测序列",
    "期间覆盖": "机构评级月度 202605、202608、202609；盈利预测 2022～2028 年度；持仓与舆情快照至检索日",
    "字段清单": "stock_name、stock_code、opinion_comment、institution_rating（月度买入/持有占比）、target_avg_price、target_price_change_pct、net_profit_history、profit_forecast、profit_forecast_yearly、profit_forecast_actual、基金持仓（fund_count、holding_ratio 等）",
    "响应标识": "trace_id=22bfe01b2a2c9834d309d3b70f5225ec；服务端时间戳=Sat Oct 03 17:40:27 CST 2026；cost=156；响应接收 2026-10-03T17:40:30+08:00",
    "检索时间": "2026-10-03T17:40:24+08:00"
  },
  "VR-04": {
    "请求条件": "query=广信股份2025年年度报告收入构成；stock_codes=603599.SH；fiscal_years=2025；report_type=年度报告",
    "源与工具": "neodata（NeoData 金融数据库 1.1.0） / mcp__neodata__report_search",
    "结果状态": "成功但空结果（result=[]，无召回）",
    "期间覆盖": "请求限定财年 2025 年度报告（空结果，无实际覆盖）",
    "字段清单": "无（空结果）",
    "响应标识": "trace_id=c5e28f1d64f3bbf3257d0b08284288d3；服务端时间戳=Sat Oct 03 17:40:27 CST 2026；响应接收 2026-10-03T17:40:30+08:00",
    "检索时间": "2026-10-03T17:40:24+08:00"
  },
  "VR-05": {
    "请求条件": "query=广信股份2025年年度报告收入构成；stock_codes=603599.SH（放宽复核：未限定财年与报告类型）",
    "源与工具": "neodata（NeoData 金融数据库 1.1.0） / mcp__neodata__report_search",
    "结果状态": "成功但空结果（result=[]，无召回；放宽参数复核结论一致）",
    "期间覆盖": "不限期间（空结果，无实际覆盖）",
    "字段清单": "无（空结果）",
    "响应标识": "trace_id=34f29ebf6ceaa304d18f6d134cbebfe3；服务端时间戳=Sat Oct 03 17:41:01 CST 2026；响应接收 2026-10-03T17:41:05+08:00",
    "检索时间": "2026-10-03T17:40:58+08:00"
  },
  "VR-06": {
    "请求条件": "code=sh603599；period=day；start=2026-09-16；end=2026-10-03；limit=10",
    "源与工具": "westock-data（路由域名；经 westock-mcp 1.0.0 连接器工具面） / mcp__westock-mcp__data_kline",
    "结果状态": "成功；返回 10 根日 K（ok=true）",
    "期间覆盖": "2026-09-16～2026-09-30（10 个交易日）",
    "字段清单": "date、open、last、high、low、volume、amount、exchange（换手率）",
    "响应标识": "无显式请求标识；结构化 JSON；响应接收 2026-10-03T17:41:05+08:00",
    "检索时间": "2026-10-03T17:40:58+08:00"
  },
  "VR-07": {
    "请求条件": "preset=low_pe；limit=10（全市场筛选，未指定证券）",
    "源与工具": "westock-tool（路由域名；经 westock-mcp 1.0.0 连接器工具面） / mcp__westock-mcp__tool_filter",
    "结果状态": "成功；totalStocks=825（表达式 intersect([PE_TTM > 0, PE_TTM < 20])）",
    "期间覆盖": "全市场快照，基准时间 2026-10-03 17:41:01（行情截至最近交易日 2026-09-30）",
    "字段清单": "totalStocks、stockAmountInUniverse、stocks[code、name、ClosePrice、ChangePCT、PB、PE_TTM、PE_Fwd]、expression、date、portfolioPath",
    "响应标识": "portfolioPath=b3d790c2-643c-4aa5-8970-a783cbac3908；响应内基准时间戳=2026-10-03 17:41:01；响应接收 2026-10-03T17:41:05+08:00",
    "检索时间": "2026-10-03T17:40:58+08:00"
  },
  "VR-08": {
    "请求条件": "executionMode=搜索并提数；question=中国GDP；observation=8",
    "源与工具": "wind-finance（Wind Alice 1.2.2） / mcp__wind-finance__natural_language_get_edb_data",
    "结果状态": "成功；code=0；命中 4 个 EDB 指标序列（error=null）",
    "期间覆盖": "季频 2018-12-31～2026-06-30（31 期）；年频 2018～2025（8 期）",
    "字段清单": "meta（code、name、freq、unit、source、updateDate）、date[]、value[]",
    "响应标识": "指标代码 M5567876、M0001395、M5567889、M5785610；无服务端请求标识；响应接收 2026-10-03T17:41:05+08:00",
    "检索时间": "2026-10-03T17:40:58+08:00"
  },
  "VR-09": {
    "请求条件": "codes=603599.SH；start_date=20260926；end_date=20261003",
    "源与工具": "neodata（NeoData 金融数据库 1.1.0） / mcp__neodata__fund_flow",
    "结果状态": "成功；返回 3 个交易日记录",
    "期间覆盖": "2026-09-28～2026-09-30（3 个交易日；请求区间 20260926～20261003）",
    "字段清单": "trading_date、main_net_inflow、main_inflow、main_outflow、主力/散户与超大单/大单净流入、近5/10/20日净买入序列",
    "响应标识": "trace_id=ea83007c1a63e7e63e72279dc1e03fcb；服务端时间戳=Sat Oct 03 17:41:01 CST 2026；响应接收 2026-10-03T17:41:05+08:00",
    "检索时间": "2026-10-03T17:40:58+08:00"
  }
}
```

