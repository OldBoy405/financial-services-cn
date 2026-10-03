"""Shared evidence parser + object-level checks for CR-2026-002 (cmd-01..cmd-05).

Stdlib only (pathlib/re/hashlib/json/importlib/unittest). Follows CR1's `_support.py`
convention: ROOT = parents[3], files read from the real repo, missing prerequisite is a
loud AssertionError (dep-9). Reuses the export script's SENSITIVE_NAME_RE /
SENSITIVE_CONTENT_RE as the single source of truth for the sensitive scan (dep-3) so
evidence text and package exports are screened by the identical patterns.

The `TABLE_COLUMNS` registry below is the interface contract (TASK-01 §6): key is
"<file>#<heading>", value is the fixed column-name tuple. Column names and their order
are load-bearing; a mismatch is an AssertionError, never a silent rename/add/drop.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "workbuddy-experts" / "equity-research"
EVIDENCE = EXP / "evidence"
RAW = EVIDENCE / "raw"
IGNORED = ROOT / "out" / "evidence" / "data-authorization"
COVERAGE = IGNORED / "coverage.json"

# dep-3: the export script owns the sensitive patterns; load them, don't copy them.
def _load_export_patterns():
    spec = importlib.util.spec_from_file_location(
        "export_workbuddy_experts", ROOT / "scripts" / "export_workbuddy_experts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # module body defines regexes only (__main__ guarded)
    return module.SENSITIVE_NAME_RE, module.SENSITIVE_CONTENT_RE


SENSITIVE_NAME_RE, SENSITIVE_CONTENT_RE = _load_export_patterns()

# TASK-01 §6: full key set + column tuples, verbatim. Keys for tables whose DATA is
# written by a later TASK (queries/safety-branches/reinstall/domain-readiness/declarations)
# are registered here so those downstream tables inherit a fixed column contract.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "index.md#RunWindow": ("字段", "值"),
    "index.md#CR1 输入核对": ("核对项", "CR1 版本/SHA", "证据位置", "核对结果"),
    "index.md#交付物入口": ("交付物类别", "入口路径", "说明"),
    "index.md#覆盖率摘要": ("指标", "计数", "生成时间"),
    "data-sources.md#安装与连接台账": (
        "ID", "层", "目标机识别结果与版本", "连接与授权路径", "账号权限",
        "许可主体", "实际工具与动作", "验证日期", "结果状态",
    ),
    "data-sources.md#连接器标识分层": (
        "ID", "manifest ID", "目标版本是否识别", "识别依据", "分层归属",
        "与路由名/服务名的关系",
    ),
    "data-sources.md#许可台账": (
        "ID", "入口", "用途", "覆盖范围与依据", "状态", "凭据存储机制与授权路径",
    ),
    "queries.md#样例登记": (
        "ID", "样例来源", "适用数据域与任务", "证券代码", "交易所", "报告期间",
        "披露日期", "来源与版本", "四条件核验与依据", "原件位置与 SHA-256",
        "裁决人", "裁决日期",
    ),
    "queries.md#查询溯源": (
        "ID", "数据域", "适用任务", "run-id", "查询日期", "查询条件",
        "证券代码/交易所", "请求期间", "源", "口径", "返回字段与结果状态",
        "数据/获取时间戳", "原始链接或文件引用", "留证方式", "证据对象引用",
        "SHA-256", "复核路径", "是否最终采用源",
    ),
    "queries.md#单指标单源": ("ID", "指标", "候选源与逐项差异", "最终采用源", "裁决依据"),
    "queries.md#口径审查": ("ID", "源", "审查项", "结论"),
    "safety-branches.md#判定顺序核对": ("ID", "顺序步骤", "可观察证据", "按序结论"),
    "safety-branches.md#安全分支实测": (
        "ID", "场景", "输入/受控条件", "实际回复类别", "采用源与相对差异",
        "证据引用", "契约符合性", "违规扫描裁决",
    ),
    "reinstall.md#重装步骤": (
        "ID", "阶段", "实际步骤", "客户端/校验器/包版本", "结果", "证据引用",
    ),
    "reinstall.md#环境依赖排查": ("ID", "排查对象", "方法", "结果", "影响"),
    "reinstall.md#重装后复现": ("ID", "复现项", "结果", "证据引用", "是否可复现"),
    "domain-readiness.md#域状态": (
        "ID", "数据域", "状态", "已验证范围", "缺口", "许可引用", "证据引用", "适用任务",
    ),
    "domain-readiness.md#任务就绪": (
        "ID", "CR1 映射行", "必需数据域", "必需查询集 REQ-NN", "覆盖计数", "已可用域",
        "尚不能支持完整版的原因", "状态", "证据引用", "未覆盖 REQ-NN",
    ),
    "declarations.md#声明修正": (
        "ID", "触发", "涉及文件", "前后差异", "回归范围", "回归证据", "结论",
    ),
}

_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(.*?)\s*$")


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def load_table(file_name: str, heading: str) -> list[dict[str, str]]:
    """Parse one markdown table under `heading` in evidence/<file_name>, keyed by §6."""
    key = f"{file_name}#{heading}"
    expected = TABLE_COLUMNS.get(key)
    if expected is None:
        raise AssertionError(f"unregistered table key: {key}")
    path = EVIDENCE / file_name
    if not path.is_file():
        raise AssertionError(f"missing evidence file: {path.relative_to(ROOT).as_posix()}")
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, ln in enumerate(lines):
        m = _HEADING_RE.match(ln)
        if m and m.group(1) == heading:
            start = i + 1
            break
    if start is None:
        raise AssertionError(f"{file_name}: heading '{heading}' not found")
    body = []
    for ln in lines[start:]:
        if _HEADING_RE.match(ln):
            break
        body.append(ln)
    rows = [ln.strip() for ln in body if ln.strip().startswith("|")]
    if len(rows) < 2:
        raise AssertionError(f"{key}: table needs a header row and a separator row")
    header = _split_row(rows[0])
    if tuple(header) != expected:
        raise AssertionError(f"{key}: columns {tuple(header)} != contract {expected}")
    data = []
    for ln in rows[2:]:  # rows[1] is the |---| separator
        cells = _split_row(ln)
        if len(cells) != len(expected):
            raise AssertionError(f"{key}: row width {len(cells)} != {len(expected)} in {ln!r}")
        data.append(dict(zip(expected, cells)))
    return data


def read_run_window() -> dict[str, str]:
    return {r["字段"]: r["值"] for r in load_table("index.md", "RunWindow")}


def require_ids(rows: Sequence[Mapping[str, str]], prefix: str, *, minimum: int) -> list[str]:
    seen = {r.get("ID", "") for r in rows}
    want = [f"{prefix}-{n:02d}" for n in range(1, minimum + 1)]
    missing = [i for i in want if i not in seen]
    if missing:
        raise AssertionError(f"missing {prefix} ids (need {minimum}): {missing}")
    return want


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_record(record: object) -> str:
    blob = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def check_object_hash(row: Mapping[str, str], *, obj_path: Path | None = None,
                      record: object | None = None) -> None:
    """Assert the row's SHA-256 equals the measured hash of its evidence object.

    `obj_path` hashes raw bytes (raw-versioned / raw-local-only); `record` hashes the
    canonical serialization (extract-only / verify-only). Exactly one is required (§2.3).
    """
    if obj_path is not None:
        actual = sha256_bytes(Path(obj_path).read_bytes())
    elif record is not None:
        actual = sha256_record(record)
    else:
        raise AssertionError("check_object_hash needs obj_path or record")
    declared = row.get("SHA-256")
    if declared != actual:
        raise AssertionError(f"SHA-256 mismatch: row {declared!r} != measured {actual!r}")


def check_in_run_window(row: Mapping[str, str], run_window: Mapping[str, str],
                        *, time_field: str) -> None:
    ts = (row.get(time_field) or "").strip()
    lo = (run_window.get("首次采集时间") or "").strip()
    hi = (run_window.get("末次采集时间") or "").strip()
    if not (lo and hi and ts):
        raise AssertionError(f"RunWindow bounds or {time_field} missing")
    if not (lo <= ts <= hi):  # same-format ISO-8601 lexicographic compare
        raise AssertionError(f"{time_field}={ts} outside RunWindow [{lo}, {hi}]")


def check_review_path(row: Mapping[str, str]) -> None:
    if not (row.get("复核路径") or "").strip():
        raise AssertionError("复核路径 must be non-empty and re-submittable")


def check_no_sensitive(text: str, *, where: str) -> None:
    if SENSITIVE_NAME_RE.search(Path(where).name):
        raise AssertionError(f"sensitive file name refused: {where}")
    m = SENSITIVE_CONTENT_RE.search(text)
    if m:
        raise AssertionError(f"sensitive content (credential/private path) in {where}: {m.group(0)!r}")


def read_coverage() -> dict[str, object]:
    return json.loads(COVERAGE.read_text(encoding="utf-8"))
