"""Shared helpers for the CR-2026-001 evidence commands (cmd-01 .. cmd-07).

The plan's evidence-command table is the only command entry point; these modules
read the repository's real files and the controlled-shell git adapter, and fail
loudly when a prerequisite is missing. Nothing here writes to the repository.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "workbuddy-experts" / "equity-research"
README = EXP / "README.md"
ACCEPTANCE = EXP / "ACCEPTANCE.md"
AGENT = EXP / "agents" / "equity-research.md"
MANIFEST = EXP / ".codebuddy-plugin" / "plugin.json"
AVATAR = EXP / "avatars" / "expert.png"
CUSTOM = ROOT / "CUSTOM.md"
SKILL_SRC = ROOT / "plugins" / "vertical-plugins" / "equity-research" / "skills"
CMD_SRC = ROOT / "plugins" / "vertical-plugins" / "equity-research" / "commands"
AGENT_PLUGINS = ROOT / "plugins" / "agent-plugins"
EXPORT_SCRIPT = ROOT / "scripts" / "export_workbuddy_experts.py"
OUT_PKG = ROOT / "out" / "workbuddy-experts" / "equity-research"
CLIENT_EVIDENCE = ROOT / "out" / "evidence" / "client-sessions" / "index.json"
HOST_EVIDENCE = ROOT / "out" / "evidence" / "host" / "index.json"

# FR-02 order: nine command -> unique skill pairs.
NINE_PAIRS = [
    ("/earnings", "earnings-analysis"),
    ("/initiate", "initiating-coverage"),
    ("/model-update", "model-update"),
    ("/screen", "idea-generation"),
    ("/catalysts", "catalyst-calendar"),
    ("/morning-note", "morning-note"),
    ("/earnings-preview", "earnings-preview"),
    ("/sector", "sector-overview"),
    ("/thesis", "thesis-tracker"),
]
COMMAND_FILE = {
    "/earnings": "earnings.md",
    "/initiate": "initiate.md",
    "/model-update": "model-update.md",
    "/screen": "screen.md",
    "/catalysts": "catalysts.md",
    "/morning-note": "morning-note.md",
    "/earnings-preview": "earnings-preview.md",
    "/sector": "sector.md",
    "/thesis": "thesis.md",
}

# SDD 3.3 order and route chains (declaration only; no connector call happens here).
SEVEN_DOMAINS = [
    ("机构财务", "wind-finance → neodata → tdx-connector F10"),
    ("一致预期", "tdx-connector yzyq → neodata"),
    ("研报", "neodata"),
    ("行情", "westock-data → neodata"),
    ("筛选", "westock-tool → tdx-connector / wind-finance"),
    ("宏观", "wind-finance → westock-data"),
    ("资金", "neodata → westock-data"),
]

MAPPING_REQUIRED_FIELDS = (
    "row", "command", "skill", "source-files", "ah-mechanism", "ah-data-domains",
    "input-followups", "required-data", "source-date", "kept-behavior",
    "cn-equivalence", "gaps", "status", "acceptance-method",
)
MAPPING_STATES = ("接受", "明确缺口", "待验")
SLOT_STATES = ("待测", "通过", "不通过", "需重测")
VERIFIED_STATES = ("已核实", "通过")

BASELINE_ANCHORS = (
    "8-12", "三个月", "transcript", "beat/miss", "DOCX", "Sources", "八项",
)
SOURCE_ANCHORS = {
    "commands/earnings.md": ("8-12", "last 3 months", "transcript", "DOCX", "Quality Checklist", "Sources"),
    "skills/earnings-analysis/SKILL.md": ("8-12", "Beat/Miss", "10-", "Sources"),
    "skills/initiating-coverage/SKILL.md": ("One Task at a Time", "Task 2"),
}
AH_MECHANISMS = ("两融", "限售解禁", "业绩预告", "LPR", "NMPA", "增减持")
GAP_ANCHORS = ("options-implied", "盘前")

SCOPE_ALLOWED_PREFIXES = (
    "plugins/vertical-plugins/equity-research/",
    "plugins/agent-plugins/earnings-reviewer/skills/",
    "plugins/agent-plugins/market-researcher/skills/",
    "plugins/agent-plugins/pitch-agent/skills/sector-overview/",
    "workbuddy-experts/equity-research/",
    "scripts/export_workbuddy_experts.py",
)
SCOPE_ALLOWED_FILES = ("CUSTOM.md", "ARCHITECTURE.md")
EXPECTED_BUNDLE_CHANGES = (
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-preview/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/model-update/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/morning-note/SKILL.md",
    "plugins/agent-plugins/market-researcher/skills/idea-generation/SKILL.md",
    "plugins/agent-plugins/market-researcher/skills/sector-overview/SKILL.md",
    "plugins/agent-plugins/pitch-agent/skills/sector-overview/SKILL.md",
)


def read_block(path: Path, name: str) -> str:
    """Return the code-fence body of an fenced machine block inside a markdown file."""
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"<!--\s*{re.escape(name)}:start\s*-->(.*?)<!--\s*{re.escape(name)}:end\s*-->",
        text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"{path.name}: missing machine block '{name}'")
    body = match.group(1)
    fence = re.search(r"```[a-zA-Z]*\n(.*?)```", body, re.DOTALL)
    if not fence:
        raise AssertionError(f"{path.name}: block '{name}' has no fenced payload")
    return fence.group(1)


def parse_yaml_subset(text: str) -> dict:
    """Parse the indentation-based YAML subset used by the machine blocks.

    Supports nested maps, `key: value` scalars and inline `[a, b]` lists only.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            raise AssertionError(f"cannot parse machine line: {raw!r}")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise AssertionError(f"bad indentation in machine block: {raw!r}")
        current = stack[-1][1]
        if value == "":
            child: dict = {}
            current[key] = child
            stack.append((indent, child))
            continue
        current[key] = parse_scalar(value)
    return root


