"""cmd-02 — seven-domain queries, sample registration and traceability (FR-04/05 -> AC-04/05).

Reads `evidence/queries.md` (SMP/QRY/SRC/KJ + the versioned verify-only record objects),
`index.md#RunWindow`, `data-sources.md#许可台账` and the CR1 SampleIndex, and checks them at
object level: each QRY row's SHA-256 is recomputed from the versioned record it points at, its
timestamp is checked against RunWindow, and its licence reference is cross-checked against the
LIC row for the (source, 本机自用) action. Counterexample rows required by TASK-02 §4 are
exercised in-memory on mutated row copies; the two table-header drift cases are exercised on a
temporary copy of queries.md with `_evidence.EVIDENCE` pointed at it (no new command entry point).
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import _evidence
from _evidence import (
    EVIDENCE,
    check_in_run_window,
    check_no_sensitive,
    check_object_hash,
    check_review_path,
    load_table,
    read_coverage,
    read_run_window,
    require_ids,
    sha256_record,
)
from _support import ROOT, RepoTest
from test_08_source_ledger import check_coverage_against, compute_coverage, load_readiness

EVIDENCE_MODES = {"raw-versioned", "raw-local-only", "extract-only", "verify-only"}
# SDD §2.3: 每种留证方式要求 (源, 用途) 的 LIC=已确认 集合。逐动作 fail-closed 由这张表机检，
# 「许可未确认却切换到更宽的留证方式」在 check_qry 内即拒。
MODE_REQUIRED_USES = {
    "verify-only": ("本机自用",),
    "extract-only": ("本机自用", "研究引用展示"),
    "raw-local-only": ("本机自用", "文件中使用"),
    "raw-versioned": ("本机自用", "研究引用展示", "文件中使用"),
}
# B-CODE-01 verify-only 版本化文件禁止出现的响应字段值形态：
# (a) 财务/计数类数据值（`<数字>` 紧跟单位/百分号）
# (b) `<标识符>=<数字>` 形态的响应字段值（如 totalStocks=825、cost=156）
FORBIDDEN_FIELD_VALUE_RES = (
    re.compile(r"\d+(?:\.\d+)?\s*(?:%|亿元|万元|元)(?![A-Za-z])"),
    re.compile(r"\b(?:totalStocks|net_profit|netProfit|profit_forecast\w*|target_avg_price|institution_rating|ROE|roe)\s*[=:：]\s*-?\d"),
)
VERIFIED_USES = {"本机自用", "研究引用展示", "文件中使用"}
REQ_DATE_PAIR_RE = re.compile(
    r"(?:start_date|start|from_date|begin)\s*[=:：]\s*(\d{4})-?(\d{2})-?(\d{2})[；;]?\s*"
    r"(?:end_date|end|to_date|until)\s*[=:：]\s*(\d{4})-?(\d{2})-?(\d{2})",
    re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ADOPTED = {"是", "否"}
COND_KEYS = ("最近完整披露", "研报覆盖充分", "研报可查", "合法使用权")
VERIFY_ONLY_FIELDS = ("请求条件", "源与工具", "结果状态", "期间覆盖", "字段清单", "响应标识", "检索时间")
SEVEN_DOMAINS = (
    "机构财务、公告、事件", "券商一致预期", "研报评级、目标价、全文", "公开行情、K 线、公告、日历",
    "筛选", "宏观", "资金、龙虎榜、两融",
)
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
QRY_ID_RE = re.compile(r"\AQRY-\d{2}\Z")
LIC_REF_RE = re.compile(r"\bLIC-\d{2}\b")
RECORD_REF_RE = re.compile(r"#核验记录对象/(VR-\d{2})\Z")
# TASK-02 §4 counterexample: a Windows private absolute path in a row. dep-3's official pattern
# only matches the JSON-escaped double-backslash form, so the single-backslash form needs its own
# check here (the export script's patterns stay zero-diff per SDD §3.2).
PRIVATE_WIN_PATH_RE = re.compile(r"[A-Za-z]:[\\/]{1,2}users[\\/]", re.IGNORECASE)


def load_verify_records() -> dict[str, dict]:
    """The versioned verify-only record objects inside queries.md's `核验记录对象` fenced block."""
    text = (EVIDENCE / "queries.md").read_text(encoding="utf-8")
    m = re.search(r"^## 核验记录对象\s*$", text, re.MULTILINE)
    if not m:
        raise AssertionError("queries.md 缺 `核验记录对象` 节（verify-only 证据对象未版本化）")
    block = re.search(r"```json\s*(.*?)\s*```", text[m.end():], re.DOTALL)
    if not block:
        raise AssertionError("queries.md#核验记录对象 缺 json 机器块")
    records = json.loads(block.group(1))
    if not isinstance(records, dict) or not records:
        raise AssertionError("queries.md#核验记录对象 记录集合为空")
    return records


