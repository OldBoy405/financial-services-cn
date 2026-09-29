"""cmd-07 — reproducible package export plus the target-host verification receipts.

Three parts:
1. manifest contract (single agent, nine skills, three quickPrompts/tags, four connector
   ids, forbidden keys) — checked on the real package source;
2. export mechanics — exercised on a throwaway fixture tree (the real tree cannot export
   while the authorized avatar is missing): two runs must produce identical sorted
   path+sha256 sets within 120s, the nine skill directories must ship complete, and the
   missing-skill / escaping-reference / symlink / sensitive-file negatives must exit
   non-zero without leaving a partial package;
3. host verification — requires the real `expert-manager` / client receipts; a local
   self-made validator is not a substitute (NFR-03).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from _support import (
    ACCEPTANCE,
    AGENT,
    AVATAR,
    EXPORT_SCRIPT,
    HOST_EVIDENCE,
    MANIFEST,
    OUT_PKG,
    ROOT,
    SKILL_SRC,
    NINE_PAIRS,
    RepoTest,
)

EXPECTED_CONNECTORS = ["wind-finance", "tdx-connector", "neodata", "westock-mcp"]
FORBIDDEN_KEYS = ("teamInfo", "mcpServers", "tools", "mcp")
PACKAGE_REL = Path("workbuddy-experts/equity-research")
FIXTURE_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)


def export(repo_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--repo-root", str(repo_root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(repo_root),
    )


def digests(package: Path) -> list[tuple[str, str]]:
    if not package.is_dir():
        return []
    out = []
    for path in sorted(p for p in package.rglob("*") if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append((path.relative_to(package).as_posix(), digest))
    return out


def make_escape_link(link: Path, target: Path) -> str:
    """Create a real link at `link` -> `target`; return which mechanism was used.

    A symbolic link needs SeCreateSymbolicLinkPrivilege on Windows; an NTFS directory
    junction needs no privilege and `shutil` copy helpers dereference it exactly the
    same way, so the AC-07 escape negative can run for real on this host instead of
    being skipped (SDD §7: link targets stay inside the package).
    """
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
        return "symlink"
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                 capture_output=True, text=True)
        if created.returncode == 0:
            return "junction"
    raise unittest.SkipTest("no link mechanism available on this host")


def make_fixture(root: Path) -> Path:
    fixture = root / "repo"
    (fixture / PACKAGE_REL / "avatars").mkdir(parents=True)
    (fixture / PACKAGE_REL / ".codebuddy-plugin").mkdir(parents=True)
    (fixture / PACKAGE_REL / "agents").mkdir(parents=True)
    shutil.copyfile(MANIFEST, fixture / PACKAGE_REL / ".codebuddy-plugin" / "plugin.json")
    shutil.copyfile(AGENT, fixture / PACKAGE_REL / "agents" / "equity-research.md")
    shutil.copyfile(PACKAGE_REL / "README.md", fixture / PACKAGE_REL / "README.md") if False else None
    shutil.copyfile(ROOT / PACKAGE_REL / "README.md", fixture / PACKAGE_REL / "README.md")
    (fixture / PACKAGE_REL / "avatars" / "expert.png").write_bytes(FIXTURE_PNG)
    skills = fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills"
    skills.parent.mkdir(parents=True)
    shutil.copytree(SKILL_SRC, skills)
    (fixture / "scripts").mkdir()
    shutil.copyfile(EXPORT_SCRIPT, fixture / "scripts" / "export_workbuddy_experts.py")
    return fixture


class ExportAndHost(RepoTest):
    def test_manifest_contract(self) -> None:
        manifest = self.load_manifest()
        self.assertEqual(manifest["expertType"], "agent")
        self.assertEqual(manifest["agentName"], "equity-research")
        self.assertEqual(manifest["agents"], ["./agents/equity-research.md"])
        self.assertEqual(len(manifest["skills"]), 9, "the manifest must declare nine skills")
        self.assertEqual(manifest["skills"], [f"./skills/{skill}" for _, skill in NINE_PAIRS])
        self.assertEqual(len(manifest["quickPrompts"]), 3)
        self.assertEqual(len(manifest["tags"]), 3)
        first = manifest["quickPrompts"][0]
        self.assertEqual(manifest["defaultInitPrompt"], first,
                         "defaultInitPrompt must equal the first quickPrompt")
        self.assertEqual(list(manifest["dependencies"]["connectors"]), EXPECTED_CONNECTORS)
        for key in FORBIDDEN_KEYS:
            self.assertNotIn(key, manifest, f"manifest must not declare {key}")
            self.assertNotIn(key, manifest.get("dependencies", {}), f"dependencies must not declare {key}")
        self.assertNotIn("./commands", json.dumps(manifest))
        self.assertFalse((ROOT / ".mcp.json").exists(), ".mcp.json must not be added")

    def test_real_export_reports_the_blocking_prerequisite(self) -> None:
        before = digests(OUT_PKG)
        proc = export(ROOT)
        if proc.returncode == 0:
            after = digests(OUT_PKG)
            self.assertGreater(len(after), 0, "a successful export must publish files")
            shipped = {rel for rel, _ in after}
            for _, skill in NINE_PAIRS:
                self.assertTrue(any(r.startswith(f"skills/{skill}/") for r in shipped),
                                f"exported package is missing skill {skill}")
            self.assertFalse(any(r == "ACCEPTANCE.md" for r in shipped),
                             "ACCEPTANCE.md must not ship inside the package")
            return
        self.assertEqual(after_default := digests(OUT_PKG), before,
                         "a failed export must not leave a partial package behind")
        self.assertTrue("avatars" in proc.stderr or "missing package source file" in proc.stderr,
                        f"real export failed for an undeclared reason: {proc.stderr.strip()[:300]}")
        self.assertFalse(AVATAR.is_file(),
                         "the avatar must be a real authorized asset, never a generated placeholder")

    def test_fixture_export_is_reproducible_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = make_fixture(Path(tmp))
            started = time.monotonic()
            first = export(fixture)
            self.assertEqual(first.returncode, 0, f"fixture export failed: {first.stderr.strip()[:400]}")
            elapsed = time.monotonic() - started
            self.assertLessEqual(elapsed, 120, "single export must stay within the 120s budget")
            package = fixture / "out" / "workbuddy-experts" / "equity-research"
            first_set = digests(package)
            second = export(fixture)
            self.assertEqual(second.returncode, 0, f"second export failed: {second.stderr.strip()[:400]}")
            second_set = digests(package)
            self.assertEqual(first_set, second_set,
                             "two consecutive exports must produce identical path+sha256 sets")
            shipped = {rel for rel, _ in second_set}
            for _, skill in NINE_PAIRS:
                self.assertTrue(any(r.startswith(f"skills/{skill}/") for r in shipped),
                                f"export missing skill {skill}")
            self.assertTrue(any(r == "agents/equity-research.md" for r in shipped))
            self.assertTrue(any(r == ".codebuddy-plugin/plugin.json" for r in shipped))
            self.assertFalse(any(r.startswith("skills/") and r.count("/") == 1 for r in shipped),
                             "skills must be directories, not flat files")
            with_references = [r for r in shipped if "/references/" in r or "/assets/" in r]
            self.assertTrue(with_references, "references/assets must ship with the skill directories")
            self.assertFalse(any(r.endswith("ACCEPTANCE.md") for r in shipped),
                             "ACCEPTANCE.md is a workspace record, not a package file")
            self.assertFalse(any(r.startswith("tests/") for r in shipped),
                             "test modules must not ship inside the package")
            self.assertFalse(any(r.startswith("out/") or "sample" in r.lower() for r in shipped),
                             "sample originals must never ship inside the package")
            self.assertTrue((package / "skills" / "initiating-coverage" / "SKILL.md").is_file())

    def test_fixture_negatives_fail_atomically(self) -> None:
        scenarios = {
            "missing-skill": lambda fixture: shutil.rmtree(
                fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills" / "thesis-tracker"),
            "escaping-reference": lambda fixture: (
                fixture / PACKAGE_REL / "agents" / "equity-research.md").write_text(
                (fixture / PACKAGE_REL / "agents" / "equity-research.md").read_text(encoding="utf-8")
                + "\n[escape](../../../../outside.md)\n", encoding="utf-8"),
            "sensitive-file": lambda fixture: (
                fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills" / "model-update"
                / ".env").write_text("api_key = not-a-real-secret\n", encoding="utf-8"),
            "missing-avatar": lambda fixture: (fixture / PACKAGE_REL / "avatars" / "expert.png").unlink(),
        }
        for name, mutate in scenarios.items():
            with self.subTest(scenario=name), tempfile.TemporaryDirectory() as tmp:
                fixture = make_fixture(Path(tmp))
                self.assertEqual(export(fixture).returncode, 0, f"{name}: fixture must export first")
                package = fixture / "out" / "workbuddy-experts" / "equity-research"
                good = digests(package)
                mutate(fixture)
                failed = export(fixture)
                self.assertNotEqual(failed.returncode, 0, f"{name}: negative case must exit non-zero")
                self.assertEqual(digests(package), good,
                                 f"{name}: previous valid package must survive a failed export "
                                 "(no partial package may become installable)")

    def test_source_escape_link_is_refused_and_never_copied(self) -> None:
        """AC-07 escape negative, executed for real (no skip) on this host.

        The source skill tree carries a link to a directory outside the package; the
        copy helpers would dereference it and stage the outside file as a regular file,
        which a post-copy check can no longer see. The export must fail on the source
        link itself and must never copy the outside content anywhere.
        """
        with tempfile.TemporaryDirectory() as tmp:
            fixture = make_fixture(Path(tmp))
            self.assertEqual(export(fixture).returncode, 0, "fixture must export first")
            package = fixture / "out" / "workbuddy-experts" / "equity-research"
            good = digests(package)
            outside = Path(tmp) / "outside"
            outside.mkdir()
            marker = "package-external content that must never ship"
            (outside / "escaped.md").write_text(marker + "\n", encoding="utf-8")
            link = (fixture / "plugins" / "vertical-plugins" / "equity-research"
                    / "skills" / "model-update" / "escaped")
            kind = make_escape_link(link, outside)
            failed = export(fixture)
            self.assertNotEqual(failed.returncode, 0,
                                f"a source {kind} pointing outside the package must be refused")
            self.assertIn("EXPORT_FAILED", failed.stderr)
            self.assertTrue("not allowed" in failed.stderr and ("symlink" in failed.stderr or "junction" in failed.stderr),
                            f"refusal must name the source link, got: {failed.stderr.strip()[:300]}")
            self.assertEqual(digests(package), good,
                             "a refused export must leave the previous valid package untouched")
            for path in package.rglob("*"):
                if path.is_file():
                    self.assertNotIn(marker, path.read_text(encoding="utf-8", errors="replace"),
                                     f"package-external content leaked into {path.name}")

    def test_ancestor_escape_link_is_refused_and_never_copied(self) -> None:
        """AC-07 escape negative on a copy source's **ancestor** directories.

        `check_no_links(source)` inspects the source and its descendants only, so a link
        at `agents/` or on the skills source root is invisible to it while
        `shutil.copyfile`/`copytree` still dereference it. Every level of the source
        path must be refused before any read or copy (B-02).
        """
        marker = "ancestor-escape content that must never ship"
        cases = {
            # ancestor of a package source file (agents/equity-research.md)
            "package-file-parent": lambda fixture, outside: (
                shutil.rmtree(fixture / PACKAGE_REL / "agents"),
                (outside / "equity-research.md").write_text(marker + "\n", encoding="utf-8"),
                make_escape_link(fixture / PACKAGE_REL / "agents", outside),
            ),
            # ancestor of every skill source dir (skills/<name>)
            "skill-source-parent": lambda fixture, outside: (
                shutil.move(str(fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills"),
                            str(outside)),
                (outside / "skills" / "model-update" / "leak-marker.md").write_text(marker + "\n", encoding="utf-8"),
                make_escape_link(fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills",
                                 outside / "skills"),
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(scenario=name), tempfile.TemporaryDirectory() as tmp:
                fixture = make_fixture(Path(tmp))
                self.assertEqual(export(fixture).returncode, 0, f"{name}: fixture must export first")
                package = fixture / "out" / "workbuddy-experts" / "equity-research"
                good = digests(package)
                outside = Path(tmp) / "outside"
                outside.mkdir()
                mutate(fixture, outside)
                failed = export(fixture)
                self.assertNotEqual(failed.returncode, 0,
                                    f"{name}: an ancestor escape link must be refused")
                self.assertIn("EXPORT_FAILED", failed.stderr)
                self.assertTrue("not allowed" in failed.stderr
                                and ("symlink" in failed.stderr or "junction" in failed.stderr),
                                f"{name}: refusal must name the ancestor link, got: {failed.stderr.strip()[:300]}")
                self.assertEqual(digests(package), good,
                                 f"{name}: a refused export must leave the previous valid package untouched")
                for path in package.rglob("*"):
                    if path.is_file():
                        self.assertNotIn(marker, path.read_text(encoding="utf-8", errors="replace"),
                                         f"{name}: package-external content leaked into {path.name}")

    def test_host_receipts_required(self) -> None:
        self.assertTrue(
            HOST_EVIDENCE.is_file(),
            "no target-host receipts: AC-07 / NFR-03 require the real target WorkBuddy version and the "
            "actual `expert-manager` init/validate/register steps plus the local install/summon "
            "observation (client version, validator version, raw output, evidence hashes, author email "
            "and avatar authorization). A locally self-made validator is not a substitute. "
            f"`expert-manager` is not present on this machine (found={bool(shutil.which('expert-manager'))}); "
            f"expected receipts at {HOST_EVIDENCE.relative_to(ROOT).as_posix()}",
        )
        receipts = json.loads(HOST_EVIDENCE.read_text(encoding="utf-8"))
        for field in ("client", "validator", "steps", "install", "summon", "author", "avatar-authorization"):
            self.assertIn(field, receipts, f"host receipts missing {field}")
        for step in receipts["steps"]:
            for field in ("command", "output-file", "sha256", "exit-code"):
                self.assertIn(field, step, f"validator step missing {field}")
            raw = ROOT / step["output-file"]
            self.assertTrue(raw.is_file(), f"validator raw output missing: {step['output-file']}")
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), step["sha256"])
        self.assertEqual(receipts["avatar-authorization"]["path"],
                         (PACKAGE_REL / "avatars" / "expert.png").as_posix())
        self.assertEqual(hashlib.sha256(AVATAR.read_bytes()).hexdigest(),
                         receipts["avatar-authorization"]["sha256"])
        self.assertIn("connectors", receipts, "the host verdict on the four connector ids must be recorded")

    def test_host_summon_receipt_matches_the_acceptance_record(self) -> None:
        """B-05: a summon claim needs a real observation, never an export exit 0.

        The receipt may only support "the expert was summoned" when it carries an
        observed status with its own timestamped evidence (UI observation or host
        output); while the status is pending the versioned record must declare it as
        untested instead of citing the session records as proof. An unknown status
        passes neither branch.
        """
        receipts = json.loads(HOST_EVIDENCE.read_text(encoding="utf-8"))
        summon = receipts["summon"]
        status = str(summon.get("status", "")).strip()
        self.assertTrue(status, "the host receipt must record the summon status")
        section3 = ACCEPTANCE.read_text(encoding="utf-8").split("## 3. 包校验", 1)[1].split("## 4.", 1)[0]
        if status.startswith("pending"):
            self.assertIn("待实测", section3,
                          "a pending summon receipt must be recorded in ACCEPTANCE §3 as untested")
            self.assertNotRegex(section3, r"已召唤|召唤：在\s*WorkBuddy",
                                "a pending summon receipt must not be claimed as an observed summon")
        else:
            self.assertEqual(status, "observed",
                             f"summon status must be 'observed' or 'pending-*', got {status!r}")
            for field in ("observed-at", "evidence-file", "sha256"):
                self.assertTrue(str(summon.get(field, "")).strip(),
                                f"an observed summon must record {field} (real UI observation / host output)")
            raw = ROOT / summon["evidence-file"]
            self.assertTrue(raw.is_file(), f"summon observation evidence missing: {summon['evidence-file']}")
            self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), summon["sha256"],
                             "summon observation hash mismatch")


if __name__ == "__main__":
    unittest.main()
