"""cmd-02 — the nine equivalence mappings and the preserved legacy constraints.

Compares README's nine MappingRows against the *real* source commands/skills, so a
file-name-only listing cannot pass: each row must carry every SDD field, and the
legacy constraints of /earnings and /initiate must still be traceable in the
source text while the README records the CN/A-H equivalence and the gaps.
"""
from __future__ import annotations

import re

from _support import (
    AH_MECHANISMS,
    BASELINE_ANCHORS,
    CMD_SRC,
    COMMAND_FILE,
    GAP_ANCHORS,
    MAPPING_REQUIRED_FIELDS,
    MAPPING_STATES,
    NINE_PAIRS,
    README,
    SKILL_SRC,
    SOURCE_ANCHORS,
    RepoTest,
)


class MappingRows(RepoTest):
    def setUp(self) -> None:
        self.rows = self.mapping_rows()
        self.readme = README.read_text(encoding="utf-8")

    def test_exactly_nine_rows_in_fr02_order(self) -> None:
        self.assertEqual(len(self.rows), 9, "README must carry exactly nine MappingRow blocks")
        listed = [(row["command"], row["skill"]) for row in self.rows]
        self.assertEqual(listed, NINE_PAIRS, "row order and pairing must match PRD FR-02")

    def test_every_row_carries_all_sdd_fields(self) -> None:
        for row in self.rows:
            for field in MAPPING_REQUIRED_FIELDS:
                self.assertIn(field, row, f"{row.get('row')} missing field {field}")
                value = row[field]
                self.assertTrue(value not in ("", [], {}), f"{row.get('row')} has empty {field}")
            self.assertIn(row["status"], MAPPING_STATES, f"{row.get('row')} has unknown status")

    def test_rows_reference_real_sources(self) -> None:
        for row in self.rows:
            for source in row["source-files"]:
                path = (SKILL_SRC.parents[3] / source).resolve()
                self.assertTrue(path.is_file(), f"{row['row']} references missing source {source}")
            self.assert_file(CMD_SRC / COMMAND_FILE[row["command"]])
            self.assert_file(SKILL_SRC / row["skill"] / "SKILL.md")

    def test_fixed_table_matches_row_blocks(self) -> None:
        table = self.readme.split("固定九行")[1].split("### 2.1")[0]
        data_rows = [ln for ln in table.splitlines() if ln.strip().startswith("|")][2:]
        self.assertEqual(len(data_rows), 9, "the fixed nine-row table must have nine data rows")
        for index, (command, skill) in enumerate(NINE_PAIRS, start=1):
            cells = [c.strip().strip("`") for c in data_rows[index - 1].strip("|").split("|")]
            self.assertEqual(cells[0], str(index))
            self.assertEqual(cells[1], command)
            self.assertEqual(cells[2], skill)
            self.assertIn(cells[3], MAPPING_STATES)

    def test_earnings_legacy_constraints_kept_and_sourced(self) -> None:
        row = next(r for r in self.rows if r["command"] == "/earnings")
        kept = " ".join(row["kept-behavior"]) if isinstance(row["kept-behavior"], list) else row["kept-behavior"]
        for anchor in BASELINE_ANCHORS:
            self.assertIn(anchor, kept, f"/earnings kept-behavior lost legacy anchor {anchor!r}")
        for source_name, anchors in SOURCE_ANCHORS.items():
            text = (SKILL_SRC.parents[3] / "plugins" / "vertical-plugins" / "equity-research" / source_name).read_text(
                encoding="utf-8"
            )
            for anchor in anchors:
                self.assertIn(anchor, text, f"{source_name} no longer contains {anchor!r} (silent deletion?)")
        self.assertIn("CNY", row["cn-equivalence"])
        self.assertIn("CNY", self.readme)

    def test_initiate_five_gates_and_ah_mechanisms(self) -> None:
        row = next(r for r in self.rows if r["command"] == "/initiate")
        kept = " ".join(row["kept-behavior"]) if isinstance(row["kept-behavior"], list) else row["kept-behavior"]
        self.assertRegex(kept, r"Task 1[～~-]5", "/initiate must state the five separately-requested tasks")
        self.assertIn("五次独立人工关口", kept)
        self.assertIn("Task 2", kept, "/initiate must state the Task 2 -> Task 3 prerequisite")
        mechanism = " ".join(row["ah-mechanism"]) if isinstance(row["ah-mechanism"], list) else row["ah-mechanism"]
        for anchor in AH_MECHANISMS:
            self.assertIn(anchor, mechanism, f"/initiate A/H mechanism inventory missing {anchor}")
        source = (SKILL_SRC / "initiating-coverage" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("One Task at a Time", source)
        self.assertIn("Task 2", source)

    def test_no_equivalent_gaps_declared(self) -> None:
        text = " ".join(
            " ".join(row["gaps"]) if isinstance(row["gaps"], list) else row["gaps"] for row in self.rows
        )
        for anchor in GAP_ANCHORS:
            self.assertIn(anchor, text, f"no-equivalent gap {anchor!r} is not declared")
        self.assertIn("缺口", text)

    def test_every_row_declares_acceptance_method(self) -> None:
        for row in self.rows:
            method = row["acceptance-method"]
            self.assertRegex(method, r"cmd-0[256]", f"{row['row']} has no evidence command")


if __name__ == "__main__":
    import unittest

    unittest.main()
