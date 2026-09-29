#!/usr/bin/env python3
"""Export the WorkBuddy equity-research expert package from its single source.

Run from the repository root, no business-data arguments:

    python scripts/export_workbuddy_experts.py [--repo-root PATH]

Reads:
  workbuddy-experts/equity-research/{.codebuddy-plugin/plugin.json,agents/*,README.md,avatars/*}
  plugins/vertical-plugins/equity-research/skills/<name>/     (nine complete skill dirs)

Writes (atomically, no partial package left behind):
  out/workbuddy-experts/equity-research/

Exit 0 prints the file count, elapsed seconds and the sorted "relative-path  sha256"
list. Any missing source, escaping reference, symlink, forbidden or sensitive file
exits non-zero and leaves the previous package (if any) untouched. Nothing is ever
read back from a previous out/ package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path

PKG_REL = Path("workbuddy-experts/equity-research")
SKILL_SRC_REL = Path("plugins/vertical-plugins/equity-research/skills")
OUT_REL = Path("out/workbuddy-experts/equity-research")

# Fixed allowlist inside the package source (README/ACCEPTANCE are workspace records,
# not runtime package files: ACCEPTANCE.md is deliberately excluded).
ALLOWED_PKG_FILES = (
    ".codebuddy-plugin/plugin.json",
    "agents/equity-research.md",
    "README.md",
    "avatars/expert.png",
)

REQUIRED_MANIFEST_KEYS = (
    "name", "version", "author", "expertType", "agentName", "agents", "skills",
    "displayName", "profession", "displayDescription", "avatar", "categoryId",
    "defaultInitPrompt", "quickPrompts", "tags", "dependencies",
)
FORBIDDEN_MANIFEST_KEYS = ("teamInfo", "mcpServers", "tools", "mcp")
EXPECTED_CONNECTORS = ("wind-finance", "tdx-connector", "neodata", "westock-mcp")

SENSITIVE_NAME_RE = re.compile(
    r"(^\.env|\.env$|\.env\.|\.key$|\.pem$|\.p12$|\.pfx$|id_rsa|id_ed25519|"
    r"credentials|secrets?$|\.mcp\.json$|\.npmrc$|\.netrc$|_token$)",
    re.IGNORECASE,
)
SENSITIVE_CONTENT_RE = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key\s*[:=]\s*\S+|"
    r"secret\s*[:=]\s*\S+|password\s*[:=]\s*\S+|"
    r"[A-Za-z]:\\\\Users\\\\|/Users/[a-z0-9_.-]+/|/home/[a-z0-9_.-]+/)",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\]\(([^)\s]+)")
RELATIVE_REF_RE = re.compile(r"^\.{0,2}/")
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "#", "mention://")


class ExportError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_inside(candidate: Path, root: Path, what: str) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise ExportError(f"{what} escapes the package: {candidate}")
    return resolved


FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def link_kind(path: Path) -> str | None:
    """Label `path` when it is a link, else None.

    Windows junctions and mounted folders are reparse points but not symlinks, and
    `shutil.copyfile`/`copytree` dereference all of them, so both kinds must be
    refused by the same gate.
    """
    if path.is_symlink():
        return "symlink"
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return "reparse point (junction/mount)"
    return None


def check_no_links(root: Path, what: str) -> None:
    """Refuse links inside a **source** tree before anything is copied.

    Checking only the staged copy is not enough: the copy helpers dereference source
    links, so a link inside a skill source directory that points outside the package
    used to be staged as a regular file and pass a post-copy check (AC-07 escape).
    Never descends into a link, so a self-referencing link cannot loop.
    """
    stack = [root]
    while stack:
        current = stack.pop()
        kind = link_kind(current)
        if kind is not None:
            raise ExportError(f"{kind} not allowed in {what}: {current}")
        if not current.is_dir():
            continue
        for entry in os.scandir(current):
            child = Path(entry.path)
            kind = link_kind(child)
            if kind is not None:
                raise ExportError(f"{kind} not allowed in {what}: {child}")
            if entry.is_dir(follow_symlinks=False):
                stack.append(child)


def check_text_safety(path: Path, package_root: Path) -> None:
    """Reject escaping relative references, sensitive names and sensitive content.

    Markdown links resolve against the file's own directory; manifest-style string
    fields (`./agents/x.md`) resolve against the package root.
    """
    rel = path.as_posix()
    if SENSITIVE_NAME_RE.search(path.name):
        raise ExportError(f"sensitive file name refused: {rel}")
    if path.suffix.lower() not in (".md", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".ini"):
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    if SENSITIVE_CONTENT_RE.search(text):
        raise ExportError(f"sensitive content (credential/private path) refused: {rel}")
    for match in LINK_RE.finditer(text):
        target = match.group(1)
        if target.startswith(SKIP_LINK_PREFIXES):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", target) or target.startswith("/") or target.startswith("\\"):
            raise ExportError(f"absolute or non-http scheme reference refused in {rel}: {target}")
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            raise ExportError(f"reference target does not exist in package: {rel} -> {target}")
        ensure_inside(resolved, package_root, f"reference {rel} -> {target}")
    # JSON/YAML string fields such as "./skills/x" or "./avatars/x.png"
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExportError(f"invalid JSON in package: {rel}: {exc}")

        def walk(node: object) -> None:
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
            elif isinstance(node, str) and RELATIVE_REF_RE.match(node):
                target = (package_root / node).resolve()
                if not target.exists():
                    raise ExportError(f"manifest reference does not exist in package: {rel} -> {node}")
                ensure_inside(target, package_root, f"manifest reference {rel} -> {node}")

        walk(data)


def load_manifest(pkg_src: Path) -> dict:
    manifest_path = pkg_src / ".codebuddy-plugin/plugin.json"
    if not manifest_path.is_file():
        raise ExportError(f"missing manifest: {manifest_path}")
    check_no_links(manifest_path, "manifest")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ExportError(f"manifest is not valid JSON: {exc}")
    if not isinstance(manifest, dict):
        raise ExportError("manifest must be a JSON object")
    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            raise ExportError(f"manifest missing required key: {key}")
    for key in FORBIDDEN_MANIFEST_KEYS:
        if key in manifest:
            raise ExportError(f"manifest contains forbidden key: {key}")
    if manifest.get("expertType") != "agent":
        raise ExportError("manifest expertType must be 'agent'")
    if manifest.get("agentName") != "equity-research":
        raise ExportError("manifest agentName must be 'equity-research'")
    if list(manifest.get("agents") or []) != ["./agents/equity-research.md"]:
        raise ExportError("manifest agents must be [\"./agents/equity-research.md\"]")
    skills = list(manifest.get("skills") or [])
    if len(skills) != 9:
        raise ExportError(f"manifest must declare exactly 9 skills, got {len(skills)}")
    prompts = list(manifest.get("quickPrompts") or [])
    if len(prompts) != 3:
        raise ExportError(f"manifest must declare exactly 3 quickPrompts, got {len(prompts)}")
    if len(list(manifest.get("tags") or [])) != 3:
        raise ExportError("manifest must declare exactly 3 tags")
    first = prompts[0]
    # Target schema (validator 5.5.6): defaultInitPrompt is an i18n object and must
    # equal the first quickPrompt entry ("与第一条 quickPrompt 相同", SDD §3.1).
    if manifest.get("defaultInitPrompt") != first:
        raise ExportError("defaultInitPrompt must equal the first quickPrompt")
    connectors = list((manifest.get("dependencies") or {}).get("connectors") or [])
    if connectors != list(EXPECTED_CONNECTORS):
        raise ExportError(f"manifest connectors must be {list(EXPECTED_CONNECTORS)}, got {connectors}")
    return manifest


def build(repo_root: Path) -> tuple[Path, list[tuple[str, str]], float, int]:
    repo_root = repo_root.resolve()
    pkg_src = repo_root / PKG_REL
    skill_src = repo_root / SKILL_SRC_REL
    out_root = repo_root / OUT_REL
    out_parent = out_root.parent

    if not pkg_src.is_dir():
        raise ExportError(f"missing package source: {pkg_src}")
    if not skill_src.is_dir():
        raise ExportError(f"missing skill source root: {skill_src}")

    manifest = load_manifest(pkg_src)

    skill_dirs: list[tuple[str, Path]] = []
    for entry in manifest["skills"]:
        if not isinstance(entry, str) or not entry.startswith("./skills/"):
            raise ExportError(f"skill entry must look like ./skills/<name>: {entry!r}")
        name = entry[len("./skills/"):]
        if "/" in name or "\\" in name or not name:
            raise ExportError(f"illegal skill name in manifest: {entry!r}")
        source = skill_src / name
        if not source.is_dir():
            raise ExportError(f"missing skill source directory: {source}")
        if not (source / "SKILL.md").is_file():
            raise ExportError(f"skill source without SKILL.md: {source}")
        if str(source.resolve()).startswith(str(out_root.resolve())):
            raise ExportError(f"skill source must not come from out/: {source}")
        check_no_links(source, f"skill source {name}")
        skill_dirs.append((name, source))

    started = time.monotonic()
    out_parent.mkdir(parents=True, exist_ok=True)
    staging = out_parent / f".{out_root.name}.building-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        for rel in ALLOWED_PKG_FILES:
            source = pkg_src / rel
            if not source.is_file():
                raise ExportError(f"missing package source file: {source}")
            check_no_links(source, f"package source file {rel}")
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)

        for name, source in skill_dirs:
            shutil.copytree(source, staging / "skills" / name)

        check_no_links(staging, "staged package")
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                check_text_safety(path, staging)

        # Everything must resolve inside the staged package.
        for parent, dirnames, filenames in os.walk(staging):
            for name in list(dirnames) + list(filenames):
                ensure_inside(Path(parent) / name, staging, "package entry")

        if out_root.exists():
            previous = out_parent / f".{out_root.name}.previous-{os.getpid()}"
            if previous.exists():
                shutil.rmtree(previous)
            out_root.rename(previous)
            try:
                staging.rename(out_root)
            except OSError:
                previous.rename(out_root)
                raise
            shutil.rmtree(previous, ignore_errors=True)
        else:
            staging.rename(out_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    elapsed = time.monotonic() - started
    files = sorted(p for p in out_root.rglob("*") if p.is_file())
    digests = [(p.relative_to(out_root).as_posix(), sha256_file(p)) for p in files]
    return out_root, digests, elapsed, len(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the WorkBuddy equity-research expert package.")
    parser.add_argument("--repo-root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    try:
        out_root, digests, elapsed, count = build(repo_root)
    except ExportError as exc:
        print(f"EXPORT_FAILED: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"EXPORT_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"exported {count} file(s) to {out_root.as_posix()} in {elapsed:.2f}s")
    for rel, digest in digests:
        print(f"{rel}  {digest}")
    if elapsed > 120:
        print(f"EXPORT_SLOW: {elapsed:.2f}s exceeds the 120s budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
