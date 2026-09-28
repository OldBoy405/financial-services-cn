"""cmd-06 — seven data-domain priorities, single-source/cross-source rules, safe stop.

Static half: the Agent declares the seven domains in the SDD order with the exact
route chains, one source per metric, cross-source annotation, US-listings-limited-to-
public-surface, and the `westock-data`/`westock-tool` (routing names) vs `westock-mcp`
(manifest id) layering.

Dynamic half: the negative cases (no authorization, stale data, US-only listing, no
equivalent source, ambiguity, missing code, Task 3 without the Task 2 model) must come
from the recorded client session. Static rule text alone must not pass.
"""
from __future__ import annotations

import hashlib
import json
import re

from _support import (
    AGENT,
    CLIENT_EVIDENCE,
    ROOT,
    SEVEN_DOMAINS,
    RepoTest,
)

NEGATIVE_CASES = (
    "no-authorization",
    "stale-data",
    "us-listing-public-only",
    "no-equivalent-source",
    "ambiguous-request",
    "missing-security-code",
    "initiate-task3-without-model",
)


def normalize(cell: str) -> str:
    cell = cell.replace("`", "").replace(" ", "")
    cell = re.split(r"[；;]", cell)[0]
    while cell.startswith("仅") or cell.startswith("只"):
        cell = cell[1:]
    return cell.replace("→", "→")


class DataSafety(RepoTest):
    def setUp(self) -> None:
        self.agent = AGENT.read_text(encoding="utf-8")
        table = self.agent.split("## 数据域路由（声明，不执行真实连接器读取）", 1)[1].split("## 安全与合规", 1)[0]
        rows = [ln for ln in table.splitlines() if ln.strip().startswith("|")]
        self.rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in rows[2:]]

    def test_seven_domains_in_sdd_order_with_exact_chains(self) -> None:
        self.assertEqual(len(self.rows), 7, "the Agent must declare exactly seven data domains")
        self.assertEqual([r[0] for r in self.rows], [str(i) for i in range(1, 8)])
        for (domain_key, chain), row in zip(SEVEN_DOMAINS, self.rows):
            self.assertIn(domain_key, row[1], f"domain row {row[0]} is not {domain_key!r}")
            expected = normalize(chain)
            actual = normalize(row[2])
            self.assertTrue(actual.startswith(expected),
                            f"domain {domain_key!r} chain drifted: {actual!r} !startswith {expected!r}")

    def test_single_source_and_cross_source_rules(self) -> None:
        self.assertTrue("单源" in self.agent, "single-source-per-metric rule missing")
        self.assertTrue("跨源" in self.agent, "cross-source annotation rule missing")
        self.assertTrue("无授权" in self.agent and "过期" in self.agent,
                        "unauthorized/stale data must stop rather than be substituted")
        self.assertTrue("不编造" in self.agent and "不静默替换" in self.agent,
                        "fabrication/silent substitution must be forbidden")

    def test_us_listings_limited_to_public_surface(self) -> None:
        self.assertTrue("美股个股只能走公开面" in self.agent,
                        "US single names must be limited to the public surface")
        self.assertTrue("不伪装机构研究" in self.agent,
                        "the Agent must not pretend to have US institutional data")

    def test_identifier_layering_is_not_conflated(self) -> None:
        self.assertTrue("westock-mcp" in self.agent, "manifest connector id must be declared")
        self.assertTrue("路由域名" in self.agent, "routing-name vs manifest-id layering must be explicit")
        self.assertTrue("不重命名" in self.agent or "不能写成路由同义词" in self.agent,
                        "westock-data/westock-tool must not be renamed into the manifest id")
        for routing_name in ("westock-data", "westock-tool"):
            self.assertTrue(routing_name in self.agent, f"missing routing name {routing_name}")

    def test_refusal_rules_are_not_outsourced(self) -> None:
        self.assertTrue("wb-finance-skill" in self.agent, "the optional guardrail must be named as optional")
        self.assertTrue("不得外包" in self.agent,
                        "domain/permission/recency refusals must be declared by this Agent, not outsourced")

    def test_dynamic_negative_cases_recorded(self) -> None:
        self.assertTrue(
            CLIENT_EVIDENCE.is_file(),
            "no negative-case evidence: AC-06 requires the recorded client session's responses to the "
            "unauthorized / stale / US-listing / no-equivalent-source cases. Static rule text is not a "
            "dynamic negative case. "
            f"Expected an index at {CLIENT_EVIDENCE.relative_to(ROOT).as_posix()} with a 'negatives' list",
        )
        index = json.loads(CLIENT_EVIDENCE.read_text(encoding="utf-8"))
        negatives = {case["case"]: case for case in index.get("negatives", [])}
        missing = [case for case in NEGATIVE_CASES if case not in negatives]
        self.assertEqual(missing, [], f"negative cases without captured client responses: {missing}")
        for case, record in negatives.items():
            for field in ("prompt", "response", "evidence-file", "sha256", "client-version"):
                self.assertIn(field, record, f"negative case {case} missing {field}")
            evidence = ROOT / record["evidence-file"]
            self.assertTrue(evidence.is_file(), f"raw output for {case} missing")
            self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), record["sha256"],
                             f"raw output hash mismatch for {case}")
            self.assertTrue(record["response"].strip(), f"negative case {case} captured no response")


if __name__ == "__main__":
    import unittest

    unittest.main()
