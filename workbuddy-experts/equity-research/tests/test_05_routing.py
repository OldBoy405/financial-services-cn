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
    MANIFEST,
    NINE_PAIRS,
    ROOT,
    SLOT_STATES,
    RepoTest,
    parse_yaml_subset,
)

REQUIRED_SESSION_FIELDS = ("client-version", "case-id", "prompt", "response", "evidence-file", "sha256")
# A decision record must open with one of the three SDD §3.2 outcomes, and a Route
# must name the one skill it selected (CN and EN wordings of the same contract).
DECISION_RE = re.compile(r"^(Clarify|Stop|Route)\(")
ROUTE_RE = re.compile(r"Route\((?:唯一|unique) skill: ([A-Za-z0-9._-]+)\)")
SLOT_LANGUAGES = (("cn", "zh-CN"), ("en", "en-US"))


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

    def test_slot_cases_are_one_to_one_with_the_nine_skills(self) -> None:
        """Each SLOT's captured CN/EN case must be the raw prompt, routed to its one skill.

        A matching session count or the bare presence of a `SKILL_SELECTION` string is
        not routing evidence: the recorded response itself must be the unique Route for
        that slot's skill (AC-05).
        """
        index = json.loads(CLIENT_EVIDENCE.read_text(encoding="utf-8"))
        by_case = {session["case-id"]: session for session in index["sessions"]}
        routed: list[str] = []
        for position, (_, skill) in enumerate(NINE_PAIRS, start=1):
            slot = self.slots[position - 1]
            slot_no = f"SLOT-{position:02d}"
            for lang, language in SLOT_LANGUAGES:
                case_id = f"slot-{position:02d}-{lang}"
                record = by_case.get(case_id)
                self.assertIsNotNone(record, f"no captured case {case_id} for {slot_no}/{skill}")
                self.assertEqual(record["acceptance-slot"], slot_no, f"{case_id}: bound to the wrong slot")
                self.assertEqual(record["language"], language, f"{case_id}: wrong language tag")
                self.assertEqual(record["SKILL_SELECTION"], skill, f"{case_id}: captured the wrong skill")
                self.assertEqual(record["prompt"], slot[f"route-prompt-{lang}"],
                                 f"{case_id}: raw input is not the {slot_no} authority prompt")
                response = record["response"].strip()
                decision = DECISION_RE.match(response)
                self.assertIsNotNone(decision, f"{case_id}: response is not a Clarify/Stop/Route decision")
                self.assertEqual(decision.group(1), "Route", f"{case_id}: a positive case must route")
                chosen = ROUTE_RE.findall(response)
                self.assertEqual(chosen, [skill],
                                 f"{case_id}: response must select exactly the unique Route {skill}")
                routed.append(chosen[0])
        self.assertEqual(len(set(routed)), 9, "the nine skills must be covered, one slot-pair each")

    def test_quickprompts_match_the_declared_entries_and_skills(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        index = json.loads(CLIENT_EVIDENCE.read_text(encoding="utf-8"))
        records = {record["case-id"]: record for record in index["quickprompts"]}
        self.assertEqual(sorted(records), ["qp-01", "qp-02", "qp-03"],
                         "the three quickPrompt entries must each be captured once")
        for position, (_, skill) in enumerate(NINE_PAIRS[:3]):
            case_id = f"qp-{position + 1:02d}"
            record = records[case_id]
            self.assertEqual(record["prompt"], manifest["quickPrompts"][position]["zh"],
                             f"{case_id}: prompt must be the manifest quickPrompt verbatim")
            self.assertIn(skill, f"{record.get('observation', '')} {record['response']}",
                          f"{case_id}: the entry must be observed on the {skill} path")
            decision = DECISION_RE.match(record["response"].strip())
            self.assertIsNotNone(decision, f"{case_id}: response is not a Clarify/Stop/Route decision")
            if decision.group(1) != "Route":
                self.assertRegex(record["response"], r"不调用任何技能|不选中任何技能",
                                 f"{case_id}: {decision.group(1)} must state that no skill was invoked")

    def test_versioned_acceptance_record_carries_the_evidence_index(self) -> None:
        """AC-08: the versioned record — not the ignored out/ dir — must locate evidence by hash.

        The recorded session version, the per-slot positive results and a
        `<path>::<sha256>` index per slot are what make the ignored raw capture
        checkable by a human reviewer.
        """
        for position, (_, skill) in enumerate(NINE_PAIRS, start=1):
            slot = self.slots[position - 1]
            for field in ("date", "source-version", "positive-result", "adjudicator"):
                self.assertTrue(str(slot.get(field, "")).strip(),
                                f"SLOT-{position:02d} must record {field}")
            entries = slot.get("evidence-files")
            self.assertIsInstance(entries, list, f"SLOT-{position:02d} must index its evidence files")
            self.assertEqual(len(entries), 2, f"SLOT-{position:02d} must index its CN and EN case")
            for entry in entries:
                path_part, _, digest = str(entry).partition("::")
                self.assertTrue(digest.strip(),
                                f"SLOT-{position:02d}: evidence entry must be '<path>::<sha256>'")
                evidence = ROOT / path_part
                self.assertTrue(evidence.is_file(), f"SLOT-{position:02d}: recorded evidence missing: {path_part}")
                self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), digest.strip(),
                                 f"SLOT-{position:02d}: recorded evidence hash mismatch: {path_part}")
            recorded = " ".join(str(entry) for entry in entries)
            for case_id in (f"slot-{position:02d}-cn", f"slot-{position:02d}-en"):
                self.assertIn(case_id, recorded, f"SLOT-{position:02d} index must name {case_id}")
            self.assertEqual(slot["skill"], skill)

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
            # The index entry must agree with the raw capture it points at, not just hash it.
            raw = json.loads(evidence.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and "prompt" in raw and "response" in raw:
                self.assertEqual(raw["prompt"], session["prompt"],
                                 f"index/raw prompt drift: {session['case-id']}")
                self.assertEqual(raw["response"], session["response"],
                                 f"index/raw response drift: {session['case-id']}")
            seen_pairs.add(session["case-id"])
        self.assertGreaterEqual(len(seen_pairs), 18, "case ids must be unique per captured case")
        for marker in ("quickPrompt", "Clarify", "Stop"):
            self.assertIn(marker, json.dumps(index, ensure_ascii=False),
                          f"index must record {marker} observations")


if __name__ == "__main__":
    import unittest

    unittest.main()
