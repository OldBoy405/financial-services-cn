"""cmd-03 — M1-02 (`model-update`) evidence gate.

Consumes the M1-02 slot (`SLOT-03`) of `ACCEPTANCE.md` §6: the read-only copy of
the existing model must keep the recorded baseline hash, the updated workbook
must be an independent XLSX with live formulas, the changelog must be cell-level,
and the host recalculation/sample records must be bound to the updated file.
Nothing here creates a placeholder model or writes an adjudication.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import _support
from _support import (
    ACCEPTANCE,
    M1_ARTIFACT_KINDS,
    M1_BLOCK,
    M1_CASE_SUMMARY_LIMIT,
    M1_LANGUAGES,
    M1_MARKETS,
    M1_NEGATIVE_CASE_KEYS,
    M1_NEGATIVE_TYPES,
    M1_OPEN_RESULTS,
    M1_POSITIVE_CASE_KEYS,
    RepoTest,
    m1_readiness_problems,
    m1_slot,
    m1_tool_record_problems,
    read_json_block,
    resolve_evidence_path,
    sha256_file,
    split_evidence_ref,
)

SLOT_ID = "M1-02"
SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CHANGELOG_HEADER = "| 工作表 | 单元格 | 前值 | 后值/公式 | 假设 | 出处/期间 | 理由 |"
SAMPLE_KEYS = {"location", "expected", "actual", "result"}
DEVIATION_KEYS = ("requirement", "actual", "reason", "adjudication-ref")
ARTIFACT_KEYS = {
    "artifact-id",
    "case-id",
    "kind",
    "path",
    "sha256",
    "bytes",
    "generated-by",
    "open-check",
    "structural",
    "meta",
    "deviations",
}
OPEN_CHECK_KEYS = {"host", "at", "result"}
STRUCTURAL_KEYS = {"type", "ok", "detail"}


def load_slot() -> tuple[dict, dict]:
    block = read_json_block(ACCEPTANCE, M1_BLOCK)
    return block, m1_slot(block, SLOT_ID)


def setUpModule() -> None:  # noqa: N802 - unittest hook
    block = read_json_block(ACCEPTANCE, M1_BLOCK)
    problems = m1_readiness_problems(block, os.environ.get("M1_EVIDENCE_CONTEXT", "develop"))
    if problems:
        raise SystemExit("ENVIRONMENT_MISMATCH: " + "; ".join(problems))


@contextlib.contextmanager
def temp_root():
    original = _support.ROOT
    with tempfile.TemporaryDirectory() as tmp:
        _support.ROOT = Path(tmp)
        try:
            yield Path(tmp)
        finally:
            _support.ROOT = original


def formula_cell_count(xml_text: str) -> int:
    """Count `<f>` formula elements in one sheet XML document."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return 0
    return sum(1 for element in root.iter() if element.tag == f"{SHEET_NS}f")


def changelog_problems(text: str) -> list[str]:
    """Cell-level change log: exact 7-column header and at least one full row."""
    if not isinstance(text, str):
        return ["CHANGELOG must be UTF-8 markdown text"]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_index = next((index for index, line in enumerate(lines) if line == CHANGELOG_HEADER), None)
    if header_index is None:
        return ["CHANGELOG must carry the exact 7-column header"]
    rows = []
    for line in lines[header_index + 1:]:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(cells)
    problems = []
    if not rows:
        problems.append("CHANGELOG needs at least one data row")
    for index, cells in enumerate(rows):
        if len(cells) != 7:
            problems.append(f"CHANGELOG row {index + 1} must have 7 columns, got {len(cells)}")
        elif not all(cells):
            problems.append(f"CHANGELOG row {index + 1} has an empty cell")
    return problems


def model_route_problems(artifact: dict) -> list[str]:
    """Existing-model routing: sheet-agent only, table-route always `existing`."""
    if artifact.get("kind") not in ("MODEL-COPY", "XLSX"):
        return []
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    problems = []
    if meta.get("table-route") != "existing":
        problems.append("existing-model artifacts must keep table-route=existing")
    problems += m1_tool_record_problems(artifact, ("tencent-docs-sheetagent",))
    return problems


