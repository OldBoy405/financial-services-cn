"""cmd-03 — fixed sample: the four conditions, the legal-usage right and the layering.

This module must FAIL while the sample is still `待确认`: AC-03 explicitly forbids
declaring the CR passed (or handing the sample to a follow-up CR) before a real,
rights-cleared filing exists. The legal/rights verdict stays a human (Ray) call;
this module only checks that the evidence and the verdict are present and
internally consistent.
"""
from __future__ import annotations

import hashlib
import re

from _support import (
    ACCEPTANCE,
    README,
    ROOT,
    SLOT_STATES,
    VERIFIED_STATES,
    RepoTest,
    parse_yaml_subset,
    read_block,
)

CONDITIONS = (
    "latest-complete-disclosure",
    "research-coverage-sufficient",
    "wind-queryable",
    "legal-usage-right",
)
REQUIRED_FIELDS = (
    "sample-id", "status", "securities-code", "exchange", "disclosure-date", "verified-at",
    "source-and-version", "selection-rationale", "original-relative-path", "original-files",
    "conditions", "adjudicator",
)


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SampleIndex(RepoTest):
    def setUp(self) -> None:
        self.index = parse_yaml_subset(read_block(README, "sample-index"))

    def test_index_shape(self) -> None:
        for field in REQUIRED_FIELDS:
            self.assertIn(field, self.index, f"sample index missing field {field}")
        for condition in CONDITIONS:
            self.assertIn(condition, self.index["conditions"], f"sample index missing condition {condition}")

    def test_sample_conditions_are_verified(self) -> None:
        pending = {
            name: state for name, state in self.index["conditions"].items() if state not in VERIFIED_STATES
        }
        self.assertEqual(
            pending, {},
            "AC-03 not satisfied: the fixed sample's four conditions are still unverified "
            f"{pending}; Ray must provide the filing original plus the per-condition evidence "
            "(latest complete disclosure / sufficient research coverage / Wind-queryable / legal usage right)",
        )
        self.assertIn(self.index["status"], VERIFIED_STATES,
                      f"sample index status is {self.index['status']!r}, not a verified state")

    def test_sample_identity_recorded(self) -> None:
        for field in ("securities-code", "exchange", "disclosure-date", "verified-at", "adjudicator"):
            self.assertTrue(str(self.index[field]).strip(),
                            f"verified sample must record {field} (codes/exchange/date/adjudicator)")
        self.assertRegex(str(self.index["securities-code"]), r"\d{6}")
        self.assertIn(str(self.index["exchange"]).upper(), ("SH", "SZ", "BJ", "HK"))

    def test_originals_live_in_the_ignored_area(self) -> None:
        rel = str(self.index["original-relative-path"]).replace("\\", "/")
        self.assertTrue(rel.startswith("out/"), "sample originals may only live under the ignored out/ area")
        self.assertTrue(rel.startswith("out/samples/"), "sample originals must sit in the out/samples/ area")
        originals = list(self.index["original-files"]) if isinstance(self.index["original-files"], list) else []
        self.assertTrue(originals, "no sample original files registered (原件缺失不得判通过)")
        for entry in originals:
            self.assertIn("::", entry, f"original entry must be '<relative-path>::<sha256>': {entry!r}")
            path_part, _, recorded = entry.partition("::")
            path = (ROOT / path_part).resolve()
            self.assertTrue(path.is_file(), f"registered sample original missing: {path_part}")
            self.assertEqual(sha256_file(path), recorded.strip(), f"sample original hash mismatch: {path_part}")

    def test_original_is_not_versioned(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertRegex(ignore, r"(?m)^\s*/?out/?\s*$", "out/ must stay git-ignored")
        pkg = ROOT / "workbuddy-experts" / "equity-research"
        for path in pkg.rglob("*"):
            self.assertNotIn("SAMPLE-01", path.name, "sample originals must not be copied into the package source")

    def test_acceptance_layers_and_nine_slots(self) -> None:
        text = ACCEPTANCE.read_text(encoding="utf-8")
        slots = [parse_yaml_subset(b) for b in re.findall(r"```yaml\n(slot: SLOT-\d\d\n.*?)```", text, re.DOTALL)]
        self.assertEqual(len(slots), 9, "ACCEPTANCE must carry nine independent record slots")
        self.assertEqual(len({s["slot"] for s in slots}), 9, "acceptance slots must be unique")
        for slot in slots:
            self.assertIn(slot["state"], SLOT_STATES, f"{slot['slot']} has illegal route state")
            self.assertEqual(slot["research-state"], "待测",
                             f"{slot['slot']} research state must stay 待测 in this CR (routing never promotes it)")
            self.assertTrue(str(slot["route-prompt-cn"]).strip(), f"{slot['slot']} missing CN prompt")
            self.assertTrue(str(slot["route-prompt-en"]).strip(), f"{slot['slot']} missing EN prompt")
        for layer in ("基线", "样例", "包校验", "路由", "研究质量"):
            self.assertIn(layer, text, f"ACCEPTANCE is missing the {layer} layer")
        self.assertNotIn("| 研究质量（九项内容/产物） | 通过 |", text,
                         "research quality must not be marked passed in this CR")
        research_row = next(
            (ln for ln in text.splitlines() if ln.startswith("| 研究质量（九项内容/产物）")), None
        )
        self.assertIsNotNone(research_row, "ACCEPTANCE is missing the research-quality layer row")
        self.assertIn("待测", research_row, "research quality must stay 待测 in this CR")


if __name__ == "__main__":
    import unittest

    unittest.main()
