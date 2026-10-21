"""cmd-03 — artifacts, host checks and tool capability groups (FR-10)."""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import _support
from _support import ACCEPTANCE, C4_BLOCK, C4_SLOTS, RepoTest, c4_check_artifact, read_json_block

ARTIFACT_KINDS = {"DOCX", "XLSX", "PPTX", "MD", "RESPONSE", "SUMMARY", "MODEL-COPY", "CHANGELOG", "ZIP", "REPORT"}
REQUIRED = {
    "C4-01": ({"RESPONSE", "MD"},),
    "C4-02": ({"XLSX"}, {"MD"}),
    "C4-03": ({"MD"},),
    "C4-04": ({"DOCX", "MD"},),
    "C4-05": ({"XLSX"}, {"DOCX", "PPTX"}),
    "C4-06": ({"MD", "DOCX"},),
}
EXPECTED_GROUPS = {
    "C4-02": {"sheet-create": {"new-xlsx"}},
    "C4-05": {"document-output": {"docx", "pptx"}, "sheet-create": {"new-xlsx"}},
    "M1-01": {"docx-output": {"docx"}},
    "M1-02": {"sheet-edit": {"existing-model"}},
    "M1-03": {"docx-output": {"docx"}, "sheet-create": {"new-xlsx"}, "chart-output": {"chart"}},
}
TOOL_BY_ROUTE = {
    "existing-model": "tencent-docs-sheetagent",
    "new-xlsx": "tencent-docs-sheet-generation",
    "docx": "tencent-docx",
}


def _generated_by_problems(value: str, label: str) -> list[str]:
    parts = (value or "").split("|")
    if len(parts) != 3 or not all(part.strip() for part in parts):
        return [f"{label}: generated-by must be tool|version|route"]
    return []


def _artifact_problems(artifact: dict, label: str, verify: bool = True) -> list[str]:
    problems = []
    if artifact.get("kind") not in ARTIFACT_KINDS:
        problems.append(f"{label}: invalid kind")
    if not (artifact.get("path") or "").startswith("out/evidence/cr4/"):
        problems.append(f"{label}: path must be under out/evidence/cr4/")
    if not re.match(r"^[0-9a-f]{64}$", artifact.get("sha256") or ""):
        problems.append(f"{label}: sha256 must be 64 lowercase hex characters")
    problems += _generated_by_problems(artifact.get("generated-by") or "", label)
    if not artifact.get("open-check"):
        problems.append(f"{label}: open-check is required")
    if not artifact.get("content-check"):
        problems.append(f"{label}: content-check is required")
    if not isinstance(artifact.get("deviations"), list):
        problems.append(f"{label}: deviations must be a list")
    if verify:
        problems += c4_check_artifact(artifact, label)
    return problems


def slot_artifact_problems(slot: dict, verify: bool = True) -> list[str]:
    problems: list[str] = []
    artifacts = slot.get("artifacts") or []
    for artifact in artifacts:
        problems += _artifact_problems(artifact, f"{slot.get('slot')}.artifact", verify)
    if slot.get("research-state") != "通过":
        return problems
    kinds = {artifact.get("kind") for artifact in artifacts}
    for alternatives in REQUIRED[slot.get("slot", "")]:
        if not kinds & alternatives:
            problems.append(f"{slot.get('slot')}: missing one of {sorted(alternatives)}")
    if "RESPONSE" in kinds and not any(artifact.get("kind") == "RESPONSE" and artifact.get("meta", {}).get("mapping-basis") for artifact in artifacts):
        problems.append(f"{slot.get('slot')}: reply artifact needs a mapping basis")
    if slot.get("slot") == "C4-04" and not any(artifact.get("meta", {}).get("consensus-table") for artifact in artifacts):
        problems.append("C4-04: earnings preview must record a consensus table")
    if slot.get("slot") == "C4-06" and not (
        any(artifact.get("meta", {}).get("old-version") for artifact in artifacts)
        and any(artifact.get("meta", {}).get("changelog") for artifact in artifacts)
    ):
        problems.append("C4-06: thesis must record old-version and changelog markers")
    return problems