def _cr1_sample_index() -> dict[str, str]:
    """CR1 README §3 SampleIndex machine block (read-only, verbatim source for SMP-01)."""
    text = (ROOT / "workbuddy-experts" / "equity-research" / "README.md").read_text(encoding="utf-8")
    m = re.search(r"<!-- sample-index:start -->\s*```ya?ml\s*(.*?)\s*```", text, re.DOTALL)
    if not m:
        raise AssertionError("CR1 README §3 SampleIndex 机器块缺失")
    fields = {}
    for ln in m.group(1).splitlines():
        if re.match(r"^\s*-\s", ln) or ":" not in ln or ln.startswith(" "):
            continue
        key, _, value = ln.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def check_smp(rows: list[dict]) -> None:
    require_ids(rows, "SMP", minimum=1)
    for r in rows:
        for col in ("ID", "样例来源", "适用数据域与任务", "证券代码", "交易所", "报告期间", "披露日期",
                    "来源与版本", "四条件核验与依据", "原件位置与 SHA-256", "裁决人", "裁决日期"):
            if not r[col].strip():
                raise AssertionError(f"SMP 行 {r['ID']} 字段 {col} 为空")
        for key in COND_KEYS:
            if not re.search(rf"{key}=已核实", r["四条件核验与依据"]):
                raise AssertionError(f"SMP 行 {r['ID']} 四条件 {key} 未逐项记 已核实")
        if r["样例来源"] not in {"CR1固定样例", "本CR补充"}:
            raise AssertionError(f"SMP 行 {r['ID']} 样例来源 {r['样例来源']!r} 不在封闭取值")
        original = r["原件位置与 SHA-256"].strip()
        if r["样例来源"] == "本CR补充":
            if "::" not in original or not HEX64.match(original.rsplit("::", 1)[1]):
                raise AssertionError(f"SMP 行 {r['ID']} 本CR补充样例缺原件 SHA-256 实测值: {original!r}")
            if _evidence.SENSITIVE_CONTENT_RE.search(original) or PRIVATE_WIN_PATH_RE.search(original):
                raise AssertionError(
                    f"SMP 行 {r['ID']} 原件位置未以可交付引用登记（私有绝对路径不得充当唯一证据）: {original!r}")
        if r["交易所"] not in {".SH", ".SZ", ".BJ", ".HK", "SH", "SZ", "BJ", "HK"}:
            raise AssertionError(f"SMP 行 {r['ID']} 交易所 {r['交易所']!r} 不在许可取值")


def check_smp01_verbatim_smp01(rows: list[dict]) -> None:
    smp01 = next((r for r in rows if r["ID"] == "SMP-01"), None)
    if smp01 is None:
        raise AssertionError("缺 SMP-01（CR1 SAMPLE-01 只读沿用行）")
    if smp01["样例来源"] != "CR1固定样例":
        raise AssertionError("SMP-01 样例来源必须是 CR1固定样例（只读沿用，不重新裁决）")
    index = _cr1_sample_index()
    for col, key in (("证券代码", "securities-code"), ("交易所", "exchange"), ("披露日期", "disclosure-date"),
                     ("裁决人", "adjudicator"), ("裁决日期", "verified-at")):
        want = index.get(key, "")
        if smp01[col].strip('"') != want:
            raise AssertionError(f"SMP-01 {col} {smp01[col]!r} != CR1 索引逐字值 {want!r}")
    want_original = index.get("original-files", "").strip("[]")
    if smp01["原件位置与 SHA-256"] != want_original:
        raise AssertionError(f"SMP-01 原件位置与 SHA-256 未逐字取自 CR1 索引: {smp01['原件位置与 SHA-256']!r}")