def _summary_problems(value: object, label: str) -> list[str]:
    if not isinstance(value, str):
        return [f"{label} must be a string"]
    problems = []
    if len(value) > M1_CASE_SUMMARY_LIMIT:
        problems.append(f"{label} exceeds {M1_CASE_SUMMARY_LIMIT} characters")
    if re.search(r"(?i)(api[_-]?key|secret|password|bearer\s+[a-z0-9._-]{8,}|sk-[a-z0-9]{8,})", value):
        problems.append(f"{label} must not contain credentials")
    return problems


def _case_problems(case: dict, keys: tuple[str, ...]) -> list[str]:
    if not isinstance(case, dict):
        return ["case record must be an object"]
    problems = []
    extra = sorted(set(case) - set(keys))
    missing = sorted(set(keys) - set(case))
    if extra:
        problems.append(f"case keys not allowed: {extra}")
    if missing:
        problems.append(f"case keys missing: {missing}")
    for key in ("input-summary", "response-summary"):
        problems += _summary_problems(case.get(key), f"case.{key}")
    return problems


def xlsx_problems(artifact: dict, baseline: str | None) -> list[str]:
    try:
        path = resolve_evidence_path(artifact.get("path"))
    except AssertionError as exc:
        return [f"artifact.path: {exc}"]
    if not path.is_file():
        return [f"artifact.path: file is missing: {artifact.get('path')}"]
    structural = artifact.get("structural") if isinstance(artifact.get("structural"), dict) else {}
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    problems = []
    if structural.get("type") != "xlsx" or structural.get("ok") is not True:
        problems.append("XLSX structural.type/ok must be xlsx/true")
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                problems.append("XLSX zip archive is corrupted")
            if "xl/workbook.xml" not in archive.namelist():
                return problems + ["XLSX is missing xl/workbook.xml"]
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = [element.get("name") for element in workbook.iter() if element.tag == f"{SHEET_NS}sheet"]
            actual_formulas = 0
            for name in archive.namelist():
                if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                    actual_formulas += formula_cell_count(archive.read(name).decode("utf-8"))
    except (zipfile.BadZipFile, ET.ParseError) as exc:
        return problems + [f"XLSX is not a readable OOXML package: {exc}"]
    if not sheets or not all(sheets):
        problems.append("XLSX workbook sheet names must be non-empty")
    if meta.get("sheets") != sheets:
        problems.append("meta.sheets does not match the workbook sheet names")
    if actual_formulas <= 0:
        problems.append("XLSX must contain at least one live formula cell")
    if meta.get("formula-cells") != actual_formulas:
        problems.append(f"meta.formula-cells must equal the {actual_formulas} live formulas")
    if baseline is not None and artifact.get("sha256") == baseline:
        problems.append("the updated XLSX must not overwrite the baseline model")
    return problems


def changelog_artifact_problems(artifact: dict) -> list[str]:
    try:
        path = resolve_evidence_path(artifact.get("path"))
    except AssertionError as exc:
        return [f"artifact.path: {exc}"]
    if not path.is_file():
        return [f"artifact.path: file is missing: {artifact.get('path')}"]
    text = path.read_text(encoding="utf-8")
    problems = changelog_problems(text)
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    rows = [line for line in text.splitlines() if line.strip().startswith("|") and "---" not in line]
    data_rows = max(len(rows) - 1, 0) if rows else 0
    if meta.get("change-count") != data_rows:
        problems.append("meta.change-count must equal the number of changelog data rows")
    return problems


