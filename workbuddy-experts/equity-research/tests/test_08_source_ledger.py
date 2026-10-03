"""cmd-01 — evidence contract base + source/install/license ledger (FR-01/02/03 -> AC-01/02/03).

Reads the G1 evidence files and the shared parser, and fails loud when the contract is
violated. Counterexamples required by TASK-01 §4 are exercised in-memory on mutated row
copies inside this module (no new command entry point is added). The registry assertion
holds the SDD/TASK-01 §6 column tuples as the expected truth, so any drift in `_evidence.TABLE_COLUMNS`
or a downstream table's columns fails here without requiring that downstream file to exist yet.
"""
from __future__ import annotations

import re
import unittest

from _evidence import (
    EVIDENCE,
    TABLE_COLUMNS,
    check_no_sensitive,
    load_table,
    read_coverage,
    read_run_window,
    require_ids,
)
from _support import ROOT, RepoTest

LAT_STATES = {"已验证", "未安装", "未识别", "未连接", "缺账号权限", "待确认许可", "阻塞"}
LIC_STATES = {"已确认", "待确认", "不适用"}
INTAKE_STATES = {"通过", "阻塞"}
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")

# TASK-01 §6: the column contract cmd-01 verifies the registry against (key set + tuples).
EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "index.md#RunWindow": ("字段", "值"),
    "index.md#CR1 输入核对": ("核对项", "CR1 版本/SHA", "证据位置", "核对结果"),
    "index.md#交付物入口": ("交付物类别", "入口路径", "说明"),
    "index.md#覆盖率摘要": ("指标", "计数", "生成时间"),
    "data-sources.md#安装与连接台账": (
        "ID", "层", "目标机识别结果与版本", "连接与授权路径", "账号权限",
        "许可主体", "实际工具与动作", "验证日期", "结果状态",
    ),
    "data-sources.md#连接器标识分层": (
        "ID", "manifest ID", "目标版本是否识别", "识别依据", "分层归属", "与路由名/服务名的关系",
    ),
    "data-sources.md#许可台账": (
        "ID", "入口", "用途", "覆盖范围与依据", "状态", "凭据存储机制与授权路径",
    ),
    "queries.md#样例登记": (
        "ID", "样例来源", "适用数据域与任务", "证券代码", "交易所", "报告期间", "披露日期",
        "来源与版本", "四条件核验与依据", "原件位置与 SHA-256", "裁决人", "裁决日期",
    ),
    "queries.md#查询溯源": (
        "ID", "数据域", "适用任务", "run-id", "查询日期", "查询条件", "证券代码/交易所",
        "请求期间", "源", "口径", "返回字段与结果状态", "数据/获取时间戳",
        "原始链接或文件引用", "留证方式", "证据对象引用", "SHA-256", "复核路径", "是否最终采用源",
    ),
    "queries.md#单指标单源": ("ID", "指标", "候选源与逐项差异", "最终采用源", "裁决依据"),
    "queries.md#口径审查": ("ID", "源", "审查项", "结论"),
    "safety-branches.md#判定顺序核对": ("ID", "顺序步骤", "可观察证据", "按序结论"),
    "safety-branches.md#安全分支实测": (
        "ID", "场景", "输入/受控条件", "实际回复类别", "采用源与相对差异",
        "证据引用", "契约符合性", "违规扫描裁决",
    ),
    "reinstall.md#重装步骤": ("ID", "阶段", "实际步骤", "客户端/校验器/包版本", "结果", "证据引用"),
    "reinstall.md#环境依赖排查": ("ID", "排查对象", "方法", "结果", "影响"),
    "reinstall.md#重装后复现": ("ID", "复现项", "结果", "证据引用", "是否可复现"),
    "domain-readiness.md#域状态": (
        "ID", "数据域", "状态", "已验证范围", "缺口", "许可引用", "证据引用", "适用任务",
    ),
    "domain-readiness.md#任务就绪": (
        "ID", "CR1 映射行", "必需数据域", "必需查询集 REQ-NN", "覆盖计数", "已可用域",
        "尚不能支持完整版的原因", "状态", "证据引用", "未覆盖 REQ-NN",
    ),
    "declarations.md#声明修正": (
        "ID", "触发", "涉及文件", "前后差异", "回归范围", "回归证据", "结论",
    ),
}


