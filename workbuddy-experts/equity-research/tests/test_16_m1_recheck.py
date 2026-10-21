"""cmd-04 — M1 recheck paths, original standards and the 9/9 view (FR-11/FR-14)."""
from __future__ import annotations

import unittest

from _support import (
    ACCEPTANCE,
    C4_BLOCK,
    C4_CLOSEOUT_BLOCK,
    C4_NINE_TASKS,
    C4_STATES,
    M1_EARNINGS_CHECKLIST_SIZE,
    M1_INITIATE_STAGES,
    RepoTest,
    c4_check_artifact,
    c4_check_ref,
    nine_view,
    read_json_block,
)
from test_13_cr4_evidence import acceptance_table, table_problems


def _case_problems(case: dict, label: str, verify: bool) -> list[str]:
    problems = []
    for key in ("case-id", "language", "market", "session-record", "expected", "actual", "result"):
        if not case.get(key):
            problems.append(f"{label}: missing {key}")
    if case.get("result") not in C4_STATES:
        problems.append(f"{label}: invalid result")
    if verify and case.get("session-record"):
        problems += c4_check_ref(case.get("session-record"), f"{label}.session-record")
    return problems


def m1_record_problems(row: dict, verify: bool = True) -> list[str]:
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
        if not prior.get("evidence-refs"):
            problems.append(f"{row.get('m1-slot')}: carry-forward requires prior.evidence-refs")
        if verify:
            if prior.get("adjudication-ref"):
                problems += c4_check_ref(prior.get("adjudication-ref"), f"{row.get('m1-slot')}.prior.adjudication-ref")
            for ref in prior.get("evidence-refs") or []:
                problems += c4_check_ref(ref, f"{row.get('m1-slot')}.prior.evidence-refs")
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
    if mode == "carry-forward":
        return problems
    if not isinstance(retest, dict):
        return problems
    for key in ("positive-cases", "negative-cases", "artifacts", "quality-checklist", "initiate-stages", "replay"):
        if key not in retest:
            problems.append(f"{row.get('m1-slot')}.retest: missing {key}")
    for case in (retest.get("positive-cases") or []) + (retest.get("negative-cases") or []):
        problems += _case_problems(case, f"{row.get('m1-slot')}.retest.case", verify)
        if case.get("result") != "通过":
            problems.append(f"{row.get('m1-slot')}.retest.case: result must be 通过")
    for artifact in retest.get("artifacts") or []:
        if verify:
            problems += c4_check_artifact(artifact, f"{row.get('m1-slot')}.retest.artifact")
    standards = row.get("original-standard-check") or []
    if not standards:
        problems.append(f"{row.get('m1-slot')}: original-standard-check is empty")
    for standard in standards:
        if not all(standard.get(key) for key in ("criterion", "evidence-ref", "result")):
            problems.append(f"{row.get('m1-slot')}: incomplete original-standard-check row")
        elif standard.get("result") != "通过":
            problems.append(f"{row.get('m1-slot')}: original-standard-check must be 通过")
        elif verify:
            problems += c4_check_ref(standard.get("evidence-ref"), f"{row.get('m1-slot')}.standard.evidence-ref")
    if row.get("m1-slot") == "M1-01":
        checklist = retest.get("quality-checklist") or []
        if len(checklist) != M1_EARNINGS_CHECKLIST_SIZE:
            problems.append("M1-01: quality-checklist must contain eight items")
        if any(not all(item.get(key) for key in ("item", "result", "evidence-ref")) for item in checklist):
            problems.append("M1-01: every checklist item needs item/result/evidence-ref")
        if any(item.get("result") != "通过" for item in checklist):
            problems.append("M1-01: every checklist item must be 通过")
        if verify:
            for item in checklist:
                if item.get("evidence-ref"):
                    problems += c4_check_ref(item.get("evidence-ref"), "M1-01.checklist.evidence-ref")
        kinds = {artifact.get("kind") for artifact in retest.get("artifacts") or []}
        if not {"DOCX", "SUMMARY"} <= kinds:
            problems.append("M1-01: DOCX and SUMMARY artifacts are required")
    if row.get("m1-slot") == "M1-02":
        if retest.get("cross-session") is not None:
            problems.append("M1-02: cross-session must stay null")
        check = retest.get("model-check") or {}
        for key in ("original-sha256", "updated-sha256", "formulas", "changes", "reopen"):
            if not check.get(key):
                problems.append(f"M1-02: model-check.{key} is required")
        if check.get("original-sha256") == check.get("updated-sha256"):
            problems.append("M1-02: original and updated model hashes must differ")
        if not isinstance(check.get("formulas"), int) or check.get("formulas", 0) <= 0:
            problems.append("M1-02: formulas must be a positive integer")
        if not isinstance(check.get("changes"), list) or not check.get("changes"):
            problems.append("M1-02: changes must be a non-empty list")
        if check.get("reopen") != "通过":
            problems.append("M1-02: reopen must be 通过")
    if row.get("m1-slot") == "M1-03":
        stages = retest.get("initiate-stages") or []
        if {stage.get("stage") for stage in stages} != {stage for stage, _ in M1_INITIATE_STAGES}:
            problems.append("M1-03: initiate-stages must cover M1-03-T1..T5 exactly")
        if len({stage.get("case-id") for stage in stages}) != len(stages):
            problems.append("M1-03: each stage needs an independent case-id")
        kinds = {artifact.get("kind") for artifact in retest.get("artifacts") or []}
        if not {"REPORT", "XLSX", "ZIP", "DOCX"} <= kinds:
            problems.append("M1-03: REPORT/XLSX/ZIP/DOCX artifacts are required")
        for stage in stages:
            for key in ("case-id", "request-summary", "artifact-refs", "result"):
                if not stage.get(key):
                    problems.append(f"M1-03.{stage.get('stage')}: missing {key}")
            if stage.get("result") != "通过":
                problems.append(f"M1-03.{stage.get('stage')}: result must be 通过")
            if verify:
                for ref in stage.get("artifact-refs") or []:
                    problems += c4_check_ref(ref, f"M1-03.{stage.get('stage')}.artifact-ref")
        cross = retest.get("cross-session") or {}
        for key in ("reentry-id", "exit-at", "reentry-at", "provided-artifacts", "stage-located", "confirmation", "final-artifact", "result"):
            if not cross.get(key):
                problems.append(f"M1-03.cross-session: missing {key}")
        if cross.get("result") != "通过":
            problems.append("M1-03.cross-session: result must be 通过")
        if verify:
            for ref in cross.get("provided-artifacts") or []:
                problems += c4_check_ref(ref, "M1-03.cross-session.provided-artifacts")
            if cross.get("final-artifact"):
                problems += c4_check_ref(cross.get("final-artifact"), "M1-03.cross-session.final-artifact")
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
                "artifacts": [{"kind": kind} for kind in ("REPORT", "XLSX", "ZIP", "DOCX")],
                "quality-checklist": [],
                "cross-session": {"reentry-id": "x", "exit-at": "x", "reentry-at": "x", "provided-artifacts": ["x"], "stage-located": "x", "confirmation": "x", "final-artifact": "x", "result": "通过"},
                "initiate-stages": [{"stage": stage, "case-id": f"c-{stage}", "request-summary": "r", "artifact-refs": ["a"], "result": "通过"} for stage, _ in M1_INITIATE_STAGES],
                "replay": [],
            },
            "adjudication": {"state": "通过", "adjudicator": "Ray", "adjudicated-at": "2026-10-21T00:00:00+08:00"},
        }

    def test_m1_gate(self) -> None:
        row = self._passing()
        self.assertEqual(m1_record_problems(row, verify=False), [])
        self.assertTrue(m1_record_problems({**row, "original-standard-check": []}, verify=False))
        self.assertTrue(m1_record_problems({**row, "retest": {**row["retest"], "initiate-stages": []}}, verify=False))
        forward = {**row, "path-mode": "carry-forward", "prior": {"state": "通过", "adjudication-ref": "x", "evidence-refs": ["x"]}, "impact": "unchanged"}
        self.assertEqual(m1_record_problems(forward, verify=False), [])
        self.assertTrue(m1_record_problems({**forward, "prior": {"state": "待测", "adjudication-ref": "x"}}, verify=False))


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
        flags = closeout.get("closeout") or {}
        allowed = bool(passed == 9 and (flags.get("reinstall") or {}).get("status") == "通过" and (flags.get("readiness") or {}).get("status") == "通过")
        self.assertEqual(flags.get("final-wording-allowed"), allowed)
        self.assertEqual(flags.get("final-wording"), "phase-1 本机自用 9/9 完成" if allowed else "")

    def test_table_matches_json(self) -> None:
        closeout = read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)
        header, rows = acceptance_table(ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertEqual(table_problems(header, rows, closeout.get("nine-summary") or []), [])


if __name__ == "__main__":
    unittest.main()
