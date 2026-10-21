"""cmd-01 — the CR4 evidence index, §6 pin and nine-item view (FR-01/FR-14).

The module has two halves: contract self-checks (temporary values, proving the
gates can fail) and the repository contract (the real §7/§8 blocks in
ACCEPTANCE.md).  Nothing here writes to the repository or adjudicates research.
"""
from __future__ import annotations

import hashlib
import os
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
    c4_m1,
    c4_section6_sha256,
    c4_slot,
    nine_view,
    read_json_block,
    sha256_file,
)

TABLE_COLUMNS = (
    "任务",
    "测试日期",
    "真实问法摘要",
    "市场与期间",
    "正例",
    "适用负例或不适用理由",
    "来源·时效·权限",
    "产物与打开记录",
    "原命令映射核对",
    "当前包与环境关联",
    "用户裁决",
    "证据定位",
)
C4_TOP_KEYS = {
    "schema-version",
    "cr",
    "recorded-at",
    "package",
    "skill-source-head",
    "prerequisites",
    "slots",
    "cross-slot-cases",
    "m1-recheck",
}
CLOSEOUT_TOP_KEYS = {
    "schema-version",
    "cr",
    "recorded-at",
    "package",
    "nine-summary",
    "count",
    "closeout",
    "distribution",
    "adjudicator",
    "adjudicated-at",
}
COMMON_KEYS = ("cr1-baseline", "cr2-authorization-framework", "package-baseline")
EVIDENCE_PREFIX = "out/evidence/cr4/"
HASH_REF_RE = re.compile(r"^out/evidence/cr4/.+::[0-9a-f]{64}$")
ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")


def load_blocks() -> tuple[dict, dict]:
    return (
        read_json_block(ACCEPTANCE, C4_BLOCK),
        read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK),
    )


def acceptance_table(text: str) -> tuple[list[str], list[list[str]]]:
    """Return the §8 Markdown header and its nine rows (cells stripped)."""
    section = re.split(r"^## 8\. ", text, maxsplit=1, flags=re.M)
    if len(section) != 2:
        raise AssertionError("ACCEPTANCE.md is missing §8")
    match = re.search(r"(?m)^\| 任务 \|.*\n\|[ :|-]+\n((?:\|.*\n)+)", section[1])
    if not match:
        raise AssertionError("§8 is missing the nine-row Markdown summary table")
    header = [cell.strip() for cell in match.group(0).split("\n", 1)[0].strip().strip("|").split("|")]
    rows = []
    for line in match.group(1).strip().split("\n"):
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return header, rows


def _case_problems(case: dict, label: str) -> list[str]:
    problems = []
    if not isinstance(case, dict):
        return [f"{label}: case must be an object"]
    for forbidden in ("prompt", "response"):
        if forbidden in case:
            problems.append(f"{label}: verbatim field '{forbidden}' is forbidden")
    for key in ("input-summary", "response-summary"):
        value = case.get(key) or ""
        if not isinstance(value, str):
            problems.append(f"{label}.{key}: must be a string")
        elif len(value) > _support.C4_CASE_SUMMARY_LIMIT:
            problems.append(f"{label}.{key}: exceeds {_support.C4_CASE_SUMMARY_LIMIT} characters")
        elif ABS_PATH_RE.match(value):
            problems.append(f"{label}.{key}: absolute path is forbidden")
    ref = case.get("session-record")
    if ref and not HASH_REF_RE.match(str(ref)):
        problems.append(f"{label}.session-record: must be out/evidence/cr4/<path>::<sha256>")
    return problems


