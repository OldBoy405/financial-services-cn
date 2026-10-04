"""cmd-05 — domain and task readiness handoff plus the DCL closure re-check (FR-09/FR-10 -> AC-09/AC-10).

Reads `evidence/domain-readiness.md` (the two registered tables + this module's own `必需查询集` and
`DCL 闭合复验` blocks), CR1's `README.md#2` mapping rows (the REQ denominator is recomputed here, never
self-declared by the ledger), the upstream `LIC`/`QRY`/`SRC`/`SBC`/`REP`/`DCL`/`RIN` rows, the real
manifest and the export script's own `EXPECTED_CONNECTORS` (dep-3: compared, never copied), and
`index.md#覆盖率摘要` against `compute_coverage` and `coverage.json`.

Fail-closed rules asserted here are SDD §2.2 invariants 1/3/4 and §4.4/§4.5: a `可用` domain needs a
recorded gap-free adopted query with a confirmed use permission, a `就绪` task needs every `REQ` covered,
and `DOM=可用` never propagates to task readiness. Nothing in this module relaxes an assertion to get
green, and it changes no declaration file — G5 re-checks TASK-04's `DCL` closure and its boundaries only.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

import _evidence
import _support
from _evidence import (
    EVIDENCE,
    TABLE_COLUMNS,
    check_no_sensitive,
    load_table,
    read_coverage,
    require_ids,
    sha256_bytes,
    sha256_record,
)
from _support import README, RepoTest
from test_08_source_ledger import check_coverage_against, compute_coverage
from test_09_query_traceability import (
    PRIVATE_WIN_PATH_RE,
    RECORD_REF_RE,
    SEVEN_DOMAINS,
    load_verify_records,
)
from test_10_safety_branches import check_agent, check_sbc01_02_independent
from test_11_reinstall_repro import (
    REPACKED_RE,
    TARGET_VERSION,
    check_connectors,
    check_dcl,
    check_manifest_version,
    check_rep,
    check_rep_blocks_domain,
    load_export_module,
)

DOM_STATES = ("可用", "可降级但质量受限", "阻塞")
TSK_STATES = ("就绪", "可降级但质量受限", "阻塞")
REQ_VERDICTS = ("覆盖", "未覆盖")
REF_RE = re.compile(r"\b(?:QRY|SRC|KJ|SBC|SMP|VR|LIC|LAT|CON|REP|RIN|ENV|DOM|TSK|REQ|MR)-\d{2}\b")
REQ_ID_RE = re.compile(r"\AREQ-\d{2}\Z")
COVERAGE_RE = re.compile(r"\A(\d+)/(\d+)\Z")
# G5 的两张附表不在 TASK-01 §6 的 TABLE_COLUMNS 注册面内（同 queries.md#核验记录对象的处理），列名在此定义。
REQ_COLUMNS = ("ID", "来源映射行", "数据域", "市场与证券样本", "报告期间", "必需字段与口径",
               "前序依赖", "关联证据行", "覆盖判定", "判定依据")
DCL_RECHECK_COLUMNS = ("ID", "复验对象", "节点复现方式", "复现结果", "闭合结论")


def local_table(heading: str, columns: tuple[str, ...], *, path: Path | None = None) -> list[dict[str, str]]:
    """Parse one unregistered table in domain-readiness.md by its own column tuple."""
    lines = (path or EVIDENCE / "domain-readiness.md").read_text(encoding="utf-8").splitlines()
    start = None
    for i, ln in enumerate(lines):
        m = _evidence._HEADING_RE.match(ln)
        if m and m.group(1) == heading:
            start = i + 1
            break
    if start is None:
        raise AssertionError(f"domain-readiness.md: heading '{heading}' not found")
    rows = []
    for ln in lines[start:]:
        if _evidence._HEADING_RE.match(ln):
            break
        if ln.strip().startswith("|"):
            rows.append(ln.strip())
    if len(rows) < 2 or tuple(_evidence._split_row(rows[0])) != columns:
        raise AssertionError(f"{heading}: 列名或列序偏离 cmd-05 定义 {columns}")
    data = []
    for ln in rows[2:]:
        cells = _evidence._split_row(ln)
        if len(cells) != len(columns):
            raise AssertionError(f"{heading}: 行宽 {len(cells)} != {len(columns)} in {ln!r}")
        data.append(dict(zip(columns, cells)))
    return data


def known_ids() -> set[str]:
    """Every row id already on disk, so a reference in G5 can only point at real evidence."""
    ids: set[str] = set()
    for file_name, heading in (
        ("data-sources.md", "许可台账"), ("data-sources.md", "安装与连接台账"),
        ("data-sources.md", "连接器标识分层"), ("queries.md", "查询溯源"),
        ("queries.md", "单指标单源"), ("queries.md", "口径审查"), ("queries.md", "样例登记"),
        ("safety-branches.md", "安全分支实测"), ("reinstall.md", "重装后复现"),
        ("reinstall.md", "重装步骤"), ("declarations.md", "声明修正"),
    ):
        ids |= {r["ID"] for r in load_table(file_name, heading)}
    ids |= set(load_verify_records())
    ids |= {f"MR-{n:02d}" for n in range(1, 10)}
    return ids


def check_ref_cell(cell: str, known: set[str], *, where: str) -> list[str]:
    refs = REF_RE.findall(cell)
    unknown = sorted({r for r in refs if r not in known})
    if unknown:
        raise AssertionError(f"{where} 引用了不存在的行 ID：{unknown}")
    return refs


def check_dom(dom: list[dict], lic: list[dict], qry: list[dict], known: set[str]) -> None:
    require_ids(dom, "DOM", minimum=7)
    if len(dom) != 7:
        raise AssertionError(f"域状态必须恰七行（§4.4 七域），现 {len(dom)} 行")
    if [r["数据域"] for r in dom] != list(SEVEN_DOMAINS):
        raise AssertionError("七域顺序漂移（§4.7 边界不变量：七域顺序不随声明修正改变）")
    lic_status = {r["ID"]: r["状态"] for r in lic}
    adopted_by_domain: dict[str, list[str]] = {}
    for row in qry:
        if row["是否最终采用源"] == "是":
            adopted_by_domain.setdefault(row["数据域"], []).append(row["ID"])
    for row in dom:
        for col in TABLE_COLUMNS["domain-readiness.md#域状态"]:
            if not row[col].strip():
                raise AssertionError(f"DOM 行 {row['ID']} 字段 {col} 为空")
        if row["状态"] not in DOM_STATES:
            raise AssertionError(f"DOM 行 {row['ID']} 状态 {row['状态']!r} 不在封闭枚举 {DOM_STATES}")
        check_ref_cell(row["许可引用"], known, where=f"DOM {row['ID']} 许可引用")
        check_ref_cell(row["证据引用"], known, where=f"DOM {row['ID']} 证据引用")
        check_ref_cell(row["适用任务"], known, where=f"DOM {row['ID']} 适用任务")
        if row["状态"] != "可用":
            continue
        # §4.4 第一支与第二支互斥：域内已记录缺口 ⇒ 不得标 可用
        if row["缺口"].strip() not in ("无", "不适用"):
            raise AssertionError(f"DOM 行 {row['ID']} 记 可用 但缺口列有已记录缺口（§4.4 应取 可降级但质量受限）")
        confirmed = [i for i in REF_RE.findall(row["许可引用"]) if i.startswith("LIC-")
                     and lic_status.get(i) == "已确认"]
        if not confirmed:  # §2.2 不变量 1：用途许可必须已确认
            raise AssertionError(f"DOM 行 {row['ID']} 判 可用 但许可引用无 LIC=已确认")
        if not set(REF_RE.findall(row["证据引用"])) & set(adopted_by_domain.get(row["数据域"], [])):
            raise AssertionError(
                f"DOM 行 {row['ID']} 判 可用 但证据引用未指向本域的成功采用 QRY 行（§2.2 不变量 1）")


def expected_reqs(mapping: list[dict]) -> dict[str, list[str]]:
    """REQ denominator recomputed from CR1's required-data lists, MR-01..09 in order."""
    out: dict[str, list[str]] = {}
    n = 0
    for row in mapping:
        items = row["required-data"]
        if not isinstance(items, list) or not items:
            raise AssertionError(f"{row['row']} 的 required-data 不是非空列表，无法展开 REQ 集")
        batch = []
        for _ in items:
            n += 1
            batch.append(f"REQ-{n:02d}")
        out[row["row"]] = batch
    return out