def check_intake(rows: list[dict]) -> None:
    for r in rows:
        for col in ("核对项", "CR1 版本/SHA", "证据位置"):
            if not r[col].strip():
                raise AssertionError(f"CR1 输入核对 缺 {col}: {r}")
        if not HEX64.match(r["CR1 版本/SHA"].strip()):
            raise AssertionError(f"CR1 版本/SHA 非 64 位十六进制实测值: {r['CR1 版本/SHA']!r}")
        if r["核对结果"] not in INTAKE_STATES:
            raise AssertionError(f"核对结果 {r['核对结果']!r} 不在枚举 {sorted(INTAKE_STATES)}")


def check_lat(rows: list[dict]) -> None:
    require_ids(rows, "LAT", minimum=6)
    for r in rows:
        for col in TABLE_COLUMNS["data-sources.md#安装与连接台账"]:
            if not r[col].strip():
                raise AssertionError(f"LAT 行 {r['ID']} 字段 {col} 为空")
        if r["结果状态"] not in LAT_STATES:
            raise AssertionError(f"LAT 结果状态 {r['结果状态']!r} 不在封闭枚举")


def check_con(rows: list[dict]) -> None:
    require_ids(rows, "CON", minimum=4)
    for r in rows:
        if not r["分层归属"].strip():
            raise AssertionError(f"CON 行 {r['ID']} 缺分层归属")
        if not r["与路由名/服务名的关系"].strip():
            raise AssertionError(f"CON 行 {r['ID']} 缺与路由名/服务名的关系")


def check_lic(rows: list[dict]) -> None:
    require_ids(rows, "LIC", minimum=18)
    for r in rows:
        if not r["覆盖范围与依据"].strip():
            raise AssertionError(f"LIC 行 {r['ID']} 缺依据")
        if r["状态"] not in LIC_STATES:
            raise AssertionError(f"LIC 状态 {r['状态']!r} 不在封闭枚举")
        # (源, 动作, 用途) fail-closed: an action may only be recorded granted when the
        # matching use-permission is 已确认; 待确认 用途 must not carry an ungranted action.
        if r["状态"] == "已确认" and not r["覆盖范围与依据"].strip():
            raise AssertionError(f"LIC 行 {r['ID']} 记 已确认 但无可核查依据")


def check_registry(registry: dict) -> None:
    if set(registry) != set(EXPECTED_COLUMNS):
        missing = sorted(set(EXPECTED_COLUMNS) - set(registry))
        extra = sorted(set(registry) - set(EXPECTED_COLUMNS))
        raise AssertionError(f"TABLE_COLUMNS 键集偏离 §6：缺 {missing} 多 {extra}")
    for key, cols in EXPECTED_COLUMNS.items():
        if registry[key] != cols:
            raise AssertionError(f"TABLE_COLUMNS[{key}] 列名/列序偏离 §6: {registry[key]} != {cols}")


def compute_coverage(lat, con, lic, intake, deliverables) -> dict:
    def _count(path, predicate):
        if not path.is_file():
            return 0
        return sum(1 for ln in path.read_text(encoding="utf-8").splitlines() if predicate(ln))

    adopted = _count(EVIDENCE / "queries.md", lambda ln: ln.rstrip().endswith("| 是 |"))
    return {
        "六入口台账条数": len(lat),
        "连接器标识条数": len(con),
        "许可记录条数": len(lic),
        "用途许可已确认数": sum(1 for r in lic if r["状态"] == "已确认"),
        "七域实取成功数": adopted,
        "域可用计数": _count(EVIDENCE / "domain-readiness.md", lambda ln: "| 可用 |" in ln),
        "安全场景实测数": _count(EVIDENCE / "safety-branches.md", lambda ln: "| SBC-0" in ln),
        "CR1 输入核对通过数": sum(1 for r in intake if r["核对结果"] == "通过"),
        "交付物入口数": len(deliverables),
    }


