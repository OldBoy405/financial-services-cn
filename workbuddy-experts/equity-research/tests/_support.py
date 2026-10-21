"""Shared helpers for the CR-2026-001 evidence commands (cmd-01 .. cmd-07).

The plan's evidence-command table is the only command entry point; these modules
read the repository's real files and the controlled-shell git adapter, and fail
loudly when a prerequisite is missing. Nothing here writes to the repository.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
import subprocess
import unittest
import zipfile
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
# SDD §8 scope_in amendment (Ray-approved ruling (a), 2026-09-28): the repo's
# pre-commit hook (.githooks/pre-commit -> scripts/version_bump.py --apply)
# force-bumps a plugin's plugin.json patch version whenever that plugin has
# staged changes, and CI (.github/workflows/version-bump.yml) fails a PR
# without the bump. Syncing the named-agent skill copies therefore drags these
# three files into the diff; they are approved as version-bump artifacts only.
SCOPE_VERSION_BUMP_FILES = (
    "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json",
    "plugins/agent-plugins/market-researcher/.claude-plugin/plugin.json",
    "plugins/agent-plugins/pitch-agent/.claude-plugin/plugin.json",
)
EXPECTED_BUNDLE_CHANGES = (
    "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json",
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-preview/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/model-update/SKILL.md",
    "plugins/agent-plugins/earnings-reviewer/skills/morning-note/SKILL.md",
    "plugins/agent-plugins/market-researcher/.claude-plugin/plugin.json",
    "plugins/agent-plugins/market-researcher/skills/idea-generation/SKILL.md",
    "plugins/agent-plugins/market-researcher/skills/sector-overview/SKILL.md",
    "plugins/agent-plugins/pitch-agent/.claude-plugin/plugin.json",
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


def crctl_workspace() -> Path:
    """Locate the CR's operational KB worktree without hardcoding a machine path.

    CR-2026-072 made `--workspace` mandatory for every CR-data subcommand and removed
    both the CRCTL_WORKSPACE environment variable and cwd implicit root selection, so the
    controlled-shell adapter has to be handed the operational workspace explicitly. The
    candidate is accepted only when it really carries this CR's ledger, and the search
    mirrors crctl_mjs() (RayAI worktree layout `<kb>/.rayai-worktrees/<repo>/requirement/<CR>`).
    """
    import os

    marker = Path("change-requests") / ROOT.name / "cr.md"
    candidates = []
    if os.environ.get("CR_KB_WORKSPACE"):
        candidates.append(Path(os.environ["CR_KB_WORKSPACE"]))
    if len(ROOT.parents) > 2:
        worktrees = ROOT.parents[2]
        candidates.append(worktrees / "knowledge-base" / "requirement" / ROOT.name)
        candidates.extend(
            cr_md.parents[2]
            for cr_md in sorted(worktrees.glob(f"*/requirement/{ROOT.name}/{marker.as_posix()}"))
        )
    for candidate in candidates:
        if (candidate / marker).is_file():
            return candidate
    raise AssertionError(
        f"operational CR workspace not found: no {marker.as_posix()} for {ROOT.name} under the "
        "RayAI worktrees; set CR_KB_WORKSPACE to that worktree (crctl requires an explicit "
        "--workspace since CR-2026-072)"
    )


def crctl_git(*args: str) -> str:
    """Run a whitelisted read-only git command through the controlled shell (full stdout)."""
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise AssertionError("node is required to run the controlled-shell adapter")
    cmd = [
        node,
        str(crctl_mjs()),
        "git",
        *args,
        "--cwd",
        str(ROOT),
        "--workspace",
        str(crctl_workspace()),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT)
    )
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

# ---------------------------------------------------------------------------
# CR-FS-2026-003 (研究主链 M1) — shared evidence contract.
# The `m1-research` JSON block in ACCEPTANCE.md §6 is the only versioned
# evidence index; raw sessions/artifacts stay in the ignored `out/` tree.
# ---------------------------------------------------------------------------

M1_BLOCK = "m1-research"
M1_CR = "CR-FS-2026-003"
M1_SCHEMA_VERSION = 1
M1_SLOTS = (
    ("M1-01", "SLOT-01", "earnings-analysis"),
    ("M1-02", "SLOT-03", "model-update"),
    ("M1-03", "SLOT-02", "initiating-coverage"),
)
M1_LANGUAGES = ("zh-CN", "en-US")
M1_MARKETS = ("A股", "港股", "美股公开面")
M1_NEGATIVE_TYPES = (
    "historical-quarter",
    "code-ambiguity",
    "no-permission",
    "conflicting-sources",
    "missing-consensus",
    "missing-prerequisite",
)
M1_REPLAY_DECISIONS = ("reuse", "redo", "revision", "confirmation-rejected")
M1_POSITIVE_CASE_KEYS = (
    "case-id",
    "language",
    "market",
    "input-summary",
    "response-summary",
    "session-record",
    "client-version",
    "tool-version",
    "collected-at",
    "expected",
    "actual",
    "result",
)
M1_NEGATIVE_CASE_KEYS = (
    "case-id",
    "type",
    "input-summary",
    "response-summary",
    "session-record",
    "expected",
    "actual",
    "result",
    "not-applicable",
)
M1_ARTIFACT_KINDS = ("DOCX", "XLSX", "ZIP", "SUMMARY", "CHANGELOG", "REPORT", "MODEL-COPY")
M1_OPEN_RESULTS = ("成功", "失败", "未执行")
M1_CASE_SUMMARY_LIMIT = 400
M1_REQUIRED_ARTIFACTS = {
    "M1-01": ("DOCX", "SUMMARY"),
    "M1-02": ("MODEL-COPY", "XLSX", "CHANGELOG"),
    "M1-03": ("REPORT", "XLSX", "ZIP", "DOCX"),
}
M1_EARNINGS_CHECKLIST_SIZE = 8
M1_EVIDENCE_PREFIX = "out/"
M1_TOOL_RESULTS = ("成功", "失败", "不支持", "未执行")
M1_TABLE_ROUTES = ("new", "existing")
M1_TOOL_ROUTES = (
    "tencent-docx",
    "tencent-docs-sheet-generation",
    "tencent-docs-sheetagent",
    "tencent-local-office-edit",
    "host-preview",
    "matplotlib-fallback",
)
M1_INITIATE_STAGES = (
    ("M1-03-T1", ("REPORT",)),
    ("M1-03-T2", ("XLSX",)),
    ("M1-03-T3", ("REPORT", "XLSX")),
    ("M1-03-T4", ("ZIP",)),
    ("M1-03-T5", ("DOCX",)),
)
M1_SCOPE_EXACT_FILES = (
    "workbuddy-experts/equity-research/ACCEPTANCE.md",
    "workbuddy-experts/equity-research/tests/_support.py",
    "workbuddy-experts/equity-research/tests/test_04_localization.py",
    "workbuddy-experts/equity-research/tests/test_08_m1_evidence.py",
    "workbuddy-experts/equity-research/tests/test_09_m1_earnings.py",
    "workbuddy-experts/equity-research/tests/test_10_m1_model_update.py",
    "workbuddy-experts/equity-research/tests/test_11_m1_initiate.py",
)
M1_SCOPE_CONDITIONAL_PREFIXES = (
    "plugins/vertical-plugins/equity-research/skills/earnings-analysis/",
    "plugins/vertical-plugins/equity-research/skills/model-update/",
    "plugins/vertical-plugins/equity-research/skills/initiating-coverage/",
    "plugins/vertical-plugins/equity-research/commands/earnings.md",
    "plugins/vertical-plugins/equity-research/commands/model-update.md",
    "plugins/vertical-plugins/equity-research/commands/initiate.md",
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/",
    "plugins/agent-plugins/earnings-reviewer/skills/model-update/",
    "plugins/vertical-plugins/equity-research/.claude-plugin/plugin.json",
    "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json",
    "workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json",
    "workbuddy-experts/equity-research/README.md",
    "CUSTOM.md",
)
M1_ZERO_DIFF_PATHS = (
    "workbuddy-experts/equity-research/agents/equity-research.md",
    "scripts/check.py",
    "scripts/sync-agent-skills.py",
    "scripts/export_workbuddy_experts.py",
    ".claude-plugin/marketplace.json",
)
M1_ZERO_DIFF_PREFIXES = ("managed-agent-cookbooks/", "plugins/partner-built/")
M1_BASE_SHA = "a919ac6f221d9675539285fa2a4b2153d8feb20e"
M1_ACCEPTANCE_PREFIX_SHA256 = (
    "ee38cc4b5c0cf7c628c2a025de24063f51727e55e1533db8a34f87fbdfaebf51"
)
M1_README_BLOCK_SHA256 = {
    "baseline-evidence": "f10a5723915c6d65d7f4cd8bacbbe60bded95c64f53248a87adf0188f531347e",
    "sample-index": "875114abefda1c7f3894d5d43cb101ddcaa96ee497518daf05d6a181a1df81f6",
}
M1_AGENT_SHA256 = "4113db05c35fca48116ec0be1c668feb38f300d46c9b176d38bd3ad5def77f55"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    """Return the lowercase sha256 of a file, streamed in binary chunks."""
    if not path.is_file():
        raise AssertionError(f"sha256_file: missing file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_block(path: Path, name: str) -> dict:
    """Read a fenced machine block and parse its body as JSON."""
    body = read_block(path, name)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path.name}: block '{name}' is not valid JSON: {exc}") from exc


def m1_slot(block: dict, slot_id: str) -> dict:
    """Return the unique slot record whose `slot` equals `slot_id`."""
    slots = block.get("slots") if isinstance(block, dict) else None
    if not isinstance(slots, list):
        raise AssertionError("m1-research: 'slots' must be a list")
    hits = [slot for slot in slots if isinstance(slot, dict) and slot.get("slot") == slot_id]
    if len(hits) != 1:
        raise AssertionError(f"m1-research: expected exactly one slot {slot_id}, found {len(hits)}")
    return hits[0]


def resolve_evidence_path(rel_path: str) -> Path:
    """Resolve a standalone `artifact.path` value under the code repo's `out/` tree."""
    if not isinstance(rel_path, str) or not rel_path:
        raise AssertionError("evidence path must be a non-empty POSIX relative path")
    if rel_path.startswith("/") or "\\" in rel_path or re.match(r"^[A-Za-z]:", rel_path):
        raise AssertionError(f"evidence path must be POSIX-relative without a drive: {rel_path!r}")
    parts = rel_path.split("/")
    if parts[0] != M1_EVIDENCE_PREFIX.rstrip("/") or ".." in parts:
        raise AssertionError(f"evidence path must live under out/: {rel_path!r}")
    resolved = (ROOT / rel_path).resolve()
    out_root = (ROOT / "out").resolve()
    if not resolved.is_relative_to(out_root):
        raise AssertionError(f"evidence path escapes out/: {rel_path!r}")
    return resolved


