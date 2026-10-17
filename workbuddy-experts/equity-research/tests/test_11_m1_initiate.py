"""cmd-04 — M1-03 (`initiating-coverage`) evidence gate.

Consumes the M1-03 slot (`SLOT-02`) of `ACCEPTANCE.md` §6. The five Task stages
must be backed by five distinct real user requests and four distinct real user
confirmations located inside the original host session files, each completion
must receipt exactly that stage's artifacts, and a cross-session re-entry may
only resume at Task 2..5 with every previous artifact supplied. No placeholder
product, no automatic chain run and no adjudication is produced here.
"""
from __future__ import annotations

import contextlib
import datetime
import json
import os
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import _support
from _support import (
    ACCEPTANCE,
    M1_BLOCK,
    M1_CASE_SUMMARY_LIMIT,
    M1_INITIATE_STAGES,
    M1_LANGUAGES,
    M1_MARKETS,
    M1_NEGATIVE_CASE_KEYS,
    M1_NEGATIVE_TYPES,
    M1_POSITIVE_CASE_KEYS,
    RepoTest,
    m1_readiness_problems,
    m1_slot,
    m1_tool_record_problems,
    read_json_block,
    resolve_evidence_path,
    sha256_file,
    split_evidence_ref,
)

SLOT_ID = "M1-03"
STAGE_KEYS = {"case-id", "stage", "request", "completion", "previous-confirmation"}
LOCATOR_KEYS = {"session-id", "message-id", "message-index"}
REQUEST_RE = re.compile(r"^(?:请求执行|Request): Task ([1-5])$", re.MULTILINE)
CONFIRM_RE = re.compile(r"^(?:确认|Confirm) Task ([1-5])$", re.MULTILINE)
STAGE_NUMBER = {case_id: number for number, (case_id, _) in enumerate(M1_INITIATE_STAGES, start=1)}
STAGE_KINDS = dict(M1_INITIATE_STAGES)
SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
MISSING_NEGATIVES = ("M1-03-T3-missing-model", "M1-03-T5-missing-zip", "M1-03-CROSS-MISSING")


def load_slot() -> tuple[dict, dict]:
    block = read_json_block(ACCEPTANCE, M1_BLOCK)
    return block, m1_slot(block, SLOT_ID)


def setUpModule() -> None:  # noqa: N802 - unittest hook
    block = read_json_block(ACCEPTANCE, M1_BLOCK)
    problems = m1_readiness_problems(block, os.environ.get("M1_EVIDENCE_CONTEXT", "develop"))
    if problems:
        raise SystemExit("ENVIRONMENT_MISMATCH: " + "; ".join(problems))


@contextlib.contextmanager
def temp_root():
    original = _support.ROOT
    with tempfile.TemporaryDirectory() as tmp:
        _support.ROOT = Path(tmp)
        try:
            yield Path(tmp)
        finally:
            _support.ROOT = original


def _parse_time(value: object, label: str) -> tuple[datetime.datetime | None, list[str]]:
    if not isinstance(value, str) or not value.strip():
        return None, [f"{label}: missing ISO8601 timestamp"]
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None, [f"{label}: not an ISO8601 timestamp: {value!r}"]
    if parsed.tzinfo is None:
        return None, [f"{label}: timestamp must carry a timezone"]
    return parsed, []


