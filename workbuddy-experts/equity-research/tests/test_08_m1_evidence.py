"""cmd-01 — the versioned `m1-research` evidence index and its fail-closed gates.

CR-FS-2026-003 (研究主链 M1). The module has two halves:

* contract self-checks — every path/hash/JSON/readiness/tool-record/scope helper is
  exercised against small temporary files, so the gates are provably able to fail;
* the repository contract — `ACCEPTANCE.md` §6 is read through `read_json_block`, every
  registered case/artifact is re-hashed here, and the SDD §9 scope plus the
  append-only §6 surface are asserted against the fixed baseline commit.

Nothing in this module writes to `ACCEPTANCE.md`, `out/` or any adjudication field.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import _support
from _support import (
    ACCEPTANCE,
    M1_ACCEPTANCE_PREFIX_SHA256,
    M1_AGENT_SHA256,
    M1_ARTIFACT_KINDS,
    M1_BASE_SHA,
    M1_BLOCK,
    M1_CASE_SUMMARY_LIMIT,
    M1_CR,
    M1_EARNINGS_CHECKLIST_SIZE,
    M1_INITIATE_STAGES,
    M1_LANGUAGES,
    M1_MARKETS,
    M1_NEGATIVE_CASE_KEYS,
    M1_NEGATIVE_TYPES,
    M1_OPEN_RESULTS,
    M1_POSITIVE_CASE_KEYS,
    M1_README_BLOCK_SHA256,
    M1_REPLAY_DECISIONS,
    M1_REQUIRED_ARTIFACTS,
    M1_SCHEMA_VERSION,
    M1_SCOPE_CONDITIONAL_PREFIXES,
    M1_SCOPE_EXACT_FILES,
    M1_SLOTS,
    M1_TABLE_ROUTES,
    M1_TOOL_RESULTS,
    M1_ZERO_DIFF_PATHS,
    M1_ZERO_DIFF_PREFIXES,
    README,
    ROOT,
    RepoTest,
    crctl_mjs,
    crctl_workspace,
    m1_readiness_problems,
    m1_slot,
    m1_tool_record_problems,
    parse_yaml_subset,
    read_block,
    read_json_block,
    resolve_evidence_path,
    sha256_file,
    split_evidence_ref,
)

EVIDENCE_CONTEXT = os.environ.get("M1_EVIDENCE_CONTEXT", "develop")
APPEND_TITLE = "## 6. M1 研究证据与裁决记录"
BASELINE_ACCEPTANCE_LINES = 282
CHECKLIST_RESULTS = ("通过", "不通过", "不适用")
SKILL_ROWS = {
    "earnings-analysis": "MR-01",
    "initiating-coverage": "MR-02",
    "model-update": "MR-03",
}
ARTIFACT_KEYS = {
    "artifact-id",
    "case-id",
    "kind",
    "path",
    "sha256",
    "bytes",
    "generated-by",
    "open-check",
    "structural",
    "meta",
    "deviations",
}
OPEN_CHECK_KEYS = {"host", "at", "result"}
STRUCTURAL_KEYS = {"type", "ok", "detail"}
DEVIATION_KEYS = ("requirement", "actual", "reason", "adjudication-ref")
CROSS_SESSION_KEYS = {
    "reentry-id",
    "exit-at",
    "reentry-at",
    "provided-artifacts",
    "stage-located",
    "confirmation",
    "final-artifact",
    "result",
}
PLUGIN_MANIFESTS = (
    "plugins/vertical-plugins/equity-research/.claude-plugin/plugin.json",
    "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json",
    "workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json",
)
SOURCE_PREFIXES = (
    "plugins/vertical-plugins/equity-research/skills/earnings-analysis/",
    "plugins/vertical-plugins/equity-research/skills/model-update/",
    "plugins/vertical-plugins/equity-research/skills/initiating-coverage/",
    "plugins/vertical-plugins/equity-research/commands/earnings.md",
    "plugins/vertical-plugins/equity-research/commands/model-update.md",
    "plugins/vertical-plugins/equity-research/commands/initiate.md",
)
COPY_PREFIXES = (
    "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/",
    "plugins/agent-plugins/earnings-reviewer/skills/model-update/",
)
SKILL_CHANGE_KEYS = {
    "changed",
    "verified-package-version",
    "skill-source-head",
    "case-id",
    "source-paths",
    "copy-paths",
    "retested-cases",
    "versions",
    "wb-custom",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
CREDENTIAL_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?key|secret[_-]?key|password\s*[:=]|bearer\s+[a-z0-9._-]{8,}|"
    r"sk-[a-z0-9]{8,}|akia[0-9a-z]{12,})"
)
ABSOLUTE_PATH_RE = re.compile(
    r"(?:^|[\s\"'(])(?:[A-Za-z]:[\\/]|\\\\|/(?:Users|home|mnt|tmp|var|opt|root)/)"
)


def load_block(path: Path = ACCEPTANCE) -> dict:
    return read_json_block(path, M1_BLOCK)


def evidence_context() -> str:
    return os.environ.get("M1_EVIDENCE_CONTEXT", "develop")


def setUpModule() -> None:  # noqa: N802 - unittest hook
    block = load_block()
    problems = m1_readiness_problems(block, evidence_context())
    if problems:
        raise SystemExit("ENVIRONMENT_MISMATCH: " + "; ".join(problems))


@contextlib.contextmanager
def temp_root():
    """Temporarily point the evidence root at a throwaway directory."""
    original = _support.ROOT
    with tempfile.TemporaryDirectory() as tmp:
        _support.ROOT = Path(tmp)
        try:
            yield Path(tmp)
        finally:
            _support.ROOT = original


def write_evidence(root: Path, rel_path: str, data: bytes) -> str:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"{rel_path}::{hashlib.sha256(data).hexdigest()}"


def _summary_problems(value: object, label: str) -> list[str]:
    if not isinstance(value, str):
        return [f"{label}: summary must be a string"]
    problems = []
    if len(value) > M1_CASE_SUMMARY_LIMIT:
        problems.append(f"{label}: summary exceeds {M1_CASE_SUMMARY_LIMIT} characters")
    if ABSOLUTE_PATH_RE.search(value):
        problems.append(f"{label}: summary must not contain an absolute path")
    if CREDENTIAL_RE.search(value):
        problems.append(f"{label}: summary must not contain credentials")
    return problems


def case_problems(case: dict, keys: tuple[str, ...]) -> list[str]:
    """Whitelist + summary gate shared by positive and negative case records."""
    if not isinstance(case, dict):
        return ["case record must be an object"]
    problems = []
    extra = sorted(set(case) - set(keys))
    missing = sorted(set(keys) - set(case))
    if extra:
        problems.append(f"case keys not allowed: {extra}")
    if missing:
        problems.append(f"case keys missing: {missing}")
    for key in ("input-summary", "response-summary"):
        problems += _summary_problems(case.get(key), f"case.{key}")
    return problems


def artifact_file_problems(artifact: dict) -> list[str]:
    """Standalone-path branch: `artifact.path` + `sha256` + `bytes`."""
    if not isinstance(artifact, dict):
        return ["artifact record must be an object"]
    try:
        path = resolve_evidence_path(artifact.get("path"))
    except AssertionError as exc:
        return [f"artifact.path: {exc}"]
    if not path.is_file():
        return [f"artifact.path: file is missing: {artifact.get('path')}"]
    problems = []
    if sha256_file(path) != artifact.get("sha256"):
        problems.append(f"artifact.sha256 does not match {artifact.get('path')}")
    if artifact.get("bytes") != path.stat().st_size:
        problems.append(f"artifact.bytes does not match {artifact.get('path')}")
    return problems


def expected_routes(artifact: dict) -> tuple[str, ...]:
    """AC-06 expected host-tool routes for one artifact (plan §6 B-07)."""
    kind = artifact.get("kind")
    case_id = artifact.get("case-id")
    if kind == "DOCX":
        return ("tencent-docx",)
    if kind in ("SUMMARY", "REPORT"):
        return ("host-preview", "tencent-docx")
    if kind == "ZIP":
        return ("matplotlib-fallback",)
    if kind == "MODEL-COPY":
        return ("tencent-docs-sheetagent",)
    if kind == "XLSX":
        if case_id == "M1-03-T2":
            return ("tencent-docs-sheet-generation",)
        return ("tencent-docs-sheetagent",)
    return ()


def table_route_problems(artifact: dict) -> list[str]:
    """New/existing table semantics: T2 is the only newly generated XLSX."""
    if artifact.get("kind") not in ("XLSX", "MODEL-COPY"):
        return []
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    expected = "new" if artifact.get("case-id") == "M1-03-T2" else "existing"
    actual = meta.get("table-route")
    if actual != expected:
        return [f"artifact {artifact.get('artifact-id')}: table-route must be {expected!r}, got {actual!r}"]
    return []


def tool_record_problems(artifact: dict) -> list[str]:
    """Per-artifact AC-06 check: route set by kind/case, shared helper enforces binding."""
    routes = expected_routes(artifact)
    if not routes:
        return []
    return m1_tool_record_problems(artifact, routes)


def _slot_cases(slot: dict) -> list[dict]:
    cases = []
    for key in ("positive-cases", "negative-cases"):
        value = slot.get(key)
        if isinstance(value, list):
            cases += [case for case in value if isinstance(case, dict)]
    return cases


def matrix_problems(slot: dict) -> list[str]:
    """CN/EN, market coverage, six negative types (or N/A reason) and result states."""
    problems = []
    positives = [c for c in slot.get("positive-cases") or [] if isinstance(c, dict)]
    negatives = [c for c in slot.get("negative-cases") or [] if isinstance(c, dict)]
    languages = {case.get("language") for case in positives}
    for language in M1_LANGUAGES:
        if language not in languages:
            problems.append(f"{slot.get('slot')}: matrix needs a {language} positive case")
    markets = [case.get("market") for case in positives]
    for market in markets:
        if market not in M1_MARKETS:
            problems.append(f"{slot.get('slot')}: positive market is not allowed: {market!r}")
    for market in ("A股", "港股", "美股公开面"):
        if market not in markets:
            problems.append(f"{slot.get('slot')}: matrix needs at least one {market} positive case")
    by_type = {}
    for case in negatives:
        by_type.setdefault(case.get("type"), []).append(case)
    for negative_type in M1_NEGATIVE_TYPES:
        cases = by_type.get(negative_type) or []
        if not cases:
            problems.append(f"{slot.get('slot')}: matrix needs a {negative_type!r} negative case or an N/A record")
            continue
        if all(not str(case.get("not-applicable") or "").strip() for case in cases):
            for case in cases:
                if not str(case.get("expected") or "").strip() or not str(case.get("actual") or "").strip():
                    problems.append(
                        f"{slot.get('slot')}: negative case {case.get('case-id')!r} needs expected/actual "
                        "or a not-applicable reason with an adjacent verification path"
                    )
        else:
            for case in cases:
                if str(case.get("not-applicable") or "").strip() and (
                    not str(case.get("expected") or "").strip() or not str(case.get("actual") or "").strip()
                ):
                    problems.append(
                        f"{slot.get('slot')}: N/A negative case {case.get('case-id')!r} needs expected/actual"
                    )
    for case in positives + negatives:
        if case.get("result") != "通过":
            problems.append(f"{slot.get('slot')}: case {case.get('case-id')!r} is not 通过")
    return problems


def checklist_problems(items: list[dict], passed: bool) -> list[str]:
    """M1-01 eight-item checklist: count, uniqueness, evidence pointer and verdicts."""
    problems = []
    if not isinstance(items, list):
        return ["quality-checklist must be a list"]
    if passed and len(items) != M1_EARNINGS_CHECKLIST_SIZE:
        problems.append(
            f"quality-checklist must have exactly {M1_EARNINGS_CHECKLIST_SIZE} items, got {len(items)}"
        )
    seen = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"quality-checklist[{index}] must be an object")
            continue
        extra = sorted(set(item) - {"item", "result", "evidence-ref"})
        if extra:
            problems.append(f"quality-checklist[{index}] keys not allowed: {extra}")
        label = f"quality-checklist[{index}]"
        for key in ("item", "result", "evidence-ref"):
            if not str(item.get(key) or "").strip():
                problems.append(f"{label}.{key} is required")
        if item.get("result") not in CHECKLIST_RESULTS:
            problems.append(f"{label}.result is not allowed: {item.get('result')!r}")
        if passed and item.get("result") == "不通过":
            problems.append(f"{label} is 不通过 but the slot claims 通过")
        if item.get("item") in seen:
            problems.append(f"{label}.item duplicates another checklist item")
        seen.add(item.get("item"))
    return problems


def _registered_artifacts(slot: dict) -> list[dict]:
    return [artifact for artifact in slot.get("artifacts") or [] if isinstance(artifact, dict)]


def _artifact_pairs(artifacts: list[dict]) -> set[tuple[object, object]]:
    return {(artifact.get("path"), artifact.get("sha256")) for artifact in artifacts}


def _replay_originals(artifacts: list[dict], reuse_pairs: set[tuple[object, object]]) -> set[tuple[object, object]]:
    """Artifacts a redo/revision may not point at: reused targets and the first record per case+kind."""
    originals = set(reuse_pairs)
    seen: set[tuple[object, object]] = set()
    for artifact in artifacts:
        key = (artifact.get("case-id"), artifact.get("kind"))
        if key in seen:
            continue
        seen.add(key)
        originals.add((artifact.get("path"), artifact.get("sha256")))
    return originals


def replay_problems(slot: dict) -> list[str]:
    """Replay/revision four-branch contract (SDD §3.3, §4.8)."""
    problems = []
    replay = slot.get("replay")
    if replay is None:
        return []
    if not isinstance(replay, list):
        return ["replay must be a list"]
    artifacts = _registered_artifacts(slot)
    registered = _artifact_pairs(artifacts)
    keys = {"replay-key", "replay-decision", "diff-summary", "confirmation", "artifact-ref"}
    reuse_pairs: set[tuple[object, object]] = set()
    for item in replay:
        if not isinstance(item, dict) or item.get("replay-decision") != "reuse":
            continue
        try:
            path, digest = split_evidence_ref(item.get("artifact-ref"))
        except AssertionError:
            continue
        reuse_pairs.add((path.relative_to(_support.ROOT).as_posix(), digest))
    originals = _replay_originals(artifacts, reuse_pairs)
    for index, item in enumerate(replay):
        label = f"replay[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{label} must be an object")
            continue
        extra = sorted(set(item) - keys)
        missing = sorted(keys - set(item))
        if extra:
            problems.append(f"{label} keys not allowed: {extra}")
        if missing:
            problems.append(f"{label} keys missing: {missing}")
        if not str(item.get("replay-key") or "").strip():
            problems.append(f"{label}.replay-key is required")
        decision = item.get("replay-decision")
        if decision not in M1_REPLAY_DECISIONS:
            problems.append(f"{label}.replay-decision is not allowed: {decision!r}")
            continue
        diff_summary = str(item.get("diff-summary") or "").strip()
        confirmation = str(item.get("confirmation") or "").strip()
        ref = item.get("artifact-ref")
        if decision == "reuse":
            if not ref:
                problems.append(f"{label}: reuse must point at the reused artifact")
                continue
            try:
                path, digest = split_evidence_ref(ref)
            except AssertionError as exc:
                problems.append(f"{label}.artifact-ref: {exc}")
                continue
            if not path.is_file():
                problems.append(f"{label}.artifact-ref: file is missing")
            elif sha256_file(path) != digest:
                problems.append(f"{label}.artifact-ref: sha256 does not match")
            elif (path.relative_to(_support.ROOT).as_posix(), digest) not in registered:
                problems.append(f"{label}: reuse must reference an already registered artifact")
        elif decision in ("redo", "revision"):
            for key, value in (("confirmation", confirmation), ("diff-summary", diff_summary)):
                if not value:
                    problems.append(f"{label}.{key} is required for {decision}")
            if not ref:
                problems.append(f"{label}: {decision} needs a new independent artifact-ref")
                continue
            try:
                path, digest = split_evidence_ref(ref)
            except AssertionError as exc:
                problems.append(f"{label}.artifact-ref: {exc}")
                continue
            pair = (path.relative_to(_support.ROOT).as_posix(), digest)
            if not path.is_file():
                problems.append(f"{label}.artifact-ref: file is missing")
            elif sha256_file(path) != digest:
                problems.append(f"{label}.artifact-ref: sha256 does not match")
            elif pair not in registered:
                problems.append(
                    f"{label}: {decision} must register the new artifact (new artifact-id and file) in "
                    "slots.artifacts, not an unindexed copy"
                )
            elif pair in originals:
                problems.append(
                    f"{label}: {decision} must produce a new artifact, not reuse or overwrite the replaced original"
                )
        else:  # confirmation-rejected
            if ref:
                problems.append(f"{label}: confirmation-rejected must not produce a formal revision")
            if not diff_summary:
                problems.append(f"{label}.diff-summary is required for confirmation-rejected")
            if not confirmation:
                problems.append(f"{label}.confirmation is required for confirmation-rejected")
    return problems


def _path_list_problems(value: object, label: str, prefixes: tuple[str, ...], allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        return [f"{label} must be a non-empty list of repository paths"]
    problems = []
    for index, path in enumerate(value):
        if not isinstance(path, str) or not path.strip():
            problems.append(f"{label}[{index}] must be a non-empty repository path")
        elif not any(path == prefix or path.startswith(prefix) for prefix in prefixes):
            problems.append(f"{label}[{index}] is outside the approved conditional paths: {path!r}")
    return problems


def _versions_problems(value: object, label: str) -> list[str]:
    """`versions` registers the bumped plugin.json path -> new three-part version."""
    if not isinstance(value, dict) or not value:
        return [f"{label} must register the bumped plugin.json paths and versions"]
    problems = []
    for path, version in value.items():
        if path not in PLUGIN_MANIFESTS:
            problems.append(f"{label}: {path!r} is not an approved plugin manifest")
        if not isinstance(version, str) or not VERSION_RE.match(version):
            problems.append(f"{label}: {path!r} needs a three-part version, got {version!r}")
    return problems


def skill_change_problems(slot: dict, block: dict) -> list[str]:
    """FR-09: no change is the default; a change must be traceable to a real case."""
    problems = []
    record = slot.get("skill-change")
    label = f"{slot.get('slot')}.skill-change"
    if not isinstance(record, dict):
        return [f"{label} must be an object"]
    extra = sorted(set(record) - SKILL_CHANGE_KEYS)
    if extra:
        problems.append(f"{label} keys not allowed: {extra}")
    if record.get("changed") is not True:
        extra = sorted(set(record) - {"changed", "verified-package-version", "skill-source-head"})
        if extra:
            problems.append(f"{label} keys not allowed when changed=false: {extra}")
        if not str(record.get("verified-package-version") or "").strip():
            problems.append(f"{label}.verified-package-version is required when changed=false")
        head = record.get("skill-source-head")
        if not isinstance(head, str) or not re.match(r"^[0-9a-f]{40}$", head):
            problems.append(f"{label}.skill-source-head must be a 40-char SHA")
        if block.get("package-version") and record.get("verified-package-version") != block.get("package-version"):
            problems.append(f"{label}.verified-package-version must equal the recorded package-version")
        if block.get("skill-source-head") and head != block.get("skill-source-head"):
            problems.append(f"{label}.skill-source-head must equal the recorded skill-source-head")
        return problems
    case_ids = {case.get("case-id") for case in _slot_cases(slot)}
    if record.get("case-id") not in case_ids:
        problems.append(f"{label}.case-id must hit a real case in this slot")
    skill = slot.get("skill")
    problems += _path_list_problems(record.get("source-paths"), f"{label}.source-paths", SOURCE_PREFIXES, False)
    copy_prefixes = tuple(prefix for prefix in COPY_PREFIXES if skill in prefix)
    problems += _path_list_problems(record.get("copy-paths"), f"{label}.copy-paths", copy_prefixes or ("",), True)
    if not copy_prefixes and record.get("copy-paths"):
        problems.append(f"{label}.copy-paths: {skill!r} has no bundled agent copy")
    retested = record.get("retested-cases")
    if not isinstance(retested, list) or not retested:
        problems.append(f"{label}.retested-cases is required when changed=true")
    else:
        for index, case_id in enumerate(retested):
            if case_id not in case_ids:
                problems.append(f"{label}.retested-cases[{index}] must hit a real case in this slot")
    problems += _versions_problems(record.get("versions"), f"{label}.versions")
    if not str(record.get("wb-custom") or "").strip():
        problems.append(f"{label}.wb-custom is required when changed=true")
    return problems


def slot_pass_problems(slot: dict, block: dict) -> list[str]:
    """Fail-closed conditions that only apply once Ray marks a slot 通过."""
    if slot.get("research-state") != "通过":
        return []
    slot_id = slot.get("slot")
    problems = list(m1_readiness_problems(block, "collect"))
    if slot.get("adjudicator") != "Ray":
        problems.append(f"{slot_id}: adjudicator must be Ray once the slot is 通过")
    if not str(slot.get("adjudicated-at") or "").strip():
        problems.append(f"{slot_id}: adjudicated-at is required once the slot is 通过")
    problems += matrix_problems(slot)
    kinds = {artifact.get("kind") for artifact in slot.get("artifacts") or [] if isinstance(artifact, dict)}
    for kind in M1_REQUIRED_ARTIFACTS.get(slot_id, ()):
        if kind not in kinds:
            problems.append(f"{slot_id}: required artifact kind {kind} is missing")
    if slot_id == "M1-01":
        problems += checklist_problems(slot.get("quality-checklist") or [], True)
    if slot_id == "M1-03" and slot.get("cross-session") is None:
        problems.append("M1-03: cross-session record is required once the slot is 通过")
    for artifact in slot.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
        open_check = artifact.get("open-check") if isinstance(artifact.get("open-check"), dict) else {}
        if meta.get("tool-result") not in ("成功", "不支持"):
            problems.append(f"{artifact.get('artifact-id')}: tool-result must be 成功 or an adjudicated 不支持")
        if artifact.get("kind") in ("DOCX", "XLSX", "SUMMARY", "REPORT") and open_check.get("result") != "成功":
            problems.append(f"{artifact.get('artifact-id')}: open-check must be 成功 for {artifact.get('kind')}")
        if artifact.get("kind") == "ZIP" and open_check.get("result") not in ("成功",):
            problems.append(f"{artifact.get('artifact-id')}: open-check must be 成功 for ZIP")
        if artifact.get("kind") == "MODEL-COPY" and open_check.get("result") not in ("成功", "未执行"):
            problems.append(f"{artifact.get('artifact-id')}: MODEL-COPY open-check must be 成功 or 未执行")
    return problems


def legacy_slots() -> dict[str, str]:
    """Parse the nine pre-existing YAML records in §2 into slot -> skill."""
    text = ACCEPTANCE.read_text(encoding="utf-8")
    if "## 2." not in text or "## 3." not in text:
        raise AssertionError("ACCEPTANCE.md: section 2/3 markers are missing")
    section = text.split("## 2.", 1)[1].split("## 3.", 1)[0]
    records = re.findall(r"```yaml\n(slot: SLOT-\d\d\n.*?)```", section, re.DOTALL)
    if len(records) != 9:
        raise AssertionError(f"ACCEPTANCE.md §2: expected 9 YAML slot records, found {len(records)}")
    mapping = {}
    for body in records:
        record = parse_yaml_subset(body)
        slot = record.get("slot")
        if slot in mapping:
            raise AssertionError(f"ACCEPTANCE.md §2: duplicate slot {slot}")
        for key in ("skill", "state", "research-state"):
            if not str(record.get(key) or "").strip():
                raise AssertionError(f"ACCEPTANCE.md §2: {slot} is missing {key}")
        mapping[slot] = record.get("skill")
    return mapping


def _slot_by_id(block: dict, slot_id: str) -> dict:
    return m1_slot(block, slot_id)


def _artifact_identity_problems(slot: dict) -> list[str]:
    problems = []
    case_ids = {case.get("case-id") for case in _slot_cases(slot)}
    artifacts = slot.get("artifacts")
    if not isinstance(artifacts, list):
        return [f"{slot.get('slot')}: artifacts must be a list"]
    seen_ids = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            problems.append(f"{slot.get('slot')}: artifact must be an object")
            continue
        artifact_id = artifact.get("artifact-id")
        extra = sorted(set(artifact) - ARTIFACT_KEYS)
        missing = sorted(ARTIFACT_KEYS - set(artifact))
        if extra:
            problems.append(f"artifact {artifact_id!r}: keys not allowed: {extra}")
        if missing:
            problems.append(f"artifact {artifact_id!r}: keys missing: {missing}")
        if not str(artifact_id or "").strip():
            problems.append(f"{slot.get('slot')}: artifact-id is required")
        elif artifact_id in seen_ids:
            problems.append(f"{slot.get('slot')}: duplicate artifact-id {artifact_id!r}")
        seen_ids.add(artifact_id)
        if artifact.get("kind") not in M1_ARTIFACT_KINDS:
            problems.append(f"artifact {artifact_id!r}: kind is not allowed: {artifact.get('kind')!r}")
        if artifact.get("case-id") not in case_ids:
            problems.append(f"{slot.get('slot')}: artifact {artifact_id!r} case-id misses a slot case")
        for key in ("path", "sha256", "generated-by"):
            value = artifact.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"artifact {artifact_id!r}: {key} must be a non-empty string")
        size = artifact.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            problems.append(f"artifact {artifact_id!r}: bytes must be a non-negative integer")
        if not isinstance(artifact.get("meta"), dict):
            problems.append(f"artifact {artifact_id!r}: meta must be an object")
        structural = artifact.get("structural")
        if not isinstance(structural, dict):
            problems.append(f"artifact {artifact_id!r}: structural must be an object")
        else:
            extra = sorted(set(structural) - STRUCTURAL_KEYS)
            missing = sorted(STRUCTURAL_KEYS - set(structural))
            if extra:
                problems.append(f"artifact {artifact_id!r}: structural keys not allowed: {extra}")
            if missing:
                problems.append(f"artifact {artifact_id!r}: structural keys missing: {missing}")
            if structural.get("type") not in ("docx", "xlsx", "zip", "markdown"):
                problems.append(f"artifact {artifact_id!r}: structural.type is not allowed")
            if not isinstance(structural.get("ok"), bool):
                problems.append(f"artifact {artifact_id!r}: structural.ok must be boolean")
            if not isinstance(structural.get("detail"), str):
                problems.append(f"artifact {artifact_id!r}: structural.detail must be a string")
        open_check = artifact.get("open-check")
        if not isinstance(open_check, dict):
            problems.append(f"artifact {artifact_id!r}: open-check must be an object")
        else:
            extra = sorted(set(open_check) - OPEN_CHECK_KEYS)
            missing = sorted(OPEN_CHECK_KEYS - set(open_check))
            if extra:
                problems.append(f"artifact {artifact_id!r}: open-check keys not allowed: {extra}")
            if missing:
                problems.append(f"artifact {artifact_id!r}: open-check keys missing: {missing}")
            for key in ("host", "at"):
                if not str(open_check.get(key) or "").strip():
                    problems.append(f"artifact {artifact_id!r}: open-check.{key} is required")
            if open_check.get("result") not in M1_OPEN_RESULTS:
                problems.append(f"artifact {artifact_id!r}: open-check.result is not allowed")
        deviations = artifact.get("deviations")
        if not isinstance(deviations, list):
            problems.append(f"artifact {artifact_id!r}: deviations must be a list")
            continue
        for index, deviation in enumerate(deviations):
            if not isinstance(deviation, dict):
                problems.append(f"artifact {artifact_id!r}: deviations[{index}] must be an object")
                continue
            extra = sorted(set(deviation) - set(DEVIATION_KEYS))
            missing = sorted(set(DEVIATION_KEYS) - set(deviation))
            if extra:
                problems.append(f"artifact {artifact_id!r}: deviations[{index}] keys not allowed: {extra}")
            if missing:
                problems.append(f"artifact {artifact_id!r}: deviations[{index}] keys missing: {missing}")
            for key in DEVIATION_KEYS:
                if not str(deviation.get(key) or "").strip():
                    problems.append(f"artifact {artifact_id!r}: deviations[{index}].{key} is required")
    return problems


def _case_identity_problems(slot: dict) -> list[str]:
    problems = []
    seen = set()
    for case in _slot_cases(slot):
        case_id = case.get("case-id")
        if not str(case_id or "").strip():
            problems.append(f"{slot.get('slot')}: case-id is required")
        elif case_id in seen:
            problems.append(f"{slot.get('slot')}: duplicate case-id {case_id!r}")
        seen.add(case_id)
        if case.get("result") not in ("待测", "通过", "不通过", "需重测"):
            problems.append(f"case {case_id!r}: result is not one of the four states")
        try:
            path, digest = split_evidence_ref(case.get("session-record"))
        except AssertionError as exc:
            problems.append(f"case {case_id!r}.session-record: {exc}")
            continue
        if case.get("session-record") and (not path.is_file() or sha256_file(path) != digest):
            problems.append(f"case {case_id!r}.session-record: file missing or sha256 mismatch")
    return problems


def _top_level_problems(block: dict) -> list[str]:
    keys = {
        "schema-version",
        "cr",
        "recorded-at",
        "package-version",
        "skill-source-head",
        "prerequisites",
        "slots",
    }
    problems = []
    extra = sorted(set(block) - keys)
    missing = sorted(keys - set(block))
    if extra:
        problems.append(f"m1-research keys not allowed: {extra}")
    if missing:
        problems.append(f"m1-research keys missing: {missing}")
    if block.get("schema-version") != M1_SCHEMA_VERSION:
        problems.append("schema-version must be 1")
    if block.get("cr") != M1_CR:
        problems.append(f"cr must be {M1_CR!r}")
    try:
        recorded_at = datetime.datetime.fromisoformat(block.get("recorded-at", ""))
    except (TypeError, ValueError):
        problems.append("recorded-at must be an ISO8601 timestamp")
    else:
        if recorded_at.tzinfo is None:
            problems.append("recorded-at must carry a timezone")
    head = block.get("skill-source-head")
    if not isinstance(head, str) or not re.match(r"^[0-9a-f]{40}$", head):
        problems.append("skill-source-head must be a 40-char SHA")
    manifest = json.loads((_support.EXP / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if block.get("package-version") != manifest.get("version"):
        problems.append("package-version must match .codebuddy-plugin/plugin.json")
    prerequisites = block.get("prerequisites")
    if not isinstance(prerequisites, dict):
        problems.append("prerequisites must be an object")
        return problems
    expected = {
        "cr1": {"status", "accepted", "evidence-ref", "checked-at", "checked-by"},
        "cr2": {"status", "accepted", "evidence-ref", "checked-at", "checked-by"},
        "existing-model": {"status", "accepted", "rights-evidence-ref", "baseline-sha256", "checked-at"},
    }
    if set(prerequisites) != set(expected):
        problems.append(f"prerequisites keys must be {sorted(expected)}")
    for name, allowed in expected.items():
        item = prerequisites.get(name)
        if not isinstance(item, dict):
            problems.append(f"prerequisites.{name} must be an object")
            continue
        if set(item) != allowed:
            problems.append(f"prerequisites.{name} keys must be {sorted(allowed)}")
        for key, value in item.items():
            if key == "accepted":
                if not isinstance(value, bool):
                    problems.append(f"prerequisites.{name}.accepted must be boolean")
            elif not isinstance(value, str):
                problems.append(f"prerequisites.{name}.{key} must be a string")
    return problems


def _evidence_ref_problems(ref: object, label: str) -> list[str]:
    try:
        path, digest = split_evidence_ref(ref)
    except AssertionError as exc:
        return [f"{label}: {exc}"]
    if not path.is_file():
        return [f"{label}: referenced file is missing"]
    if sha256_file(path) != digest:
        return [f"{label}: sha256 does not match the referenced file"]
    return []


def _cross_session_shape_problems(record: object) -> list[str]:
    """TASK-01 §6 cross-session key/ref/hash/stage contract for any non-null record."""
    if not isinstance(record, dict):
        return ["cross-session must be an object or null"]
    problems = []
    extra = sorted(set(record) - CROSS_SESSION_KEYS)
    missing = sorted(CROSS_SESSION_KEYS - set(record))
    if extra:
        problems.append(f"cross-session keys not allowed: {extra}")
    if missing:
        problems.append(f"cross-session keys missing: {missing}")
    for key in ("reentry-id", "exit-at", "reentry-at", "stage-located", "confirmation", "final-artifact"):
        if not str(record.get(key) or "").strip():
            problems.append(f"cross-session.{key} is required")
    if not re.match(r"^Task [2-5]$", str(record.get("stage-located") or "")):
        problems.append(f"cross-session.stage-located must be Task 2..5, got {record.get('stage-located')!r}")
    exit_at = reentry_at = None
    for key in ("exit-at", "reentry-at"):
        try:
            parsed = datetime.datetime.fromisoformat(str(record.get(key) or ""))
        except ValueError:
            problems.append(f"cross-session.{key} must be an ISO8601 timestamp")
            continue
        if parsed.tzinfo is None:
            problems.append(f"cross-session.{key} must carry a timezone")
        elif key == "exit-at":
            exit_at = parsed
        else:
            reentry_at = parsed
    if exit_at is not None and reentry_at is not None and not reentry_at > exit_at:
        problems.append("cross-session.reentry-at must be after exit-at")
    provided = record.get("provided-artifacts")
    if not isinstance(provided, list) or not provided:
        problems.append("cross-session.provided-artifacts must be a non-empty list")
        provided = []
    for index, ref in enumerate(provided):
        problems += _evidence_ref_problems(ref, f"cross-session.provided-artifacts[{index}]")
    problems += _evidence_ref_problems(record.get("final-artifact"), "cross-session.final-artifact")
    return problems


def _slot_shape_problems(slot: dict) -> list[str]:
    keys = {
        "slot",
        "acceptance-slot",
        "skill",
        "research-state",
        "adjudicator",
        "adjudicated-at",
        "rationale",
        "positive-cases",
        "negative-cases",
        "quality-checklist",
        "artifacts",
        "cross-session",
        "replay",
        "skill-change",
    }
    problems = []
    extra = sorted(set(slot) - keys)
    missing = sorted(keys - set(slot))
    if extra:
        problems.append(f"{slot.get('slot')} keys not allowed: {extra}")
    if missing:
        problems.append(f"{slot.get('slot')} keys missing: {missing}")
    if slot.get("research-state") not in ("待测", "通过", "不通过", "需重测"):
        problems.append(f"{slot.get('slot')}: research-state is not one of the four states")
    for key in ("positive-cases", "negative-cases", "quality-checklist", "artifacts", "replay"):
        if not isinstance(slot.get(key), list):
            problems.append(f"{slot.get('slot')}.{key} must be a list")
    record = slot.get("cross-session")
    if record is not None:
        problems += _cross_session_shape_problems(record)
    return problems


def _manifest_version(before: str, after: str, expected: str | None = None) -> list[str]:
    problems = []
    try:
        old = json.loads(before)
        new = json.loads(after)
    except json.JSONDecodeError as exc:
        return [f"plugin.json is not valid JSON: {exc}"]
    if not isinstance(old, dict) or not isinstance(new, dict):
        return ["plugin.json must contain an object"]
    old_version = old.pop("version", None)
    new_version = new.pop("version", None)
    if old != new:
        problems.append("only the top-level version may change in plugin.json")
    pattern = VERSION_RE
    if not isinstance(old_version, str) or not pattern.match(old_version):
        problems.append(f"old plugin version is not three non-negative integers: {old_version!r}")
    if not isinstance(new_version, str) or not pattern.match(new_version):
        problems.append(f"new plugin version is not three non-negative integers: {new_version!r}")
    if isinstance(old_version, str) and isinstance(new_version, str) and pattern.match(old_version) and pattern.match(new_version):
        if tuple(map(int, new_version.split("."))) <= tuple(map(int, old_version.split("."))):
            problems.append("plugin version must strictly increase")
    if not isinstance(expected, str) or not pattern.match(expected):
        problems.append(f"versions must register a three-part version for this plugin.json, got {expected!r}")
    elif isinstance(new_version, str) and new_version != expected:
        problems.append(f"plugin version {new_version!r} must equal the versions record {expected!r}")
    return problems


def _readme_identity(text: str) -> dict[str, tuple[str, ...]]:
    identity = {}
    for match in re.finditer(r"```yaml\nrow: (MR-\d\d)\n(.*?)```", text, re.DOTALL):
        row = match.group(1)
        body = parse_yaml_subset(match.group(2))
        identity[row] = (
            body.get("row"),
            body.get("command"),
            body.get("skill"),
            ",".join(body.get("source-files") or []),
        )
    table = {}
    for match in re.finditer(r"^\| (\d) \| `(/[a-z-]+)` \| `([a-z-]+)` \|.*\|$", text, re.M):
        table[match.group(3)] = (match.group(1), match.group(2))
    for skill, (_, command) in table.items():
        row = SKILL_ROWS.get(skill)
        if row and row in identity:
            identity[row] = identity[row] + (command,)
    return identity


def _readme_masked(text: str, affected: set[str]) -> str:
    masked = text
    rows = {SKILL_ROWS[skill] for skill in affected if skill in SKILL_ROWS}
    for row in rows:
        masked = re.sub(
            rf"```yaml\nrow: {row}\n.*?```",
            f"```yaml\nrow: {row}\n<SENTINEL>\n```",
            masked,
            flags=re.DOTALL,
        )
    lines = []
    for line in masked.split("\n"):
        match = re.match(r"^\| (\d) \| `(/[a-z-]+)` \| `([a-z-]+)` \|.*\|$", line)
        if match and match.group(3) in affected:
            lines.append(f"| {match.group(1)} | `{match.group(2)}` | `{match.group(3)}` |<SENTINEL>|")
        else:
            lines.append(line)
    return "\n".join(lines)


def _readme_problems(before: str, after: str, affected: set[str]) -> list[str]:
    problems = []
    identity_before = _readme_identity(before)
    identity_after = _readme_identity(after)
    for skill in affected:
        row = SKILL_ROWS.get(skill)
        if row is None:
            problems.append(f"README: no mapping row for affected skill {skill!r}")
        elif identity_before.get(row) != identity_after.get(row):
            problems.append(f"README: {row} identity (row/command/skill/source-files) changed")
    if _readme_masked(before, affected) != _readme_masked(after, affected):
        problems.append("README: changes outside the affected MR row/YAML body")
    return problems


COMMAND_FILES = {
    "earnings-analysis": "earnings.md",
    "model-update": "model-update.md",
    "initiating-coverage": "initiate.md",
}


CUSTOM_PATH_RE = re.compile(r"(?:baseline/[^:\s|`]+:)?((?:plugins|workbuddy-experts|scripts)/[^\s|`（）()]+)")


def _custom_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in text.split("\n"):
        if not line.startswith("| WB-CUSTOM-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        rows[cells[0]] = cells
    return rows


def _custom_row_paths(cells: list[str]) -> set[str]:
    """Repository paths a WB-CUSTOM row names (files, or directories ending with '/')."""
    paths = set()
    for cell in cells:
        for match in CUSTOM_PATH_RE.finditer(cell):
            paths.add(match.group(1))
    return paths


def _custom_path_registered(path: str, allowed_paths: set[str]) -> bool:
    if path in allowed_paths:
        return True
    if path.endswith("/"):
        return any(entry.startswith(path) for entry in allowed_paths)
    return False


def _custom_is_target(cells: list[str], allowed_paths: set[str]) -> bool:
    return any(_custom_path_registered(path, allowed_paths) for path in _custom_row_paths(cells))


def _custom_stripped(text: str, allowed_paths: set[str]) -> str:
    out = []
    for line in text.split("\n"):
        if line.startswith("| WB-CUSTOM-"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 6 and _custom_is_target(cells, allowed_paths):
                out.append(cells[0] + "|<MASKED>")
                continue
        out.append(line)
    return "\n".join(out)


def _custom_problems(before: str, after: str, allowed_paths: set[str]) -> list[str]:
    if not allowed_paths:
        return ["CUSTOM.md: no registered source-paths/copy-paths authorize any WB-CUSTOM row"]
    old_rows = _custom_rows(before)
    new_rows = _custom_rows(after)
    if set(old_rows) != set(new_rows):
        return ["CUSTOM.md: WB-CUSTOM rows were added or removed"]
    problems = []
    for row_id in old_rows:
        old_cells = old_rows[row_id]
        new_cells = new_rows[row_id]
        if len(old_cells) != len(new_cells):
            problems.append(f"CUSTOM.md: {row_id} column count changed")
            continue
        targeted = _custom_is_target(old_cells, allowed_paths) or _custom_is_target(new_cells, allowed_paths)
        if targeted:
            unregistered = sorted(
                {
                    path
                    for path in _custom_row_paths(old_cells) | _custom_row_paths(new_cells)
                    if not _custom_path_registered(path, allowed_paths)
                }
            )
            if unregistered:
                problems.append(
                    f"CUSTOM.md: {row_id} names paths outside the registered source-paths/copy-paths: {unregistered}"
                )
            if old_cells[0:3] != new_cells[0:3] or old_cells[4] != new_cells[4]:
                problems.append(f"CUSTOM.md: {row_id} stable cells changed")
        elif old_cells != new_cells:
            problems.append(f"CUSTOM.md: unrelated row {row_id} changed")
    if problems:
        return problems
    if _custom_stripped(before, allowed_paths) != _custom_stripped(after, allowed_paths):
        return ["CUSTOM.md: changes outside the permitted WB-CUSTOM cells"]
    return []


def conditional_content_problems(
    path: str,
    before: str,
    after: str,
    affected_skills: set[str],
    versions: dict | None = None,
    paths: set[str] | None = None,
) -> list[str]:
    """Second scope layer: what a conditional file is allowed to change in content."""
    name = path.replace("\\", "/")
    if name in PLUGIN_MANIFESTS:
        registered = versions if isinstance(versions, dict) else {}
        return _manifest_version(before, after, registered.get(name))
    if name == "workbuddy-experts/equity-research/README.md":
        return _readme_problems(before, after, affected_skills)
    if name == "CUSTOM.md":
        return _custom_problems(before, after, set(paths or ()))
    skills = skills_for_path(name)
    if not skills:
        return [f"{name}: conditional path has no content rule"]
    unauthorized = sorted(skills - affected_skills)
    if unauthorized:
        return [f"{name}: skill change is not authorized for {', '.join(unauthorized)}"]
    return []


def skills_for_path(path: str) -> set[str]:
    mapping = (
        ("plugins/vertical-plugins/equity-research/skills/earnings-analysis/", "earnings-analysis"),
        ("plugins/vertical-plugins/equity-research/skills/model-update/", "model-update"),
        ("plugins/vertical-plugins/equity-research/skills/initiating-coverage/", "initiating-coverage"),
        ("plugins/vertical-plugins/equity-research/commands/earnings.md", "earnings-analysis"),
        ("plugins/vertical-plugins/equity-research/commands/model-update.md", "model-update"),
        ("plugins/vertical-plugins/equity-research/commands/initiate.md", "initiating-coverage"),
        ("plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/", "earnings-analysis"),
        ("plugins/agent-plugins/earnings-reviewer/skills/model-update/", "model-update"),
    )
    hits = {skill for prefix, skill in mapping if path == prefix or path.startswith(prefix)}
    if hits:
        return hits
    shared = (
        "plugins/vertical-plugins/equity-research/.claude-plugin/plugin.json",
        "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json",
        "workbuddy-experts/equity-research/.codebuddy-plugin/plugin.json",
        "workbuddy-experts/equity-research/README.md",
        "CUSTOM.md",
    )
    if path in shared:
        return {"earnings-analysis", "model-update", "initiating-coverage"}
    return set()


def _skill_change_path_registered(path: str, record: dict) -> bool:
    """A changed conditional path must be registered by the same slot's skill-change record."""
    source_paths = set(record.get("source-paths") or [])
    copy_paths = set(record.get("copy-paths") or [])
    if path in source_paths or path in copy_paths:
        return True
    versions = record.get("versions") if isinstance(record.get("versions"), dict) else {}
    if path in PLUGIN_MANIFESTS:
        return bool(str(versions.get(path) or "").strip())
    if path == "CUSTOM.md":
        return bool(str(record.get("wb-custom") or "").strip())
    if path == "workbuddy-experts/equity-research/README.md":
        return True
    return False