def sample_problems(samples: list[dict], sheet_names: list[str], passed: bool) -> list[str]:
    if not isinstance(samples, list):
        return ["meta.samples must be a list"]
    problems = []
    if passed and not samples:
        problems.append("meta.samples needs at least one recalculation/sample record")
    for index, sample in enumerate(samples):
        label = f"meta.samples[{index}]"
        if not isinstance(sample, dict):
            problems.append(f"{label} must be an object")
            continue
        extra = sorted(set(sample) - SAMPLE_KEYS)
        missing = sorted(SAMPLE_KEYS - set(sample))
        if extra:
            problems.append(f"{label} keys not allowed: {extra}")
        if missing:
            problems.append(f"{label} keys missing: {missing}")
        if not all(str(sample.get(key) or "").strip() for key in SAMPLE_KEYS):
            problems.append(f"{label} fields must all be non-empty")
        location = str(sample.get("location") or "")
        if not ("!" in location or any(name and name in location for name in sheet_names)):
            problems.append(f"{label}.location must point at a sheet or cell in the updated workbook")
        if passed and sample.get("result") != "通过":
            problems.append(f"{label}.result must be 通过 once the slot is 通过")
    return problems


def artifact_keys_problems(artifact: dict) -> list[str]:
    """TASK-01 §6 whitelist: exact keys, kind enum and enumerated sub-records."""
    if not isinstance(artifact, dict):
        return ["artifact must be an object"]
    label = artifact.get("artifact-id") or "<artifact>"
    problems = []
    extra = sorted(set(artifact) - ARTIFACT_KEYS)
    missing = sorted(ARTIFACT_KEYS - set(artifact))
    if extra:
        problems.append(f"artifact {label!r}: keys not allowed: {extra}")
    if missing:
        problems.append(f"artifact {label!r}: keys missing: {missing}")
    if artifact.get("kind") not in M1_ARTIFACT_KINDS:
        problems.append(f"artifact {label!r}: kind is not allowed: {artifact.get('kind')!r}")
    if not isinstance(artifact.get("meta"), dict):
        problems.append(f"artifact {label!r}: meta must be an object")
    structural = artifact.get("structural")
    if not isinstance(structural, dict):
        problems.append(f"artifact {label!r}: structural must be an object")
    else:
        extra = sorted(set(structural) - STRUCTURAL_KEYS)
        missing = sorted(STRUCTURAL_KEYS - set(structural))
        if extra:
            problems.append(f"artifact {label!r}: structural keys not allowed: {extra}")
        if missing:
            problems.append(f"artifact {label!r}: structural keys missing: {missing}")
        if not isinstance(structural.get("ok"), bool):
            problems.append(f"artifact {label!r}: structural.ok must be boolean")
        if not isinstance(structural.get("detail"), str):
            problems.append(f"artifact {label!r}: structural.detail must be a string")
    open_check = artifact.get("open-check")
    if not isinstance(open_check, dict):
        problems.append(f"artifact {label!r}: open-check must be an object")
    else:
        extra = sorted(set(open_check) - OPEN_CHECK_KEYS)
        missing = sorted(OPEN_CHECK_KEYS - set(open_check))
        if extra:
            problems.append(f"artifact {label!r}: open-check keys not allowed: {extra}")
        if missing:
            problems.append(f"artifact {label!r}: open-check keys missing: {missing}")
        if open_check.get("result") not in M1_OPEN_RESULTS:
            problems.append(f"artifact {label!r}: open-check.result is not allowed")
    deviations = artifact.get("deviations")
    if not isinstance(deviations, list):
        problems.append(f"artifact {label!r}: deviations must be a list")
    else:
        for index, deviation in enumerate(deviations):
            if not isinstance(deviation, dict):
                problems.append(f"artifact {label!r}: deviations[{index}] must be an object")
                continue
            extra = sorted(set(deviation) - set(DEVIATION_KEYS))
            missing = sorted(set(DEVIATION_KEYS) - set(deviation))
            if extra:
                problems.append(f"artifact {label!r}: deviations[{index}] keys not allowed: {extra}")
            if missing:
                problems.append(f"artifact {label!r}: deviations[{index}] keys missing: {missing}")
            for key in DEVIATION_KEYS:
                if not str(deviation.get(key) or "").strip():
                    problems.append(f"artifact {label!r}: deviations[{index}].{key} is required")
    return problems