def stage_groups(artifacts: list[dict]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for artifact in artifacts or []:
        if not isinstance(artifact, dict):
            continue
        groups.setdefault(artifact.get("case-id"), set()).add(artifact.get("kind"))
    return groups


def _locator_problems(locator: object, label: str) -> list[str]:
    if not isinstance(locator, dict):
        return [f"{label}: locator must be an object"]
    problems = []
    if set(locator) != LOCATOR_KEYS:
        problems.append(f"{label}: locator keys must be {sorted(LOCATOR_KEYS)}")
    if not str(locator.get("session-id") or "").strip():
        problems.append(f"{label}.session-id is required")
    if not str(locator.get("message-id") or "").strip():
        problems.append(f"{label}.message-id is required")
    index = locator.get("message-index")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        problems.append(f"{label}.message-index must be a 0-based integer")
    return problems


def _load_session(ref: object, label: str) -> tuple[dict | None, list[str]]:
    try:
        path, digest = split_evidence_ref(ref)
    except AssertionError as exc:
        return None, [f"{label}: {exc}"]
    if not path.is_file():
        return None, [f"{label}: session file is missing"]
    if sha256_file(path) != digest:
        return None, [f"{label}: sha256 does not match the session file"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{label}: session file is not readable JSON: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{label}: session file must be an object"]
    return data, []


def _messages(record: dict) -> list[dict] | None:
    messages = record.get("messages")
    return messages if isinstance(messages, list) else None


def _locate(locator: dict, files: list[dict]) -> tuple[dict | None, list[str]]:
    matches = [record for record in files if record.get("session-id") == locator.get("session-id")]
    if not matches:
        return None, [f"locator session-id {locator.get('session-id')!r} is not in the supplied session files"]
    messages = _messages(matches[0])
    if messages is None:
        return None, ["session file has no messages list"]
    index = locator.get("message-index")
    if not isinstance(index, int) or index < 0 or index >= len(messages):
        return None, [f"message-index {index!r} is out of range"]
    message = messages[index]
    if not isinstance(message, dict):
        return None, [f"message at index {index} is not an object"]
    if message.get("id") != locator.get("message-id"):
        return None, [f"message-id does not match the message at index {index}"]
    for key in ("id", "role", "at", "text"):
        if key not in message:
            return None, [f"message at index {index} is missing {key}"]
    return message, []


def _receipts(message: dict) -> list[tuple[str, str]]:
    raw = message.get("artifacts")
    if raw is None:
        raw = message.get("artifact-receipts")
    receipts = []
    for item in raw or []:
        if isinstance(item, dict) and item.get("path") and item.get("sha256"):
            receipts.append((item["path"], item["sha256"]))
    return receipts


def _session_shape_problems(record: dict, label: str) -> list[str]:
    problems = []
    if not str(record.get("session-id") or "").strip():
        problems.append(f"{label}: root session-id is required")
    messages = _messages(record)
    if messages is None:
        problems.append(f"{label}: messages must be a list")
    else:
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                problems.append(f"{label}: message {index} must be an object")
                continue
            for key in ("id", "role", "at", "text"):
                if key not in message:
                    problems.append(f"{label}: message {index} is missing {key}")
    return problems


def stage_problems(slot: dict) -> list[str]:
    """Five-stage independent-request binding, read from the original session files."""
    passed = slot.get("research-state") == "通过"
    cases = [case for case in slot.get("positive-cases") or [] if isinstance(case, dict)]
    artifacts = [artifact for artifact in slot.get("artifacts") or [] if isinstance(artifact, dict)]
    if not cases and not artifacts:
        return []
    problems = []
    by_case = {case.get("case-id"): case for case in cases}
    groups = stage_groups(artifacts)
    for case_id, kinds in M1_INITIATE_STAGES:
        if case_id not in by_case:
            if passed:
                problems.append(f"{SLOT_ID}: stage case {case_id} is missing from positive-cases")
            continue
        if groups.get(case_id, set()) != set(kinds):
            problems.append(f"{case_id}: artifact kinds {sorted(groups.get(case_id, set()))} != {sorted(kinds)}")
    for case_id in groups:
        if case_id not in STAGE_KINDS:
            problems.append(f"{case_id}: extra stage case is not part of M1_INITIATE_STAGES")
    sessions: dict[str, dict] = {}
    for case_id, case in by_case.items():
        record, session_problems = _load_session(case.get("session-record"), f"{case_id}.session-record")
        problems += session_problems
        if record is None:
            continue
        sessions[case_id] = record
        problems += _session_shape_problems(record, case_id)
        evidence = record.get("stage-evidence")
        if not isinstance(evidence, dict):
            problems.append(f"{case_id}: stage-evidence is missing")
            continue
        if set(evidence) != STAGE_KEYS:
            problems.append(f"{case_id}: stage-evidence keys must be {sorted(STAGE_KEYS)}")
        if evidence.get("case-id") != case_id:
            problems.append(f"{case_id}: stage-evidence.case-id does not match")
        number = STAGE_NUMBER.get(case_id)
        if evidence.get("stage") != number:
            problems.append(f"{case_id}: stage-evidence.stage must be {number}")
    files = list(sessions.values())
    request_identities = set()
    completion_times: dict[str, datetime.datetime] = {}
    confirmation_identities: dict[str, tuple[str, str]] = {}
    ordered = [case_id for case_id, _ in M1_INITIATE_STAGES if case_id in sessions]
    previous_completion: datetime.datetime | None = None
    for case_id in ordered:
        record = sessions[case_id]
        evidence = record.get("stage-evidence") if isinstance(record.get("stage-evidence"), dict) else {}
        number = STAGE_NUMBER[case_id]
        label = f"{case_id}.stage-evidence"
        problems += _locator_problems(evidence.get("request"), f"{label}.request")
        problems += _locator_problems(evidence.get("completion"), f"{label}.completion")
        request, request_problems = _locate(evidence.get("request") or {}, files)
        problems += request_problems
        completion, completion_problems = _locate(evidence.get("completion") or {}, files)
        problems += completion_problems
        if request is not None:
            if evidence.get("request", {}).get("session-id") != record.get("session-id"):
                problems.append(f"{case_id}: the request must be located in this stage's own session file")
            if request.get("role") != "user":
                problems.append(f"{case_id}: the request must be a real user message")
            matches = [int(match) for match in REQUEST_RE.findall(str(request.get("text") or ""))]
            if matches != [number]:
                problems.append(f"{case_id}: the request message must name exactly one stage: Task {number}")
            identity = (evidence.get("request", {}).get("session-id"), request.get("id"))
            if identity in request_identities:
                problems.append(f"{case_id}: the request message is not distinct from another stage")
            request_identities.add(identity)
            request_time, time_problems = _parse_time(request.get("at"), f"{case_id}.request.at")
            problems += time_problems
        else:
            request_time = None
        if completion is not None:
            if evidence.get("completion", {}).get("session-id") != record.get("session-id"):
                problems.append(f"{case_id}: the completion must be located in this stage's own session file")
            if completion.get("role") != "assistant":
                problems.append(f"{case_id}: the completion must be an assistant message")
            completion_time, time_problems = _parse_time(completion.get("at"), f"{case_id}.completion.at")
            problems += time_problems
            if completion_time is not None:
                completion_times[case_id] = completion_time
            receipts = _receipts(completion)
            expected = {(artifact.get("path"), artifact.get("sha256")) for artifact in artifacts if artifact.get("case-id") == case_id}
            if set(receipts) != expected:
                problems.append(f"{case_id}: the completion receipt must equal this stage's artifacts")
            if request_time is not None and completion_time is not None and not completion_time > request_time:
                problems.append(f"{case_id}: the completion must follow the request")
            if (
                request is not None
                and evidence.get("request", {}).get("session-id") == record.get("session-id")
                and evidence.get("completion", {}).get("session-id") == record.get("session-id")
                and isinstance(evidence.get("completion", {}).get("message-index"), int)
                and isinstance(evidence.get("request", {}).get("message-index"), int)
                and evidence.get("completion", {}).get("message-index") <= evidence.get("request", {}).get("message-index")
            ):
                problems.append(f"{case_id}: the completion message index must follow the request")
            if previous_completion is not None and completion_time is not None and not completion_time > previous_completion:
                problems.append(f"{case_id}: stage completion times must increase")
        confirmation = evidence.get("previous-confirmation")
        if number == 1:
            if confirmation is not None:
                problems.append(f"{case_id}: Task 1 must not carry a previous confirmation")
        else:
            problems += _locator_problems(confirmation, f"{label}.previous-confirmation")
            message, confirmation_problems = _locate(confirmation or {}, files)
            problems += confirmation_problems
            if message is not None:
                if message.get("role") != "user":
                    problems.append(f"{case_id}: the previous confirmation must be a real user message")
                matches = [int(match) for match in CONFIRM_RE.findall(str(message.get("text") or ""))]
                if matches != [number - 1]:
                    problems.append(f"{case_id}: the previous confirmation must confirm Task {number - 1}")
                if (confirmation or {}).get("message-id") == (evidence.get("request") or {}).get("message-id") and (
                    confirmation or {}
                ).get("session-id") == (evidence.get("request") or {}).get("session-id"):
                    problems.append(f"{case_id}: the confirmation and the request cannot be the same message")
                confirmation_time, time_problems = _parse_time(message.get("at"), f"{case_id}.confirmation.at")
                problems += time_problems
                if request_time is not None and confirmation_time is not None and not confirmation_time < request_time:
                    problems.append(f"{case_id}: the confirmation must precede the current request")
                position = ordered.index(case_id)
                previous = ordered[position - 1] if position > 0 else None
                if previous and previous in completion_times:
                    if confirmation_time is not None and not confirmation_time > completion_times[previous]:
                        problems.append(f"{case_id}: the confirmation must follow the previous completion")
                confirmation_identities[case_id] = (
                    (confirmation or {}).get("session-id"),
                    (confirmation or {}).get("message-id"),
                )
        if completion_times.get(case_id) is not None:
            previous_completion = completion_times[case_id]
    if passed:
        collected = []
        for case_id, _ in M1_INITIATE_STAGES:
            case = by_case.get(case_id) or {}
            if f"Task {STAGE_NUMBER[case_id]}" not in str(case.get("expected") or ""):
                problems.append(f"{case_id}: expected must name Task {STAGE_NUMBER[case_id]}")
            if not str(case.get("actual") or "").strip():
                problems.append(f"{case_id}: actual is required")
            collected.append(str(case.get("collected-at") or ""))
        parsed = []
        for index, value in enumerate(collected):
            parsed_time, time_problems = _parse_time(value, f"collected-at[{index}]")
            parsed.append(parsed_time)
            problems += time_problems
        for before, after in zip(parsed, parsed[1:]):
            if before is not None and after is not None and not after > before:
                problems.append("collected-at must strictly increase across the five stages")
    return problems


def cross_session_problems(record: dict, stage_artifacts: dict[str, list[dict]]) -> list[str]:
    """Cross-session re-entry: only Task 2..5, all previous artifacts supplied."""
    if not isinstance(record, dict):
        return ["cross-session record must be an object"]
    keys = {
        "reentry-id",
        "exit-at",
        "reentry-at",
        "provided-artifacts",
        "stage-located",
        "confirmation",
        "final-artifact",
        "result",
    }
    problems = []
    extra = sorted(set(record) - keys)
    missing = sorted(keys - set(record))
    if extra:
        problems.append(f"cross-session keys not allowed: {extra}")
    if missing:
        problems.append(f"cross-session keys missing: {missing}")
    for key in ("reentry-id", "confirmation"):
        if not str(record.get(key) or "").strip():
            problems.append(f"cross-session.{key} is required")
    stage_located = str(record.get("stage-located") or "")
    match = re.match(r"^Task ([2-5])$", stage_located)
    if not match:
        problems.append(f"cross-session.stage-located must be Task 2..5, got {stage_located!r}")
        stage_number = None
    else:
        stage_number = int(match.group(1))
    exit_time, exit_problems = _parse_time(record.get("exit-at"), "cross-session.exit-at")
    reentry_time, reentry_problems = _parse_time(record.get("reentry-at"), "cross-session.reentry-at")
    problems += exit_problems + reentry_problems
    if exit_time is not None and reentry_time is not None and not reentry_time > exit_time:
        problems.append("cross-session.reentry-at must be after exit-at")
    provided = record.get("provided-artifacts")
    if not isinstance(provided, list) or not provided:
        problems.append("cross-session.provided-artifacts must be a non-empty list")
        provided = []
    provided_pairs = set()
    for index, ref in enumerate(provided):
        try:
            path, digest = split_evidence_ref(ref)
        except AssertionError as exc:
            problems.append(f"cross-session.provided-artifacts[{index}]: {exc}")
            continue
        if not path.is_file():
            problems.append(f"cross-session.provided-artifacts[{index}]: file is missing")
        elif sha256_file(path) != digest:
            problems.append(f"cross-session.provided-artifacts[{index}]: sha256 does not match")
        provided_pairs.add((path.relative_to(_support.ROOT).as_posix(), digest))
    if stage_number is not None:
        required = set()
        for case_id, _ in M1_INITIATE_STAGES[: stage_number - 1]:
            for artifact in stage_artifacts.get(case_id) or []:
                if isinstance(artifact, dict) and artifact.get("path") and artifact.get("sha256"):
                    required.add((artifact["path"], artifact["sha256"]))
        missing_pairs = required - provided_pairs
        if missing_pairs:
            problems.append(f"cross-session.provided-artifacts misses {len(missing_pairs)} previous artifact(s)")
    final_ref = record.get("final-artifact")
    try:
        final_path, final_digest = split_evidence_ref(final_ref)
    except AssertionError as exc:
        problems.append(f"cross-session.final-artifact: {exc}")
    else:
        docx = [artifact for artifact in stage_artifacts.get("M1-03-T5") or [] if artifact.get("kind") == "DOCX"]
        if not docx:
            problems.append("cross-session.final-artifact: M1-03-T5 DOCX is not registered")
        elif (final_path.relative_to(_support.ROOT).as_posix(), final_digest) != (docx[0].get("path"), docx[0].get("sha256")):
            problems.append("cross-session.final-artifact must be the M1-03-T5 DOCX")
    if record.get("result") != "通过":
        problems.append("cross-session.result must be 通过")
    return problems


def tool_record_problems(artifact: dict) -> list[str]:
    """AC-06 per-stage routing: T2 new table, T3 update of the same model."""
    kind = artifact.get("kind")
    case_id = artifact.get("case-id")
    if kind == "DOCX":
        routes = ("tencent-docx",)
    elif kind == "REPORT":
        routes = ("host-preview", "tencent-docx")
    elif kind == "ZIP":
        routes = ("matplotlib-fallback",)
    elif kind == "XLSX":
        routes = ("tencent-docs-sheet-generation",) if case_id == "M1-03-T2" else ("tencent-docs-sheetagent",)
    else:
        return []
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    problems = []
    if kind == "XLSX":
        expected = "new" if case_id == "M1-03-T2" else "existing"
        if meta.get("table-route") != expected:
            problems.append(f"{case_id}: table-route must be {expected!r}")
    problems += m1_tool_record_problems(artifact, routes)
    return problems


def _structure_problems(artifact: dict) -> list[str]:
    kind = artifact.get("kind")
    if kind not in ("DOCX", "XLSX", "ZIP", "REPORT"):
        return []
    try:
        path = resolve_evidence_path(artifact.get("path"))
    except AssertionError as exc:
        return [f"artifact.path: {exc}"]
    if not path.is_file():
        return [f"artifact.path: file is missing: {artifact.get('path')}"]
    structural = artifact.get("structural") if isinstance(artifact.get("structural"), dict) else {}
    meta = artifact.get("meta") if isinstance(artifact.get("meta"), dict) else {}
    problems = []
    if kind in ("DOCX", "XLSX", "ZIP"):
        try:
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    problems.append(f"{kind} zip archive is corrupted")
                entries = archive.namelist()
                if kind == "DOCX":
                    if "word/document.xml" not in entries:
                        problems.append("DOCX is missing word/document.xml")
                    else:
                        ET.fromstring(archive.read("word/document.xml"))
                if kind == "XLSX":
                    if "xl/workbook.xml" not in entries:
                        problems.append("XLSX is missing xl/workbook.xml")
                    else:
                        ET.fromstring(archive.read("xl/workbook.xml"))
                    formulas = 0
                    for name in entries:
                        if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                            root = ET.fromstring(archive.read(name))
                            formulas += sum(1 for element in root.iter() if element.tag == f"{SHEET_NS}f")
                    if formulas <= 0:
                        problems.append("XLSX must contain at least one live formula cell")
                if kind == "ZIP":
                    if meta.get("entries") != len(entries):
                        problems.append("meta.entries must equal the ZIP entry count")
                    figures = meta.get("figures")
                    if not isinstance(figures, list) or not figures:
                        problems.append("meta.figures must list each figure with its source")
                    else:
                        for index, figure in enumerate(figures):
                            if not isinstance(figure, dict) or set(figure) != {"name", "source"}:
                                problems.append(f"meta.figures[{index}] must have exactly name/source")
                                continue
                            if not str(figure.get("source") or "").strip():
                                problems.append(f"meta.figures[{index}].source is required")
                            if figure.get("name") not in entries:
                                problems.append(f"meta.figures[{index}].name is not in the ZIP")
        except (zipfile.BadZipFile, ET.ParseError) as exc:
            problems.append(f"{kind} is not a readable OOXML package: {exc}")
    expected_type = {"DOCX": "docx", "XLSX": "xlsx", "ZIP": "zip", "REPORT": "markdown"}[kind]
    if structural.get("type") != expected_type or structural.get("ok") is not True:
        problems.append(f"{kind} structural.type/ok must be {expected_type}/true")
    if kind == "REPORT" and path.stat().st_size == 0:
        problems.append("REPORT must not be empty")
    return problems


def _summary_problems(value: object, label: str) -> list[str]:
    if not isinstance(value, str):
        return [f"{label} must be a string"]
    problems = []
    if len(value) > M1_CASE_SUMMARY_LIMIT:
        problems.append(f"{label} exceeds {M1_CASE_SUMMARY_LIMIT} characters")
    if re.search(r"(?i)(api[_-]?key|secret|password|bearer\s+[a-z0-9._-]{8,}|sk-[a-z0-9]{8,})", value):
        problems.append(f"{label} must not contain credentials")
    return problems


def _case_problems(case: dict, keys: tuple[str, ...]) -> list[str]:
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


def slot_evidence_problems(slot: dict, block: dict) -> list[str]:
    passed = slot.get("research-state") == "通过"
    problems = []
    case_ids = set()
    for case in slot.get("positive-cases") or []:
        problems += _case_problems(case, M1_POSITIVE_CASE_KEYS)
        if case.get("language") not in M1_LANGUAGES:
            problems.append(f"{case.get('case-id')}: language is not allowed")
        if case.get("market") not in M1_MARKETS:
            problems.append(f"{case.get('case-id')}: market is not allowed")
        case_ids.add(case.get("case-id"))
    for case in slot.get("negative-cases") or []:
        problems += _case_problems(case, M1_NEGATIVE_CASE_KEYS)
        if case.get("type") not in M1_NEGATIVE_TYPES:
            problems.append(f"{case.get('case-id')}: negative type is not allowed")
        case_ids.add(case.get("case-id"))
    for case in (slot.get("positive-cases") or []) + (slot.get("negative-cases") or []):
        try:
            path, digest = split_evidence_ref(case.get("session-record"))
        except AssertionError as exc:
            problems.append(f"{case.get('case-id')}.session-record: {exc}")
            continue
        if not path.is_file() or sha256_file(path) != digest:
            problems.append(f"{case.get('case-id')}.session-record: file missing or sha256 mismatch")
        if passed and case.get("result") != "通过":
            problems.append(f"{case.get('case-id')}: result is not 通过")
    artifact_ids = set()
    stage_artifacts: dict[str, list[dict]] = {}
    for artifact in slot.get("artifacts") or []:
        if not isinstance(artifact, dict):
            problems.append("artifact must be an object")
            continue
        artifact_id = artifact.get("artifact-id")
        if artifact_id in artifact_ids:
            problems.append(f"duplicate artifact-id {artifact_id!r}")
        artifact_ids.add(artifact_id)
        stage_artifacts.setdefault(artifact.get("case-id"), []).append(artifact)
        if artifact.get("case-id") not in case_ids:
            problems.append(f"artifact {artifact_id!r}: case-id misses a registered case")
        try:
            path = resolve_evidence_path(artifact.get("path"))
        except AssertionError as exc:
            problems.append(f"artifact {artifact_id!r}.path: {exc}")
            continue
        if not path.is_file():
            problems.append(f"artifact {artifact_id!r}.path: file is missing")
        else:
            if sha256_file(path) != artifact.get("sha256"):
                problems.append(f"artifact {artifact_id!r}: sha256 does not match")
            if artifact.get("bytes") != path.stat().st_size:
                problems.append(f"artifact {artifact_id!r}: bytes does not match")
        problems += _structure_problems(artifact)
        problems += tool_record_problems(artifact)
        open_check = artifact.get("open-check") if isinstance(artifact.get("open-check"), dict) else {}
        if passed and artifact.get("kind") in ("DOCX", "XLSX") and open_check.get("result") != "成功":
            problems.append(f"artifact {artifact_id!r}: open-check must be 成功 once the slot is 通过")
        for index, deviation in enumerate(artifact.get("deviations") or []):
            for key in ("requirement", "actual", "reason", "adjudication-ref"):
                if not isinstance(deviation, dict) or not str(deviation.get(key) or "").strip():
                    problems.append(f"artifact {artifact_id!r}: deviations[{index}].{key} is required")
    problems += stage_problems(slot)
    if passed:
        languages = {case.get("language") for case in slot.get("positive-cases") or []}
        for language in M1_LANGUAGES:
            if language not in languages:
                problems.append(f"{SLOT_ID}: needs a {language} positive case")
        negatives = {case.get("case-id"): case for case in slot.get("negative-cases") or []}
        for case_id in MISSING_NEGATIVES:
            case = negatives.get(case_id)
            if not isinstance(case, dict):
                problems.append(f"{SLOT_ID}: missing-prerequisite negative {case_id} is required")
                continue
            if case.get("type") != "missing-prerequisite" or case.get("result") != "通过":
                problems.append(f"{case_id}: must be a 通过 missing-prerequisite negative")
            if not str(case.get("expected") or "").strip() or not str(case.get("actual") or "").strip():
                problems.append(f"{case_id}: expected/actual are required")
            if any(artifact.get("case-id") == case_id for artifact in slot.get("artifacts") or []):
                problems.append(f"{case_id}: no placeholder artifact may be registered for a missing-prerequisite case")
        record = slot.get("cross-session")
        if record is None:
            problems.append(f"{SLOT_ID}: cross-session record is required once the slot is 通过")
        else:
            problems += cross_session_problems(record, stage_artifacts)
        problems += m1_readiness_problems(block, "collect")
    return problems


class SyntheticChecks(unittest.TestCase):
    """Legality and every required failure mode, against temporary session files."""

    def test_stage_groups(self) -> None:
        artifacts = [
            {"case-id": "M1-03-T1", "kind": "REPORT"},
            {"case-id": "M1-03-T2", "kind": "XLSX"},
            {"case-id": "M1-03-T1", "kind": "REPORT"},
        ]
        self.assertEqual(stage_groups(artifacts), {"M1-03-T1": {"REPORT"}, "M1-03-T2": {"XLSX"}})

    def _fixture(self, root: Path) -> tuple[dict, dict[str, dict]]:
        slot = {"research-state": "通过", "positive-cases": [], "negative-cases": [], "artifacts": []}
        sessions: dict[str, dict] = {}
        start = datetime.datetime(2026, 10, 17, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        offset = 0
        previous_confirmation = None
        for number, (case_id, kinds) in enumerate(M1_INITIATE_STAGES, start=1):
            session_id = f"sess-{number}"
            artifacts = []
            for kind in kinds:
                suffix = {"REPORT": "report.md", "XLSX": "model.xlsx", "ZIP": "charts.zip", "DOCX": "final.docx"}[kind]
                path = root / "out" / "evidence" / "m1" / "artifacts" / case_id / suffix
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f"{case_id}-{kind}".encode("utf-8"))
                artifacts.append(
                    {
                        "artifact-id": f"{case_id}-{kind}",
                        "case-id": case_id,
                        "kind": kind,
                        "path": path.relative_to(root).as_posix(),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                )
            messages = [
                {
                    "id": "m1",
                    "role": "user",
                    "at": (start + datetime.timedelta(minutes=offset)).isoformat(),
                    "text": f"请求执行: Task {number}\n请只执行本阶段。",
                },
                {
                    "id": "m2",
                    "role": "assistant",
                    "at": (start + datetime.timedelta(minutes=offset + 5)).isoformat(),
                    "text": "done",
                    "artifacts": [{"path": item["path"], "sha256": item["sha256"]} for item in artifacts],
                },
            ]
            confirmation = previous_confirmation
            if number < len(M1_INITIATE_STAGES):
                messages.append(
                    {
                        "id": "m3",
                        "role": "user",
                        "at": (start + datetime.timedelta(minutes=offset + 10)).isoformat(),
                        "text": f"确认 Task {number}",
                    }
                )
                previous_confirmation = {"session-id": session_id, "message-id": "m3", "message-index": 2}
            record = {
                "session-id": session_id,
                "messages": messages,
                "stage-evidence": {
                    "case-id": case_id,
                    "stage": number,
                    "request": {"session-id": session_id, "message-id": "m1", "message-index": 0},
                    "completion": {"session-id": session_id, "message-id": "m2", "message-index": 1},
                    "previous-confirmation": confirmation,
                },
            }
            path = root / "out" / "evidence" / "m1" / "sessions" / f"{case_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            sessions[case_id] = record
            slot["positive-cases"].append(
                {
                    "case-id": case_id,
                    "language": "zh-CN",
                    "market": "A股",
                    "input-summary": "摘要",
                    "response-summary": "摘要",
                    "session-record": f"{path.relative_to(root).as_posix()}::{sha256_file(path)}",
                    "client-version": "v",
                    "tool-version": "v",
                    "collected-at": (start + datetime.timedelta(minutes=offset + 15)).isoformat(),
                    "expected": f"Task {number}",
                    "actual": "ok",
                    "result": "通过",
                }
            )
            slot["artifacts"].extend(artifacts)
            offset += 30
        return slot, sessions

    def test_stage_bindings_accept_and_reject(self) -> None:
        with temp_root() as root:
            slot, _ = self._fixture(root)
            self.assertEqual(stage_problems(slot), [])

            slot, _ = self._fixture(root)
            copied = json.loads(json.dumps(slot))
            copied["positive-cases"][1]["session-record"] = copied["positive-cases"][0]["session-record"]
            self.assertTrue(stage_problems(copied))

            slot, sessions = self._fixture(root)
            session = sessions["M1-03-T3"]
            session["stage-evidence"]["previous-confirmation"] = None
            path = root / "out" / "evidence" / "m1" / "sessions" / "M1-03-T3.json"
            path.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
            slot["positive-cases"][2]["session-record"] = f"{path.relative_to(root).as_posix()}::{sha256_file(path)}"
            self.assertTrue(stage_problems(slot))

            slot, sessions = self._fixture(root)
            session = sessions["M1-03-T3"]
            session["stage-evidence"]["previous-confirmation"] = {
                "session-id": session["session-id"],
                "message-id": "m1",
                "message-index": 0,
            }
            path = root / "out" / "evidence" / "m1" / "sessions" / "M1-03-T3.json"
            path.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
            slot["positive-cases"][2]["session-record"] = f"{path.relative_to(root).as_posix()}::{sha256_file(path)}"
            self.assertTrue(stage_problems(slot))

            slot, sessions = self._fixture(root)
            record = sessions["M1-03-T4"]
            record["stage-evidence"]["previous-confirmation"]["message-index"] = 1
            path = root / "out" / "evidence" / "m1" / "sessions" / "M1-03-T4.json"
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            slot["positive-cases"][3]["session-record"] = f"{path.relative_to(root).as_posix()}::{sha256_file(path)}"
            self.assertTrue(stage_problems(slot))

            slot, sessions = self._fixture(root)
            record = sessions["M1-03-T2"]
            record["messages"][1]["artifacts"] = [{"path": "out/evidence/m1/other.xlsx", "sha256": "a" * 64}]
            path = root / "out" / "evidence" / "m1" / "sessions" / "M1-03-T2.json"
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            slot["positive-cases"][1]["session-record"] = f"{path.relative_to(root).as_posix()}::{sha256_file(path)}"
            self.assertTrue(stage_problems(slot))

            slot, _ = self._fixture(root)
            slot["artifacts"][0]["kind"] = "DOCX"
            self.assertTrue(stage_problems(slot))

            slot, _ = self._fixture(root)
            slot["positive-cases"] = slot["positive-cases"][:4]
            self.assertTrue(stage_problems(slot))

            slot, sessions = self._fixture(root)
            record = sessions["M1-03-T3"]
            record["messages"][0]["at"] = record["messages"][2]["at"]
            record["messages"][2]["at"] = "2026-10-17T08:00:00+08:00"
            path = root / "out" / "evidence" / "m1" / "sessions" / "M1-03-T3.json"
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            slot["positive-cases"][2]["session-record"] = f"{path.relative_to(root).as_posix()}::{sha256_file(path)}"
            self.assertTrue(stage_problems(slot))

    def test_cross_session_problems(self) -> None:
        with temp_root() as root:
            t5_docx = root / "out" / "evidence" / "m1" / "artifacts" / "M1-03-T5" / "final.docx"
            t5_docx.parent.mkdir(parents=True)
            t5_docx.write_bytes(b"final")
            t1_report = root / "out" / "evidence" / "m1" / "artifacts" / "M1-03-T1" / "report.md"
            t1_report.parent.mkdir(parents=True)
            t1_report.write_bytes(b"report")
            t2_xlsx = root / "out" / "evidence" / "m1" / "artifacts" / "M1-03-T2" / "model.xlsx"
            t2_xlsx.parent.mkdir(parents=True)
            t2_xlsx.write_bytes(b"model")
            stage_artifacts = {
                "M1-03-T1": [{"kind": "REPORT", "path": t1_report.relative_to(root).as_posix(), "sha256": sha256_file(t1_report)}],
                "M1-03-T2": [{"kind": "XLSX", "path": t2_xlsx.relative_to(root).as_posix(), "sha256": sha256_file(t2_xlsx)}],
                "M1-03-T5": [{"kind": "DOCX", "path": t5_docx.relative_to(root).as_posix(), "sha256": sha256_file(t5_docx)}],
            }
            record = {
                "reentry-id": "R1",
                "exit-at": "2026-10-17T10:00:00+08:00",
                "reentry-at": "2026-10-17T11:00:00+08:00",
                "provided-artifacts": [
                    f"{t1_report.relative_to(root).as_posix()}::{sha256_file(t1_report)}",
                    f"{t2_xlsx.relative_to(root).as_posix()}::{sha256_file(t2_xlsx)}",
                ],
                "stage-located": "Task 3",
                "confirmation": "用户确认从 Task 3 继续",
                "final-artifact": f"{t5_docx.relative_to(root).as_posix()}::{sha256_file(t5_docx)}",
                "result": "通过",
            }
            self.assertEqual(cross_session_problems(record, stage_artifacts), [])
            for broken in (
                {**record, "stage-located": "Task 1"},
                {**record, "provided-artifacts": []},
                {**record, "provided-artifacts": record["provided-artifacts"][:1]},
                {**record, "provided-artifacts": [record["provided-artifacts"][0].rsplit("::", 1)[0] + "::" + "b" * 64]},
                {**record, "reentry-at": "2026-10-17T09:00:00+08:00"},
                {**record, "final-artifact": record["provided-artifacts"][0]},
            ):
                self.assertTrue(cross_session_problems(broken, stage_artifacts))

    def test_tool_record_problems(self) -> None:
        with temp_root() as root:
            path = root / "out" / "evidence" / "m1" / "artifacts" / "M1-03-T2" / "model.xlsx"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"xlsx")
            artifact = {
                "artifact-id": "M1-03-T2-XLSX",
                "case-id": "M1-03-T2",
                "kind": "XLSX",
                "path": "out/evidence/m1/artifacts/M1-03-T2/model.xlsx",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "generated-by": "tencent-docs-sheet-generation|1.0|tencent-docs-sheet-generation",
                "meta": {"schema-query": "sheet.create", "tool-result": "成功", "table-route": "new"},
                "deviations": [],
            }
            self.assertEqual(tool_record_problems(artifact), [])
            self.assertTrue(tool_record_problems({**artifact, "meta": {**artifact["meta"], "table-route": "existing"}}))
            self.assertTrue(tool_record_problems({**artifact, "generated-by": "x|1|tencent-docs-sheetagent"}))
            self.assertTrue(tool_record_problems({**artifact, "meta": {"tool-result": "成功", "table-route": "new"}}))
            t3 = {**artifact, "artifact-id": "M1-03-T3-XLSX", "case-id": "M1-03-T3", "generated-by": "a|1|tencent-docs-sheetagent", "meta": {**artifact["meta"], "table-route": "existing"}}
            self.assertEqual(tool_record_problems(t3), [])
            self.assertTrue(tool_record_problems({**t3, "meta": {**t3["meta"], "table-route": "new"}}))
            zip_artifact = {
                **artifact,
                "artifact-id": "M1-03-T4-ZIP",
                "case-id": "M1-03-T4",
                "kind": "ZIP",
                "generated-by": "matplotlib|3|matplotlib-fallback",
                "meta": {"schema-query": "zip", "tool-result": "成功"},
            }
            self.assertTrue(tool_record_problems(zip_artifact))
            source = root / "out" / "evidence" / "m1" / "artifacts" / "M1-03-T4" / "data.csv"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"date,value")
            self.assertEqual(
                tool_record_problems(
                    {
                        **zip_artifact,
                        "meta": {
                            **zip_artifact["meta"],
                            "script": "s.py",
                            "dependencies": ["matplotlib"],
                            "inputs": [f"{source.relative_to(root).as_posix()}::{sha256_file(source)}"],
                        },
                    }
                ),
                [],
            )


class RepositoryChecks(RepoTest):
    def test_slot_identity_matches_the_legacy_record(self) -> None:
        _, slot = load_slot()
        self.assertEqual(slot.get("slot"), SLOT_ID)
        self.assertEqual(slot.get("skill"), "initiating-coverage")
        self.assertEqual(slot.get("acceptance-slot"), "SLOT-02")

    def test_registered_evidence_is_self_consistent(self) -> None:
        block, slot = load_slot()
        self.assertEqual(slot_evidence_problems(slot, block), [])


if __name__ == "__main__":
    unittest.main()
