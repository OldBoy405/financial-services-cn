"""cmd-02 — six capability matrix: CN/EN, A/H, negatives, branches (FR-08/FR-09)."""
from __future__ import annotations

import re
import unittest

import _support
from _support import (
    ACCEPTANCE,
    C4_BLOCK,
    C4_NINE_TASKS,
    C4_SLOTS,
    C4_STATES,
    RepoTest,
    c4_check_ref,
    c4_slot,
    read_json_block,
    sha256_file,
)

REQUIRED_NEGATIVES = {
    "C4-01": {"ambiguous-input", "invalid-code", "empty-result", "no-permission", "source-conflict", "stale-data"},
    "C4-02": {"ambiguous-input", "invalid-code", "historical-date", "empty-result", "no-permission", "source-conflict", "stale-data", "unknown-date"},
    "C4-03": {"ambiguous-input", "historical-date", "no-permission", "source-conflict", "stale-data"},
    "C4-04": {"ambiguous-input", "invalid-code", "historical-date", "no-permission", "source-conflict", "stale-data", "missing-consensus"},
    "C4-05": {"ambiguous-input", "no-permission", "source-conflict", "stale-data"},
    "C4-06": {"ambiguous-input", "invalid-code", "historical-date", "no-permission", "source-conflict", "stale-data", "missing-prior-version"},
}
BRANCHES = (
    "输入不可解析/歧义",
    "无权限/许可不足",
    "空结果/过期/冲突/未知日期",
    "缺旧版本/前置文件",
    "同一有效请求重放",
    "任一字段改变/要求重做",
    "工具不支持/锁/保存失败",
    "下载/打开/内容核对失败",
)
LANGUAGES = {"zh-CN", "en-US"}
MARKETS = {"A股", "港股", "美股公开面"}


def _case_problems(case: dict, label: str, verify: bool = True) -> list[str]:
    problems = []
    if case.get("language") not in LANGUAGES:
        problems.append(f"{label}: language must be zh-CN or en-US")
    if case.get("market") not in MARKETS:
        problems.append(f"{label}: market must be A股/港股/美股公开面")
    if case.get("result") not in C4_STATES:
        problems.append(f"{label}: invalid result")
    if not case.get("session-record"):
        problems.append(f"{label}: session-record is required")
    elif verify:
        problems += c4_check_ref(case.get("session-record"), f"{label}.session-record")
    if not case.get("expected") or not case.get("actual"):
        problems.append(f"{label}: expected/actual are required")
    return problems


def slot_matrix_problems(slot: dict, verify: bool = True) -> list[str]:
    problems: list[str] = []
    positives = slot.get("positive-cases") or []
    negatives = slot.get("negative-cases") or []
    for case in positives + negatives:
        problems += _case_problems(case, f"{slot.get('slot')}.case", verify)
    if slot.get("research-state") != "通过":
        return problems
    languages = {case.get("language") for case in positives}
    markets = {case.get("market") for case in positives}
    if not {"zh-CN", "en-US"} <= languages:
        problems.append(f"{slot.get('slot')}: 通过 requires zh-CN and en-US positive cases")
    if not {"A股", "港股"} <= markets:
        problems.append(f"{slot.get('slot')}: 通过 requires A股 and 港股 positive cases")
    if any(case.get("result") != "通过" for case in positives):
        problems.append(f"{slot.get('slot')}: every positive case must result=通过")
    if any(case.get("applicable", True) and case.get("result") != "通过" for case in negatives):
        problems.append(f"{slot.get('slot')}: applicable negative cases must result=通过")
    if not any(case.get("branch") for case in negatives):
        problems.append(f"{slot.get('slot')}: 通过 requires at least one failure branch")
    if any(case.get("branch") and case.get("branch") not in BRANCHES for case in negatives):
        problems.append(f"{slot.get('slot')}: failure branch is not in the approved enum")
    present = {case.get("type") for case in negatives if case.get("applicable", True)}
    for negative_type in REQUIRED_NEGATIVES[slot.get("slot", "")]:
        if negative_type not in present:
            problems.append(f"{slot.get('slot')}: missing negative type {negative_type}")
    for case in negatives:
        if case.get("applicable") is False:
            if not case.get("not-applicable-reason") or not case.get("adjacent-path"):
                problems.append(f"{slot.get('slot')}: N/A negative lacks reason/adjacent-path")
    if not (slot.get("mapping-check") or {}).get("result"):
        problems.append(f"{slot.get('slot')}: mapping-check.result is empty")
    if not (slot.get("adjudication") or {}).get("adjudicator") or not (slot.get("adjudication") or {}).get("adjudicated-at"):
        problems.append(f"{slot.get('slot')}: missing adjudication")
    return problems