def open_check_problems(artifact: dict, passed: bool) -> list[str]:
    """Host identity/time always required; an updated XLSX also needs a successful open."""
    label = artifact.get("artifact-id")
    open_check = artifact.get("open-check") if isinstance(artifact.get("open-check"), dict) else {}
    problems = []
    for key in ("host", "at"):
        if not str(open_check.get(key) or "").strip():
            problems.append(f"artifact {label!r}: open-check.{key} is required")
    if passed and artifact.get("kind") == "XLSX" and open_check.get("result") != "成功":
        problems.append(f"artifact {label!r}: updated XLSX open-check must be 成功")
    return problems


def slot_evidence_problems(slot: dict, block: dict) -> list[str]:
    passed = slot.get("research-state") == "通过"
    baseline = (block.get("prerequisites") or {}).get("existing-model", {}).get("baseline-sha256")
    problems = []
    case_ids = set()
    for case in slot.get("positive-cases") or []:
        problems += _case_problems(case, M1_POSITIVE_CASE_KEYS)
        if case.get("language") not in M1_LANGUAGES:
            problems.append(f"{case.get('case-id')}: language is not allowed")
        if case.get("market") not in M1_MARKETS:
            problems.append(f"{case.get('case-id')}: market is not allowed")
        case_ids.add(case.get("case-id"))
    for case in slot.get("negative-cases") or []:
        problems += _case_problems(case, M1_NEGATIVE_CASE_KEYS)
        if case.get("type") not in M1_NEGATIVE_TYPES:
            problems.append(f"{case.get('case-id')}: negative type is not allowed")
        case_ids.add(case.get("case-id"))
    for case in (slot.get("positive-cases") or []) + (slot.get("negative-cases") or []):
        try:
            path, digest = split_evidence_ref(case.get("session-record"))
        except AssertionError as exc:
            problems.append(f"{case.get('case-id')}.session-record: {exc}")
            continue
        if not path.is_file() or sha256_file(path) != digest:
            problems.append(f"{case.get('case-id')}.session-record: file missing or sha256 mismatch")
        if passed and case.get("result") != "通过":
            problems.append(f"{case.get('case-id')}: result is not 通过")
    sheets = []
    artifact_ids = set()
    found = {"MODEL-COPY": 0, "XLSX": 0, "CHANGELOG": 0}
    for artifact in slot.get("artifacts") or []:
        if not isinstance(artifact, dict):
            problems.append("artifact must be an object")
            continue
        artifact_id = artifact.get("artifact-id")
        if artifact_id in artifact_ids:
            problems.append(f"duplicate artifact-id {artifact_id!r}")
        artifact_ids.add(artifact_id)
        kind = artifact.get("kind")
        if kind in found:
            found[kind] += 1
        if artifact.get("case-id") not in case_ids:
            problems.append(f"artifact {artifact_id!r}: case-id misses a registered case")
        try:
            path = resolve_evidence_path(artifact.get("path"))
        except AssertionError as exc:
            problems.append(f"artifact {artifact_id!r}.path: {exc}")
            continue
        if not path.is_file():
            problems.append(f"artifact {artifact_id!r}.path: file is missing")
        else:
            if sha256_file(path) != artifact.get("sha256"):
                problems.append(f"artifact {artifact_id!r}: sha256 does not match")
            if artifact.get("bytes") != path.stat().st_size:
                problems.append(f"artifact {artifact_id!r}: bytes does not match")
        if kind == "MODEL-COPY":
            if artifact.get("sha256") != baseline:
                problems.append(f"artifact {artifact_id!r}: MODEL-COPY must keep the baseline sha256")
            open_check = artifact.get("open-check") if isinstance(artifact.get("open-check"), dict) else {}
            if open_check.get("result") not in ("成功", "未执行"):
                problems.append(f"artifact {artifact_id!r}: MODEL-COPY open-check must be 成功/未执行")
        elif kind == "XLSX":
            problems += xlsx_problems(artifact, baseline)
            meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
            sheets = meta.get("sheets") if isinstance(meta.get("sheets"), list) else []
            problems += sample_problems(meta.get("samples") or [], sheets, passed)
            problems += open_check_problems(artifact, passed)
        elif kind == "CHANGELOG":
            problems += changelog_artifact_problems(artifact)
        problems += artifact_keys_problems(artifact)
        problems += model_route_problems(artifact)
        for index, deviation in enumerate(artifact.get("deviations") or []):
            for key in DEVIATION_KEYS:
                if not isinstance(deviation, dict) or not str(deviation.get(key) or "").strip():
                    problems.append(f"artifact {artifact_id!r}: deviations[{index}].{key} is required")
    if passed:
        languages = {case.get("language") for case in slot.get("positive-cases") or []}
        for language in M1_LANGUAGES:
            if language not in languages:
                problems.append(f"{SLOT_ID}: needs a {language} positive case")
        for kind in ("MODEL-COPY", "XLSX", "CHANGELOG"):
            if not found[kind]:
                problems.append(f"{SLOT_ID}: required artifact kind {kind} is missing")
        baseline_problem = m1_readiness_problems(block, "collect")
        if not isinstance(baseline, str) or not re.match(r"^[0-9a-f]{64}$", baseline):
            baseline_problem.append("existing-model.baseline-sha256 must be 64 lowercase hex chars")
        problems += baseline_problem
    return problems


