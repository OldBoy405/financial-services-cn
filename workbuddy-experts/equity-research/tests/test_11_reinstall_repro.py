"""cmd-04 — package 0.11.0, the target-validation-driven conditional correction and the reinstall repro (FR-08 -> AC-08).

Reads `evidence/reinstall.md` (RIN/ENV/REP + the measured export/install machine block + the delivery anchors),
`evidence/declarations.md` (DCL), `index.md#RunWindow`, the real `plugin.json` and the export script's own
`ALLOWED_PKG_FILES` / `EXPECTED_CONNECTORS` (dep-3: compared, never copied). The export is re-run twice here for
real and its path+sha256 set is checked against the value recorded in the ledger, so RIN-01 is recomputable
inside the repo instead of being a transcription.

AC-08's install-side checks are mechanical on purpose: `test_install_and_summon_receipt_for_final_package`
requires a `通过` new-session row plus every `REP` row reproduced, and `check_rin` refuses a `通过` new-session/install
row without a measured validator version, a client `installedAt=` receipt and a final-package manifest `sha256=`.
As of the third dispatch the 0.11.0 package IS validated, isolated-from-0.10.0 and installed (`RIN-02`/`RIN-04`/`RIN-05`),
`REP-01..03` are reproduced post-install, and `RIN-06` holds on the client-side collection receipt plus the node's same-machine
recompute (`ENV-12`/`ENV-13`). The caliber for `RIN-06` is the owner's written authorization recorded verbatim in
`reinstall.md#登记口径` 第 10 条, together with the two facts that conflict with it; no assertion here was relaxed to get green —
only ledger row values changed, on new evidence.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

import _evidence
import _support
from _evidence import (
    EVIDENCE,
    ROOT,
    check_in_run_window,
    check_no_sensitive,
    load_table,
    read_run_window,
    require_ids,
    sha256_bytes,
)
from _support import AGENT, EXPORT_SCRIPT, MANIFEST, OUT_PKG, SKILL_SRC, RepoTest
from test_07_export_host import digests, export, make_fixture
from test_09_query_traceability import PRIVATE_WIN_PATH_RE

AGENT_SECTION = "## 数据动作判定顺序与降级/停止行为（FR-06 / FR-07）"
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
TARGET_VERSION = "0.11.0"
RIN_STAGES = ("导出", "目标校验", "条件性修正", "卸下或隔离", "安装", "新会话", "逐项复现")
CLIENT_STAGES = ("目标校验", "卸下或隔离", "安装", "新会话", "逐项复现")
PACKAGE_SHA_RE = re.compile(r"sha256=([0-9a-f]{64})")
INSTALLED_AT_RE = re.compile(r"installedAt=\d{4}-\d{2}-\d{2}T[\d:.]+Z")
PACKAGE_SPLIT_RE = re.compile(r"实际通过 (\d+) 行[\s\S]{0,200}?未执行缺口 (\d+) 行")
REPACKED_RE = re.compile(r"包=([0-9][0-9.]*)")
CLIENT_RE = re.compile(r"客户端=(\S+)")
VALIDATOR_RE = re.compile(r"校验器=(\S+)")
ENTRY_NAME = "CWServ"


def load_export_module():
    spec = importlib.util.spec_from_file_location("export_workbuddy_experts", EXPORT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # module body defines constants only (__main__ guarded)
    return module


def load_machine_block(file_name: str, heading: str) -> dict:
    text = (EVIDENCE / file_name).read_text(encoding="utf-8")
    start = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    if not start:
        raise AssertionError(f"{file_name} 缺 `{heading}` 节")
    block = re.search(r"```json\s*(.*?)\s*```", text[start.end():], re.DOTALL)
    if not block:
        raise AssertionError(f"{file_name}#{heading} 缺 json 机器块")
    data = json.loads(block.group(1))
    if not isinstance(data, dict) or not data:
        raise AssertionError(f"{file_name}#{heading} 机器块为空")
    return data


def digest_set_sha(package: Path) -> str:
    """One hash over the whole sorted (relative path, per-file sha256) set of an export."""
    joined = "\n".join(f"{rel}  {sha}" for rel, sha in sorted(digests(package)))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def check_manifest_version(manifest: dict) -> None:
    got = str(manifest.get("version", ""))
    if got != TARGET_VERSION:
        raise AssertionError(f"plugin.json#version={got!r} != 0.11.0（§5 包版本行；G4 不改其它字段）")


def check_connectors(manifest: dict, exp) -> None:
    connectors = list(manifest.get("dependencies", {}).get("connectors", []))
    if len(connectors) != 4 or set(connectors) != set(exp.EXPECTED_CONNECTORS):
        raise AssertionError(
            f"dependencies.connectors={connectors} 与导出脚本 EXPECTED_CONNECTORS="
            f"{list(exp.EXPECTED_CONNECTORS)} 不是同一组四个标识（§4.7：修正须两边同步）")
    if connectors != list(exp.EXPECTED_CONNECTORS):
        raise AssertionError(f"connectors 数组元素顺序漂移：{connectors}")


def check_exported_files(package: Path, exp) -> None:
    if not package.is_dir():
        raise AssertionError(f"导出物不存在：{package.relative_to(ROOT).as_posix()}")
    files = [p for p in package.rglob("*") if p.is_file()]
    if not files:
        raise AssertionError("导出物为空")
    rel = {p.relative_to(package).as_posix() for p in files}
    if any(r.startswith("evidence/") or r == "evidence" for r in rel):
        raise AssertionError(f"导出物含 evidence/ 路径（§3.1：evidence/** 不是包文件）：{sorted(r for r in rel if 'evidence' in r)}")
    top = {r for r in rel if not r.startswith("skills/")}
    if top != set(exp.ALLOWED_PKG_FILES):
        raise AssertionError(f"包内非技能文件集 != ALLOWED_PKG_FILES：多出 {sorted(top - set(exp.ALLOWED_PKG_FILES))}，"
                             f"缺少 {sorted(set(exp.ALLOWED_PKG_FILES) - top)}")
    for path in files:
        where = path.as_posix()
        check_no_sensitive(path.read_bytes().decode("utf-8", errors="replace"), where=where)


def check_two_exports(exp_module_run, recorded: dict) -> None:
    first = time.monotonic()
    run1 = exp_module_run(ROOT)
    set1 = digests(OUT_PKG)
    run2 = exp_module_run(ROOT)
    set2 = digests(OUT_PKG)
    if run1.returncode != 0 or run2.returncode != 0:
        raise AssertionError(f"两次导出必须都成功退出：{run1.returncode}/{run2.returncode} "
                             f"{(run1.stderr or run2.stderr).strip()[:200]}")
    elapsed = round(time.monotonic() - first, 3)
    if set1 != set2:
        raise AssertionError("两次导出的相对路径与逐文件 SHA-256 集合不一致（§3.1 可复现导出）")
    if len(set1) != recorded.get("files"):
        raise AssertionError(f"导出件数 {len(set1)} != reinstall.md 登记的 {recorded.get('files')}")
    actual = digest_set_sha(OUT_PKG)
    if actual != recorded.get("digest_set_sha256"):
        raise AssertionError(f"导出集合哈希现算 {actual} != RIN-01 登记的 {recorded.get('digest_set_sha256')}")
    if elapsed > 120:
        raise AssertionError(f"两次导出合计 {elapsed}s 超 120s 预算")


def assert_negative_exited_failed(proc: subprocess.CompletedProcess, name: str) -> None:
    if proc.returncode == 0:
        raise AssertionError(f"{name} 负例退出码为 0：缺失/逃逸必须让导出失败（§3.1 不残包）")


def check_rin(rows: list[dict], manifest: dict, client_token: str, dcl: list[dict],
              old_installed_sha: str) -> None:
    require_ids(rows, "RIN", minimum=7)
    if len(rows) != 7:
        raise AssertionError(f"RIN 行必须恰为七阶段（§3.3），实为 {len(rows)}")
    for i, row in enumerate(rows):
        for col in ("ID", "阶段", "实际步骤", "客户端/校验器/包版本", "结果", "证据引用"):
            if not row[col].strip():
                raise AssertionError(f"RIN 行 {row['ID']} 字段 {col} 为空")
        stage = row["阶段"].strip()
        if not stage.startswith(RIN_STAGES[i]):
            raise AssertionError(f"RIN 行 {row['ID']} 阶段 {stage[:12]!r} 不是第 {i + 1} 步 {RIN_STAGES[i]!r}")
        version_cell = row["客户端/校验器/包版本"]
        packed = REPACKED_RE.search(version_cell)
        if not packed or packed.group(1) != manifest["version"]:
            raise AssertionError(
                f"RIN 行 {row['ID']} 包版本 {packed and packed.group(1)!r} 与 manifest#version="
                f"{manifest['version']!r} 双向不一致")
        client = CLIENT_RE.search(version_cell)
        if not client or client.group(1) not in {"未参与", client_token}:
            raise AssertionError(
                f"RIN 行 {row['ID']} 客户端版本 {client and client.group(1)!r} 既非 未参与 也非 "
                f"index.md#RunWindow 现值 {client_token!r}")
        result = row["结果"].strip()
        cited = row["证据引用"]
        if result == "通过":
            if "不适用" in cited:
                raise AssertionError(f"RIN 行 {row['ID']} 记 通过 却引用不适用项")
            if stage.startswith(CLIENT_STAGES):
                validator = VALIDATOR_RE.search(version_cell)
                if not validator or validator.group(1) in {"未实测", "未参与"}:
                    raise AssertionError(
                        f"RIN 行 {row['ID']} 为 {stage[:6]} 阶段却无实测校验器版本：目标机校验未执行不得签通过")
                if not INSTALLED_AT_RE.search(cited):
                    raise AssertionError(f"RIN 行 {row['ID']} 签通过但无客户端注册回执 installedAt 实测值")
                shipped = PACKAGE_SHA_RE.findall(cited)
                if not shipped:
                    raise AssertionError(f"RIN 行 {row['ID']} 签通过但未登记安装件 manifest 的 sha256 实测值")
                if shipped[-1] == old_installed_sha:
                    raise AssertionError(
                        f"RIN 行 {row['ID']} 引用的回执是修正前/前版本包（{old_installed_sha[:12]}…），"
                        "不得充当最终包完成标志（§3.3）")
        elif result.startswith("阻塞"):
            if not cited.startswith("不适用（未执行"):
                raise AssertionError(f"RIN 行 {row['ID']} 缺口行的证据引用必须以 不适用（未执行 起首")
            if "可重授权路径" not in cited:
                raise AssertionError(f"RIN 行 {row['ID']} 缺口行缺可重授权路径")
        elif result.startswith("不适用（"):
            if RIN_STAGES[i] != "条件性修正":
                raise AssertionError(f"RIN 行 {row['ID']} 只有条件性修正阶段可取 不适用")
            if not all(r["结论"].startswith("无需修正") for r in dcl):
                raise AssertionError(f"RIN 行 {row['ID']} 记 不适用（无条件性修正）但 DCL 有修正结论")
        else:
            raise AssertionError(f"RIN 行 {row['ID']} 结果 {result!r} 不在 通过/阻塞/不适用 封闭取值")


def check_rin_split(rows: list[dict], text: str) -> None:
    passed = [r["ID"] for r in rows if r["结果"] == "通过"]
    gaps = [r["ID"] for r in rows if r["结果"].startswith("阻塞")]
    declared = PACKAGE_SPLIT_RE.search(text)
    if not declared:
        raise AssertionError("reinstall.md 前言未声明通过/未执行缺口的行数分布")
    if (int(declared.group(1)), int(declared.group(2))) != (len(passed), len(gaps)):
        raise AssertionError(
            f"前言声明 通过{declared.group(1)}/缺口{declared.group(2)} != 实测 通过{passed}/缺口{gaps}")


def check_env(rows: list[dict]) -> None:
    require_ids(rows, "ENV", minimum=4)
    for row in rows:
        for col in ("ID", "排查对象", "方法", "结果", "影响"):
            if not row[col].strip():
                raise AssertionError(f"ENV 行 {row['ID']} 字段 {col} 为空")
        if not row["方法"].strip():
            raise AssertionError(f"ENV 行 {row['ID']} 未记排查方法")
        if row["结果"].startswith("阻塞") and "路径" not in row["影响"]:
            raise AssertionError(f"ENV 行 {row['ID']} 残留导致阻塞却未写明清理/重授权路径")


def check_rep(rows: list[dict]) -> None:
    require_ids(rows, "REP", minimum=3)
    for row in rows:
        for col in ("ID", "复现项", "结果", "证据引用", "是否可复现"):
            if not row[col].strip():
                raise AssertionError(f"REP 行 {row['ID']} 字段 {col} 为空")
        value = row["是否可复现"].strip()
        if not value.startswith(("是", "否", "未验证")):
            raise AssertionError(f"REP 行 {row['ID']} 是否可复现 {value!r} 不在 是/否/未验证")
        if value != "是" and not row["结果"].startswith("阻塞"):
            raise AssertionError(f"REP 行 {row['ID']} 未复现却未记阻塞结论")
        if value == "是" and "不适用" in row["证据引用"]:
            raise AssertionError(f"REP 行 {row['ID']} 记可复现但证据引用为不适用")


def check_rep_blocks_domain(rep: list[dict]) -> None:
    """§2.2 不变量 4：任一 REP 未复现 ⇒ 受影响域不得为 可用（域状态行归 TASK-05 落盘）。"""
    path = _evidence.EVIDENCE / "domain-readiness.md"
    if not path.is_file():
        return
    domains = load_table("domain-readiness.md", "域状态")
    if any(r["是否可复现"] != "是" for r in rep):
        adopted = [r["ID"] for r in domains if r["状态"] == "可用"]
        if adopted:
            raise AssertionError(
                f"REP 存在未复现项，域 {adopted} 不得判定为 可用（§2.2 不变量 4）")


def check_dcl(rows: list[dict]) -> None:
    require_ids(rows, "DCL", minimum=1)
    for row in rows:
        for col in ("ID", "触发",  "涉及文件", "前后差异", "回归范围", "回归证据", "结论"):
            if not row[col].strip():
                raise AssertionError(f"DCL 行 {row['ID']} 字段 {col} 为空")
        if "对比对象" not in row["触发"] and "实测" not in row["触发"]:
            raise AssertionError(f"DCL 行 {row['ID']} 触发未写对比对象与目标机实测结果（§4.7）")
        conclusion = row["结论"].strip()
        if conclusion.startswith("无需修正"):
            if "零差异" not in row["前后差异"] and "未修正" not in row["前后差异"]:
                raise AssertionError(f"DCL 行 {row['ID']} 结论 无需修正 但前后差异未记零差异/未修正")
            if "依据" not in row["结论"]:
                raise AssertionError(f"DCL 行 {row['ID']} 无需修正缺核查依据")
        elif conclusion.startswith("修正"):
            if not row["回归证据"].strip() or row["回归范围"].startswith("不适用"):
                raise AssertionError(f"DCL 行 {row['ID']} 发生修正必须有受影响回归范围与证据（§4.7）")
        else:
            raise AssertionError(f"DCL 行 {row['ID']} 结论 {conclusion!r} 不在 无需修正/修正/阻塞")


class ReinstallRepro(RepoTest):
    def setUp(self) -> None:
        self.exp = load_export_module()
        self.text = (EVIDENCE / "reinstall.md").read_text(encoding="utf-8")
        self.declarations_text = (EVIDENCE / "declarations.md").read_text(encoding="utf-8")
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.rin = load_table("reinstall.md", "重装步骤")
        self.env = load_table("reinstall.md", "环境依赖排查")
        self.rep = load_table("reinstall.md", "重装后复现")
        self.dcl = load_table("declarations.md", "声明修正")
        self.measured = load_machine_block("reinstall.md", "导出与安装态实测")
        self.run_window = read_run_window()
        self.client_token = self.run_window["客户端版本"].split("（")[0].strip()
        self.old_installed_sha = self.measured["安装态对照"]["installed_0.10.0_manifest_sha256"]

    # --- FR-08: package version and the connector identifiers ---
    def test_manifest_version_and_fields(self) -> None:
        check_manifest_version(self.manifest)
        self.assertEqual(self.manifest["expertType"], "agent")
        self.assertEqual(self.manifest["agentName"], "equity-research")
        self.assertEqual(len(self.manifest["skills"]), 9, "九项技能声明不得因升版漂移")

    def test_connectors_match_export_constant(self) -> None:
        check_connectors(self.manifest, self.exp)

    def test_export_is_reproducible_and_within_contract(self) -> None:
        check_two_exports(export, self.measured["导出两次一致"])
        check_exported_files(OUT_PKG, self.exp)
        exported_manifest = json.loads((OUT_PKG / ".codebuddy-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(exported_manifest["version"], TARGET_VERSION,
                         "导出物内的版本行必须是 0.11.0（§5 显式写入，钩子不覆盖 .codebuddy-plugin）")

    def test_agent_declaration_section_ships_in_package(self) -> None:
        shipped = (OUT_PKG / "agents" / "equity-research.md").read_text(encoding="utf-8")
        self.assertIn(AGENT_SECTION, shipped, "重装包内必须已含 TASK-03 新增节（§6 消费条件）")

    def test_export_negatives_exit_nonzero(self) -> None:
        scenarios = {
            "missing-skill-dir": lambda fixture: shutil.rmtree(
                fixture / "plugins" / "vertical-plugins" / "equity-research" / "skills" / "thesis-tracker"),
            "missing-agent-dir": lambda fixture: shutil.rmtree(
                fixture / "workbuddy-experts" / "equity-research" / "agents"),
        }
        for name, mutate in scenarios.items():
            with self.subTest(scenario=name), tempfile.TemporaryDirectory() as tmp:
                fixture = make_fixture(Path(tmp))
                self.assertEqual(export(fixture).returncode, 0, f"{name}: 夹具须先导出成功")
                package = fixture / "out" / "workbuddy-experts" / "equity-research"
                good = digests(package)
                mutate(fixture)
                failed = export(fixture)
                assert_negative_exited_failed(failed, name)
                self.assertEqual(digests(package), good,
                                 f"{name}: 失败导出不得留下半成品包")

    # --- FR-08: the three ledgers ---
    def test_rin_rows_complete_and_versions_cross_checked(self) -> None:
        check_rin(self.rin, self.manifest, self.client_token, self.dcl, self.old_installed_sha)

    def test_rin_split_declared(self) -> None:
        check_rin_split(self.rin, self.text)

    def test_env_rows_complete(self) -> None:
        check_env(self.env)

    def test_rep_rows_complete(self) -> None:
        check_rep(self.rep)

    def test_rep_unreproducible_blocks_domain_adopted(self) -> None:
        check_rep_blocks_domain(self.rep)

    def test_dcl_rows_have_basis(self) -> None:
        check_dcl(self.dcl)

    def test_entry_name_absent_from_declared_surfaces(self) -> None:
        """DCL-02 的依据：FC-02 的不符 entry 名不在本 CR 的任何包内声明面（因此无修正对象）。"""
        self.assertTrue(OUT_PKG.is_dir(), "导出物不存在，DCL-02 的归属结论无从机检")
        faces = [OUT_PKG, AGENT.parent, SKILL_SRC]
        hits = [p.relative_to(ROOT).as_posix() for base in faces if base.is_dir()
                for p in base.rglob("*")
                if p.is_file() and ENTRY_NAME in p.read_bytes().decode("utf-8", errors="replace")]
        self.assertEqual(hits, [], f"entry 名出现在包内声明面，DCL-02 的归属结论失效：{hits}")

    def test_sensitive_scan(self) -> None:
        for name, text in (("evidence/reinstall.md", self.text), ("evidence/declarations.md", self.declarations_text)):
            check_no_sensitive(text, where=name)
            self.assertIsNone(PRIVATE_WIN_PATH_RE.search(text), f"{name} 含私有绝对路径")

    def test_delivery_anchors_are_hex_and_cited_rows_exist(self) -> None:
        anchors = load_machine_block("reinstall.md", "投递件哈希锚点")
        for key, value in anchors.items():
            if key == "说明":
                continue
            self.assertTrue(HEX64.match(value), f"锚点 {key} 非 64 位十六进制实测值")
            self.assertFalse(REPACKED_RE.search(key) and PRIVATE_WIN_PATH_RE.search(key), f"锚点 {key} 含私有绝对路径")

    def test_run_window_client_version_is_measured(self) -> None:
        self.assertTrue(re.match(r"\A\d+\.\d+\.\d+", self.client_token),
                        f"index.md#RunWindow 客户端版本 {self.client_token!r} 不是实测版本号")
        # 校验器版本与 RIN 实测回执双向绑定：无 通过 回执时不得预填，有回执时不得滞留在 待确认（§4.6、ENV-05）。
        cell = self.run_window["校验器版本"].split("（")[0].strip()
        measured = set()
        for row in self.rin:
            if row["结果"] != "通过":
                continue
            validator = VALIDATOR_RE.search(row["客户端/校验器/包版本"])
            if validator and validator.group(1) not in {"未实测", "未参与"}:
                measured.add(validator.group(1))
        if cell == "待确认":
            self.assertEqual(measured, set(),
                             "已有带实测校验器的 通过 RIN 行，校验器版本不得滞留在 待确认")
        else:
            self.assertIn(cell, measured,
                          "index.md#RunWindow 校验器版本必须等于某条 通过 RIN 行的实测校验器值，不得预填")

    # --- AC-08: the install-side receipts the target machine has still not produced ---
    def test_target_validation_receipt_for_final_package(self) -> None:
        passed = [r for r in self.rin if r["阶段"].startswith("目标校验") and r["结果"] == "通过"]
        self.assertTrue(
            passed,
            "AC-08 要求被目标版本接受的最终包校验回执：RIN-02 必须按目标机实测的 validate/register 结果签 通过，"
            "并登记客户端实测校验器版本与注册条目回执（installedAt/version/installPath + 安装件 plugin.json 的 sha256）。"
            "校验通道＝客户端 builtin 的 skill-expert-manager cache 副本脚本（见 ENV-05），不自制校验器（NFR-02）。")

    def test_install_and_summon_receipt_for_final_package(self) -> None:
        installed = [r for r in self.rin
                     if r["阶段"].startswith(("安装", "新会话")) and r["结果"] == "通过"]
        self.assertEqual(len(installed), 2,
                         "AC-08 要求 安装 与 新会话 两阶段都按最终包实测通过（§4.6：安装→新会话仅保留包声明依赖→实际调用）；"
                         "静态文件比对不得充当安装/召唤回执，缺 GUI 收敛与新会话工具面时该行保持 阻塞 并写明重授权路径。")
        unrepro = [r["ID"] for r in self.rep if r["是否可复现"].strip() != "是"]
        self.assertEqual(unrepro, [],
                         f"REP {unrepro} 未按最终包实际复现；缺权限负例的拒绝前提只能由目标账户实际成立，"
                         "不得以 tool-not-mounted 或注入无效凭据代替（safety-branches.md#登记口径 第 4 条）。")

    # --- counterexamples (TASK-04 §4) ---
    def test_version_rolled_back_rejected(self) -> None:
        bad = dict(self.manifest, version="0.10.0")
        with self.assertRaises(AssertionError):
            check_manifest_version(bad)

    def test_evidence_path_inside_package_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "pkg"
            (package / "evidence").mkdir(parents=True)
            (package / "evidence" / "index.md").write_text("x\n", encoding="utf-8")
            (package / ".codebuddy-plugin").mkdir()
            (package / "agents").mkdir()
            with self.assertRaises(AssertionError):
                check_exported_files(package, self.exp)

    def test_missing_dir_negative_with_zero_exit_rejected(self) -> None:
        ok = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with self.assertRaises(AssertionError):
            assert_negative_exited_failed(ok, "missing-dir")

    def test_identifier_fix_without_export_sync_rejected(self) -> None:
        bad = json.loads(json.dumps(self.manifest))
        bad["dependencies"]["connectors"] = ["wind-finance", "tdx-connector", "neodata", "westock-mcp2"]
        with self.assertRaises(AssertionError):
            check_connectors(bad, self.exp)

    def test_predecessor_receipt_cannot_sign_validation_passed(self) -> None:
        bad = [dict(r) for r in self.rin]
        row = next(r for r in bad if r["阶段"].startswith("目标校验"))
        row["结果"] = "通过"
        row["客户端/校验器/包版本"] = "客户端=37.10.3-24 校验器=5.6.2-wb.39298511.g37a65c0b.he233403f909a 包=0.11.0"
        row["证据引用"] = (f"注册条目 installedAt=2026-09-29T06:54:07.733Z 实测；安装件 manifest "
                          f"sha256={self.old_installed_sha}")
        with self.assertRaises(AssertionError):
            check_rin(bad, self.manifest, self.client_token, self.dcl, self.old_installed_sha)

    def test_gap_row_without_reauth_path_rejected(self) -> None:
        bad = [dict(r) for r in self.rin]
        row = next(r for r in bad if r["阶段"].startswith("安装"))
        row["证据引用"] = "不适用（未执行）"
        with self.assertRaises(AssertionError):
            check_rin(bad, self.manifest, self.client_token, self.dcl, self.old_installed_sha)

    def test_package_version_drift_in_rin_rejected(self) -> None:
        bad = [dict(r) for r in self.rin]
        row = bad[0]
        row["客户端/校验器/包版本"] = row["客户端/校验器/包版本"].replace("包=0.11.0", "包=0.10.0")
        with self.assertRaises(AssertionError):
            check_rin(bad, self.manifest, self.client_token, self.dcl, self.old_installed_sha)

    def test_rep_unreproducible_with_domain_adopted_rejected(self) -> None:
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "equity-research"
            shutil.copytree(EVIDENCE, home)
            row = next(r for r in load_table("reinstall.md", "重装后复现") if r["ID"] == "REP-02")
            # 反例要测的是不变量 4 本身，不是盘上现值：未复现态显式构造，避免随 REP 行改判而失效
            fake = [{**row, "是否可复现": "否", "结果": "阻塞（反例构造）"}]
            # 域状态表按 TASK-05 的列契约造一行 可用，断言不变量 4 会拒绝它
            dom = home / "domain-readiness.md"
            cols = _evidence.TABLE_COLUMNS["domain-readiness.md#域状态"]
            dom.write_text(
                "## 域状态\n\n" + "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
                + "| DOM-01 | 机构财务 | 可用 | x | 无 | LIC-01 | QRY-01 | MR-01 |\n",
                encoding="utf-8", newline="")
            saved = _evidence.EVIDENCE
            try:
                _evidence.EVIDENCE = home
                with self.assertRaises(AssertionError):
                    check_rep_blocks_domain(fake)
            finally:
                _evidence.EVIDENCE = saved


if __name__ == "__main__":
    unittest.main()