def parse_scalar(value: str):
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def block_rows(path: Path, start_marker: str, end_marker: str) -> list[list[str]]:
    """Return markdown table rows (as cell lists) between two literal markers."""
    text = path.read_text(encoding="utf-8")
    if start_marker not in text or end_marker not in text:
        raise AssertionError(f"{path.name}: missing section markers {start_marker!r}/{end_marker!r}")
    body = text.split(start_marker, 1)[1].split(end_marker, 1)[0]
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(cells)
    return rows


def crctl_mjs() -> Path:
    """Locate the controlled-shell adapter (crctl.mjs) without hardcoding a machine path."""
    import os

    candidates = []
    if os.environ.get("CRCTL_MJS"):
        candidates.append(Path(os.environ["CRCTL_MJS"]))
    rel = Path("skills/shared/crctl/scripts/crctl.mjs")
    node = ROOT
    for _ in range(6):
        candidates.append(node / "tools" / rel)
        candidates.append(node.parent / "tools" / rel)
        node = node.parent
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise AssertionError(
        "controlled-shell adapter not found: set CRCTL_MJS to the crctl.mjs path "
        "(no fallback to raw git is allowed)"
    )


def crctl_git(*args: str) -> str:
    """Run a whitelisted read-only git command through the controlled shell (full stdout)."""
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise AssertionError("node is required to run the controlled-shell adapter")
    cmd = [node, str(crctl_mjs()), "git", *args, "--cwd", str(ROOT)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        raise AssertionError(f"controlled git {' '.join(args)} failed: {proc.stderr.strip()[:400]}")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        raise AssertionError(f"controlled git {' '.join(args)} returned no output")
    payload = []
    for line in lines:
        if line.lstrip().startswith("{"):
            break
        payload.append(line.strip())
    if not payload:
        raise AssertionError(f"controlled git {' '.join(args)} produced no payload: {lines[0][:200]}")
    return "\n".join(payload)


def crctl_git_lines(*args: str) -> list[str]:
    return [ln for ln in crctl_git(*args).splitlines() if ln.strip()]


class RepoTest(unittest.TestCase):
    """Base class with a couple of common assertions."""

    def assert_file(self, path: Path) -> None:
        self.assertTrue(path.is_file(), f"missing required file: {path}")

    def assert_dir(self, path: Path) -> None:
        self.assertTrue(path.is_dir(), f"missing required directory: {path}")

    def load_manifest(self) -> dict:
        self.assert_file(MANIFEST)
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def mapping_rows(self) -> list[dict]:
        text = README.read_text(encoding="utf-8")
        blocks = re.findall(
            r"```yaml\n(row: MR-\d\d\n.*?)```",
            text,
            re.DOTALL,
        )
        return [parse_yaml_subset(b) for b in blocks]