def _licence_for(row: dict, lic: list[dict]) -> dict:
    """Cross-check the (源, 动作=本机查询/实取 ⇒ 用途=本机自用) LIC row referenced by 复核路径,
    then per SDD §2.2/§2.3 assert every use required by 留证方式 has a 已确认 LIC for that 入口."""
    refs = LIC_REF_RE.findall(row["复核路径"])
    if not refs:
        raise AssertionError(f"QRY 行 {row['ID']} 复核路径未引用 LIC 记录")
    entry = row["源"].split("（")[0].split("／")[0].strip()
    hits = [r for r in lic if r["ID"] in refs]
    for hit in hits:
        if hit["状态"] != "已确认":
            raise AssertionError(f"QRY 行 {row['ID']} 引用的 LIC 行 {hit['ID']} 状态={hit['状态']}，非 已确认")
        if hit["用途"] != "本机自用":
            raise AssertionError(f"QRY 行 {row['ID']} 引用 {hit['ID']} 用途={hit['用途']}，与实取动作不匹配")
    matched = [hit for hit in hits if hit["入口"] == entry]
    if not matched:
        raise AssertionError(f"QRY 行 {row['ID']} 的源 {entry!r} 无对应 已确认 的本机自用 LIC 行（引用 {refs}）")
    # SDD §2.3：留证方式所要求的每一种用途都必须在该入口有 LIC=已确认，否则 fail-closed
    for use in MODE_REQUIRED_USES[row["留证方式"]]:
        ok = any(l["入口"] == entry and l["用途"] == use and l["状态"] == "已确认" for l in lic)
        if not ok:
            raise AssertionError(
                f"QRY 行 {row['ID']} 留证方式={row['留证方式']} 要求 ({entry}, {use}) LIC=已确认，"
                f"实际未获准（SDD §2.2 不变量 2/§2.3 逐动作 fail-closed）")
    return matched[0]


def _forbid_field_values(text: str, *, where: str) -> None:
    for pat in FORBIDDEN_FIELD_VALUE_RES:
        m = pat.search(text)
        if m:
            raise AssertionError(
                f"{where} 出现 verify-only 不允许的响应字段值形态 {m.group(0)!r}（SDD §2.3 不复制字段值）")


def _extract_request_dates(conditions: str) -> tuple[str, str] | None:
    m = REQ_DATE_PAIR_RE.search(conditions)
    if not m:
        return None
    y1, mo1, d1, y2, mo2, d2 = m.groups()
    return (f"{y1}-{mo1}-{d1}", f"{y2}-{mo2}-{d2}")


def _date_span(text: str) -> tuple[str, str] | None:
    ds = ISO_DATE_RE.findall(text)
    if not ds:
        return None
    return (min(ds), max(ds))


