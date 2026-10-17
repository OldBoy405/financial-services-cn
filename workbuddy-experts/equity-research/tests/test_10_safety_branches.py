"""cmd-03 — decision order, nine safety branches and the Agent declaration section (FR-06/07 -> AC-06/07).

Reads `evidence/safety-branches.md` (ORD + SBC tables and the three versioned machine blocks),
the preread G2 tables in `queries.md`, `data-sources.md#许可台账`, `index.md#RunWindow` and
`agents/equity-research.md`. Everything is checked at object level: each transcribed negative
record's canonical SHA-256 is recomputed against the published anchor block, every cited ledger ID
has to exist, the ②-no-fetch-before-licence invariant is re-run through cmd-02's own licence
cross-check, and the Agent file's zero-diff is proved by hashing the text that precedes the one
added section against the CR1 SHA already recorded in `index.md#CR1 输入核对`.
TASK-03 §4 counterexamples run in-memory on mutated copies. Since round3 every scenario row is reproduced, so each row's
actual reply has to be bound to a record object whose canonical SHA-256 is recomputed here; the `缺口-未重现` bundling
stays armed (a gap row can neither be刷绿 nor hide a real refusal), and `采用` — the §4.2 SBC-08 success path the §2.1
enum cannot express — is locked to that one row and to records that really returned data (登记口径 第 2 与第 7 条).
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest

import _evidence
import _support
from _evidence import (
    EVIDENCE,
    check_in_run_window,
    check_no_sensitive,
    load_table,
    read_coverage,
    read_run_window,
    require_ids,
    sha256_record,
)
from _support import NINE_PAIRS, RepoTest
from test_08_source_ledger import check_coverage_against, compute_coverage, load_readiness
from test_09_query_traceability import (
    PRIVATE_WIN_PATH_RE,
    VERIFY_ONLY_FIELDS,
    _licence_for,
    load_verify_records,
)

REPLIED = {"澄清", "合格备选", "公开摘要", "停止"}
GAP = "缺口-未重现"
ADOPT = "采用"  # §4.1 ⑤ 的裁决词，§2.1 枚举缺该态（登记口径第 7 条），只允许 SBC-08 取
SBC_COLUMNS = _evidence.TABLE_COLUMNS["safety-branches.md#安全分支实测"]
ORD_STEPS = ("①", "②", "③", "④", "⑤")
STEP_KEYWORDS = ("确认证券", "核对", "首选", "非空性", "裁决")
AGENT_SECTION = "## 数据动作判定顺序与降级/停止行为（FR-06 / FR-07）"
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
# 无来源数字 / 未支持评级的零容忍面：本文件按许可只登记 verify-only 记录，任何金额、比率、
# 估值、评级或目标价的数值都属越界（TASK-03 §3.5 与登记口径第 5 条）。
FIN_VALUE_RE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:元|亿元|万元|港元|美元|倍|只|篇|%|％)")
RATING_RE = re.compile(r"评级|目标价|估值")
EXPECT_ONLY_RE = re.compile(r"预期(停止|输出|回复)")
ID_RE = re.compile(r"\b(?:QRY|SRC|KJ|LIC|NZ|FC|VR|SMP|SBC|ORD|DOM)-\d{2}(?:-[A-Z]{2,3})?\b")
RECORD_ID_RE = re.compile(r"\bSBC-\d{2}-[A-Z]{2,3}\b")
MS_SECONDS_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}\Z")
LIC_STATUS_RE = re.compile(r"\b(LIC-\d{2}) 实际状态=([^\s，；）)）`]+)")
ISO_SECONDS_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\Z")
SOURCE_NAMES_RE = re.compile(
    r"wind-finance|tdx-connector|neodata-financial-search|neodata|westock-data|westock-tool|"
    r"westock-mcp|tushare|ifind|同花顺",
    re.IGNORECASE,
)
DECLARED_SPLIT_RE = re.compile(r"实际重现 (\d+) 行[\s\S]{0,160}?未重现缺口 (\d+) 行")


def load_json_block(heading: str) -> dict:
    text = (EVIDENCE / "safety-branches.md").read_text(encoding="utf-8")
    start = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    if not start:
        raise AssertionError(f"safety-branches.md 缺 `{heading}` 节")
    block = re.search(r"```json\s*(.*?)\s*```", text[start.end():], re.DOTALL)
    if not block:
        raise AssertionError(f"safety-branches.md#{heading} 缺 json 机器块")
    data = json.loads(block.group(1))
    if not isinstance(data, dict) or not data:
        raise AssertionError(f"safety-branches.md#{heading} 机器块为空")
    return data


def _cells(rows: list[dict]) -> str:
    return "\n".join(" ".join(r.values()) for r in rows)


def known_ids(ord_rows: list[dict], sbc_rows: list[dict], records: dict, failures: dict,
              lic: list[dict], vr: dict, sbc_records: dict) -> set[str]:
    ids = ({r["ID"] for r in ord_rows} | {r["ID"] for r in sbc_rows} | set(records)
           | set(failures) | set(vr) | set(sbc_records))
    for heading in ("查询溯源", "单指标单源", "口径审查", "样例登记"):
        ids |= {r["ID"] for r in load_table("queries.md", heading)}
    ids |= {r["ID"] for r in lic}
    return ids


def returned_data(rec: dict) -> bool:
    """The source really returned fields: 字段清单 lists field names instead of 「无…」.

    期间覆盖 is not part of this test — a successful entity-recognition reply has no reporting
    period, while the refusal blocks check that column separately (`_records_block`).
    """
    return not str(rec["字段清单"]).startswith("无")


def check_ord(rows: list[dict], backings: dict[str, bool], known: set[str]) -> None:
    require_ids(rows, "ORD", minimum=5)
    if len(rows) != 5:
        raise AssertionError(f"ORD 行必须恰为 5 行（①～⑤），实为 {len(rows)}")
    for i, row in enumerate(rows):
        for col in ("ID", "顺序步骤", "可观察证据", "按序结论"):
            if not row[col].strip():
                raise AssertionError(f"ORD 行 {row['ID']} 字段 {col} 为空")
        step = row["顺序步骤"].strip()
        if not step.startswith(ORD_STEPS[i]):
            raise AssertionError(f"ORD 行 {row['ID']} 顺序步骤 {step[:8]!r} 不是第 {ORD_STEPS[i]} 步")
        if STEP_KEYWORDS[i] not in step:
            raise AssertionError(f"ORD 行 {row['ID']} 步骤文本缺 §4.1 该步要素 {STEP_KEYWORDS[i]!r}")
        passed = row["按序结论"].startswith("通过")
        if passed != backings[ORD_STEPS[i]]:
            raise AssertionError(
                f"ORD 行 {row['ID']} 结论与机检不一致：结论={row['按序结论'][:12]!r} 机检={backings[ORD_STEPS[i]]}")
        if not passed and not row["按序结论"].startswith("阻塞"):
            raise AssertionError(f"ORD 行 {row['ID']} 按序结论 {row['按序结论'][:12]!r} 非 通过/阻塞")
        unknown = [x for x in ID_RE.findall(row["可观察证据"]) if x not in known]
        if unknown:
            raise AssertionError(f"ORD 行 {row['ID']} 可观察证据引用不存在的行 {unknown}")


def check_sbc(rows: list[dict], known: set[str], src_ids: set[str], lic_by_id: dict[str, dict],
              sbc_records: dict[str, dict]) -> None:
    require_ids(rows, "SBC", minimum=9)
    if len(rows) != 9:
        raise AssertionError(f"SBC 行必须恰为九行（§4.2 九场景），实为 {len(rows)}")
    for row in rows:
        for col in SBC_COLUMNS:
            if not row[col].strip():
                raise AssertionError(f"SBC 行 {row['ID']} 字段 {col} 为空")
        kind = row["实际回复类别"].strip()
        if kind not in REPLIED | {GAP, ADOPT}:
            raise AssertionError(f"SBC 行 {row['ID']} 实际回复类别 {kind!r} 不在封闭取值")
        if EXPECT_ONLY_RE.search(_cells([row])):
            raise AssertionError(f"SBC 行 {row['ID']} 以预期描述代替实际输出（§4.2「只写预期停止不算证据」）")
        unknown = [x for x in ID_RE.findall(_cells([row])) if x not in known]
        if unknown:
            raise AssertionError(f"SBC 行 {row['ID']} 证据引用指向不存在的行 {unknown}")
        cited_records = set(RECORD_ID_RE.findall(_cells([row])))
        ghost = sorted(cited_records - set(sbc_records))
        if ghost:
            raise AssertionError(
                f"SBC 行 {row['ID']} 引用了「安全分支实测记录对象」里不存在的记录 {ghost}")
        if kind == GAP:
            if not row["契约符合性"].startswith("阻塞（未重现）"):
                raise AssertionError(f"SBC 行 {row['ID']} 缺口行的契约符合性必须为 阻塞（未重现）")
            if not row["证据引用"].startswith("不适用（未重现"):
                raise AssertionError(f"SBC 行 {row['ID']} 缺口行必须写明不适用并给出可重授权路径")
            if "可重授权路径" not in row["证据引用"]:
                raise AssertionError(f"SBC 行 {row['ID']} 缺口行缺可重授权路径")
            if not row["违规扫描裁决"].startswith("不适用"):
                raise AssertionError(f"SBC 行 {row['ID']} 无实际输出的行不得给违规扫描结论")
            if not row["采用源与相对差异"].startswith("不适用"):
                raise AssertionError(f"SBC 行 {row['ID']} 缺口行不得声称采用任何源")
            continue
        if kind == ADOPT:
            if row["ID"] != "SBC-08":
                raise AssertionError(
                    f"行 {row['ID']} 取 采用：该补值是 §2.1 枚举对 §4.2 成功行的空缺裁定，只允许 SBC-08（登记口径第 7 条）")
            if not cited_records:
                raise AssertionError("SBC-08 的 采用 行未引用任何记录对象")
            silent = sorted(rid for rid in cited_records if not returned_data(sbc_records[rid]))
            if silent:
                raise AssertionError(
                    f"SBC-08 的 采用 行引用了源未返回数据的记录 {silent}：采用须绑定确实返回数据的实测记录")
        if row["ID"] == "SBC-07":
            shapes = {returned_data(sbc_records[rid]) for rid in cited_records}
            if shapes != {True, False}:
                raise AssertionError(
                    "SBC-07 须同时引用一次空返回（不存在代码）与一次非空返回（歧义标的）的真实记录，"
                    f"现引用形状={sorted(shapes)}")
        if not row["契约符合性"].startswith("符合"):
            raise AssertionError(f"SBC 行 {row['ID']} 已重现行的契约符合性必须以 符合 起首")
        if row["违规扫描裁决"] != "无违规":
            raise AssertionError(f"SBC 行 {row['ID']} 违规扫描裁决 {row['违规扫描裁决']!r} 非 无违规")
        cited = set(ID_RE.findall(row["证据引用"]))
        if not cited:
            raise AssertionError(f"SBC 行 {row['ID']} 证据引用为空")
        if kind in {"合格备选", "公开摘要"}:
            if not (cited & src_ids):
                raise AssertionError(
                    f"SBC 行 {row['ID']} 的 {kind} 场景未引用 queries.md#单指标单源 的既有行 ID")
        lic_pairs = LIC_STATUS_RE.findall(_cells([row]))
        plain = set(re.findall(r"\bLIC-\d{2}\b", _cells([row])))
        if plain:
            for lid in plain:
                if lid not in lic_by_id:
                    raise AssertionError(f"SBC 行 {row['ID']} 引用台账不存在的 {lid}")
            stated = {lid for lid, _ in lic_pairs}
            if stated != plain:
                raise AssertionError(
                    f"SBC 行 {row['ID']} 有 LIC 引用未标注实际状态：{sorted(plain - stated)}")
            for lid, value in lic_pairs:
                if lid not in lic_by_id:
                    raise AssertionError(f"SBC 行 {row['ID']} 引用台账不存在的 {lid}")
                if lic_by_id[lid]["状态"] != value:
                    raise AssertionError(
                        f"SBC 行 {row['ID']} 记 {lid} 实际状态={value} != 台账现值 {lic_by_id[lid]['状态']}")
                if lic_by_id[lid]["用途"] != "本机自用":
                    raise AssertionError(
                        f"SBC 行 {row['ID']} 引用 {lid} 用途={lic_by_id[lid]['用途']}，与实取动作不匹配")
        elif "LIC 不适用（" not in _cells([row]):
            raise AssertionError(
                f"SBC 行 {row['ID']} 未引用被尝试动作对应的 LIC 记录，也未声明 LIC 不适用及其源层依据")


def check_split(rows: list[dict], text: str) -> None:
    gaps = {r["ID"] for r in rows if r["实际回复类别"] == GAP}
    reproduced = {r["ID"] for r in rows} - gaps
    declared = DECLARED_SPLIT_RE.search(text)
    if not declared:
        raise AssertionError("safety-branches.md 前言未声明重现/缺口的行数分布")
    if (int(declared.group(1)), int(declared.group(2))) != (len(reproduced), len(gaps)):
        raise AssertionError(
            f"前言声明 重现{declared.group(1)}/缺口{declared.group(2)} != 实测 重现{len(reproduced)}/缺口{sorted(gaps)}")


def check_sbc01_02_independent(rows: list[dict]) -> None:
    by_id = {r["ID"]: r for r in rows}
    a, b = by_id.get("SBC-01"), by_id.get("SBC-02")
    if a is None or b is None:
        raise AssertionError("SBC-01 与 SBC-02 必须都在（AC-07 完整性门禁，不得由其一占位）")
    for row, other in ((a, b), (b, a)):
        if row["实际回复类别"] == GAP:
            raise AssertionError(f"{row['ID']} 是订阅缺失/权限拒绝的独立留证行，不得为缺口行")
        if set(ID_RE.findall(row["证据引用"])) & set(ID_RE.findall(other["证据引用"])):
            raise AssertionError("SBC-01 与 SBC-02 共用同一条记录，属互相占位")
    if a["场景"] == b["场景"]:
        raise AssertionError("SBC-01 与 SBC-02 场景名不得相同")


def check_no_unsourced_figure(rows: list[dict]) -> None:
    for row in rows:
        cells = _cells([row])
        m = FIN_VALUE_RE.search(cells)
        if m:
            raise AssertionError(
                f"{row['ID']} 出现取数数值 {m.group(0)!r}：verify-only 台账只可引用行 ID，不得复制字段值")
        if RATING_RE.search(cells) and not set(re.findall(r"\b(?:QRY|SRC)-\d{2}\b", row["证据引用"])):
            raise AssertionError(f"{row['ID']} 提到评级/目标价/估值但未引用实际取数行（未支持评级）")


def _records_block(records: dict, *, where: str, run_window: dict[str, str]) -> None:
    for rid, rec in records.items():
        if tuple(rec) != VERIFY_ONLY_FIELDS:
            raise AssertionError(f"{where}/{rid} 字段 {tuple(rec)} != §2.3 verify-only 七字段")
        for field in VERIFY_ONLY_FIELDS:
            if not str(rec[field]).strip():
                raise AssertionError(f"{where}/{rid} 字段 {field} 为空")
        if not str(rec["字段清单"]).startswith("无"):
            raise AssertionError(
                f"{where}/{rid} 字段清单非「无…」：被拒/失败的动作不得有任何持久化内容")
        if not str(rec["期间覆盖"]).startswith("不适用"):
            raise AssertionError(f"{where}/{rid} 期间覆盖必须为 不适用（请求被拒）")
        ts = str(rec["检索时间"])
        if ISO_SECONDS_RE.match(ts):
            check_in_run_window({"t": ts}, run_window, time_field="t")
        elif run_window["首次采集时间"][:10] not in ts:
            raise AssertionError(f"{where}/{rid} 检索时间 {ts!r} 未落在 RunWindow 同日且非 ISO 秒级值")


def check_negative_hashes(neg: dict, anchors: dict, published: dict[str, str]) -> None:
    if set(neg) != set(published):
        raise AssertionError(f"负例记录键集 {sorted(neg)} != 锚点公布键集 {sorted(published)}")
    for rid, rec in neg.items():
        actual = sha256_record(rec)
        if actual != published[rid]:
            raise AssertionError(f"{rid} canonical SHA-256 现算 {actual} != 公布 {published[rid]}")
        if not HEX64.match(published[rid]):
            raise AssertionError(f"{rid} 公布值不是 64 位十六进制")
        if "拒绝" not in rec["结果状态"]:
            raise AssertionError(f"{rid} 结果状态不含真实拒绝原文")
    for path, value in anchors["投递件文件级SHA256"].items():
        if not HEX64.match(value):
            raise AssertionError(f"投递件锚点 {path} 非 64 位十六进制实测值")
        if _evidence.SENSITIVE_CONTENT_RE.search(path) or PRIVATE_WIN_PATH_RE.search(path):
            raise AssertionError(f"投递件锚点 {path} 含私有绝对路径")


def check_sbc_records(records: dict, published: dict[str, str], run_window: dict[str, str]) -> None:
    """round3 记录对象：§2.3 七字段、毫秒级时刻落在 RunWindow 内、canonical SHA-256 逐条重算等于锚点公布值。"""
    if set(records) != set(published):
        raise AssertionError(f"安全分支记录键集 {sorted(records)} != 锚点公布键集 {sorted(published)}")
    for rid, rec in records.items():
        if tuple(rec) != VERIFY_ONLY_FIELDS:
            raise AssertionError(f"安全分支实测记录对象/{rid} 字段 {tuple(rec)} != §2.3 verify-only 七字段")
        for field in VERIFY_ONLY_FIELDS:
            if not str(rec[field]).strip():
                raise AssertionError(f"安全分支实测记录对象/{rid} 字段 {field} 为空")
        ts = str(rec["检索时间"])
        if not MS_SECONDS_RE.match(ts):
            raise AssertionError(f"安全分支实测记录对象/{rid} 检索时间 {ts!r} 不是采集会话记录的毫秒级时刻")
        check_in_run_window({"t": ts}, run_window, time_field="t")
        m = FIN_VALUE_RE.search(json.dumps(rec, ensure_ascii=False))
        if m:
            raise AssertionError(
                f"安全分支实测记录对象/{rid} 出现取数字段值 {m.group(0)!r}：verify-only 不落响应正文与字段值")
        actual = sha256_record(rec)
        if actual != published[rid]:
            raise AssertionError(f"{rid} canonical SHA-256 现算 {actual} != 公布 {published[rid]}")
        if not HEX64.match(published[rid]):
            raise AssertionError(f"{rid} 公布值不是 64 位十六进制")


def check_fc_precision(failures: dict, run_window: dict[str, str]) -> None:
    for rid, rec in failures.items():
        ts = str(rec["检索时间"])
        if ISO_SECONDS_RE.match(ts):
            raise AssertionError(
                f"{rid} 检索时间为秒级 ISO 值，但采集回执未记逐条秒级时刻（不得补造精度）")
        if run_window["首次采集时间"][:10] not in ts:
            raise AssertionError(f"{rid} 检索时间 {ts!r} 不在 RunWindow 同日")


def check_agent(zero_diff_sha: str) -> str:
    # bytes, not read_text(): the repo checkout is CRLF and universal-newline decoding would
    # turn every \r\n into \n, so the prefix hash would no longer be the CR1 file's hash.
    text = _support.AGENT.read_bytes().decode("utf-8")
    if text.count(AGENT_SECTION) != 1:
        raise AssertionError(f"agents/equity-research.md 的新增节标题必须恰出现一次")
    idx = text.index(AGENT_SECTION)
    # The recorded CR1 SHA covers this checkout's line endings; accept either convention so the
    # assertion tests "no existing line changed" instead of testing how git happened to check out.
    candidates = {hashlib.sha256((text[:idx].rstrip("\r\n") + eol).encode("utf-8")).hexdigest()
                  for eol in ("\r\n", "\n")}
    if zero_diff_sha not in candidates:
        raise AssertionError(
            f"新增节之前的既有内容不是 CR1 版本零差异：现算 {sorted(candidates)} != index.md 登记的 {zero_diff_sha}")
    section = text[idx:]
    for token in ORD_STEPS:
        if token not in section:
            raise AssertionError(f"新增节缺 §4.1 的第 {token} 步")
    for marker in ("②之前不得发起取数", "原样保留为证据", "不接入美系机构数据源", "无来源数字",
                   "未支持的评级或目标价", "不把缓存或演示数据当本次成功", "静默换"):
        if marker not in section:
            raise AssertionError(f"新增节缺 §4.1/§4.2 的要求条目 {marker!r}")
    for scenario in ("订阅缺失", "权限拒绝", "服务不可达", "空结果", "过期数据", "冲突来源",
                     "错误", "指定历史季度", "美股个股仅公开面"):
        if scenario not in section:
            raise AssertionError(f"新增节缺 §4.2 的场景 {scenario!r}")
    if SOURCE_NAMES_RE.search(section):
        raise AssertionError("新增节引入了新的数据源/连接器名（§3.2：本节不新增任何数据源或第二技能源）")
    return section


class SafetyBranches(RepoTest):
    def setUp(self) -> None:
        self.text = (EVIDENCE / "safety-branches.md").read_text(encoding="utf-8")
        self.ord_rows = load_table("safety-branches.md", "判定顺序核对")
        self.sbc = load_table("safety-branches.md", "安全分支实测")
        self.lic = load_table("data-sources.md", "许可台账")
        self.qry = load_table("queries.md", "查询溯源")
        self.src = load_table("queries.md", "单指标单源")
        self.run_window = read_run_window()
        self.neg = load_json_block("负例核验记录对象")
        self.failures = load_json_block("失败回执摘录对象")
        self.sbc_records = load_json_block("安全分支实测记录对象")
        self.anchors = load_json_block("投递件哈希锚点")
        self.vr = load_verify_records()
        self.known = known_ids(self.ord_rows, self.sbc, self.neg, self.failures, self.lic, self.vr,
                               self.sbc_records)
        self.src_ids = {r["ID"] for r in self.src}
        self.lic_by_id = {r["ID"]: r for r in self.lic}

    # --- AC-06: ①→⑤ order with a machine check backing each step ---
    def test_ord_rows(self) -> None:
        check_ord(self.ord_rows, self._backings(), self.known)

    def test_ord02_backed_by_licence_cross_check(self) -> None:
        """② 之前的禁取数不变量：每条 QRY 行都必须引用一条 本机自用 且 已确认 的 LIC 行。"""
        for row in self.qry:
            _licence_for(row, self.lic)

    def _backings(self) -> dict[str, bool]:
        qry_ids = {r["ID"] for r in self.qry}
        return {
            "①": all(r["证券代码/交易所"].strip() and r["请求期间"].strip()
                     and r["run-id"] == self.run_window["run-id"] for r in self.qry),
            "②": all(_licence_for(r, self.lic) is not None for r in self.qry),
            "③": all(r["最终采用源"].startswith("QRY") or r["最终采用源"].startswith("无") for r in self.src),
            "④": all(("空结果" not in r["返回字段与结果状态"]) or r["是否最终采用源"] == "否"
                     for r in self.qry),
            "⑤": all(set(re.findall(r"QRY-\d{2}", r["最终采用源"])) <= qry_ids for r in self.src),
        }

    # --- AC-07: nine scenarios, SBC-01/SBC-02 independent, no expectation-only rows ---
    def test_sbc_rows(self) -> None:
        check_sbc(self.sbc, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_sbc01_and_sbc02_independent(self) -> None:
        check_sbc01_02_independent(self.sbc)

    def test_reproduced_and_gap_split_declared(self) -> None:
        check_split(self.sbc, self.text)

    def test_no_unsourced_figures(self) -> None:
        check_no_unsourced_figure(self.ord_rows + self.sbc)

    def test_refused_actions_persisted_nothing(self) -> None:
        """被拒绝的源不发生调用、持久化或导出（§4.1 不变量）。"""
        _records_block(self.neg, where="负例核验记录对象", run_window=self.run_window)
        _records_block(self.failures, where="失败回执摘录对象", run_window=self.run_window)

    def test_negative_records_match_published_hashes(self) -> None:
        check_negative_hashes(self.neg, self.anchors, self.anchors["负例记录canonicalSHA256"])

    def test_sbc_records_match_published_hashes(self) -> None:
        check_sbc_records(self.sbc_records, self.anchors["安全分支记录canonicalSHA256"], self.run_window)

    def test_failure_records_keep_source_precision(self) -> None:
        check_fc_precision(self.failures, self.run_window)

    # --- FR-06: the Agent declaration section, existing lines zero-diff ---
    def test_agent_declaration_section(self) -> None:
        intake = {r["核对项"]: r["CR1 版本/SHA"] for r in load_table("index.md", "CR1 输入核对")}
        check_agent(intake["Agent 七域声明（数据域路由）"])

    def test_agent_existing_routes_and_guards_untouched(self) -> None:
        text = _support.AGENT.read_text(encoding="utf-8")
        table = text.split("## 九项路由（恰九项）", 1)[1].split("## 数据域路由", 1)[0]
        for command, skill in NINE_PAIRS:
            self.assertIn(f"| `{command}` | `{skill}` |", table, f"九项路由被改动：{command}")
        for reason in ('Stop("data-stale")', 'Stop("no-authorization")',
                       'Stop("missing-prerequisite-model")', 'Clarify(["securities-code","exchange"])'):
            self.assertIn(reason, text, f"既有守卫 reason 缺失：{reason}")
        self.assertIn("## 安全与合规", text)

    def test_agent_new_reasons_do_not_replace_existing(self) -> None:
        section = check_agent(
            {r["核对项"]: r["CR1 版本/SHA"] for r in load_table("index.md", "CR1 输入核对")}
            ["Agent 七域声明（数据域路由）"])
        prefix = _support.AGENT.read_text(encoding="utf-8").split(AGENT_SECTION, 1)[0]
        new = set(re.findall(r'Stop\("([a-z-]+)"\)', section))
        old = set(re.findall(r'Stop\("([a-z-]+)"\)', prefix))
        self.assertTrue(new, "新增节必须带来场景层 reason")
        self.assertEqual(new & old, set(), f"新增节复用了既有 reason 语义：{sorted(new & old)}")
        self.assertEqual(new & {"data-stale"}, set())

    # --- coverage + sensitive scan ---
    def test_sensitive_scan(self) -> None:
        check_no_sensitive(self.text, where="evidence/safety-branches.md")
        self.assertIsNone(PRIVATE_WIN_PATH_RE.search(self.text), "safety-branches.md 含私有绝对路径")

    def test_coverage_counts_match(self) -> None:
        dom, tsk, reqs = load_readiness()
        computed = compute_coverage(
            load_table("data-sources.md", "安装与连接台账"),
            load_table("data-sources.md", "连接器标识分层"),
            self.lic,
            load_table("index.md", "CR1 输入核对"),
            load_table("index.md", "交付物入口"),
            dom=dom, tsk=tsk, reqs=reqs,
        )
        self.assertEqual(computed["安全场景实测数"], len(self.sbc), "安全场景实测数 != SBC 登记行数")
        check_coverage_against(computed, load_table("index.md", "覆盖率摘要"), read_coverage())

    # --- counterexamples (TASK-03 §4) ---
    def test_dropped_sbc02_row_rejected(self) -> None:
        bad = [r for r in self.sbc if r["ID"] != "SBC-02"]
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_normal_output_category_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        bad[0]["实际回复类别"] = "照常输出"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_unsourced_figure_in_row_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["实际回复类别"] != GAP)
        row["采用源与相对差异"] = "两源差异约 6.5691 亿元"
        with self.assertRaises(AssertionError):
            check_no_unsourced_figure(bad)

    def test_unsupported_rating_without_fetch_ref_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["实际回复类别"] != GAP)
        row["采用源与相对差异"] = "综合目标价上调"
        row["证据引用"] = "NZ-01"
        with self.assertRaises(AssertionError):
            check_no_unsourced_figure(bad)

    def test_gap_marker_cannot_hide_a_real_refusal(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-03")
        row["实际回复类别"] = GAP
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_green_row_cannot_be_declared_blocked(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-03")
        row["契约符合性"] = "阻塞（未重现）"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_public_summary_without_src_ref_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["实际回复类别"] == "公开摘要")
        row["证据引用"] = "QRY-06、QRY-07、QRY-08"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_missing_licence_annotation_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-01")
        row["输入/受控条件"] = "同一账户、同一入参的真实拒绝（未记许可判定面）"
        row["证据引用"] = "NZ-04；queries.md#交付边界与事实注记"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_licence_status_drift_rejected(self) -> None:
        lic = [dict(r) for r in self.lic]
        lic[0]["状态"] = "待确认"  # LIC-01 wind-finance 本机自用
        by_id = {r["ID"]: r for r in lic}
        with self.assertRaises(AssertionError):
            check_sbc(self.sbc, self.known, self.src_ids, by_id, self.sbc_records)

    def test_tampered_negative_record_rejected(self) -> None:
        neg = {k: dict(v) for k, v in self.neg.items()}
        first = sorted(neg)[0]
        neg[first]["结果状态"] = neg[first]["结果状态"] + "（改写）"
        with self.assertRaises(AssertionError):
            check_negative_hashes(neg, self.anchors, self.anchors["负例记录canonicalSHA256"])

    def test_tampered_sbc_record_rejected(self) -> None:
        recs = {k: dict(v) for k, v in self.sbc_records.items()}
        first = sorted(recs)[0]
        recs[first]["结果状态"] = recs[first]["结果状态"] + "（改写）"
        with self.assertRaises(AssertionError):
            check_sbc_records(recs, self.anchors["安全分支记录canonicalSHA256"], self.run_window)

    def test_sbc_record_outside_run_window_rejected(self) -> None:
        recs = {k: dict(v) for k, v in self.sbc_records.items()}
        first = sorted(recs)[0]
        recs[first]["检索时间"] = "2026-10-03T23:59:59.000+08:00"
        with self.assertRaises(AssertionError):
            check_sbc_records(recs, self.anchors["安全分支记录canonicalSHA256"], self.run_window)

    def test_adopt_value_on_another_row_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-04")
        row["实际回复类别"] = ADOPT
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_adopt_row_without_returned_data_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-08")
        row["证据引用"] = "SBC-07-NC；`LIC-07 实际状态=已确认`"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_sbc07_one_shape_only_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-07")
        for col in ("输入/受控条件", "采用源与相对差异", "契约符合性"):
            row[col] = "（本项引用只留证据列）"
        row["证据引用"] = "SBC-07-AT；`LIC-07 实际状态=已确认`"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_fabricated_sbc_record_id_rejected(self) -> None:
        bad = [dict(r) for r in self.sbc]
        row = next(r for r in bad if r["ID"] == "SBC-07")
        row["证据引用"] = "SBC-07-NC、SBC-07-XX；`LIC-07 实际状态=已确认`"
        with self.assertRaises(AssertionError):
            check_sbc(bad, self.known, self.src_ids, self.lic_by_id, self.sbc_records)

    def test_fabricated_seconds_in_failure_record_rejected(self) -> None:
        failures = {k: dict(v) for k, v in self.failures.items()}
        first = sorted(failures)[0]
        failures[first]["检索时间"] = "2026-10-03T16:19:00+08:00"
        with self.assertRaises(AssertionError):
            check_fc_precision(failures, self.run_window)

    def test_refused_record_with_payload_rejected(self) -> None:
        neg = {k: dict(v) for k, v in self.neg.items()}
        first = sorted(neg)[0]
        neg[first]["字段清单"] = "Wind代码、证券简称"
        with self.assertRaises(AssertionError):
            _records_block(neg, where="负例核验记录对象", run_window=self.run_window)

    def test_ord_step_order_swap_rejected(self) -> None:
        bad = [dict(r) for r in self.ord_rows]
        bad[0], bad[1] = bad[1], bad[0]
        with self.assertRaises(AssertionError):
            check_ord(bad, self._backings(), self.known)

    def test_ord_claim_without_machine_backing_rejected(self) -> None:
        backings = self._backings()
        backings["③"] = False
        with self.assertRaises(AssertionError):
            check_ord(self.ord_rows, backings, self.known)

    def test_agent_section_rename_rejected(self) -> None:
        import shutil
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp(prefix="cmd03-"))
        copy = tmp / "equity-research.md"
        original = _support.AGENT
        try:
            shutil.copyfile(original, copy)
            copy.write_text(
                original.read_text(encoding="utf-8").replace(AGENT_SECTION, "## 判定顺序（改）"),
                encoding="utf-8", newline="")
            _support.AGENT = copy
            with self.assertRaises(AssertionError):
                check_agent(
                    {r["核对项"]: r["CR1 版本/SHA"] for r in load_table("index.md", "CR1 输入核对")}
                    ["Agent 七域声明（数据域路由）"])
        finally:
            _support.AGENT = original
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