def collection_problems(c4: dict, verify: bool = True) -> list[str]:
    problems: list[str] = []
    slots = c4.get("slots") or []
    if len(slots) != 6:
        return ["§7 must contain six slots"]
    if not all(slot.get("research-state") == "通过" for slot in slots):
        return problems
    branches = {
        case.get("branch")
        for slot in slots
        for case in (slot.get("negative-cases") or [])
        if case.get("branch")
    }
    for branch in BRANCHES:
        if branch not in branches:
            problems.append(f"collection is missing failure branch {branch}")
    us_cases = [case for case in c4.get("cross-slot-cases") or [] if case.get("case-id") == "C4-US-01"]
    if len(us_cases) != 1:
        problems.append("cross-slot-cases must contain exactly C4-US-01")
    else:
        case = us_cases[0]
        problems += _case_problems(case, "C4-US-01", verify)
        if case.get("market") != "美股公开面":
            problems.append("C4-US-01 must be 美股公开面")
        if case.get("result") != "通过":
            problems.append("C4-US-01 must be an actual positive case")
        if "不接入美系机构数据源" not in (case.get("response-summary") or ""):
            problems.append("C4-US-01 must declare public-only US coverage")
        if any(term in (case.get("response-summary") or "") for term in ("目标价", "评级", "一致预期")):
            problems.append("C4-US-01 must not claim institutional-data results")
    seen = set()
    for slot in slots:
        for case in (slot.get("positive-cases") or []) + (slot.get("negative-cases") or []):
            case_id = case.get("case-id")
            if case_id in seen:
                problems.append(f"duplicate case-id {case_id}")
            seen.add(case_id)
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _passing_slot(self) -> dict:
        return {
            "slot": "C4-01",
            "acceptance-slot": "SLOT-04",
            "research-state": "通过",
            "adjudication": {"state": "通过", "adjudicator": "Ray", "adjudicated-at": "2026-10-21T00:00:00+08:00"},
            "mapping-check": {"row": "MR-04", "result": "通过", "notes": ""},
            "positive-cases": [
                {"case-id": "c1", "language": "zh-CN", "market": "A股", "result": "通过", "session-record": "out/evidence/cr4/a.json::" + "a" * 64, "expected": "x", "actual": "x"},
                {"case-id": "c2", "language": "en-US", "market": "港股", "result": "通过", "session-record": "out/evidence/cr4/b.json::" + "b" * 64, "expected": "x", "actual": "x"},
            ],
            "negative-cases": [
                {"case-id": "n1", "type": negative, "branch": BRANCHES[0], "language": "zh-CN", "market": "A股", "result": "通过", "session-record": "out/evidence/cr4/n.json::" + "c" * 64, "expected": "x", "actual": "x"}
                for negative in REQUIRED_NEGATIVES["C4-01"]
            ],
        }

    def test_slot_matrix_gate(self) -> None:
        slot = self._passing_slot()
        self.assertEqual(slot_matrix_problems(slot, verify=False), [])
        self.assertTrue(slot_matrix_problems({**slot, "positive-cases": slot["positive-cases"][:1]}, verify=False))
        self.assertTrue(slot_matrix_problems({**slot, "negative-cases": slot["negative-cases"][:2]}, verify=False))
        self.assertTrue(slot_matrix_problems({**slot, "adjudication": {"state": "通过"}}, verify=False))
        self.assertTrue(slot_matrix_problems({**slot, "mapping-check": {"result": ""}}, verify=False))
        failing = {**slot["positive-cases"][0], "result": "不通过"}
        self.assertTrue(slot_matrix_problems({**slot, "positive-cases": [failing]}, verify=False))

    def test_collection_branch_and_us_gate(self) -> None:
        slot = self._passing_slot()
        c4 = {"slots": [slot] * 6, "cross-slot-cases": []}
        self.assertTrue(collection_problems(c4, verify=False))
        c4["cross-slot-cases"] = [{"case-id": "C4-US-01", "market": "美股公开面", "result": "通过", "language": "zh-CN", "session-record": "out/evidence/cr4/us.json::" + "d" * 64, "expected": "公开面，无机构数据", "actual": "公开面", "response-summary": "仅公开面，不接入美系机构数据源"}]
        self.assertTrue(collection_problems(c4, verify=False))
        c4["cross-slot-cases"] = [{"case-id": "C4-US-01", "market": "美股公开面", "result": "通过"}]
        self.assertTrue(collection_problems(c4, verify=False))


class RepositoryContract(RepoTest):
    def test_six_slot_matrix(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        problems: list[str] = []
        for slot in c4.get("slots") or []:
            problems += slot_matrix_problems(slot)
        problems += collection_problems(c4)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_mapping_rows_are_the_six_mr_rows(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        expected = {slot: f"MR-0{index}" for index, (slot, _, _) in enumerate(C4_SLOTS, start=4)}
        for slot in c4.get("slots") or []:
            row = (slot.get("mapping-check") or {}).get("row")
            self.assertEqual(row, expected[slot.get("slot")], f"{slot.get('slot')} mapping row mismatch")
            self.assertIn("result", slot.get("mapping-check") or {})


if __name__ == "__main__":
    unittest.main()