def check_qry(rows: list[dict], smp: list[dict], records: dict[str, dict],
              lic: list[dict], run_window: dict[str, str]) -> None:
    require_ids(rows, "QRY", minimum=7)
    verified_samples = [r for r in smp if all(
        re.search(rf"{key}=已核实", r["四条件核验与依据"]) for key in COND_KEYS)
        and r["裁决人"].strip() and r["裁决日期"].strip()]
    for row in rows:
        for col in ("ID", "数据域", "适用任务", "run-id", "查询日期", "查询条件", "证券代码/交易所", "请求期间",
                    "源", "口径", "返回字段与结果状态", "数据/获取时间戳", "原始链接或文件引用", "留证方式",
                    "证据对象引用", "SHA-256", "复核路径", "是否最终采用源"):
            if not row[col].strip():
                raise AssertionError(f"QRY 行 {row['ID']} 字段 {col} 为空")
        text = " ".join(row.values())
        if _evidence.SENSITIVE_CONTENT_RE.search(text) or PRIVATE_WIN_PATH_RE.search(text):
            raise AssertionError(f"QRY 行 {row['ID']} 含私有绝对路径或凭据形态: {text[:80]!r}")
        if row["留证方式"] not in EVIDENCE_MODES:
            raise AssertionError(f"QRY 行 {row['ID']} 留证方式 {row['留证方式']!r} 不在封闭枚举")
        if row["是否最终采用源"] not in ADOPTED:
            raise AssertionError(f"QRY 行 {row['ID']} 是否最终采用源 {row['是否最终采用源']!r} 不在枚举")
        if row["run-id"] != run_window["run-id"]:
            raise AssertionError(f"QRY 行 {row['ID']} run-id {row['run-id']!r} != RunWindow {run_window['run-id']!r}")
        check_in_run_window(row, run_window, time_field="数据/获取时间戳")
        check_review_path(row)
        _licence_for(row, lic)

        # evidence object exists (versioned) and the row hash equals the measured canonical hash
        ref = RECORD_REF_RE.search(row["证据对象引用"].strip())
        if not ref:
            raise AssertionError(f"QRY 行 {row['ID']} 证据对象引用未指向版本化记录: {row['证据对象引用']!r}")
        record = records.get(ref.group(1))
        if record is None:
            raise AssertionError(f"QRY 行 {row['ID']} 证据对象 {ref.group(1)} 不存在于版本化记录块")
        if row["留证方式"] == "verify-only":
            if tuple(record) != VERIFY_ONLY_FIELDS:
                raise AssertionError(
                    f"QRY 行 {row['ID']} verify-only 记录字段 {tuple(record)} != §2.3 七字段（不得含响应正文）")
            for key in ("结果状态", "字段清单", "期间覆盖"):
                _forbid_field_values(record[key], where=f"QRY 行 {row['ID']} verify-only 记录 {key}")
            # 记录自身检索时间必须落 RunWindow（对象时间出窗而行时间在窗是 B-CODE-04 反例）
            check_in_run_window({"t": record["检索时间"]}, run_window, time_field="t")
        _forbid_field_values(row["口径"], where=f"QRY 行 {row['ID']} 口径")
        _forbid_field_values(row["返回字段与结果状态"], where=f"QRY 行 {row['ID']} 返回字段与结果状态")
        check_object_hash(row, record=record)

        # 6(a) sample identity layer: securities code + exchange must equal a verified SMP row
        code_exchange = row["证券代码/交易所"].strip()
        sample = None
        if code_exchange.startswith("不适用"):
            if "（" not in code_exchange:
                raise AssertionError(f"QRY 行 {row['ID']} 标 不适用 未注明 FR-05 非财报类口径依据")
        else:
            code, _, exchange = code_exchange.partition("/")
            matched = [s for s in verified_samples
                       if s["证券代码"].strip('"') == code.strip() and s["交易所"].strip(".") == exchange.strip()]
            if not matched:
                raise AssertionError(
                    f"QRY 行 {row['ID']} 证券代码/交易所 {code_exchange!r} 无四条件全部已核实的 SMP 行对应")
            sample = matched[0]

        # 6(b) request-period layer
        period = row["请求期间"].strip()
        if period.startswith("不适用"):
            if "（" not in period:
                raise AssertionError(f"QRY 行 {row['ID']} 请求期间 标 不适用 未注明口径依据")
        else:
            # 请求期间 必须原样承载 查询条件 中 start/end 参数（§2.2 不变量 6(b)：结果覆盖不得反写请求）
            req_dates = _extract_request_dates(row["查询条件"])
            period_span = _date_span(period)
            if req_dates is not None:
                if period_span is None or not (period_span[0] <= req_dates[0] and req_dates[1] <= period_span[1]):
                    raise AssertionError(
                        f"QRY 行 {row['ID']} 请求期间 {period!r} 未原样承载查询条件参数区间 {req_dates}"
                        f"（§2.2 不变量 6(b)：返回覆盖不能改写本次请求期间）")
            coverage = record["期间覆盖"]
            # 证据对象的期间覆盖必须 ⊆ 请求期间（非交易日截断合法，反写或扩张非法）
            cov_span = _date_span(coverage)
            if req_dates is not None:
                if cov_span is not None and period_span is not None:
                    if not (period_span[0] <= cov_span[0] and cov_span[1] <= period_span[1]):
                        raise AssertionError(
                            f"QRY 行 {row['ID']} 证据对象期间覆盖 {cov_span} 越出请求期间 {period_span}"
                            f"（§2.2 不变量 6(b)：覆盖 ⊆ 请求）")
            elif period not in coverage:
                raise AssertionError(
                    f"QRY 行 {row['ID']} 请求期间 {period!r} 与证据对象期间覆盖 {coverage!r} 不一致")
            if sample is not None and "同一原件复取" in row["查询条件"]:
                if period != sample["报告期间"]:
                    raise AssertionError(
                        f"QRY 行 {row['ID']} 对同一样例原件的复取/复核行 请求期间 {period!r} != SMP 报告期间 "
                        f"{sample['报告期间']!r}")
        if "空结果" in row["返回字段与结果状态"]:
            if row["是否最终采用源"] != "否":
                raise AssertionError(f"QRY 行 {row['ID']} 空结果行不得标最终采用源=是（空结果≠有效零值）")
            if "空结果" not in row["口径"] and "空结果" not in row["返回字段与结果状态"]:
                raise AssertionError(f"QRY 行 {row['ID']} 未区分空结果与有效零值")

    for domain in SEVEN_DOMAINS:
        adopted = [r for r in rows if r["数据域"] == domain and r["是否最终采用源"] == "是"]
        if not adopted:
            raise AssertionError(f"数据域 {domain!r} 无采用行（七域逐域至少一条成功实取或明确缺口）")
        if not any("成功" in r["返回字段与结果状态"] for r in adopted):
            raise AssertionError(f"数据域 {domain!r} 的采用行缺真实成功状态")