def scope_problems(changed: list[str], block: dict) -> list[str]:
    """Path/trigger layer of SDD §9; the content layer runs separately."""
    problems = []
    changed_records = []
    for slot in block.get("slots") or []:
        if not isinstance(slot, dict):
            continue
        record = slot.get("skill-change")
        if isinstance(record, dict) and record.get("changed") is True:
            changed_records.append((slot, record))
    for path in changed:
        if path in M1_ZERO_DIFF_PATHS or path.startswith(M1_ZERO_DIFF_PREFIXES) or path.startswith("out/"):
            problems.append(f"{path}: zero_diff path must not change")
            continue
        if path in M1_SCOPE_EXACT_FILES:
            continue
        if not any(path == prefix or path.startswith(prefix) for prefix in M1_SCOPE_CONDITIONAL_PREFIXES):
            problems.append(f"{path}: outside the SDD §9 scope_in")
            continue
        skills = skills_for_path(path)
        accepted = False
        for slot, record in changed_records:
            if slot.get("skill") not in skills:
                continue
            case_ids = {case.get("case-id") for case in _slot_cases(slot)}
            if record.get("case-id") not in case_ids:
                continue
            if not _skill_change_path_registered(path, record):
                continue
            accepted = True
            break
        if not accepted:
            problems.append(
                f"{path}: conditional path needs the same slot's skill-change.changed=true with a real case-id "
                "and path-level registration (source-paths/copy-paths, plugin.json version, CUSTOM row, README row)"
            )
    return problems