def _artifact_problems(artifact: dict, label: str) -> list[str]:
    problems = []
    path = artifact.get("path") if isinstance(artifact, dict) else None
    if not isinstance(path, str) or not path.startswith(EVIDENCE_PREFIX):
        problems.append(f"{label}.path: must start with {EVIDENCE_PREFIX}")
    elif ABS_PATH_RE.match(path) or "\\" in path:
        problems.append(f"{label}.path: must be POSIX-relative")
    digest = artifact.get("sha256") if isinstance(artifact, dict) else None
    if not isinstance(digest, str) or not re.match(r"^[0-9a-f]{64}$", digest):
        problems.append(f"{label}.sha256: must be 64 lowercase hex characters")
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
    if not isinstance(c4.get("cross-slot-cases"), list):
        problems.append("§7 cross-slot-cases must be a list")
    common = (c4.get("prerequisites") or {}).get("common") or {}
    if set(common) != set(COMMON_KEYS):
        problems.append("§7 prerequisites.common is incomplete")
    slot_reqs = (c4.get("prerequisites") or {}).get("slots") or []
    if [row.get("slot") for row in slot_reqs] != [row[0] for row in C4_SLOTS] + [row[0] for row in C4_M1_SLOTS]:
        problems.append("§7 prerequisites.slots is not the nine task rows in order")
    for slot in c4.get("slots") or []:
        if slot.get("research-state") not in C4_STATES:
            problems.append(f"{slot.get('slot')}: invalid research-state")
        if (slot.get("adjudication") or {}).get("state") != slot.get("research-state"):
            problems.append(f"{slot.get('slot')}: research-state and adjudication.state differ")
        if slot.get("acceptance-slot") not in {row[1] for row in C4_SLOTS}:
            problems.append(f"{slot.get('slot')}: invalid acceptance-slot")
        for case in (slot.get("positive-cases") or []) + (slot.get("negative-cases") or []):
            problems += _case_problems(case, f"{slot.get('slot')}.case")
        for artifact in slot.get("artifacts") or []:
            problems += _artifact_problems(artifact, f"{slot.get('slot')}.artifact")
    for row in c4.get("m1-recheck") or []:
        path_mode = row.get("path-mode")
        if path_mode not in ("carry-forward", "retest"):
            problems.append(f"{row.get('m1-slot')}: invalid path-mode")
        if path_mode == "carry-forward":
            if (row.get("prior") or {}).get("state") != "通过":
                problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.state=通过")
            if not (row.get("prior") or {}).get("adjudication-ref"):
                problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.adjudication-ref")
        elif not isinstance(row.get("retest"), dict):
            problems.append(f"{row.get('m1-slot')}: retest requires a retest object")
        for case in ((row.get("retest") or {}).get("positive-cases") or []) + ((row.get("retest") or {}).get("negative-cases") or []):
            problems += _case_problems(case, f"{row.get('m1-slot')}.retest.case")
        for artifact in (row.get("retest") or {}).get("artifacts") or []:
            problems += _artifact_problems(artifact, f"{row.get('m1-slot')}.retest.artifact")
    summary = closeout.get("nine-summary") or []
    if [row.get("task") for row in summary] != list(C4_NINE_TASKS):
        problems.append("§8 nine-summary is not the nine tasks in order")
    for row in summary:
        expected = nine_view(c4, closeout, row.get("task"))
        if row != expected:
            problems.append(f"§8 nine-summary row {row.get('task')} differs from nine_view()")
    count = closeout.get("count") or {}
    if count.get("total") != 9:
        problems.append("§8 count.total must be 9")
    if count.get("passed") != sum(1 for row in summary if row.get("counts-toward-9")):
        problems.append("§8 count.passed must equal counts-toward-9 rows")
    closeout_flags = closeout.get("closeout") or {}
    if closeout_flags.get("final-wording-allowed") and count.get("passed") != 9:
        problems.append("final-wording-allowed requires count.passed=9")
    if not closeout_flags.get("final-wording-allowed") and closeout_flags.get("final-wording"):
        problems.append("final-wording must be empty when final-wording-allowed=false")
    return problems


def table_problems(header: list[str], rows: list[list[str]], summary: list[dict]) -> list[str]:
    problems: list[str] = []
    if tuple(header) != TABLE_COLUMNS:
        problems.append(f"§8 table header differs from the fixed 12 columns: {header}")
    if len(rows) != 9:
        problems.append(f"§8 table must have 9 rows, found {len(rows)}")
        return problems
    for row, expected in zip(rows, summary):
        if len(row) != len(TABLE_COLUMNS):
            problems.append(f"§8 table row {row[0] if row else '?'} has {len(row)} cells")
            continue
        if row[0] != expected.get("task"):
            problems.append(f"§8 table task order differs at {row[0]!r} vs {expected.get('task')!r}")
        if row[10] != expected.get("current-state"):
            problems.append(f"§8 table state for {row[0]} differs from JSON")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def test_section6_hash_is_line_ending_and_separator_independent(self) -> None:
        base = "## 6. M1 研究证据与裁决记录\nbody\n<!-- m1-research:end -->"
        appended = base + "\n\n## 7. 其余六项研究证据与裁决记录\nnew\n"
        self.assertEqual(c4_section6_sha256(base), c4_section6_sha256(appended))
        self.assertEqual(c4_section6_sha256(base.replace("\n", "\r\n")), c4_section6_sha256(base))
        self.assertNotEqual(c4_section6_sha256(base), c4_section6_sha256(base + "\nbody-change"))

    def test_table_parser_and_cross_check(self) -> None:
        summary = [{"task": task, "current-state": "待测"} for task in C4_NINE_TASKS]
        header = "| " + " | ".join(TABLE_COLUMNS) + " |"
        rows = "\n".join("| " + " | ".join([task] + ["—"] * 9 + ["待测", "—"]) + " |" for task in C4_NINE_TASKS)
        text = f"## 8. x\n\n{header}\n|" + "---|" * 12 + "\n" + rows + "\n"
        h, r = acceptance_table(text)
        self.assertEqual(table_problems(h, r, summary), [])
        self.assertTrue(table_problems(h, r[:-1], summary))
        self.assertTrue(table_problems(h, [[cell] * 11 for cell in [row[0] for row in r]], summary))

    def test_case_and_artifact_whitelists(self) -> None:
        self.assertTrue(_case_problems({"prompt": "x"}, "c"))
        self.assertTrue(_case_problems({"input-summary": "x" * 401}, "c"))
        self.assertTrue(_case_problems({"input-summary": "C:\\secret"}, "c"))
        self.assertTrue(_case_problems({"session-record": "out/evidence/cr4/x.json::bad"}, "c"))
        self.assertTrue(_artifact_problems({"path": "tmp/x.docx", "sha256": "0" * 64}, "a"))
        self.assertEqual(_artifact_problems({"path": "out/evidence/cr4/x.docx", "sha256": "0" * 64}, "a"), [])


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

    def test_nine_summary_table_matches_json(self) -> None:
        _, closeout = load_blocks()
        header, rows = acceptance_table(ACCEPTANCE.read_text(encoding="utf-8"))
        problems = table_problems(header, rows, closeout.get("nine-summary") or [])
        self.assertEqual(problems, [], "\n".join(problems))

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
