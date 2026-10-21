"""cmd-04 — M1 recheck paths, original standards and the 9/9 view (FR-11/FR-14)."""
from __future__ import annotations

import copy
import hashlib
import json
import posixpath
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

import _support
from test_10_m1_model_update import CHANGELOG_HEADER, changelog_problems, model_route_problems, open_check_problems, xlsx_problems
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


def _workbook_cells(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Read declared worksheet cells/formulas/cached results without recalculating them."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    cells = {}
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target", "") for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(item.itertext()) for item in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        for sheet in workbook.iter(f"{ns}sheet"):
            target = rels[sheet.get(f"{rel_ns}id")]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            for cell in ET.fromstring(archive.read(member)).iter(f"{ns}c"):
                formula = cell.find(f"{ns}f")
                cached = cell.findtext(f"{ns}v", "")
                if cell.get("t") == "s":
                    cached = strings[int(cached)]
                elif cell.get("t") == "inlineStr":
                    cached = "".join(t.text or "" for t in cell.iter(f"{ns}t"))
                value = "=" + (formula.text or "") if formula is not None else cached
                if value:
                    cells[(sheet.get("name"), cell.get("r"))] = (value, cached)
    return cells


def _model_problems(retest: dict, verify: bool) -> list[str]:
    problems = []
    for name in ("positive-cases", "negative-cases"):
        if not retest.get(name):
            problems.append(f"M1-02: {name} must not be empty")
    if not {"zh-CN", "en-US"} <= {case.get("language") for case in retest.get("positive-cases") or []}:
        problems.append("M1-02: original standard requires CN and EN positive cases")
    artifacts = retest.get("artifacts") or []
    models = {}
    for kind in ("MODEL-COPY", "XLSX", "CHANGELOG"):
        matches = [a for a in artifacts if a.get("kind") == kind]
        if len(matches) != 1:
            problems.append(f"M1-02: exactly one {kind} artifact is required")
        else:
            models[kind] = matches[0]
    if len(models) != 3:
        return problems
    original, updated, log = (models[k] for k in ("MODEL-COPY", "XLSX", "CHANGELOG"))
    check = retest.get("model-check") or {}
    if original.get("path") == updated.get("path"):
        problems.append("M1-02: original and updated models must be independent files")
    for field, artifact in (("original-sha256", original), ("updated-sha256", updated)):
        if check.get(field) != artifact.get("sha256"):
            problems.append(f"M1-02: {field} must match its model artifact")
    case_ids = {c.get("case-id") for c in retest.get("positive-cases") or []}
    if any(a.get("case-id") not in case_ids for a in models.values()):
        problems.append("M1-02: model/log artifacts must link to a positive case")
    if not verify:
        return problems
    for artifact in (original, updated):
        problems += model_route_problems(artifact)
    problems += open_check_problems(updated, True)
    problems += xlsx_problems(updated, original.get("sha256"))
    try:
        before = _workbook_cells(_support.resolve_evidence_path(original.get("path")))
        after = _workbook_cells(_support.resolve_evidence_path(updated.get("path")))
        actual_changes = [{"sheet": sheet, "cell": cell, "before": before.get((sheet, cell), ("", ""))[0], "after": after.get((sheet, cell), ("", ""))[0]} for sheet, cell in sorted(set(before) | set(after)) if before.get((sheet, cell), ("", ""))[0] != after.get((sheet, cell), ("", ""))[0]]
        if not actual_changes or check.get("changes") != actual_changes:
            problems.append("M1-02: changes must match the actual per-cell model diff")
        formula_count = sum(value.startswith("=") for value, _ in after.values())
        if formula_count <= 0 or check.get("formulas") != formula_count:
            problems.append("M1-02: formulas must match actual live model formulas")
        text = _support.resolve_evidence_path(log.get("path")).read_text(encoding="utf-8")
        problems += changelog_problems(text)
        rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in text.splitlines() if line.strip().startswith("|") and line.strip() != CHANGELOG_HEADER and not set(line.strip()) <= set("|:- ")]
        if sorted(row[:4] for row in rows) != sorted([c["sheet"], c["cell"], c["before"], c["after"]] for c in actual_changes):
            problems.append("M1-02: CHANGELOG must cover the actual per-cell changes")
        ref = updated.get("meta", {}).get("verification-ref")
        ref_problems = c4_check_ref(ref, "M1-02.model-verification")
        problems += ref_problems
        if not ref_problems:
            receipt_path, _ = _support.split_evidence_ref(ref)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected = {"original-before-sha256": original.get("sha256"), "original-after-sha256": original.get("sha256"), "updated-sha256": updated.get("sha256"), "reopen": "通过", "recalculate": "通过"}
            if not isinstance(receipt, dict) or any(receipt.get(k) != v for k, v in expected.items()):
                problems.append("M1-02: original protection/reopen/recalculation receipt does not match the models")
            else:
                samples = receipt.get("samples") or []
                if not samples or samples != updated.get("meta", {}).get("samples"):
                    problems.append("M1-02: model-bound recalculation samples are required")
                for sample in samples:
                    location = str(sample.get("location") or "")
                    sheet, _, cell = location.rpartition("!")
                    actual = after.get((sheet, cell), ("", ""))[1]
                    if not actual or sample.get("expected") != actual or sample.get("actual") != actual or sample.get("result") != "通过":
                        problems.append("M1-02: sample must reconcile with the reopened model cell")
    except (OSError, ValueError, KeyError, IndexError, AssertionError, zipfile.BadZipFile, ET.ParseError) as exc:
        problems.append(f"M1-02: unreadable model/log/verification evidence: {exc}")
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
        problems += _model_problems(retest, verify)
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
            "adjudication": {"state": "通过", "adjudicator": "synthetic-fixture", "adjudicated-at": "2026-10-21T00:00:00+08:00"},
        }

    def test_m1_02_cannot_pass_on_self_report_without_models(self) -> None:
        row = self._passing()
        row["m1-slot"] = "M1-02"
        row["retest"].update({
            "positive-cases": [], "negative-cases": [], "artifacts": [], "cross-session": None,
            "model-check": {"original-sha256": "0" * 64, "updated-sha256": "1" * 64, "formulas": 1, "changes": ["A1"], "reopen": "通过"},
        })
        # A real, hash-checked standard receipt isolates the missing-model gap.
        import hashlib
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import _support
        with tempfile.TemporaryDirectory() as tmp, patch.object(_support, "ROOT", Path(tmp)):
            target = Path(tmp) / "out/evidence/cr4/standard.json"
            target.parent.mkdir(parents=True)
            target.write_text('{"fixture": true}', encoding="utf-8")
            row["original-standard-check"][0]["evidence-ref"] = "out/evidence/cr4/standard.json::" + hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertTrue(m1_record_problems(row))

    def _model_fixture(self, root: Path, live_formula: bool = True) -> dict:
        """Small synthetic OOXML files; not Ray's research or an adjudication."""
        base = root / "out/evidence/cr4"
        base.mkdir(parents=True, exist_ok=True)
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        for name, value, cached in (("original.xlsx", "1", "2"), ("updated.xlsx", "2", "4")):
            formula = "<f>A1*2</f>" if name == "original.xlsx" or live_formula else ""
            with zipfile.ZipFile(base / name, "w") as archive:
                archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
                archive.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Model" sheetId="1" r:id="rId1"/></sheets></workbook>')
                archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>')
                archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1"><v>{value}</v></c><c r="B1">{formula}<v>{cached}</v></c></row></sheetData></worksheet>')
        (base / "changes.md").write_text(CHANGELOG_HEADER + "\n|---|---|---|---|---|---|---|\n| Model | A1 | 1 | 2 | fixture assumption | fixture period | fixture change |\n", encoding="utf-8")
        (base / "session.json").write_text('{"fixture": true}', encoding="utf-8")
        def digest(name):
            return hashlib.sha256((base / name).read_bytes()).hexdigest()
        def ref(name):
            return f"out/evidence/cr4/{name}::{digest(name)}"
        samples = [{"location": "Model!B1", "expected": "4", "actual": "4", "result": "通过"}]
        receipt = {"original-before-sha256": digest("original.xlsx"), "original-after-sha256": digest("original.xlsx"), "updated-sha256": digest("updated.xlsx"), "reopen": "通过", "recalculate": "通过", "samples": samples}
        (base / "verification.json").write_text(json.dumps(receipt), encoding="utf-8")
        artifacts = []
        for kind, name in (("MODEL-COPY", "original.xlsx"), ("XLSX", "updated.xlsx"), ("CHANGELOG", "changes.md")):
            artifacts.append({
                "artifact-id": name, "case-id": "cn", "kind": kind, "path": f"out/evidence/cr4/{name}", "sha256": digest(name), "bytes": (base / name).stat().st_size,
                "generated-by": "tencent-docs-sheetagent|fixture|tencent-docs-sheetagent",
                "open-check": {"host": "fixture", "at": "2026-10-21T00:00:00+08:00", "result": "成功"}, "content-check": "fixture",
                "structural": {"type": "xlsx", "ok": True, "detail": "fixture"},
                "meta": {"schema-query": "sheet.update", "tool-result": "成功", "table-route": "existing", "sheets": ["Model"], "formula-cells": 1, "samples": samples, "verification-ref": ref("verification.json")}, "deviations": [],
            })
        row = self._passing()
        row["m1-slot"] = "M1-02"
        row["adjudication"]["adjudicator"] = "synthetic-fixture"
        row["original-standard-check"] = [{"criterion": "model standard fixture", "evidence-ref": ref("session.json"), "result": "通过"}]
        def case(case_id, language):
            return {"case-id": case_id, "language": language, "market": "A股", "session-record": ref("session.json"), "expected": "fixture", "actual": "fixture", "result": "通过"}
        row["retest"].update({
            "positive-cases": [case("cn", "zh-CN"), case("en", "en-US")],
            "negative-cases": [{**case("negative", "zh-CN"), "type": "missing-prior-version"}], "artifacts": artifacts, "cross-session": None,
            "model-check": {"original-sha256": digest("original.xlsx"), "updated-sha256": digest("updated.xlsx"), "formulas": 1, "changes": [{"sheet": "Model", "cell": "A1", "before": "1", "after": "2"}], "reopen": "通过"},
        })
        return row

    def test_m1_02_reads_models_log_and_bound_reopen_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.object(_support, "ROOT", Path(tmp)):
            row = self._model_fixture(Path(tmp))
            self.assertEqual(m1_record_problems(row), [])
            mutations = (
                ("positive-cases", []), ("negative-cases", []), ("artifacts", []),
                ("model-check", {**row["retest"]["model-check"], "formulas": 9}),
                ("model-check", {**row["retest"]["model-check"], "changes": ["A1"]}),
                ("model-check", {**row["retest"]["model-check"], "original-sha256": "0" * 64}),
            )
            for key, value in mutations:
                bad = copy.deepcopy(row)
                bad["retest"][key] = value
                self.assertTrue(m1_record_problems(bad), key)
            for kind in ("MODEL-COPY", "XLSX", "CHANGELOG"):
                bad = copy.deepcopy(row)
                bad["retest"]["artifacts"] = [a for a in bad["retest"]["artifacts"] if a["kind"] != kind]
                self.assertTrue(m1_record_problems(bad), kind)
            for index in (0, 1, 2):
                bad = copy.deepcopy(row)
                bad["retest"]["artifacts"][index]["path"] = "out/evidence/cr4/missing"
                self.assertTrue(m1_record_problems(bad), index)
                bad = copy.deepcopy(row)
                bad["retest"]["artifacts"][index]["sha256"] = "0" * 64
                self.assertTrue(m1_record_problems(bad), index)
            bad = copy.deepcopy(row)
            bad["retest"]["artifacts"][1]["meta"]["verification-ref"] = "out/evidence/cr4/missing.json::" + "0" * 64
            self.assertTrue(m1_record_problems(bad))
            receipt_path = Path(tmp) / "out/evidence/cr4/verification.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for field, value in (("updated-sha256", "0" * 64), ("original-after-sha256", "0" * 64), ("reopen", "失败"), ("recalculate", "失败"), ("samples", [])):
                changed = {**receipt, field: value}
                receipt_path.write_text(json.dumps(changed), encoding="utf-8")
                bad = copy.deepcopy(row)
                bad["retest"]["artifacts"][1]["meta"]["verification-ref"] = "out/evidence/cr4/verification.json::" + hashlib.sha256(receipt_path.read_bytes()).hexdigest()
                self.assertTrue(m1_record_problems(bad), field)
            changed = copy.deepcopy(receipt)
            changed["samples"][0]["actual"] = "999"
            changed["samples"][0]["expected"] = "999"
            receipt_path.write_text(json.dumps(changed), encoding="utf-8")
            bad = copy.deepcopy(row)
            bad["retest"]["artifacts"][1]["meta"]["samples"] = changed["samples"]
            bad["retest"]["artifacts"][1]["meta"]["verification-ref"] = "out/evidence/cr4/verification.json::" + hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            self.assertTrue(any("reconcile" in p for p in m1_record_problems(bad)))
            no_formula = self._model_fixture(Path(tmp), live_formula=False)
            self.assertTrue(any("formula" in p for p in m1_record_problems(no_formula)))

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
