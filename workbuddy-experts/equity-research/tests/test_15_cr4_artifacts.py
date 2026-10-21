"""cmd-03 — artifacts, host checks and tool capability groups (FR-10)."""
from __future__ import annotations

import re
import unittest

import _support
from _support import ACCEPTANCE, C4_BLOCK, C4_SLOTS, RepoTest, read_json_block

ARTIFACT_KINDS = {"DOCX", "XLSX", "PPTX", "MD", "RESPONSE", "SUMMARY", "MODEL-COPY", "CHANGELOG", "ZIP", "REPORT"}
REQUIRED = {
    "C4-01": ({"RESPONSE", "MD"},),
    "C4-02": ({"XLSX"}, {"MD"}),
    "C4-03": ({"MD"},),
    "C4-04": ({"DOCX", "MD"},),
    "C4-05": ({"XLSX"}, {"DOCX", "PPTX"}),
    "C4-06": ({"MD", "DOCX"},),
}
TOOL_BY_ROUTE = {
    "existing-model": "tencent-docs-sheetagent",
    "new-xlsx": "tencent-docs-sheet-generation",
    "docx": "tencent-docx",
}


def _artifact_problems(artifact: dict, label: str) -> list[str]:
    problems = []
    if artifact.get("kind") not in ARTIFACT_KINDS:
        problems.append(f"{label}: invalid kind")
    path = artifact.get("path") or ""
    if not path.startswith("out/evidence/cr4/"):
        problems.append(f"{label}: path must be under out/evidence/cr4/")
    if not re.match(r"^[0-9a-f]{64}$", artifact.get("sha256") or ""):
        problems.append(f"{label}: sha256 must be 64 lowercase hex characters")
    if not artifact.get("generated-by"):
        problems.append(f"{label}: generated-by is required")
    if not artifact.get("open-check"):
        problems.append(f"{label}: open-check is required")
    if not artifact.get("content-check"):
        problems.append(f"{label}: content-check is required")
    if not isinstance(artifact.get("deviations"), list):
        problems.append(f"{label}: deviations must be a list")
    return problems


def slot_artifact_problems(slot: dict) -> list[str]:
    problems: list[str] = []
    artifacts = slot.get("artifacts") or []
    for artifact in artifacts:
        problems += _artifact_problems(artifact, f"{slot.get('slot')}.artifact")
    if slot.get("research-state") != "通过":
        return problems
    kinds = {artifact.get("kind") for artifact in artifacts}
    for alternatives in REQUIRED[slot.get("slot", "")]:
        if not kinds & alternatives:
            problems.append(f"{slot.get('slot')}: missing one of {sorted(alternatives)}")
    if "RESPONSE" in kinds and not any(artifact.get("kind") == "RESPONSE" and artifact.get("meta", {}).get("mapping-basis") for artifact in artifacts):
        problems.append(f"{slot.get('slot')}: reply artifact needs a mapping basis")
    return problems


def tool_group_problems(group: dict, label: str) -> list[str]:
    problems: list[str] = []
    allowed = group.get("allowed-routes") or []
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
    if group.get("capability") == "sheet-edit" and "new-xlsx" in allowed:
        problems.append(f"{label}: sheet-edit may not accept new-xlsx")
    return problems


def requirement_problems(slot: dict) -> list[str]:
    problems: list[str] = []
    for group in slot.get("required-tools") or []:
        problems += tool_group_problems(group, f"{slot.get('slot')}.{group.get('capability')}")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _artifact(self, kind: str) -> dict:
        return {
            "kind": kind,
            "path": "out/evidence/cr4/a.docx",
            "sha256": "a" * 64,
            "generated-by": "tencent-docx|1.0|docx",
            "open-check": "opened",
            "content-check": "checked",
            "deviations": [],
        }

    def test_artifact_gate(self) -> None:
        slot = {"slot": "C4-02", "research-state": "通过", "artifacts": [self._artifact("XLSX"), self._artifact("MD")]}
        self.assertEqual(slot_artifact_problems(slot), [])
        self.assertTrue(slot_artifact_problems({**slot, "artifacts": []}))
        self.assertTrue(slot_artifact_problems({**slot, "artifacts": [{**self._artifact("XLSX"), "open-check": ""}]}))

    def test_tool_capability_gate(self) -> None:
        ok = {"capability": "sheet-edit", "allowed-routes": ["existing-model"], "selected-route": "existing-model", "selected-tool": "tencent-docs-sheetagent", "accepted": True}
        self.assertEqual(tool_group_problems(ok, "g"), [])
        bad = {**ok, "selected-route": "new-xlsx", "selected-tool": "tencent-docs-sheet-generation", "accepted": True, "allowed-routes": ["existing-model", "new-xlsx"]}
        self.assertTrue(tool_group_problems(bad, "g"))


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

    def test_all_slots_have_four_required_records(self) -> None:
        c4 = read_json_block(ACCEPTANCE, C4_BLOCK)
        self.assertEqual({slot.get("slot") for slot in c4.get("slots") or []}, {row[0] for row in C4_SLOTS})
        self.assertEqual(len((c4.get("prerequisites") or {}).get("slots") or []), 9)


if __name__ == "__main__":
    unittest.main()
