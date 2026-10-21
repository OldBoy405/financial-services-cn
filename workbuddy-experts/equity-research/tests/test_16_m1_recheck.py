"""cmd-04 — M1 recheck paths, original standards and the 9/9 view (FR-11/FR-14)."""
from __future__ import annotations

import unittest

import _support
from _support import (
    ACCEPTANCE,
    C4_BLOCK,
    C4_CLOSEOUT_BLOCK,
    C4_NINE_TASKS,
    C4_STATES,
    M1_EARNINGS_CHECKLIST_SIZE,
    M1_INITIATE_STAGES,
    M1_REQUIRED_ARTIFACTS,
    RepoTest,
    c4_m1,
    nine_view,
    read_json_block,
)
from test_13_cr4_evidence import acceptance_table, table_problems


def _case_problems(case: dict, label: str) -> list[str]:
    problems = []
    for key in ("case-id", "language", "market", "session-record", "expected", "actual", "result"):
        if not case.get(key):
            problems.append(f"{label}: missing {key}")
    if case.get("result") not in C4_STATES:
        problems.append(f"{label}: invalid result")
    return problems


def m1_record_problems(row: dict) -> list[str]:
    problems: list[str] = []
    prior = row.get("prior") or {}
    adjudication = row.get("adjudication") or {}
    retest = row.get("retest")
    mode = row.get("path-mode")
    if prior.get("state") not in C4_STATES:
        problems.append(f"{row.get('m1-slot')}: invalid prior.state")
    if mode == "carry-forward":
        if prior.get("state") != "通过":
            problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.state=通过")
        if not prior.get("adjudication-ref"):
            problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.adjudication-ref")
        if row.get("impact") != "unchanged":
            problems.append(f"{row.get('m1-slot')}: carry-forward requires impact=unchanged")
    elif mode == "retest":
        if not isinstance(retest, dict):
            problems.append(f"{row.get('m1-slot')}: retest requires a retest object")
        if prior.get("state") in (None, "", "待测") and prior.get("adjudication-ref"):
            problems.append(f"{row.get('m1-slot')}: 待测 prior may not carry an adjudication-ref")
    else:
        problems.append(f"{row.get('m1-slot')}: invalid path-mode")
    if adjudication.get("state") not in C4_STATES:
        problems.append(f"{row.get('m1-slot')}: invalid adjudication.state")
    if adjudication.get("state") != "通过":
        return problems
    if not adjudication.get("adjudicator") or not adjudication.get("adjudicated-at"):
        problems.append(f"{row.get('m1-slot')}: missing adjudicator/adjudicated-at")
    if not isinstance(retest, dict):
        return problems
    for key in ("positive-cases", "negative-cases", "artifacts", "quality-checklist", "initiate-stages", "replay"):
        if key not in retest:
            problems.append(f"{row.get('m1-slot')}.retest: missing {key}")
    for case in (retest.get("positive-cases") or []) + (retest.get("negative-cases") or []):
        problems += _case_problems(case, f"{row.get('m1-slot')}.retest.case")
    standards = row.get("original-standard-check") or []
    if not standards:
        problems.append(f"{row.get('m1-slot')}: original-standard-check is empty")
    if row.get("m1-slot") == "M1-01":
        if len(retest.get("quality-checklist") or []) != M1_EARNINGS_CHECKLIST_SIZE:
            problems.append("M1-01: quality-checklist must contain eight items")
        if "DOCX" not in {artifact.get("kind") for artifact in retest.get("artifacts") or []}:
            problems.append("M1-01: DOCX artifact is required")
    if row.get("m1-slot") == "M1-02":
        if retest.get("cross-session") is not None:
            problems.append("M1-02: cross-session must stay null")
    if row.get("m1-slot") == "M1-03":
        stages = {stage.get("stage") for stage in retest.get("initiate-stages") or []}
        if stages != {stage for stage, _ in M1_INITIATE_STAGES}:
            problems.append("M1-03: initiate-stages must cover M1-03-T1..T5 exactly")
        if not retest.get("cross-session"):
            problems.append("M1-03: cross-session is required")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _passing(self) -> dict:
        return {
            "m1-slot": "M1-03",
            "prior": {"state": "待测", "adjudication-ref": "", "evidence-refs": []},
            "path-mode": "retest",
            "impact": "retest-required",
            "original-standard-check": [{"criterion": "five stages", "evidence-ref": "x", "result": "通过"}],
            "retest": {
                "positive-cases": [{"case-id": "p", "language": "zh-CN", "market": "A股", "session-record": "x", "expected": "x", "actual": "x", "result": "通过"}],
                "negative-cases": [],
                "artifacts": [{"kind": "DOCX"}],
                "quality-checklist": [],
                "cross-session": {"reentry-id": "r"},
                "initiate-stages": [{"stage": stage} for stage, _ in M1_INITIATE_STAGES],
                "replay": [],
            },
            "adjudication": {"state": "通过", "adjudicator": "Ray", "adjudicated-at": "2026-10-21T00:00:00+08:00"},
        }

    def test_m1_gate(self) -> None:
        row = self._passing()
        self.assertEqual(m1_record_problems(row), [])
        self.assertTrue(m1_record_problems({**row, "original-standard-check": []}))
        self.assertTrue(m1_record_problems({**row, "retest": {**row["retest"], "initiate-stages": []}}))
        forward = {**row, "path-mode": "carry-forward", "prior": {"state": "通过", "adjudication-ref": "x", "evidence-refs": []}, "impact": "unchanged"}
        self.assertEqual(m1_record_problems(forward), [])
        self.assertTrue(m1_record_problems({**forward, "prior": {"state": "待测", "adjudication-ref": "x"}}))


class RepositoryContract(RepoTest):
    def test_m1_records(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        problems: list[str] = []
        for row in c4.get("m1-recheck") or []:
            problems += m1_record_problems(row)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_nine_view_and_count(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        closeout = read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)
        summary = closeout.get("nine-summary") or []
        self.assertEqual([row.get("task") for row in summary], list(C4_NINE_TASKS))
        for row in summary:
            self.assertEqual(row, nine_view(c4, closeout, row.get("task")))
        passed = sum(1 for row in summary if row.get("counts-toward-9"))
        self.assertEqual((closeout.get("count") or {}).get("passed"), passed)
        if passed == 9:
            self.assertTrue((closeout.get("closeout") or {}).get("final-wording-allowed"))
        else:
            self.assertFalse((closeout.get("closeout") or {}).get("final-wording-allowed"))

    def test_table_matches_json(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        closeout = read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)
        header, rows = acceptance_table(ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertEqual(table_problems(header, rows, closeout.get("nine-summary") or []), [])
        self.assertEqual(len(c4.get("m1-recheck") or []), 3)


if __name__ == "__main__":
    unittest.main()
