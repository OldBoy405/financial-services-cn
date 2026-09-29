"""cmd-04 — single editable skill source, WB-CUSTOM traceability and sync regression.

The vertical plugin stays the only editable source: every localized text file carries
a WB-CUSTOM block, root CUSTOM.md traces each change back to the verified upstream
baseline, the synced named-agent copies are byte-identical to the source, the
repository's own static check passes, and the CR diff stays inside the approved scope.
"""
from __future__ import annotations

import filecmp
import re
import subprocess
import sys

from _support import (
    AGENT_PLUGINS,
    CMD_SRC,
    COMMAND_FILE,
    CUSTOM,
    EXPECTED_BUNDLE_CHANGES,
    NINE_PAIRS,
    README,
    ROOT,
    SCOPE_ALLOWED_FILES,
    SCOPE_ALLOWED_PREFIXES,
    SCOPE_VERSION_BUMP_FILES,
    SKILL_SRC,
    RepoTest,
    crctl_git,
    crctl_git_lines,
    parse_yaml_subset,
    read_block,
)

CHANGED_SKILLS = ("earnings-analysis", "earnings-preview", "model-update", "morning-note",
                  "idea-generation", "sector-overview")
COLUMNS = ("记录", "上游来源（ref@SHA:路径）", "原路径 → 本地路径",
           "原语义 → 中文等价及保留约束", "同步副本", "上游增量/冲突处理")


def localized_files() -> list:
    files = [(SKILL_SRC / skill / "SKILL.md", f"WB-CUSTOM-{index:02d}")
             for index, (_, skill) in enumerate(NINE_PAIRS, start=1)]
    files += [(CMD_SRC / COMMAND_FILE[command], f"WB-CUSTOM-{index:02d}")
              for index, (command, _) in enumerate(NINE_PAIRS, start=10)]
    return files


class Localization(RepoTest):
    def test_every_localized_file_is_marked(self) -> None:
        for path, record in localized_files():
            self.assert_file(path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("WB-CUSTOM", text, f"{path.name}: missing WB-CUSTOM marker")
            self.assertIn(record, text, f"{path.name}: missing localization record {record}")
            for field in ("输入契约", "数据域", "保留的旧约束", "中文等价口径", "明确缺口"):
                self.assertIn(field, text, f"{path.name}: WB-CUSTOM block missing '{field}'")

    def test_custom_ledger_traces_every_record(self) -> None:
        self.assert_file(CUSTOM)
        text = CUSTOM.read_text(encoding="utf-8")
        self.assertIn("WB-CUSTOM", text)
        self.assertIn("上游基线", text)
        self.assertIn("本地化增量合并规则", text)
        for column in COLUMNS:
            self.assertIn(column, text, f"CUSTOM.md change list is missing column {column!r}")
        baseline = parse_yaml_subset(read_block(README, "baseline-evidence"))
        for anchor in (baseline["source-head-sha"], baseline["baseline-tag"],
                       baseline["baseline-tag-commit-sha"]):
            self.assertIn(anchor, text, f"CUSTOM.md upstream baseline is missing {anchor}")

        rows = [ln for ln in text.splitlines() if ln.startswith("| WB-CUSTOM-")]
        self.assertEqual(len(rows), 18, "CUSTOM.md must carry one row per localized file")
        numbers = []
        for line in rows:
            cells = [c.strip() for c in line.strip("|").split("|")]
            numbers.append(int(cells[0].removeprefix("WB-CUSTOM-")))
            record = cells[0]
            upstream = re.search(r"@([0-9a-f]{7,40}):(\S+)", cells[1])
            self.assertIsNotNone(upstream, f"{record}: upstream source must use ref@SHA:path form")
            self.assertTrue(baseline["source-head-sha"].startswith(upstream.group(1)),
                            f"{record}: upstream SHA must be the verified baseline HEAD")
            target = ROOT / upstream.group(2).replace("`", "")
            self.assertTrue(target.is_file(), f"{record}: upstream/local path does not exist: {upstream.group(2)}")
            self.assertIn("→", cells[2], f"{record}: old -> new path mapping is missing")
            self.assertTrue(cells[3].strip(), f"{record}: CN equivalence / kept constraints are empty")
            self.assertTrue(cells[5].strip(), f"{record}: upstream merge rule is empty")
        self.assertEqual(numbers, list(range(1, 19)), "records must be consecutive WB-CUSTOM-01..18")

    def test_source_paths_match_the_recorded_rows(self) -> None:
        text = CUSTOM.read_text(encoding="utf-8")
        recorded = set()
        for line in text.splitlines():
            if line.startswith("| WB-CUSTOM-"):
                upstream = re.search(r"@([0-9a-f]{7,40}):(\S+)", line)
                if upstream:
                    recorded.add(upstream.group(2).replace("`", ""))
        expected = {p.relative_to(ROOT).as_posix() for p, _ in localized_files()}
        self.assertEqual(recorded, expected, "CUSTOM.md rows and WB-CUSTOM markers must cover the same files")

    def test_synced_copies_match_the_vertical_source(self) -> None:
        compared = 0
        for skill in CHANGED_SKILLS:
            source = SKILL_SRC / skill
            for plugin in sorted(p for p in AGENT_PLUGINS.iterdir() if p.is_dir()):
                bundled = plugin / "skills" / skill
                if not bundled.is_dir():
                    continue
                comparison = filecmp.dircmp(source, bundled)
                self.assertEqual(comparison.left_only, [], f"{bundled}: extra files in vertical source")
                self.assertEqual(comparison.right_only, [], f"{bundled}: stale files in bundled copy")
                self.assertEqual(comparison.diff_files, [], f"{bundled}: drifted from its vertical source")
                self.assertEqual(comparison.funny_files, [])
                compared += 1
        self.assertGreaterEqual(compared, 7, "expected at least the seven affected named-agent copies")

    def test_repository_static_check_passes(self) -> None:
        proc = subprocess.run([sys.executable, "scripts/check.py"], cwd=str(ROOT),
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0, f"scripts/check.py failed:\n{proc.stdout}\n{proc.stderr}")

    def test_diff_stays_inside_the_approved_scope(self) -> None:
        changed = crctl_git_lines("diff", "--name-only", "origin/workbuddy/main")
        self.assertTrue(changed, "no diff against workbuddy/main: nothing to review")
        for path in changed:
            allowed = (path in SCOPE_ALLOWED_FILES
                       or path in SCOPE_VERSION_BUMP_FILES
                       or path.startswith(SCOPE_ALLOWED_PREFIXES))
            self.assertTrue(allowed, f"{path} is outside the approved scope_in (scope creep)")
        bundles = sorted(p for p in changed if p.startswith("plugins/agent-plugins/"))
        self.assertEqual(bundles, sorted(EXPECTED_BUNDLE_CHANGES),
                         "only CR-caused named-agent copies may change (no unrelated upstream drift)")

    def test_other_verticals_untouched(self) -> None:
        changed = crctl_git_lines("diff", "--name-only", "origin/workbuddy/main")
        for path in changed:
            if path.startswith("plugins/vertical-plugins/"):
                self.assertTrue(path.startswith("plugins/vertical-plugins/equity-research/"),
                                f"other industry source changed: {path}")


if __name__ == "__main__":
    import unittest

    unittest.main()
