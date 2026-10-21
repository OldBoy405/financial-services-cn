"""cmd-01 — the CR4 evidence index, §6 pin and nine-item view (FR-01/FR-11/FR-14)."""
from __future__ import annotations

import hashlib
import re
import tempfile
import unittest
from pathlib import Path

import _support
from _support import (
    ACCEPTANCE,
    C4_BASELINE_ACCEPTANCE_LINES,
    C4_BLOCK,
    C4_CLOSEOUT_BLOCK,
    C4_CR,
    C4_M1_SLOTS,
    C4_NINE_TASKS,
    C4_SCHEMA_VERSION,
    C4_SECTION6_SHA256,
    C4_SLOTS,
    C4_STATES,
    M1_ACCEPTANCE_PREFIX_SHA256,
    RepoTest,
    c4_check_artifact,
    c4_check_ref,
    c4_m1,
    c4_section6_sha256,
    c4_slot,
    c4_slot_eligible,
    nine_view,
    read_json_block,
)

TABLE_COLUMNS = (
    "任务", "测试日期", "真实问法摘要", "市场与期间", "正例", "适用负例或不适用理由",
    "来源·时效·权限", "产物与打开记录", "原命令映射核对", "当前包与环境关联", "用户裁决", "证据定位",
)
C4_TOP_KEYS = {"schema-version", "cr", "recorded-at", "package", "skill-source-head", "prerequisites", "slots", "cross-slot-cases", "m1-recheck"}
CLOSEOUT_TOP_KEYS = {"schema-version", "cr", "recorded-at", "package", "nine-summary", "count", "closeout", "distribution", "adjudicator", "adjudicated-at"}
SLOT_KEYS = {"slot", "acceptance-slot", "skill", "market-scope", "research-state", "adjudication", "positive-cases", "negative-cases", "artifacts", "mapping-check", "skill-change"}
M1_KEYS = {"m1-slot", "acceptance-slot", "skill", "prior", "package-link", "impact", "impact-basis", "path-mode", "original-standard-check", "retest", "adjudication", "evidence-refs", "skill-change"}
CASE_KEYS = {"case-id", "slot", "language", "market", "input-summary", "response-summary", "session-record", "client-version", "tool-version", "collected-at", "expected", "actual", "result", "evidence-refs", "zero-file", "type", "branch", "applicable", "not-applicable-reason", "adjacent-path"}
ARTIFACT_KEYS = {"artifact-id", "case-id", "kind", "path", "sha256", "bytes", "generated-by", "open-check", "structural", "content-check", "meta", "deviations"}
COMMON_KEYS = ("cr1-baseline", "cr2-authorization-framework", "package-baseline")
FORBIDDEN_KEYS = {"prompt", "response", "api-key", "api_key", "token", "password", "secret", "credential"}
SENSITIVE_RE = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key\s*[:=]\s*\S+|bearer\s+[A-Za-z0-9._-]{12,}|\btoken\s*[:=]\s*\S{8,})", re.I)
ABS_PATH_RE = re.compile(r"(?:^|[\\/])[A-Za-z]:[\\/]|(?:^|[\s\"'])/home/")
HASH_REF_RE = re.compile(r"^out/evidence/cr4/.+::[0-9a-f]{64}$")


def load_blocks() -> tuple[dict, dict]:
    return read_json_block(ACCEPTANCE, C4_BLOCK), read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)


def acceptance_table(text: str) -> tuple[list[str], list[list[str]]]:
    section = re.split(r"^## 8\. ", text, maxsplit=1, flags=re.M)
    if len(section) != 2:
        raise AssertionError("ACCEPTANCE.md is missing §8")
    match = re.search(r"(?m)^\| 任务 \|.*\n\|[ :|-]+\n((?:\|.*\n)+)", section[1])
    if not match:
        raise AssertionError("§8 is missing the nine-row Markdown summary table")
    header = [cell.strip() for cell in match.group(0).split("\n", 1)[0].strip().strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in match.group(1).strip().split("\n")]
    return header, rows