def check_src(rows: list[dict], kj: list[dict], qry: list[dict]) -> None:
    require_ids(rows, "SRC", minimum=1)
    qry_ids = {r["ID"] for r in qry}
    seen: dict[str, str] = {}
    for row in rows:
        for col in ("指标", "候选源与逐项差异", "最终采用源", "裁决依据"):
            if not row[col].strip():
                raise AssertionError(f"SRC 行 {row['ID']} 字段 {col} 为空")
            _forbid_field_values(row[col], where=f"SRC 行 {row['ID']} {col}")
        adopted = row["最终采用源"].strip()
        if adopted.startswith("无"):
            continue  # explicit non-adoption with a recorded gap
        for ref in re.findall(r"QRY-\d{2}", adopted):
            if ref not in qry_ids:
                raise AssertionError(f"SRC 行 {row['ID']} 采用源引用不存在的 QRY 行 {ref}")
        if adopted not in seen.setdefault(row["指标"], adopted):
            raise AssertionError(
                f"指标 {row['指标']!r} 出现两个采用源：{seen[row['指标']]!r} 与 {adopted!r}（同一任务同一指标恰一个）")
        if "neodata" in row["候选源与逐项差异"] and adopted != "无":
            if not any("neodata" in k["源"] for k in kj):
                raise AssertionError(f"SRC 行 {row['ID']} 以 neodata 作候选源但无对应口径审查行（§4.4）")
    if not any("neodata" in k["源"] for k in kj) and any(
            "neodata" in row["候选源与逐项差异"] for row in rows):
        raise AssertionError("neodata 备选未经口径审查（§4.4「无记录不得进入备选」）")


def check_kj(rows: list[dict]) -> None:
    require_ids(rows, "KJ", minimum=1)
    for row in rows:
        for col in ("源", "审查项", "结论"):
            if not row[col].strip():
                raise AssertionError(f"口径审查 行 {row['ID']} 字段 {col} 为空")
            _forbid_field_values(row[col], where=f"口径审查 行 {row['ID']} {col}")


