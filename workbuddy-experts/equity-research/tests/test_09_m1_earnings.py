"""cmd-02 — M1-01 (`earnings-analysis`) evidence gate.

Only the M1-01 slot of `ACCEPTANCE.md` §6 is consumed. The module checks the
DOCX/Summary structure pre-trial, page/figure/table anchors, the eight-item
quality checklist, CN/EN market coverage and the AC-06 host-tool records. It
never produces a Ray adjudication and never writes to `out/` or the index.
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
    M1_BLOCK,
    M1_CASE_SUMMARY_LIMIT,
    M1_EARNINGS_CHECKLIST_SIZE,
    M1_LANGUAGES,
    M1_MARKETS,
    M1_NEGATIVE_CASE_KEYS,
    M1_NEGATIVE_TYPES,
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

SLOT_ID = "M1-01"
CHECKLIST_RESULTS = ("通过", "不通过", "不适用")
DEVIATION_KEYS = ("requirement", "actual", "reason", "adjudication-ref")


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


def _int_problem(meta: dict, key: str) -> list[str]:
    value = meta.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        return [f"meta.{key} must be an integer"]
    return []


def anchor_violations(meta: dict) -> list[str]:
    """PRD anchors: 8-12 pages, 8-12 figures, 1-3 summary tables."""
    if not isinstance(meta, dict):
        return ["meta must be an object"]
    problems = _int_problem(meta, "pages") + _int_problem(meta, "figures") + _int_problem(meta, "summary-tables")
    if problems:
        return [problem.split(".")[-1].split()[0] for problem in problems]
    violations = []
    if not 8 <= meta["pages"] <= 12:
        violations.append("pages")
    if not 8 <= meta["figures"] <= 12:
        violations.append("figures")
    if not 1 <= meta["summary-tables"] <= 3:
        violations.append("summary-tables")
    return violations


def checklist_problems(items: list[dict], passed: bool) -> list[str]:
    problems = []
    if not isinstance(items, list):
        return ["quality-checklist must be a list"]
    if passed and len(items) != M1_EARNINGS_CHECKLIST_SIZE:
        problems.append(f"quality-checklist must have {M1_EARNINGS_CHECKLIST_SIZE} items, got {len(items)}")
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"quality-checklist[{index}] must be an object")
            continue
        label = f"quality-checklist[{index}]"
        extra = sorted(set(item) - {"item", "result", "evidence-ref"})
        if extra:
            problems.append(f"{label} keys not allowed: {extra}")
        for key in ("item", "result", "evidence-ref"):
            if not str(item.get(key) or "").strip():
                problems.append(f"{label}.{key} is required")
        if item.get("result") not in CHECKLIST_RESULTS:
            problems.append(f"{label}.result is not allowed: {item.get('result')!r}")
        if passed and item.get("result") == "不通过":
            problems.append(f"{label} is 不通过 while the slot claims 通过")
        if item.get("item") in seen:
            problems.append(f"{label}.item duplicates another item")
        seen.add(item.get("item"))
    return problems


def tool_record_problems(artifact: dict) -> list[str]:
    kind = artifact.get("kind")
    if kind == "DOCX":
        routes = ("tencent-docx",)
    elif kind == "SUMMARY":
        routes = ("host-preview", "tencent-docx")
    else:
        return []
    return m1_tool_record_problems(artifact, routes)


def _cjk_problems(path: Path) -> list[str]:
    if not re.search(r"[一-鿿]", path.name):
        return [f"artifact file name must contain a CJK character: {path.name!r}"]
    return []


def structure_problems(artifact: dict) -> list[str]:
    """DOCX/Summary structure pre-trial (stdlib zipfile + ElementTree only)."""
    if not isinstance(artifact, dict):
        return ["artifact must be an object"]
    kind = artifact.get("kind")
    if kind not in ("DOCX", "SUMMARY"):
        return []
    try:
        path = resolve_evidence_path(artifact.get("path"))
    except AssertionError as exc:
        return [f"artifact.path: {exc}"]
    if not path.is_file():
        return [f"artifact.path: file is missing: {artifact.get('path')}"]
    structural = artifact.get("structural") if isinstance(artifact.get("structural"), dict) else {}
    problems = []
    if kind == "DOCX":
        if structural.get("type") != "docx" or structural.get("ok") is not True:
            problems.append("DOCX structural.type/ok must be docx/true")
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    problems.append("DOCX zip archive is corrupted")
                if "word/document.xml" not in archive.namelist():
                    problems.append("DOCX is missing word/document.xml")
                else:
                    ET.fromstring(archive.read("word/document.xml"))
        except (zipfile.BadZipFile, ET.ParseError) as exc:
            problems.append(f"DOCX is not a readable OOXML package: {exc}")
        problems += _cjk_problems(path)
        meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
        for key in ("pages", "figures", "summary-tables"):
            problems += _int_problem(meta, key)
    else:
        if structural.get("type") != "markdown" or structural.get("ok") is not True:
            problems.append("SUMMARY structural.type/ok must be markdown/true")
        if path.stat().st_size == 0:
            problems.append("SUMMARY must not be empty")
    return problems


def deviation_problems(artifact: dict) -> list[str]:
    """Every anchor violation needs an adjudicated deviation, not a silent waiver."""
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    violations = anchor_violations(meta) if artifact.get("kind") == "DOCX" else []
    if not violations:
        return []
    problems = []
    deviations = [d for d in artifact.get("deviations") or [] if isinstance(d, dict)]
    for violation in violations:
        if not any(violation in str(deviation.get("requirement") or "") for deviation in deviations):
            problems.append(f"artifact {artifact.get('artifact-id')!r}: anchor {violation!r} needs a deviation")
    for deviation in deviations:
        for key in DEVIATION_KEYS:
            if not str(deviation.get(key) or "").strip():
                problems.append(f"artifact {artifact.get('artifact-id')!r}: deviation.{key} is required")
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


def slot_evidence_problems(slot: dict) -> list[str]:
    """Fail-closed over whatever M1-01 has registered, whether or not it is 通过."""
    passed = slot.get("research-state") == "通过"
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
    artifact_ids = set()
    for artifact in slot.get("artifacts") or []:
        if not isinstance(artifact, dict):
            problems.append("artifact must be an object")
            continue
        artifact_id = artifact.get("artifact-id")
        if artifact_id in artifact_ids:
            problems.append(f"duplicate artifact-id {artifact_id!r}")
        artifact_ids.add(artifact_id)
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
        problems += structure_problems(artifact)
        problems += tool_record_problems(artifact)
        problems += deviation_problems(artifact)
        open_check = artifact.get("open-check") if isinstance(artifact.get("open-check"), dict) else {}
        if not str(open_check.get("host") or "").strip() or not str(open_check.get("at") or "").strip():
            problems.append(f"artifact {artifact_id!r}: open-check.host/at are required")
        if passed and open_check.get("result") != "成功":
            problems.append(f"artifact {artifact_id!r}: open-check must be 成功 once the slot is 通过")
    if passed:
        languages = {case.get("language") for case in slot.get("positive-cases") or []}
        for language in M1_LANGUAGES:
            if language not in languages:
                problems.append(f"{SLOT_ID}: needs a {language} positive case")
        kinds = {artifact.get("kind") for artifact in slot.get("artifacts") or [] if isinstance(artifact, dict)}
        for kind in ("DOCX", "SUMMARY"):
            if kind not in kinds:
                problems.append(f"{SLOT_ID}: required artifact kind {kind} is missing")
        problems += checklist_problems(slot.get("quality-checklist") or [], True)
    return problems


class SyntheticChecks(unittest.TestCase):
    """The gates must be provably able to fail, using temporary data only."""

    def test_anchor_violations(self) -> None:
        self.assertEqual(anchor_violations({"pages": 13, "figures": 9, "summary-tables": 2}), ["pages"])
        self.assertEqual(anchor_violations({"pages": 9, "figures": 8, "summary-tables": 2}), [])
        self.assertEqual(anchor_violations({"pages": 7, "figures": 13, "summary-tables": 4}), ["pages", "figures", "summary-tables"])
        self.assertTrue(anchor_violations({"pages": "9"}))

    def test_checklist_problems(self) -> None:
        good = [
            {"item": f"item-{index}", "result": "通过", "evidence-ref": f"out/evidence/m1/checklist/{index}.json"}
            for index in range(M1_EARNINGS_CHECKLIST_SIZE)
        ]
        self.assertEqual(checklist_problems(good, True), [])
        self.assertTrue(checklist_problems(good[:7], True))
        self.assertTrue(checklist_problems([{**good[0], "evidence-ref": ""}] + good[1:], True))
        self.assertTrue(checklist_problems([{**good[0], "result": "不通过"}] + good[1:], True))

    def test_tool_record_two_branches(self) -> None:
        with temp_root() as root:
            path = root / "out" / "evidence" / "m1" / "artifacts" / "case" / "茅台业绩点评.docx"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"docx")
            payload = {
                "artifact-id": "M1-01-A1",
                "case-id": "M1-01-P1",
                "kind": "DOCX",
                "path": "out/evidence/m1/artifacts/case/茅台业绩点评.docx",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "generated-by": "tencent-docx|1.2.0|tencent-docx",
                "meta": {"schema-query": "docx.create", "tool-result": "成功", "pages": 9, "figures": 8, "summary-tables": 2},
                "deviations": [],
            }
            self.assertEqual(tool_record_problems(payload), [])
            self.assertTrue(tool_record_problems({**payload, "generated-by": "x|1|host-preview"}))
            self.assertTrue(tool_record_problems({**payload, "meta": {"schema-query": "", "tool-result": "成功"}}))
            summary = {**payload, "kind": "SUMMARY", "generated-by": "host|1|host-preview", "meta": {"schema-query": "md", "tool-result": "成功"}}
            self.assertEqual(tool_record_problems(summary), [])
            self.assertTrue(tool_record_problems({**summary, "generated-by": "host|1|matplotlib-fallback"}))


class RepositoryChecks(RepoTest):
    def test_slot_identity_matches_the_legacy_record(self) -> None:
        block, slot = load_slot()
        self.assertEqual(slot.get("slot"), SLOT_ID)
        self.assertEqual(slot.get("skill"), "earnings-analysis")
        self.assertEqual(slot.get("acceptance-slot"), "SLOT-01")
        legacy = _support.ACCEPTANCE.read_text(encoding="utf-8").split("## 2.", 1)[1].split("## 3.", 1)[0]
        self.assertIn("slot: SLOT-01", legacy)
        self.assertIn("skill: earnings-analysis", legacy)

    def test_registered_evidence_is_self_consistent(self) -> None:
        _, slot = load_slot()
        self.assertEqual(slot_evidence_problems(slot), [])

    def test_docx_and_summary_never_replaced_by_public_only(self) -> None:
        _, slot = load_slot()
        if slot.get("research-state") == "通过":
            kinds = {artifact.get("kind") for artifact in slot.get("artifacts") or []}
            self.assertIn("DOCX", kinds)
            self.assertIn("SUMMARY", kinds)


if __name__ == "__main__":
    unittest.main()