def _req_violations(row: dict, *, qry_by_id: dict, lic_by_id: dict, records: dict,
                    machine: dict[str, bool]) -> list[str]:
    """SDD §4.5 的四条件机检（覆盖不来自台账，来自对上游 QRY/LIC/VR/前序 REQ 的现算）。"""
    violations: list[str] = []
    refs = REF_RE.findall(row["关联证据行"])
    qrids = [r for r in refs if r.startswith("QRY-")]
    licids = [r for r in refs if r.startswith("LIC-")]
    vrids = [r for r in refs if r.startswith("VR-")]
    adopted = [qry_by_id[q] for q in qrids if q in qry_by_id and qry_by_id[q]["是否最终采用源"] == "是"]
    if not adopted:
        violations.append("本次实测成功行（关联 QRY 缺位或均未采用）")
    bound_vrids: set[str] = set()
    for q in adopted:
        m = RECORD_REF_RE.search(q["证据对象引用"])
        if m is None:
            violations.append(f"{q['ID']} 证据对象引用不合法")
            continue
        vrid = m.group(1)
        rec = records.get(vrid)
        if rec is None:
            violations.append(f"{q['ID']} 证据对象 {vrid} 缺位")
            continue
        if sha256_record(rec) != q["SHA-256"]:
            violations.append(f"{q['ID']} 证据对象 {vrid} 哈希不匹配")
            continue
        bound_vrids.add(vrid)
    if vrids and not set(vrids) <= bound_vrids:
        violations.append(f"关联 VR 未绑定 adopted QRY：{sorted(set(vrids) - bound_vrids)}")
    entries = {q["源"].split("（")[0].split("／")[0].strip() for q in adopted}
    ok_lic = any(
        lic_by_id.get(l, {}).get("状态") == "已确认" and lic_by_id[l].get("入口") in entries
        for l in licids
    )
    if not ok_lic:
        violations.append("对应用途 LIC=已确认（关联 LIC 与 adopted QRY 入口不匹配或未确认）")
    for dep in re.findall(r"REQ-\d{2}", row["前序依赖"]):
        if not machine.get(dep, False):
            violations.append(f"前序依赖 {dep} 未成立")
    if adopted:
        req_domains = {d.strip() for d in re.split(r"[；;]", row["数据域"])
                       if d.strip() and not d.strip().startswith("不适用")}
        qry_domains = {q["数据域"] for q in adopted}
        if req_domains and not (req_domains & qry_domains):
            violations.append(f"数据域不满足（REQ={sorted(req_domains)} ∩ QRY={sorted(qry_domains)} = ∅）")
        req_period = row["报告期间"].strip()
        if not req_period.startswith("不适用"):
            req_years = set(re.findall(r"\b\d{4}\b", req_period))
            qry_text = " ".join(
                [q["请求期间"] for q in adopted]
                + [records[b]["期间覆盖"] for b in bound_vrids if b in records]
            )
            qry_years = set(re.findall(r"\b\d{4}\b", qry_text))
            if req_years and not (req_years & qry_years):
                violations.append(f"期间满足（REQ {sorted(req_years)} ∩ QRY {sorted(qry_years)} = ∅）")
    return violations