def _walk_problems(value: object, label: str) -> list[str]:
    problems: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                problems.append(f"{label}: forbidden field {key!r}")
            problems += _walk_problems(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            problems += _walk_problems(child, f"{label}[{index}]")
    elif isinstance(value, str):
        if SENSITIVE_RE.search(value):
            problems.append(f"{label}: credential-like content")
        if ABS_PATH_RE.search(value):
            problems.append(f"{label}: absolute path is forbidden")
    return problems


def _keys_problems(record: dict, allowed: set[str], label: str) -> list[str]:
    if not isinstance(record, dict):
        return [f"{label}: must be an object"]
    return [f"{label}: undeclared field {key!r}" for key in sorted(set(record) - allowed)]


def _case_problems(case: dict, label: str) -> list[str]:
    problems = _keys_problems(case, CASE_KEYS, label)
    problems += _walk_problems(case, label)
    for key in ("input-summary", "response-summary"):
        value = case.get(key) or ""
        if len(value) > _support.C4_CASE_SUMMARY_LIMIT:
            problems.append(f"{label}.{key}: exceeds {_support.C4_CASE_SUMMARY_LIMIT} characters")
    ref = case.get("session-record")
    if ref:
        if not HASH_REF_RE.match(str(ref)):
            problems.append(f"{label}.session-record: must be out/evidence/cr4/<path>::<sha256>")
        else:
            problems += c4_check_ref(ref, f"{label}.session-record")
    return problems


def _artifact_problems(artifact: dict, label: str) -> list[str]:
    problems = _keys_problems(artifact, ARTIFACT_KEYS, label)
    problems += _walk_problems(artifact, label)
    if not artifact.get("path"):
        return problems + [f"{label}: path is required"]
    problems += c4_check_artifact(artifact, label)
    if not isinstance(artifact.get("deviations"), list):
        problems.append(f"{label}: deviations must be a list")
    return problems


def index_problems(c4: dict, closeout: dict, acceptance_text: str) -> list[str]:
    problems: list[str] = []
    if set(c4) != C4_TOP_KEYS:
        problems.append(f"§7 keys differ: {sorted(set(c4) ^ C4_TOP_KEYS)}")
    if set(closeout) != CLOSEOUT_TOP_KEYS:
        problems.append(f"§8 keys differ: {sorted(set(closeout) ^ CLOSEOUT_TOP_KEYS)}")
    if c4.get("schema-version") != C4_SCHEMA_VERSION or closeout.get("schema-version") != C4_SCHEMA_VERSION:
        problems.append("schema-version must be 1 in both blocks")
    if c4.get("cr") != C4_CR or closeout.get("cr") != C4_CR:
        problems.append(f"cr must be {C4_CR}")
    if [slot.get("slot") for slot in c4.get("slots") or []] != [row[0] for row in C4_SLOTS]:
        problems.append("§7 slots are not the six C4 slots in order")
    if [row.get("m1-slot") for row in c4.get("m1-recheck") or []] != [row[0] for row in C4_M1_SLOTS]:
        problems.append("§7 m1-recheck is not the three M1 slots in order")
    common = (c4.get("prerequisites") or {}).get("common") or {}
    if set(common) != set(COMMON_KEYS):
        problems.append("§7 prerequisites.common is incomplete")
    slot_reqs = (c4.get("prerequisites") or {}).get("slots") or []
    if [row.get("slot") for row in slot_reqs] != [row[0] for row in C4_SLOTS] + [row[0] for row in C4_M1_SLOTS]:
        problems.append("§7 prerequisites.slots is not the nine task rows in order")
    for slot in c4.get("slots") or []:
        problems += _keys_problems(slot, SLOT_KEYS, f"{slot.get('slot')}")
        if slot.get("research-state") not in C4_STATES:
            problems.append(f"{slot.get('slot')}: invalid research-state")
        if (slot.get("adjudication") or {}).get("state") != slot.get("research-state"):
            problems.append(f"{slot.get('slot')}: research-state and adjudication.state differ")
        if slot.get("research-state") == "通过" and not c4_slot_eligible(c4, slot.get("slot", "")):
            problems.append(f"{slot.get('slot')}: 通过 requires every own prerequisite accepted")
        for case in (slot.get("positive-cases") or []) + (slot.get("negative-cases") or []):
            problems += _case_problems(case, f"{slot.get('slot')}.case")
        for artifact in slot.get("artifacts") or []:
            problems += _artifact_problems(artifact, f"{slot.get('slot')}.artifact")
    for case in c4.get("cross-slot-cases") or []:
        problems += _case_problems(case, "cross-slot.case")
        if case.get("case-id") == "C4-US-01" and case.get("market") != "美股公开面":
            problems.append("C4-US-01 must be 美股公开面")
    for row in c4.get("m1-recheck") or []:
        problems += _keys_problems(row, M1_KEYS, str(row.get("m1-slot")))
        path_mode = row.get("path-mode")
        if path_mode == "carry-forward":
            if (row.get("prior") or {}).get("state") != "通过":
                problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.state=通过")
            if not (row.get("prior") or {}).get("adjudication-ref"):
                problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.adjudication-ref")
            if not (row.get("prior") or {}).get("evidence-refs"):
                problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.evidence-refs")
        elif path_mode == "retest":
            if not isinstance(row.get("retest"), dict):
                problems.append(f"{row.get('m1-slot')}: retest requires an object")
        else:
            problems.append(f"{row.get('m1-slot')}: invalid path-mode")
        if (row.get("adjudication") or {}).get("state") == "通过" and not c4_slot_eligible(c4, str(row.get("m1-slot"))):
            problems.append(f"{row.get('m1-slot')}: 通过 requires every own prerequisite accepted")
        for case in ((row.get("retest") or {}).get("positive-cases") or []) + ((row.get("retest") or {}).get("negative-cases") or []):
            problems += _case_problems(case, f"{row.get('m1-slot')}.retest.case")
        for artifact in (row.get("retest") or {}).get("artifacts") or []:
            problems += _artifact_problems(artifact, f"{row.get('m1-slot')}.retest.artifact")
    summary = closeout.get("nine-summary") or []
    if [row.get("task") for row in summary] != list(C4_NINE_TASKS):
        problems.append("§8 nine-summary is not the nine tasks in order")
    for row in summary:
        if row != nine_view(c4, closeout, row.get("task")):
            problems.append(f"§8 nine-summary row {row.get('task')} differs from nine_view()")
    count = closeout.get("count") or {}
    if count.get("total") != 9:
        problems.append("§8 count.total must be 9")
    if count.get("passed") != sum(1 for row in summary if row.get("counts-toward-9")):
        problems.append("§8 count.passed must equal counts-toward-9 rows")
    flags = closeout.get("closeout") or {}
    allowed = bool(
        count.get("passed") == 9
        and ((flags.get("reinstall") or {}).get("status") == "通过")
        and ((flags.get("readiness") or {}).get("status") == "通过")
    )
    if flags.get("final-wording-allowed") != allowed:
        problems.append("final-wording-allowed must equal passed==9 AND reinstall/readiness 通过")
    expected_wording = "phase-1 本机自用 9/9 完成" if allowed else ""
    if flags.get("final-wording") != expected_wording:
        problems.append("final-wording does not match the approved wording rule")
    if problems:
        return problems
    headers, rows = acceptance_table(acceptance_text)
    return table_problems(headers, rows, summary)


def table_problems(header: list[str], rows: list[list[str]], summary: list[dict]) -> list[str]:
    problems: list[str] = []
    if tuple(header) != TABLE_COLUMNS:
        problems.append("§8 table header differs from the fixed 12 columns")
    if len(rows) != 9:
        return problems + [f"§8 table must have 9 rows, found {len(rows)}"]
    for row, expected in zip(rows, summary):
        if len(row) != len(TABLE_COLUMNS):
            problems.append(f"§8 table row {row[0] if row else '?'} has {len(row)} cells")
            continue
        if row[0] != expected.get("task") or row[10] != expected.get("current-state"):
            problems.append(f"§8 table row {row[0]} differs from JSON task/current-state")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def test_section6_hash_is_line_ending_and_separator_independent(self) -> None:
        base = "## 6. M1 研究证据与裁决记录\nbody\n<!-- m1-research:end -->"
        appended = base + "\n\n## 7. 其余六项研究证据与裁决记录\nnew\n"
        self.assertEqual(c4_section6_sha256(base), c4_section6_sha256(appended))
        self.assertEqual(c4_section6_sha256(base.replace("\n", "\r\n")), c4_section6_sha256(base))
        self.assertNotEqual(c4_section6_sha256(base), c4_section6_sha256(base + "\nbody-change"))

    def test_nested_whitelist_and_sensitive_scan(self) -> None:
        self.assertTrue(_keys_problems({"prompt": "x"}, CASE_KEYS, "c"))
        self.assertTrue(_walk_problems({"meta": {"api_key": "x"}}, "a"))
        self.assertTrue(_walk_problems({"summary": "token: abcdefghijklmnop"}, "a"))
        self.assertTrue(_walk_problems({"summary": "C:\\Users\\x"}, "a"))
        self.assertTrue(_walk_problems({"input-summary": "/home/x"}, "a"))

    def test_table_parser_and_cross_check(self) -> None:
        summary = [{"task": task, "current-state": "待测"} for task in C4_NINE_TASKS]
        header = "| " + " | ".join(TABLE_COLUMNS) + " |"
        rows = "\n".join("| " + " | ".join([task] + ["—"] * 9 + ["待测", "—"]) + " |" for task in C4_NINE_TASKS)
        text = f"## 8. x\n\n{header}\n|" + "---|" * 12 + "\n" + rows + "\n"
        h, r = acceptance_table(text)
        self.assertEqual(table_problems(h, r, summary), [])
        self.assertTrue(table_problems(h, r[:-1], summary))

    def test_eligibility_gate_blocks_empty_package(self) -> None:
        c4 = {
            "prerequisites": {"common": {key: {"accepted": False} for key in COMMON_KEYS}, "slots": []},
            "slots": [{"slot": "C4-01", "research-state": "通过", "adjudication": {"state": "通过", "adjudicator": "Ray", "adjudicated-at": "t"}}],
        }
        closeout = {"package": {"content-sha256": "a" * 64}, "nine-summary": []}
        self.assertFalse(c4_slot_eligible(c4, "C4-01"))
        self.assertFalse(nine_view(c4, closeout, "screen")["counts-toward-9"])

    def test_artifact_verification_rejects_missing_and_bad_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_root = _support.ROOT
            try:
                _support.ROOT = Path(tmp)
                (Path(tmp) / "out" / "evidence" / "cr4").mkdir(parents=True)
                target = Path(tmp) / "out" / "evidence" / "cr4" / "a.docx"
                target.write_bytes(b"not-a-zip")
                artifact = {"path": "out/evidence/cr4/a.docx", "sha256": "0" * 64, "bytes": 9, "kind": "DOCX"}
                problems = c4_check_artifact(artifact, "a")
                self.assertTrue(any("sha256" in problem for problem in problems))
                self.assertTrue(any("ZIP" in problem for problem in problems))
                self.assertTrue(c4_check_artifact({**artifact, "path": "out/evidence/cr4/missing.docx"}, "a"))
            finally:
                _support.ROOT = old_root


class RepositoryContract(RepoTest):
    def test_index_schema_and_nine_view(self) -> None:
        c4, closeout = load_blocks()
        problems = index_problems(c4, closeout, ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_section6_pin_and_prefix(self) -> None:
        text = ACCEPTANCE.read_text(encoding="utf-8")
        self.assertEqual(c4_section6_sha256(text), C4_SECTION6_SHA256)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        prefix = "\n".join(lines[:C4_BASELINE_ACCEPTANCE_LINES]) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode("utf-8")).hexdigest(), M1_ACCEPTANCE_PREFIX_SHA256)

    def test_helpers_reject_duplicate_and_missing_records(self) -> None:
        c4, _ = load_blocks()
        self.assertEqual(c4_slot(c4, "C4-01").get("slot"), "C4-01")
        self.assertEqual(c4_m1(c4, "M1-01").get("m1-slot"), "M1-01")
        with self.assertRaises(AssertionError):
            c4_slot(c4, "C4-99")
        with self.assertRaises(AssertionError):
            c4_m1(c4, "M1-99")


if __name__ == "__main__":
    unittest.main()