def tool_group_problems(group: dict, label: str) -> list[str]:
    problems: list[str] = []
    allowed = set(group.get("allowed-routes") or [])
    selected = group.get("selected-route") or ""
    tool = group.get("selected-tool") or ""
    if not allowed:
        problems.append(f"{label}: allowed-routes is empty")
    if group.get("accepted"):
        if selected not in allowed:
            problems.append(f"{label}: selected-route is not allowed")
        if not tool:
            problems.append(f"{label}: selected-tool is required")
        if selected in TOOL_BY_ROUTE and tool != TOOL_BY_ROUTE[selected]:
            problems.append(f"{label}: {selected} must use {TOOL_BY_ROUTE[selected]}")
        if selected in ("pptx", "chart") and ("sheet-generation" in tool or not tool):
            problems.append(f"{label}: {selected} needs its own verified tool route")
    if group.get("capability") == "sheet-edit" and "new-xlsx" in allowed:
        problems.append(f"{label}: sheet-edit may not accept new-xlsx")
    return problems


def requirement_problems(slot: dict) -> list[str]:
    problems: list[str] = []
    groups = {group.get("capability"): group for group in slot.get("required-tools") or []}
    expected = EXPECTED_GROUPS.get(slot.get("slot", ""))
    if expected and slot.get("research-state") == "通过":
        if set(groups) != set(expected):
            problems.append(f"{slot.get('slot')}: required capability groups differ from the slot contract")
    for capability, group in groups.items():
        problems += tool_group_problems(group, f"{slot.get('slot')}.{capability}")
        if expected and capability in expected and set(group.get("allowed-routes") or []) != expected[capability]:
            problems.append(f"{slot.get('slot')}.{capability}: allowed-routes differ from the slot contract")
        if expected and slot.get("research-state") == "通过" and group.get("accepted") is not True:
            problems.append(f"{slot.get('slot')}.{capability}: 通过 requires accepted=true")
    for capability in expected or {}:
        if capability not in groups:
            problems.append(f"{slot.get('slot')}: missing capability {capability}")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _artifact(self, kind: str) -> dict:
        return {
            "kind": kind,
            "path": "out/evidence/cr4/a.docx",
            "sha256": "a" * 64,
            "bytes": 1,
            "generated-by": "tencent-docx|1.0|docx",
            "open-check": "opened",
            "content-check": "checked",
            "deviations": [],
            "meta": {},
        }

    def test_artifact_gate(self) -> None:
        slot = {"slot": "C4-02", "research-state": "通过", "artifacts": [self._artifact("XLSX"), self._artifact("MD")]}
        self.assertEqual(slot_artifact_problems(slot, verify=False), [])
        self.assertTrue(slot_artifact_problems({**slot, "artifacts": []}, verify=False))
        self.assertTrue(slot_artifact_problems({**slot, "artifacts": [{**self._artifact("XLSX"), "open-check": ""}]}, verify=False))
        self.assertTrue(slot_artifact_problems({**slot, "artifacts": [{**self._artifact("XLSX"), "generated-by": "x"}]}, verify=False))

    def test_tool_capability_gate(self) -> None:
        slot = {"slot": "M1-02", "research-state": "通过", "required-tools": [
            {"capability": "sheet-edit", "allowed-routes": ["existing-model"], "selected-route": "existing-model", "selected-tool": "tencent-docs-sheetagent", "accepted": True}
        ]}
        self.assertEqual(requirement_problems(slot), [])
        bad = {**slot, "required-tools": [{**slot["required-tools"][0], "selected-tool": "tencent-docs-sheet-generation"}]}
        self.assertTrue(requirement_problems(bad))
        missing = {**slot, "required-tools": []}
        self.assertTrue(requirement_problems(missing))

    def test_artifact_file_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_root = _support.ROOT
            try:
                _support.ROOT = Path(tmp)
                (Path(tmp) / "out" / "evidence" / "cr4").mkdir(parents=True)
                target = Path(tmp) / "out" / "evidence" / "cr4" / "a.docx"
                target.write_bytes(b"not-a-zip")
                artifact = {**self._artifact("DOCX"), "sha256": "0" * 64, "bytes": 9}
                problems = _artifact_problems(artifact, "a", verify=True)
                self.assertTrue(any("sha256" in problem for problem in problems))
                self.assertTrue(any("ZIP" in problem for problem in problems))
            finally:
                _support.ROOT = old_root


class RepositoryContract(RepoTest):
    def test_slot_artifacts(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        problems: list[str] = []
        for slot in c4.get("slots") or []:
            problems += slot_artifact_problems(slot)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_tool_capability_groups(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        problems: list[str] = []
        for slot in (c4.get("prerequisites") or {}).get("slots") or []:
            problems += requirement_problems(slot)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_all_slots_have_required_records(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        self.assertEqual({slot.get("slot") for slot in c4.get("slots") or []}, {row[0] for row in C4_SLOTS})
        self.assertEqual(len((c4.get("prerequisites") or {}).get("slots") or []), 9)


if __name__ == "__main__":
    unittest.main()