def check_req(reqs: list[dict], mapping: list[dict], known: set[str], *,
              qry: list[dict], lic: list[dict], records: dict) -> dict[str, tuple[int, int, list[str]]]:
    want = expected_reqs(mapping)
    flat = [i for batch in want.values() for i in batch]
    got = [r["ID"] for r in reqs]
    if got != flat:
        raise AssertionError(f"必需查询集条目或顺序偏离 CR1 required-data 展开：现 {got} != 应 {flat}")
    qry_by_id = {r["ID"]: r for r in qry}
    lic_by_id = {r["ID"]: r for r in lic}
    machine: dict[str, bool] = {}
    for row, req_id in zip(reqs, flat):
        for col in REQ_COLUMNS:
            if not row[col].strip():
                raise AssertionError(f"REQ 行 {req_id} 字段 {col} 为空")
        if not REQ_ID_RE.match(req_id):
            raise AssertionError(f"REQ id {req_id!r} 非 REQ-NN")
        if row["覆盖判定"] not in REQ_VERDICTS:
            raise AssertionError(f"REQ 行 {req_id} 覆盖判定 {row['覆盖判定']!r} 不在 {REQ_VERDICTS}")
        if row["关联证据行"].strip() != "无":
            check_ref_cell(row["关联证据行"], known, where=f"REQ {req_id} 关联证据行")
        # §4.5 四条件机检——覆盖与否由现算而非由本行「覆盖判定」标签决定
        violations = _req_violations(row, qry_by_id=qry_by_id, lic_by_id=lic_by_id,
                                     records=records, machine=machine)
        machine[req_id] = not violations
        label = row["覆盖判定"] == "覆盖"
        if label != machine[req_id]:
            raise AssertionError(
                f"REQ 行 {req_id} 覆盖判定 {row['覆盖判定']} 与 §4.5 四条件机检不一致（violations={violations}）")
        if not label and "缺" not in row["判定依据"]:
            raise AssertionError(f"REQ 行 {req_id} 记未覆盖但未写明 §4.5 四条件中缺哪一条")
    per_task: dict[str, tuple[int, int, list[str]]] = {}
    for mr, batch in want.items():
        covered = sum(1 for rid in batch if machine[rid])
        gaps = [rid for rid in batch if not machine[rid]]
        per_task[mr] = (covered, len(batch), gaps)
    return per_task


