"""cmd-01 — baseline, tag, trunk and the 16-expert structure.

Checks the recorded baseline against the repository's real refs through the
controlled shell (`crctl git rev-parse --verify` is read-only; tag creation is
another, authorised channel and never happens here).
"""
from __future__ import annotations

import json
import re

from _support import (
    AGENT_PLUGINS,
    CMD_SRC,
    COMMAND_FILE,
    NINE_PAIRS,
    README,
    ROOT,
    SKILL_SRC,
    RepoTest,
    crctl_git,
    parse_yaml_subset,
    read_block,
)

SHA40 = re.compile(r"^[0-9a-f]{40}$")
VERTICALS = (
    "equity-research", "financial-analysis", "fund-admin",
    "investment-banking", "operations", "private-equity",
)
NAMED_AGENTS = (
    "earnings-reviewer", "gl-reconciler", "kyc-screener", "market-researcher",
    "meeting-prep-agent", "model-builder", "month-end-closer", "pitch-agent",
    "statement-auditor", "valuation-reviewer",
)


class BaselineEvidence(RepoTest):
    def setUp(self) -> None:
        self.evidence = parse_yaml_subset(read_block(README, "baseline-evidence"))

    def test_required_fields_recorded(self) -> None:
        for key in (
            "upstream-repo", "source-head-sha", "baseline-tag", "baseline-tag-object-sha",
            "baseline-tag-commit-sha", "target-trunk", "target-trunk-sha",
            "trunk-merge-base-sha", "cr-branch", "collected-at", "collected-by", "structure",
        ):
            self.assertIn(key, self.evidence, f"baseline evidence missing {key}")
            self.assertTrue(str(self.evidence[key]).strip(), f"baseline evidence {key} is empty")
        self.assertRegex(self.evidence["source-head-sha"], SHA40)
        self.assertEqual(self.evidence["baseline-tag-commit-sha"], self.evidence["source-head-sha"])

    def test_tag_points_at_recorded_source_head(self) -> None:
        tag = self.evidence["baseline-tag"]
        self.assertTrue(tag.startswith("baseline/"), "recorded tag must be a real baseline tag, not a suggestion")
        tag_object = crctl_git("rev-parse", "--verify", f"refs/tags/{tag}")
        self.assertEqual(tag_object, self.evidence["baseline-tag-object-sha"])
        peeled = crctl_git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
        self.assertEqual(peeled, self.evidence["source-head-sha"],
                         "baseline tag must resolve to the recorded 40-char source HEAD")

    def test_trunk_and_branch(self) -> None:
        trunk = self.evidence["target-trunk"]
        self.assertEqual(crctl_git("rev-parse", f"origin/{trunk}"), self.evidence["target-trunk-sha"])
        self.assertEqual(crctl_git("branch", "--show-current"), self.evidence["cr-branch"])

    def test_structure_counts_match_repository(self) -> None:
        structure = self.evidence["structure"]
        verticals = sorted(p.name for p in (ROOT / "plugins" / "vertical-plugins").iterdir() if p.is_dir())
        agents = sorted(p.name for p in AGENT_PLUGINS.iterdir() if p.is_dir())
        self.assertEqual(len(verticals), int(structure["vertical-plugins"]))
        self.assertEqual(verticals, sorted(VERTICALS))
        self.assertEqual(len(agents), int(structure["agent-plugins"]))
        self.assertEqual(agents, sorted(NAMED_AGENTS))
        commands = sorted(p.name for p in CMD_SRC.glob("*.md"))
        skills = sorted(p.name for p in SKILL_SRC.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
        self.assertEqual(len(commands), int(structure["equity-research-commands"]))
        self.assertEqual(len(skills), int(structure["equity-research-skills"]))
        marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        entries = marketplace["plugins"]
        sources = [e["source"] for e in entries]
        self.assertEqual(sum(1 for s in sources if "/vertical-plugins/" in s), 6)
        self.assertEqual(sum(1 for s in sources if "/agent-plugins/" in s), 10)
        # 16 experts (6 vertical + 10 named agents) plus the 3 non-expert entries kept verbatim
        self.assertEqual(sorted(s for s in sources if "/vertical-plugins/" in s),
                         sorted(f"./plugins/vertical-plugins/{v}" for v in VERTICALS))
        self.assertEqual(sorted(s for s in sources if "/agent-plugins/" in s),
                         sorted(f"./plugins/agent-plugins/{a}" for a in NAMED_AGENTS))
        self.assertEqual(sum(1 for s in sources if "/partner-built/" in s), 2)
        self.assertEqual(len(sources), 19, "marketplace inventory changed: 16 experts + 2 partner-built + 1 install tooling")

    def test_nine_command_skill_pairs_exist(self) -> None:
        for command, skill in NINE_PAIRS:
            self.assert_file(CMD_SRC / COMMAND_FILE[command])
            self.assert_file(SKILL_SRC / skill / "SKILL.md")

    def test_connector_and_mcp_inventory_recorded(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("connectors/", text)
        self.assertIn(".mcp.json", text)
        self.assertFalse((SKILL_SRC.parent / "connectors").exists(),
                         "README claims there is no connectors/ dir; repository must match")
        self.assertFalse((SKILL_SRC.parent / ".mcp.json").exists(),
                         "README claims there is no .mcp.json; repository must match")


if __name__ == "__main__":
    import unittest

    unittest.main()