def _git_envelope(args: list[str]) -> str:
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        raise AssertionError("node is required to run the controlled-shell adapter")
    cmd = [
        node,
        str(crctl_mjs()),
        "git",
        *args,
        "--json",
        "--cwd",
        str(ROOT),
        "--workspace",
        str(crctl_workspace()),
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT)
    )
    if proc.returncode != 0:
        raise AssertionError(f"controlled git {args} failed: {proc.stderr.strip()[:400]}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"controlled git {args}: envelope is not JSON: {exc}") from exc
    if payload.get("ok") is not True:
        raise AssertionError(f"controlled git {args}: envelope reported failure")
    return payload.get("stdout") or ""


def controlled_diff(path: str, context: int) -> str:
    """Raw stdout of `crctl git diff`, consumed only after ok=true (plan §6 B-04)."""
    return _git_envelope(["diff", f"--unified={context}", M1_BASE_SHA, "--", path])


def changed_paths() -> list[str]:
    return [line.strip() for line in _git_envelope(["diff", "--name-only", M1_BASE_SHA]).splitlines() if line.strip()]


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$", re.M)


def acceptance_append_problems(diff_text: str, before: str, after: str) -> list[str]:
    """§6 must be a pure append after line 282 (blank line + title + machine block)."""
    problems = []
    hunks = list(HUNK_RE.finditer(diff_text))
    if len(hunks) != 1:
        return [f"ACCEPTANCE diff must contain exactly one hunk, found {len(hunks)}"]
    header = hunks[0]
    old_start = int(header.group(1))
    old_count = int(header.group(2) or 1)
    new_start = int(header.group(3))
    new_count = int(header.group(4) or 1)
    if (old_start, old_count) != (BASELINE_ACCEPTANCE_LINES, 0):
        problems.append(f"ACCEPTANCE hunk must append after line 282, got -{old_start},{old_count}")
    if new_start != BASELINE_ACCEPTANCE_LINES + 1:
        problems.append(f"ACCEPTANCE hunk must start the new content at line 283, got +{new_start}")
    added = []
    for line in diff_text[header.end():].split("\n"):
        if not line:
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-") or line.startswith(" "):
            problems.append("ACCEPTANCE §6 may only be appended; no old line may change")
    if problems:
        return problems
    if len(added) != new_count:
        problems.append(f"ACCEPTANCE hunk new_count {new_count} does not match {len(added)} added lines")
    if before + "".join(f"{line}\n" for line in added) != after:
        problems.append("ACCEPTANCE after-state is not the baseline plus the appended lines")
    if added[:2] != ["", APPEND_TITLE]:
        problems.append("ACCEPTANCE append must start with a blank line then the §6 heading")
    return problems


def full_context_pair(diff_text: str, current: str) -> tuple[str, str]:
    """Reconstruct before/after from a `--unified=999999` single-file, single-hunk diff."""
    if not diff_text.strip():
        return current, current
    hunks = list(HUNK_RE.finditer(diff_text))
    if len(hunks) != 1:
        raise AssertionError(f"full-context diff must contain exactly one hunk, found {len(hunks)}")
    header = hunks[0]
    if int(header.group(1)) != 1 or int(header.group(3)) != 1:
        raise AssertionError("full-context diff must start at old/new line 1")
    old_lines: list[str] = []
    new_lines: list[str] = []
    no_newline_old = no_newline_new = False
    for line in diff_text[header.end():].split("\n"):
        if not line:
            continue
        if line.startswith("\\ No newline at end of file"):
            if new_lines and not no_newline_new:
                no_newline_new = True
            elif old_lines:
                no_newline_old = True
            continue
        if line.startswith(" "):
            old_lines.append(line[1:])
            new_lines.append(line[1:])
        elif line.startswith("-"):
            old_lines.append(line[1:])
        elif line.startswith("+"):
            new_lines.append(line[1:])
    before = "\n".join(old_lines) + ("" if no_newline_old else "\n")
    after = "\n".join(new_lines) + ("" if no_newline_new else "\n")
    if int(header.group(2) or 1) != len(old_lines) or int(header.group(4) or 1) != len(new_lines):
        raise AssertionError("full-context diff hunk counts do not match its body")
    if after != current:
        raise AssertionError("full-context diff after-state does not match the current file")
    return before, after


class ContractSelfChecks(unittest.TestCase):
    """Every gate is exercised against temporary files, never real evidence."""

    def test_sha256_file_known_vector(self) -> None:
        with temp_root() as root:
            path = root / "out" / "abc.bin"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"abc")
            self.assertEqual(
                sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )
            with self.assertRaises(AssertionError):
                sha256_file(root / "out" / "missing.bin")

    def test_read_json_block_accepts_and_rejects(self) -> None:
        with temp_root() as root:
            good = root / "doc.md"
            good.write_text(
                "<!-- m1-research:start -->\n```json\n{\"a\": 1}\n```\n<!-- m1-research:end -->\n",
                encoding="utf-8",
            )
            self.assertEqual(read_json_block(good, "m1-research"), {"a": 1})
            bad = root / "bad.md"
            bad.write_text(
                "<!-- m1-research:start -->\n```json\n{not json}\n```\n<!-- m1-research:end -->\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssertionError) as ctx:
                read_json_block(bad, "m1-research")
            self.assertIn("m1-research", str(ctx.exception))

    def test_case_whitelist_rejects_restricted_bodies(self) -> None:
        case = {key: "x" for key in M1_POSITIVE_CASE_KEYS}
        case["input-summary"] = "短摘要"
        case["response-summary"] = "短摘要"
        self.assertEqual(case_problems(case, M1_POSITIVE_CASE_KEYS), [])
        self.assertTrue(case_problems({**case, "prompt": "逐字输入"}, M1_POSITIVE_CASE_KEYS))
        self.assertTrue(case_problems({**case, "response": "逐字响应"}, M1_POSITIVE_CASE_KEYS))
        self.assertTrue(
            case_problems({**case, "response-summary": "x" * (M1_CASE_SUMMARY_LIMIT + 1)}, M1_POSITIVE_CASE_KEYS)
        )
        self.assertTrue(case_problems({**case, "input-summary": "C:\\Users\\GOBAO\\secret.txt"}, M1_POSITIVE_CASE_KEYS))
        self.assertTrue(case_problems({**case, "response-summary": "api_key: abc123"}, M1_POSITIVE_CASE_KEYS))

    def test_evidence_references_and_standalone_paths(self) -> None:
        with temp_root() as root:
            ref = write_evidence(root, "out/evidence/m1/sessions/case.json", b'{"ok": true}')
            path, digest = split_evidence_ref(ref)
            self.assertEqual(sha256_file(path), digest)
            for bad in (
                "evidence/m1/sessions/case.json::" + "a" * 64,
                "out\\evidence\\case.json::" + "a" * 64,
                "C:/Users/GOBAO/out/case.json::" + "a" * 64,
                "out/evidence/case.json::" + "A" * 64,
                "out/../secret.json::" + "a" * 64,
                "out/evidence/case.json",
            ):
                with self.assertRaises(AssertionError, msg=bad):
                    split_evidence_ref(bad)
            artifact = {
                "artifact-id": "A-1",
                "case-id": "M1-01-P1",
                "kind": "SUMMARY",
                "path": "out/evidence/m1/artifacts/case/summary.md",
                "sha256": hashlib.sha256(b"summary").hexdigest(),
                "bytes": len(b"summary"),
            }
            (root / artifact["path"]).parent.mkdir(parents=True, exist_ok=True)
            (root / artifact["path"]).write_bytes(b"summary")
            self.assertEqual(artifact_file_problems(artifact), [])
            self.assertTrue(artifact_file_problems({**artifact, "sha256": "b" * 64}))
            self.assertTrue(artifact_file_problems({**artifact, "path": "out/../secret.md"}))
            self.assertTrue(artifact_file_problems({**artifact, "bytes": 1}))

    def test_readiness_develop_and_collect(self) -> None:
        skeleton = {"slots": [{"slot": "M1-01", "research-state": "待测", "positive-cases": [], "negative-cases": [], "artifacts": []}]}
        self.assertEqual(m1_readiness_problems(skeleton, "develop"), [])
        self.assertTrue(m1_readiness_problems(skeleton, "collect"))
        self.assertTrue(m1_readiness_problems(skeleton, "unknown"))
        with temp_root() as root:
            ref1 = write_evidence(root, "out/evidence/m1/prereq/cr1.json", b'{"accepted": true}')
            ref2 = write_evidence(root, "out/evidence/m1/prereq/cr2.json", b'{"accepted": true}')
            rights = write_evidence(root, "out/evidence/m1/prereq/rights.json", b'{"model": "ok"}')
            ready = {
                "prerequisites": {
                    "cr1": {
                        "status": "accepted",
                        "accepted": True,
                        "evidence-ref": ref1,
                        "checked-at": "2026-10-17T10:00:00+08:00",
                        "checked-by": "Ray",
                    },
                    "cr2": {
                        "status": "accepted",
                        "accepted": True,
                        "evidence-ref": ref2,
                        "checked-at": "2026-10-17T10:00:00+08:00",
                        "checked-by": "Ray",
                    },
                    "existing-model": {
                        "status": "accepted",
                        "accepted": True,
                        "rights-evidence-ref": rights,
                        "baseline-sha256": "c" * 64,
                        "checked-at": "2026-10-17T10:00:00+08:00",
                    },
                },
                "slots": skeleton["slots"],
            }
            self.assertEqual(m1_readiness_problems(ready, "collect"), [])
            registered = {
                "slots": [{"slot": "M1-01", "research-state": "待测", "positive-cases": [{"case-id": "c"}], "negative-cases": [], "artifacts": []}],
                "prerequisites": skeleton.get("prerequisites", {}),
            }
            self.assertTrue(m1_readiness_problems(registered, "develop"))
            broken = json.loads(json.dumps(ready))
            broken["prerequisites"]["cr1"]["evidence-ref"] = "out/evidence/m1/prereq/cr1.json::" + "d" * 64
            self.assertTrue(m1_readiness_problems(broken, "collect"))
            dangling = json.loads(json.dumps(ready))
            dangling["prerequisites"]["cr2"]["evidence-ref"] = "out/evidence/m1/prereq/missing.json::" + "e" * 64
            self.assertTrue(m1_readiness_problems(dangling, "collect"))

    def test_tool_record_two_branches(self) -> None:
        with temp_root() as root:
            payload = root / "out" / "evidence" / "m1" / "artifacts" / "case" / "report.docx"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b"docx-bytes")
            digest = sha256_file(payload)
            artifact = {
                "artifact-id": "A-1",
                "case-id": "M1-01-P1",
                "kind": "DOCX",
                "path": "out/evidence/m1/artifacts/case/report.docx",
                "sha256": digest,
                "bytes": payload.stat().st_size,
                "generated-by": "tencent-docx|1.2.0|tencent-docx",
                "meta": {"schema-query": "docx.create", "tool-result": "成功"},
                "deviations": [],
            }
            self.assertEqual(m1_tool_record_problems(artifact, ("tencent-docx",)), [])
            self.assertTrue(m1_tool_record_problems(artifact, ("host-preview",)))
            missing_query = json.loads(json.dumps(artifact))
            missing_query["meta"].pop("schema-query")
            self.assertTrue(m1_tool_record_problems(missing_query, ("tencent-docx",)))

            adjudication = write_evidence(
                root,
                "out/evidence/m1/adjudications/case-a1.json",
                json.dumps(
                    {
                        "adjudicator": "Ray",
                        "decision": "批准最小替代",
                        "case-id": "M1-01-P1",
                        "artifact-id": "A-1",
                        "actual": "minimal-editor|2.0|local-office-edit",
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
            )
            retest = write_evidence(
                root,
                "out/evidence/m1/retests/case-a1.json",
                json.dumps(
                    {
                        "case-id": "M1-01-P1",
                        "artifact-id": "A-1",
                        "kind": "DOCX",
                        "path": artifact["path"],
                        "sha256": digest,
                        "generated-by": "minimal-editor|2.0|local-office-edit",
                        "result": "成功",
                        "open-check-result": "成功",
                        "checked-at": "2026-10-17T10:00:00+08:00",
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
            )
            unsupported = {
                **artifact,
                "generated-by": "minimal-editor|2.0|local-office-edit",
                "meta": {
                    "schema-query": "docx.create",
                    "tool-result": "不支持",
                    "unsupported-generated-by": "tencent-docx|1.2.0|tencent-docx",
                    "retest": retest,
                },
                "deviations": [
                    {
                        "requirement": "DOCX 优先走 tencent-docx",
                        "actual": "minimal-editor|2.0|local-office-edit",
                        "reason": "目标版本无该路由",
                        "adjudication-ref": adjudication,
                    }
                ],
            }
            self.assertEqual(m1_tool_record_problems(unsupported, ("tencent-docx",)), [])
            missing_retest = json.loads(json.dumps(unsupported))
            missing_retest["meta"]["retest"] = "out/evidence/m1/retests/missing.json::" + "f" * 64
            self.assertTrue(m1_tool_record_problems(missing_retest, ("tencent-docx",)))
            bad_hash = json.loads(json.dumps(unsupported))
            bad_hash["meta"]["retest"] = unsupported["meta"]["retest"].rsplit("::", 1)[0] + "::" + "a" * 64
            self.assertTrue(m1_tool_record_problems(bad_hash, ("tencent-docx",)))
            failed = json.loads(json.dumps(unsupported))
            failed_record = json.loads((root / retest.rsplit("::", 1)[0]).read_text(encoding="utf-8"))
            failed_record["result"] = "失败"
            failed_path = root / "out" / "evidence" / "m1" / "retests" / "failed.json"
            failed_path.write_text(json.dumps(failed_record, ensure_ascii=False), encoding="utf-8")
            failed["meta"]["retest"] = f"out/evidence/m1/retests/failed.json::{sha256_file(failed_path)}"
            self.assertTrue(m1_tool_record_problems(failed, ("tencent-docx",)))
            wrong_binding = json.loads(json.dumps(unsupported))
            wrong_binding["artifact-id"] = "A-2"
            self.assertTrue(m1_tool_record_problems(wrong_binding, ("tencent-docx",)))
            no_adjudication = json.loads(json.dumps(unsupported))
            no_adjudication["deviations"][0]["adjudication-ref"] = "out/evidence/m1/adjudications/missing.json::" + "b" * 64
            self.assertTrue(m1_tool_record_problems(no_adjudication, ("tencent-docx",)))

    def test_replay_requires_a_registered_new_revision(self) -> None:
        with temp_root() as root:
            original = write_evidence(root, "out/evidence/m1/artifacts/case/report.docx", b"original")
            revised = write_evidence(root, "out/evidence/m1/artifacts/case/report-rev2.docx", b"revised")
            original_pair = {"path": original.rsplit("::", 1)[0], "sha256": original.rsplit("::", 1)[1]}
            revised_pair = {"path": revised.rsplit("::", 1)[0], "sha256": revised.rsplit("::", 1)[1]}
            slot = {
                "artifacts": [
                    {"artifact-id": "A-1", "case-id": "M1-01-P1", "kind": "DOCX", **original_pair},
                    {"artifact-id": "A-2", "case-id": "M1-01-P1", "kind": "DOCX", **revised_pair},
                ],
                "replay": [
                    {
                        "replay-key": "k1",
                        "replay-decision": "reuse",
                        "diff-summary": "same key",
                        "confirmation": "user confirmed",
                        "artifact-ref": original,
                    }
                ],
            }
            self.assertEqual(replay_problems(slot), [])
            for decision in ("redo", "revision"):
                item = {
                    "replay-key": "k2",
                    "replay-decision": decision,
                    "diff-summary": "diff",
                    "confirmation": "confirmation",
                    "artifact-ref": revised,
                }
                self.assertEqual(replay_problems({**slot, "replay": slot["replay"] + [item]}), [])
            overwrite = {
                "replay-key": "k3",
                "replay-decision": "redo",
                "diff-summary": "diff",
                "confirmation": "confirmation",
                "artifact-ref": original,
            }
            self.assertTrue(replay_problems({**slot, "replay": slot["replay"] + [overwrite]}))
            unregistered = write_evidence(root, "out/evidence/m1/artifacts/case/report-rev3.docx", b"rev3")
            self.assertTrue(
                replay_problems({**slot, "replay": slot["replay"] + [{**overwrite, "artifact-ref": unregistered}]})
            )
            self.assertTrue(
                replay_problems(
                    {**slot, "replay": [{**slot["replay"][0], "artifact-ref": original.replace("::", "")}]}
                )
            )

    def test_artifact_whitelist_is_closed(self) -> None:
        deviation = {"requirement": "r", "actual": "a", "reason": "why", "adjudication-ref": "out/x::" + "b" * 64}
        artifact = {
            "artifact-id": "A-1",
            "case-id": "M1-01-P1",
            "kind": "SUMMARY",
            "path": "out/evidence/m1/artifacts/case/summary.md",
            "sha256": "a" * 64,
            "bytes": 7,
            "generated-by": "host|1|host-preview",
            "open-check": {"host": "workbuddy", "at": "2026-10-17T10:00:00+08:00", "result": "成功"},
            "structural": {"type": "markdown", "ok": True, "detail": ""},
            "meta": {"schema-query": "md", "tool-result": "成功"},
            "deviations": [deviation],
        }
        slot = {
            "slot": "M1-01",
            "positive-cases": [{"case-id": "M1-01-P1"}],
            "negative-cases": [],
            "artifacts": [artifact],
        }
        self.assertEqual(_artifact_identity_problems(slot), [])
        self.assertTrue(_artifact_identity_problems({**slot, "artifacts": [{**artifact, "prompt": "逐字输入"}]}))
        self.assertTrue(_artifact_identity_problems({**slot, "artifacts": [{**artifact, "response": "逐字响应"}]}))
        self.assertTrue(_artifact_identity_problems({**slot, "artifacts": [{**artifact, "kind": "SHEET"}]}))
        missing_key = {key: value for key, value in artifact.items() if key != "meta"}
        self.assertTrue(_artifact_identity_problems({**slot, "artifacts": [missing_key]}))
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "open-check": {**artifact["open-check"], "host": ""}}]}
            )
        )
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "open-check": {**artifact["open-check"], "at": ""}}]}
            )
        )
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "open-check": {**artifact["open-check"], "note": "x"}}]}
            )
        )
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "structural": {"type": "markdown", "ok": True}}]}
            )
        )
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "deviations": [{"requirement": "r", "actual": "a", "reason": "why"}]}]}
            )
        )
        self.assertTrue(
            _artifact_identity_problems(
                {**slot, "artifacts": [{**artifact, "deviations": [{**deviation, "note": "x"}]}]}
            )
        )

    def test_cross_session_shape_is_closed(self) -> None:
        with temp_root() as root:
            provided = write_evidence(root, "out/evidence/m1/artifacts/M1-03-T1/report.md", b"report")
            final = write_evidence(root, "out/evidence/m1/artifacts/M1-03-T5/final.docx", b"final")
            record = {
                "reentry-id": "R1",
                "exit-at": "2026-10-17T10:00:00+08:00",
                "reentry-at": "2026-10-17T11:00:00+08:00",
                "provided-artifacts": [provided],
                "stage-located": "Task 2",
                "confirmation": "用户确认从 Task 2 继续",
                "final-artifact": final,
                "result": "待测",
            }
            self.assertEqual(_cross_session_shape_problems(record), [])
            self.assertTrue(
                _cross_session_shape_problems({key: value for key, value in record.items() if key != "confirmation"})
            )
            self.assertTrue(
                _cross_session_shape_problems(
                    {**record, "provided-artifacts": [provided.rsplit("::", 1)[0] + "::" + "c" * 64]}
                )
            )
            self.assertTrue(
                _cross_session_shape_problems(
                    {**record, "final-artifact": "out/evidence/m1/missing.docx::" + "d" * 64}
                )
            )
            self.assertTrue(_cross_session_shape_problems({**record, "stage-located": "Task 1"}))
            self.assertTrue(_cross_session_shape_problems({**record, "reentry-at": "2026-10-17T09:00:00+08:00"}))

    def test_scope_path_and_trigger_layer(self) -> None:
        block = {
            "slots": [
                {
                    "slot": "M1-01",
                    "skill": "earnings-analysis",
                    "positive-cases": [{"case-id": "M1-01-P1"}],
                    "negative-cases": [],
                    "artifacts": [],
                    "skill-change": {"changed": False},
                },
                {
                    "slot": "M1-02",
                    "skill": "model-update",
                    "positive-cases": [],
                    "negative-cases": [],
                    "artifacts": [],
                    "skill-change": {"changed": False},
                },
                {
                    "slot": "M1-03",
                    "skill": "initiating-coverage",
                    "positive-cases": [],
                    "negative-cases": [],
                    "artifacts": [],
                    "skill-change": {"changed": False},
                },
            ]
        }
        self.assertEqual(scope_problems(list(M1_SCOPE_EXACT_FILES), block), [])
        self.assertEqual(scope_problems(["scripts/check.py"], block)[0][:10], "scripts/ch")
        self.assertTrue(scope_problems(["plugins/vertical-plugins/equity-research/skills/earnings-preview/SKILL.md"], block))
        target = "plugins/vertical-plugins/equity-research/skills/earnings-analysis/SKILL.md"
        command = "plugins/vertical-plugins/equity-research/commands/earnings.md"
        copy = "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/SKILL.md"
        manifest = "plugins/vertical-plugins/equity-research/.claude-plugin/plugin.json"
        self.assertTrue(scope_problems([target], block))
        changed = json.loads(json.dumps(block))
        changed["slots"][0]["skill-change"] = {
            "changed": True,
            "case-id": "M1-01-P1",
            "source-paths": [target, command],
            "copy-paths": [copy],
            "retested-cases": ["M1-01-P1"],
            "versions": {manifest: "0.11.1"},
            "wb-custom": "WB-CUSTOM-01",
        }
        self.assertEqual(
            scope_problems(
                [target, command, copy, manifest, "CUSTOM.md", "workbuddy-experts/equity-research/README.md"],
                changed,
            ),
            [],
        )
        self.assertEqual(skill_change_problems(changed["slots"][0], {}), [])
        omitted = json.loads(json.dumps(changed))
        omitted["slots"][0]["skill-change"]["copy-paths"] = []
        self.assertTrue(scope_problems([copy], omitted))
        wrong_version = json.loads(json.dumps(changed))
        wrong_version["slots"][0]["skill-change"]["versions"] = {
            "plugins/agent-plugins/earnings-reviewer/.claude-plugin/plugin.json": "0.11.1"
        }
        self.assertTrue(scope_problems([manifest], wrong_version))
        wrong_case = json.loads(json.dumps(changed))
        wrong_case["slots"][0]["skill-change"]["case-id"] = "nope"
        self.assertTrue(scope_problems([target], wrong_case))
        bad_version = json.loads(json.dumps(changed["slots"][0]))
        bad_version["skill-change"]["versions"] = {manifest: "0.11"}
        self.assertTrue(skill_change_problems(bad_version, {}))
        unregistered_source = json.loads(json.dumps(changed["slots"][0]))
        unregistered_source["skill-change"]["source-paths"] = ["scripts/check.py"]
        self.assertTrue(skill_change_problems(unregistered_source, {}))
        initiate = {
            "slot": "M1-03",
            "skill": "initiating-coverage",
            "positive-cases": [{"case-id": "M1-03-P1"}],
            "negative-cases": [],
            "skill-change": {
                "changed": True,
                "case-id": "M1-03-P1",
                "source-paths": ["plugins/vertical-plugins/equity-research/skills/initiating-coverage/SKILL.md"],
                "copy-paths": [copy],
                "retested-cases": ["M1-03-P1"],
                "versions": {manifest: "0.11.1"},
                "wb-custom": "WB-CUSTOM-02",
            },
        }
        self.assertTrue(skill_change_problems(initiate, {}))

    def test_conditional_content_layer(self) -> None:
        before_plugin = json.dumps({"name": "pkg", "version": "0.11.0"}, indent=2) + "\n"
        after_plugin = json.dumps({"name": "pkg", "version": "0.11.1"}, indent=2) + "\n"
        path = "plugins/vertical-plugins/equity-research/.claude-plugin/plugin.json"
        self.assertEqual(
            conditional_content_problems(path, before_plugin, after_plugin, {"earnings-analysis"}, {path: "0.11.1"}),
            [],
        )
        self.assertTrue(conditional_content_problems(path, before_plugin, after_plugin, {"earnings-analysis"}))
        self.assertTrue(
            conditional_content_problems(path, before_plugin, after_plugin, {"earnings-analysis"}, {path: "0.11.2"})
        )
        renamed = json.dumps({"name": "other", "version": "0.11.1"}, indent=2) + "\n"
        self.assertTrue(
            conditional_content_problems(path, before_plugin, renamed, {"earnings-analysis"}, {path: "0.11.1"})
        )
        unchanged = json.dumps({"name": "pkg", "version": "0.11.0"}, indent=2) + "\n"
        self.assertTrue(
            conditional_content_problems(path, before_plugin, unchanged, {"earnings-analysis"}, {path: "0.11.0"})
        )
        skill_source = "plugins/vertical-plugins/equity-research/skills/earnings-analysis/SKILL.md"
        skill_copy = "plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/SKILL.md"
        skill_command = "plugins/vertical-plugins/equity-research/commands/earnings.md"
        self.assertEqual(conditional_content_problems(skill_source, "old", "new", {"earnings-analysis"}), [])
        self.assertEqual(conditional_content_problems(skill_copy, "old", "new", {"earnings-analysis"}), [])
        self.assertEqual(conditional_content_problems(skill_command, "old", "new", {"earnings-analysis"}), [])
        self.assertTrue(conditional_content_problems(skill_source, "old", "new", {"model-update"}))
        readme_before = (
            "## 2. 九项映射\n\n"
            "| # | 原命令 | 唯一技能 | 状态 | 验收方法 |\n"
            "|---|---|---|---|---|\n"
            "| 1 | `/earnings` | `earnings-analysis` | 明确缺口 | cmd-02 |\n"
            "| 2 | `/initiate` | `initiating-coverage` | 明确缺口 | cmd-02 |\n"
            "| 7 | `/earnings-preview` | `earnings-preview` | 明确缺口 | cmd-02 |\n\n"
            "### 2.1 MR-01 `/earnings` → `earnings-analysis`\n\n"
            "```yaml\nrow: MR-01\ncommand: /earnings\nskill: earnings-analysis\n"
            "source-files: [a/earnings.md]\nstatus: 明确缺口\n```\n\n"
            "### 2.2 MR-02 `/initiate` → `initiating-coverage`\n\n"
            "```yaml\nrow: MR-02\ncommand: /initiate\nskill: initiating-coverage\n"
            "source-files: [a/initiate.md]\nstatus: 明确缺口\n```\n"
        )
        readme_after = readme_before.replace(
            "| 1 | `/earnings` | `earnings-analysis` | 明确缺口 | cmd-02 |",
            "| 1 | `/earnings` | `earnings-analysis` | 接受 | cmd-02 + cmd-05 |",
        ).replace("status: 明确缺口\n```\n\n### 2.2", "status: 接受\n```\n\n### 2.2")
        self.assertEqual(
            conditional_content_problems(
                "workbuddy-experts/equity-research/README.md",
                readme_before,
                readme_after,
                {"earnings-analysis"},
            ),
            [],
        )
        wrong_row = readme_after.replace(
            "| 2 | `/initiate` | `initiating-coverage` | 明确缺口 | cmd-02 |",
            "| 2 | `/initiate` | `initiating-coverage` | 接受 | cmd-02 |",
        )
        self.assertTrue(
            conditional_content_problems(
                "workbuddy-experts/equity-research/README.md",
                readme_before,
                wrong_row,
                {"earnings-analysis"},
            )
        )
        custom_before = (
            "| WB-CUSTOM-01 | `baseline/a@1:plugins/vertical-plugins/equity-research/skills/earnings-analysis/SKILL.md` "
            "| `…/skills/earnings-analysis/SKILL.md` → 同路径 | 原语义 | `plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/` | 冲突处理旧 |\n"
            "| WB-CUSTOM-03 | `baseline/a@1:plugins/vertical-plugins/equity-research/skills/model-update/SKILL.md` "
            "| `…/skills/model-update/SKILL.md` → 同路径 | 原语义 | `plugins/agent-plugins/earnings-reviewer/skills/model-update/` | 冲突处理旧 |\n"
        )
        custom_after = custom_before.replace("| 原语义 |", "| 新语义 |", 1)
        self.assertEqual(
            conditional_content_problems(
                "CUSTOM.md",
                custom_before,
                custom_after,
                {"earnings-analysis", "model-update"},
                paths={skill_source, skill_copy},
            ),
            [],
        )
        self.assertTrue(
            conditional_content_problems("CUSTOM.md", custom_before, custom_after, {"earnings-analysis"}, paths=set())
        )
        self.assertTrue(
            conditional_content_problems(
                "CUSTOM.md", custom_before, custom_after, {"earnings-analysis"}, paths={skill_command}
            )
        )
        unrelated = custom_before.replace(
            "| `…/skills/model-update/SKILL.md` → 同路径 | 原语义 |",
            "| `…/skills/model-update/SKILL.md` → 同路径 | 改语义 |",
        )
        self.assertTrue(
            conditional_content_problems(
                "CUSTOM.md", custom_before, unrelated, {"earnings-analysis"}, paths={skill_source}
            )
        )

    def test_acceptance_append_is_pure(self) -> None:
        baseline = ACCEPTANCE.read_text(encoding="utf-8")
        lines = baseline.split("\n")
        prefix = "\n".join(lines[:BASELINE_ACCEPTANCE_LINES]) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode("utf-8")).hexdigest(), M1_ACCEPTANCE_PREFIX_SHA256)
        appended = prefix + "\n" + APPEND_TITLE + "\n\n<!-- m1-research:start -->\n```json\n{}\n```\n<!-- m1-research:end -->\n"
        added = appended[len(prefix):].split("\n")[:-1]
        diff = (
            f"diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -{BASELINE_ACCEPTANCE_LINES},0 "
            f"+{BASELINE_ACCEPTANCE_LINES + 1},{len(added)} @@\n"
            + "".join(f"+{line}\n" for line in added)
        )
        self.assertEqual(acceptance_append_problems(diff, prefix, appended), [])
        removed = diff.replace("+## 6. M1 研究证据与裁决记录\n", "-旧标题\n")
        self.assertTrue(acceptance_append_problems(removed, prefix, appended))
        mid_insert = diff.replace(f"@@ -{BASELINE_ACCEPTANCE_LINES},0", "@@ -10,0")
        self.assertTrue(acceptance_append_problems(mid_insert, prefix, appended))
        truncated = diff.replace(f",{len(added)} @@", f",{len(added) - 1} @@")
        self.assertTrue(acceptance_append_problems(truncated, prefix, appended))

    def test_readme_blocks_and_agent_hash_pin(self) -> None:
        text = README.read_text(encoding="utf-8")
        for name, digest in M1_README_BLOCK_SHA256.items():
            match = re.search(rf"<!--\s*{name}:start\s*-->(.*?)<!--\s*{name}:end\s*-->", text, re.DOTALL)
            self.assertIsNotNone(match, f"README missing {name} block")
            self.assertEqual(hashlib.sha256(match.group(0).encode("utf-8")).hexdigest(), digest)
            tampered = match.group(0).replace("<!--", "<!-- ", 1)
            self.assertNotEqual(hashlib.sha256(tampered.encode("utf-8")).hexdigest(), digest)
        agent = _support.AGENT.read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(agent.encode("utf-8")).hexdigest(), M1_AGENT_SHA256)