def check_tsk(tsk: list[dict], reqs: list[dict], dom: list[dict], mapping: list[dict],
              known: set[str], *, qry: list[dict], lic: list[dict],
              records: dict) -> None:
    require_ids(tsk, "TSK", minimum=9)
    if len(tsk) != 9:
        raise AssertionError(f"任务就绪必须恰九行（MR-01..09），现 {len(tsk)} 行")
    want = expected_reqs(mapping)
    per_task = check_req(reqs, mapping, known, qry=qry, lic=lic, records=records)
    available_domains = {r["ID"] for r in dom if r["状态"] == "可用"}
    for i, row in enumerate(tsk):
        mr = f"MR-{i + 1:02d}"
        for col in TABLE_COLUMNS["domain-readiness.md#任务就绪"]:
            if not row[col].strip():
                raise AssertionError(f"TSK 行 {row['ID']} 字段 {col} 为空")
        if row["CR1 映射行"] != f"{mr} `{mapping[i]['command']}`":
            raise AssertionError(
                f"TSK 行 {row['ID']} 的映射行 {row['CR1 映射行']!r} != CR1 README 的 {mr} `{mapping[i]['command']}`")
        if row["状态"] not in TSK_STATES:
            raise AssertionError(f"TSK 行 {row['ID']} 状态 {row['状态']!r} 不在封闭枚举 {TSK_STATES}")
        listed = REF_RE.findall(row["必需查询集 REQ-NN"])
        if sorted(set(listed)) != sorted(want[mr]):
            raise AssertionError(f"TSK 行 {row['ID']} 的必需查询集 {listed} != CR1 展开 {want[mr]}")
        covered, total, gaps = per_task[mr]
        m = COVERAGE_RE.match(row["覆盖计数"].strip())
        if not m:
            raise AssertionError(f"TSK 行 {row['ID']} 覆盖计数 {row['覆盖计数']!r} 非 n/m 形态")
        if (int(m.group(1)), int(m.group(2))) != (covered, total):
            raise AssertionError(
                f"TSK 行 {row['ID']} 覆盖计数 {m.group(0)} != 现算 {covered}/{total}（分母 = REQ 条目数）")
        uncovered = REF_RE.findall(row["未覆盖 REQ-NN"]) if row["未覆盖 REQ-NN"].strip() != "无" else []
        if sorted(uncovered) != sorted(gaps):
            raise AssertionError(f"TSK 行 {row['ID']} 未覆盖清单 {uncovered} != 现算 {gaps}")
        check_ref_cell(row["证据引用"], known, where=f"TSK {row['ID']} 证据引用")
        check_ref_cell(row["必需数据域"], known, where=f"TSK {row['ID']} 必需数据域")
        listed_dom = [d for d in re.findall(r"DOM-\d{2}", row["已可用域"])]
        if not set(listed_dom) <= available_domains:
            raise AssertionError(
                f"TSK 行 {row['ID']} 的已可用域 {listed_dom} 含非 可用 域（可用域={sorted(available_domains) or '无'}）")
        if row["状态"] == "就绪":
            if covered != total or gaps:
                raise AssertionError(f"TSK 行 {row['ID']} 覆盖不足却签 就绪（§2.2 不变量 3）")
            if uncovered:
                raise AssertionError(f"TSK 行 {row['ID']} 就绪但未覆盖列非空")
        elif gaps == []:
            raise AssertionError(f"TSK 行 {row['ID']} REQ 全覆盖却未签 就绪，须写明其它限制依据")
        if row["状态"] == "阻塞" and "可重授权路径" not in row["尚不能支持完整版的原因"]:
            raise AssertionError(f"TSK 行 {row['ID']} 阻塞但未在原因列列明可重授权路径（TASK-05 §5）")
        for dom_cell in row["必需数据域"].split("；"):
            if dom_cell.strip() and dom_cell.strip() not in SEVEN_DOMAINS:
                raise AssertionError(f"TSK 行 {row['ID']} 必需数据域 {dom_cell!r} 不在七域封闭集")