class SyntheticChecks(unittest.TestCase):
    """Gates and their failure modes are exercised on temporary inputs only."""

    def test_formula_cell_count(self) -> None:
        two = (
            f'<worksheet xmlns="{SHEET_NS.strip("{}")}"><sheetData><row><c><f>1+1</f></c>'
            "<c><f>SUM(A1:A2)</f></c></row></sheetData></worksheet>"
        )
        one = f'<worksheet xmlns="{SHEET_NS.strip("{}")}"><sheetData><row><c><v>1</v></c></row></sheetData></worksheet>'
        self.assertEqual(formula_cell_count(two), 2)
        self.assertEqual(formula_cell_count(one), 0)
        self.assertEqual(formula_cell_count("<worksheet"), 0)

    def test_changelog_problems(self) -> None:
        good = CHANGELOG_HEADER + "\n|---|---|---|---|---|---|---|\n| 假设 | B12 | 100 | =B11*1.1 | 提价 10% | 2026Q3 报告 | 中报确认 |\n"
        self.assertEqual(changelog_problems(good), [])
        self.assertTrue(changelog_problems(CHANGELOG_HEADER + "\n"))
        self.assertTrue(changelog_problems(CHANGELOG_HEADER.replace("| 理由 |", "| note |") + "\n| a | b | c | d | e | f | g |"))
        self.assertTrue(changelog_problems(CHANGELOG_HEADER + "\n|---|---|---|---|---|---|---|\n| a | b | c | d | e | f | |"))

    def test_model_route_problems(self) -> None:
        with temp_root() as root:
            path = root / "out" / "evidence" / "m1" / "artifacts" / "case" / "model.xlsx"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"xlsx")
            artifact = {
                "artifact-id": "M1-02-A1",
                "case-id": "M1-02-P1",
                "kind": "XLSX",
                "path": "out/evidence/m1/artifacts/case/model.xlsx",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "generated-by": "tencent-docs-sheetagent|1.0|tencent-docs-sheetagent",
                "meta": {"schema-query": "sheet.update", "tool-result": "成功", "table-route": "existing"},
                "deviations": [],
            }
            self.assertEqual(model_route_problems(artifact), [])
            self.assertTrue(model_route_problems({**artifact, "meta": {**artifact["meta"], "table-route": "new"}}))
            self.assertTrue(
                model_route_problems({**artifact, "generated-by": "x|1|tencent-docs-sheet-generation"})
            )
            self.assertTrue(model_route_problems({**artifact, "meta": {"tool-result": "成功", "table-route": "existing"}}))

            adjudication = root / "out" / "evidence" / "m1" / "adjudications" / "m1-02-a1.json"
            adjudication.parent.mkdir(parents=True)
            adjudication.write_text(
                json.dumps(
                    {
                        "adjudicator": "Ray",
                        "decision": "批准最小替代",
                        "case-id": "M1-02-P1",
                        "artifact-id": "M1-02-A1",
                        "actual": "sheet-cli|3|local-sheet-edit",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            retest = root / "out" / "evidence" / "m1" / "retests" / "m1-02-a1.json"
            retest.parent.mkdir(parents=True)
            retest.write_text(
                json.dumps(
                    {
                        "case-id": "M1-02-P1",
                        "artifact-id": "M1-02-A1",
                        "kind": "XLSX",
                        "path": artifact["path"],
                        "sha256": artifact["sha256"],
                        "generated-by": "sheet-cli|3|local-sheet-edit",
                        "result": "成功",
                        "open-check-result": "成功",
                        "checked-at": "2026-10-17T10:00:00+08:00",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            unsupported = {
                **artifact,
                "generated-by": "sheet-cli|3|local-sheet-edit",
                "meta": {
                    **artifact["meta"],
                    "tool-result": "不支持",
                    "unsupported-generated-by": "tencent-docs-sheetagent|1.0|tencent-docs-sheetagent",
                    "retest": f"out/evidence/m1/retests/m1-02-a1.json::{sha256_file(retest)}",
                },
                "deviations": [
                    {
                        "requirement": "既有模型走 sheetagent",
                        "actual": "sheet-cli|3|local-sheet-edit",
                        "reason": "目标版本不支持",
                        "adjudication-ref": f"out/evidence/m1/adjudications/m1-02-a1.json::{sha256_file(adjudication)}",
                    }
                ],
            }
            self.assertEqual(model_route_problems(unsupported), [])
            self.assertTrue(
                model_route_problems({**unsupported, "meta": {**unsupported["meta"], "retest": "out/evidence/m1/retests/missing.json::" + "a" * 64}})
            )
            self.assertTrue(model_route_problems({**unsupported, "artifact-id": "M1-02-A2"}))

    def test_open_check_host_and_time_are_required(self) -> None:
        artifact = {
            "artifact-id": "M1-02-A1",
            "case-id": "M1-02-P1",
            "kind": "XLSX",
            "path": "out/evidence/m1/artifacts/case/model.xlsx",
            "sha256": "a" * 64,
            "bytes": 4,
            "generated-by": "tencent-docs-sheetagent|1.0|tencent-docs-sheetagent",
            "open-check": {"host": "workbuddy", "at": "2026-10-17T10:00:00+08:00", "result": "成功"},
            "structural": {"type": "xlsx", "ok": True, "detail": ""},
            "meta": {"schema-query": "sheet.update", "tool-result": "成功", "table-route": "existing"},
            "deviations": [],
        }
        self.assertEqual(open_check_problems(artifact, True), [])
        self.assertEqual(
            open_check_problems({**artifact, "open-check": {**artifact["open-check"], "result": "成功"}}, False),
            [],
        )
        self.assertTrue(
            open_check_problems({**artifact, "open-check": {**artifact["open-check"], "host": ""}}, True)
        )
        self.assertTrue(
            open_check_problems({**artifact, "open-check": {**artifact["open-check"], "at": ""}}, True)
        )
        self.assertTrue(
            open_check_problems({**artifact, "open-check": {**artifact["open-check"], "result": "未执行"}}, True)
        )
        self.assertTrue(artifact_keys_problems({**artifact, "prompt": "逐字输入"}))
        self.assertTrue(artifact_keys_problems({**artifact, "kind": "SHEET"}))
        self.assertTrue(
            artifact_keys_problems({key: value for key, value in artifact.items() if key != "open-check"})
        )
        self.assertTrue(artifact_keys_problems({**artifact, "structural": {"type": "xlsx", "ok": True}}))
        self.assertTrue(
            artifact_keys_problems(
                {**artifact, "deviations": [{"requirement": "r", "actual": "a", "reason": "why"}]}
            )
        )


class RepositoryChecks(RepoTest):
    def test_slot_identity_matches_the_legacy_record(self) -> None:
        _, slot = load_slot()
        self.assertEqual(slot.get("slot"), SLOT_ID)
        self.assertEqual(slot.get("skill"), "model-update")
        self.assertEqual(slot.get("acceptance-slot"), "SLOT-03")

    def test_registered_evidence_is_self_consistent(self) -> None:
        block, slot = load_slot()
        self.assertEqual(slot_evidence_problems(slot, block), [])


if __name__ == "__main__":
    unittest.main()
