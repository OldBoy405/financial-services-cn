"""cmd-05 — reinstall and release-readiness receipts (FR-12/FR-13)."""
from __future__ import annotations

import re
import unittest

from _support import ACCEPTANCE, C4_CLOSEOUT_BLOCK, RepoTest, read_json_block

RIN_IDS = tuple(f"RIN-C4-{index:02d}" for index in range(1, 9))
RDY_IDS = tuple(f"RDY-C4-{index:02d}" for index in range(1, 8))
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _step_problems(step: dict, label: str) -> list[str]:
    problems = []
    for key in ("stage", "actual-step", "client-version", "validator-version", "package-version", "result", "evidence-ref"):
        if not str(step.get(key) or "").strip():
            problems.append(f"{label}: missing {key}")
    if not SHA_RE.match(step.get("package-content-sha256") or ""):
        problems.append(f"{label}: package-content-sha256 must be 64 lowercase hex")
    return problems


def _item_problems(item: dict, label: str) -> list[str]:
    problems = []
    for key in ("item", "method", "found", "conclusion", "blocking-scope", "evidence-ref"):
        if not str(item.get(key) or "").strip():
            problems.append(f"{label}: missing {key}")
    return problems


def closeout_problems(closeout: dict) -> list[str]:
    problems: list[str] = []
    closeout_block = closeout.get("closeout") or {}
    reinstall = closeout_block.get("reinstall") or {}
    readiness = closeout_block.get("readiness") or {}
    steps = reinstall.get("steps") or []
    items = readiness.get("items") or []
    if reinstall.get("status") == "通过":
        if [step.get("rin-id") for step in steps] != list(RIN_IDS):
            problems.append("reinstall.steps must be RIN-C4-01..08 in order")
        for step in steps:
            problems += _step_problems(step, f"reinstall.{step.get('rin-id')}")
        if not reinstall.get("evidence-ref"):
            problems.append("reinstall.evidence-ref is required when status=通过")
    if readiness.get("status") == "通过":
        if [item.get("rdy-id") for item in items] != list(RDY_IDS):
            problems.append("readiness.items must be RDY-C4-01..07 in order")
        for item in items:
            problems += _item_problems(item, f"readiness.{item.get('rdy-id')}")
        if not readiness.get("evidence-ref"):
            problems.append("readiness.evidence-ref is required when status=通过")
    if closeout_block.get("final-wording-allowed"):
        if reinstall.get("status") != "通过" or readiness.get("status") != "通过":
            problems.append("final-wording-allowed requires both reinstall and readiness 通过")
    distribution = closeout.get("distribution") or {}
    if distribution.get("marketplace") not in ("not-submitted", "") and distribution.get("public-distribution") == "approved":
        problems.append("marketplace must not claim approval")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _passing(self) -> dict:
        steps = [{
            "rin-id": rin, "stage": "s", "actual-step": "a", "client-version": "c",
            "validator-version": "v", "package-version": "0.11.0",
            "package-content-sha256": "a" * 64, "result": "通过", "evidence-ref": "out/evidence/cr4/r.json::" + "b" * 64,
        } for rin in RIN_IDS]
        items = [{
            "rdy-id": rdy, "item": "i", "method": "m", "found": "f", "conclusion": "c",
            "blocking-scope": "none", "evidence-ref": "out/evidence/cr4/d.json::" + "c" * 64,
        } for rdy in RDY_IDS]
        return {"closeout": {
            "reinstall": {"status": "通过", "evidence-ref": "x", "steps": steps},
            "readiness": {"status": "通过", "evidence-ref": "y", "items": items},
            "final-wording-allowed": True,
            "final-wording": "phase-1 本机自用 9/9 完成",
        }, "distribution": {"marketplace": "not-submitted"}}

    def test_closeout_gate(self) -> None:
        block = self._passing()
        self.assertEqual(closeout_problems(block), [])
        self.assertTrue(closeout_problems({"closeout": {**block["closeout"], "reinstall": {**block["closeout"]["reinstall"], "steps": []}}}))
        self.assertTrue(closeout_problems({"closeout": {**block["closeout"], "readiness": {**block["closeout"]["readiness"], "status": "待测"}}}))


class RepositoryContract(RepoTest):
    def test_reinstall_and_readiness(self) -> None:
        closeout = read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)
        problems = closeout_problems(closeout)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_distribution_is_separate(self) -> None:
        closeout = read_json_block(ACCEPTANCE, C4_CLOSEOUT_BLOCK)
        distribution = closeout.get("distribution") or {}
        self.assertEqual(distribution.get("public-distribution"), "pending")
        self.assertEqual(distribution.get("marketplace"), "not-submitted")


if __name__ == "__main__":
    unittest.main()