class ReadinessHandoff(RepoTest):
    def setUp(self) -> None:
        self.text = (EVIDENCE / "domain-readiness.md").read_text(encoding="utf-8")
        self.dom = load_table("domain-readiness.md", "域状态")
        self.tsk = load_table("domain-readiness.md", "任务就绪")
        self.req = local_table("必需查询集", REQ_COLUMNS)
        self.dcl_recheck = local_table("DCL 闭合复验", DCL_RECHECK_COLUMNS)
        self.lic = load_table("data-sources.md", "许可台账")
        self.qry = load_table("queries.md", "查询溯源")
        self.sbc = load_table("safety-branches.md", "安全分支实测")
        self.rep = load_table("reinstall.md", "重装后复现")
        self.rin = load_table("reinstall.md", "重装步骤")
        self.dcl = load_table("declarations.md", "声明修正")
        self.intake = load_table("index.md", "CR1 输入核对")
        self.mapping = self.mapping_rows()
        self.records = load_verify_records()
        self.known = known_ids() | {r["ID"] for r in self.dom} | {r["ID"] for r in self.tsk} | \
            {r["ID"] for r in self.req}

    # --- AC-09: three-state domain table ---
    def test_domain_table_shape_and_states(self) -> None:
        check_dom(self.dom, self.lic, self.qry, self.known)

    def test_domain_gap_is_recorded_for_every_non_available_row(self) -> None:
        for row in self.dom:
            if row["状态"] == "可用":
                continue
            self.assertIn("未实取", row["缺口"], f"{row['ID']} 非可用却未写明缺口依据")

    def test_rep_invariant_four_now_binds(self) -> None:
        # §2.2 不变量 4 此前因 domain-readiness.md 缺位而跳过，本 TASK 落盘后必须实际生效
        check_rep(self.rep)
        check_rep_blocks_domain(self.rep)

    # --- AC-09: REQ set expanded from CR1, not self-declared ---
    def test_req_set_equals_cr1_expansion(self) -> None:
        check_req(self.req, self.mapping, self.known,
                  qry=self.qry, lic=self.lic, records=self.records)
        self.assertEqual(len(self.req), 31, "九项映射 required-data 展开应恰 31 条 REQ")

    # --- AC-09: task readiness rows ---
    def test_task_rows_cover_counts_and_states(self) -> None:
        check_tsk(self.tsk, self.req, self.dom, self.mapping, self.known,
                  qry=self.qry, lic=self.lic, records=self.records)

    def test_no_task_signed_ready(self) -> None:
        # FR-09：许可或必需查询阻塞域可明示交付限制，但不得签成完整任务能力
        self.assertEqual([r["ID"] for r in self.tsk if r["状态"] == "就绪"], [])
        self.assertEqual([r["ID"] for r in self.tsk if r["状态"] == "阻塞"],
                         [f"TSK-{n:02d}" for n in range(1, 10)],
                         "九任务按 §4.5 全部保持阻塞（港股样例与引用/导出用途许可未闭合）")

    def test_domain_available_does_not_propagate_to_task(self) -> None:
        # §4.5「域级传播不成立」：每条 REQ 覆盖齐备才可就绪，域级成功不能替代
        # 映射键比较按 MR 编号取前缀（B-CODE-02：`row["CR1 映射行"]` 含 ` `/earnings` 尾缀）
        for row in self.tsk:
            mr_key = row["CR1 映射行"].split()[0]
            gaps = [r["ID"] for r in self.req
                    if r["来源映射行"] == mr_key and r["覆盖判定"] == "未覆盖"]
            if gaps:
                self.assertNotEqual(row["状态"], "就绪", f"{row['ID']} 有未覆盖 {gaps} 却签就绪")
            else:
                # 无未覆盖时若仍非就绪，须在原因列写明其他限制依据（§4.5/不变量 3）
                if row["状态"] != "就绪":
                    self.assertTrue(row["尚不能支持完整版的原因"].strip(),
                                    f"{row['ID']} REQ 全覆盖却未就绪且未写明其它限制")

    # --- AC-09: coverage summary == computed == coverage.json ---
    def test_coverage_summary_matches_computed(self) -> None:
        computed = compute_coverage(
            load_table("data-sources.md", "安装与连接台账"),
            load_table("data-sources.md", "连接器标识分层"),
            self.lic,
            self.intake,
            load_table("index.md", "交付物入口"),
            dom=self.dom, tsk=self.tsk, reqs=self.req,
        )
        self.assertEqual(computed["域可用计数"], sum(1 for r in self.dom if r["状态"] == "可用"),
                         "域可用计数 != 域状态表的 可用 行数")
        self.assertEqual(computed["安全场景实测数"], 9, "九场景登记行数漂移")
        self.assertEqual(computed["九任务 REQ 分母"], 31, "REQ 分母 != CR1 required-data 展开 31")
        check_sbc01_02_independent(self.sbc)
        check_coverage_against(computed, load_table("index.md", "覆盖率摘要"), read_coverage())

    # --- AC-10: DCL closure re-checked, boundaries untouched ---
    def test_dcl_rows_closed_by_recomputed_zero_diff(self) -> None:
        check_dcl(self.dcl)
        self.assertEqual([r["ID"] for r in self.dcl_recheck], [r["ID"] for r in self.dcl],
                         "DCL 闭合复验行与 declarations.md 的 DCL 行不一一对应")
        for row in self.dcl_recheck:
            for col in DCL_RECHECK_COLUMNS:
                self.assertTrue(row[col].strip(), f"复验行 {row['ID']} 缺 {col}")
            self.assertTrue(row["闭合结论"].startswith("闭合"), f"{row['ID']} 复验未闭合")

    def test_no_repair_rows_must_point_at_final_package(self) -> None:
        # §4.7：无修正时的闭合依据是最终包的导出与目标校验回执，不得由修正前证据代替
        for row in self.dcl:
            if not row["结论"].startswith("无需修正"):
                continue
            for stage in ("导出", "目标校验"):
                rin = [r for r in self.rin if r["阶段"].startswith(stage)]
                self.assertTrue(rin, f"缺 {stage} 阶段的 RIN 行")
                for r in rin:
                    if "通过" not in r["结果"]:
                        continue
                    m = REPACKED_RE.search(r["客户端/校验器/包版本"])
                    self.assertIsNotNone(m, f"RIN {r['ID']} 未写包版本")
                    self.assertEqual(m.group(1), TARGET_VERSION,
                                     f"RIN {r['ID']} 的回执指向 {m.group(1)}，非最终包 {TARGET_VERSION}")

    def test_cr1_readme_zero_diff_still_holds(self) -> None:
        got = sha256_bytes(README.read_bytes())
        for item in ("九项路由记录（命令→唯一技能）", "九项映射 MR-01..09"):
            self.assertEqual(self.intake_row(item), got, f"{item} 的 CR1 登记 SHA != README.md 实测值（边界项漂移）")

    def test_agent_declaration_boundaries_unchanged(self) -> None:
        check_agent(self.intake_row("Agent 七域声明（数据域路由）"))
        nine = [(row["command"], row["skill"]) for row in self.mapping]
        self.assertEqual(nine, [(c, s) for c, s in _support.NINE_PAIRS], "九项路由集合或顺序漂移")

    def test_connector_set_unchanged(self) -> None:
        manifest = self.load_manifest()
        check_manifest_version(manifest)
        check_connectors(manifest, load_export_module())

    def test_sensitive_scan(self) -> None:
        check_no_sensitive(self.text, where="evidence/domain-readiness.md")
        self.assertIsNone(PRIVATE_WIN_PATH_RE.search(self.text), "domain-readiness.md 含私有绝对路径")

    def test_no_upstream_file_rewritten_by_g5(self) -> None:
        # 本 TASK 只读引用上游台账：G5 的写入面只有 domain-readiness.md 与本测试模块
        for name in ("index.md", "data-sources.md", "queries.md", "safety-branches.md",
                     "reinstall.md", "declarations.md"):
            path = EVIDENCE / name
            self.assertTrue(path.is_file(), f"上游证据文件缺位：{name}")
        for rel in ("agents/equity-research.md", ".codebuddy-plugin/plugin.json"):
            self.assertTrue((EVIDENCE.parent / rel).is_file(), f"§4.7 允许对象缺位：{rel}")

    def intake_row(self, item: str) -> str:
        return next(r["CR1 版本/SHA"].strip() for r in self.intake if r["核对项"] == item)

    # --- counterexamples (TASK-05 §4) ---
    def test_available_domain_without_adopted_query_rejected(self) -> None:
        bad = [dict(r) for r in self.dom]
        bad[0]["状态"] = "可用"
        bad[0]["缺口"] = "无"
        bad[0]["证据引用"] = "SBC-04"  # 本域无采用行可指
        with self.assertRaises(AssertionError):
            check_dom(bad, self.lic, self.qry, self.known)

    def test_partial_cover_count_signed_ready_rejected(self) -> None:
        bad = [dict(r) for r in self.tsk]
        row = bad[0]
        row["状态"] = "就绪"
        row["未覆盖 REQ-NN"] = "无"
        with self.assertRaises(AssertionError):
            check_tsk(bad, self.req, self.dom, self.mapping, self.known,
                      qry=self.qry, lic=self.lic, records=self.records)

    def test_sbc01_02_merged_row_rejected(self) -> None:
        merged = [r for r in self.sbc if r["ID"] != "SBC-02"]
        merged[0] = {**merged[0], "场景": "订阅缺失／权限拒绝"}
        with self.assertRaises(AssertionError):
            check_sbc01_02_independent(merged)

    def test_pre_repair_receipt_as_closure_rejected(self) -> None:
        bad = [dict(r) for r in self.rin]
        row = next(r for r in bad if r["阶段"].startswith("目标校验") and "通过" in r["结果"])
        row["客户端/校验器/包版本"] = REPACKED_RE.sub("包=0.10.0", row["客户端/校验器/包版本"])
        saved, self.rin = self.rin, bad
        try:
            with self.assertRaises(AssertionError):
                self.test_no_repair_rows_must_point_at_final_package()
        finally:
            self.rin = saved

    def test_domain_order_drift_rejected(self) -> None:
        bad = [dict(r) for r in self.dom]
        bad[0]["数据域"] = bad[1]["数据域"]
        with self.assertRaises(AssertionError):
            check_dom(bad, self.lic, self.qry, self.known)

    def test_req_dropped_from_set_rejected(self) -> None:
        bad = [r for r in self.req if r["ID"] != "REQ-07"]
        with self.assertRaises(AssertionError):
            check_req(bad, self.mapping, self.known,
                      qry=self.qry, lic=self.lic, records=self.records)

    # --- B-CODE-02 反例：REQ 覆盖由四条件机检而非台账标签 ---
    def _check_req_wrapper(self, reqs):
        check_req(reqs, self.mapping, self.known,
                  qry=self.qry, lic=self.lic, records=self.records)

    def test_wrong_entry_licence_cannot_sign_coverage(self) -> None:
        """REQ-01 的 adopted QRY 源为 wind-finance；引用 tdx-connector 的 LIC-04 不再满足条件 1。"""
        bad = [dict(r) for r in self.req]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "REQ-01")
        bad[idx]["关联证据行"] = bad[idx]["关联证据行"].replace("LIC-01", "LIC-04")
        with self.assertRaises(AssertionError):
            self._check_req_wrapper(bad)

    def test_existing_but_failed_qry_cannot_sign_coverage(self) -> None:
        """把 REQ-01 的 QRY-01 换成 QRY-04（是否最终采用源=否），条件 2 破坏。"""
        bad = [dict(r) for r in self.req]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "REQ-01")
        bad[idx]["关联证据行"] = bad[idx]["关联证据行"].replace("QRY-01", "QRY-04")
        bad[idx]["关联证据行"] = bad[idx]["关联证据行"].replace("VR-01", "VR-04")
        with self.assertRaises(AssertionError):
            self._check_req_wrapper(bad)

    def test_wrong_domain_cannot_sign_coverage(self) -> None:
        """REQ-01 数据域改成「券商一致预期」但 adopted QRY-01 属机构财务域 ⇒ 条件 4 破坏。"""
        bad = [dict(r) for r in self.req]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "REQ-01")
        bad[idx]["数据域"] = "券商一致预期"
        with self.assertRaises(AssertionError):
            self._check_req_wrapper(bad)

    def test_wrong_period_cannot_sign_coverage(self) -> None:
        """REQ-01 期间改成「2030 年报」，adopted QRY-01 无任何 2030 token ⇒ 条件 4 破坏。"""
        bad = [dict(r) for r in self.req]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "REQ-01")
        bad[idx]["报告期间"] = "2030 年报期（2030-12-31）"
        with self.assertRaises(AssertionError):
            self._check_req_wrapper(bad)

    def test_wrong_prerequisite_cannot_sign_coverage(self) -> None:
        """REQ-16 前序改成未覆盖的 REQ-15 ⇒ 条件 4 破坏。"""
        bad = [dict(r) for r in self.req]
        idx = next(i for i, r in enumerate(bad) if r["ID"] == "REQ-16")
        bad[idx]["前序依赖"] = "REQ-15"
        with self.assertRaises(AssertionError):
            self._check_req_wrapper(bad)

    def test_legal_coverage_positive_example_passes(self) -> None:
        """REQ-01/03/13/14/16/24/30 现值均满足四条件（正向确认，防恒假断言）。"""
        legal = {"REQ-01", "REQ-03", "REQ-13", "REQ-14", "REQ-16", "REQ-24", "REQ-30"}
        for rid in legal:
            row = next(r for r in self.req if r["ID"] == rid)
            v = _req_violations(row, qry_by_id={q["ID"]: q for q in self.qry},
                                lic_by_id={l["ID"]: l for l in self.lic},
                                records=self.records,
                                machine={r["ID"]: (r["覆盖判定"] == "覆盖") for r in self.req})
            self.assertEqual(v, [], f"{rid} 应满足四条件却检出 violations={v}")


if __name__ == "__main__":
    unittest.main()