def check_no_hk_sample_rows(smp: list[dict], qry: list[dict]) -> None:
    """HK sample right is not adjudicated, so no .HK row may be registered or queried (§4.4)."""
    if any(s["交易所"].endswith("HK") for s in smp):
        raise AssertionError("存在 .HK 样例登记行，但港股样例合法使用权未核实（不得进入任何 QRY 行）")
    if any("/HK" in q["证券代码/交易所"] or ".HK" in q["证券代码/交易所"] for q in qry):
        raise AssertionError("存在以未核实港股样例填报的 QRY 行")


class QueryTraceability(RepoTest):
    def setUp(self) -> None:
        self.run_window = read_run_window()
        self.smp = load_table("queries.md", "样例登记")
        self.qry = load_table("queries.md", "查询溯源")
        self.src = load_table("queries.md", "单指标单源")
        self.kj = load_table("queries.md", "口径审查")
        self.lic = load_table("data-sources.md", "许可台账")
        self.records = load_verify_records()

    # --- AC-04: sample registration + per-domain real fetch ---
    def test_smp_rows(self) -> None:
        check_smp(self.smp)

    def test_smp01_verbatim_from_cr1_index(self) -> None:
        check_smp01_verbatim_smp01(self.smp)

    def test_qry_rows(self) -> None:
        check_qry(self.qry, self.smp, self.records, self.lic, self.run_window)

    def test_src_and_kj_rows(self) -> None:
        check_src(self.src, self.kj, self.qry)
        check_kj(self.kj)

    def test_hk_sample_stays_blocked(self) -> None:
        check_no_hk_sample_rows(self.smp, self.qry)

    def test_all_seven_domains_use_versioned_records(self) -> None:
        used = {RECORD_REF_RE.search(r["证据对象引用"].strip()).group(1)
                for r in self.qry if RECORD_REF_RE.search(r["证据对象引用"].strip())}
        self.assertEqual(len(used), len(self.qry), "QRY 行未逐条绑定唯一的版本化记录对象")
        self.assertTrue(set(used) <= set(self.records), "QRY 引用的记录对象未全部版本化")

    # --- counterexamples (TASK-02 §4) ---
    def test_tampered_sha256_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["SHA-256"] = "0" * 64
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_illegal_evidence_mode_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["留证方式"] = "raw-remote"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_private_windows_path_in_row_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["原始链接或文件引用"] = r"C:\Users\someone\outputs\verify-records.json"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_record_body_leak_rejected(self) -> None:
        """verify-only 记录加入响应正文 ⇒ 字段集合偏离 §2.3，必须拒绝。"""
        records = {k: dict(v) for k, v in self.records.items()}
        records["VR-01"]["响应正文"] = "…"
        with self.assertRaises(AssertionError):
            check_qry(self.qry, self.smp, records, self.lic, self.run_window)

    def test_unregistered_securities_code_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["证券代码/交易所"] = "600519/SH"  # 未登记 SMP 行（SDD §2.2 6(a)）
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_unverified_sample_rejected(self) -> None:
        smp = [dict(r) for r in self.smp]
        smp[0]["四条件核验与依据"] = smp[0]["四条件核验与依据"].replace("合法使用权=已核实", "合法使用权=未核实")
        with self.assertRaises(AssertionError):
            check_qry(self.qry, smp, self.records, self.lic, self.run_window)

    def test_period_mismatch_against_evidence_coverage_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["请求期间"] = "2027 年半年度"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_same_original_refetch_period_must_equal_sample_period(self) -> None:
        """同一原件复取/复核行的 请求期间 必须等于该 SMP 报告期间。"""
        row = dict(self.qry[0])
        record = dict(self.records["VR-01"])
        row["查询条件"] = "同一原件复取/复核：" + row["查询条件"]
        row["请求期间"] = "2024 年报"
        record["期间覆盖"] = row["请求期间"]
        row["SHA-256"] = sha256_record(record)
        rows = [dict(r) for r in self.qry]
        rows[0] = row
        with self.assertRaises(AssertionError):
            check_qry(rows, self.smp, {**self.records, "VR-01": record}, self.lic, self.run_window)

    def test_historical_quarter_row_passes(self) -> None:
        """已授权源可返回指定历史季度：成功行按原请求期间留证，不得因与样例选取期间不等而失败。"""
        row = dict(self.qry[0])
        record = dict(self.records["VR-01"])
        record["期间覆盖"] = "2025 年第一季度（2025-03-31），单期"
        row["请求期间"] = "2025 年第一季度（2025-03-31）"
        row["SHA-256"] = sha256_record(record)
        rows = [dict(r) for r in self.qry]
        rows[0] = row
        check_qry(rows, self.smp, {**self.records, "VR-01": record}, self.lic, self.run_window)

    def test_duplicate_adopted_source_rejected(self) -> None:
        bad = [dict(r) for r in self.src] + [dict(self.src[0])]
        bad[-1]["ID"] = "SRC-99"
        bad[-1]["最终采用源"] = "QRY-03（重复采用）"
        with self.assertRaises(AssertionError):
            check_src(bad, self.kj, self.qry)

    def test_neodata_candidate_without_calibration_rejected(self) -> None:
        kj = [dict(r) for r in self.kj if "neodata" not in r["源"]]
        with self.assertRaises(AssertionError):
            check_src(self.src, kj, self.qry)

    def test_adopted_empty_result_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        empty = next(i for i, r in enumerate(bad) if "空结果" in r["返回字段与结果状态"])
        bad[empty]["是否最终采用源"] = "是"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_licence_not_confirmed_rejected(self) -> None:
        lic = [dict(r) for r in self.lic]
        lic[0]["状态"] = "待确认"  # LIC-01 wind-finance 本机自用
        with self.assertRaises(AssertionError):
            check_qry(self.qry, self.smp, self.records, lic, self.run_window)

    # --- B-CODE-01 反例：verify-only 复制响应字段值 / 许可未确认却切换留证方式 ---
    def test_verify_only_field_value_leak_rejected(self) -> None:
        """SDD §2.3 verify-only 不复制字段值：totalStocks 具体数值塞回 VR-07 必须失败。"""
        records = {k: dict(v) for k, v in self.records.items()}
        records["VR-07"]["结果状态"] = "成功；totalStocks=825（表达式 ...）"
        with self.assertRaises(AssertionError):
            check_qry(self.qry, self.smp, records, self.lic, self.run_window)

    def test_verify_only_financial_unit_value_rejected(self) -> None:
        """财务数值+单位（如 6.5691 亿元）在 QRY 行内即越界。"""
        bad = [dict(r) for r in self.qry]
        bad[0]["口径"] = bad[0]["口径"] + "；净利润=6.5691 亿元"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_src_row_field_value_leak_rejected(self) -> None:
        bad = [dict(r) for r in self.src]
        bad[0]["候选源与逐项差异"] = "QRY-01 wind-finance（6.5691 亿元）／QRY-03 neodata（656907533 元）"
        with self.assertRaises(AssertionError):
            check_src(bad, self.kj, self.qry)

    def test_kj_row_field_value_leak_rejected(self) -> None:
        bad = [dict(r) for r in self.kj]
        bad[1]["结论"] = "656907533 元 与 6.5691 亿元 一致"
        with self.assertRaises(AssertionError):
            check_kj(bad)

    def test_extract_mode_switch_without_citation_licence_rejected(self) -> None:
        """研究引用展示=待确认时把 verify-only 切 extract-only 必须失败（§2.2 不变量 2）。"""
        bad = [dict(r) for r in self.qry]
        bad[0]["留证方式"] = "extract-only"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_raw_versioned_mode_switch_without_file_licence_rejected(self) -> None:
        bad = [dict(r) for r in self.qry]
        bad[0]["留证方式"] = "raw-versioned"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    # --- B-CODE-04 反例：请求期间被返回覆盖反写 / 对象时间出窗 / 换记录 ---
    def test_request_period_rewritten_by_result_coverage_rejected(self) -> None:
        """QRY-06 请求 end=2026-10-03，把 请求期间 改成截断到 2026-09-30 即反写。"""
        bad = [dict(r) for r in self.qry]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "QRY-06")
        bad[idx]["请求期间"] = "2026-09-16～2026-09-30"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_object_time_outside_row_window_rejected(self) -> None:
        """证据对象检索时间出 RunWindow、而行 数据/获取时间戳 仍在窗：对象时间落窗断言必须拒。"""
        records = {k: dict(v) for k, v in self.records.items()}
        records["VR-01"]["检索时间"] = "2026-10-05T09:00:00+08:00"
        with self.assertRaises(AssertionError):
            check_qry(self.qry, self.smp, records, self.lic, self.run_window)

    def test_qry_bound_to_wrong_record_rejected(self) -> None:
        """换记录（QRY-06 指向 VR-07）：SHA-256 与 canonical hash 不等必须拒。"""
        bad = [dict(r) for r in self.qry]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "QRY-06")
        bad[idx]["证据对象引用"] = "workbuddy-experts/equity-research/evidence/queries.md#核验记录对象/VR-07"
        with self.assertRaises(AssertionError):
            check_qry(bad, self.smp, self.records, self.lic, self.run_window)

    def test_non_trading_truncation_still_passes(self) -> None:
        """合法非交易日截断（请求 09-16～10-03、覆盖 09-16～09-30）仍必须通过（positive case）。"""
        check_qry(self.qry, self.smp, self.records, self.lic, self.run_window)

    # --- header drift counterexamples on a temporary copy of the table file ---
    def _load_from_mutated_file(self, mutate) -> None:
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="cmd02-"))
        original = _evidence.EVIDENCE
        try:
            shutil.copytree(original, tmp / "evidence")
            path = tmp / "evidence" / "queries.md"
            text = path.read_text(encoding="utf-8")
            path.write_text(mutate(text), encoding="utf-8")
            _evidence.EVIDENCE = tmp / "evidence"
            load_table("queries.md", "样例登记")
        finally:
            _evidence.EVIDENCE = original
            shutil.rmtree(tmp, ignore_errors=True)

    def test_dropped_sample_column_rejected(self) -> None:
        def mutate(text: str) -> str:
            header = "| ID | 样例来源 | 适用数据域与任务 | 证券代码 |"
            return text.replace(header, "| ID | 适用数据域与任务 | 证券代码 |", 1)
        with self.assertRaises(AssertionError):
            self._load_from_mutated_file(mutate)

    def test_swapped_sample_columns_rejected(self) -> None:
        def mutate(text: str) -> str:
            return text.replace("| 证券代码 | 交易所 |", "| 交易所 | 证券代码 |", 1)
        with self.assertRaises(AssertionError):
            self._load_from_mutated_file(mutate)

    # --- sensitive scan over the versioned ledger (dep-3 patterns + Windows private path form) ---
    def test_queries_md_passes_sensitive_scan(self) -> None:
        text = (EVIDENCE / "queries.md").read_text(encoding="utf-8")
        check_no_sensitive(text, where="evidence/queries.md")
        m = PRIVATE_WIN_PATH_RE.search(text)
        self.assertIsNone(m, "queries.md 含 Windows 私有绝对路径")

    # --- coverage: computed here == index.md summary == coverage.json (same source as cmd-01) ---
    def test_coverage_counts_match(self) -> None:
        intake = load_table("index.md", "CR1 输入核对")
        deliverables = load_table("index.md", "交付物入口")
        summary = load_table("index.md", "覆盖率摘要")
        dom, tsk, reqs = load_readiness()
        computed = compute_coverage(self._lat(), self._con(), self.lic, intake, deliverables,
                                     dom=dom, tsk=tsk, reqs=reqs)
        self.assertEqual(computed["七域实取成功数"], 7, "七域采用行数与实取成功数不一致")
        check_coverage_against(computed, summary, read_coverage())

    @staticmethod
    def _lat():
        return load_table("data-sources.md", "安装与连接台账")

    @staticmethod
    def _con():
        return load_table("data-sources.md", "连接器标识分层")


if __name__ == "__main__":
    unittest.main()