class RepositoryContract(RepoTest):
    """The real ACCEPTANCE.md §6 must satisfy the same contract in the skeleton state."""

    def test_top_level_contract(self) -> None:
        block = load_block()
        self.assertEqual(_top_level_problems(block), [])
        self.assertEqual(block["schema-version"], M1_SCHEMA_VERSION)
        self.assertEqual(block["cr"], M1_CR)

    def test_slot_mapping_matches_the_nine_legacy_records(self) -> None:
        block = load_block()
        legacy = legacy_slots()
        slots = block.get("slots")
        self.assertEqual([slot["slot"] for slot in slots], [slot for slot, _, _ in M1_SLOTS])
        for slot_id, acceptance, skill in M1_SLOTS:
            slot = m1_slot(block, slot_id)
            self.assertEqual(slot.get("acceptance-slot"), acceptance)
            self.assertEqual(slot.get("skill"), skill)
            self.assertEqual(legacy.get(acceptance), skill, "§2 mapping and §6 slot disagree")
        self.assertEqual(m1_slot(block, "M1-02")["acceptance-slot"], "SLOT-03")
        self.assertEqual(m1_slot(block, "M1-03")["acceptance-slot"], "SLOT-02")

    def test_every_registered_case_and_artifact_is_self_consistent(self) -> None:
        block = load_block()
        for slot_id, _, _ in M1_SLOTS:
            slot = m1_slot(block, slot_id)
            self.assertEqual(_slot_shape_problems(slot), [])
            problems = _case_identity_problems(slot) + _artifact_identity_problems(slot)
            for case in slot.get("positive-cases") or []:
                problems += case_problems(case, M1_POSITIVE_CASE_KEYS)
                problems += [] if case.get("language") in M1_LANGUAGES else [f"case {case.get('case-id')}: bad language"]
                problems += [] if case.get("market") in M1_MARKETS else [f"case {case.get('case-id')}: bad market"]
            for case in slot.get("negative-cases") or []:
                problems += case_problems(case, M1_NEGATIVE_CASE_KEYS)
                problems += [] if case.get("type") in M1_NEGATIVE_TYPES else [f"case {case.get('case-id')}: bad type"]
            for artifact in slot.get("artifacts") or []:
                problems += artifact_file_problems(artifact)
                problems += tool_record_problems(artifact)
                problems += table_route_problems(artifact)
            problems += checklist_problems(slot.get("quality-checklist") or [], slot.get("research-state") == "通过")
            problems += replay_problems(slot)
            problems += skill_change_problems(slot, block)
            self.assertEqual(problems, [], f"{slot_id} has inconsistent evidence")

    def test_pass_conditions_are_fail_closed(self) -> None:
        block = load_block()
        for slot_id, _, _ in M1_SLOTS:
            self.assertEqual(slot_pass_problems(m1_slot(block, slot_id), block), [])

    def test_scope_stays_inside_the_approved_range(self) -> None:
        block = load_block()
        changed = changed_paths()
        self.assertTrue(changed, "no diff against the fixed baseline: nothing to review")
        self.assertEqual(scope_problems(changed, block), [])
        conditional = [path for path in changed if skills_for_path(path)]
        affected = set()
        versions: dict[str, str] = {}
        allowed_paths: set[str] = set()
        for slot in block.get("slots") or []:
            record = slot.get("skill-change") if isinstance(slot.get("skill-change"), dict) else {}
            if record.get("changed") is True:
                affected.add(slot.get("skill"))
                allowed_paths.update(record.get("source-paths") or [])
                allowed_paths.update(record.get("copy-paths") or [])
                if isinstance(record.get("versions"), dict):
                    versions.update(record["versions"])
        for path in conditional:
            before, after = full_context_pair(controlled_diff(path, 999999), (_support.ROOT / path).read_text(encoding="utf-8"))
            self.assertEqual(
                conditional_content_problems(path, before, after, affected, versions, allowed_paths),
                [],
                f"{path} has a content-level scope violation",
            )
        agent = (_support.ROOT / "workbuddy-experts/equity-research/agents/equity-research.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(hashlib.sha256(agent.encode("utf-8")).hexdigest(), M1_AGENT_SHA256)
        for name, digest in M1_README_BLOCK_SHA256.items():
            match = re.search(
                rf"<!--\s*{name}:start\s*-->(.*?)<!--\s*{name}:end\s*-->",
                README.read_text(encoding="utf-8"),
                re.DOTALL,
            )
            self.assertIsNotNone(match)
            self.assertEqual(hashlib.sha256(match.group(0).encode("utf-8")).hexdigest(), digest)

    def test_acceptance_section_six_is_a_pure_append(self) -> None:
        current = ACCEPTANCE.read_text(encoding="utf-8")
        lines = current.split("\n")
        prefix = "\n".join(lines[:BASELINE_ACCEPTANCE_LINES]) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode("utf-8")).hexdigest(), M1_ACCEPTANCE_PREFIX_SHA256)
        self.assertEqual(lines[BASELINE_ACCEPTANCE_LINES], "")
        self.assertEqual(lines[BASELINE_ACCEPTANCE_LINES + 1], APPEND_TITLE)
        self.assertEqual(acceptance_append_problems(controlled_diff("workbuddy-experts/equity-research/ACCEPTANCE.md", 0), prefix, current), [])


if __name__ == "__main__":
    unittest.main()
