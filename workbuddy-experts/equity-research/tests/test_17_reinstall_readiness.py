"""cmd-05 — reinstall and release-readiness receipts (FR-12/FR-13)."""
from __future__ import annotations

import re
import unittest

from _support import ACCEPTANCE, C4_CLOSEOUT_BLOCK, RepoTest, c4_check_ref, read_json_block

RIN_IDS = tuple(f"RIN-C4-{index:02d}" for index in range(1, 9))
RDY_IDS = tuple(f"RDY-C4-{index:02d}" for index in range(1, 8))
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GOOD_CONCLUSIONS = {"通过", "无", "无阻塞", "不适用"}


def _step_problems(step: dict, label: str, package_hash: str, verify: bool = True) -> list[str]:
    problems = []
    for key in ("stage", "actual-step", "client-version", "validator-version", "package-version", "result", "evidence-ref"):
        if not str(step.get(key) or "").strip():
            problems.append(f"{label}: missing {key}")
    if step.get("result") != "通过":
        problems.append(f"{label}: result must be 通过")
    if not SHA_RE.match(step.get("package-content-sha256") or ""):
        problems.append(f"{label}: package-content-sha256 must be 64 lowercase hex")
    if package_hash and step.get("package-content-sha256") != package_hash:
        problems.append(f"{label}: package hash differs from the closeout package")
    if step.get("rin-id") == "RIN-C4-01":
        runs = step.get("export-runs") or []
        if len(runs) != 2:
            problems.append("RIN-C4-01: exactly two export runs are required")
        else:
            first = {item.get("path"): item.get("sha256") for item in runs[0].get("files") or []}
            second = {item.get("path"): item.get("sha256") for item in runs[1].get("files") or []}
            if not first or first != second:
                problems.append("RIN-C4-01: export file sets/digests differ between runs")
            if verify:
                for run in runs:
                    for item in run.get("files") or []:
                        problems += c4_check_ref(f"{item.get('path')}::{item.get('sha256')}", "RIN-C4-01.export")
    if step.get("rin-id") in ("RIN-C4-02", "RIN-C4-03") and step.get("exit-code") != 0:
        problems.append(f"{label}: exit-code must be 0")
    if step.get("rin-id") == "RIN-C4-03" and not step.get("terminal-state"):
        problems.append("RIN-C4-03: terminal-state is required")
    if step.get("rin-id") == "RIN-C4-05" and step.get("installed-version") != step.get("package-version"):
        problems.append("RIN-C4-05: installed version must match the package version")
    if step.get("rin-id") == "RIN-C4-04":
        if not step.get("recovery-point"):
            problems.append("RIN-C4-04: recovery point is required")
        elif verify:
            problems += c4_check_ref(step.get("recovery-point"), "RIN-C4-04.recovery-point")
    if verify and step.get("evidence-ref"):
        problems += c4_check_ref(step.get("evidence-ref"), f"{label}.evidence-ref")
    if step.get("rin-id") in ("RIN-C4-06", "RIN-C4-07"):
        session = step.get("new-session") or {}
        connectors = session.get("connectors") or []
        routes = session.get("routes") or []
        if step.get("rin-id") == "RIN-C4-06" and len(connectors) != 4:
            problems.append("RIN-C4-06: four declared connectors are required")
        if len(routes) != 9:
            problems.append(f"{step.get('rin-id')}: nine route receipts are required")
    return problems


def _item_problems(item: dict, label: str, verify: bool = True) -> list[str]:
    problems = []
    for key in ("item", "method", "found", "conclusion", "blocking-scope", "evidence-ref"):
        if not str(item.get(key) or "").strip():
            problems.append(f"{label}: missing {key}")
    if item.get("conclusion") not in GOOD_CONCLUSIONS:
        problems.append(f"{label}: conclusion must be an explicit non-blocking result")
    if str(item.get("blocking-scope") or "").lower() not in ("", "none", "无"):
        problems.append(f"{label}: blocking-scope must be empty when readiness passes")
    if item.get("rdy-id") == "RDY-C4-04" and "阻塞" in str(item.get("conclusion") or ""):
        problems.append(f"{label}: local license blocker cannot be readiness=通过")
    if verify and item.get("evidence-ref"):
        problems += c4_check_ref(item.get("evidence-ref"), f"{label}.evidence-ref")
    return problems


