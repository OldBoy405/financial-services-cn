"""cmd-05 — single-Agent routing: nine skills, CN/EN cases, guards, quickPrompts.

The static half verifies the Agent contract and the nine acceptance slots. The
dynamic half consumes **actual target-client interaction records** (raw input,
raw response, client version, per-record evidence hash). A missing or static-only
record set must fail: "nine entries exist" or a `--list` dump is never routing
evidence (TASK-03 5 / plan.md cmd-05 observation surface).
"""
from __future__ import annotations

import hashlib
import json
import re

from _support import (
    ACCEPTANCE,
    AGENT,
    CLIENT_EVIDENCE,
    NINE_PAIRS,
    ROOT,
    SLOT_STATES,
    RepoTest,
    parse_yaml_subset,
)

REQUIRED_SESSION_FIELDS = ("client-version", "case-id", "prompt", "response", "evidence-file", "sha256")


class Routing(RepoTest):
    def setUp(self) -> None:
        self.agent = AGENT.read_text(encoding="utf-8")
        self.slots = [parse_yaml_subset(b)
                      for b in re.findall(r"```yaml\n(slot: SLOT-\d\d\n.*?)```",
                                          ACCEPTANCE.read_text(encoding="utf-8"), re.DOTALL)]

    def test_decision_signature_is_declared(self) -> None:
        for token in ("Clarify(", "Stop(", "Route("):
            self.assertTrue(token in self.agent, f"Agent contract missing {token}")
        self.assertTrue("唯一 skill" in self.agent, "Agent must route to exactly one skill")
        self.assertTrue("不调用任何技能" in self.agent, "Clarify/Stop must not invoke a skill")
        self.assertTrue("不代表研究通过" in self.agent, "Route must state it is not a research verdict")

    def test_nine_unique_routes_declared(self) -> None:
        table = self.agent.split("## 九项路由（恰九项）", 1)[1].split("## 数据域路由", 1)[0]
        rows = [ln for ln in table.splitlines() if ln.strip().startswith("|")][2:]
        self.assertEqual(len(rows), 9, "the Agent must declare exactly nine routes")
        declared = []
        for line in rows:
            cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
            declared.append((cells[0], cells[1]))
        self.assertEqual(declared, NINE_PAIRS, "Agent routing must match PRD FR-02 one-to-one")
        self.assertEqual(len({skill for _, skill in declared}), 9, "routes must be unique per intent")

    def test_guards_are_declared(self) -> None:
        for guard in ("securities-code", "exchange", "period", "data-stale", "no-authorization",
                      "missing-prerequisite-model"):
            self.assertTrue(guard in self.agent, f"Agent is missing guard {guard}")
        self.assertTrue("Task 1～5" in self.agent, "/initiate five-gate rule missing")
        self.assertTrue("Task 2" in self.agent, "/initiate Task 2 -> Task 3 prerequisite missing")
        self.assertRegex(self.agent, r"不(得|能|可)自动连跑", "the Task 2 -> Task 3 guard must forbid auto chaining")

    def test_acceptance_slots_are_ready(self) -> None:
        self.assertEqual(len(self.slots), 9)
        for index, slot in enumerate(self.slots, start=1):
            self.assertEqual(slot["slot"], f"SLOT-{index:02d}")
            self.assertEqual(slot["skill"], NINE_PAIRS[index - 1][1])
            self.assertIn(slot["state"], SLOT_STATES)
            self.assertEqual(slot["research-state"], "待测")
            self.assertTrue(str(slot["route-prompt-cn"]).strip())
            self.assertTrue(str(slot["route-prompt-en"]).strip())

    def test_target_client_evidence_exists(self) -> None:
        self.assertTrue(
            CLIENT_EVIDENCE.is_file(),
            "no target-client routing evidence: AC-05 requires 18 CN/EN cases plus the three "
            "quickPrompts captured from the recorded WorkBuddy client session. Static Agent text, "
            "a skill directory listing or `--list` output cannot substitute. "
            f"Expected an index at {CLIENT_EVIDENCE.relative_to(ROOT).as_posix()} produced by the "
            "host step (G4) once the client session is available",
        )
        index = json.loads(CLIENT_EVIDENCE.read_text(encoding="utf-8"))
        self.assertIn("client-version", index, "client version must be recorded")
        self.assertIn("sessions", index)
        sessions = index["sessions"]
        self.assertGreaterEqual(len(sessions), 18, "AC-05 needs nine CN + nine EN positive cases")
        seen_pairs = set()
        for session in sessions:
            for field in REQUIRED_SESSION_FIELDS:
                self.assertIn(field, session, f"session record missing {field}: {session.get('case-id')}")
            self.assertTrue(str(session["client-version"]).strip())
            self.assertIn("SKILL_SELECTION", json.dumps(session, ensure_ascii=False))
            evidence = ROOT / session["evidence-file"]
            self.assertTrue(evidence.is_file(), f"raw client output missing: {session['evidence-file']}")
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            self.assertEqual(digest, session["sha256"], f"raw output hash mismatch: {session['evidence-file']}")
            seen_pairs.add(session["case-id"])
        self.assertGreaterEqual(len(seen_pairs), 18, "case ids must be unique per captured case")
        for marker in ("quickPrompt", "Clarify", "Stop"):
            self.assertIn(marker, json.dumps(index, ensure_ascii=False),
                          f"index must record {marker} observations")


if __name__ == "__main__":
    import unittest

    unittest.main()