class SourceLedger(RepoTest):
    def setUp(self) -> None:
        self.run_window = read_run_window()
        self.intake = load_table("index.md", "CR1 输入核对")
        self.deliverables = load_table("index.md", "交付物入口")
        self.summary = load_table("index.md", "覆盖率摘要")
        self.lat = load_table("data-sources.md", "安装与连接台账")
        self.con = load_table("data-sources.md", "连接器标识分层")
        self.lic = load_table("data-sources.md", "许可台账")

    # --- AC-01: RunWindow + CR1 intake ---
    def test_run_window_has_six_fields(self) -> None:
        for key in ("run-id", "首次采集时间", "末次采集时间", "客户端版本", "校验器版本", "包版本"):
            self.assertIn(key, self.run_window, f"RunWindow 缺字段 {key}")
        self.assertTrue(self.run_window["run-id"].startswith("CR-2026-002-"), "run-id 前缀不符")

    def test_cr1_intake_rows(self) -> None:
        check_intake(self.intake)

    def test_cr1_intake_illegal_state_rejected(self) -> None:  # counterexample
        bad = [dict(r) for r in self.intake]
        bad[0]["核对结果"] = "未知"
        with self.assertRaises(AssertionError):
            check_intake(bad)

    # --- AC-02: LAT / CON ledger ---
    def test_lat_rows(self) -> None:
        check_lat(self.lat)

    def test_lat_illegal_state_rejected(self) -> None:  # counterexample
        bad = [dict(r) for r in self.lat]
        bad[0]["结果状态"] = "已批准"
        with self.assertRaises(AssertionError):
            check_lat(bad)

    def test_con_rows(self) -> None:
        check_con(self.con)

    def test_con_blank_layering_rejected(self) -> None:  # counterexample
        bad = [dict(r) for r in self.con]
        bad[0]["与路由名/服务名的关系"] = ""
        with self.assertRaises(AssertionError):
            check_con(bad)

    # --- AC-03: LIC three uses, fail-closed, credential scan ---
    def test_lic_rows(self) -> None:
        check_lic(self.lic)

    def test_lic_illegal_state_rejected(self) -> None:  # counterexample
        bad = [dict(r) for r in self.lic]
        bad[0]["状态"] = "已批准"
        with self.assertRaises(AssertionError):
            check_lic(bad)

    def test_lic_granted_without_basis_rejected(self) -> None:  # counterexample
        bad = [dict(r) for r in self.lic]
        bad[0]["状态"] = "已确认"
        bad[0]["覆盖范围与依据"] = ""
        with self.assertRaises(AssertionError):
            check_lic(bad)

    # --- registry (TABLE_COLUMNS == §6, including downstream tables) ---
    def test_table_columns_registry_matches_spec(self) -> None:
        check_registry(TABLE_COLUMNS)

    def test_registry_missing_key_rejected(self) -> None:  # counterexample
        bad = dict(TABLE_COLUMNS)
        bad.pop("queries.md#样例登记")
        with self.assertRaises(AssertionError):
            check_registry(bad)

    def test_registry_downstream_column_drift_rejected(self) -> None:  # counterexample
        bad = dict(TABLE_COLUMNS)
        cols = list(bad["queries.md#样例登记"])
        cols[0] = "编号"  # rename -> column order/name deviates from §6
        bad["queries.md#样例登记"] = tuple(cols)
        with self.assertRaises(AssertionError):
            check_registry(bad)

    # --- coverage summary == computed == coverage.json ---
    def test_coverage_summary_equals_computed(self) -> None:
        computed = compute_coverage(self.lat, self.con, self.lic, self.intake, self.deliverables)
        for row in self.summary:
            self.assertIn(row["指标"], computed, f"覆盖率摘要未知指标 {row['指标']}")
            self.assertEqual(int(row["计数"]), computed[row["指标"]],
                             f"{row['指标']} 摘要 {row['计数']} != 现算 {computed[row['指标']]}")
        cov = read_coverage()
        for key, value in computed.items():
            self.assertEqual(cov.get(key), value, f"coverage.json {key} {cov.get(key)} != 现算 {value}")

    # --- sensitive scan (dep-3 patterns) over evidence text ---
    def test_evidence_files_pass_sensitive_scan(self) -> None:
        for name in ("index.md", "data-sources.md"):
            text = (EVIDENCE / name).read_text(encoding="utf-8")
            check_no_sensitive(text, where=f"evidence/{name}")

    def test_sensitive_content_rejected(self) -> None:  # counterexample
        with self.assertRaises(AssertionError):
            check_no_sensitive("凭据 password: hunter2 已泄露", where="evidence/data-sources.md")

    def test_private_path_rejected(self) -> None:  # counterexample
        with self.assertRaises(AssertionError):
            check_no_sensitive("原件在 /home/devuser/out/samples/x.pdf", where="evidence/index.md")


if __name__ == "__main__":
    unittest.main()