def closeout_problems(closeout: dict, verify: bool = True) -> list[str]:
    problems: list[str] = []
    closeout_block = closeout.get("closeout") or {}
    reinstall = closeout_block.get("reinstall") or {}
    readiness = closeout_block.get("readiness") or {}
    steps = reinstall.get("steps") or []
    items = readiness.get("items") or []
    package_hash = ((closeout.get("package") or {}).get("content-sha256")) or ""
    if reinstall.get("status") == "通过":
        if [step.get("rin-id") for step in steps] != list(RIN_IDS):
            problems.append("reinstall.steps must be RIN-C4-01..08 in order")
        for step in steps:
            problems += _step_problems(step, f"reinstall.{step.get('rin-id')}", package_hash, verify)
        if not reinstall.get("evidence-ref"):
            problems.append("reinstall.evidence-ref is required when status=通过")
    if readiness.get("status") == "通过":
        if [item.get("rdy-id") for item in items] != list(RDY_IDS):
            problems.append("readiness.items must be RDY-C4-01..07 in order")
        for item in items:
            problems += _item_problems(item, f"readiness.{item.get('rdy-id')}", verify)
        if not readiness.get("evidence-ref"):
            problems.append("readiness.evidence-ref is required when status=通过")
    count = closeout.get("count") or {}
    allowed = bool(count.get("passed") == 9 and reinstall.get("status") == "通过" and readiness.get("status") == "通过")
    if closeout_block.get("final-wording-allowed") != allowed:
        problems.append("final-wording-allowed must equal passed==9 AND reinstall/readiness 通过")
    expected = "phase-1 本机自用 9/9 完成" if allowed else ""
    if closeout_block.get("final-wording") != expected:
        problems.append("final-wording does not match the approved wording rule")
    return problems


class ContractSelfChecks(unittest.TestCase):
    def _passing(self) -> dict:
        steps = [{
            "rin-id": rin, "stage": "s", "actual-step": "a", "client-version": "c",
            "validator-version": "v", "package-version": "0.11.0",
            "package-content-sha256": "a" * 64, "result": "通过",
            "evidence-ref": "out/evidence/cr4/r.json::" + "b" * 64,
        } for rin in RIN_IDS]
        steps[0]["export-runs"] = [
            {"digest-set-sha256": "c" * 64, "files": [{"path": "out/evidence/cr4/e.docx", "sha256": "c" * 64}]},
            {"digest-set-sha256": "c" * 64, "files": [{"path": "out/evidence/cr4/e.docx", "sha256": "c" * 64}]},
        ]
        steps[1]["exit-code"] = 0
        steps[2]["exit-code"] = 0
        steps[2]["terminal-state"] = "registered"
        steps[3]["recovery-point"] = "out/evidence/cr4/backup::" + "d" * 64
        steps[4]["installed-version"] = "0.11.0"
        steps[5]["new-session"] = {"connectors": ["a", "b", "c", "d"], "routes": [f"/r{i}" for i in range(9)]}
        steps[6]["new-session"] = {"connectors": ["a", "b", "c", "d"], "routes": [f"/r{i}" for i in range(9)]}
        items = [{
            "rdy-id": rdy, "item": "i", "method": "m", "found": "ok", "conclusion": "通过",
            "blocking-scope": "none", "evidence-ref": "out/evidence/cr4/d.json::" + "e" * 64,
        } for rdy in RDY_IDS]
        closeout = {
            "package": {"content-sha256": "a" * 64},
            "count": {"passed": 9, "total": 9},
            "closeout": {
                "reinstall": {"status": "通过", "evidence-ref": "x", "steps": steps},
                "readiness": {"status": "通过", "evidence-ref": "y", "items": items},
                "final-wording-allowed": True,
                "final-wording": "phase-1 本机自用 9/9 完成",
            },
        }
        return closeout

    def test_closeout_gate(self) -> None:
        block = self._passing()
        self.assertEqual(closeout_problems(block, verify=False), [])
        broken = {**block, "closeout": {**block["closeout"], "reinstall": {**block["closeout"]["reinstall"], "steps": block["closeout"]["reinstall"]["steps"][:-1]}}}
        self.assertTrue(closeout_problems(broken, verify=False))
        failed = {**block, "closeout": {**block["closeout"], "reinstall": {**block["closeout"]["reinstall"], "steps": [{**block["closeout"]["reinstall"]["steps"][0], "result": "失败"}]}}}
        self.assertTrue(closeout_problems(failed, verify=False))

    def test_intermediate_nine_pass_without_reinstall(self) -> None:
        block = self._passing()
        block["closeout"]["reinstall"]["status"] = "待测"
        block["closeout"]["final-wording-allowed"] = False
        block["closeout"]["final-wording"] = ""
        self.assertEqual(closeout_problems(block, verify=False), [])
        block["closeout"]["final-wording"] = "phase-1 本机自用 9/9 完成"
        self.assertTrue(closeout_problems(block, verify=False))


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