def split_evidence_ref(ref: str) -> tuple[Path, str]:
    """Split a combined `<out-relative path>::<sha256>` evidence reference."""
    if not isinstance(ref, str) or "::" not in ref:
        raise AssertionError(f"evidence reference must be '<path>::<sha256>': {ref!r}")
    rel_path, _, digest = ref.rpartition("::")
    path = resolve_evidence_path(rel_path)
    if not _SHA256_RE.match(digest):
        raise AssertionError(f"evidence reference digest must be 64 lowercase hex chars: {ref!r}")
    return path, digest


def _iso8601_problems(value: object, label: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{label}: missing ISO8601 timestamp"]
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return [f"{label}: not an ISO8601 timestamp: {value!r}"]
    if parsed.tzinfo is None:
        return [f"{label}: timestamp must carry a timezone: {value!r}"]
    return []


def _ref_problems(ref: object, label: str) -> list[str]:
    try:
        path, digest = split_evidence_ref(ref)
    except AssertionError as exc:
        return [f"{label}: {exc}"]
    if not path.is_file():
        return [f"{label}: referenced file is missing: {ref}"]
    if sha256_file(path) != digest:
        return [f"{label}: sha256 does not match the referenced file: {ref}"]
    return []


def _three_part_problems(value: object, label: str) -> list[str]:
    parts = value.split("|") if isinstance(value, str) else []
    if len(parts) != 3 or any(not part.strip() for part in parts):
        return [f"{label}: expected '<tool>|<version>|<route>': {value!r}"]
    return []


def _route_of(value: str) -> str:
    return value.split("|")[2]


def _load_ref_json(ref: object, label: str) -> tuple[dict | None, list[str]]:
    problems = _ref_problems(ref, label)
    if problems:
        return None, problems
    path, _ = split_evidence_ref(ref)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{label}: cannot parse referenced JSON: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{label}: referenced JSON must be an object"]
    return data, []


def m1_readiness_problems(block: dict, context: str) -> list[str]:
    """Fail-closed prerequisite gate shared by cmd-01 .. cmd-04 (plan §6 B-03)."""
    if context not in ("develop", "collect"):
        return [f"unknown evidence context {context!r}; only develop/collect are allowed"]
    if not isinstance(block, dict):
        return ["m1-research: evidence block must be an object"]
    slots = block.get("slots")
    if not isinstance(slots, list):
        return ["m1-research: 'slots' must be a list"]
    registered = any(
        isinstance(slot, dict)
        and (
            slot.get("positive-cases")
            or slot.get("negative-cases")
            or slot.get("artifacts")
            or slot.get("research-state") != "待测"
        )
        for slot in slots
    )
    if context != "collect" and not registered:
        return []
    prerequisites = block.get("prerequisites")
    if not isinstance(prerequisites, dict):
        return ["prerequisites: missing record map"]
    problems: list[str] = []
    for key in ("cr1", "cr2"):
        item = prerequisites.get(key)
        if not isinstance(item, dict):
            problems.append(f"prerequisites.{key}: missing record")
            continue
        if item.get("accepted") is not True:
            problems.append(f"prerequisites.{key}: accepted must be true before real evidence is consumed")
        problems += _iso8601_problems(item.get("checked-at"), f"prerequisites.{key}.checked-at")
        if not str(item.get("checked-by") or "").strip():
            problems.append(f"prerequisites.{key}: checked-by is required")
        problems += _ref_problems(item.get("evidence-ref"), f"prerequisites.{key}.evidence-ref")
    existing = prerequisites.get("existing-model")
    if not isinstance(existing, dict):
        problems.append("prerequisites.existing-model: missing record")
    else:
        if existing.get("accepted") is not True:
            problems.append("prerequisites.existing-model: accepted must be true before real evidence is consumed")
        problems += _iso8601_problems(existing.get("checked-at"), "prerequisites.existing-model.checked-at")
        problems += _ref_problems(
            existing.get("rights-evidence-ref"), "prerequisites.existing-model.rights-evidence-ref"
        )
        baseline = existing.get("baseline-sha256")
        if not isinstance(baseline, str) or not _SHA256_RE.match(baseline):
            problems.append("prerequisites.existing-model: baseline-sha256 must be 64 lowercase hex chars")
    return problems


def m1_tool_record_problems(artifact: dict, expected_routes: tuple[str, ...]) -> list[str]:
    """Fail-closed AC-06 host-file-tool record check (plan §6 B-07)."""
    if not isinstance(artifact, dict):
        return ["artifact record must be an object"]
    problems = _three_part_problems(artifact.get("generated-by"), "generated-by")
    meta = artifact.get("meta")
    if not isinstance(meta, dict):
        return problems + ["artifact.meta must be an object"]
    if not str(meta.get("schema-query") or "").strip():
        problems.append("meta.schema-query is required")
    kind = artifact.get("kind")
    if kind not in M1_ARTIFACT_KINDS:
        problems.append(f"artifact.kind is not allowed: {kind!r}")
    if kind in ("XLSX", "MODEL-COPY"):
        if meta.get("table-route") not in M1_TABLE_ROUTES:
            problems.append("meta.table-route must be new/existing for XLSX and MODEL-COPY")
    elif kind == "ZIP":
        for key in ("script", "dependencies", "inputs"):
            value = meta.get(key)
            if isinstance(value, str):
                if not value.strip():
                    problems.append(f"meta.{key} is required for ZIP")
            elif not value:
                problems.append(f"meta.{key} is required for ZIP")
        inputs = meta.get("inputs")
        if isinstance(inputs, list):
            for index, item in enumerate(inputs):
                problems += _ref_problems(item, f"meta.inputs[{index}]")
        elif inputs:
            problems.append("meta.inputs must be a list of <path>::<sha256> references")
    result = meta.get("tool-result")
    if result not in M1_TOOL_RESULTS:
        return problems + [f"meta.tool-result is not allowed: {result!r}"]
    actual_route = _route_of(artifact["generated-by"]) if not _three_part_problems(
        artifact.get("generated-by"), "generated-by"
    ) else ""
    if result != "不支持":
        if actual_route not in expected_routes:
            problems.append(
                f"generated-by route {actual_route!r} is not allowed here; expected one of {expected_routes}"
            )
        return problems
    unsupported = meta.get("unsupported-generated-by")
    unsupported_problems = _three_part_problems(unsupported, "meta.unsupported-generated-by")
    problems += unsupported_problems
    if not unsupported_problems and _route_of(unsupported) not in expected_routes:
        problems.append(
            f"meta.unsupported-generated-by route {_route_of(unsupported)!r} is not in {expected_routes}"
        )
    deviations = artifact.get("deviations")
    matching = None
    if isinstance(deviations, list):
        for deviation in deviations:
            if isinstance(deviation, dict) and deviation.get("actual") == artifact.get("generated-by"):
                matching = deviation
                break
    if matching is None:
        problems.append("a deviation whose actual equals generated-by is required when the tool is unsupported")
    else:
        for key in ("requirement", "actual", "reason", "adjudication-ref"):
            if not str(matching.get(key) or "").strip():
                problems.append(f"deviation.{key} is required")
        adjudication, adjudication_problems = _load_ref_json(
            matching.get("adjudication-ref"), "deviation.adjudication-ref"
        )
        problems += adjudication_problems
        if adjudication is not None:
            if adjudication.get("adjudicator") != "Ray":
                problems.append("adjudication record must be adjudicated by Ray")
            if adjudication.get("decision") != "批准最小替代":
                problems.append("adjudication record must record decision '批准最小替代'")
            for key, value in (
                ("case-id", artifact.get("case-id")),
                ("artifact-id", artifact.get("artifact-id")),
                ("actual", artifact.get("generated-by")),
            ):
                if adjudication.get(key) != value:
                    problems.append(f"adjudication record {key} does not match this artifact")
    retest, retest_problems = _load_ref_json(meta.get("retest"), "meta.retest")
    problems += retest_problems
    if retest is not None:
        for key, value in (
            ("case-id", artifact.get("case-id")),
            ("artifact-id", artifact.get("artifact-id")),
            ("kind", artifact.get("kind")),
            ("path", artifact.get("path")),
            ("sha256", artifact.get("sha256")),
            ("generated-by", artifact.get("generated-by")),
        ):
            if retest.get(key) != value:
                problems.append(f"retest record {key} does not match this artifact")
        if retest.get("result") != "成功":
            problems.append("retest result must be 成功")
        if retest.get("open-check-result") != "成功":
            problems.append("retest open-check-result must be 成功")
        problems += _iso8601_problems(retest.get("checked-at"), "retest.checked-at")
    return problems


# ── CR-FS-2026-004 六项与 phase-1 收口证据契约（TASK-01） ──────────────────
# The CR4 index is append-only: §1–§6 keep their bytes; §7/§8 are new blocks.
C4_BLOCK = "cr4-research"
C4_CLOSEOUT_BLOCK = "phase1-closeout"
C4_CR = "CR-FS-2026-004"
C4_SCHEMA_VERSION = 1
C4_CASE_SUMMARY_LIMIT = 400
C4_BASELINE_ACCEPTANCE_LINES = 282
C4_SECTION6_TITLE = "## 6. M1 研究证据与裁决记录"
C4_SECTION7_TITLE = "## 7. 其余六项研究证据与裁决记录"
C4_STATES = ("待测", "通过", "不通过", "需重测")
C4_SLOTS = (
    ("C4-01", "SLOT-04", "idea-generation"),
    ("C4-02", "SLOT-05", "catalyst-calendar"),
    ("C4-03", "SLOT-06", "morning-note"),
    ("C4-04", "SLOT-07", "earnings-preview"),
    ("C4-05", "SLOT-08", "sector-overview"),
    ("C4-06", "SLOT-09", "thesis-tracker"),
)
C4_M1_SLOTS = (
    ("M1-01", "SLOT-01", "earnings-analysis"),
    ("M1-02", "SLOT-03", "model-update"),
    ("M1-03", "SLOT-02", "initiating-coverage"),
)
C4_NINE_TASKS = (
    "earnings",
    "initiate",
    "model-update",
    "screen",
    "catalysts",
    "morning-note",
    "earnings-preview",
    "sector",
    "thesis",
)
C4_SECTION6_SHA256 = "bd1f53b460488f4c3fb9fbeb4848fad2fa6096461c7b539f3288cc33f30e1d1a"
C4_SCOPE_EXACT_FILES = (
    "workbuddy-experts/equity-research/ACCEPTANCE.md",
    "workbuddy-experts/equity-research/tests/_support.py",
    "workbuddy-experts/equity-research/tests/test_08_m1_evidence.py",
    "workbuddy-experts/equity-research/tests/test_13_cr4_evidence.py",
    "workbuddy-experts/equity-research/tests/test_14_cr4_matrix.py",
    "workbuddy-experts/equity-research/tests/test_15_cr4_artifacts.py",
    "workbuddy-experts/equity-research/tests/test_16_m1_recheck.py",
    "workbuddy-experts/equity-research/tests/test_17_reinstall_readiness.py",
)
C4_CONDITIONAL_PREFIXES = (
    "plugins/vertical-plugins/equity-research/skills/idea-generation/",
    "plugins/vertical-plugins/equity-research/skills/catalyst-calendar/",
    "plugins/vertical-plugins/equity-research/skills/morning-note/",
    "plugins/vertical-plugins/equity-research/skills/earnings-preview/",
    "plugins/vertical-plugins/equity-research/skills/sector-overview/",
    "plugins/vertical-plugins/equity-research/skills/thesis-tracker/",
    "plugins/vertical-plugins/equity-research/commands/screen.md",
    "plugins/vertical-plugins/equity-research/commands/catalysts.md",
    "plugins/vertical-plugins/equity-research/commands/morning-note.md",
    "plugins/vertical-plugins/equity-research/commands/earnings-preview.md",
    "plugins/vertical-plugins/equity-research/commands/sector.md",
    "plugins/vertical-plugins/equity-research/commands/thesis.md",
)
C4_ZIP_KINDS = ("DOCX", "XLSX", "PPTX", "ZIP")


def c4_section6_sha256(text: str) -> str:
    """Hash the §6 region with one canonical, line-ending-independent rule.

    LF-normalise, slice from the §6 heading (inclusive) to the §7 heading
    (exclusive; EOF when §7 is absent), trim trailing blank lines, add one
    trailing LF, then SHA-256 the UTF-8 bytes.  The separator blank line that
    precedes §7 is therefore trimmed on both sides of the append.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    try:
        start = lines.index(C4_SECTION6_TITLE)
    except ValueError as exc:
        raise AssertionError("ACCEPTANCE.md is missing the §6 heading") from exc
    try:
        end = lines.index(C4_SECTION7_TITLE, start)
    except ValueError:
        end = len(lines)
    region = lines[start:end]
    while region and region[-1] == "":
        region.pop()
    return hashlib.sha256(("\n".join(region) + "\n").encode("utf-8")).hexdigest()


def c4_slot(block: dict, slot_id: str) -> dict:
    matches = [slot for slot in block.get("slots") or [] if slot.get("slot") == slot_id]
    if len(matches) != 1:
        raise AssertionError(f"{slot_id}: expected exactly one slot record, found {len(matches)}")
    return matches[0]


def c4_m1(block: dict, m1_slot: str) -> dict:
    matches = [row for row in block.get("m1-recheck") or [] if row.get("m1-slot") == m1_slot]
    if len(matches) != 1:
        raise AssertionError(f"{m1_slot}: expected exactly one m1-recheck record, found {len(matches)}")
    return matches[0]


def c4_slot_eligible(c4_block: dict, slot_id: str) -> bool:
    """Common prerequisites plus this slot's own domains/tools/records must all be accepted."""
    common = (c4_block.get("prerequisites") or {}).get("common") or {}
    if not all((common.get(key) or {}).get("accepted") is True for key in ("cr1-baseline", "cr2-authorization-framework", "package-baseline")):
        return False
    requirement = next(
        (row for row in ((c4_block.get("prerequisites") or {}).get("slots") or []) if row.get("slot") == slot_id),
        None,
    )
    if requirement is None:
        return False
    for key in ("required-domains", "required-tools", "required-records"):
        for item in requirement.get(key) or []:
            if item.get("accepted") is not True:
                return False
    return True


def c4_check_ref(ref: object, label: str) -> list[str]:
    """Verify a `<path>::<sha256>` evidence reference against the real file."""
    try:
        path, digest = split_evidence_ref(str(ref))
    except AssertionError as exc:
        return [f"{label}: {exc}"]
    try:
        actual = sha256_file(path)
    except AssertionError as exc:
        return [f"{label}: {exc}"]
    if actual != digest:
        return [f"{label}: sha256 mismatch ({actual} != {digest})"]
    return []


def c4_check_artifact(artifact: dict, label: str) -> list[str]:
    """Verify a standalone artifact path, size, digest and container structure."""
    problems: list[str] = []
    try:
        path = resolve_evidence_path(str(artifact.get("path") or ""))
    except AssertionError as exc:
        return [f"{label}: {exc}"]
    if not path.is_file():
        return [f"{label}: missing file {path}"]
    actual = sha256_file(path)
    if actual != artifact.get("sha256"):
        problems.append(f"{label}: sha256 mismatch")
    if path.stat().st_size != artifact.get("bytes"):
        problems.append(f"{label}: bytes mismatch")
    if artifact.get("kind") in C4_ZIP_KINDS and not zipfile.is_zipfile(path):
        problems.append(f"{label}: {artifact.get('kind')} is not a readable ZIP container")
    return problems


def _c4_adjudication(record: dict) -> tuple[str, str, str]:
    adjudication = record.get("adjudication") or {}
    return (
        adjudication.get("state") or "",
        adjudication.get("adjudicator") or "",
        adjudication.get("adjudicated-at") or "",
    )


def nine_view(c4_block: dict, closeout_block: dict, task: str) -> dict:
    """Project the six C4 slots and three M1 rechecks into the nine-item view."""
    if task not in C4_NINE_TASKS:
        raise AssertionError(f"{task}: not one of the nine tasks")
    if task in ("earnings", "initiate", "model-update"):
        m1_slot = {"earnings": "M1-01", "model-update": "M1-02", "initiate": "M1-03"}[task]
        record = c4_m1(c4_block, m1_slot)
        adj_state, adjudicator, adjudicated_at = _c4_adjudication(record)
        prior = record.get("prior") or {}
        if record.get("path-mode") == "carry-forward":
            state = adj_state or (prior.get("state") or "")
            carry_ok = prior.get("state") == "通过" and bool(prior.get("adjudication-ref"))
        else:
            state = adj_state
            carry_ok = True
        package_hash = ((record.get("package-link") or {}).get("content-sha256")) or ""
        eligible = c4_slot_eligible(c4_block, m1_slot)
        kind, ref = "m1", f"§7/m1-recheck#{m1_slot}"
        adjudication_ok = adj_state == "通过"
    else:
        slot_id = {
            "screen": "C4-01",
            "catalysts": "C4-02",
            "morning-note": "C4-03",
            "earnings-preview": "C4-04",
            "sector": "C4-05",
            "thesis": "C4-06",
        }[task]
        record = c4_slot(c4_block, slot_id)
        state, adjudicator, adjudicated_at = _c4_adjudication(record)
        package_hash = ((c4_block.get("package") or {}).get("content-sha256")) or ""
        eligible = c4_slot_eligible(c4_block, slot_id)
        kind, ref = "c4", f"§7/slots#{slot_id}"
        carry_ok = True
        adjudication_ok = state == "通过"
    closeout_hash = ((closeout_block.get("package") or {}).get("content-sha256")) or ""
    counts = bool(
        adjudication_ok
        and carry_ok
        and eligible
        and state == "通过"
        and adjudicator
        and adjudicated_at
        and package_hash
        and package_hash == closeout_hash
    )
    return {
        "task": task,
        "record-kind": kind,
        "record-ref": ref,
        "current-state": state,
        "adjudicator": adjudicator,
        "adjudicated-at": adjudicated_at,
        "package-content-sha256": package_hash,
        "counts-toward-9": counts,
    }
